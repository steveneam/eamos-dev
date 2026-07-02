from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.schemas.run import (
    EvidenceSourceSummary,
    FunctionalEvidenceSummary,
    ReportPayload,
    VariantSummaryRow,
)
from app.services.acmg_points_engine import compute_report_acmg_classification
from app.services.clinvar_local import ClinVarLocalError
from app.services.lookup_service_cache import (
    GENE_CONTEXT_SNAPSHOT_CACHE_VERSION,
    cached_functional_evidence_is_current,
    gene_context_snapshot_cache_is_current,
)
from app.services.lookup_service_clinvar_distribution import (
    clinvar_gene_distribution_exclusion_warning,
    local_clinvar_gene_distribution,
)
from app.services.lookup_service_publications_trials import (
    build_lookup_publication_literature,
    build_publications_callout,
    build_therapeutic_landscape,
    merge_litvar_articles,
    pubmed_articles_from_evidence_map,
)
from app.services.report_call_cards import (
    build_population_frequency_detail,
    build_variant_report_call_cards,
)
from app.services.report_data_currency import (
    build_report_data_currency,
    build_source_version_pins,
    current_report_timestamp,
)
from app.services.variant_decoder import decode_variant
from app.tools.base import ToolResult

TimingStart = Callable[[], float]
RecordPhase = Callable[..., None]
SourceCachedResult = Callable[[str, Callable[[], ToolResult]], ToolResult]
RecordResult = Callable[[str, ToolResult], None]


@dataclass(frozen=True)
class LookupReportPayloadAssembly:
    payload: ReportPayload
    litvar_summary: dict[str, Any]
    total_publications: int
    rebuild_functional_evidence_cache: bool
    gene_context_snapshot_cache: dict[str, Any] | None
    rebuild_gene_context_snapshot_cache: bool


def acmg_classification_snapshot(gene: str, cdna: str, clinvar: dict[str, Any]) -> str:
    classification = clinvar.get("classification", "Unavailable")
    review_status_text = clinvar.get("review_status", "review status unavailable")
    return (
        f"ClinVar currently lists {gene} {cdna} as {classification} ({review_status_text}). "
        "This is a source snapshot only and should not be read as formal ACMG evidence-code "
        "assignment or a final laboratory classification."
    )


