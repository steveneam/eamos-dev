from __future__ import annotations

import re
from typing import Any, Callable

from fastapi import status

from app.schemas.gene_viewer import (
    GeneViewerResponse,
    ProteinAlphaMissenseHeatmap,
    ProteinAlphaMissenseResidue,
)
from app.schemas.protein_annotation import ProteinAnnotationRequest
from app.services.alphamissense_local import AlphaMissenseLocalAdapter
from app.services.gene_viewer_errors import (
    GENE_VIEWER_PROVIDER_MALFORMED,
    GeneViewerError,
)
from app.services.gene_viewer_models import SourceTranscriptExon, SourceTranscriptModel
from app.services.gene_viewer_utils import (
    clean_dna as _clean_dna,
    dedupe_warnings as _dedupe_warnings,
)
from app.services.gene_viewer_variants import VariantProjection
from app.services.protein_annotation import (
    ProteinAnnotationService,
    protein_features_from_domain_track,
)
from app.services.variant_applied_model import build_protein_product_effect


def hydrate_response_with_record_protein_track(
    *,
    response: GeneViewerResponse,
    record: dict[str, Any],
    protein_annotation_service: ProteinAnnotationService | None,
) -> None:
    if protein_annotation_service is None:
        return
    coding_dna = coding_dna_from_record(record)
    if coding_dna is None:
        return
    track = protein_annotation_service.annotate(
        ProteinAnnotationRequest(
            sequence=coding_dna,
            input_type="coding_dna",
            sequence_label=(
                f"{str(record.get('gene') or '').upper()} "
                f"{str(record.get('transcript') or '').strip()} reference"
            ).strip(),
            gene_symbol=str(record.get("gene") or "").upper() or None,
            transcript=str(record.get("transcript") or "").strip() or None,
            use_cache=True,
            allow_run=False,
        )
    )
    response.tracks.protein_features = protein_features_from_domain_track(
        response.tracks.protein_features,
        track,
    )
    merged_track = response.tracks.protein_features.domain_track
    if merged_track is not None and merged_track.status in {"available", "cache_hit", "partial"}:
        warning = "protein_domain_track_from_local_cache"
    else:
        warning = f"protein_domain_track_unavailable:{track.fail_closed_reason or track.status}"
    response.provenance.warnings = _dedupe_warnings([*response.provenance.warnings, warning])


def hydrate_response_with_source_protein_track(
    *,
    response: GeneViewerResponse,
    transcript_source: SourceTranscriptModel,
    protein_annotation_service: ProteinAnnotationService | None,
    sequence_for_exon: Callable[[SourceTranscriptExon], str],
) -> None:
    if protein_annotation_service is None:
        return
    try:
        coding_dna = coding_dna_from_source_transcript(
            transcript_source,
            sequence_for_exon=sequence_for_exon,
        )
    except GeneViewerError as exc:
        response.provenance.warnings = _dedupe_warnings(
            [
                *response.provenance.warnings,
                f"protein_domain_track_unavailable:{exc.code}",
            ]
        )
        return
    except Exception as exc:
        response.provenance.warnings = _dedupe_warnings(
            [
                *response.provenance.warnings,
                f"protein_domain_track_unavailable:{type(exc).__name__}",
            ]
        )
        return
    if coding_dna is None:
        response.provenance.warnings = _dedupe_warnings(
            [
                *response.provenance.warnings,
                "protein_domain_track_unavailable:source_cds_sequence_missing",
            ]
        )
        return

    try:
        track = protein_annotation_service.annotate(
            ProteinAnnotationRequest(
                sequence=coding_dna,
                input_type="coding_dna",
                sequence_label=(
                    f"{transcript_source.gene.upper()} "
                    f"{transcript_source.transcript} reference CDS"
                ).strip(),
                gene_symbol=transcript_source.gene.upper(),
                transcript=transcript_source.transcript,
                use_cache=True,
                allow_run=False,
            )
        )
    except Exception as exc:
        response.provenance.warnings = _dedupe_warnings(
            [
                *response.provenance.warnings,
                f"protein_domain_track_unavailable:{type(exc).__name__}",
            ]
        )
        return

    response.tracks.protein_features = protein_features_from_domain_track(
        response.tracks.protein_features,
        track,
    )
    if track.status in {"available", "cache_hit", "partial"}:
        warning = "protein_domain_track_from_local_cache"
    else:
        warning = "protein_domain_track_unavailable:" f"{track.fail_closed_reason or track.status}"
    response.provenance.warnings = _dedupe_warnings([*response.provenance.warnings, warning])


def coding_dna_from_source_transcript(
    source: SourceTranscriptModel,
    *,
    sequence_for_exon: Callable[[SourceTranscriptExon], str],
) -> str | None:
    sequence = "".join(
        _clean_dna(sequence_for_exon(exon))
        for exon in sorted(source.exons, key=lambda item: item.cds_start)
    )
    if not sequence or not re.fullmatch(r"[ACGTUN]+", sequence):
        return None
    return sequence


