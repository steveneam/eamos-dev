from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Any, Literal, cast, get_args

from app.schemas.capabilities import CapabilityExecutionDisclosureV2
from app.schemas.report import (
    ReportExecutionStateV2,
    ReportMatchLevelV2,
    ReportPredictorExecutionV2,
    ReportSectionExecutionV2,
    ReportSectionIdV2,
)
from app.schemas.run import (
    ComputationalPredictorRow,
    EvidenceSourceSummary,
    ReportPayload,
)
from app.schemas.workflow import CanonicalVariantRefV1
from app.services.report_source_truth import (
    normalize_report_source_status,
    report_source_category,
)
from app.services.search_input_resolver import SearchInputResolution

_CANONICAL_SOURCES = frozenset(
    {
        "clinvar",
        "computational_annotations",
        "gnomad",
        "spliceai",
        "variant_validator",
        "vep",
    }
)
_IDENTITY_KEYS = (
    "variant_id",
    "genomic_hg38",
    "genomic_hgvs",
    "hgvs",
    "query",
    "search_text",
    "submitted",
    "submitted_variant",
    "hgvs_transcript_variant",
    "transcript_hgvs",
    "cdna",
)
_SECTION_ORDER = cast(tuple[ReportSectionIdV2, ...], get_args(ReportSectionIdV2))
_SECTION_SOURCES: dict[ReportSectionIdV2, tuple[str, ...]] = {
    "header": ("variant_validator", "vep", "clinvar", "gnomad"),
    "interpretation_summary": ("clinical_consensus", "clinvar"),
    "disease_mechanism": ("gene_disease",),
    "gene_context_snapshot": ("gene_context_snapshot",),
    "population_frequency": ("gnomad",),
    "molecular_context": (
        "molecular_context",
        "sequence_context",
        "gene_context_snapshot",
        "vep",
        "variant_validator",
    ),
    "computational_deep_dive": ("computational_annotations", "spliceai", "vep"),
    "acmg_worksheet": ("clinical_consensus", "clinvar"),
    "expert_panel": ("clingen", "clinvar"),
    "publications": ("litvar2", "pubmed", "clinvar", "clingen"),
    "therapies_trials": ("clinical_trials",),
    "provenance": (),
}
_SECTION_MATCH_LEVEL: dict[ReportSectionIdV2, ReportMatchLevelV2] = {
    "header": "exact_allele",
    "interpretation_summary": "exact_allele",
    "disease_mechanism": "gene_disease",
    "gene_context_snapshot": "transcript",
    "population_frequency": "exact_allele",
    "molecular_context": "transcript",
    "computational_deep_dive": "exact_allele",
    "acmg_worksheet": "exact_allele",
    "expert_panel": "exact_allele",
    "publications": "exact_allele",
    "therapies_trials": "discovery_only",
    "provenance": "exact_allele",
}


@dataclass(frozen=True)
class ReportExecutionBuildResult:
    state: ReportExecutionStateV2 | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _PredictorSpec:
    predictor_id: str
    aliases: tuple[str, ...]
    missense_only: bool
    missing_requirement: str


_PREDICTOR_SPECS = (
    _PredictorSpec(
        "alphamissense",
        ("alphamissense",),
        True,
        "Mount the AlphaMissense source file with an immutable manifest.",
    ),
    _PredictorSpec(
        "esm1b",
        ("esm1b", "esm-1b", "esm1b llr"),
        True,
        "Mount the ESM-1b score artifact with an immutable manifest.",
    ),
    _PredictorSpec(
        "revel",
        ("revel",),
        True,
        "Mount the REVEL score artifact with an immutable manifest.",
    ),
    _PredictorSpec(
        "primateai-3d",
        ("primateai-3d", "primateai3d", "primateai"),
        True,
        "Mount the PrimateAI-3D score artifact with an immutable manifest.",
    ),
    _PredictorSpec(
        "capice",
        ("capice",),
        False,
        "Mount the CAPICE model artifact with an immutable manifest.",
    ),
    _PredictorSpec(
        "ci-spliceai",
        ("ci-spliceai", "cispliceai"),
        False,
        "Mount the CI-SpliceAI model artifact with an immutable manifest.",
    ),
    _PredictorSpec(
        "spliceai",
        ("spliceai",),
        False,
        "Provide a source-backed SpliceAI score for the resolved allele.",
    ),
)