def build_lookup_report_payload(
    *,
    gene: str,
    cdna: str,
    protein_change: str | None,
    species: str,
    query_kind: str,
    input_resolution: Any,
    variant: Any,
    variant_row: VariantSummaryRow,
    variant_label: str,
    decision: Any,
    lookup_modules: dict[str, Any],
    evidence: list[EvidenceSourceSummary],
    evidence_map: dict[str, dict[str, Any]],
    evidence_raw: dict[str, Any],
    evidence_statuses: dict[str, str],
    warnings: list[str],
    publication_cache: dict[str, Any] | Any,
    cache_hit: dict[str, Any] | None,
    litvar_result: ToolResult,
    tool_registry: dict[str, Any],
    publication_literature: Any,
    functional_evidence: Any,
    clinical_consensus: Any,
    sequence_context: Any,
    gene_context_snapshot: Any,
    settings: Any,
    cached_report_source_results: dict[str, ToolResult],
    source_cached_result: SourceCachedResult,
    record_result: RecordResult,
    timing_start: TimingStart,
    record_phase: RecordPhase,
) -> LookupReportPayloadAssembly:
    phase_started = timing_start()
    therapeutic_landscape_result = build_therapeutic_landscape(
        gene=gene,
        variant=variant,
        evidence_map=evidence_map,
        tool_registry=tool_registry,
        cached_report_source_results=cached_report_source_results,
        source_cached_result=source_cached_result,
        record_result=record_result,
    )
    record_phase(
        "clinical_trials",
        phase_started,
        metadata={"tool_present": therapeutic_landscape_result.clinical_trials_tool_present},
    )

    pubmed_articles = pubmed_articles_from_evidence_map(evidence_map)
    clinvar = evidence_map.get("clinvar", {})
    classification = clinvar.get("classification", "Unavailable")
    acmg_classification = acmg_classification_snapshot(gene, cdna, clinvar)

    lines = list(decision.evidence_lines)
    degraded = sorted(
        n.upper()
        for n, status in evidence_statuses.items()
        if status in {"fallback", "degraded", "error", "failed"}
    )
    if degraded:
        lines.append(f"Source quality note: {', '.join(degraded)} evidence was not fully live.")
    expanded_evidence = "\n".join(line for line in lines if line).strip() or None

    consequence = evidence_map.get("vep", {}).get("most_severe_consequence", "")
    clinical_integration = (
        f'{variant_label}: {consequence or "consequence pending VEP annotation"}. '
        f"External classification: {classification}. "
        "Interpret in the context of the clinical phenotype and family history before drawing "
        "conclusions."
    )
    recommendations = (
        f"Confirm the reported variant {gene} {cdna} against the original sequencing data. "
        f"{decision.next_step} "
        "Seek specialist review before drawing clinical conclusions."
    )

    payload = ReportPayload(
        patient_id=f"lookup_{uuid4().hex[:8]}",
        case_label=None,
        report_title=f"{gene} {cdna}",
        source_filenames=[],
        patient_context=None,
        clinical_phenotype=None,
        ai_clinical_summary=decision.recommendation,
        variant_summary_rows=[variant_row],
        expanded_evidence=expanded_evidence,
        acmg_classification=acmg_classification,
        clinical_integration=clinical_integration,
        expected_symptoms=None,
        recommendations=recommendations,
        limitations=(
            "Variant lookup report presenting publicly available database information. "
            "No clinical recommendations are made. "
            "All data should be independently verified before clinical use."
        ),
        variant_decoder=decode_variant(
            gene=gene,
            transcript_hgvs=input_resolution.transcript_hgvs,
            protein_change=protein_change,
        ),
        therapeutic_landscape=therapeutic_landscape_result.text,
        pubmed_articles=pubmed_articles,
        **lookup_modules,
    )
    _attach_clinvar_gene_distribution(
        payload=payload,
        gene=gene,
        variant=variant,
        settings=settings,
        warnings=warnings,
    )

    litvar_summary = evidence_map.get("litvar2", {})
    phase_started = timing_start()
    literature = build_lookup_publication_literature(
        publication_literature=publication_literature,
        variant=variant,
        evidence_map=evidence_map,
        evidence_raw=evidence_raw,
        evidence_statuses=evidence_statuses,
        warnings=warnings,
    )
    if literature is not None:
        payload.publications_literature = literature
        payload.pubmed_articles = literature.articles
    else:
        payload.pubmed_articles = merge_litvar_articles(pubmed_articles, litvar_summary)
    record_phase("publication_literature", phase_started)

    cached_functional_evidence = (
        publication_cache.get("functional_evidence")
        if isinstance(publication_cache, dict)
        else None
    )
    rebuild_functional_evidence_cache = (
        isinstance(publication_cache, dict)
        and isinstance(cached_functional_evidence, dict)
        and not cached_functional_evidence_is_current(
            publication_cache,
            cached_functional_evidence,
        )
    )
    phase_started = timing_start()
    try:
        if isinstance(cached_functional_evidence, dict) and not rebuild_functional_evidence_cache:
            functional_summary = FunctionalEvidenceSummary.model_validate(
                cached_functional_evidence
            )
        else:
            functional_summary = functional_evidence.build_for_lookup(
                variant,
                evidence_map,
                evidence_raw=evidence_raw,
                source_statuses=evidence_statuses,
                allow_live=bool(settings is not None and settings.use_real_apis),
            )
        payload.functional_evidence = functional_summary
        warnings.extend(functional_summary.warnings)
    except Exception as exc:
        warnings.append(f"functional_evidence_failed:{type(exc).__name__}")
    record_phase(
        "functional_evidence",
        phase_started,
        metadata={
            "cached": isinstance(cached_functional_evidence, dict)
            and not rebuild_functional_evidence_cache
        },
    )

    phase_started = timing_start()
    try:
        consensus = clinical_consensus.build_for_lookup(
            variant,
            payload,
            evidence_map,
            evidence_raw=evidence_raw,
            source_statuses=evidence_statuses,
            allow_live=bool(settings is not None and settings.use_real_apis),
        )
        evidence_map["clinical_consensus"] = consensus.summary
        evidence_statuses["clinical_consensus"] = consensus.status
        warnings.extend(consensus.warnings)
    except Exception as exc:
        warnings.append(f"clinical_consensus_failed:{type(exc).__name__}")
    record_phase("clinical_consensus", phase_started)

    payload.publications_callout = build_publications_callout(
        payload=payload,
        litvar_summary=litvar_summary,
        gene=gene,
        cdna=cdna,
    )
    total_publications = payload.publications_callout.total_count

    gnomad_evidence = next((item for item in evidence if item.source == "gnomad"), None)
    gnomad_identity = dict(gnomad_evidence.request_identity) if gnomad_evidence else None
    if gnomad_identity is not None:
        if not gnomad_identity.get("variant_id"):
            gnomad_identity["variant_id"] = variant.genomic_hg38 or None
        if not gnomad_identity.get("dataset"):
            gnomad_identity["dataset"] = str(
                getattr(tool_registry.get("gnomad"), "DATASET", "gnomad_r4")
            )
    payload.population_frequency_detail = build_population_frequency_detail(
        evidence_map.get("gnomad", {}),
        source_status=evidence_statuses.get("gnomad", ""),
        source_url=gnomad_evidence.source_url if gnomad_evidence is not None else None,
        source_warnings=gnomad_evidence.warnings if gnomad_evidence is not None else None,
        source_identity=gnomad_identity,
    )
    payload.call_cards = build_variant_report_call_cards(payload, evidence_map, evidence_statuses)

    _hydrate_sequence_context(
        gene=gene,
        cdna=cdna,
        species=species,
        input_resolution=input_resolution,
        sequence_context=sequence_context,
        evidence_map=evidence_map,
        evidence_statuses=evidence_statuses,
        timing_start=timing_start,
        record_phase=record_phase,
    )
    gene_context_result = _hydrate_gene_context_snapshot(
        gene=gene,
        cdna=cdna,
        species=species,
        input_resolution=input_resolution,
        cache_hit=cache_hit,
        gene_context_snapshot=gene_context_snapshot,
        evidence_map=evidence_map,
        evidence_statuses=evidence_statuses,
        warnings=warnings,
        timing_start=timing_start,
        record_phase=record_phase,
    )
    if query_kind == "unknown":
        payload.limitations = (
            f"We could not parse '{cdna}' as cDNA, rsID, protein, or genomic HGVS. "
            "Check the variant syntax and retry."
        )

    return LookupReportPayloadAssembly(
        payload=payload,
        litvar_summary=litvar_summary,
        total_publications=total_publications,
        rebuild_functional_evidence_cache=rebuild_functional_evidence_cache,
        gene_context_snapshot_cache=gene_context_result.cache_payload,
        rebuild_gene_context_snapshot_cache=gene_context_result.rebuild_cache,
    )


