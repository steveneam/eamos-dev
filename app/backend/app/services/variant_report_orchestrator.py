from __future__ import annotations

import re
from typing import Any

from app.schemas.lookup import SearchInputInterpretation
from app.schemas.protein_annotation import ProteinDomainTrack
from app.schemas.run import (
    AcmgWorksheetCriterion,
    AcmgWorksheetLedger,
    AssociatedCondition,
    ClinicalTrialQueryExecution,
    ComputationalDeepDiveSection,
    ComputationalPredictorRow,
    DiseaseMechanismSection,
    EvidenceIdentityMatch,
    EvidenceSourceSummary,
    ExpertPanelSection,
    GeneContextSnapshot,
    InterpretationSummary,
    MolecularContextSection,
    PopulationFrequencyReportSection,
    ReportPayload,
    ReportSectionSignal,
    SourceProvenance,
    TherapiesTrialsSection,
    TrialMatch,
    VariantReportHeader,
    VariantReportProfile,
    VariantSummaryRow,
)
from app.services.population_frequency_section import build_population_frequency_section
from app.services.clinical_consensus import sanitize_acmg_rationale
from app.services.computational_calibration import calibration_field_values
from app.services.report_data_currency import current_report_timestamp, latest_evidence_timestamp
from app.services.report_extraction_plan import ReportExtractionPlanBuilder
from app.services.report_provenance import provenance_for_source, provenance_from_evidence
from app.services.search_input_resolver import SearchInputResolution


class VariantReportDataOrchestrator:
    """Assemble the typed Variant Evidence Report profile from fetched facts."""

    def __init__(self, plan_builder: ReportExtractionPlanBuilder | None = None) -> None:
        self.plan_builder = plan_builder or ReportExtractionPlanBuilder()

    def build_profile(
        self,
        *,
        resolution: SearchInputResolution,
        interpretation: SearchInputInterpretation | None,
        payload: ReportPayload,
        evidence: list[EvidenceSourceSummary],
        evidence_map: dict[str, dict[str, Any]],
        evidence_statuses: dict[str, str],
    ) -> VariantReportProfile:
        plan = self.plan_builder.build(
            resolution=resolution,
            interpretation=interpretation,
        )
        provenance = provenance_from_evidence(evidence)
        header = _build_header(
            resolution=resolution,
            payload=payload,
            evidence_map=evidence_map,
            evidence=evidence,
        )
        interpretation_summary = _build_summary(payload, evidence_map)
        disease_mechanism = _build_disease_mechanism(
            payload=payload,
            evidence_map=evidence_map,
            evidence_statuses=evidence_statuses,
        )
        gene_context_snapshot = _build_gene_context_snapshot(evidence_map)
        population_frequency = build_population_frequency_section(
            payload.population_frequency_detail,
            source_status=evidence_statuses.get("gnomad", "missing"),
            gnomad_summary=evidence_map.get("gnomad"),
        )
        molecular_context = _build_molecular_context(
            payload=payload,
            evidence_map=evidence_map,
            evidence_statuses=evidence_statuses,
            provenance=provenance,
        )
        computational_deep_dive = _build_computational_deep_dive(
            payload=payload,
            evidence_map=evidence_map,
            evidence_statuses=evidence_statuses,
            provenance=provenance,
        )
        acmg_worksheet = _build_acmg_worksheet(payload, evidence_map)
        expert_panel = _build_expert_panel(evidence, evidence_map)
        therapies_trials = _build_therapies_trials(
            payload=payload,
            evidence_map=evidence_map,
            evidence_statuses=evidence_statuses,
        )
        return VariantReportProfile(
            extraction_plan=plan,
            header=header,
            interpretation_summary=interpretation_summary,
            disease_mechanism=disease_mechanism,
            gene_context_snapshot=gene_context_snapshot,
            population_frequency=population_frequency,
            molecular_context=molecular_context,
            computational_deep_dive=computational_deep_dive,
            acmg_worksheet=acmg_worksheet,
            expert_panel=expert_panel,
            therapies_trials=therapies_trials,
            section_signals=_build_section_signals(
                payload=payload,
                interpretation_summary=interpretation_summary,
                disease_mechanism=disease_mechanism,
                gene_context_snapshot=gene_context_snapshot,
                population_frequency=population_frequency,
                molecular_context=molecular_context,
                computational_deep_dive=computational_deep_dive,
                acmg_worksheet=acmg_worksheet,
                expert_panel=expert_panel,
                therapies_trials=therapies_trials,
            ),
            provenance=provenance,
        )


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


