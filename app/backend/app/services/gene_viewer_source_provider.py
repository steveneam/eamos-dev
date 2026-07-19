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
from app.services.gene_viewer_full_locus import _full_gene_response_from_record
from app.services.gene_viewer_source_client import HttpGeneViewerSourceClient
from app.services.gene_viewer_utils import (
    clean_dna as _clean_dna,
    reverse_complement as _reverse_complement,
)
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
            return self._full_gene_viewer(payload)
        return self.viewer_bundle(payload).response

    def _full_gene_viewer(self, payload: GeneViewerRequest) -> GeneViewerResponse:
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
            self._validate_complete_locus(transcript_source)
            gene_start = int(transcript_source.gene_start or 0)
            gene_end = int(transcript_source.gene_end or 0)
            locus_sequence = _clean_dna(
                self.source_client.fetch_sequence(
                    chrom=transcript_source.chrom,
                    start=gene_start,
                    end=gene_end,
                    strand="+",
                )
            )
            if len(locus_sequence) != gene_end - gene_start + 1:
                raise GeneViewerError(
                    code=GENE_VIEWER_PROVIDER_MALFORMED,
                    message="Full-gene source sequence did not cover the declared gene bounds.",
                    status_code=status.HTTP_502_BAD_GATEWAY,
                )
            response = _full_gene_response_from_record(
                payload=payload,
                record=_source_full_gene_record(
                    transcript=transcript_source,
                    variant=variant,
                    locus_sequence=locus_sequence,
                ),
                fixture_version="",
                provenance_sources=self.source_client.provenance_sources(
                    query=query,
                    transcript=transcript_source,
                    variant=variant,
                ),
                provenance_warnings=[
                    *transcript_source.warnings,
                    "full_gene_source_hydrated",
                ],
                source_label="source_backed_full_gene",
            )
            protein_features = self.source_client.fetch_protein_features(
                transcript=transcript_source
            )
            if protein_features is not None:
                response.tracks.protein_features = protein_features
            return response
        except GeneViewerError:
            raise
        except Exception as exc:
            raise GeneViewerError(
                code=f"{GENE_VIEWER_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="Gene viewer source provider failed while building the full locus.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

    def _validate_complete_locus(self, source: SourceTranscriptModel) -> None:
        if (
            source.gene_start is None
            or source.gene_end is None
            or source.gene_start < 1
            or source.gene_end < source.gene_start
        ):
            raise GeneViewerError(
                code=unsupported_input_warning("full_gene_source_bounds"),
                message="A complete source-backed gene locus is unavailable.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        locus_length = source.gene_end - source.gene_start + 1
        max_bases = max(
            1,
            int(getattr(self.settings, "gene_viewer_full_locus_max_bases", 750_000)),
        )
        if locus_length > max_bases:
            raise GeneViewerError(
                code=unsupported_input_warning("full_gene_response_budget"),
                message="The complete gene locus exceeds the configured response budget.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        expected_exons = source.total_exons or len(source.exons)
        if not source.exons or len(source.exons) != expected_exons:
            raise GeneViewerError(
                code=unsupported_input_warning("full_gene_exon_annotation"),
                message="Complete source-backed exon annotation is unavailable for this transcript.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if len(source.exons) > 1 and len(source.introns) != len(source.exons) - 1:
            raise GeneViewerError(
                code=unsupported_input_warning("full_gene_intron_annotation"),
                message="Complete source-backed intron annotation is unavailable for this transcript.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        for exon in source.exons:
            start, end = sorted((exon.genomic_start, exon.genomic_end))
            if start < source.gene_start or end > source.gene_end:
                raise GeneViewerError(
                    code=GENE_VIEWER_PROVIDER_MALFORMED,
                    message="Source transcript exon lies outside the declared gene locus.",
                    status_code=status.HTTP_502_BAD_GATEWAY,
                )

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


def _source_full_gene_record(
    *,
    transcript: SourceTranscriptModel,
    variant: VariantProjection,
    locus_sequence: str,
) -> dict[str, object]:
    gene_start = int(transcript.gene_start or 0)
    exons: list[dict[str, object]] = []
    for exon in transcript.exons:
        start, end = sorted((exon.genomic_start, exon.genomic_end))
        genomic_sequence = locus_sequence[start - gene_start : end - gene_start + 1]
        exon_sequence = (
            _reverse_complement(genomic_sequence)
            if _schema_strand(transcript.strand) == "-"
            else genomic_sequence
        )
        exons.append(
            {
                "number": exon.number,
                "cds_start": exon.cds_start,
                "cds_end": exon.cds_end,
                "genomic_start": start,
                "genomic_end": end,
                "sequence": exon_sequence,
            }
        )
    return {
        "gene": transcript.gene,
        "cdna": variant.hgvs_c,
        "transcript": transcript.transcript,
        "transcript_aliases": list(transcript.transcript_aliases),
        "chrom": transcript.chrom,
        "strand": transcript.strand,
        "ensembl_gene_id": transcript.ensembl_gene_id,
        "species": transcript.species,
        "genome_build": transcript.genome_build,
        "gene_start": transcript.gene_start,
        "gene_end": transcript.gene_end,
        "gene_length": transcript.gene_length,
        "cds_length": transcript.cds_length,
        "protein_length": transcript.protein_length,
        "utr5_length": transcript.utr5_length,
        "utr3_length": transcript.utr3_length,
        "mrna_length": transcript.mrna_length,
        "variant": {
            "hgvs_c": variant.hgvs_c,
            "cds_pos": variant.cds_pos,
            "ref": variant.ref,
            "alt": variant.alt,
            "hgvs_p": variant.hgvs_p,
            "genomic_hg38": variant.genomic_hg38,
            "codon_number": variant.codon_number,
            "codon_offset": variant.codon_offset,
            "aa_ref": variant.aa_ref,
            "aa_alt": variant.aa_alt,
            "classification": variant.classification,
        },
        "exons": exons,
        "introns": [
            {
                "number": intron.number,
                "genomic_start": min(intron.genomic_start, intron.genomic_end),
                "genomic_end": max(intron.genomic_start, intron.genomic_end),
                "total_len": intron.total_len,
            }
            for intron in transcript.introns
        ],
        "locus_sequence": locus_sequence,
        "warnings": list(transcript.warnings),
    }


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
