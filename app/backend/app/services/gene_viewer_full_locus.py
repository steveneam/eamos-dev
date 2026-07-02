from __future__ import annotations

import re
from typing import Any

from fastapi import status

from app.schemas.gene_viewer import (
    ClinvarVariant,
    ExonVariantDensity,
    GeneViewerRequest,
    GeneViewerResponse,
    QueriedVariant,
    ViewerCodonStart,
    ViewerCoordinateMapRange,
    ViewerFeatureInterval,
    ViewerFullLocus,
    ViewerGenomicLocus,
    ViewerIdentity,
    ViewerLocus,
    ViewerProvenance,
    ViewerProvenanceSource,
    ViewerRenderingHints,
    ViewerSequences,
    ViewerSummary,
    ViewerTracks,
    ViewerTranscriptProjection,
    ViewerTranscriptProjectionInterval,
    ViewerWindow,
)
from app.services.gene_viewer_errors import (
    GENE_VIEWER_PROVIDER_MALFORMED,
    HTTP_UNPROCESSABLE_ENTITY,
    GeneViewerError,
    raise_unsupported_gene_viewer_input as _raise_unsupported,
)
from app.services.gene_viewer_fixture_records import (
    curated_fixture_provenance_sources,
    curated_fixture_record,
    fixture_int_or_none,
    placeholder_sequence,
    source_transcript_from_curated_fixture,
    variant_from_curated_fixture,
)
from app.services.gene_viewer_utils import (
    dedupe_warnings as _dedupe_warnings,
    reverse_complement as _reverse_complement,
)
from app.services.gene_viewer_variants import VariantProjection
from app.services.gene_viewer_window import (
    _raise_reference_mismatch,
    _raise_variant_outside_window,
    _schema_strand,
)
from app.services.sequence_context import NormalizedVariantQuery, unsupported_input_warning
from app.services.variant_applied_model import build_protein_product_effect

FULL_GENE_FIXTURE_VERSION = "2026-05-28-fgv-002-full-gene-fixtures-v1"
RPE65_FULL_GENE_EXON_SCAFFOLD: tuple[tuple[int, int, int, int], ...] = (
    (1, 1, 24, 113),
    (2, 25, 88, 64),
    (3, 89, 231, 143),
    (4, 232, 324, 93),
    (5, 325, 432, 108),
    (6, 433, 533, 101),
    (7, 534, 660, 127),
    (8, 661, 770, 110),
    (9, 771, 884, 114),
    (10, 885, 988, 104),
    (11, 989, 1130, 142),
    (12, 1131, 1276, 146),
    (13, 1277, 1452, 176),
    (14, 1453, 1602, 1366),
)
RPE65_FULL_GENE_INTRON_LENGTHS: dict[int, int] = {
    1: 1812,
    2: 661,
    3: 1240,
    4: 982,
    5: 753,
    6: 1504,
    7: 921,
    8: 1082,
    9: 787,
    10: 1342,
    11: 1155,
    12: 984,
    13: 823,
}
RPE65_KNOWN_EXON_COORDS: dict[int, tuple[int, int]] = {
    3: (68446200, 68446342),
    4: (68444805, 68444897),
    5: (68443000, 68443107),
}


def full_gene_fixture_response(
    *,
    payload: GeneViewerRequest,
    query: NormalizedVariantQuery,
    fixture: dict[str, Any],
    rpe65_window: dict[str, Any],
) -> GeneViewerResponse:
    if payload.allele_mode != "reference":
        _raise_unsupported(
            "full_gene_variant_mode",
            "Full-gene fixture payloads currently expose a reference locus with a queried variant pin.",
        )

    if query.gene == "RPE65" and query.hgvs == "c.260A>G":
        record = _rpe65_full_gene_record(rpe65_window)
    else:
        record = curated_fixture_record(fixture=fixture, query=query)
    if record is None:
        code = unsupported_input_warning("fixture")
        raise GeneViewerError(
            code=code,
            message=(
                "Offline full-gene fixtures are available for RPE65 c.260A>G "
                "and curated ClinVar-stack transcript-model cases."
            ),
            status_code=HTTP_UNPROCESSABLE_ENTITY,
            warnings=[code],
        )
    return _full_gene_response_from_record(
        payload=payload,
        record=record,
        fixture_version=str(fixture.get("version") or FULL_GENE_FIXTURE_VERSION),
    )