def _build_header(
    *,
    resolution: SearchInputResolution,
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
    evidence: list[EvidenceSourceSummary],
) -> VariantReportHeader:
    row = _first_variant_row(payload)
    consensus = _clinical_consensus(evidence_map)
    clinvar = evidence_map.get("clinvar", {})
    classification = _classification_text(consensus.get("classification")) or _classification_text(
        clinvar.get("classification")
    )
    classification_source = _optional_text(consensus.get("classification_source")) or (
        "ClinVar" if classification else None
    )
    display_cdna = resolution.hgvs if resolution.kind == "cdna" else row.transcript_hgvs
    display_name = " ".join(
        item
        for item in [
            resolution.gene or row.gene,
            display_cdna,
            resolution.protein_change or row.protein_change,
        ]
        if item
    )
    source_urls = [item.source_url for item in evidence if item.source_url]
    badges = []
    if resolution.resolver_transcript:
        badges.append("transcript_resolved")
    if row.genomic_hg38 or resolution.genomic_hg38:
        badges.append("grch38_resolved")
    if classification:
        badges.append("clinical_consensus_available")
    gene_context = _dict_or_empty(evidence_map.get("gene_context_snapshot"))
    transcript_aliases = _string_list(gene_context.get("transcript_aliases"))
    ensembl_transcript = _first_prefixed(transcript_aliases, "ENST")
    mane_select = any(alias.strip().lower() == "mane select" for alias in transcript_aliases)

    return VariantReportHeader(
        display_name=display_name or payload.report_title or "Variant Evidence Report",
        gene=resolution.gene or row.gene or "",
        transcript=resolution.resolver_transcript or resolution.transcript,
        cdna=display_cdna,
        protein_change=resolution.protein_change or row.protein_change,
        genomic_hg38=row.genomic_hg38 or resolution.genomic_hg38,
        dbsnp_rsid=_optional_text(clinvar.get("dbsnp_rsid")),
        ensembl_gene_id=_optional_text(gene_context.get("ensembl_gene_id")),
        ensembl_transcript=ensembl_transcript,
        transcript_aliases=transcript_aliases,
        mane_select=mane_select if transcript_aliases else None,
        updated_at=latest_evidence_timestamp(evidence, evidence_map)
        or payload.report_generated_at
        or current_report_timestamp(),
        classification=classification,
        classification_source=classification_source,
        verification_badges=badges,
        source_urls=source_urls,
    )


def _build_summary(
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
) -> InterpretationSummary:
    row = _first_variant_row(payload)
    facts: list[str] = []
    refs: list[str] = []
    variant_label = " ".join(
        item for item in [row.gene, row.transcript_hgvs, row.protein_change] if item
    )
    if variant_label:
        facts.append(variant_label)
        refs.append("header")

    clinvar = evidence_map.get("clinvar", {})
    consensus = _clinical_consensus(evidence_map)
    classification = _classification_text(consensus.get("classification")) or _classification_text(
        clinvar.get("classification")
    )
    if classification:
        classification_source = _optional_text(consensus.get("classification_source")) or "ClinVar"
        facts.append(f"{classification_source} classification: {classification}")
        refs.append("clinical_consensus")

    population = payload.population_frequency_detail
    if population is not None and population.allele_frequency is not None:
        facts.append(f"gnomAD allele frequency: {population.allele_frequency:g}")
        refs.append("population_frequency")

    if (
        payload.publications_literature is not None
        and payload.publications_literature.total_count > 0
    ):
        facts.append(f"{payload.publications_literature.total_count} publication(s) identified")
        refs.append("publications")

    if not facts:
        return InterpretationSummary(
            mode="unavailable",
            text="No source-backed report facts are available for an interpretation summary.",
            warnings=["summary_fact_bundle_empty"],
        )

    return InterpretationSummary(
        mode="deterministic",
        text="; ".join(facts) + ".",
        fact_refs=refs,
    )


