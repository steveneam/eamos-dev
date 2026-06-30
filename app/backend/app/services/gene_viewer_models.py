from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.schemas.gene_viewer import (
    GeneViewerRequest,
    GeneViewerResponse,
    ProteinFeatures,
    ViewerProvenanceSource,
)
from app.services.reference_genome import ReferenceWindow
from app.services.sequence_context import NormalizedVariantQuery


class GeneViewerProvider(Protocol):
    def viewer(self, payload: GeneViewerRequest) -> GeneViewerResponse: ...


@dataclass(frozen=True)
class SourceTranscriptExon:
    number: int
    cds_start: int
    cds_end: int
    genomic_start: int
    genomic_end: int


@dataclass(frozen=True)
class SourceTranscriptIntron:
    number: int
    genomic_start: int
    genomic_end: int

    @property
    def total_len(self) -> int:
        return abs(self.genomic_end - self.genomic_start) + 1


@dataclass(frozen=True)
class SourceTranscriptModel:
    gene: str
    transcript: str
    chrom: str
    strand: str
    exons: tuple[SourceTranscriptExon, ...]
    introns: tuple[SourceTranscriptIntron, ...] = ()
    total_exons: int | None = None
    ensembl_gene_id: str | None = None
    transcript_aliases: tuple[str, ...] = ()
    species: str = "human"
    genome_build: str = "GRCh38"
    gene_start: int | None = None
    gene_end: int | None = None
    gene_length: int | None = None
    cds_length: int | None = None
    protein_length: int | None = None
    utr5_length: int | None = None
    utr3_length: int | None = None
    mrna_length: int | None = None
    translation_id: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceBackedViewerBundle:
    query: NormalizedVariantQuery
    variant: Any
    transcript_source: SourceTranscriptModel
    response: GeneViewerResponse


class GeneViewerSourceClient(Protocol):
    def resolve_variant(
        self,
        *,
        query: NormalizedVariantQuery,
        genome_build: str,
    ) -> Any: ...

    def fetch_transcript(
        self,
        *,
        query: NormalizedVariantQuery,
        variant: Any,
        genome_build: str,
    ) -> SourceTranscriptModel: ...

    def fetch_sequence(
        self,
        *,
        chrom: str,
        start: int,
        end: int,
        strand: str,
    ) -> str: ...

    def fetch_protein_features(
        self,
        *,
        transcript: SourceTranscriptModel,
    ) -> ProteinFeatures | None: ...

    def provenance_sources(
        self,
        *,
        query: NormalizedVariantQuery,
        transcript: SourceTranscriptModel,
        variant: Any,
    ) -> list[ViewerProvenanceSource]: ...


class GeneViewerReferenceReader(Protocol):
    def get_sequence(
        self,
        chrom: str,
        start: int,
        end: int,
        build: str | None = None,
    ) -> ReferenceWindow: ...