def _full_gene_response_from_record(
    *,
    payload: GeneViewerRequest,
    record: dict[str, Any],
    fixture_version: str,
) -> GeneViewerResponse:
    variant = variant_from_curated_fixture(record)
    _validate_full_gene_variant_reference(record=record, variant=variant)
    source = source_transcript_from_curated_fixture(record)
    gene_start = source.gene_start
    gene_end = source.gene_end
    if gene_start is None or gene_end is None or gene_start > gene_end:
        raise GeneViewerError(
            code=GENE_VIEWER_PROVIDER_MALFORMED,
            message="Full-gene fixture record must include valid gene_start and gene_end.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )

    locus_sequence = _build_full_locus_sequence(record=record, variant=variant)
    locus_length = len(locus_sequence)
    cds_start = min(exon.cds_start for exon in source.exons)
    cds_end = max(exon.cds_end for exon in source.exons)
    cds_to_genomic = _cds_to_genomic_map(record=record)
    genomic_variant = _genomic_variant_parts(variant.genomic_hg38)
    variant_position = genomic_variant[1] if genomic_variant is not None else None
    exon_number = next(
        (exon.number for exon in source.exons if exon.cds_start <= variant.cds_pos <= exon.cds_end),
        None,
    )
    transcript_projection = ViewerTranscriptProjection(
        transcript=source.transcript,
        strand=_schema_strand(source.strand),
        intervals=_full_locus_projection_intervals(record=record),
        coordinate_map=_full_locus_coordinate_map(record=record),
        codon_starts=_full_locus_codon_starts(
            cds_to_genomic=cds_to_genomic,
            cds_length=source.cds_length or cds_end,
        ),
    )

    response = GeneViewerResponse(
        identity=ViewerIdentity(
            gene=source.gene,
            ensembl_gene_id=source.ensembl_gene_id,
            requested_transcript=payload.transcript,
            resolved_transcript=source.transcript,
            transcript_aliases=list(source.transcript_aliases),
            species=source.species,
            genome_build=source.genome_build,
        ),
        locus=ViewerLocus(
            chrom=source.chrom,
            gene_start=gene_start,
            gene_end=gene_end,
            strand=_schema_strand(source.strand),
        ),
        summary=ViewerSummary(
            gene_length=locus_length,
            total_exons=len(source.exons),
            cds_length=source.cds_length,
            protein_length=source.protein_length,
            utr5_length=source.utr5_length,
            utr3_length=source.utr3_length,
            mrna_length=source.mrna_length,
        ),
        window=ViewerWindow(
            kind="full_gene",
            basis="genomic_locus",
            cds_start=cds_start,
            cds_end=cds_end,
            cds_flank_bp=payload.window.cds_flank_bp,
            intron_flank_bp=payload.window.intron_flank_bp,
            display_cds_start=cds_start,
            display_cds_end=cds_end,
            total_display_bases=locus_length,
            display_genomic_start=gene_start,
            display_genomic_end=gene_end,
            total_locus_bases=locus_length,
        ),
        segments=[],
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
            allele_mode="reference",
            reference_window_sequence="",
            display_window_sequence="",
            applied_variant=None,
        ),
        tracks=ViewerTracks(
            clinvar_variants=[
                ClinvarVariant(
                    cds_pos=variant.cds_pos,
                    hgvs_c=variant.hgvs_c,
                    hgvs_p=variant.hgvs_p,
                    classification=variant.classification,
                    clinvar_id=str(
                        record.get("accession") or record.get("clinvar_variation_id") or ""
                    ),
                    queried=True,
                )
            ],
            exon_density=(
                [ExonVariantDensity(exon_number=exon_number, variant_count=1)]
                if exon_number is not None
                else []
            ),
            protein_product=build_protein_product_effect(
                variant=variant,
                allele_mode="reference",
                reference_protein_length=source.protein_length,
                exons=source.exons,
            ),
        ),
        transcript_projection=transcript_projection,
        full_locus=ViewerFullLocus(
            locus=ViewerGenomicLocus(
                chrom=source.chrom,
                start=gene_start,
                end=gene_end,
                strand=_schema_strand(source.strand),
                genome_build=source.genome_build,
                sequence=locus_sequence,
            ),
            transcript_projection=transcript_projection,
            feature_intervals=_full_locus_feature_intervals(
                record=record,
                variant=variant,
                gene_start=gene_start,
                gene_end=gene_end,
                variant_position=variant_position,
            ),
            rendering_hints=ViewerRenderingHints(
                orientation=(
                    "genomic_reverse" if _schema_strand(source.strand) == "-" else "genomic_forward"
                ),
                row_coordinate_policy="genomic",
                bases_per_row_min=80,
                bases_per_row_max=140,
                max_visual_density=locus_length,
                base_color_scheme="none",
                amino_acid_color_scheme="biochemical",
            ),
        ),
        provenance=ViewerProvenance(
            sources=[
                *curated_fixture_provenance_sources(
                    record=record,
                    fixture_version=fixture_version,
                ),
                ViewerProvenanceSource(
                    name="eamos_full_gene_fixture",
                    identifier=source.transcript,
                    version=FULL_GENE_FIXTURE_VERSION,
                ),
            ],
            warnings=_dedupe_warnings(
                [
                    *[str(warning) for warning in record.get("warnings") or []],
                    "full_gene_fixture_hydrated",
                    "full_gene_intronic_sequence_is_deterministic_fixture",
                ]
            ),
        ),
    )
    return response


