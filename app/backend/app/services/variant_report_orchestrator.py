from __future__ import annotations

from typing import Any

from app.schemas.lookup import SearchInputInterpretation
from app.schemas.protein_annotation import ProteinDomainTrack
from app.schemas.run import (
    AcmgWorksheetCriterion,
    AcmgWorksheetLedger,
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
    ReportPayload,
    SourceProvenance,
    TherapiesTrialsSection,
    TrialMatch,
    VariantReportHeader,
    VariantReportProfile,
    VariantSummaryRow,
)
from app.services.population_frequency_section import build_population_frequency_section
from app.services.omim_cross_references import (
    legacy_condition_ids,
    validated_omim_cross_references,
)
from app.services.clinical_consensus import sanitize_acmg_rationale
from app.services.computational_calibration import calibration_field_values
from app.services.computational_evidence import (
    build_computational_evidence_decision,
    selection_accounting,
)
from app.services.report_data_currency import current_report_timestamp, latest_evidence_timestamp
from app.services.report_extraction_plan import ReportExtractionPlanBuilder
from app.services.report_provenance import (
    provenance_for_source,
    provenance_from_evidence,
    source_provenance_from_mapping,
)
from app.services.search_input_resolver import SearchInputResolution
from app.services.variant_report_helpers import (
    _associated_condition_publicly_usable,
    _chromosome,
    _chromosome_from_variant_validator,
    _classification_text,
    _clinical_consensus,
    _codon_change,
    _codon_change_from_sequence_context,
    _codon_change_from_vep,
    _dedupe_provenance,
    _dedupe_text,
    _dict_or_empty,
    _exon_from_coords,
    _exon_from_variant_validator,
    _exon_from_vep,
    _filter_provenance,
    _first_prefixed,
    _list_of_dicts,
    _molecular_context_provenance,
    _optional_bool,
    _optional_float,
    _optional_int,
    _optional_text,
    _protein_position,
    _protein_position_from_vep,
    _sequence_context_provenance,
    _strand_from_coords,
    _strand_from_sequence_context,
    _strand_from_vep,
    _string_list,
)
from app.services.variant_report_signals import _build_section_signals


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
        computational_decision = build_computational_evidence_decision(
            payload=payload,
            evidence_map=evidence_map,
            disease_mechanism=disease_mechanism,
            deep_dive=computational_deep_dive,
        )
        if computational_deep_dive is not None:
            computational_deep_dive = computational_deep_dive.model_copy(
                update={"selection_accounting": selection_accounting(computational_decision)}
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
            computational_decision=computational_decision,
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
        omim_cross_references, omim_warnings = validated_omim_cross_references(
            gene_disease.get("omim_cross_references")
        )
        warnings = _dedupe_text([*warnings, *omim_warnings])
        if not _optional_text(gene_disease.get("penetrance")):
            warnings = _dedupe_text([*warnings, "penetrance_not_source_backed"])
        return DiseaseMechanismSection(
            primary_condition=_optional_text(gene_disease.get("primary_condition")),
            disease_ids=_string_list(gene_disease.get("disease_ids")),
            omim_cross_references=omim_cross_references,
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

    condition = next(
        (
            item
            for item in payload.associated_conditions
            if _associated_condition_publicly_usable(item)
        ),
        None,
    )
    warnings: list[str] = []
    if condition is None:
        warnings.append("disease_sources_not_hydrated")
        return DiseaseMechanismSection(warnings=warnings)

    return DiseaseMechanismSection(
        primary_condition=condition.name,
        disease_ids=legacy_condition_ids(condition),
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
    rows = [
        row
        for row in (
            _computational_row_from_dict(item)
            for item in _list_of_dicts(computational.get("predictors"))
        )
        if row is not None
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
        if row is not None
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
        **calibration,
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
            provenance.append(source_provenance_from_mapping(item))
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
            provenance.append(source_provenance_from_mapping(item))
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
