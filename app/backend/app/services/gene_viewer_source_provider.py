from __future__ import annotations

from fastapi import status

from app.core.config import Settings
from app.schemas.gene_viewer import (
    GeneViewerRequest,
    GeneViewerResponse,
    ViewerCoordinateMapRange,
    ViewerProvenance,
    ViewerTranscriptProjection,
    ViewerTranscriptProjectionInterval,
    ViewerWindowRequest,
)
from app.services.alphamissense_local import AlphaMissenseLocalAdapter
from app.services.gene_viewer_errors import (
    GENE_VIEWER_PROVIDER_FAILED_PREFIX,
    GENE_VIEWER_PROVIDER_MALFORMED,
    HTTP_UNPROCESSABLE_ENTITY,
    GeneViewerError,
    raise_unsupported_gene_viewer_input as _raise_unsupported,
)
from app.services.gene_viewer_models import (
    GeneViewerProvider,
    GeneViewerSourceClient,
    SourceBackedViewerBundle,
    SourceTranscriptIntron,
    SourceTranscriptModel,
)
from app.services.gene_viewer_protein_tracks import (
    hydrate_response_with_alphamissense_heatmap,
    hydrate_response_with_source_protein_track,
)
from app.services.gene_viewer_source_client import HttpGeneViewerSourceClient
from app.services.gene_viewer_utils import clean_dna as _clean_dna
from app.services.gene_viewer_variants import VariantProjection
from app.services.gene_viewer_window import (
    TranscriptExon,
    TranscriptIntron,
    TranscriptModel,
    TranscriptWindowBuilder,
    _raise_full_gene_not_hydrated,
    _schema_strand,
)
from app.services.protein_annotation import ProteinAnnotationService
from app.services.sequence_context import (
    NormalizedVariantQuery,
    normalize_sequence_query,
    unsupported_input_warning,
)
from app.services.variant_applied_model import build_protein_product_effect