def _rpe65_full_gene_record(window_payload: dict[str, Any]) -> dict[str, Any]:
    response = GeneViewerResponse(**window_payload)
    coords = _rpe65_full_gene_exon_coordinates()
    variant = response.queried_variant
    exons: list[dict[str, Any]] = []
    exon4_sequence = next(
        (
            segment.sequence
            for segment in response.segments
            if segment.kind == "exon" and segment.exon_number == 4
        ),
        "",
    )
    for number, cds_start, cds_end, length in RPE65_FULL_GENE_EXON_SCAFFOLD:
        sequence = (
            exon4_sequence
            if number == 4 and len(exon4_sequence) == length
            else _deterministic_transcript_sequence("RPE65", number, length)
        )
        if cds_start <= variant.cds_pos <= cds_end:
            offset = variant.cds_pos - cds_start
            sequence = f"{sequence[:offset]}{variant.ref}{sequence[offset + 1:]}"
        genomic_start, genomic_end = coords[number]
        exons.append(
            {
                "number": number,
                "cds_start": cds_start,
                "cds_end": cds_end,
                "genomic_start": genomic_start,
                "genomic_end": genomic_end,
                "sequence": sequence,
            }
        )

    introns: list[dict[str, Any]] = []
    for previous, current in zip(exons, exons[1:], strict=False):
        intron_start = int(current["genomic_end"]) + 1
        intron_end = int(previous["genomic_start"]) - 1
        introns.append(
            {
                "number": int(previous["number"]),
                "genomic_start": intron_start,
                "genomic_end": intron_end,
                "total_len": intron_end - intron_start + 1,
            }
        )

    clinvar_id = next(
        (
            item.clinvar_id
            for item in response.tracks.clinvar_variants
            if item.queried and item.clinvar_id
        ),
        "VCV001421454",
    )
    return {
        "gene": response.identity.gene,
        "cdna": response.queried_variant.hgvs_c,
        "transcript": response.identity.resolved_transcript,
        "requested_transcript": response.identity.requested_transcript,
        "transcript_aliases": response.identity.transcript_aliases,
        "clinical_significance": "Uncertain significance",
        "clinvar_variation_id": clinvar_id.removeprefix("VCV"),
        "accession": clinvar_id,
        "chrom": response.locus.chrom.removeprefix("chr"),
        "strand": response.locus.strand,
        "ensembl_gene_id": response.identity.ensembl_gene_id,
        "species": response.identity.species,
        "genome_build": response.identity.genome_build,
        "gene_start": response.locus.gene_start,
        "gene_end": response.locus.gene_end,
        "gene_length": response.summary.gene_length,
        "cds_length": response.summary.cds_length,
        "protein_length": response.summary.protein_length,
        "utr5_length": response.summary.utr5_length,
        "utr3_length": response.summary.utr3_length,
        "mrna_length": response.summary.mrna_length,
        "variant": response.queried_variant.model_dump(),
        "exons": exons,
        "introns": introns,
        "warnings": [
            *response.provenance.warnings,
            "rpe65_full_gene_synthetic_fixture_scaffold",
        ],
    }


