from __future__ import annotations

from typing import Any

from app.schemas.run import (
    AcmgWorksheetLedger,
    ComputationalDeepDiveSection,
    DiseaseMechanismSection,
    ExpertPanelSection,
    GeneContextSnapshot,
    InterpretationSummary,
    MolecularContextSection,
    PopulationFrequencyReportSection,
    ReportPayload,
    ReportSectionSignal,
    TherapiesTrialsSection,
)
from app.services.variant_report_helpers import _dedupe_text, _string_list

_READY_SOURCE_STATUSES = {"live", "local", "cache", "stale", "fixture", "fallback", "live_stub"}
_ERROR_SOURCE_STATUSES = {"error", "failed"}


def _build_section_signals(
    *,
    payload: ReportPayload,
    interpretation_summary: InterpretationSummary | None,
    disease_mechanism: DiseaseMechanismSection | None,
    gene_context_snapshot: GeneContextSnapshot | None,
    population_frequency: PopulationFrequencyReportSection | None,
    molecular_context: MolecularContextSection | None,
    computational_deep_dive: ComputationalDeepDiveSection | None,
    acmg_worksheet: AcmgWorksheetLedger | None,
    expert_panel: ExpertPanelSection | None,
    therapies_trials: TherapiesTrialsSection | None,
) -> list[ReportSectionSignal]:
    """Rank report sections for dashboard ordering and progressive disclosure."""

    signals = [
        _section_signal(
            section_id="interpretation_summary",
            label="Summary",
            priority=96,
            confidence=(
                0.82 if interpretation_summary and interpretation_summary.fact_refs else 0.45
            ),
            relevance="summary",
            source_strength="source_mixed",
            status="ready" if interpretation_summary else "empty",
            default_open=False,
            headline=interpretation_summary.text if interpretation_summary else None,
            data_notes=interpretation_summary.warnings if interpretation_summary else [],
            source_refs=interpretation_summary.fact_refs if interpretation_summary else [],
        ),
        _section_signal(
            section_id="expert_panel",
            label="Expert Panel",
            priority=94 if expert_panel else 42,
            confidence=0.96 if expert_panel else 0.2,
            relevance="exact_variant" if expert_panel else "summary",
            source_strength="expert_panel" if expert_panel else "unavailable",
            status="ready" if expert_panel else "empty",
            default_open=expert_panel is not None,
            headline=expert_panel.final_classification if expert_panel else None,
            data_notes=[],
            source_refs=["clingen"] if expert_panel else [],
        ),
        _section_signal(
            section_id="acmg_worksheet",
            label="Eamos ACMG",
            priority=90 if acmg_worksheet and acmg_worksheet.criteria else 54,
            confidence=0.78 if acmg_worksheet and acmg_worksheet.criteria else 0.35,
            relevance="exact_variant",
            source_strength="eamos_computed",
            status="ready" if acmg_worksheet and acmg_worksheet.criteria else "empty",
            default_open=bool(acmg_worksheet and acmg_worksheet.criteria),
            headline=acmg_worksheet.classification if acmg_worksheet else None,
            source_refs=["acmg_worksheet"],
        ),
        _section_signal(
            section_id="population_frequency",
            label="Population Frequency",
            priority=88 if _population_has_data(population_frequency) else 50,
            confidence=_source_confidence(
                population_frequency.source_status if population_frequency else "missing",
                has_data=_population_has_data(population_frequency),
            ),
            relevance="exact_variant",
            source_strength="primary_db" if population_frequency else "unavailable",
            status=_section_status(
                population_frequency.source_status if population_frequency else "missing",
                has_data=_population_has_data(population_frequency),
                warnings=population_frequency.warnings if population_frequency else [],
            ),
            default_open=_population_has_data(population_frequency),
            headline=_population_headline(population_frequency),
            data_notes=population_frequency.warnings if population_frequency else [],
            source_refs=["gnomad"] if population_frequency else [],
        ),
        _section_signal(
            section_id="computational_deep_dive",
            label="In Silico Predictors",
            priority=76 if _computational_has_data(computational_deep_dive) else 38,
            confidence=0.72 if _computational_has_data(computational_deep_dive) else 0.25,
            relevance="exact_variant",
            source_strength=(
                "primary_db" if _computational_has_data(computational_deep_dive) else "unavailable"
            ),
            status=_data_status(
                has_data=_computational_has_data(computational_deep_dive),
                warnings=computational_deep_dive.warnings if computational_deep_dive else [],
            ),
            default_open=_computational_has_data(computational_deep_dive),
            headline=_computational_headline(computational_deep_dive),
            data_notes=computational_deep_dive.warnings if computational_deep_dive else [],
            source_refs=["computational_annotations"],
        ),
        _section_signal(
            section_id="disease_mechanism",
            label="Gene Disease Context",
            priority=68 if disease_mechanism and disease_mechanism.primary_condition else 36,
            confidence=0.7 if disease_mechanism and disease_mechanism.primary_condition else 0.25,
            relevance="gene_disease",
            source_strength=(
                "curated"
                if disease_mechanism and disease_mechanism.primary_condition
                else "unavailable"
            ),
            status=_data_status(
                has_data=bool(disease_mechanism and disease_mechanism.primary_condition),
                warnings=disease_mechanism.warnings if disease_mechanism else [],
            ),
            default_open=bool(disease_mechanism and disease_mechanism.primary_condition),
            headline=disease_mechanism.primary_condition if disease_mechanism else None,
            data_notes=disease_mechanism.warnings if disease_mechanism else [],
            source_refs=["gene_disease"],
        ),
        _section_signal(
            section_id="gene_context_snapshot",
            label="Gene View",
            priority=64 if _gene_context_has_data(gene_context_snapshot) else 34,
            confidence=_source_confidence(
                gene_context_snapshot.source_status if gene_context_snapshot else "missing",
                has_data=_gene_context_has_data(gene_context_snapshot),
            ),
            relevance="transcript_locus",
            source_strength=(
                "curated" if _gene_context_has_data(gene_context_snapshot) else "unavailable"
            ),
            status=_section_status(
                gene_context_snapshot.source_status if gene_context_snapshot else "missing",
                has_data=_gene_context_has_data(gene_context_snapshot),
                warnings=gene_context_snapshot.warnings if gene_context_snapshot else [],
            ),
            default_open=_gene_context_has_data(gene_context_snapshot),
            headline=_gene_context_headline(gene_context_snapshot),
            data_notes=gene_context_snapshot.warnings if gene_context_snapshot else [],
            source_refs=["gene_context_snapshot"],
        ),
        _section_signal(
            section_id="molecular_context",
            label="Molecular Context",
            priority=58 if _molecular_has_data(molecular_context) else 32,
            confidence=0.64 if _molecular_has_data(molecular_context) else 0.25,
            relevance=(
                "protein_region"
                if molecular_context and molecular_context.domain
                else "transcript_locus"
            ),
            source_strength=(
                "source_mixed" if _molecular_has_data(molecular_context) else "unavailable"
            ),
            status=_data_status(
                has_data=_molecular_has_data(molecular_context),
                warnings=molecular_context.warnings if molecular_context else [],
            ),
            default_open=True,
            headline=molecular_context.domain if molecular_context else None,
            data_notes=molecular_context.warnings if molecular_context else [],
            source_refs=["molecular_context"],
        ),
        _section_signal(
            section_id="publications",
            label="Publications",
            priority=52 if _publications_has_data(payload) else 30,
            confidence=0.58 if _publications_has_data(payload) else 0.2,
            relevance="exact_variant" if _publications_has_data(payload) else "gene_discovery",
            source_strength="literature" if payload.publications_literature else "unavailable",
            status=_data_status(
                has_data=_publications_has_data(payload),
                warnings=(
                    payload.publications_literature.warnings
                    if payload.publications_literature
                    else []
                ),
            ),
            default_open=True,
            headline=_publications_headline(payload),
            data_notes=(
                payload.publications_literature.warnings if payload.publications_literature else []
            ),
            source_refs=["publications"],
        ),
        _section_signal(
            section_id="therapies_trials",
            label="Trials and Therapies",
            priority=46 if therapies_trials and therapies_trials.trial_rows else 28,
            confidence=0.42 if therapies_trials and therapies_trials.trial_rows else 0.18,
            relevance=_trials_relevance(therapies_trials),
            source_strength=(
                "primary_db" if therapies_trials and therapies_trials.trial_rows else "unavailable"
            ),
            status=_data_status(
                has_data=bool(therapies_trials and therapies_trials.trial_rows),
                warnings=therapies_trials.warnings if therapies_trials else [],
            ),
            default_open=True,
            headline=_trials_headline(therapies_trials),
            data_notes=therapies_trials.warnings if therapies_trials else [],
            source_refs=["clinical_trials"],
        ),
    ]
    return sorted(signals, key=lambda signal: (-signal.priority, signal.section_id))