class SourceBackedGeneViewerProvider:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        source_client: GeneViewerSourceClient | None = None,
        builder: TranscriptWindowBuilder | None = None,
        fixture_provider: GeneViewerProvider | None = None,
        protein_annotation_service: ProteinAnnotationService | None = None,
        alphamissense_adapter: AlphaMissenseLocalAdapter | None = None,
    ) -> None:
        self.settings = settings
        self.source_client = source_client or HttpGeneViewerSourceClient(settings)
        self.builder = builder or TranscriptWindowBuilder()
        if fixture_provider is None:
            from app.services.gene_viewer import GeneViewerFixtureProvider

            fixture_provider = GeneViewerFixtureProvider()
        self.fixture_provider = fixture_provider
        self.protein_annotation_service = protein_annotation_service
        self.alphamissense_adapter = alphamissense_adapter

    def viewer(self, payload: GeneViewerRequest) -> GeneViewerResponse:
        if payload.window.kind == "full_gene":
            return self.fixture_provider.viewer(payload)
        return self.viewer_bundle(payload).response

    def viewer_bundle(self, payload: GeneViewerRequest) -> SourceBackedViewerBundle:
        query = normalize_sequence_query(payload.gene, payload.cdna, payload.transcript)
        self._validate_query(payload=payload, query=query)
        try:
            variant_seed = VariantProjection.from_hgvs_c(query.hgvs)
            if query.resolver_transcript:
                variant = self.source_client.resolve_variant(
                    query=query,
                    genome_build=payload.genome_build,
                )
                transcript_source = self.source_client.fetch_transcript(
                    query=query,
                    variant=variant,
                    genome_build=payload.genome_build,
                )
            else:
                transcript_source = self.source_client.fetch_transcript(
                    query=query,
                    variant=variant_seed,
                    genome_build=payload.genome_build,
                )
                query = query_with_source_transcript(query, transcript_source)
                variant = self.source_client.resolve_variant(
                    query=query,
                    genome_build=payload.genome_build,
                )
            transcript = self._transcript_model(
                source=transcript_source,
                window=payload.window,
                variant=variant,
                intron_flank_bp=payload.window.intron_flank_bp,
            )
            response = self.builder.build(
                request=payload,
                transcript=transcript,
                variant=variant,
            )
            response.transcript_projection = source_transcript_projection(transcript_source)
            protein_features = self.source_client.fetch_protein_features(
                transcript=transcript_source
            )
        except GeneViewerError:
            raise
        except Exception as exc:
            raise GeneViewerError(
                code=f"{GENE_VIEWER_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="Gene viewer source provider failed while building the viewer.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        if protein_features is not None:
            response.tracks.protein_features = protein_features
        response.tracks.protein_product = build_protein_product_effect(
            variant=variant,
            allele_mode=payload.allele_mode,
            reference_protein_length=transcript_source.protein_length,
            exons=transcript_source.exons,
        )
        response.provenance = ViewerProvenance(
            sources=self.source_client.provenance_sources(
                query=query,
                transcript=transcript_source,
                variant=variant,
            ),
            warnings=list(transcript_source.warnings),
        )
        hydrate_response_with_source_protein_track(
            response=response,
            transcript_source=transcript_source,
            protein_annotation_service=self.protein_annotation_service,
            sequence_for_exon=lambda exon: self._sequence(
                chrom=transcript_source.chrom,
                start=exon.genomic_start,
                end=exon.genomic_end,
                strand=transcript_source.strand,
                expected_len=exon.cds_end - exon.cds_start + 1,
            ),
        )
        if "alphamissense" in payload.tracks:
            hydrate_response_with_alphamissense_heatmap(
                response=response,
                variant=variant,
                transcript_source=transcript_source,
                alphamissense_adapter=self.alphamissense_adapter,
                sequence_for_exon=lambda exon: self._sequence(
                    chrom=transcript_source.chrom,
                    start=exon.genomic_start,
                    end=exon.genomic_end,
                    strand=transcript_source.strand,
                    expected_len=exon.cds_end - exon.cds_start + 1,
                ),
            )
        return SourceBackedViewerBundle(
            query=query,
            variant=variant,
            transcript_source=transcript_source,
            response=response,
        )

    def _validate_query(
        self,
        *,
        payload: GeneViewerRequest,
        query: NormalizedVariantQuery,
    ) -> None:
        if payload.species.strip().lower() != "human":
            _raise_unsupported("species", "Gene viewer currently supports human transcripts only.")
        if payload.genome_build not in {"GRCh38", "hg38"}:
            _raise_unsupported(
                "genome_build",
                "Gene viewer currently supports GRCh38/hg38 only.",
            )
        if payload.window.kind == "full_gene":
            _raise_full_gene_not_hydrated()
        if query.kind != "cdna":
            _raise_unsupported(
                query.kind,
                "Gene viewer source-backed mode currently supports coding cDNA HGVS only.",
            )

    def _transcript_model(
        self,
        *,
        source: SourceTranscriptModel,
        window: ViewerWindowRequest,
        variant: VariantProjection,
        intron_flank_bp: int,
    ) -> TranscriptModel:
        display_start, display_end = source_window_bounds(
            window=window,
            variant=variant,
            source=source,
        )
        source_exons = tuple(
            exon
            for exon in source.exons
            if exon.cds_end >= display_start and exon.cds_start <= display_end
        )
        if not source_exons:
            raise GeneViewerError(
                code=unsupported_input_warning("window"),
                message="Viewer window does not overlap the transcript CDS.",
                status_code=HTTP_UNPROCESSABLE_ENTITY,
            )

        exons: list[TranscriptExon] = []
        for exon in source_exons:
            sequence = self._sequence(
                chrom=source.chrom,
                start=exon.genomic_start,
                end=exon.genomic_end,
                strand=source.strand,
                expected_len=exon.cds_end - exon.cds_start + 1,
            )
            exons.append(
                TranscriptExon(
                    number=exon.number,
                    cds_start=exon.cds_start,
                    cds_end=exon.cds_end,
                    sequence=sequence,
                    genomic_start=exon.genomic_start,
                    genomic_end=exon.genomic_end,
                )
            )

        selected_exon_numbers = {exon.number for exon in source_exons}
        introns = tuple(
            self._intron_model(
                source=source,
                intron=intron,
                intron_flank_bp=intron_flank_bp,
            )
            for intron in source.introns
            if intron.number in selected_exon_numbers
            and (intron.number + 1) in selected_exon_numbers
        )
        return TranscriptModel(
            gene=source.gene,
            transcript=source.transcript,
            chrom=source.chrom,
            strand=source.strand,
            exons=tuple(exons),
            introns=introns,
            ensembl_gene_id=source.ensembl_gene_id,
            transcript_aliases=source.transcript_aliases,
            species=source.species,
            genome_build=source.genome_build,
            gene_start=source.gene_start,
            gene_end=source.gene_end,
            gene_length=source.gene_length,
            cds_length=source.cds_length,
            protein_length=source.protein_length,
            utr5_length=source.utr5_length,
            utr3_length=source.utr3_length,
            mrna_length=source.mrna_length,
            total_exons=source.total_exons or len(source.exons),
        )

    def _intron_model(
        self,
        *,
        source: SourceTranscriptModel,
        intron: SourceTranscriptIntron,
        intron_flank_bp: int,
    ) -> TranscriptIntron:
        start = min(intron.genomic_start, intron.genomic_end)
        end = max(intron.genomic_start, intron.genomic_end)
        total_len = end - start + 1
        flank = max(0, intron_flank_bp)
        five_len = min(flank, total_len)
        three_len = min(flank, max(0, total_len - five_len))
        five_prime = ""
        three_prime = ""
        if five_len:
            if source.strand == "-":
                five_prime = self._sequence(
                    chrom=source.chrom,
                    start=end - five_len + 1,
                    end=end,
                    strand=source.strand,
                    expected_len=five_len,
                ).lower()
            else:
                five_prime = self._sequence(
                    chrom=source.chrom,
                    start=start,
                    end=start + five_len - 1,
                    strand=source.strand,
                    expected_len=five_len,
                ).lower()
        if three_len:
            if source.strand == "-":
                three_prime = self._sequence(
                    chrom=source.chrom,
                    start=start,
                    end=start + three_len - 1,
                    strand=source.strand,
                    expected_len=three_len,
                ).lower()
            else:
                three_prime = self._sequence(
                    chrom=source.chrom,
                    start=end - three_len + 1,
                    end=end,
                    strand=source.strand,
                    expected_len=three_len,
                ).lower()
        return TranscriptIntron(
            number=intron.number,
            total_len=total_len,
            five_prime_sequence=five_prime,
            three_prime_sequence=three_prime,
            genomic_start=intron.genomic_start,
            genomic_end=intron.genomic_end,
        )

    def _sequence(
        self,
        *,
        chrom: str,
        start: int,
        end: int,
        strand: str,
        expected_len: int,
    ) -> str:
        if start > end:
            start, end = end, start
        sequence = _clean_dna(
            self.source_client.fetch_sequence(
                chrom=chrom,
                start=start,
                end=end,
                strand=strand,
            )
        )
        if len(sequence) != expected_len:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_MALFORMED,
                message=(
                    "Gene viewer source sequence length did not match the "
                    f"requested interval ({len(sequence)} != {expected_len})."
                ),
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        return sequence


def query_with_source_transcript(
    query: NormalizedVariantQuery,
    source: SourceTranscriptModel,
) -> NormalizedVariantQuery:
    resolver_transcript = source_resolver_transcript(source)
    return query.model_copy(
        update={
            "resolver_transcript": resolver_transcript,
            "resolver_transcript_hgvs": f"{resolver_transcript}:{query.hgvs}",
        }
    )


def source_resolver_transcript(source: SourceTranscriptModel) -> str:
    candidates = [*source.transcript_aliases, source.transcript]
    for candidate in candidates:
        if candidate.startswith(("NM_", "NR_")):
            return candidate
    for candidate in candidates:
        if candidate.startswith("ENST"):
            return candidate
    if source.transcript:
        return source.transcript
    _raise_unsupported(
        "transcript",
        f"Could not choose a source-backed transcript for {source.gene}.",
    )


def source_window_bounds(
    *,
    window: ViewerWindowRequest,
    variant: VariantProjection,
    source: SourceTranscriptModel,
) -> tuple[int, int]:
    min_cds = min(exon.cds_start for exon in source.exons)
    max_cds = max(exon.cds_end for exon in source.exons)
    if window.kind == "full_gene":
        _raise_full_gene_not_hydrated()
    if window.kind == "cds_range":
        start = window.cds_start if window.cds_start is not None else min_cds
        end = window.cds_end if window.cds_end is not None else max_cds
    else:
        start = variant.cds_pos - window.cds_flank_bp
        end = variant.cds_pos + window.cds_flank_bp
    start = max(min_cds, start)
    end = min(max_cds, end)
    if start > end:
        raise GeneViewerError(
            code=unsupported_input_warning("window"),
            message="Viewer window does not overlap the transcript CDS.",
            status_code=HTTP_UNPROCESSABLE_ENTITY,
        )
    return start, end


def source_transcript_projection(source: SourceTranscriptModel) -> ViewerTranscriptProjection:
    introns_by_number = {intron.number: intron for intron in source.introns}
    intervals: list[ViewerTranscriptProjectionInterval] = []
    coordinate_map: list[ViewerCoordinateMapRange] = []

    for exon in source.exons:
        intervals.append(
            ViewerTranscriptProjectionInterval(
                id=f"exon-{exon.number}",
                kind="exon",
                label=f"Exon {exon.number}",
                genomic_start=exon.genomic_start,
                genomic_end=exon.genomic_end,
                strand=_schema_strand(source.strand),
                exon_number=exon.number,
                cds_start=exon.cds_start,
                cds_end=exon.cds_end,
            )
        )
        coordinate_map.append(
            ViewerCoordinateMapRange(
                genomic_start=exon.genomic_start,
                genomic_end=exon.genomic_end,
                cds_start=exon.cds_start,
                cds_end=exon.cds_end,
            )
        )
        intron = introns_by_number.get(exon.number)
        if intron is None:
            continue
        intervals.append(
            ViewerTranscriptProjectionInterval(
                id=f"intron-{intron.number}",
                kind="intron",
                label=f"Intron {intron.number}",
                genomic_start=intron.genomic_start,
                genomic_end=intron.genomic_end,
                strand=_schema_strand(source.strand),
                intron_number=intron.number,
            )
        )

    return ViewerTranscriptProjection(
        transcript=source.transcript,
        strand=_schema_strand(source.strand),
        intervals=intervals,
        coordinate_map=coordinate_map,
    )
