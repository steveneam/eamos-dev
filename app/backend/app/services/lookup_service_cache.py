from __future__ import annotations

from typing import Any

from app.schemas.lookup import (
    LookupInitialSummaryResponse,
    LookupRequest,
    LookupResponse,
    LookupSectionFetchRequest,
    LookupSectionFetchResponse,
)
from app.schemas.run import EvidenceSourceSummary
from app.services.lookup_sections import LAZY_SECTION_ORDER, build_lookup_section_fetch_response
from app.services.lookup_service_utils import dedupe_values
from app.tools.base import ToolResult

PUBLICATION_DATA_CACHE_VERSION = 2
STRICT_GENOMIC_CACHE_VERSION = 2
FUNCTIONAL_EVIDENCE_CACHE_VERSION = 4
GENE_CONTEXT_SNAPSHOT_CACHE_VERSION = 1
REPORT_SHELL_CACHE_VERSION = 1
REPORT_SECTION_CACHE_VERSION = 1
SOURCE_RESULT_CACHE_VERSION = 1
LEGACY_REPORT_SHELL_CACHE_READ_WARNING = "legacy_variant_publication_data_report_shell_cache_read"
LEGACY_REPORT_SECTIONS_CACHE_READ_WARNING = (
    "legacy_variant_publication_data_report_sections_cache_read"
)


def result_to_evidence(result: ToolResult) -> EvidenceSourceSummary:
    return EvidenceSourceSummary(
        source=result.source,
        status=result.status,
        request_identity=result.request_identity,
        summary=result.summary,
        warnings=result.warnings,
        source_url=result.source_url,
        fetched_at=result.fetched_at,
        source_version=result.source_version,
        cache_status=result.cache_status,
    )


def cached_functional_evidence_is_current(
    publication_cache: dict[str, Any],
    cached_functional_evidence: dict[str, Any],
) -> bool:
    if publication_cache.get("functional_evidence_cache_version") != (
        FUNCTIONAL_EVIDENCE_CACHE_VERSION
    ):
        return False

    metrics = cached_functional_evidence.get("display_metrics")
    if not isinstance(metrics, dict):
        return False
    required_metric_fields = {
        "state",
        "primary_label",
        "acmg_badge_text",
        "verdict_source",
        "study_count_badge_text",
        "conflict_split",
        "code_rests_on",
        "ui_color_theme",
    }
    if not required_metric_fields.issubset(metrics):
        return False

    state = metrics.get("state")
    verdict_source = metrics.get("verdict_source")
    total_count = cached_functional_evidence.get("total_count")
    has_codes = bool(
        cached_functional_evidence.get("evidence_codes")
        or cached_functional_evidence.get("source_asserted_codes")
    )
    if state == "none":
        return (
            total_count == 0
            and verdict_source == "none"
            and not has_codes
            and metrics.get("acmg_badge_text") == "None"
            and metrics.get("ui_color_theme") == "neutral_slate_state"
        )
    if state in {"strong_deficit", "emerging_deficit", "normal"}:
        code_rests_on = metrics.get("code_rests_on")
        return verdict_source in {"clingen", "clinvar", "clingen+clinvar"} and (
            code_rests_on is None or isinstance(code_rests_on, dict)
        )
    if state == "conflict":
        return verdict_source == "conflict"
    if state == "uncurated":
        return (
            isinstance(total_count, int)
            and total_count > 0
            and verdict_source == "uncurated"
            and metrics.get("acmg_badge_text") == "No code asserted"
        )
    return False


def publication_data_cache_is_current(publication_cache: dict[str, Any]) -> bool:
    return publication_cache.get("publication_data_cache_version") == PUBLICATION_DATA_CACHE_VERSION


def report_shell_cache_payload(summary: LookupInitialSummaryResponse) -> dict[str, Any]:
    return {
        "report_shell_cache_version": REPORT_SHELL_CACHE_VERSION,
        "summary": summary.model_dump(mode="json"),
    }


def summary_from_report_shell_cache(
    publication_cache: dict[str, Any],
) -> LookupInitialSummaryResponse | None:
    shell = publication_cache.get("report_shell")
    if not isinstance(shell, dict):
        return None
    if shell.get("report_shell_cache_version") != REPORT_SHELL_CACHE_VERSION:
        return None
    summary = shell.get("summary")
    if not isinstance(summary, dict):
        return None
    try:
        response = LookupInitialSummaryResponse.model_validate(summary)
    except Exception:
        return None
    response.warnings = dedupe_values([*response.warnings, LEGACY_REPORT_SHELL_CACHE_READ_WARNING])
    return response


