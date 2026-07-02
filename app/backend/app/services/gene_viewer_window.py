from __future__ import annotations

from dataclasses import dataclass

from app.schemas.gene_viewer import (
    AppliedVariant,
    GeneViewerRequest,
    GeneViewerResponse,
    QueriedVariant,
    ViewerIdentity,
    ViewerLocus,
    ViewerProvenance,
    ViewerProvenanceSource,
    ViewerSegment,
    ViewerSequences,
    ViewerSummary,
    ViewerTracks,
    ViewerWindow,
    ViewerWindowRequest,
)
from app.services.gene_viewer_errors import (
    GENE_VIEWER_REFERENCE_MISMATCH,
    HTTP_UNPROCESSABLE_ENTITY,
    GeneViewerError,
    raise_unsupported_gene_viewer_input,
)
from app.services.gene_viewer_variants import VariantProjection
from app.services.variant_applied_model import build_protein_product_effect


@dataclass(frozen=True)
class TranscriptExon:
    number: int
    cds_start: int
    cds_end: int
    sequence: str
    genomic_start: int | None = None
    genomic_end: int | None = None

    def sequence_for(self, cds_start: int, cds_end: int) -> str:
        start_offset = cds_start - self.cds_start
        end_offset = cds_end - self.cds_start + 1
        return self.sequence[start_offset:end_offset]


@dataclass(frozen=True)
class TranscriptIntron:
    number: int
    total_len: int
    five_prime_sequence: str = ""
    three_prime_sequence: str = ""
    genomic_start: int | None = None
    genomic_end: int | None = None

    @property
    def omitted_bp(self) -> int:
        return max(
            0, self.total_len - len(self.five_prime_sequence) - len(self.three_prime_sequence)
        )


@dataclass(frozen=True)
class TranscriptModel:
    gene: str
    transcript: str
    chrom: str
    strand: str
    exons: tuple[TranscriptExon, ...]
    introns: tuple[TranscriptIntron, ...] = ()
    ensembl_gene_id: str | None = None
    transcript_aliases: tuple[str, ...] = ()
    species: str = "human"
    genome_build: str = "GRCh38"
    gene_start: int | None = None
    gene_end: int | None = None
    gene_length: int | None = None
    total_exons: int | None = None
    cds_length: int | None = None
    protein_length: int | None = None
    utr5_length: int | None = None
    utr3_length: int | None = None
    mrna_length: int | None = None


@dataclass(frozen=True)
class VariantDisplayOperation:
    segment_id: str
    sequence_offset: int
    ref: str
    alt: str
    replace_length: int


