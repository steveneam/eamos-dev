from __future__ import annotations

from typing import Any

from app.schemas.lookup import SearchInputInterpretation
from app.schemas.protein_annotation import ProteinDomainTrack
from app.schemas.run import (
    AcmgWorksheetCriterion,
    AcmgWorksheetLedger,
    ClinicalTrialQueryExecution,
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
from app.services.computational_evidence import (
    build_computational_evidence_decision,
    selection_accounting,
)
from app.services.lovd_fixture_adapter import validated_lovd_basic_records
from app.services.report_data_currency import current_report_timestamp, latest_evidence_timestamp
from app.services.report_execution_truth import report_identity_mismatched_sources
from app.services.report_extraction_plan import ReportExtractionPlanBuilder
from app.services.report_provenance import (
    provenance_for_source,
    provenance_from_evidence,
    source_provenance_from_mapping,
)
from app.services.report_source_truth import (
    normalize_report_source_status,
    report_source_allows_payload,
    report_source_is_weak,
)
from app.services.search_input_resolver import SearchInputResolution
from app.services.variant_report_helpers import (
    _associated_condition_publicly_usable,
    _chromosome,
    _chromosome_from_variant_validator,
    _classification_text,
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
from app.services.variant_report_computational import (
    _computational_deep_dive_from_annotations as _computational_deep_dive_from_annotations,
    build_computational_deep_dive as _build_computational_deep_dive,
)
from app.services.variant_report_signals import _build_section_signals


def _usable_source_summary(
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
    source: str,
) -> dict[str, Any]:
    if not report_source_allows_payload(evidence_statuses.get(source, "missing")):
        return {}
    return _dict_or_empty(evidence_map.get(source))


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
        mismatched_sources = report_identity_mismatched_sources(
            resolution=resolution,
            evidence=evidence,
        )
        if mismatched_sources:
            evidence_statuses = dict(evidence_statuses)
            for source in mismatched_sources:
                evidence_statuses[source] = "fallback"
            if mismatched_sources & {"clingen", "clinvar"}:
                evidence_statuses["clinical_consensus"] = "fallback"
            evidence = [
                (
                    item.model_copy(
                        update={
                            "status": "fallback",
                            "warnings": _dedupe_text(
                                [*item.warnings, "report_source_identity_mismatch"]
                            ),
                        }
                    )
                    if item.source.strip().casefold() in mismatched_sources
                    else item
                )
                for item in evidence
            ]
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
            evidence_statuses=evidence_statuses,
        )
        interpretation_summary = _build_summary(payload, evidence_map, evidence_statuses)
        disease_mechanism = _build_disease_mechanism(
            payload=payload,
            evidence_map=evidence_map,
            evidence_statuses=evidence_statuses,
        )
        gene_context_snapshot = _build_gene_context_snapshot(
            evidence_map,
            evidence_statuses,
        )
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
        acmg_worksheet = _build_acmg_worksheet(payload, evidence_map, evidence_statuses)
        expert_panel = _build_expert_panel(evidence, evidence_map, evidence_statuses)
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
            lovd_basic_records=validated_lovd_basic_records(
                evidence_map.get("lovd_fixture")
                if report_source_allows_payload(evidence_statuses.get("lovd_fixture", "missing"))
                else None
            ),
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
    evidence_statuses: dict[str, str],
) -> VariantReportHeader:
    row = _first_variant_row(payload)
    consensus = _usable_source_summary(
        evidence_map,
        evidence_statuses,
        "clinical_consensus",
    )
    clinvar = _usable_source_summary(evidence_map, evidence_statuses, "clinvar")
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
    source_urls = [
        item.source_url
        for item in evidence
        if item.source_url and report_source_allows_payload(item.status)
    ]
    badges = []
    if resolution.resolver_transcript:
        badges.append("transcript_resolved")
    if row.genomic_hg38 or resolution.genomic_hg38:
        badges.append("grch38_resolved")
    if classification:
        badges.append("clinical_consensus_available")
    gene_context = _usable_source_summary(
        evidence_map,
        evidence_statuses,
        "gene_context_snapshot",
    )
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
    evidence_statuses: dict[str, str],
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

    clinvar = _usable_source_summary(evidence_map, evidence_statuses, "clinvar")
    consensus = _usable_source_summary(
        evidence_map,
        evidence_statuses,
        "clinical_consensus",
    )
    classification = _classification_text(consensus.get("classification")) or _classification_text(
        clinvar.get("classification")
    )
    if classification:
        classification_source = _optional_text(consensus.get("classification_source")) or "ClinVar"
        facts.append(f"{classification_source} classification: {classification}")
        refs.append("clinical_consensus")

    population = (
        payload.population_frequency_detail
        if report_source_allows_payload(evidence_statuses.get("gnomad", "missing"))
        else None
    )
    if population is not None and population.allele_frequency is not None:
        facts.append(f"gnomAD allele frequency: {population.allele_frequency:g}")
        refs.append("population_frequency")

    publication_source_available = any(
        report_source_allows_payload(evidence_statuses.get(source, "missing"))
        for source in ("pubmed", "litvar2", "clinvar", "clingen")
    )
    if (
        publication_source_available
        and payload.publications_literature is not None
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
    gene_disease_status = evidence_statuses.get("gene_disease", "missing")
    gene_disease = _usable_source_summary(
        evidence_map,
        evidence_statuses,
        "gene_disease",
    )
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
                status=gene_disease_status,
            ),
            warnings=warnings,
        )

    fixture_mode = normalize_report_source_status(gene_disease_status) == "fixture"
    condition = (
        next(
            (
                item
                for item in payload.associated_conditions
                if _associated_condition_publicly_usable(item)
            ),
            None,
        )
        if fixture_mode
        else None
    )
    warnings: list[str] = []
    if condition is None:
        if report_source_is_weak(gene_disease_status) and evidence_map.get("gene_disease"):
            warnings.append("gene_disease_source_unavailable")
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
    evidence_statuses: dict[str, str],
) -> GeneContextSnapshot | None:
    raw_snapshot = evidence_map.get("gene_context_snapshot")
    if not raw_snapshot:
        return None
    try:
        snapshot = GeneContextSnapshot.model_validate(raw_snapshot)
    except Exception:
        return None
    source_status = evidence_statuses.get(
        "gene_context_snapshot",
        snapshot.source_status,
    )
    if report_source_allows_payload(source_status):
        return snapshot
    return GeneContextSnapshot(
        source_status=normalize_report_source_status(source_status),  # type: ignore[arg-type]
        gene=snapshot.gene,
        transcript=snapshot.transcript,
        warnings=_dedupe_text([*snapshot.warnings, "gene_context_snapshot_source_unavailable"]),
    )