def report_identity_mismatched_sources(
    *,
    resolution: SearchInputResolution,
    evidence: list[EvidenceSourceSummary],
) -> frozenset[str]:
    """Return current/stale exact-source rows that contradict the resolved allele."""

    gene = str(getattr(resolution, "gene", None) or "").strip().upper()
    cdna = str(getattr(resolution, "hgvs", None) or "").strip()
    transcript = getattr(resolution, "resolver_transcript", None) or getattr(
        resolution,
        "transcript",
        None,
    )
    genomic = getattr(resolution, "genomic_hg38", None)
    if not gene or not cdna or not genomic:
        return frozenset()
    expected = _expected_identity_values(
        resolution=resolution,
        gene=gene,
        cdna=cdna,
        transcript=transcript,
        genomic=genomic,
    )
    mismatched = {
        _source_key(item.source)
        for item in evidence
        if _source_key(item.source) in _CANONICAL_SOURCES
        and _status_category(item.status) in {"current", "stale"}
        and _evidence_identity_result(
            item,
            gene=gene,
            cdna=cdna,
            expected=expected,
        )[1]
    }
    _, resolver_mismatch = _resolver_source_support(
        resolution=resolution,
        gene=gene,
        expected=expected,
    )
    if resolver_mismatch:
        mismatched.update(
            _source_key(item.source)
            for item in evidence
            if _status_category(item.status) in {"current", "stale"}
        )
    return frozenset(mismatched)


def build_report_execution_state_v2(
    *,
    resolution: SearchInputResolution,
    payload: ReportPayload,
    evidence: list[EvidenceSourceSummary],
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
    section_ids: Iterable[ReportSectionIdV2] | None = None,
) -> ReportExecutionBuildResult:
    """Build the canonical, fail-closed execution snapshot for a variant report.

    The snapshot contains only bounded status codes and opaque digests. Raw source
    payloads, user text, filesystem paths, and provider exception messages never
    enter the contract.
    """

    canonical_result = _canonical_variant(
        resolution=resolution,
        payload=payload,
        evidence=evidence,
    )
    if canonical_result.variant is None:
        return ReportExecutionBuildResult(state=None, warnings=canonical_result.warnings)

    canonical = canonical_result.variant
    selected_sections = _selected_sections(section_ids)
    snapshot_id = _source_snapshot_id(
        canonical=canonical,
        evidence=evidence,
        evidence_statuses=evidence_statuses,
    )
    source_rows = _source_rows(
        evidence=evidence,
        evidence_map=evidence_map,
        evidence_statuses=evidence_statuses,
    )
    sections = [
        _section_execution(
            section_id=section_id,
            payload=payload,
            source_rows=source_rows,
            source_snapshot_id=snapshot_id,
        )
        for section_id in selected_sections
    ]
    predictors = _predictor_executions(
        payload=payload,
        evidence_map=evidence_map,
        evidence_statuses=evidence_statuses,
        source_rows=source_rows,
        source_snapshot_id=snapshot_id,
    )
    coverage: Literal["partial", "complete"] = (
        "complete" if tuple(selected_sections) == _SECTION_ORDER else "partial"
    )
    state = ReportExecutionStateV2(
        coverage=coverage,
        canonical_variant=canonical,
        source_snapshot_id=snapshot_id,
        sections=sections,
        predictors=predictors,
    )
    return ReportExecutionBuildResult(state=state, warnings=canonical_result.warnings)


@dataclass(frozen=True)
class _CanonicalBuildResult:
    variant: CanonicalVariantRefV1 | None
    warnings: tuple[str, ...]