def _build_disease_mechanism(
    *,
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
) -> DiseaseMechanismSection:
    gene_disease = evidence_map.get("gene_disease", {})
    if gene_disease:
        warnings = _string_list(gene_disease.get("warnings"))
        if not _optional_text(gene_disease.get("penetrance")):
            warnings = _dedupe_text([*warnings, "penetrance_not_source_backed"])
        return DiseaseMechanismSection(
            primary_condition=_optional_text(gene_disease.get("primary_condition")),
            disease_ids=_string_list(gene_disease.get("disease_ids")),
            inheritance=_optional_text(gene_disease.get("inheritance")),
            penetrance=_optional_text(gene_disease.get("penetrance")),
            gene_disease_validity=_optional_text(gene_disease.get("gene_disease_validity")),
            mechanism=_optional_text(gene_disease.get("mechanism")),
            provenance=_gene_disease_provenance(
                gene_disease,
                status=evidence_statuses.get("gene_disease", "missing"),
            ),
            warnings=warnings,
        )

    condition = payload.associated_conditions[0] if payload.associated_conditions else None
    warnings: list[str] = []
    if condition is None:
        warnings.append("disease_sources_not_hydrated")
        return DiseaseMechanismSection(warnings=warnings)

    return DiseaseMechanismSection(
        primary_condition=condition.name,
        disease_ids=_condition_ids(condition),
        inheritance=condition.inheritance,
        penetrance=None,
        gene_disease_validity=condition.evidence_level,
        mechanism=None,
        provenance=[
            provenance_for_source(
                "associated_conditions_fixture",
                status="fixture",
                query={"condition": condition.name, "source": condition.source},
            )
        ],
        warnings=[
            "gene_disease_source_unavailable",
            "associated_conditions_legacy_fallback",
            "penetrance_not_source_backed",
            "mechanism_source_not_hydrated",
        ],
    )


def _build_gene_context_snapshot(
    evidence_map: dict[str, dict[str, Any]],
) -> GeneContextSnapshot | None:
    raw_snapshot = evidence_map.get("gene_context_snapshot")
    if not raw_snapshot:
        return None
    return GeneContextSnapshot.model_validate(raw_snapshot)


def _build_molecular_context(
    *,
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
    provenance: list[SourceProvenance],
) -> MolecularContextSection:
    row = _first_variant_row(payload)
    context = payload.locus_context
    vep = evidence_map.get("vep", {})
    variant_validator = evidence_map.get("variant_validator", {})
    sequence_context = evidence_map.get("sequence_context", {})
    molecular_context = evidence_map.get("molecular_context", {})
    coords = context.coords if context is not None else ""
    query_codon = (
        next(
            (cell for cell in context.codon_strip if cell.is_query),
            None,
        )
        if context is not None
        else None
    )
    warnings: list[str] = []
    if not row.genomic_hg38:
        warnings.append("genomic_coordinate_unavailable")
    if context is None:
        warnings.append("locus_context_unavailable")
    warnings.extend(_string_list(sequence_context.get("warnings")))
    warnings.extend(_string_list(molecular_context.get("warnings")))

    gnomad_constraint = _dict_or_empty(molecular_context.get("gnomad_constraint"))
    clingen_dosage = _dict_or_empty(molecular_context.get("clingen_dosage"))
    loeuf = _optional_float(gnomad_constraint.get("loeuf"))
    haploinsufficiency = _optional_text(clingen_dosage.get("haploinsufficiency"))
    overlapping_cnvs = _string_list(molecular_context.get("overlapping_cnvs"))
    protein_position = _protein_position_from_vep(vep) or _protein_position(row.protein_change)
    protein_domain_track = _protein_domain_track_from_evidence(evidence_map)
    protein_domain_label = _protein_domain_label_at_position(
        protein_domain_track,
        protein_position,
    )

    if loeuf is None:
        warnings.append("constraint_source_not_hydrated")
    if haploinsufficiency is None:
        warnings.append("clingen_dosage_source_not_hydrated")
    if not overlapping_cnvs:
        warnings.append("structural_cnv_overlap_source_not_hydrated")
    if protein_domain_label is None:
        warnings.append("protein_domain_source_not_hydrated")
    warnings.append("hotspot_source_not_hydrated")

    return MolecularContextSection(
        chromosome=_chromosome(row.genomic_hg38)
        or _chromosome_from_variant_validator(variant_validator),
        strand=_strand_from_sequence_context(sequence_context)
        or _strand_from_vep(vep)
        or _strand_from_coords(coords),
        exon=_exon_from_variant_validator(variant_validator)
        or _exon_from_vep(vep)
        or _exon_from_coords(coords),
        codon_change=_codon_change_from_sequence_context(sequence_context)
        or _codon_change(query_codon)
        or _codon_change_from_vep(vep),
        protein_position=protein_position,
        domain=protein_domain_label,
        hotspot_flag=None,
        loeuf=loeuf,
        clingen_haploinsufficiency=haploinsufficiency,
        overlapping_cnvs=overlapping_cnvs,
        protein_domain_track=protein_domain_track,
        provenance=_dedupe_provenance(
            [
                *_filter_provenance(provenance, {"vep", "variant_validator", "gnomad"}),
                *_sequence_context_provenance(sequence_context),
                *_molecular_context_provenance(
                    molecular_context,
                    status=evidence_statuses.get("molecular_context", "missing"),
                ),
            ]
        ),
        warnings=_dedupe_text(warnings),
    )