def _section_signal(**kwargs: Any) -> ReportSectionSignal:
    data_notes = _dedupe_text(_string_list(kwargs.get("data_notes")))
    source_refs = _dedupe_text(_string_list(kwargs.get("source_refs")))
    return ReportSectionSignal(
        **{
            **kwargs,
            "data_notes": data_notes[:6],
            "source_refs": source_refs,
        }
    )


def _section_status(status: str, *, has_data: bool, warnings: list[str]) -> str:
    if status in _ERROR_SOURCE_STATUSES:
        return "error"
    if has_data and warnings:
        return "limited"
    if has_data:
        return "ready"
    if status in _READY_SOURCE_STATUSES or warnings:
        return "limited"
    return "empty"


def _data_status(*, has_data: bool, warnings: list[str]) -> str:
    if has_data and warnings:
        return "limited"
    if has_data:
        return "ready"
    if warnings:
        return "limited"
    return "empty"


def _source_confidence(status: str, *, has_data: bool) -> float:
    if not has_data:
        return 0.2
    if status in {"live", "local"}:
        return 0.88
    if status in {"cache", "fixture"}:
        return 0.74
    if status in {"stale", "fallback", "live_stub"}:
        return 0.52
    return 0.35


def _population_has_data(section: PopulationFrequencyReportSection | None) -> bool:
    return bool(section and (section.visual_groups or section.source_rows or section.overall))