def _canonical_variant(
    *,
    resolution: SearchInputResolution,
    payload: ReportPayload,
    evidence: list[EvidenceSourceSummary],
) -> _CanonicalBuildResult:
    row = payload.variant_summary_rows[0] if payload.variant_summary_rows else None
    gene = str(resolution.gene or (row.gene if row is not None else "")).strip().upper()
    cdna = str(resolution.hgvs or "").strip()
    transcript = resolution.resolver_transcript or resolution.transcript
    protein = resolution.protein_change or (row.protein_change if row is not None else None)
    genomic = resolution.genomic_hg38 or (row.genomic_hg38 if row is not None else None)
    if not gene or not cdna or not genomic:
        return _CanonicalBuildResult(
            variant=None,
            warnings=("report_canonical_identity_unresolved",),
        )
    if resolution.kind == "cdna" and not transcript:
        return _CanonicalBuildResult(
            variant=None,
            warnings=("report_canonical_transcript_unresolved",),
        )

    expected = _expected_identity_values(
        resolution=resolution,
        gene=gene,
        cdna=cdna,
        transcript=transcript,
        genomic=genomic,
    )
    support: list[str] = []
    mismatch = False
    for item in evidence:
        source = _source_key(item.source)
        if source not in _CANONICAL_SOURCES or _status_category(item.status) not in {
            "current",
            "stale",
        }:
            continue
        matched, contradicted = _evidence_identity_result(
            item,
            gene=gene,
            cdna=cdna,
            expected=expected,
        )
        if contradicted:
            mismatch = True
        if matched and item.source not in support:
            support.append(item.source)

    resolver_support, resolver_mismatch = _resolver_source_support(
        resolution=resolution,
        gene=gene,
        expected=expected,
    )
    mismatch = mismatch or resolver_mismatch
    for source in resolver_support:
        if source not in support:
            support.append(source)

    if mismatch:
        return _CanonicalBuildResult(
            variant=None,
            warnings=("report_canonical_identity_source_mismatch",),
        )
    if not support:
        return _CanonicalBuildResult(
            variant=None,
            warnings=("report_canonical_identity_source_unavailable",),
        )

    identity_material = {
        "gene": gene,
        "cdna": cdna,
        "transcript": transcript,
        "protein": protein,
        "genomic": genomic,
    }
    variant_key = f"cv~{_digest(identity_material)[:24]}"
    return _CanonicalBuildResult(
        variant=CanonicalVariantRefV1(
            schema_version="canonical_variant_ref.v1",
            gene=gene,
            cdna=cdna,
            transcript=transcript,
            protein_hgvs=protein,
            genomic_hg38=genomic,
            variant_key=variant_key,
            species="human",
            genome_build="GRCh38",
            resolution_status="resolved",
            source_support=support,
            warnings=[],
        ),
        warnings=(),
    )


def _expected_identity_values(
    *,
    resolution: SearchInputResolution,
    gene: str,
    cdna: str,
    transcript: str | None,
    genomic: str,
) -> set[str]:
    values = {
        genomic,
        resolution.genomic_hgvs,
        resolution.genomic_hg38,
        resolution.transcript_hgvs,
        resolution.resolver_transcript_hgvs,
        resolution.protein_change,
        cdna,
        f"{gene}:{cdna}",
        f"{transcript}:{cdna}" if transcript else None,
    }
    return {_identity_text(value) for value in values if value}


def _evidence_identity_result(
    item: EvidenceSourceSummary,
    *,
    gene: str,
    cdna: str,
    expected: set[str],
) -> tuple[bool, bool]:
    item_gene = _first_text(item.request_identity.get("gene"), item.summary.get("gene"))
    if item_gene and item_gene.upper() != gene:
        return False, True

    candidates: list[str] = []
    for container in (item.request_identity, item.summary):
        for key in _IDENTITY_KEYS:
            value = container.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value.strip())
    if not candidates:
        return False, False

    matched = False
    contradicted = False
    for candidate in candidates:
        normalized = _identity_text(candidate)
        if normalized in expected:
            matched = True
            continue
        if _identity_value_kind(normalized) != "cdna" and any(
            value and value in normalized for value in expected if len(value) >= 8
        ):
            matched = True
            continue
        if normalized == _identity_text(cdna) and item_gene:
            matched = True
            continue
        contradicted = contradicted or _identity_value_contradicts_expected(candidate, expected)

    return matched and not contradicted, contradicted


def _resolver_source_support(
    *,
    resolution: SearchInputResolution,
    gene: str,
    expected: set[str],
) -> tuple[list[str], bool]:
    audit = resolution.coordinate_resolution_audit
    support: list[str] = []
    mismatch = False
    if audit.used_eamos_local and isinstance(resolution.local_coordinate_summary, dict):
        matched, contradicted = _mapping_identity_result(
            resolution.local_coordinate_summary,
            gene=gene,
            expected=expected,
        )
        if matched:
            support.append("eamos_local_coordinate_resolver")
        mismatch = mismatch or contradicted
    if audit.used_variant_validator and isinstance(resolution.variant_validator_summary, dict):
        matched, contradicted = _mapping_identity_result(
            resolution.variant_validator_summary,
            gene=gene,
            expected=expected,
        )
        if matched:
            support.append("variant_validator")
        mismatch = mismatch or contradicted
    return support, mismatch


def _mapping_identity_result(
    mapping: dict[str, Any],
    *,
    gene: str,
    expected: set[str],
) -> tuple[bool, bool]:
    mapped_gene = _first_text(mapping.get("gene"), mapping.get("gene_symbol"))
    if mapped_gene and mapped_gene.upper() != gene:
        return False, True
    candidates = [
        str(mapping[key]).strip()
        for key in _IDENTITY_KEYS
        if mapping.get(key) is not None and str(mapping[key]).strip()
    ]
    matched = any(_identity_text(item) in expected for item in candidates)
    contradicted = any(
        _identity_text(item) not in expected
        and _identity_value_contradicts_expected(item, expected)
        for item in candidates
    )
    return matched and not contradicted, contradicted


