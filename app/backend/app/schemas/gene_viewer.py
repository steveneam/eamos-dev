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
ViewerWindowKind = Literal["around_variant", "cds_range", "full_gene"]
ViewerDisplayBasis = Literal["transcript_window", "genomic_locus"]
ViewerSegmentKind = Literal["exon", "intron"]
ViewerCoordinateSystem = Literal["genomic", "cdna", "cds", "protein", "row"]
ViewerTranscriptIntervalKind = Literal["exon", "intron", "utr5", "utr3", "cds"]
ViewerFullLocusFeatureKind = Literal[
    "gene",
    "transcript",
    "exon",
    "intron",
    "utr5",
    "utr3",
    "cds",
    "queried_variant",
    "clinvar",
    "restriction_site",
    "conservation_bin",
    "primer",
    "guide",
    "custom",
]
ViewerOrientation = Literal["genomic_forward", "genomic_reverse", "transcript"]
ViewerRowCoordinatePolicy = Literal["genomic", "transcript"]
ViewerBaseColorScheme = Literal["none", "nucleotide"]
ViewerAminoAcidColorScheme = Literal["none", "biochemical"]
ProteinConsequenceKind = Literal[
    "reference",
    "synonymous",
    "missense",
    "stop_gained",
    "stop_lost",
    "frameshift",
    "inframe_deletion",
    "inframe_insertion",
    "inframe_duplication",
    "delins",
    "splice",
    "unknown",
]
ProteinProductExonState = Literal[
    "retained",
    "contains_variant",
    "downstream_truncated",
    "not_applicable",
]
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
    cds_start: int | None = Field(default=None, ge=1, le=50000)
    cds_end: int | None = Field(default=None, ge=1, le=50000)
    cds_flank_bp: int = Field(default=120, ge=0, le=5000)
    intron_flank_bp: int = Field(default=30, ge=0, le=500)


class GeneViewerRequest(BaseModel):
    gene: str = Field(min_length=1, max_length=32)
    cdna: str = Field(min_length=1, max_length=160)
    transcript: str | None = Field(default=None, max_length=80)
    species: str = Field(default="human", min_length=1, max_length=32)
    genome_build: str = Field(default="GRCh38", min_length=1, max_length=16)
    allele_mode: AlleleMode = "reference"
    window: ViewerWindowRequest = Field(default_factory=ViewerWindowRequest)
    tracks: list[ViewerTrack] = Field(
        default_factory=lambda: [
            "sequence",
            "exons",
            "clinvar",
            "protein_features",
            "restriction",
        ],
        max_length=8,
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
    basis: ViewerDisplayBasis = "transcript_window"
    cds_start: int | None = None
    cds_end: int | None = None
    cds_flank_bp: int
    intron_flank_bp: int
    display_cds_start: int
    display_cds_end: int
    total_display_bases: int
    display_genomic_start: int | None = None
    display_genomic_end: int | None = None
    total_locus_bases: int | None = None


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


class ProteinProductExonEffect(BaseModel):
    exon_number: int
    cds_start: int
    cds_end: int
    state: ProteinProductExonState
    affected_cds_start: int | None = None
    affected_cds_end: int | None = None
    lost_cds_bases: int = 0


class ProteinProductEffect(BaseModel):
    allele_mode: AlleleMode
    consequence: ProteinConsequenceKind
    label: str
    description: str
    reference_protein_length: int | None = None
    effective_protein_length: int | None = None
    truncates_protein: bool = False
    stop_codon: int | None = None
    affected_aa_start: int | None = None
    lost_aa_count: int = 0
    nmd_risk: str | None = None
    exon_effects: list[ProteinProductExonEffect] = Field(default_factory=list)


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
    protein_product: ProteinProductEffect | None = None
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


class ViewerGenomicLocus(BaseModel):
    chrom: str
    start: int = Field(ge=1)
    end: int = Field(ge=1)
    strand: GenomeStrand = "unknown"
    genome_build: str = "GRCh38"
    sequence: str
    coordinate_system: Literal["genomic"] = "genomic"


class ViewerCoordinateMapRange(BaseModel):
    genomic_start: int = Field(ge=1)
    genomic_end: int = Field(ge=1)
    cdna_start: int | None = None
    cdna_end: int | None = None
    cds_start: int | None = None
    cds_end: int | None = None
    protein_start: int | None = None
    protein_end: int | None = None


class ViewerCodonStart(BaseModel):
    codon_number: int = Field(ge=1)
    cds_start: int = Field(ge=1)
    protein_position: int = Field(ge=1)
    genomic_start: int = Field(ge=1)
    genomic_positions: list[int] = Field(default_factory=list)


class ViewerTranscriptProjectionInterval(BaseModel):
    id: str
    kind: ViewerTranscriptIntervalKind
    label: str
    genomic_start: int = Field(ge=1)
    genomic_end: int = Field(ge=1)
    strand: GenomeStrand = "unknown"
    exon_number: int | None = None
    intron_number: int | None = None
    cdna_start: int | None = None
    cdna_end: int | None = None
    cds_start: int | None = None
    cds_end: int | None = None
    protein_start: int | None = None
    protein_end: int | None = None


class ViewerTranscriptProjection(BaseModel):
    transcript: str
    strand: GenomeStrand = "unknown"
    intervals: list[ViewerTranscriptProjectionInterval] = Field(default_factory=list)
    coordinate_map: list[ViewerCoordinateMapRange] = Field(default_factory=list)
    codon_starts: list[ViewerCodonStart] = Field(default_factory=list)


class ViewerFeatureInterval(BaseModel):
    id: str
    kind: ViewerFullLocusFeatureKind
    label: str
    coordinate_system: ViewerCoordinateSystem
    start: int = Field(ge=1)
    end: int = Field(ge=1)
    strand: GenomeStrand = "unknown"
    source: str | None = None
    classification: VariantClassification | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ViewerRenderingHints(BaseModel):
    orientation: ViewerOrientation = "genomic_forward"
    row_coordinate_policy: ViewerRowCoordinatePolicy = "genomic"
    bases_per_row_min: int = Field(default=80, ge=20, le=1000)
    bases_per_row_max: int = Field(default=140, ge=20, le=2000)
    max_visual_density: int | None = Field(default=None, ge=1)
    base_color_scheme: ViewerBaseColorScheme = "none"
    amino_acid_color_scheme: ViewerAminoAcidColorScheme = "biochemical"


class ViewerFullLocus(BaseModel):
    basis: Literal["genomic_locus"] = "genomic_locus"
    locus: ViewerGenomicLocus
    transcript_projection: ViewerTranscriptProjection
    feature_intervals: list[ViewerFeatureInterval] = Field(default_factory=list)
    rendering_hints: ViewerRenderingHints = Field(default_factory=ViewerRenderingHints)


class GeneViewerResponse(BaseModel):
    identity: ViewerIdentity
    locus: ViewerLocus
    summary: ViewerSummary
    window: ViewerWindow
    segments: list[ViewerSegment] = Field(default_factory=list)
    queried_variant: QueriedVariant
    sequences: ViewerSequences
    tracks: ViewerTracks = Field(default_factory=ViewerTracks)
    full_locus: ViewerFullLocus | None = None
    provenance: ViewerProvenance = Field(default_factory=ViewerProvenance)
