from __future__ import annotations

import pytest

from app.schemas.workbench import CrisprRequest
from app.services.crispr_design import (
    HSU_DISTANCE_PENALTY_CONSTANT,
    HSU_MISMATCH_PENALTIES,
    CrisprDesignInputError,
    LocalDeterministicCrisprProvider,
    discover_spcas9_pam_sites,
    hsu_off_target_cutting_score,
    hsu_specificity_score,
)
from app.services.sequence_context import SequenceContext, unsupported_input_warning


def _context(sequence: str) -> SequenceContext:
    return SequenceContext(
        gene="RPE65",
        cdna="c.260A>G",
        transcript="NM_000329.3",
        transcript_hgvs="NM_000329.3:c.260A>G",
        query_kind="cdna",
        genome_build="GRCh38",
        genomic_hg38="1-68444869-T-C",
        strand="-",
        window_sequence=sequence,
        target_offset=min(28, max(0, len(sequence) - 1)),
        reference_base=sequence[min(28, max(0, len(sequence) - 1))],
        alternate_base="G",
        source="resolver",
    )


def test_spcas9_pam_discovery_covers_overlapping_plus_sites() -> None:
    sites = discover_spcas9_pam_sites("A" * 20 + "GGGG" + "T" * 20, strand_filter="plus")

    assert [(site.spacer, site.pam, site.strand, site.cut_position) for site in sites] == [
        ("A" * 20, "GGG", "+", 17),
        ("A" * 19 + "G", "GGG", "+", 18),
    ]
    assert all(len(site.deep_hf_context) == 21 for site in sites)


def test_spcas9_pam_discovery_maps_reverse_complement_sites_to_forward_offsets() -> None:
    sites = discover_spcas9_pam_sites("CCA" + "A" * 20, strand_filter="minus")

    assert len(sites) == 1
    site = sites[0]
    assert site.spacer == "T" * 20
    assert site.pam == "TGG"
    assert site.strand == "-"
    assert site.pam_start == 0
    assert site.pam_end == 3
    assert site.spacer_start == 3
    assert site.spacer_end == 23
    assert site.cut_position == 5
    assert site.deep_hf_context == "T" * 21


def test_hsu_off_target_cutting_score_uses_position_distance_and_count_penalties() -> None:
    spacer = "A" * 20
    one_mismatch = "A" * 5 + "C" + "A" * 14
    two_mismatches = "A" * 5 + "C" + "A" * 4 + "C" + "A" * 9

    expected_one = 100.0 * (1.0 - HSU_MISMATCH_PENALTIES[5])
    average_distance = 5
    distance_factor = 1.0 / ((((19 - average_distance) / 19) * HSU_DISTANCE_PENALTY_CONSTANT) + 1.0)
    expected_two = (
        100.0
        * (1.0 - HSU_MISMATCH_PENALTIES[5])
        * (1.0 - HSU_MISMATCH_PENALTIES[10])
        * distance_factor
        * 0.25
    )

    assert hsu_off_target_cutting_score(spacer, spacer) == 100.0
    assert hsu_off_target_cutting_score(spacer, one_mismatch) == pytest.approx(
        round(expected_one, 6)
    )
    assert hsu_off_target_cutting_score(spacer, two_mismatches) == pytest.approx(
        round(expected_two, 6)
    )


def test_hsu_specificity_score_aggregates_local_off_target_risk() -> None:
    assert hsu_specificity_score([]) == 100.0
    assert hsu_specificity_score([100.0]) == 50.0
    assert hsu_specificity_score([25.0, 25.0]) == pytest.approx(66.666667)


def test_local_deterministic_provider_returns_guides_and_source_backed_ssodn() -> None:
    sequence = "TGGACAAGACAGTCGCCATTCGGTGCCTACATTCAAGAGAACAACGAA"
    response = LocalDeterministicCrisprProvider().design(
        CrisprRequest(gene="RPE65", cdna="c.260A>G"),
        _context(sequence),
    )

    assert response.cas == "SpCas9"
    assert response.guides
    assert len(response.guides) <= 6
    assert response.guides[0].index == 1
    assert all(len(guide.guide) == 20 for guide in response.guides)
    assert all(len(guide.pam) == 3 for guide in response.guides)
    assert all(0.0 <= guide.on_target_score <= 100.0 for guide in response.guides)
    assert all(0.0 <= guide.off_target_score <= 100.0 for guide in response.guides)
    assert "not DeepHF" in response.guides[0].notes
    assert "not a genome-wide Bowtie/BWA" in response.guides[0].notes
    assert response.ssodn is not None
    left_length = response.ssodn.arm_lengths["left"]
    assert response.ssodn.reference_arm[left_length] == "A"
    assert response.ssodn.variant_arm[left_length] == "G"
    assert response.ssodn.edits_encoded == ["c.260A>G"]


def test_local_deterministic_provider_returns_empty_result_when_no_pam_exists() -> None:
    response = LocalDeterministicCrisprProvider().design(
        CrisprRequest(gene="RPE65", cdna="c.260A>G"),
        _context("ATATATATATATATATATATATATATATATATATAT"),
    )

    assert response.guides == []
    assert response.ssodn is None


def test_local_deterministic_provider_rejects_too_short_sequence_context() -> None:
    with pytest.raises(CrisprDesignInputError) as error:
        LocalDeterministicCrisprProvider().design(
            CrisprRequest(gene="RPE65", cdna="c.260A>G"),
            _context("ACGT" * 5),
        )

    assert error.value.code == unsupported_input_warning("sequence_too_short")
