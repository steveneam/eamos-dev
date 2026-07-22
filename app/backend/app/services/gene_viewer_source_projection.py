from __future__ import annotations

from app.schemas.gene_viewer import (
    ViewerCoordinateMapRange,
    ViewerTranscriptProjection,
    ViewerTranscriptProjectionInterval,
    ViewerWindowRequest,
)
from app.services.gene_viewer_errors import (
    HTTP_UNPROCESSABLE_ENTITY,
    GeneViewerError,
    raise_unsupported_gene_viewer_input as _raise_unsupported,
)
from app.services.gene_viewer_models import SourceTranscriptModel
from app.services.gene_viewer_utils import reverse_complement as _reverse_complement
from app.services.gene_viewer_variants import VariantProjection
from app.services.gene_viewer_window import _raise_full_gene_not_hydrated, _schema_strand
from app.services.sequence_context import NormalizedVariantQuery, unsupported_input_warning


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