def _selected_sections(
    section_ids: Iterable[ReportSectionIdV2] | None,
) -> tuple[ReportSectionIdV2, ...]:
    if section_ids is None:
        return _SECTION_ORDER
    requested = set(section_ids)
    return tuple(section_id for section_id in _SECTION_ORDER if section_id in requested)


def _source_rows(
    *,
    evidence: list[EvidenceSourceSummary],
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
) -> dict[str, EvidenceSourceSummary]:
    result: dict[str, EvidenceSourceSummary] = {}
    for item in evidence:
        result[_source_key(item.source)] = item
    for source, status in evidence_statuses.items():
        key = _source_key(source)
        if key in result:
            continue
        result[key] = EvidenceSourceSummary(
            source=source,
            status=status,
            summary=evidence_map.get(source, {}),
        )
    return result


def _section_execution(
    *,
    section_id: ReportSectionIdV2,
    payload: ReportPayload,
    source_rows: dict[str, EvidenceSourceSummary],
    source_snapshot_id: str,
) -> ReportSectionExecutionV2:
    sources = _SECTION_SOURCES[section_id]
    candidates = (
        list(source_rows.values())
        if section_id == "provenance"
        else [source_rows[source] for source in sources if source in source_rows]
    )
    disclosures = [_source_disclosure(item=item, section_id=section_id) for item in candidates]
    if not disclosures:
        disclosures = [_missing_section_disclosure(section_id)]

    categories = [_status_category(item.status) for item in candidates]
    executed = any(
        item.execution in {"eamos_local", "mounted_artifact", "external_provider"}
        for item in disclosures
    )
    has_unavailable = any(
        item.applicability == "applicable" and item.execution == "unavailable"
        for item in disclosures
    )
    has_failed = any(item.validation_status == "failed" for item in disclosures)
    warnings = _dedupe([warning for item in disclosures for warning in item.warnings])
    stale = "stale" in categories
    if stale and executed:
        state = "stale"
        stale_on_failure = True
        warnings = _dedupe([*warnings, "report_section_stale_source_snapshot"])
    elif executed and (has_unavailable or has_failed):
        state = "partial"
        stale_on_failure = False
        warnings = _dedupe([*warnings, "report_section_partial_source_coverage"])
    elif executed:
        state = "ready" if _section_has_content(payload, section_id) else "empty"
        stale_on_failure = False
    elif has_failed:
        state = "failed"
        stale_on_failure = False
    else:
        state = "unavailable"
        stale_on_failure = False

    return ReportSectionExecutionV2(
        section_id=section_id,
        state=state,  # type: ignore[arg-type]
        match_level=_section_match_level(payload, section_id),
        source_snapshot_id=source_snapshot_id,
        execution_disclosures=disclosures,
        stale_on_failure=stale_on_failure,
        warnings=warnings,
    )


def _source_disclosure(
    *,
    item: EvidenceSourceSummary,
    section_id: ReportSectionIdV2,
) -> CapabilityExecutionDisclosureV2:
    source = _source_key(item.source) or "unknown"
    category = _status_category(item.status)
    version = _source_version(item)
    warnings = _dedupe([_warning_code(value) for value in item.warnings])
    requirements: list[str] = []
    not_found = any("not_found" in warning for warning in warnings)

    common: dict[str, Any] = {
        "capability_id": _opaque_id(f"report.{section_id}.{source}"),
        "claim": f"Retrieve {source} evidence for the {section_id} report section.",
        "input_scope": _SECTION_MATCH_LEVEL[section_id],
        "applicability": "applicable",
        "retention": "none",
        "warnings": warnings,
        "requirements": requirements,
    }
    if version is None and category in {"current", "stale"}:
        warnings.append("source_version_unavailable")
        requirements.append(f"Pin and expose an immutable {source} source version.")

    if category == "current":
        if _normalized_status(item.status) == "live":
            return CapabilityExecutionDisclosureV2(
                **common,
                execution="external_provider",
                provider_id=_opaque_id(source),
                provider_version=version,
                source_status="not_found" if not_found else "source_backed",
                source_release=version,
                validation_status="unvalidated",
                consent_required=True,
            )
        return CapabilityExecutionDisclosureV2(
            **common,
            execution="eamos_local",
            algorithm_id=_opaque_id(f"eamos.report.{_normalized_status(item.status)}_lookup"),
            algorithm_version=version,
            source_status="not_found" if not_found else "source_backed",
            source_release=version,
            validation_status="unvalidated",
            consent_required=False,
        )
    if category == "stale":
        warnings.append("stale_source_snapshot")
        return CapabilityExecutionDisclosureV2(
            **common,
            execution="eamos_local",
            algorithm_id="eamos.report.stale_cache_lookup",
            algorithm_version=version,
            source_status="source_backed",
            source_release=version,
            validation_status="unvalidated",
            consent_required=False,
        )

    failed = category == "failed"
    requirements.append(_source_requirement(source, item.status))
    return CapabilityExecutionDisclosureV2(
        **common,
        execution="unavailable",
        source_status="unavailable",
        validation_status="failed" if failed else "unvalidated",
        consent_required=False,
    )