def _protein_domain_track_from_evidence(
    evidence_map: dict[str, dict[str, Any]],
) -> ProteinDomainTrack | None:
    raw_track = evidence_map.get("protein_domain_track")
    raw_snapshot = evidence_map.get("gene_context_snapshot")
    if raw_track is None and isinstance(raw_snapshot, dict):
        raw_track = raw_snapshot.get("protein_domain_track")
    if not isinstance(raw_track, dict):
        return None
    try:
        return ProteinDomainTrack.model_validate(raw_track)
    except Exception:
        return None


def _protein_domain_label_at_position(
    track: ProteinDomainTrack | None,
    protein_position: str | None,
) -> str | None:
    if track is None or track.status not in {"available", "cache_hit"}:
        return None
    position = _optional_int(protein_position)
    if position is None:
        return None
    feature = next(
        (
            item
            for item in track.features
            if item.aa_start <= position <= item.aa_end
            and item.kind in {"domain", "family", "motif", "repeat", "region", "site"}
        ),
        None,
    )
    if feature is None:
        return None
    return feature.short_label or feature.label


def _build_computational_deep_dive(
    *,
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
    provenance: list[SourceProvenance],
) -> ComputationalDeepDiveSection:
    computational = evidence_map.get("computational_annotations", {})
    if computational:
        section = _computational_deep_dive_from_annotations(
            computational,
            status=evidence_statuses.get("computational_annotations", "missing"),
            provenance=provenance,
        )
        if section is not None:
            return section

    return _computational_deep_dive_from_legacy_predictions(payload, provenance)


def _computational_deep_dive_from_legacy_predictions(
    payload: ReportPayload,
    provenance: list[SourceProvenance],
) -> ComputationalDeepDiveSection:
    predictions = payload.in_silico_predictions
    rows: list[ComputationalPredictorRow] = []
    spliceai_max_delta: float | None = None
    spliceai_consequence: str | None = None
    if predictions is not None:
        for card in predictions.cards:
            rows.append(
                ComputationalPredictorRow(
                    name=card.name,
                    score=card.score,
                    threshold=card.threshold,
                    interpretation=card.verdict_label or card.verdict,
                    source=card.name,
                    source_url=card.source_url,
                    **calibration_field_values(card.name, card.score),
                )
            )
            if card.name == "SpliceAI":
                spliceai_max_delta = card.score
                spliceai_consequence = card.verdict_label or card.verdict

    warnings = []
    if not rows:
        warnings.append("computational_predictors_unavailable")
    return ComputationalDeepDiveSection(
        predictors=rows,
        spliceai_max_delta=spliceai_max_delta,
        spliceai_consequence=spliceai_consequence,
        conservation=[],
        provenance=_filter_provenance(provenance, {"spliceai", "vep"}),
        warnings=warnings,
    )