def _rpe65_full_gene_exon_coordinates() -> dict[int, tuple[int, int]]:
    coords = dict(RPE65_KNOWN_EXON_COORDS)
    lengths = {
        number: length for number, _cds_start, _cds_end, length in RPE65_FULL_GENE_EXON_SCAFFOLD
    }
    for number in range(2, 0, -1):
        _next_start, next_end = coords[number + 1]
        intron_len = RPE65_FULL_GENE_INTRON_LENGTHS[number]
        start = next_end + intron_len + 1
        coords[number] = (start, start + lengths[number] - 1)
    for number in range(6, 15):
        previous_start, _previous_end = coords[number - 1]
        intron_len = RPE65_FULL_GENE_INTRON_LENGTHS[number - 1]
        end = previous_start - intron_len - 1
        coords[number] = (end - lengths[number] + 1, end)
    return coords


def _full_locus_projection_intervals(
    record: dict[str, Any],
) -> list[ViewerTranscriptProjectionInterval]:
    strand = _schema_strand(str(record.get("strand") or "unknown"))
    utr5_length = fixture_int_or_none(record.get("utr5_length")) or 0
    cds_length = fixture_int_or_none(record.get("cds_length")) or 0
    intervals: list[ViewerTranscriptProjectionInterval] = []
    intervals.extend(_full_locus_utr_intervals(record=record, utr5_length=utr5_length))
    for exon in _record_exons(record):
        exon_number = int(exon["number"])
        cds_start = int(exon["cds_start"])
        cds_end = int(exon["cds_end"])
        genomic_start = int(exon["genomic_start"])
        genomic_end = int(exon["genomic_end"])
        protein_start, protein_end = _protein_range(cds_start, cds_end)
        intervals.append(
            ViewerTranscriptProjectionInterval(
                id=f"{str(record['gene']).lower()}-exon-{exon_number}",
                kind="exon",
                label=f"Exon {exon_number}",
                genomic_start=genomic_start,
                genomic_end=genomic_end,
                strand=strand,
                exon_number=exon_number,
                cdna_start=utr5_length + cds_start,
                cdna_end=utr5_length + cds_end,
                cds_start=cds_start,
                cds_end=cds_end,
                protein_start=protein_start,
                protein_end=protein_end,
            )
        )
        intervals.append(
            ViewerTranscriptProjectionInterval(
                id=f"{str(record['gene']).lower()}-cds-{exon_number}",
                kind="cds",
                label=f"CDS exon {exon_number}",
                genomic_start=genomic_start,
                genomic_end=genomic_end,
                strand=strand,
                exon_number=exon_number,
                cdna_start=utr5_length + cds_start,
                cdna_end=utr5_length + cds_end,
                cds_start=cds_start,
                cds_end=cds_end,
                protein_start=protein_start,
                protein_end=protein_end,
            )
        )
    for intron in _record_introns(record):
        intron_number = int(intron["number"])
        intervals.append(
            ViewerTranscriptProjectionInterval(
                id=f"{str(record['gene']).lower()}-intron-{intron_number}",
                kind="intron",
                label=f"Intron {intron_number}",
                genomic_start=int(intron["genomic_start"]),
                genomic_end=int(intron["genomic_end"]),
                strand=strand,
                intron_number=intron_number,
            )
        )
    intervals.extend(
        _full_locus_utr3_intervals(
            record=record,
            utr5_length=utr5_length,
            cds_length=cds_length,
        )
    )
    return intervals


def _full_locus_utr_intervals(
    *,
    record: dict[str, Any],
    utr5_length: int,
) -> list[ViewerTranscriptProjectionInterval]:
    if utr5_length <= 0:
        return []
    gene_start = int(record["gene_start"])
    gene_end = int(record["gene_end"])
    strand = _schema_strand(str(record.get("strand") or "unknown"))
    genomic_start, genomic_end = (
        (gene_end - utr5_length + 1, gene_end)
        if strand == "-"
        else (gene_start, gene_start + utr5_length - 1)
    )
    return [
        ViewerTranscriptProjectionInterval(
            id=f"{str(record['gene']).lower()}-utr5",
            kind="utr5",
            label="5' UTR",
            genomic_start=genomic_start,
            genomic_end=genomic_end,
            strand=strand,
            cdna_start=1,
            cdna_end=utr5_length,
        )
    ]


