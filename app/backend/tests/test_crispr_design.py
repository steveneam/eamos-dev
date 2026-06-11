from __future__ import annotations

import json
import subprocess

import pytest

from app.schemas.workbench import CrisprRequest
from app.services.crispr_design import (
    HSU_DISTANCE_PENALTY_CONSTANT,
    HSU_MISMATCH_PENALTIES,
    CrisprScoreRAdapter,
    CrisprScoreRBackedCrisprProvider,
    CrisprDesignInputError,
    LocalDeterministicCrisprProvider,
    discover_spcas9_pam_sites,
    hsu_off_target_cutting_score,
    hsu_specificity_score,
    inspect_crisprscore_r_runtime,
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
    assert "RuleSet1=unavailable" in response.guides[0].notes
    assert "RuleSet3=unavailable" in response.guides[0].notes
    assert "CRISPRscan=unavailable" in response.guides[0].notes
    assert "CRISPRater=unavailable" in response.guides[0].notes
    assert "MIT/CFD off-target" in response.guides[0].notes
    assert "Lindel frameshift=unavailable" in response.guides[0].notes
    assert "DeepHF/DeepCpf1/enPAM+GB=platform-gated Windows-unavailable" in response.guides[0].notes
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


def test_crisprscore_r_backed_provider_falls_back_when_rscript_is_unavailable(tmp_path) -> None:
    sequence = "TGGACAAGACAGTCGCCATTCGGTGCCTACATTCAAGAGAACAACGAA"
    payload = CrisprRequest(gene="RPE65", cdna="c.260A>G")
    provider = CrisprScoreRBackedCrisprProvider(
        scoring_adapter=CrisprScoreRAdapter(rscript_path=tmp_path / "missing-Rscript")
    )

    response = provider.design(payload, _context(sequence))
    fallback_response = LocalDeterministicCrisprProvider().design(payload, _context(sequence))

    assert response.guides
    assert response.guides[0].on_target_score == fallback_response.guides[0].on_target_score
    assert response.guides[0].off_target_score == fallback_response.guides[0].off_target_score
    assert "crisprScore R/Rscript provider unavailable" in response.guides[0].notes
    assert "Using local deterministic fallback" in response.guides[0].notes
    assert "RuleSet1=unavailable" in response.guides[0].notes
    assert "CFD=unavailable" in response.guides[0].notes
    assert "Lindel frameshift=unavailable" in response.guides[0].notes


def test_crisprscore_runtime_preflight_is_sanitized_when_rscript_is_missing(tmp_path) -> None:
    inspection = inspect_crisprscore_r_runtime(
        configured_provider="crisprscore_r",
        rscript_path=tmp_path / "missing-Rscript",
    )
    payload = inspection.to_sanitized_dict()

    assert payload["available"] is False
    assert payload["status"] == "unavailable"
    assert payload["checks"]["rscript"] is False
    assert payload["local_path_values_emitted"] is False
    assert str(tmp_path).lower() not in json.dumps(payload).lower()


def test_crisprscore_runtime_preflight_reports_score_family_readiness() -> None:
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        stdout = json.dumps(
            {
                "jsonlite_package": True,
                "crisprscore_package": True,
            }
        )
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    inspection = inspect_crisprscore_r_runtime(
        configured_provider="crisprscore_r",
        rscript_path=__file__,
        rule_set3_conda_env="ruleset3-env",
        runner=runner,
    )
    payload = inspection.to_sanitized_dict()

    assert calls
    assert payload["available"] is True
    assert payload["checks"]["jsonlite_package"] is True
    assert payload["score_families"]["ruleset1"]["available"] is True
    assert payload["score_families"]["ruleset3"]["available"] is True
    assert payload["score_families"]["lindel_frameshift"]["available"] is False
    assert payload["request_time_install_allowed"] is False


def test_crisprscore_r_backed_provider_applies_source_score_payload() -> None:
    sequence = "TGGACAAGACAGTCGCCATTCGGTGCCTACATTCAAGAGAACAACGAA"
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        payload = json.loads(kwargs["input"])
        assert len(payload["rows"][0]["spacer"]) == 20
        assert len(payload["rows"][0]["pam"]) == 3
        stdout = json.dumps(
            {
                "scores": [
                    {
                        "id": "0",
                        "ruleset1": 0.71,
                        "ruleset3": None,
                        "crisprscan": 0.63,
                        "crisprater": 0.52,
                        "mit_specificity": 0.91,
                        "cfd_specificity": 0.88,
                        "lindel_frameshift": None,
                        "warnings": ["RuleSet3 unavailable: conda environment is not configured"],
                    }
                ],
                "warnings": ["Lindel frameshift unavailable: conda environment is not configured"],
            }
        )
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    provider = CrisprScoreRBackedCrisprProvider(
        scoring_adapter=CrisprScoreRAdapter(
            rscript_path=__file__,
            runner=runner,
        )
    )

    response = provider.design(
        CrisprRequest(gene="RPE65", cdna="c.260A>G"),
        _context(sequence),
    )

    assert calls
    assert calls[0][0][1] == "--vanilla"
    guide = response.guides[0]
    assert guide.on_target_score == 71.0
    assert guide.off_target_score == 12.0
    assert "crisprScore R/Rscript source scores" in guide.notes
    assert "RuleSet1=71.0" in guide.notes
    assert "RuleSet3=unavailable" in guide.notes
    assert "CRISPRscan=63.0" in guide.notes
    assert "CRISPRater=52.0" in guide.notes
    assert "MIT=91.0 specificity" in guide.notes
    assert "CFD=88.0 specificity" in guide.notes
    assert "Primary on-target provider: RuleSet1" in guide.notes
    assert "primary off-target provider: CFD" in guide.notes