def _build_molecular_context(
    *,
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
    provenance: list[SourceProvenance],
) -> MolecularContextSection:
    row = _first_variant_row(payload)
    context_source_available = report_source_allows_payload(
        evidence_statuses.get("sequence_context", "missing")
    )
    context = payload.locus_context if context_source_available else None
    vep = _usable_source_summary(evidence_map, evidence_statuses, "vep")
    variant_validator = _usable_source_summary(
        evidence_map,
        evidence_statuses,
        "variant_validator",
    )
    sequence_context = _usable_source_summary(
        evidence_map,
        evidence_statuses,
        "sequence_context",
    )
    molecular_context = _usable_source_summary(
        evidence_map,
        evidence_statuses,
        "molecular_context",
    )
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
    protein_domain_track = _protein_domain_track_from_evidence(
        evidence_map,
        evidence_statuses,
    )
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
    evidence_statuses: dict[str, str],
) -> ProteinDomainTrack | None:
    raw_track = (
        evidence_map.get("protein_domain_track")
        if report_source_allows_payload(evidence_statuses.get("protein_domain_track", "missing"))
        else None
    )
    raw_snapshot = _usable_source_summary(
        evidence_map,
        evidence_statuses,
        "gene_context_snapshot",
    )
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


def _build_acmg_worksheet(
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
) -> AcmgWorksheetLedger:
    scaffold = payload.acmg_criteria_scaffold
    consensus = _usable_source_summary(
        evidence_map,
        evidence_statuses,
        "clinical_consensus",
    )
    consensus_worksheet = consensus.get("acmg_worksheet")
    if isinstance(consensus_worksheet, dict):
        try:
            return AcmgWorksheetLedger.model_validate(consensus_worksheet)
        except Exception:
            pass
    clinvar = _usable_source_summary(evidence_map, evidence_statuses, "clinvar")
    classification = _classification_text(clinvar.get("classification"))
    fixture_mode = any(
        normalize_report_source_status(evidence_statuses.get(source)) == "fixture"
        for source in ("clinical_consensus", "clinvar", "clingen")
    )
    if scaffold is None or not fixture_mode:
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
    evidence_statuses: dict[str, str],
) -> ExpertPanelSection | None:
    clingen_status = evidence_statuses.get("clingen", "missing")
    if not report_source_allows_payload(clingen_status):
        return None
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
    if evidence.status in {"live", "local", "cache"}:
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
    if report_source_is_weak(source_status):
        return TherapiesTrialsSection(
            warnings=_dedupe_text([*warnings, "clinical_trials_source_unavailable"]),
            provenance=[
                provenance_for_source(
                    "ClinicalTrials.gov",
                    status=source_status,
                    warnings=_dedupe_text([*warnings, "clinical_trials_source_unavailable"]),
                )
            ],
        )
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
