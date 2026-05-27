from __future__ import annotations

from app.data_sources import LOCAL_HG38_2BIT_SOURCE_ID
from app.services.reference_genome import ReferenceGenomeStore
from app.services.sequence_window_model import (
    REFERENCE_ALLELE_MISMATCH,
    REFERENCE_WINDOW_UNAVAILABLE,
    UNSUPPORTED_VARIANT_ALLELE,
    LocalSequenceWindowBuilder,
)


def test_builds_reference_and_variant_window_for_resolved_snv() -> None:
    builder = LocalSequenceWindowBuilder(ReferenceGenomeStore(), flank_bp=4)

    context = builder.build(
        gene="RPE65",
        transcript="NM_000329.3",
        cdna_hgvs="NM_000329.3:c.260A>G",
        genomic_hg38="1-8-T-C",
        chrom="NC_000001.11",
        position=8,
        reference_allele="T",
        alternate_allele="C",
        strand="-",
    )

    assert context.warnings == ()
    assert context.unavailable_reason is None
    assert context.gene == "RPE65"
    assert context.transcript == "NM_000329.3"
    assert context.cdna_hgvs == "NM_000329.3:c.260A>G"
    assert context.genomic_hg38 == "1-8-T-C"
    assert context.reference_window is not None
    assert context.reference_window.chrom == "1"
    assert context.reference_window.start == 4
    assert context.reference_window.end == 12
    assert context.reference_window.strand == "-"
    assert context.reference_window.sequence == "TACGTACGT"
    assert context.reference_window.length == 9
    assert context.reference_base_check is not None
    assert context.reference_base_check.position == 8
    assert context.reference_base_check.expected_base == "T"
    assert context.reference_base_check.observed_base == "T"
    assert context.reference_base_check.expected_allele == "T"
    assert context.reference_base_check.observed_allele == "T"
    assert context.reference_base_check.matches is True
    assert context.variant_window is not None
    assert context.variant_window.change_type == "substitution"
    assert context.variant_window.reference_start_offset == 4
    assert context.variant_window.reference_end_offset_exclusive == 5
    assert context.variant_window.variant_start_offset == 4
    assert context.variant_window.variant_end_offset_exclusive == 5
    assert context.variant_window.applied_sequence == "TACGCACGT"
    assert (
        context.variant_window.flank_convention
        == "genomic_forward_1_based_inclusive_ref_allele_centered"
    )
    assert context.provenance is not None
    assert context.provenance.source_id == LOCAL_HG38_2BIT_SOURCE_ID
    assert context.provenance.reader == "fixture_json"


def test_builds_insertion_window_using_vcf_anchored_alleles() -> None:
    builder = LocalSequenceWindowBuilder(ReferenceGenomeStore(), flank_bp=2)

    context = builder.build(
        chrom="1",
        position=4,
        reference_allele="T",
        alternate_allele="TAA",
    )

    assert context.reference_window is not None
    assert context.reference_window.sequence == "CGTAC"
    assert context.reference_base_check is not None
    assert context.reference_base_check.matches is True
    assert context.variant_window is not None
    assert context.variant_window.change_type == "insertion"
    assert context.variant_window.applied_sequence == "CGTAAAC"
    assert context.variant_window.reference_start_offset == 2
    assert context.variant_window.reference_end_offset_exclusive == 3
    assert context.variant_window.variant_end_offset_exclusive == 5


def test_builds_deletion_window_using_vcf_anchored_alleles() -> None:
    builder = LocalSequenceWindowBuilder(ReferenceGenomeStore(), flank_bp=2)

    context = builder.build(
        chrom="chr1",
        position=4,
        reference_allele="TAC",
        alternate_allele="T",
    )

    assert context.reference_window is not None
    assert context.reference_window.sequence == "CGTACGT"
    assert context.reference_base_check is not None
    assert context.reference_base_check.expected_allele == "TAC"
    assert context.reference_base_check.observed_allele == "TAC"
    assert context.reference_base_check.matches is True
    assert context.variant_window is not None
    assert context.variant_window.change_type == "deletion"
    assert context.variant_window.applied_sequence == "CGTGT"
    assert context.variant_window.reference_start_offset == 2
    assert context.variant_window.reference_end_offset_exclusive == 5
    assert context.variant_window.variant_end_offset_exclusive == 3


def test_reference_allele_mismatch_fails_closed_without_variant_window() -> None:
    builder = LocalSequenceWindowBuilder(ReferenceGenomeStore(), flank_bp=4)

    context = builder.build(
        chrom="1",
        position=8,
        reference_allele="A",
        alternate_allele="G",
    )

    assert context.reference_window is not None
    assert context.reference_base_check is not None
    assert context.reference_base_check.expected_base == "A"
    assert context.reference_base_check.observed_base == "T"
    assert context.reference_base_check.matches is False
    assert context.reference_base_check.reason == REFERENCE_ALLELE_MISMATCH
    assert context.variant_window is None
    assert context.warnings == (REFERENCE_ALLELE_MISMATCH,)
    assert context.unavailable_reason == REFERENCE_ALLELE_MISMATCH


def test_unknown_chromosome_returns_unavailable_state() -> None:
    builder = LocalSequenceWindowBuilder(ReferenceGenomeStore(), flank_bp=4)

    context = builder.build(
        chrom="chr7",
        position=8,
        reference_allele="T",
        alternate_allele="C",
    )

    assert context.reference_window is None
    assert context.reference_base_check is None
    assert context.variant_window is None
    assert context.warnings == (f"{REFERENCE_WINDOW_UNAVAILABLE}:unknown_chromosome",)
    assert context.unavailable_reason == "unknown_chromosome"
    assert context.provenance is not None
    assert context.provenance.reader == "fixture_json"


def test_unsupported_allele_returns_unavailable_state_without_reference_read() -> None:
    builder = LocalSequenceWindowBuilder(ReferenceGenomeStore(), flank_bp=4)

    context = builder.build(
        chrom="1",
        position=8,
        reference_allele="T",
        alternate_allele="R",
    )

    assert context.reference_window is None
    assert context.reference_base_check is None
    assert context.variant_window is None
    assert context.warnings == (UNSUPPORTED_VARIANT_ALLELE,)
    assert context.unavailable_reason == UNSUPPORTED_VARIANT_ALLELE
    assert context.provenance is not None