def _missing_section_disclosure(
    section_id: ReportSectionIdV2,
) -> CapabilityExecutionDisclosureV2:
    return CapabilityExecutionDisclosureV2(
        capability_id=f"report.{section_id}.availability",
        claim=f"Provide source-backed evidence for the {section_id} report section.",
        execution="unavailable",
        input_scope=_SECTION_MATCH_LEVEL[section_id],
        source_status="unavailable",
        applicability="applicable",
        validation_status="unvalidated",
        retention="none",
        consent_required=False,
        requirements=[f"Provide an identity-bound source for {section_id}."],
    )


def _section_has_content(payload: ReportPayload, section_id: ReportSectionIdV2) -> bool:
    profile = payload.report_profile
    if section_id == "header":
        return bool(profile and profile.header)
    if section_id == "interpretation_summary":
        return bool(
            profile
            and profile.interpretation_summary
            and profile.interpretation_summary.mode != "unavailable"
        )
    if section_id == "disease_mechanism":
        section = profile.disease_mechanism if profile else None
        return bool(
            section
            and (
                section.primary_condition
                or section.disease_ids
                or section.inheritance
                or section.gene_disease_validity
                or section.mechanism
            )
        )
    if section_id == "gene_context_snapshot":
        return bool(profile and profile.gene_context_snapshot)
    if section_id == "population_frequency":
        detail = payload.population_frequency_detail
        return bool(
            detail
            and (
                detail.allele_frequency is not None
                or detail.allele_count is not None
                or detail.genetic_ancestry_groups
            )
        )
    if section_id == "molecular_context":
        section = profile.molecular_context if profile else None
        return bool(
            section
            and any(
                value is not None and value != []
                for value in (
                    section.chromosome,
                    section.strand,
                    section.exon,
                    section.codon_change,
                    section.protein_position,
                    section.domain,
                    section.loeuf,
                    section.clingen_haploinsufficiency,
                    section.overlapping_cnvs,
                    section.protein_domain_track,
                )
            )
        )
    if section_id == "computational_deep_dive":
        section = profile.computational_deep_dive if profile else None
        return bool(
            section
            and (
                section.predictors or section.conservation or section.spliceai_max_delta is not None
            )
        )
    if section_id == "acmg_worksheet":
        section = profile.acmg_worksheet if profile else None
        return bool(section and (section.classification or section.criteria))
    if section_id == "expert_panel":
        return bool(profile and profile.expert_panel)
    if section_id == "publications":
        section = payload.publications_literature
        return bool(section and (section.total_count > 0 or section.articles))
    if section_id == "therapies_trials":
        section = profile.therapies_trials if profile else None
        return bool(section and section.trial_rows)
    return bool(profile and profile.provenance)


def _section_match_level(
    payload: ReportPayload,
    section_id: ReportSectionIdV2,
) -> ReportMatchLevelV2:
    if section_id == "publications" and payload.publications_literature is not None:
        return _publication_match_level(payload)
    if section_id == "therapies_trials":
        profile = payload.report_profile
        trials = profile.therapies_trials if profile else None
        levels = {row.match_level for row in (trials.trial_rows if trials else [])}
        if "disease_level" in levels:
            return "condition"
        if "gene_level" in levels:
            return "gene"
        if "variant_level" in levels:
            return "exact_allele"
    return _SECTION_MATCH_LEVEL[section_id]


