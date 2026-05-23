from __future__ import annotations

from app.schemas.lookup import SearchInputInterpretation
from app.schemas.run import (
    ReportExtractionPlan,
    ReportExtractionSectionTarget,
    ReportMatchLevel,
)
from app.services.search_input_resolver import SearchInputResolution

VARIANT_LEVEL_SECTIONS = (
    "header",
    "population_frequency",
    "rna_splicing",
    "clinical_consensus",
    "interpretation_summary",
    "gene_context_snapshot",
    "molecular_context",
    "computational_deep_dive",
    "acmg_worksheet",
    "publications",
    "provenance",
)


class ReportExtractionPlanBuilder:
    """Build section gates from the interpreted search input."""

    def build(
        self,
        *,
        resolution: SearchInputResolution,
        interpretation: SearchInputInterpretation | None = None,
    ) -> ReportExtractionPlan:
        submitted_text = _submitted_text(resolution, interpretation)
        mode = interpretation.mode if interpretation is not None else "structured"
        has_variant_identity = _has_variant_identity(resolution, interpretation)
        canonical_identity = _canonical_identity(resolution)
        source_query_bundle = _source_query_bundle(resolution)
        section_targets = self._section_targets(
            resolution=resolution,
            has_variant_identity=has_variant_identity,
            source_query_bundle=source_query_bundle,
        )
        warnings: list[str] = []
        if not has_variant_identity:
            warnings.append(f"variant_identity_unavailable:{mode}")

        return ReportExtractionPlan(
            submitted_text=submitted_text,
            mode=mode,
            canonical_identity=canonical_identity,
            source_query_bundle=source_query_bundle,
            section_targets=section_targets,
            warnings=warnings,
            provenance=["search_input_interpreter", "eamos_search_input_resolver"],
        )

    def _section_targets(
        self,
        *,
        resolution: SearchInputResolution,
        has_variant_identity: bool,
        source_query_bundle: dict[str, str | list[str] | None],
    ) -> list[ReportExtractionSectionTarget]:
        match_level: ReportMatchLevel = "variant_level" if has_variant_identity else "unavailable"
        variant_terms = _as_list(source_query_bundle.get("publication_variant_terms"))
        targets = [
            ReportExtractionSectionTarget(
                section_id="header",
                match_level=match_level,
                required_sources=["variant_validator", "ensembl_vep", "clinvar"],
                query_terms=_identity_terms(resolution),
                warnings=[] if has_variant_identity else ["header_requires_variant_identity"],
            ),
            ReportExtractionSectionTarget(
                section_id="population_frequency",
                match_level=match_level,
                required_sources=["gnomad"],
                query_terms=[term for term in [resolution.genomic_hg38] if term],
                warnings=[] if has_variant_identity else ["population_frequency_requires_allele"],
            ),
            ReportExtractionSectionTarget(
                section_id="rna_splicing",
                match_level=match_level,
                required_sources=["spliceai"],
                query_terms=[term for term in [resolution.genomic_hg38] if term],
                warnings=[] if has_variant_identity else ["rna_splicing_requires_allele"],
            ),
            ReportExtractionSectionTarget(
                section_id="lab_functional",
                match_level=match_level,
                required_sources=["clingen", "clinvar", "pubmed"],
                query_terms=variant_terms,
                warnings=[] if has_variant_identity else ["functional_evidence_requires_allele"],
            ),
            ReportExtractionSectionTarget(
                section_id="clinical_consensus",
                match_level=match_level,
                required_sources=["clingen", "clinvar"],
                query_terms=_identity_terms(resolution),
                warnings=[] if has_variant_identity else ["clinical_consensus_requires_allele"],
            ),
            ReportExtractionSectionTarget(
                section_id="interpretation_summary",
                match_level=match_level,
                required_sources=["report_profile"],
                query_terms=_identity_terms(resolution),
                warnings=[] if has_variant_identity else ["summary_requires_report_facts"],
            ),
            ReportExtractionSectionTarget(
                section_id="disease_mechanism",
                match_level="gene_level" if resolution.gene else "unavailable",
                required_sources=["clingen_gene_disease", "medgen", "orphadata"],
                query_terms=[resolution.gene] if resolution.gene else [],
                warnings=[] if resolution.gene else ["disease_mechanism_requires_gene"],
            ),
            ReportExtractionSectionTarget(
                section_id="gene_context_snapshot",
                match_level=match_level,
                required_sources=["gene_viewer"],
                query_terms=_identity_terms(resolution),
                warnings=[] if has_variant_identity else ["gene_context_requires_variant_identity"],
            ),
            ReportExtractionSectionTarget(
                section_id="molecular_context",
                match_level=match_level,
                required_sources=["ensembl_vep", "sequence_context", "gnomad_constraint"],
                query_terms=_identity_terms(resolution),
                warnings=[] if has_variant_identity else ["molecular_context_requires_allele"],
            ),
            ReportExtractionSectionTarget(
                section_id="computational_deep_dive",
                match_level=match_level,
                required_sources=["spliceai", "dbnsfp_or_myvariant"],
                query_terms=_identity_terms(resolution),
                warnings=[] if has_variant_identity else ["computational_scores_require_allele"],
            ),
            ReportExtractionSectionTarget(
                section_id="acmg_worksheet",
                match_level=match_level,
                required_sources=["clingen", "clinvar"],
                query_terms=_identity_terms(resolution),
                warnings=[] if has_variant_identity else ["acmg_worksheet_requires_allele"],
            ),
            ReportExtractionSectionTarget(
                section_id="publications",
                match_level=match_level,
                required_sources=["pubmed", "litvar2", "clinvar"],
                query_terms=variant_terms,
                warnings=[] if has_variant_identity else ["publication_inventory_requires_allele"],
            ),
            ReportExtractionSectionTarget(
                section_id="therapies_trials",
                match_level="gene_level" if resolution.gene else "unavailable",
                required_sources=["clinical_trials_gov"],
                query_terms=_clinical_trials_terms(source_query_bundle),
                warnings=(
                    ["clinical_trials_gene_level_fallback"]
                    if resolution.gene
                    else ["clinical_trials_requires_gene_or_disease"]
                ),
            ),
            ReportExtractionSectionTarget(
                section_id="provenance",
                match_level=match_level,
                required_sources=["source_statuses"],
                query_terms=_identity_terms(resolution),
                warnings=(
                    [] if has_variant_identity else ["provenance_records_unavailable_sections"]
                ),
            ),
        ]
        return targets