def _full_locus_utr3_intervals(
    *,
    record: dict[str, Any],
    utr5_length: int,
    cds_length: int,
) -> list[ViewerTranscriptProjectionInterval]:
    utr3_length = fixture_int_or_none(record.get("utr3_length")) or 0
    if utr3_length <= 0:
        return []
    gene_start = int(record["gene_start"])
    gene_end = int(record["gene_end"])
    strand = _schema_strand(str(record.get("strand") or "unknown"))
    genomic_start, genomic_end = (
        (gene_start, gene_start + utr3_length - 1)
        if strand == "-"
        else (gene_end - utr3_length + 1, gene_end)
    )
    cdna_start = utr5_length + cds_length + 1
    return [
        ViewerTranscriptProjectionInterval(
            id=f"{str(record['gene']).lower()}-utr3",
            kind="utr3",
            label="3' UTR",
            genomic_start=genomic_start,
            genomic_end=genomic_end,
            strand=strand,
            cdna_start=cdna_start,
            cdna_end=cdna_start + utr3_length - 1,
        )
    ]


def _full_locus_coordinate_map(record: dict[str, Any]) -> list[ViewerCoordinateMapRange]:
    utr5_length = fixture_int_or_none(record.get("utr5_length")) or 0
    return [
        ViewerCoordinateMapRange(
            genomic_start=int(exon["genomic_start"]),
            genomic_end=int(exon["genomic_end"]),
            cdna_start=utr5_length + int(exon["cds_start"]),
            cdna_end=utr5_length + int(exon["cds_end"]),
            cds_start=int(exon["cds_start"]),
            cds_end=int(exon["cds_end"]),
            protein_start=_protein_range(int(exon["cds_start"]), int(exon["cds_end"]))[0],
            protein_end=_protein_range(int(exon["cds_start"]), int(exon["cds_end"]))[1],
        )
        for exon in _record_exons(record)
    ]


def _full_locus_codon_starts(
    *,
    cds_to_genomic: dict[int, int],
    cds_length: int,
) -> list[ViewerCodonStart]:
    codons: list[ViewerCodonStart] = []
    for cds_start in range(1, cds_length + 1, 3):
        genomic_positions = [
            cds_to_genomic[position]
            for position in range(cds_start, min(cds_start + 3, cds_length + 1))
            if position in cds_to_genomic
        ]
        if not genomic_positions:
            continue
        protein_position = (cds_start + 2) // 3
        codons.append(
            ViewerCodonStart(
                codon_number=protein_position,
                cds_start=cds_start,
                protein_position=protein_position,
                genomic_start=genomic_positions[0],
                genomic_positions=genomic_positions,
            )
        )
    return codons


def _full_locus_feature_intervals(
    *,
    record: dict[str, Any],
    variant: VariantProjection,
    gene_start: int,
    gene_end: int,
    variant_position: int | None,
) -> list[ViewerFeatureInterval]:
    strand = _schema_strand(str(record.get("strand") or "unknown"))
    gene = str(record["gene"])
    features = [
        ViewerFeatureInterval(
            id=f"{gene.lower()}-gene",
            kind="gene",
            label=gene,
            coordinate_system="genomic",
            start=gene_start,
            end=gene_end,
            strand=strand,
            source="full_gene_fixture",
        ),
        ViewerFeatureInterval(
            id=f"{gene.lower()}-transcript",
            kind="transcript",
            label=str(record["transcript"]),
            coordinate_system="genomic",
            start=gene_start,
            end=gene_end,
            strand=strand,
            source="full_gene_fixture",
        ),
    ]
    if variant_position is not None:
        features.append(
            ViewerFeatureInterval(
                id=f"{gene.lower()}-queried-variant",
                kind="queried_variant",
                label=f"{gene} {variant.hgvs_c}",
                coordinate_system="genomic",
                start=variant_position,
                end=variant_position,
                strand=strand,
                source="clinvar_fixture",
                classification=variant.classification,
                metadata={
                    "hgvs_c": variant.hgvs_c,
                    "hgvs_p": variant.hgvs_p,
                    "cds_pos": variant.cds_pos,
                },
            )
        )
        features.append(
            ViewerFeatureInterval(
                id=f"{gene.lower()}-clinvar-queried",
                kind="clinvar",
                label=str(record.get("accession") or record.get("clinvar_variation_id") or ""),
                coordinate_system="genomic",
                start=variant_position,
                end=variant_position,
                strand=strand,
                source="clinvar_gene_agnostic_stack",
                classification=variant.classification,
                metadata={"queried": True},
            )
        )
    return features


