from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AlleleMode = Literal["reference", "variant"]
GenomeStrand = Literal["+", "-", "unknown"]
ViewerTrack = Literal[
    "sequence",
    "exons",
    "clinvar",
    "protein_features",
    "restriction",
    "conservation",
]
ViewerWindowKind = Literal["around_variant", "cds_range"]
ViewerSegmentKind = Literal["exon", "intron"]
VariantClassification = Literal[
    "pathogenic",
    "likely_pathogenic",
    "vus",
    "likely_benign",
    "benign",
    "unknown",
]


class ViewerWindowRequest(BaseModel):
    kind: ViewerWindowKind = "around_variant"
    cds_start: int | None = None
    cds_end: int | None = None
    cds_flank_bp: int = 120
    intron_flank_bp: int = 30


class GeneViewerRequest(BaseModel):
    gene: str
    cdna: str
    transcript: str | None = None
    species: str = "human"
    genome_build: str = "GRCh38"
    allele_mode: AlleleMode = "reference"
    window: ViewerWindowRequest = Field(default_factory=ViewerWindowRequest)
    tracks: list[ViewerTrack] = Field(
        default_factory=lambda: [
            "sequence",
            "exons",
            "clinvar",
            "protein_features",
            "restriction",
        ]
    )


class ViewerIdentity(BaseModel):
    gene: str
    ensembl_gene_id: str | None = None
    requested_transcript: str | None = None
    resolved_transcript: str
    transcript_aliases: list[str] = Field(default_factory=list)
    species: str = "human"
    genome_build: str = "GRCh38"


class ViewerLocus(BaseModel):
    chrom: str
    gene_start: int | None = None
    gene_end: int | None = None
    strand: GenomeStrand = "unknown"


class ViewerSummary(BaseModel):
    gene_length: int | None = None
    total_exons: int
    cds_length: int | None = None
    protein_length: int | None = None
    utr5_length: int | None = None
    utr3_length: int | None = None
    mrna_length: int | None = None


class ViewerWindow(BaseModel):
    kind: ViewerWindowKind
    cds_start: int | None = None
    cds_end: int | None = None
    cds_flank_bp: int
    intron_flank_bp: int
    display_cds_start: int
    display_cds_end: int
    total_display_bases: int


class ViewerSegment(BaseModel):
    id: str
    kind: ViewerSegmentKind
    label: str
    exon_number: int | None = None
    intron_number: int | None = None
    cds_start: int | None = None
    cds_end: int | None = None
    genomic_start: int | None = None
    genomic_end: int | None = None
    strand: GenomeStrand = "unknown"
    sequence: str = ""
    five_prime_sequence: str = ""
    three_prime_sequence: str = ""
    omitted_bp: int = 0


class QueriedVariant(BaseModel):
    hgvs_c: str
    hgvs_p: str | None = None
    cds_pos: int
    genomic_hg38: str | None = None
    ref: str
    alt: str
    codon_number: int | None = None
    codon_offset: int | None = None
    aa_ref: str | None = None
    aa_alt: str | None = None
    classification: VariantClassification = "unknown"


class AppliedVariant(BaseModel):
    hgvs_c: str
    cds_pos: int
    segment_id: str
    sequence_offset: int
    ref: str
    alt: str


class ViewerSequences(BaseModel):
    allele_mode: AlleleMode
    reference_window_sequence: str
    display_window_sequence: str
    applied_variant: AppliedVariant | None = None


class ClinvarVariant(BaseModel):
    cds_pos: int | str
    hgvs_c: str
    hgvs_p: str | None = None
    classification: VariantClassification
    clinvar_id: str | None = None
    queried: bool = False
    splice: bool = False


class ExonVariantDensity(BaseModel):
    exon_number: int
    variant_count: int


class ProteinDomain(BaseModel):
    aa_start: int
    aa_end: int
    label: str
    short_label: str | None = None


class ProteinActiveSite(BaseModel):
    aa: int
    residue: str
    label: str


class ProteinRangeFeature(BaseModel):
    aa_start: int
    aa_end: int
    label: str


class ProteinPointFeature(BaseModel):
    aa: int
    residue: str
    label: str


class ProteinFeatures(BaseModel):
    signal_peptide: ProteinRangeFeature | None = None
    transmembrane: list[ProteinRangeFeature] = Field(default_factory=list)
    domains: list[ProteinDomain] = Field(default_factory=list)
    active_sites: list[ProteinActiveSite] = Field(default_factory=list)
    membrane_binding: list[ProteinRangeFeature] = Field(default_factory=list)
    palmitoylation: list[ProteinPointFeature] = Field(default_factory=list)


class RestrictionSite(BaseModel):
    name: str
    site: str
    flat_pos: int


class ViewerFeature(BaseModel):
    type: str
    cds_start: int
    cds_end: int
    label: str


class ViewerTracks(BaseModel):
    clinvar_variants: list[ClinvarVariant] = Field(default_factory=list)
    exon_density: list[ExonVariantDensity] = Field(default_factory=list)
    protein_features: ProteinFeatures = Field(default_factory=ProteinFeatures)
    conservation_values: list[float] = Field(default_factory=list)
    restriction_sites: list[RestrictionSite] = Field(default_factory=list)
    features: list[ViewerFeature] = Field(default_factory=list)


class ViewerProvenanceSource(BaseModel):
    name: str
    identifier: str | None = None
    url: str | None = None
    version: str | None = None


class ViewerProvenance(BaseModel):
    sources: list[ViewerProvenanceSource] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class GeneViewerResponse(BaseModel):
    identity: ViewerIdentity
    locus: ViewerLocus
    summary: ViewerSummary
    window: ViewerWindow
    segments: list[ViewerSegment] = Field(default_factory=list)
    queried_variant: QueriedVariant
    sequences: ViewerSequences
    tracks: ViewerTracks = Field(default_factory=ViewerTracks)
    provenance: ViewerProvenance = Field(default_factory=ViewerProvenance)
