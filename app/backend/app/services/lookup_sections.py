from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from app.schemas.lookup import (
    LookupInitialSummaryResponse,
    LookupResponse,
    LookupSectionDescriptor,
    LookupSectionEnvelope,
    LookupSectionFetchResponse,
    LookupSectionFreshness,
    LookupSectionId,
    LookupSectionStatus,
    LookupSummaryTile,
)
from app.schemas.run import EvidenceSourceSummary, SourceProvenance

SECTION_FETCH_ENDPOINT = "/api/v1/lookup/sections"
LAZY_SECTION_ORDER: tuple[LookupSectionId, ...] = (
    "publications",
    "computational_deep_dive",
    "clingen_vcep",
)
TILE_FETCH_SECTION: dict[str, LookupSectionId] = {
    "computational": "computational_deep_dive",
    "clinical_consensus": "clingen_vcep",
}
SECTION_SOURCE_HINTS: dict[LookupSectionId, tuple[str, ...]] = {
    "publications": ("litvar2", "pubmed", "clinvar"),
    "computational_deep_dive": (
        "computational_annotations",
        "spliceai",
        "vep",
        "dbnsfp",
        "cadd",
    ),
    "clingen_vcep": ("clingen", "clinvar", "clinical_consensus"),
}
STATUS_PRIORITY = ("live", "cache", "stale", "fixture", "fallback", "error", "failed", "missing")


def build_lookup_initial_summary(response: LookupResponse) -> LookupInitialSummaryResponse:
    """Return the M7 cheap-summary contract without embedding heavy section payloads."""

    profile = response.report_payload.report_profile
    header = (
        profile.header.model_dump(mode="json")
        if profile is not None and profile.header is not None
        else None
    )
    return LookupInitialSummaryResponse(
        query=response.query,
        species=response.species,
        header=header,
        tiles=_summary_tiles(response),
        lazy_sections=[
            LookupSectionDescriptor(section_id=section_id, include_value=section_id)
            for section_id in LAZY_SECTION_ORDER
        ],
        warnings=list(response.warnings),
    )


def build_lookup_section_fetch_response(
    response: LookupResponse,
    include: list[LookupSectionId],
) -> LookupSectionFetchResponse:
    sections = {section_id: _section_envelope(response, section_id) for section_id in include}
    return LookupSectionFetchResponse(
        query=response.query,
        species=response.species,
        sections=sections,
        warnings=list(response.warnings),
    )


def _summary_tiles(response: LookupResponse) -> list[LookupSummaryTile]:
    call_cards = response.report_payload.call_cards
    if call_cards is None:
        return []

    tiles: list[LookupSummaryTile] = []
    for card in call_cards.cards:
        interaction = card.interaction
        tiles.append(
            LookupSummaryTile(
                tile_id=card.card_id,
                title=card.title,
                primary_label=card.primary_label,
                support_badges=[badge.text for badge in card.support_badges],
                source_status=card.source_status,
                ui_color_theme=card.ui_color_theme,
                target_section_id=(
                    interaction.target_section_id if interaction is not None else None
                ),
                target_panel_id=interaction.target_panel_id if interaction is not None else None,
                fetch_section_id=TILE_FETCH_SECTION.get(card.card_id),
                warnings=list(card.warnings),
            )
        )
    return tiles


def _section_envelope(
    response: LookupResponse,
    section_id: LookupSectionId,
) -> LookupSectionEnvelope:
    if section_id == "publications":
        return _publications_envelope(response)
    if section_id == "computational_deep_dive":
        return _computational_envelope(response)
    return _clingen_vcep_envelope(response)


def _publications_envelope(response: LookupResponse) -> LookupSectionEnvelope:
    section = response.report_payload.publications_literature
    status: LookupSectionStatus = "available" if section is not None else "missing"
    return LookupSectionEnvelope(
        section_id="publications",
        status=status,
        payload=section.model_dump(mode="json") if section is not None else None,
        freshness=_freshness(response, "publications"),
        warnings=list(section.warnings) if section is not None else ["publications_unavailable"],
    )