def _submitted_text(
    resolution: SearchInputResolution,
    interpretation: SearchInputInterpretation | None,
) -> str:
    if interpretation is not None and interpretation.submitted_text:
        return interpretation.submitted_text
    if resolution.gene:
        return f"{resolution.gene}:{resolution.hgvs}"
    return resolution.hgvs


def _has_variant_identity(
    resolution: SearchInputResolution,
    interpretation: SearchInputInterpretation | None,
) -> bool:
    if interpretation is not None and interpretation.requires_confirmation:
        return False
    if resolution.kind not in {"cdna", "genomic", "rsid"}:
        return False
    return bool(resolution.hgvs)


def _canonical_identity(resolution: SearchInputResolution) -> dict[str, str]:
    identity = {
        "gene": resolution.gene,
        "cdna": resolution.hgvs if resolution.kind == "cdna" else "",
        "transcript": resolution.resolver_transcript or resolution.transcript or "",
        "transcript_hgvs": resolution.resolver_transcript_hgvs,
        "protein_change": resolution.protein_change or "",
        "genomic_hg38": resolution.genomic_hg38 or "",
        "genomic_hgvs": resolution.genomic_hgvs or "",
        "query_kind": resolution.kind,
    }
    if resolution.kind == "genomic":
        identity["genomic_input"] = resolution.hgvs
    if resolution.kind == "rsid":
        identity["rsid"] = resolution.hgvs
    return {key: value for key, value in identity.items() if value}


def _source_query_bundle(resolution: SearchInputResolution) -> dict[str, str | list[str] | None]:
    source_inputs = resolution.source_inputs
    literature_terms = list(source_inputs.literature_terms)
    variant_terms = [
        term
        for term in literature_terms
        if term and (term != resolution.gene or resolution.kind in {"genomic", "rsid"})
    ]
    if not variant_terms:
        variant_terms = _identity_terms(resolution)
    gene_fallback_terms = [resolution.gene] if resolution.gene else []
    return {
        "variant_validator": source_inputs.variant_validator,
        "ensembl_vep": source_inputs.ensembl_vep,
        "gnomad": source_inputs.gnomad,
        "spliceai": source_inputs.spliceai,
        "clinvar": source_inputs.clinvar,
        "publication_variant_terms": _dedupe(variant_terms),
        "publication_gene_fallback_terms": gene_fallback_terms,
        "clinical_trials_terms": _dedupe([*variant_terms, *gene_fallback_terms]),
    }


def _identity_terms(resolution: SearchInputResolution) -> list[str]:
    return _dedupe(
        [
            resolution.gene,
            resolution.hgvs,
            resolution.resolver_transcript_hgvs,
            resolution.protein_change,
            resolution.genomic_hg38,
            resolution.genomic_hgvs,
        ]
    )


def _clinical_trials_terms(bundle: dict[str, str | list[str] | None]) -> list[str]:
    return _dedupe(_as_list(bundle.get("clinical_trials_terms")))


def _as_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [item for item in value if isinstance(item, str) and item]


def _dedupe(items: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = (item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
