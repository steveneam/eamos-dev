from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    completed = "completed"
    degraded = "degraded"
    blocked = "blocked"


class ReviewStatus(str, Enum):
    pending_review = "pending_review"
    reviewed = "reviewed"
    approved = "approved"
    dropped = "dropped"


class RunRequest(BaseModel):
    patient_id: str = Field(min_length=1)
    report_ids: list[str] = Field(min_length=1)


class EvidenceSourceSummary(BaseModel):
    source: str
    status: str
    request_identity: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    source_url: str | None = None


class VariantSummaryRow(BaseModel):
    gene: str | None = None
    transcript_hgvs: str | None = None
    protein_change: str | None = None
    genomic_hg38: str | None = None
    variation_type: str | None = None
    consequence: str | None = None


class PubMedArticle(BaseModel):
    pmid: str
    title: str
    authors: str
    journal: str
    year: str
    url: str
    abstract: str | None = None


ClassificationTier = Literal["pathogenic", "likely_pathogenic", "vus", "likely_benign", "benign"]
AcmgVerdict = Literal["met", "not_met", "not_assessed"]
PredictorVerdict = Literal["damaging", "tolerated", "uncertain"]


class NearbyVariant(BaseModel):
    cds_pos: int
    classification: ClassificationTier
    hgvs: str
    clinvar_id: str | None = None
    protein_change: str | None = None


class CodonCell(BaseModel):
    codon_number: int
    aa_ref: str
    aa_alt: str | None = None
    dna_ref: str = ""
    dna_alt: str | None = None
    is_query: bool = False


class LocusContext(BaseModel):
    """Region viewer payload for the report."""

    gene: str
    centre_cdna: str
    coords: str = ""
    nearby_variants: list[NearbyVariant] = Field(default_factory=list)
    codon_strip: list[CodonCell] = Field(default_factory=list)


class PredictorCard(BaseModel):
    """One card in the in-silico prediction grid."""

    name: Literal["REVEL", "AlphaMissense", "MetaLR", "SpliceAI"]
    score: float
    threshold: float
    verdict: PredictorVerdict
    verdict_label: str = ""
    source_url: str | None = None


class InSilicoPredictions(BaseModel):
    cards: list[PredictorCard] = Field(default_factory=list)
    consensus_note: str


class AcmgCriterion(BaseModel):
    code: Literal[
        "PVS1",
        "PS1", "PS2", "PS3", "PS4",
        "PM1", "PM2", "PM3", "PM4", "PM5", "PM6",
        "PP1", "PP2", "PP3", "PP4", "PP5",
        "BA1",
        "BS1", "BS2", "BS3", "BS4",
        "BP1", "BP2", "BP3", "BP4", "BP5", "BP6", "BP7",
    ]
    verdict: AcmgVerdict
    note: str | None = None


class AcmgCriteriaScaffold(BaseModel):
    criteria: list[AcmgCriterion] = Field(default_factory=list)
    intro: str = ""
    note: str = ""
    disclaimer: str = "Supporting evidence, not classification."


class CuratedVariantsDistribution(BaseModel):
    """3 by 4 heat matrix, flattened into keyed cells."""

    cells: dict[str, int] = Field(default_factory=dict)
    row_totals: dict[str, int] = Field(default_factory=dict)
    total: int
    subtitle: str = ""
    reading: str


class AssociatedCondition(BaseModel):
    name: str
    case_count: int
    evidence_level: Literal["definitive", "strong", "moderate", "limited"]
    inheritance: Literal["AR", "AD", "XL", "MT"]
    source: str
    db_tag: str = ""
    db_tag_bold: str | None = None
    source_list: str = ""


class PublicationsCallout(BaseModel):
    total_count: int
    scholar_url: str
    blurb: str = ""
    ai_summary_prompt: str


class ReportPayload(BaseModel):
    patient_id: str
    case_label: str | None = None
    report_title: str | None = None
    source_filenames: list[str] = Field(default_factory=list)
    patient_context: str | None = None
    clinical_phenotype: str | None = None
    ai_clinical_summary: str | None = None
    variant_summary_rows: list[VariantSummaryRow] = Field(default_factory=list)
    expanded_evidence: str | None = None
    acmg_classification: str | None = None
    clinical_integration: str | None = None
    expected_symptoms: str | None = None
    recommendations: str | None = None
    limitations: str | None = None
    variant_decoder: str | None = None
    therapeutic_landscape: str | None = None
    pubmed_articles: list[PubMedArticle] = Field(default_factory=list)
    ai_generated_sections: list[str] = Field(default_factory=list)
    locus_context: LocusContext | None = None
    in_silico_predictions: InSilicoPredictions | None = None
    acmg_criteria_scaffold: AcmgCriteriaScaffold | None = None
    curated_variants_distribution: CuratedVariantsDistribution | None = None
    associated_conditions: list[AssociatedCondition] = Field(default_factory=list)
    publications_callout: PublicationsCallout | None = None


class RunResponse(BaseModel):
    run_id: str
    patient_id: str
    report_ids: list[str]
    run_status: RunStatus
    review_status: ReviewStatus
    report_payload: ReportPayload
    evidence: list[EvidenceSourceSummary] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    review_note: str | None = None
    reviewed_at: datetime | None = None
    approved_pdf_path: str | None = None