def _publication_match_level(payload: ReportPayload) -> ReportMatchLevelV2:
    literature = payload.publications_literature
    if literature is None:
        return "discovery_only"
    if literature.scope == "gene":
        return "gene"

    levels: set[ReportMatchLevelV2] = set()
    for article in literature.articles:
        status = str(article.snippet_status or "").strip().lower()
        if status == "gene_only_no_variant":
            levels.add("gene")
            continue
        matched_terms = [
            term for snippet in article.snippets for term in snippet.matched_terms if term.strip()
        ]
        if any(_term_is_exact_allele(term) for term in matched_terms):
            levels.add("exact_allele")
        elif any(_term_is_protein(term) for term in matched_terms):
            levels.add("protein")
        elif matched_terms:
            levels.add("gene")
        else:
            levels.add("discovery_only")

    for conservative_level in ("discovery_only", "gene", "protein", "exact_allele"):
        if conservative_level in levels:
            return cast(ReportMatchLevelV2, conservative_level)
    return "discovery_only"


def _term_is_exact_allele(value: str) -> bool:
    normalized = _identity_text(value)
    return bool(
        re.search(r"(?:^|:)c\.", normalized)
        or re.search(r"(?:^|:)(?:g|n|m|r)\.", normalized)
        or normalized.startswith(("nc_", "rs"))
        or re.fullmatch(r"(?:[0-9]{1,2}|x|y|mt)-\d+-[acgtn]+-[acgtn]+", normalized)
    )


def _term_is_protein(value: str) -> bool:
    normalized = _identity_text(value)
    return bool(
        re.search(r"(?:^|:)p\.", normalized)
        or re.fullmatch(r"[a-z]{3}\d+(?:[a-z]{3}|ter|stop|\*)", normalized)
        or re.fullmatch(r"[acdefghiklmnpqrstvwy*]\d+[acdefghiklmnpqrstvwy*]", normalized)
    )


def _predictor_executions(
    *,
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
    source_rows: dict[str, EvidenceSourceSummary],
    source_snapshot_id: str,
) -> list[ReportPredictorExecutionV2]:
    profile = payload.report_profile
    deep_dive = profile.computational_deep_dive if profile else None
    rows = list(deep_dive.predictors if deep_dive else [])
    computational = evidence_map.get("computational_annotations", {})
    warnings = _dedupe(
        [
            *[str(item) for item in computational.get("warnings", []) if isinstance(item, str)],
            *(
                source_rows.get("computational_annotations").warnings
                if source_rows.get("computational_annotations") is not None
                else []
            ),
        ]
    )
    aggregate_status = evidence_statuses.get("computational_annotations", "missing")
    missense = _missense_applicability(payload)
    result: list[ReportPredictorExecutionV2] = []
    consumed: set[int] = set()
    for spec in _PREDICTOR_SPECS:
        row_index, row = _matching_predictor_row(rows, spec.aliases)
        if row_index is not None:
            consumed.add(row_index)
        result.append(
            _predictor_execution(
                spec=spec,
                row=row,
                aggregate_status=aggregate_status,
                all_warnings=warnings,
                missense=missense,
                source_snapshot_id=source_snapshot_id,
            )
        )

    predictor_ids = {item.predictor_id for item in result}
    for index, row in enumerate(rows):
        if index in consumed:
            continue
        predictor_id = _predictor_id(row.name)
        if predictor_id in predictor_ids:
            continue
        result.append(
            _predictor_execution(
                spec=_PredictorSpec(
                    predictor_id=predictor_id,
                    aliases=(row.name,),
                    missense_only=False,
                    missing_requirement=(
                        f"Provide a source-backed {predictor_id} result for the resolved allele."
                    ),
                ),
                row=row,
                aggregate_status=aggregate_status,
                all_warnings=warnings,
                missense=missense,
                source_snapshot_id=source_snapshot_id,
            )
        )
        predictor_ids.add(predictor_id)
        if len(result) == 128:
            break
    return result


