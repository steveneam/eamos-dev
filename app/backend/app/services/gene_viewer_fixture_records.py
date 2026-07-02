from __future__ import annotations

from typing import Any

from app.schemas.gene_viewer import (
    GeneViewerRequest,
    ViewerProvenanceSource,
)
from app.services.gene_viewer_errors import (
    HTTP_UNPROCESSABLE_ENTITY,
    GeneViewerError,
)
from app.services.gene_viewer_models import (
    SourceTranscriptExon,
    SourceTranscriptIntron,
    SourceTranscriptModel,
)
from app.services.gene_viewer_utils import versionless as _versionless
from app.services.gene_viewer_variants import VariantProjection
from app.services.gene_viewer_window import TranscriptExon, TranscriptIntron, TranscriptModel
from app.services.sequence_context import NormalizedVariantQuery, unsupported_input_warning


def curated_fixture_record(
    *,
    fixture: dict[str, Any],
    query: NormalizedVariantQuery,
) -> dict[str, Any] | None:
    requested_transcript = _versionless(query.resolver_transcript or query.transcript or "")
    for record in fixture.get("records") or []:
        if not isinstance(record, dict):
            continue
        if str(record.get("gene") or "").upper() != query.gene:
            continue
        if str(record.get("cdna") or "") != query.hgvs:
            continue
        if not requested_transcript:
            return record
        aliases = [
            str(record.get("transcript") or ""),
            str(record.get("requested_transcript") or ""),
            *(str(alias) for alias in record.get("transcript_aliases") or []),
        ]
        if any(_versionless(alias) == requested_transcript for alias in aliases):
            return record
    return None


def validate_curated_fixture_window(
    *,
    payload: GeneViewerRequest,
    record: dict[str, Any],
) -> None:
    default_window = record.get("default_window") or {
        "kind": "around_variant",
        "cds_flank_bp": 120,
        "intron_flank_bp": 30,
    }
    if (
        payload.window.kind == default_window.get("kind")
        and payload.window.cds_start is None
        and payload.window.cds_end is None
        and payload.window.cds_flank_bp == default_window.get("cds_flank_bp")
        and payload.window.intron_flank_bp == default_window.get("intron_flank_bp")
    ):
        return
    code = unsupported_input_warning("fixture_window")
    raise GeneViewerError(
        code=code,
        message=(
            "Curated non-RPE65 gene viewer fixtures support the default "
            "around-variant window only."
        ),
        status_code=HTTP_UNPROCESSABLE_ENTITY,
        warnings=[code],
    )


def source_transcript_from_curated_fixture(record: dict[str, Any]) -> SourceTranscriptModel:
    return SourceTranscriptModel(
        gene=str(record["gene"]),
        transcript=str(record["transcript"]),
        chrom=str(record["chrom"]),
        strand=str(record.get("strand") or "unknown"),
        exons=tuple(
            SourceTranscriptExon(
                number=int(exon["number"]),
                cds_start=int(exon["cds_start"]),
                cds_end=int(exon["cds_end"]),
                genomic_start=int(exon["genomic_start"]),
                genomic_end=int(exon["genomic_end"]),
            )
            for exon in record.get("exons") or []
        ),
        introns=tuple(
            SourceTranscriptIntron(
                number=int(intron["number"]),
                genomic_start=int(intron["genomic_start"]),
                genomic_end=int(intron["genomic_end"]),
            )
            for intron in record.get("introns") or []
        ),
        ensembl_gene_id=optional_fixture_text(record.get("ensembl_gene_id")),
        transcript_aliases=tuple(str(alias) for alias in record.get("transcript_aliases") or []),
        species=str(record.get("species") or "human"),
        genome_build=str(record.get("genome_build") or "GRCh38"),
        gene_start=fixture_int_or_none(record.get("gene_start")),
        gene_end=fixture_int_or_none(record.get("gene_end")),
        gene_length=fixture_int_or_none(record.get("gene_length")),
        cds_length=fixture_int_or_none(record.get("cds_length")),
        protein_length=fixture_int_or_none(record.get("protein_length")),
        utr5_length=fixture_int_or_none(record.get("utr5_length")),
        utr3_length=fixture_int_or_none(record.get("utr3_length")),
        mrna_length=fixture_int_or_none(record.get("mrna_length")),
        translation_id=optional_fixture_text(record.get("translation_id")),
        warnings=tuple(str(warning) for warning in record.get("warnings") or []),
    )