def finalize_lookup_report_payload(
    *,
    payload: ReportPayload,
    gene: str,
    cdna: str,
    variant_label: str,
    decision: Any,
    input_resolution: Any,
    search_interpretation: Any,
    evidence: list[EvidenceSourceSummary],
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
    warnings: list[str],
    draft_render_service: Any,
    report_orchestrator: Any,
    timing_start: TimingStart,
    record_phase: RecordPhase,
) -> None:
    phase_started = timing_start()
    if draft_render_service is not None:
        draft_payload, draft_warnings = draft_render_service.render(
            case_title=f"{gene}:{cdna}",
            patient_context=None,
            clinical_phenotype=None,
            variant_summary=variant_label,
            decision=decision,
            evidence_statuses=evidence_statuses,
            warnings=[*warnings, *decision.warnings],
            base_payload=payload,
        )
        payload.ai_clinical_summary = draft_payload.ai_clinical_summary
        payload.expanded_evidence = draft_payload.expanded_evidence
        payload.clinical_integration = draft_payload.clinical_integration
        payload.recommendations = draft_payload.recommendations
        payload.limitations = draft_payload.limitations
        warnings.extend(draft_warnings)
    record_phase(
        "draft_render",
        phase_started,
        metadata={"enabled": draft_render_service is not None},
    )

    phase_started = timing_start()
    report_generated_at = current_report_timestamp()
    payload.report_generated_at = report_generated_at
    payload.report_data_currency = build_report_data_currency(
        evidence,
        evidence_map,
        generated_at=report_generated_at,
    )
    payload.source_versions = build_source_version_pins(payload.report_data_currency)
    payload.report_profile = report_orchestrator.build_profile(
        resolution=input_resolution,
        interpretation=search_interpretation,
        payload=payload,
        evidence=evidence,
        evidence_map=evidence_map,
        evidence_statuses=evidence_statuses,
    )
    record_phase("report_profile", phase_started)

    phase_started = timing_start()
    try:
        payload.eamos_computed_classification = compute_report_acmg_classification(
            payload,
            evidence_map,
            evidence_statuses,
        )
    except Exception as exc:
        warnings.append(f"eamos_computed_classification_failed:{type(exc).__name__}")
    record_phase("eamos_computed_classification", phase_started)