def _population_headline(section: PopulationFrequencyReportSection | None) -> str | None:
    if not section:
        return None
    if section.unavailable_reason:
        return section.unavailable_reason
    if section.visual_scale and section.visual_scale.max_group_id:
        return f"Popmax group: {section.visual_scale.max_group_id}"
    return section.dataset or None


def _computational_has_data(section: ComputationalDeepDiveSection | None) -> bool:
    return bool(
        section
        and (section.predictors or section.conservation or section.spliceai_max_delta is not None)
    )


def _computational_headline(section: ComputationalDeepDiveSection | None) -> str | None:
    if not section:
        return None
    calibrated = [
        row
        for row in section.predictors
        if row.calibrated_label or row.calibration_bucket or row.score is not None
    ]
    if calibrated:
        return f"{len(calibrated)} predictor signal(s)"
    if section.spliceai_max_delta is not None:
        return f"SpliceAI max delta {section.spliceai_max_delta:g}"
    return None


def _gene_context_has_data(section: GeneContextSnapshot | None) -> bool:
    return bool(section and (section.exons or section.variant or section.zoom_segments))


def _gene_context_headline(section: GeneContextSnapshot | None) -> str | None:
    if not section:
        return None
    if section.transcript:
        return section.transcript
    return section.gene or None


def _molecular_has_data(section: MolecularContextSection | None) -> bool:
    return bool(
        section
        and (
            section.chromosome
            or section.exon
            or section.protein_position
            or section.domain
            or section.loeuf is not None
            or section.clingen_haploinsufficiency
        )
    )


def _publications_has_data(payload: ReportPayload) -> bool:
    return bool(payload.publications_literature and payload.publications_literature.total_count > 0)


def _publications_headline(payload: ReportPayload) -> str | None:
    literature = payload.publications_literature
    if literature is None:
        return None
    return f"{literature.total_count} publication(s)"


def _trials_relevance(section: TherapiesTrialsSection | None) -> str:
    if not section or not section.trial_rows:
        return "disease_discovery"
    levels = {row.match_level for row in section.trial_rows}
    if "variant_level" in levels:
        return "exact_variant"
    if "gene_level" in levels:
        return "gene_discovery"
    return "disease_discovery"


def _trials_headline(section: TherapiesTrialsSection | None) -> str | None:
    if not section or not section.trial_rows:
        return None
    return f"{len(section.trial_rows)} registry row(s)"