def _computational_deep_dive_from_annotations(
    computational: dict[str, Any],
    *,
    status: str,
    provenance: list[SourceProvenance],
) -> ComputationalDeepDiveSection | None:
    excluded = set(_string_list(computational.get("excluded_predictors")))
    excluded.discard("AlphaMissense")
    rows = [
        row
        for row in (
            _computational_row_from_dict(item)
            for item in _list_of_dicts(computational.get("predictors"))
        )
        if row is not None and row.name not in excluded
    ]

    spliceai = _dict_or_empty(computational.get("spliceai"))
    spliceai_max_delta = _optional_float(spliceai.get("max_delta"))
    spliceai_consequence = _optional_text(spliceai.get("consequence"))
    spliceai_row = _spliceai_row(spliceai)
    if spliceai_row is not None and spliceai_row.name not in {row.name for row in rows}:
        rows.append(spliceai_row)

    conservation = [
        row
        for row in (
            _computational_row_from_dict(item)
            for item in _list_of_dicts(computational.get("conservation"))
        )
        if row is not None and row.name not in excluded
    ]
    warnings = _dedupe_text(
        [
            *_string_list(computational.get("warnings")),
        ]
    )
    if not rows and not conservation and spliceai_max_delta is None:
        warnings.append("computational_predictors_unavailable")
        if not computational.get("predictors") and not computational.get("spliceai"):
            return None

    return ComputationalDeepDiveSection(
        predictors=rows,
        spliceai_max_delta=spliceai_max_delta,
        spliceai_consequence=spliceai_consequence,
        conservation=conservation,
        provenance=_dedupe_provenance(
            [
                *_filter_provenance(provenance, {"computational_annotations", "spliceai"}),
                *_computational_annotations_provenance(computational, status=status),
            ]
        ),
        warnings=_dedupe_text(warnings),
    )


def _computational_row_from_dict(item: dict[str, Any]) -> ComputationalPredictorRow | None:
    name = _optional_text(item.get("name"))
    if not name:
        return None
    score = _score_value(item.get("score"))
    source = _optional_text(item.get("source")) or name
    calibration = calibration_field_values(name, score)
    return ComputationalPredictorRow(
        name=name,
        score=score,
        threshold=_score_value(item.get("threshold")),
        interpretation=_optional_text(item.get("interpretation")),
        source=source,
        source_id=_optional_text(item.get("source_id")),
        version=_optional_text(item.get("version")),
        calibrated_label=_optional_text(item.get("calibrated_label"))
        or calibration["calibrated_label"],
        calibration_bucket=_optional_text(item.get("calibration_bucket"))
        or calibration["calibration_bucket"],
        calibration_method=_optional_text(item.get("calibration_method"))
        or calibration["calibration_method"],
        calibration_version=_optional_text(item.get("calibration_version"))
        or calibration["calibration_version"],
        source_url=_optional_text(item.get("source_url")),
        public_serialization_allowed=_optional_bool(item.get("public_serialization_allowed")),
        launch_gate=_optional_text(item.get("launch_gate")),
        warnings=_string_list(item.get("warnings")),
    )


def _spliceai_row(spliceai: dict[str, Any]) -> ComputationalPredictorRow | None:
    if not spliceai:
        return None
    max_delta = _optional_float(spliceai.get("max_delta"))
    component_scores = _dict_or_empty(spliceai.get("component_scores"))
    if max_delta is None and not component_scores:
        return None
    consequence = _optional_text(spliceai.get("consequence"))
    component_text = _spliceai_component_text(component_scores)
    interpretation_parts = []
    if consequence:
        interpretation_parts.append(f"Max delta consequence: {consequence}.")
    if component_text:
        interpretation_parts.append(f"Component scores: {component_text}.")
    return ComputationalPredictorRow(
        name="SpliceAI",
        score=max_delta,
        threshold=_score_value(spliceai.get("threshold")),
        interpretation=" ".join(interpretation_parts) or None,
        source=_optional_text(spliceai.get("source")) or "SpliceAI",
        version=_optional_text(spliceai.get("version")),
        **calibration_field_values("SpliceAI", max_delta),
        source_url=_optional_text(spliceai.get("source_url")),
        warnings=_string_list(spliceai.get("warnings")),
    )


def _spliceai_component_text(component_scores: dict[str, Any]) -> str:
    components: list[str] = []
    for key in ("DS_AL", "DS_DL", "DS_AG", "DS_DG"):
        score = _optional_float(component_scores.get(key))
        if score is not None:
            components.append(f"{key}={score:g}")
    return ", ".join(components)


def _score_value(value: Any) -> str | float | None:
    numeric = _optional_float(value)
    if numeric is not None:
        return numeric
    return _optional_text(value)


def _computational_annotations_provenance(
    summary: dict[str, Any],
    *,
    status: str,
) -> list[SourceProvenance]:
    raw = summary.get("provenance")
    provenance: list[SourceProvenance] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                provenance.append(SourceProvenance.model_validate(item))
            except Exception:
                continue
    if provenance:
        return provenance
    gene = _optional_text(summary.get("gene"))
    return [
        provenance_for_source(
            "computational_annotations",
            status=status,
            query={"gene": gene} if gene else {},
            warnings=_string_list(summary.get("warnings")),
        )
    ]