def summary_from_report_shell_payload(
    payload: dict[str, Any],
) -> LookupInitialSummaryResponse | None:
    try:
        return LookupInitialSummaryResponse.model_validate(payload)
    except Exception:
        return None


def report_sections_cache_payload(response: LookupResponse) -> dict[str, Any]:
    section_response = build_lookup_section_fetch_response(response, list(LAZY_SECTION_ORDER))
    return report_sections_cache_payload_from_response(section_response)


def report_sections_cache_payload_from_response(
    response: LookupSectionFetchResponse,
) -> dict[str, Any]:
    return {
        "report_section_cache_version": REPORT_SECTION_CACHE_VERSION,
        "response": response.model_dump(mode="json"),
    }


def cached_report_sections_response(
    publication_cache: dict[str, Any],
) -> LookupSectionFetchResponse | None:
    cached = publication_cache.get("report_sections")
    if not isinstance(cached, dict):
        return None
    if cached.get("report_section_cache_version") != REPORT_SECTION_CACHE_VERSION:
        return None
    response_payload = cached.get("response")
    if not isinstance(response_payload, dict):
        return None
    try:
        return LookupSectionFetchResponse.model_validate(response_payload)
    except Exception:
        return None


def sections_from_report_section_cache(
    publication_cache: dict[str, Any],
    include: list[str],
) -> LookupSectionFetchResponse | None:
    cached_response = cached_report_sections_response(publication_cache)
    if cached_response is None:
        return None
    if any(section_id not in cached_response.sections for section_id in include):
        return None
    return LookupSectionFetchResponse(
        query=cached_response.query,
        species=cached_response.species,
        sections={section_id: cached_response.sections[section_id] for section_id in include},
        warnings=dedupe_values(
            [*cached_response.warnings, LEGACY_REPORT_SECTIONS_CACHE_READ_WARNING]
        ),
    )


def sections_from_report_section_payload(
    payload: dict[str, Any],
    include: list[str],
) -> LookupSectionFetchResponse | None:
    try:
        cached_response = LookupSectionFetchResponse.model_validate(payload)
    except Exception:
        return None
    if any(section_id not in cached_response.sections for section_id in include):
        return None
    return LookupSectionFetchResponse(
        query=cached_response.query,
        species=cached_response.species,
        sections={section_id: cached_response.sections[section_id] for section_id in include},
        warnings=list(cached_response.warnings),
    )


def merged_report_sections_cache_payload(
    publication_cache: dict[str, Any],
    response: LookupSectionFetchResponse,
) -> dict[str, Any]:
    cached_response = cached_report_sections_response(publication_cache)
    if cached_response is None:
        return report_sections_cache_payload_from_response(response)

    sections = dict(cached_response.sections)
    sections.update(response.sections)
    return report_sections_cache_payload_from_response(
        LookupSectionFetchResponse(
            query=response.query or cached_response.query,
            species=response.species or cached_response.species,
            sections=sections,
            warnings=dedupe_values([*cached_response.warnings, *response.warnings]),
        )
    )


def strict_genomic_cache_is_current(cached_strict: dict[str, Any]) -> bool:
    if cached_strict.get("strict_genomic_cache_version") != STRICT_GENOMIC_CACHE_VERSION:
        return False
    return isinstance(cached_strict.get("variant"), dict) and isinstance(
        cached_strict.get("evidence"),
        dict,
    )


def gene_context_snapshot_cache_is_current(cached_snapshot: dict[str, Any]) -> bool:
    if (
        cached_snapshot.get("gene_context_snapshot_cache_version")
        != GENE_CONTEXT_SNAPSHOT_CACHE_VERSION
    ):
        return False
    snapshot = cached_snapshot.get("snapshot")
    return isinstance(snapshot, dict) and "protein_domain_track" in snapshot


def evidence_summary_to_result(item: dict[str, Any]) -> ToolResult:
    return ToolResult(
        source=item.get("source", ""),
        status=item.get("status", "cache"),
        request_identity=item.get("request_identity", {}),
        summary=item.get("summary", {}),
        warnings=item.get("warnings", []),
        raw=item.get("raw"),
        source_url=item.get("source_url"),
        fetched_at=item.get("fetched_at"),
        source_version=item.get("source_version"),
        cache_status=item.get("cache_status"),
    )