def transcript_model_from_curated_fixture(record: dict[str, Any]) -> TranscriptModel:
    return TranscriptModel(
        gene=str(record["gene"]),
        transcript=str(record["transcript"]),
        chrom=str(record["chrom"]),
        strand=str(record.get("strand") or "unknown"),
        exons=tuple(
            TranscriptExon(
                number=int(exon["number"]),
                cds_start=int(exon["cds_start"]),
                cds_end=int(exon["cds_end"]),
                sequence=str(exon.get("sequence") or placeholder_sequence(exon)),
                genomic_start=int(exon["genomic_start"]),
                genomic_end=int(exon["genomic_end"]),
            )
            for exon in record.get("exons") or []
        ),
        introns=tuple(
            TranscriptIntron(
                number=int(intron["number"]),
                total_len=int(intron.get("total_len") or fixture_intron_length(intron)),
                five_prime_sequence=str(intron.get("five_prime_sequence") or ""),
                three_prime_sequence=str(intron.get("three_prime_sequence") or ""),
                genomic_start=int(intron["genomic_start"]),
                genomic_end=int(intron["genomic_end"]),
            )
            for intron in record.get("introns") or []
        ),
        ensembl_gene_id=optional_fixture_text(record.get("ensembl_gene_id")),
        transcript_aliases=tuple(str(alias) for alias in record.get("transcript_aliases") or []),
        species=str(record.get("species") or "human"),
        genome_build=str(record.get("genome_build") or "GRCh38"),
        gene_start=fixture_int_or_none(record.get("gene_start")),
        gene_end=fixture_int_or_none(record.get("gene_end")),
        gene_length=fixture_int_or_none(record.get("gene_length")),
        total_exons=len(record.get("exons") or []),
        cds_length=fixture_int_or_none(record.get("cds_length")),
        protein_length=fixture_int_or_none(record.get("protein_length")),
        utr5_length=fixture_int_or_none(record.get("utr5_length")),
        utr3_length=fixture_int_or_none(record.get("utr3_length")),
        mrna_length=fixture_int_or_none(record.get("mrna_length")),
    )


def variant_from_curated_fixture(record: dict[str, Any]) -> VariantProjection:
    variant = record.get("variant") or {}
    return VariantProjection(
        hgvs_c=str(variant["hgvs_c"]),
        cds_pos=int(variant["cds_pos"]),
        ref=str(variant["ref"]),
        alt=str(variant["alt"]),
        hgvs_p=optional_fixture_text(variant.get("hgvs_p")),
        genomic_hg38=optional_fixture_text(variant.get("genomic_hg38")),
        codon_number=fixture_int_or_none(variant.get("codon_number")),
        codon_offset=fixture_int_or_none(variant.get("codon_offset")),
        aa_ref=optional_fixture_text(variant.get("aa_ref")),
        aa_alt=optional_fixture_text(variant.get("aa_alt")),
        classification=str(variant.get("classification") or "unknown"),
    )


def curated_fixture_provenance_sources(
    *,
    record: dict[str, Any],
    fixture_version: str,
) -> list[ViewerProvenanceSource]:
    return [
        ViewerProvenanceSource(
            name="ensembl_rest_fixture",
            identifier=str(record.get("transcript") or ""),
            url="https://rest.ensembl.org",
            version=fixture_version or None,
        ),
        ViewerProvenanceSource(
            name="clinvar_gene_agnostic_stack",
            identifier=str(record.get("accession") or record.get("clinvar_variation_id") or ""),
            url=optional_fixture_text(record.get("source_url")),
            version=fixture_version or None,
        ),
    ]


def placeholder_sequence(exon: dict[str, Any]) -> str:
    return "N" * (int(exon["cds_end"]) - int(exon["cds_start"]) + 1)


def fixture_intron_length(intron: dict[str, Any]) -> int:
    return abs(int(intron["genomic_end"]) - int(intron["genomic_start"])) + 1


def fixture_int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def optional_fixture_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