def _computational_envelope(response: LookupResponse) -> LookupSectionEnvelope:
    profile = response.report_payload.report_profile
    section = profile.computational_deep_dive if profile is not None else None
    has_payload = section is not None and (
        section.predictors or section.conservation or section.spliceai_max_delta is not None
    )
    status: LookupSectionStatus = "available" if has_payload else "missing"
    provenance = section.provenance if section is not None else []
    return LookupSectionEnvelope(
        section_id="computational_deep_dive",
        status=status,
        payload=section.model_dump(mode="json") if section is not None else None,
        freshness=_freshness(response, "computational_deep_dive", provenance=provenance),
        warnings=(
            list(section.warnings)
            if section is not None
            else ["computational_deep_dive_unavailable"]
        ),
    )


def _clingen_vcep_envelope(response: LookupResponse) -> LookupSectionEnvelope:
    profile = response.report_payload.report_profile
    expert_panel = profile.expert_panel if profile is not None else None
    if expert_panel is not None:
        return LookupSectionEnvelope(
            section_id="clingen_vcep",
            status="available",
            payload=expert_panel.model_dump(mode="json"),
            freshness=_freshness(response, "clingen_vcep"),
            warnings=[],
        )

    worksheet = profile.acmg_worksheet if profile is not None else None
    if worksheet is None:
        return LookupSectionEnvelope(
            section_id="clingen_vcep",
            status="missing",
            payload=None,
            freshness=_freshness(response, "clingen_vcep"),
            warnings=["clingen_vcep_unavailable"],
        )

    payload: dict[str, Any] = worksheet.model_dump(mode="json")
    payload["narrative"] = response.report_payload.acmg_classification
    payload["source_scope"] = "current_clinical_consensus_snapshot"
    warnings = [
        "clingen_vcep_evidence_repo_source_cache_not_integrated",
        *[warning for criterion in worksheet.criteria for warning in (criterion.warnings or [])],
    ]
    return LookupSectionEnvelope(
        section_id="clingen_vcep",
        status="partial",
        payload=payload,
        freshness=_freshness(response, "clingen_vcep"),
        warnings=_dedupe(warnings),
    )


def _freshness(
    response: LookupResponse,
    section_id: LookupSectionId,
    *,
    provenance: Iterable[SourceProvenance] = (),
) -> LookupSectionFreshness:
    evidence = _matching_evidence(response.evidence, SECTION_SOURCE_HINTS[section_id])
    provenance_items = list(provenance)
    return LookupSectionFreshness(
        fetched_at=_first_text(item.fetched_at for item in evidence)
        or _first_datetime(item.retrieved_at for item in provenance_items),
        source_version=_first_text(item.source_version for item in evidence)
        or _first_text(item.version for item in provenance_items),
        stale_on_failure=any(
            item.cache_status == "stale_on_failure" or item.status == "stale" for item in evidence
        ),
        source_status=_best_status(
            [item.status for item in evidence] + [item.status for item in provenance_items]
        ),
        source_url=_first_text(item.source_url for item in evidence)
        or _first_text(item.source_url for item in provenance_items),
    )


def _matching_evidence(
    evidence: list[EvidenceSourceSummary],
    source_hints: tuple[str, ...],
) -> list[EvidenceSourceSummary]:
    hints = tuple(_source_key(item) for item in source_hints)
    return [
        item
        for item in evidence
        if any(_source_matches(_source_key(item.source), hint) for hint in hints)
    ]


def _source_key(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum())


def _source_matches(source: str, hint: str) -> bool:
    return source == hint or source.endswith(hint) or hint in source


def _first_text(values: Iterable[str | None]) -> str | None:
    for value in values:
        text = (value or "").strip()
        if text:
            return text
    return None


def _first_datetime(values: Iterable[datetime | None]) -> str | None:
    for value in values:
        if value is not None:
            return value.isoformat()
    return None


def _best_status(values: Iterable[str | None]) -> str | None:
    statuses = {_source_status(value) for value in values}
    for status in STATUS_PRIORITY:
        if status in statuses:
            return status
    return None


def _source_status(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    return normalized if normalized in STATUS_PRIORITY else "fallback"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = value.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