def _build_acmg_worksheet(
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
) -> AcmgWorksheetLedger:
    scaffold = payload.acmg_criteria_scaffold
    consensus = _clinical_consensus(evidence_map)
    consensus_worksheet = consensus.get("acmg_worksheet")
    if isinstance(consensus_worksheet, dict):
        return AcmgWorksheetLedger.model_validate(consensus_worksheet)
    clinvar = evidence_map.get("clinvar", {})
    classification = _classification_text(clinvar.get("classification"))
    if scaffold is None:
        return AcmgWorksheetLedger(
            classification=classification,
            classification_source="ClinVar" if classification else None,
            criteria=[],
            synthesis=None,
        )

    criteria = [
        AcmgWorksheetCriterion(
            code=item.code,
            state=item.verdict,
            assertion_level="not_assessed" if item.verdict == "not_assessed" else "eamos_hint",
            rationale=sanitize_acmg_rationale(item.note),
            source="Eamos worksheet scaffold" if item.verdict != "not_assessed" else None,
            evidence_refs=[item.code] if item.note else [],
        )
        for item in scaffold.criteria
    ]
    return AcmgWorksheetLedger(
        classification=classification,
        classification_source="ClinVar" if classification else None,
        criteria=criteria,
        synthesis=scaffold.note or None,
        disclaimer=scaffold.disclaimer,
    )


def _build_expert_panel(
    evidence: list[EvidenceSourceSummary],
    evidence_map: dict[str, dict[str, Any]],
) -> ExpertPanelSection | None:
    clingen = _dict_or_empty(evidence_map.get("clingen"))
    raw_panel = clingen.get("expert_panel")
    if not isinstance(raw_panel, dict):
        return None

    try:
        panel = ExpertPanelSection.model_validate(raw_panel)
    except Exception:
        return None

    clingen_evidence = _first_source_evidence(evidence, "clingen")
    freshness, freshness_reason = _expert_panel_freshness(clingen_evidence)
    provenance = panel.provenance
    identity_match = provenance.identity_match
    if clingen_evidence is not None:
        if identity_match is None:
            identity_match = _evidence_identity_match(clingen_evidence)
        provenance = provenance.model_copy(
            update={
                "fetched_at": clingen_evidence.fetched_at or provenance.fetched_at,
                "source_version": clingen_evidence.source_version or provenance.source_version,
                "source_url": clingen_evidence.source_url or provenance.source_url,
                "identity_match": identity_match,
            }
        )
    if not _identity_auto_attach_allowed(identity_match):
        return None
    return panel.model_copy(
        update={
            "provenance": provenance,
            "freshness": freshness,
            "freshness_reason": freshness_reason,
        }
    )


def _identity_auto_attach_allowed(identity_match: EvidenceIdentityMatch | None) -> bool:
    return bool(identity_match and identity_match.auto_attach_allowed)


def _expert_panel_freshness(
    evidence: EvidenceSourceSummary | None,
) -> tuple[str, str | None]:
    if evidence is None:
        return "unknown", "tile_only"
    if evidence.cache_status == "stale_on_failure" or evidence.status == "stale":
        return "stale", "stale_on_failure"
    if evidence.cache_status == "cache_hit":
        return "fresh", "cache_hit"
    if evidence.status in {"live", "local", "fixture", "cache"}:
        return "fresh", None
    return "unknown", "tile_only"


def _evidence_identity_match(evidence: EvidenceSourceSummary) -> EvidenceIdentityMatch | None:
    raw = evidence.summary.get("identity_match")
    if not isinstance(raw, dict):
        return None
    try:
        return EvidenceIdentityMatch.model_validate(raw)
    except Exception:
        return None


def _first_source_evidence(
    evidence: list[EvidenceSourceSummary],
    source: str,
) -> EvidenceSourceSummary | None:
    for item in evidence:
        if item.source == source:
            return item
    return None