def _predictor_execution(
    *,
    spec: _PredictorSpec,
    row: ComputationalPredictorRow | None,
    aggregate_status: str,
    all_warnings: list[str],
    missense: bool | None,
    source_snapshot_id: str,
) -> ReportPredictorExecutionV2:
    relevant_warnings = _predictor_warnings(spec.predictor_id, all_warnings, row)
    if spec.missense_only and missense is False:
        disclosure = CapabilityExecutionDisclosureV2(
            capability_id=f"report.predictor.{spec.predictor_id}",
            claim=f"Execute {spec.predictor_id} for an applicable resolved allele.",
            execution="unavailable",
            algorithm_id=None,
            input_scope="exact_allele",
            source_status="not_applicable",
            applicability="not_applicable",
            validation_status="not_applicable",
            retention="none",
            consent_required=False,
        )
        return ReportPredictorExecutionV2(
            predictor_id=spec.predictor_id,
            applicability="not_applicable",
            state="not_applicable",
            source_snapshot_id=source_snapshot_id,
            execution_disclosure=disclosure,
            warnings=relevant_warnings,
        )

    applicability: Literal["applicable", "unknown"] = (
        "unknown" if spec.missense_only and missense is None else "applicable"
    )
    independent_local = bool(
        row
        and row.score is not None
        and row.source_id
        and "fixture" not in row.source_id.casefold()
        and row.version
        and row.public_serialization_allowed is True
        and _source_key(row.source) != "fixture"
        and _normalized_status(aggregate_status) != "fixture"
    )
    category = _status_category(aggregate_status)
    executed = bool(
        row and row.score is not None and (category in {"current", "stale"} or independent_local)
    )
    if executed:
        algorithm_version = _safe_version(row.version)
        stale = category == "stale" and not independent_local
        disclosure = CapabilityExecutionDisclosureV2(
            capability_id=f"report.predictor.{spec.predictor_id}",
            claim=f"Execute {spec.predictor_id} for an applicable resolved allele.",
            execution="eamos_local",
            algorithm_id=spec.predictor_id,
            algorithm_version=algorithm_version,
            input_scope="exact_allele",
            source_status="source_backed",
            source_release=algorithm_version,
            applicability=applicability,
            validation_status="unvalidated",
            retention="none",
            consent_required=False,
            warnings=relevant_warnings,
            requirements=(
                []
                if algorithm_version
                else [f"Pin and expose an immutable {spec.predictor_id} algorithm version."]
            ),
        )
        predictor_warnings = list(relevant_warnings)
        if stale:
            predictor_warnings.append("predictor_stale_source_snapshot")
        return ReportPredictorExecutionV2(
            predictor_id=spec.predictor_id,
            applicability=applicability,
            state="stale" if stale else "executed",
            source_snapshot_id=source_snapshot_id,
            calibration_id=_opaque_id(row.calibration_id) if row.calibration_id else None,
            execution_disclosure=disclosure,
            stale_on_failure=stale,
            warnings=_dedupe(predictor_warnings),
        )

    failed = category == "failed" or any(
        token in warning for warning in relevant_warnings for token in ("_failed", "_timeout")
    )
    disclosure = CapabilityExecutionDisclosureV2(
        capability_id=f"report.predictor.{spec.predictor_id}",
        claim=f"Execute {spec.predictor_id} for an applicable resolved allele.",
        execution="unavailable",
        input_scope="exact_allele",
        source_status="unavailable",
        applicability=applicability,
        validation_status="failed" if failed else "unvalidated",
        retention="none",
        consent_required=False,
        warnings=relevant_warnings,
        requirements=[_predictor_requirement(spec, relevant_warnings)],
    )
    return ReportPredictorExecutionV2(
        predictor_id=spec.predictor_id,
        applicability=applicability,
        state="failed" if failed else "unavailable",
        source_snapshot_id=source_snapshot_id,
        calibration_id=(
            _opaque_id(row.calibration_id) if row is not None and row.calibration_id else None
        ),
        execution_disclosure=disclosure,
        warnings=relevant_warnings,
    )


def _matching_predictor_row(
    rows: list[ComputationalPredictorRow],
    aliases: tuple[str, ...],
) -> tuple[int | None, ComputationalPredictorRow | None]:
    normalized_aliases = {_predictor_id(alias) for alias in aliases}
    for index, row in enumerate(rows):
        if _predictor_id(row.name) in normalized_aliases:
            return index, row
    return None, None


def _predictor_warnings(
    predictor_id: str,
    warnings: list[str],
    row: ComputationalPredictorRow | None,
) -> list[str]:
    tokens = {
        predictor_id.replace("-", ""),
        predictor_id.replace("-", "_"),
    }
    values = [*warnings, *(row.warnings if row is not None else [])]
    selected = [
        _warning_code(value)
        for value in values
        if any(token in _source_key(value) for token in tokens)
    ]
    return _dedupe(selected)


def _predictor_requirement(spec: _PredictorSpec, warnings: list[str]) -> str:
    if spec.predictor_id == "alphamissense" and any(
        "missing_source_file" in warning or "missing_manifest" in warning for warning in warnings
    ):
        return "Mount the AlphaMissense source file with an immutable manifest."
    return spec.missing_requirement


def _missense_applicability(payload: ReportPayload) -> bool | None:
    row = payload.variant_summary_rows[0] if payload.variant_summary_rows else None
    if row is None:
        return None
    text = f"{row.consequence or ''} {row.variation_type or ''}".lower()
    if "missense" in text:
        return True
    if any(
        token in text
        for token in (
            "deletion",
            "duplication",
            "frameshift",
            "inframe",
            "in-frame",
            "insertion",
            "splice",
            "stop",
            "synonymous",
        )
    ):
        return False
    return None