def _build_full_locus_sequence(
    *,
    record: dict[str, Any],
    variant: VariantProjection,
) -> str:
    gene = str(record["gene"])
    chrom = str(record["chrom"]).removeprefix("chr")
    gene_start = int(record["gene_start"])
    gene_end = int(record["gene_end"])
    bases = [
        _deterministic_genomic_base(gene=gene, chrom=chrom, position=position)
        for position in range(gene_start, gene_end + 1)
    ]
    strand = _schema_strand(str(record.get("strand") or "unknown"))
    for exon in _record_exons(record):
        sequence = str(exon.get("sequence") or placeholder_sequence(exon)).upper()
        genomic_sequence = _reverse_complement(sequence) if strand == "-" else sequence
        start = int(exon["genomic_start"])
        offset = start - gene_start
        if offset < 0 or offset + len(genomic_sequence) > len(bases):
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_MALFORMED,
                message="Full-gene fixture exon lies outside the declared gene locus.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        bases[offset : offset + len(genomic_sequence)] = list(genomic_sequence)

    genomic_variant = _genomic_variant_parts(variant.genomic_hg38)
    if genomic_variant is not None:
        variant_chrom, variant_pos, genomic_ref, _genomic_alt = genomic_variant
        if variant_chrom != chrom or variant_pos < gene_start or variant_pos > gene_end:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_MALFORMED,
                message="Full-gene fixture variant locus is outside the declared gene locus.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        bases[variant_pos - gene_start] = genomic_ref
    return "".join(bases)


def _cds_to_genomic_map(record: dict[str, Any]) -> dict[int, int]:
    strand = _schema_strand(str(record.get("strand") or "unknown"))
    mapping: dict[int, int] = {}
    for exon in _record_exons(record):
        genomic_start = int(exon["genomic_start"])
        genomic_end = int(exon["genomic_end"])
        for offset, cds_pos in enumerate(range(int(exon["cds_start"]), int(exon["cds_end"]) + 1)):
            mapping[cds_pos] = genomic_end - offset if strand == "-" else genomic_start + offset
    return mapping


def _validate_full_gene_variant_reference(
    *,
    record: dict[str, Any],
    variant: VariantProjection,
) -> None:
    if not variant.ref:
        return
    exon = next(
        (
            item
            for item in _record_exons(record)
            if int(item["cds_start"]) <= variant.cds_pos <= int(item["cds_end"])
        ),
        None,
    )
    if exon is None:
        _raise_variant_outside_window(variant)
    sequence = str(exon.get("sequence") or placeholder_sequence(exon)).upper()
    offset = variant.cds_pos - int(exon["cds_start"])
    observed = sequence[offset : offset + len(variant.ref)]
    if observed != variant.ref.upper():
        _raise_reference_mismatch(variant)


def _record_exons(record: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        [exon for exon in record.get("exons") or [] if isinstance(exon, dict)],
        key=lambda exon: int(exon["cds_start"]),
    )


def _record_introns(record: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        [intron for intron in record.get("introns") or [] if isinstance(intron, dict)],
        key=lambda intron: int(intron["number"]),
    )


def _protein_range(cds_start: int, cds_end: int) -> tuple[int, int]:
    return ((cds_start + 2) // 3, (cds_end + 2) // 3)


def _genomic_variant_parts(value: str | None) -> tuple[str, int, str, str] | None:
    if not value:
        return None
    match = re.fullmatch(
        r"(?:chr)?(?P<chrom>[^-]+)-(?P<pos>\d+)-(?P<ref>[ACGTN]+)-(?P<alt>[ACGTN]+)",
        value,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return (
        match.group("chrom").removeprefix("chr"),
        int(match.group("pos")),
        match.group("ref").upper(),
        match.group("alt").upper(),
    )


def _deterministic_transcript_sequence(gene: str, exon_number: int, length: int) -> str:
    alphabet = "ACGT"
    offset = sum(ord(char) for char in gene) + exon_number
    return "".join(alphabet[(offset + index) % len(alphabet)] for index in range(length))


def _deterministic_genomic_base(*, gene: str, chrom: str, position: int) -> str:
    alphabet = "ACGT"
    offset = sum(ord(char) for char in f"{gene}:{chrom}") + position
    return alphabet[offset % len(alphabet)]