def _build_therapies_trials(
    *,
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
) -> TherapiesTrialsSection:
    status = "fixture" if payload.therapeutic_landscape else "missing"
    source_status = evidence_statuses.get("clinical_trials", status)
    clinical_trials = _dict_or_empty(evidence_map.get("clinical_trials"))
    warnings = _string_list(clinical_trials.get("warnings"))
    source_fetched_at = _optional_text(clinical_trials.get("fetched_at"))
    trial_rows: list[TrialMatch] = []
    for item in _list_of_dicts(clinical_trials.get("trial_rows")):
        try:
            row_payload = dict(item)
            if source_fetched_at and not _optional_text(row_payload.get("fetched_at")):
                row_payload["fetched_at"] = source_fetched_at
            trial_rows.append(TrialMatch.model_validate(row_payload))
        except Exception:
            warnings.append("clinical_trials_row_validation_failed")
    query_executions: list[ClinicalTrialQueryExecution] = []
    for item in _list_of_dicts(clinical_trials.get("query_executions")):
        try:
            query_executions.append(ClinicalTrialQueryExecution.model_validate(item))
        except Exception:
            warnings.append("clinical_trials_query_execution_validation_failed")

    if trial_rows:
        if any(row.match_level in {"gene_level", "disease_level"} for row in trial_rows):
            warnings.append("clinical_trials_gene_level_target_only")
    elif source_status in {"fixture", "missing"}:
        warnings.append("clinical_trials_structured_rows_unavailable")

    query_term = _optional_text(clinical_trials.get("query_term"))
    source_url = _optional_text(clinical_trials.get("source_url"))
    return TherapiesTrialsSection(
        trial_rows=trial_rows,
        query_executions=query_executions,
        warnings=_dedupe_text(warnings),
        provenance=[
            provenance_for_source(
                "ClinicalTrials.gov",
                status=source_status,
                query={"query": query_term} if query_term else {},
                source_url=source_url,
                warnings=_dedupe_text(warnings),
            )
        ],
    )


def _first_variant_row(payload: ReportPayload) -> VariantSummaryRow:
    if payload.variant_summary_rows:
        return payload.variant_summary_rows[0]
    return VariantSummaryRow()


def _condition_ids(condition: AssociatedCondition) -> list[str]:
    candidates = [condition.source, condition.db_tag, condition.source_list]
    ids: list[str] = []
    for text in candidates:
        if not text:
            continue
        ids.extend(re.findall(r"(OMIM\s*#?\d+|ORPHA:\d+|MONDO:\d+)", text, flags=re.I))
    seen: set[str] = set()
    result: list[str] = []
    for item in ids:
        normalized = item.replace(" ", "").replace("#", "#")
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(item)
    return result