def hydrate_response_with_alphamissense_heatmap(
    *,
    response: GeneViewerResponse,
    variant: VariantProjection,
    transcript_source: SourceTranscriptModel,
    alphamissense_adapter: AlphaMissenseLocalAdapter | None,
    sequence_for_exon: Callable[[SourceTranscriptExon], str],
) -> None:
    if alphamissense_adapter is None:
        response.tracks.alphamissense_heatmap = ProteinAlphaMissenseHeatmap(
            status="unavailable",
            fail_closed_reason="alphamissense_adapter_unconfigured",
            protein_length=transcript_source.protein_length,
            aa_start=max(1, (variant.codon_number or 1) - 12),
            aa_end=variant.codon_number or 1,
            queried_aa=variant.codon_number,
            warnings=["alphamissense_adapter_unconfigured"],
        )
        response.provenance.warnings = _dedupe_warnings(
            [*response.provenance.warnings, "alphamissense_adapter_unconfigured"]
        )
        return
    try:
        coding_dna, genomic_positions = coding_dna_and_positions_from_source_transcript(
            transcript_source,
            sequence_for_exon=sequence_for_exon,
        )
    except GeneViewerError as exc:
        reason = f"alphamissense_heatmap_unavailable:{exc.code}"
        response.tracks.alphamissense_heatmap = ProteinAlphaMissenseHeatmap(
            status="unavailable",
            fail_closed_reason=exc.code,
            protein_length=transcript_source.protein_length,
            aa_start=max(1, (variant.codon_number or 1) - 12),
            aa_end=variant.codon_number or 1,
            queried_aa=variant.codon_number,
            warnings=[reason],
        )
        response.provenance.warnings = _dedupe_warnings([*response.provenance.warnings, reason])
        return
    queried_aa = variant.codon_number or max(1, (variant.cds_pos + 2) // 3)
    aa_start = max(1, queried_aa - 18)
    protein_length = transcript_source.protein_length or max(1, len(coding_dna) // 3)
    aa_end = min(protein_length, queried_aa + 18)
    heatmap = alphamissense_adapter.heatmap(
        chrom=transcript_source.chrom,
        genomic_strand=transcript_source.strand,
        coding_sequence=coding_dna,
        coding_genomic_positions=genomic_positions,
        protein_length=transcript_source.protein_length,
        aa_start=aa_start,
        aa_end=aa_end,
        queried_cds_pos=variant.cds_pos,
        queried_ref=variant.ref,
        queried_alt=variant.alt,
        queried_aa=queried_aa,
    )
    response.tracks.alphamissense_heatmap = ProteinAlphaMissenseHeatmap(
        status=heatmap.status,
        fail_closed_reason=heatmap.fail_closed_reason,
        protein_length=heatmap.protein_length,
        aa_start=heatmap.aa_start,
        aa_end=heatmap.aa_end,
        source_id=heatmap.source_id,
        source_release=heatmap.source_release,
        calibrated_method=heatmap.calibrated_method,
        queried_aa=heatmap.queried_aa,
        queried_score=heatmap.queried_score,
        queried_calibrated_label=heatmap.queried_calibrated_label,
        residues=[
            ProteinAlphaMissenseResidue(
                aa=item.aa,
                mean_score=item.mean_score,
                max_score=item.max_score,
                scored_variant_count=item.scored_variant_count,
            )
            for item in heatmap.residues
        ],
        warnings=list(heatmap.warnings),
    )
    response.provenance.warnings = _dedupe_warnings(
        [*response.provenance.warnings, *heatmap.warnings]
    )


def coding_dna_and_positions_from_source_transcript(
    source: SourceTranscriptModel,
    *,
    sequence_for_exon: Callable[[SourceTranscriptExon], str],
) -> tuple[str, tuple[int, ...]]:
    sequence_parts: list[str] = []
    positions: list[int] = []
    for exon in sorted(source.exons, key=lambda item: item.cds_start):
        sequence = _clean_dna(sequence_for_exon(exon))
        expected_len = exon.cds_end - exon.cds_start + 1
        if len(sequence) != expected_len:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_MALFORMED,
                message="AlphaMissense heatmap source CDS sequence length did not match exon span.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        start = min(exon.genomic_start, exon.genomic_end)
        end = max(exon.genomic_start, exon.genomic_end)
        exon_positions = (
            range(end, start - 1, -1) if source.strand == "-" else range(start, end + 1)
        )
        sequence_parts.append(sequence)
        positions.extend(exon_positions)
    coding_dna = "".join(sequence_parts)
    if not coding_dna or not re.fullmatch(r"[ACGTN]+", coding_dna):
        raise GeneViewerError(
            code=GENE_VIEWER_PROVIDER_MALFORMED,
            message="AlphaMissense heatmap source CDS sequence was missing or malformed.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    if len(coding_dna) != len(positions):
        raise GeneViewerError(
            code=GENE_VIEWER_PROVIDER_MALFORMED,
            message="AlphaMissense heatmap source CDS coordinate map was malformed.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    return coding_dna, tuple(positions)


def coding_dna_from_record(record: dict[str, Any]) -> str | None:
    sequence = "".join(
        str(exon.get("sequence") or "")
        for exon in sorted(
            [item for item in record.get("exons") or [] if isinstance(item, dict)],
            key=lambda item: int(item["cds_start"]),
        )
    ).upper()
    if not sequence or not re.fullmatch(r"[ACGTUN]+", sequence):
        return None
    return sequence


def set_windowed_protein_product(response: GeneViewerResponse, *, allele_mode: str) -> None:
    response.tracks.protein_product = build_protein_product_effect(
        variant=response.queried_variant,
        allele_mode=allele_mode,
        reference_protein_length=response.summary.protein_length,
        exons=[
            SourceTranscriptExon(
                number=segment.exon_number,
                cds_start=segment.cds_start,
                cds_end=segment.cds_end,
                genomic_start=segment.genomic_start or 0,
                genomic_end=segment.genomic_end or 0,
            )
            for segment in response.segments
            if (
                segment.kind == "exon"
                and segment.exon_number is not None
                and segment.cds_start is not None
                and segment.cds_end is not None
            )
        ],
    )