def _source_snapshot_id(
    *,
    canonical: CanonicalVariantRefV1,
    evidence: list[EvidenceSourceSummary],
    evidence_statuses: dict[str, str],
) -> str:
    material = {
        "variant_key": canonical.variant_key,
        "sources": sorted(
            {
                (
                    _source_key(item.source),
                    _normalized_status(item.status),
                    item.source_version or _source_version(item) or "unversioned",
                )
                for item in evidence
            }
            | {
                (_source_key(source), _normalized_status(status), "unversioned")
                for source, status in evidence_statuses.items()
                if not any(_source_key(item.source) == _source_key(source) for item in evidence)
            }
        ),
    }
    return f"rs~{_digest(material)[:24]}"


def _source_version(item: EvidenceSourceSummary) -> str | None:
    if item.source_version and item.source_version.strip():
        return _safe_version(item.source_version)
    for key in ("source_version", "version", "dataset", "release"):
        value = item.summary.get(key)
        if isinstance(value, str) and value.strip():
            return _safe_version(value)
    return None


def _safe_version(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+~: -]{0,127}", text):
        return text
    return f"sv~{sha256(text.encode()).hexdigest()[:24]}"


def _source_requirement(source: str, status: str) -> str:
    category = _status_category(status)
    if category == "failed":
        return f"Restore the {source} source and repeat the identity-bound lookup."
    if _normalized_status(status) in {"fixture", "fallback", "degraded", "live_stub"}:
        return f"Replace the {source} fixture or fallback with identity-bound source evidence."
    return f"Provide identity-bound {source} evidence for this report section."


def _status_category(value: str | None) -> Literal["current", "stale", "failed", "unavailable"]:
    category = report_source_category(value)
    if category in {"current", "stale", "failed"}:
        return category
    return "unavailable"


def _normalized_status(value: str | None) -> str:
    return normalize_report_source_status(value)


def _source_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _predictor_id(value: str) -> str:
    compact = re.sub(r"[^a-z0-9]+", "", value.strip().lower())
    aliases = {
        "alphamissense": "alphamissense",
        "capice": "capice",
        "cispliceai": "ci-spliceai",
        "esm1b": "esm1b",
        "esm1bllr": "esm1b",
        "primateai": "primateai-3d",
        "primateai3d": "primateai-3d",
        "revel": "revel",
        "spliceai": "spliceai",
    }
    return aliases.get(compact, _opaque_id(compact or "unknown"))


def _warning_code(value: str) -> str:
    head = str(value or "warning").split(":", 1)[0]
    code = re.sub(r"[^A-Za-z0-9._~-]+", "_", head).strip("_.-")
    return (code or "warning")[:128]


def _opaque_id(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._~-]+", "_", value).strip("_.-~")
    return (text or "unknown")[:128]


def _identity_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip().lower().removeprefix("chr")


def _looks_variant_specific(value: str) -> bool:
    normalized = _identity_text(value)
    return bool(
        re.search(r"(?:^|[:(])(?:c|g|n|m|r|p)\.", normalized)
        or normalized.startswith("nc_")
        or re.fullmatch(r"(?:[0-9]{1,2}|x|y|mt)-\d+-[acgtn]+-[acgtn]+", normalized)
        or re.fullmatch(r"rs\d+", normalized)
    )


def _identity_value_contradicts_expected(value: str, expected: set[str]) -> bool:
    normalized = _identity_text(value)
    if not _looks_variant_specific(normalized):
        return False
    value_kind = _identity_value_kind(normalized)
    return any(_identity_value_kind(item) == value_kind for item in expected)


def _identity_value_kind(value: str) -> str:
    normalized = _identity_text(value)
    if re.fullmatch(r"rs\d+", normalized):
        return "rsid"
    if re.search(r"(?:^|[:(])p\.", normalized):
        return "protein"
    if re.search(r"(?:^|[:(])c\.", normalized):
        return "cdna"
    if (
        re.search(r"(?:^|[:(])(?:g|n|m|r)\.", normalized)
        or normalized.startswith("nc_")
        or re.fullmatch(r"(?:[0-9]{1,2}|x|y|mt)-\d+-[acgtn]+-[acgtn]+", normalized)
    ):
        return "genomic"
    return "variant"


def _first_text(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return sha256(encoded).hexdigest()


def _dedupe(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text[:512])
        if len(result) == 32:
            break
    return result