def _attach_clinvar_gene_distribution(
    *,
    payload: ReportPayload,
    gene: str,
    variant: Any,
    settings: Any,
    warnings: list[str],
) -> None:
    warning = clinvar_gene_distribution_exclusion_warning(settings)
    if warning:
        payload.curated_variants_distribution = None
        warnings.append(warning)
        return
    try:
        payload.curated_variants_distribution = local_clinvar_gene_distribution(
            gene,
            settings,
            variant_id=variant.genomic_hg38 or None,
        )
    except ClinVarLocalError as exc:
        payload.curated_variants_distribution = None
        warnings.append(f"clinvar_local_gene_distribution_failed:{exc.code}")


def _hydrate_sequence_context(
    *,
    gene: str,
    cdna: str,
    species: str,
    input_resolution: Any,
    sequence_context: Any,
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
    timing_start: TimingStart,
    record_phase: RecordPhase,
) -> None:
    phase_started = timing_start()
    result = sequence_context.resolve(
        gene=gene,
        cdna=cdna,
        transcript=input_resolution.resolver_transcript,
        species=species,
    )
    if result.context is not None:
        evidence_map["sequence_context"] = result.context.model_dump(mode="json")
        evidence_statuses["sequence_context"] = result.context.source
    elif result.warnings:
        evidence_map["sequence_context"] = {"warnings": list(result.warnings)}
        evidence_statuses["sequence_context"] = "missing"
    record_phase("sequence_context", phase_started)


@dataclass(frozen=True)
class _GeneContextSnapshotResult:
    cache_payload: dict[str, Any] | None
    rebuild_cache: bool


def _hydrate_gene_context_snapshot(
    *,
    gene: str,
    cdna: str,
    species: str,
    input_resolution: Any,
    cache_hit: dict[str, Any] | None,
    gene_context_snapshot: Any,
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
    warnings: list[str],
    timing_start: TimingStart,
    record_phase: RecordPhase,
) -> _GeneContextSnapshotResult:
    cached_gene_context = (
        (cache_hit or {}).get("gene_context_snapshot", {}) if isinstance(cache_hit, dict) else {}
    )
    if not (
        isinstance(cached_gene_context, dict)
        and gene_context_snapshot_cache_is_current(cached_gene_context)
    ):
        cached_gene_context = {}
    snapshot_payload = (
        cached_gene_context.get("snapshot") if isinstance(cached_gene_context, dict) else None
    )
    rebuild_cache = not isinstance(snapshot_payload, dict)

    phase_started = timing_start()
    if isinstance(snapshot_payload, dict):
        evidence_map["gene_context_snapshot"] = snapshot_payload
        evidence_statuses["gene_context_snapshot"] = str(
            snapshot_payload.get("source_status") or "cache"
        )
    else:
        snapshot_payload = None
        try:
            snapshot = gene_context_snapshot.build(
                gene=gene,
                cdna=cdna,
                transcript=input_resolution.resolver_transcript,
                species=species,
            )
            snapshot_payload = snapshot.model_dump(mode="json")
            evidence_map["gene_context_snapshot"] = snapshot_payload
            evidence_statuses["gene_context_snapshot"] = snapshot.source_status
        except Exception as exc:
            warnings.append(f"gene_context_snapshot_failed:{type(exc).__name__}")
    record_phase(
        "gene_context_snapshot",
        phase_started,
        metadata={"cached": isinstance(cached_gene_context, dict) and bool(cached_gene_context)},
    )

    return _GeneContextSnapshotResult(
        cache_payload=(
            {
                "gene_context_snapshot_cache_version": GENE_CONTEXT_SNAPSHOT_CACHE_VERSION,
                "snapshot": snapshot_payload,
            }
            if snapshot_payload is not None
            else None
        ),
        rebuild_cache=rebuild_cache,
    )