class TranscriptWindowBuilder:
    def build(
        self,
        *,
        request: GeneViewerRequest,
        transcript: TranscriptModel,
        variant: VariantProjection,
    ) -> GeneViewerResponse:
        display_start, display_end = self._window_bounds(
            window=request.window,
            variant=variant,
            transcript=transcript,
        )
        segments = self._segments(
            transcript=transcript,
            display_start=display_start,
            display_end=display_end,
        )
        reference_sequence = "".join(_segment_display_sequence(segment) for segment in segments)
        applied_variant, display_sequence = self._apply_variant(
            allele_mode=request.allele_mode,
            reference_sequence=reference_sequence,
            segments=segments,
            variant=variant,
        )

        return GeneViewerResponse(
            identity=ViewerIdentity(
                gene=transcript.gene,
                ensembl_gene_id=transcript.ensembl_gene_id,
                requested_transcript=request.transcript,
                resolved_transcript=transcript.transcript,
                transcript_aliases=list(transcript.transcript_aliases),
                species=transcript.species,
                genome_build=transcript.genome_build,
            ),
            locus=ViewerLocus(
                chrom=transcript.chrom,
                gene_start=transcript.gene_start,
                gene_end=transcript.gene_end,
                strand=_schema_strand(transcript.strand),
            ),
            summary=ViewerSummary(
                gene_length=transcript.gene_length,
                total_exons=transcript.total_exons or len(transcript.exons),
                cds_length=transcript.cds_length,
                protein_length=transcript.protein_length,
                utr5_length=transcript.utr5_length,
                utr3_length=transcript.utr3_length,
                mrna_length=transcript.mrna_length,
            ),
            window=ViewerWindow(
                kind=request.window.kind,
                cds_start=request.window.cds_start,
                cds_end=request.window.cds_end,
                cds_flank_bp=request.window.cds_flank_bp,
                intron_flank_bp=request.window.intron_flank_bp,
                display_cds_start=display_start,
                display_cds_end=display_end,
                total_display_bases=len(reference_sequence),
            ),
            segments=segments,
            queried_variant=QueriedVariant(
                hgvs_c=variant.hgvs_c,
                hgvs_p=variant.hgvs_p,
                cds_pos=variant.cds_pos,
                genomic_hg38=variant.genomic_hg38,
                ref=variant.ref,
                alt=variant.alt,
                codon_number=variant.codon_number,
                codon_offset=variant.codon_offset,
                aa_ref=variant.aa_ref,
                aa_alt=variant.aa_alt,
                classification=variant.classification,
            ),
            sequences=ViewerSequences(
                allele_mode=request.allele_mode,
                reference_window_sequence=reference_sequence,
                display_window_sequence=display_sequence,
                applied_variant=applied_variant,
            ),
            tracks=ViewerTracks(
                protein_product=build_protein_product_effect(
                    variant=variant,
                    allele_mode=request.allele_mode,
                    reference_protein_length=transcript.protein_length,
                    exons=transcript.exons,
                )
            ),
            provenance=ViewerProvenance(
                sources=[
                    ViewerProvenanceSource(
                        name="synthetic_transcript_model",
                        identifier=transcript.transcript,
                    )
                ]
            ),
        )

    def _window_bounds(
        self,
        *,
        window: ViewerWindowRequest,
        variant: VariantProjection,
        transcript: TranscriptModel,
    ) -> tuple[int, int]:
        min_cds = min(exon.cds_start for exon in transcript.exons)
        max_cds = max(exon.cds_end for exon in transcript.exons)
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
            raise_unsupported_gene_viewer_input(
                "window",
                "Viewer window does not overlap the transcript CDS.",
            )
        return start, end

    def _segments(
        self,
        *,
        transcript: TranscriptModel,
        display_start: int,
        display_end: int,
    ) -> list[ViewerSegment]:
        ordered_exons = sorted(transcript.exons, key=lambda exon: exon.cds_start)
        introns = {intron.number: intron for intron in transcript.introns}
        selected: list[tuple[TranscriptExon, int, int]] = []
        for exon in ordered_exons:
            if exon.cds_end < display_start or exon.cds_start > display_end:
                continue
            start = max(display_start, exon.cds_start)
            end = min(display_end, exon.cds_end)
            selected.append((exon, start, end))

        segments: list[ViewerSegment] = []
        for index, (exon, start, end) in enumerate(selected):
            segment_id = f"exon-{exon.number}:{start}-{end}"
            segments.append(
                ViewerSegment(
                    id=segment_id,
                    kind="exon",
                    label=f"Exon {exon.number}",
                    exon_number=exon.number,
                    cds_start=start,
                    cds_end=end,
                    genomic_start=exon.genomic_start,
                    genomic_end=exon.genomic_end,
                    strand=_schema_strand(transcript.strand),
                    sequence=exon.sequence_for(start, end),
                )
            )
            next_exon = selected[index + 1][0] if index + 1 < len(selected) else None
            if next_exon is None or next_exon.number != exon.number + 1:
                continue
            intron = introns.get(exon.number)
            if intron is None:
                continue
            segments.append(
                ViewerSegment(
                    id=f"intron-{intron.number}",
                    kind="intron",
                    label=f"Intron {intron.number}",
                    intron_number=intron.number,
                    genomic_start=intron.genomic_start,
                    genomic_end=intron.genomic_end,
                    strand=_schema_strand(transcript.strand),
                    five_prime_sequence=intron.five_prime_sequence,
                    three_prime_sequence=intron.three_prime_sequence,
                    omitted_bp=intron.omitted_bp,
                )
            )

        return segments

    def _apply_variant(
        self,
        *,
        allele_mode: str,
        reference_sequence: str,
        segments: list[ViewerSegment],
        variant: VariantProjection,
    ) -> tuple[AppliedVariant | None, str]:
        operation = _variant_display_operation(
            segments=segments,
            reference_sequence=reference_sequence,
            variant=variant,
        )
        if allele_mode == "reference":
            return None, reference_sequence

        applied = AppliedVariant(
            hgvs_c=variant.hgvs_c,
            cds_pos=variant.cds_pos,
            segment_id=operation.segment_id,
            sequence_offset=operation.sequence_offset,
            ref=operation.ref,
            alt=operation.alt,
        )
        display_sequence = (
            reference_sequence[: operation.sequence_offset]
            + operation.alt
            + reference_sequence[operation.sequence_offset + operation.replace_length :]
        )
        return applied, display_sequence