def _gene_disease_provenance(
    summary: dict[str, Any],
    *,
    status: str,
) -> list[SourceProvenance]:
    raw = summary.get("provenance")
    provenance: list[SourceProvenance] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                provenance.append(SourceProvenance.model_validate(item))
            except Exception:
                continue
    if provenance:
        return provenance
    gene = _optional_text(summary.get("approved_symbol") or summary.get("gene"))
    return [
        provenance_for_source(
            "gene_disease",
            status=status,
            query={"gene": gene} if gene else {},
            warnings=_string_list(summary.get("warnings")),
        )
    ]


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [text for text in (_optional_text(item) for item in value) if text]
    text = _optional_text(value)
    return [text] if text else []


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _dedupe_text(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = item.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _first_prefixed(items: list[str], prefix: str) -> str | None:
    prefix_upper = prefix.upper()
    return next((item for item in items if item.upper().startswith(prefix_upper)), None)


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    match = re.search(r"\d+", text)
    if match is None:
        return None
    return int(match.group(0))


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _chromosome(genomic_hg38: str | None) -> str | None:
    if not genomic_hg38 or "-" not in genomic_hg38:
        return None
    return genomic_hg38.split("-", 1)[0]


def _chromosome_from_variant_validator(summary: dict[str, Any]) -> str | None:
    vcf = _dict_or_empty(summary.get("vcf"))
    return _optional_text(vcf.get("chr"))


def _strand_from_sequence_context(summary: dict[str, Any]) -> str | None:
    strand = _optional_text(summary.get("strand"))
    return strand if strand in {"+", "-"} else None


def _strand_from_vep(summary: dict[str, Any]) -> str | None:
    strand = summary.get("strand")
    if strand in {"+", "-"}:
        return strand
    if strand in {1, "1", "+1"}:
        return "+"
    if strand in {-1, "-1"}:
        return "-"
    return None


def _strand_from_coords(coords: str) -> str | None:
    if "(+)" in coords:
        return "+"
    if "(-)" in coords:
        return "-"
    return None


def _exon_from_variant_validator(summary: dict[str, Any]) -> str | None:
    return _optional_text(summary.get("exon"))


def _exon_from_vep(summary: dict[str, Any]) -> str | None:
    exon = _optional_text(summary.get("exon"))
    if exon and "/" in exon:
        return exon.split("/", 1)[0]
    return exon


def _exon_from_coords(coords: str) -> str | None:
    match = re.search(r"\bexon\s+(\d+)\b", coords, flags=re.I)
    if match is None:
        return None
    return match.group(1)


def _codon_change(query_codon) -> str | None:
    if query_codon is None:
        return None
    if not query_codon.aa_alt:
        return f"{query_codon.aa_ref}{query_codon.codon_number}"
    return f"{query_codon.aa_ref}{query_codon.codon_number}{query_codon.aa_alt}"


def _codon_change_from_sequence_context(summary: dict[str, Any]) -> str | None:
    ref = _optional_text(summary.get("codon_ref"))
    alt = _optional_text(summary.get("codon_alt"))
    if ref and alt:
        return f"{ref}>{alt}"
    number = _optional_text(summary.get("codon_number"))
    return f"codon {number}" if number else None


def _codon_change_from_vep(summary: dict[str, Any]) -> str | None:
    codons = _optional_text(summary.get("codons"))
    if not codons:
        return None
    parts = [part.upper() for part in re.split(r"[/|]", codons) if part]
    if len(parts) >= 2:
        return f"{parts[0]}>{parts[1]}"
    return codons


def _protein_position_from_vep(summary: dict[str, Any]) -> str | None:
    return _optional_text(summary.get("protein_position"))


def _protein_position(protein_change: str | None) -> str | None:
    if not protein_change:
        return None
    match = re.search(r"(\d+)", protein_change)
    return match.group(1) if match else None


def _filter_provenance(
    provenance: list[SourceProvenance],
    sources: set[str],
) -> list[SourceProvenance]:
    return [item for item in provenance if item.source in sources]


def _sequence_context_provenance(summary: dict[str, Any]) -> list[SourceProvenance]:
    if not summary:
        return []
    source = _optional_text(summary.get("source"))
    status = "fixture" if source == "fixture" else "live" if source == "resolver" else "missing"
    metadata = _dict_or_empty(summary.get("source_metadata"))
    query = {
        "gene": summary.get("gene"),
        "cdna": summary.get("cdna"),
        "transcript": summary.get("transcript"),
        "genomic_hg38": summary.get("genomic_hg38"),
    }
    source_url = _optional_text(
        metadata.get("ensembl_sequence_url") or metadata.get("variant_validator_url")
    )
    version = _optional_text(metadata.get("fixture") or metadata.get("coordinate_source"))
    return [
        provenance_for_source(
            "sequence_context",
            status=status,
            query=query,
            source_url=source_url,
            version=version,
            warnings=_string_list(summary.get("warnings")),
        )
    ]


def _molecular_context_provenance(
    summary: dict[str, Any],
    *,
    status: str,
) -> list[SourceProvenance]:
    raw = summary.get("provenance")
    provenance: list[SourceProvenance] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                provenance.append(SourceProvenance.model_validate(item))
            except Exception:
                continue
    if provenance:
        return provenance
    gene = _optional_text(summary.get("gene"))
    return [
        provenance_for_source(
            "molecular_context",
            status=status,
            query={"gene": gene} if gene else {},
            warnings=_string_list(summary.get("warnings")),
        )
    ]


def _dedupe_provenance(items: list[SourceProvenance]) -> list[SourceProvenance]:
    seen: set[tuple[str, str | None, str | None, tuple[tuple[str, str], ...]]] = set()
    result: list[SourceProvenance] = []
    for item in items:
        key = (
            item.source,
            item.source_url,
            item.version,
            tuple(sorted(item.query.items())),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _classification_text(value: Any) -> str | None:
    text = _optional_text(value)
    if text is None or text.lower() in {"unavailable", "not found", "none"}:
        return None
    return text


def _clinical_consensus(evidence_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    value = evidence_map.get("clinical_consensus")
    return value if isinstance(value, dict) else {}