def source_result_cache_to_result(source_id: str, item: dict[str, Any]) -> ToolResult:
    freshness = item.get("freshness") if isinstance(item.get("freshness"), dict) else {}
    source_versions = (
        item.get("source_versions") if isinstance(item.get("source_versions"), dict) else {}
    )
    source_status = str(freshness.get("source_status") or item.get("status") or "cache")
    status = "stale" if freshness.get("stale_on_failure") else source_status
    if status in {"live", "local", "fixture", "fallback"}:
        status = "cache"
    source_version = freshness.get("source_version") or source_versions.get("source_version")
    return ToolResult(
        source=source_id,
        status=status,
        request_identity={},
        summary=item.get("payload") if isinstance(item.get("payload"), dict) else {},
        warnings=list(item.get("warnings") or []),
        raw=item.get("raw"),
        source_url=freshness.get("source_url"),
        fetched_at=freshness.get("fetched_at"),
        source_version=str(source_version) if source_version else None,
        cache_status="cache_hit",
    )


def source_version_from_result(result: ToolResult) -> str | None:
    if result.source_version:
        return result.source_version
    summary = result.summary or {}
    for key in ("source_version", "version", "dataset"):
        value = summary.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def source_cache_token(value: str | None) -> str:
    return (value or "").strip().removeprefix("chr").lower()


def report_cache_identity_from_resolution(
    *,
    cache_key: str,
    input_resolution: Any,
    request: LookupRequest | LookupSectionFetchRequest,
) -> dict[str, Any]:
    return {
        "identity_version": 1,
        "query_string": cache_key,
        "species": request.species,
        "genome_build": "GRCh38",
        "gene": getattr(input_resolution, "gene", None),
        "cdna": getattr(input_resolution, "hgvs", None),
        "transcript": getattr(input_resolution, "resolver_transcript", None),
        "protein_change": getattr(input_resolution, "protein_change", None),
        "genomic_hg38": getattr(input_resolution, "genomic_hg38", None),
        "genomic_hgvs": getattr(input_resolution, "genomic_hgvs", None),
        "request_identity": {
            "gene": request.gene,
            "cdna": request.cdna,
            "transcript": request.transcript,
            "protein_change": request.protein_change,
        },
    }


def report_cache_identity_from_response(
    *,
    cache_key: str,
    response: LookupResponse,
) -> dict[str, Any]:
    gene, _, cdna = cache_key.partition(":")
    summary_row = next(iter(response.report_payload.variant_summary_rows or []), None)
    return {
        "identity_version": 1,
        "query_string": cache_key,
        "species": response.species,
        "genome_build": "GRCh38",
        "gene": gene or None,
        "cdna": cdna or None,
        "transcript": getattr(summary_row, "transcript", None),
        "protein_change": getattr(summary_row, "protein_change", None),
        "genomic_hg38": getattr(summary_row, "genomic_hg38", None),
        "genomic_hgvs": getattr(summary_row, "genomic_hgvs", None),
        "request_identity": {"query": cache_key},
    }


def report_cache_identity_from_variant(
    *,
    cache_key: str,
    variant: Any,
    species: str = "human",
) -> dict[str, Any]:
    gene, _, cdna = cache_key.partition(":")
    return {
        "identity_version": 1,
        "query_string": cache_key,
        "species": species,
        "genome_build": "GRCh38",
        "gene": getattr(variant, "gene", None) or gene or None,
        "cdna": getattr(variant, "transcript_hgvs", None) or cdna or None,
        "transcript": getattr(variant, "transcript", None),
        "protein_change": getattr(variant, "protein_change", None),
        "genomic_hg38": getattr(variant, "genomic_hg38", None),
        "genomic_hgvs": getattr(variant, "genomic_hgvs", None),
        "request_identity": {"query": cache_key},
    }


def annotate_source_cached_result(name: str, result: ToolResult, *, cache_key: str) -> None:
    if name != "clingen":
        return
    expert_panel = (result.summary or {}).get("expert_panel")
    if not isinstance(expert_panel, dict):
        return
    provenance = expert_panel.get("provenance")
    if not isinstance(provenance, dict):
        return
    provenance.setdefault("cache_record_id", f"clingen:{cache_key}")


def hydrate_variant_from_source_result(variant, source_name: str, result: ToolResult) -> None:
    summary = result.summary or {}
    if source_name == "variant_validator":
        variant_id = summary.get("variant_id")
        if isinstance(variant_id, str) and variant_id:
            variant.genomic_hg38 = variant_id
        genomic_hgvs = summary.get("hgvs_genomic_description")
        if isinstance(genomic_hgvs, str) and genomic_hgvs:
            variant.genomic_hgvs = genomic_hgvs
        variation_type = summary.get("variation_type") or summary.get("variant_type")
        if isinstance(variation_type, str) and variation_type and not variant.variation_type:
            variant.variation_type = variation_type
        consequence = summary.get("consequence") or summary.get("most_severe_consequence")
        if isinstance(consequence, str) and consequence and not variant.consequence:
            variant.consequence = consequence