def _segment_display_sequence(segment: ViewerSegment) -> str:
    if segment.kind == "intron":
        return f"{segment.five_prime_sequence}{segment.three_prime_sequence}"
    return segment.sequence


def _replace_at(sequence: str, index: int, value: str) -> str:
    return f"{sequence[:index]}{value}{sequence[index + 1:]}"


def _variant_display_operation(
    *,
    segments: list[ViewerSegment],
    reference_sequence: str,
    variant: VariantProjection,
) -> VariantDisplayOperation:
    coord_map = _exon_display_coordinate_map(segments)
    end = variant.cds_end or variant.cds_pos

    if variant.variant_type == "insertion":
        left = variant.cds_pos
        right = end
        if right != left + 1:
            raise_unsupported_gene_viewer_input(
                "variant_insert_coordinates",
                "Viewer insertion overlays require adjacent coding coordinates.",
            )
        if left not in coord_map or right not in coord_map:
            _raise_variant_outside_window(variant)
        segment_id, left_offset = coord_map[left]
        return VariantDisplayOperation(
            segment_id=segment_id,
            sequence_offset=left_offset + 1,
            ref="",
            alt=variant.alt,
            replace_length=0,
        )

    positions = list(range(variant.cds_pos, end + 1))
    if not positions or any(position not in coord_map for position in positions):
        _raise_variant_outside_window(variant)

    mapped = [coord_map[position] for position in positions]
    segment_ids = {segment_id for segment_id, _offset in mapped}
    offsets = [offset for _segment_id, offset in mapped]
    if len(segment_ids) != 1 or offsets != list(range(offsets[0], offsets[0] + len(offsets))):
        raise_unsupported_gene_viewer_input(
            "variant_spans_segments",
            "Viewer overlays currently require the affected coding bases to be contiguous in the displayed segment.",
        )

    segment_id = mapped[0][0]
    sequence_offset = offsets[0]
    observed_ref = reference_sequence[sequence_offset : offsets[-1] + 1].upper()

    if variant.variant_type == "duplication":
        duplicated = variant.alt or observed_ref
        if variant.alt and duplicated != observed_ref:
            _raise_reference_mismatch(variant)
        return VariantDisplayOperation(
            segment_id=segment_id,
            sequence_offset=offsets[-1] + 1,
            ref="",
            alt=duplicated,
            replace_length=0,
        )

    if variant.ref and observed_ref != variant.ref.upper():
        _raise_reference_mismatch(variant)

    if variant.variant_type in {"substitution", "deletion", "delins"}:
        return VariantDisplayOperation(
            segment_id=segment_id,
            sequence_offset=sequence_offset,
            ref=variant.ref.upper() or observed_ref,
            alt=variant.alt,
            replace_length=len(observed_ref),
        )

    raise_unsupported_gene_viewer_input(
        "variant_type",
        f"Viewer overlays do not support variant type {variant.variant_type}.",
    )


def _exon_display_coordinate_map(
    segments: list[ViewerSegment],
) -> dict[int, tuple[str, int]]:
    coord_map: dict[int, tuple[str, int]] = {}
    cumulative = 0
    for segment in segments:
        segment_sequence = _segment_display_sequence(segment)
        if segment.kind == "exon" and segment.cds_start is not None and segment.cds_end is not None:
            for local_offset, cds_pos in enumerate(range(segment.cds_start, segment.cds_end + 1)):
                coord_map[cds_pos] = (segment.id, cumulative + local_offset)
        cumulative += len(segment_sequence)
    return coord_map


def _raise_reference_mismatch(variant: VariantProjection) -> None:
    raise GeneViewerError(
        code=GENE_VIEWER_REFERENCE_MISMATCH,
        message=(
            "Viewer reference sequence does not match the requested "
            f"variant at {variant.hgvs_c}."
        ),
        status_code=HTTP_UNPROCESSABLE_ENTITY,
        warnings=[GENE_VIEWER_REFERENCE_MISMATCH],
    )


def _raise_variant_outside_window(variant: VariantProjection) -> None:
    raise_unsupported_gene_viewer_input(
        "variant_outside_window",
        f"Queried variant {variant.hgvs_c} is outside the active viewer window.",
    )


def _raise_full_gene_not_hydrated() -> None:
    raise_unsupported_gene_viewer_input(
        "full_gene",
        (
            "Full-gene genomic-locus viewer payloads are defined by the backend "
            "contract but require FGV-002 fixture/source hydration before runtime use."
        ),
    )


def _schema_strand(strand: str) -> str:
    return strand if strand in {"+", "-"} else "unknown"
