from __future__ import annotations

import pytest

from app.services.computational_calibration import calibration_field_values, calibrate_predictor


@pytest.mark.parametrize(
    ("score", "label", "bucket"),
    [
        (0.003, "Very strong benign", "Benign"),
        (0.016, "Strong benign", "Benign"),
        (0.183, "Moderate benign", "Likely benign"),
        (0.290, "Supporting benign", "Likely benign"),
        (0.500, "Indeterminate", "VUS"),
        (0.644, "Supporting damaging", "Likely pathogenic"),
        (0.773, "Moderate damaging", "Likely pathogenic"),
        (0.932, "Strong damaging", "Pathogenic"),
    ],
)
def test_revel_pejaver_boundaries(score: float, label: str, bucket: str) -> None:
    calibration = calibrate_predictor("REVEL", score)

    assert calibration is not None
    assert calibration.calibrated_label == label
    assert calibration.calibration_bucket == bucket
    assert calibration.calibration_method == "Pejaver 2022 / ClinGen SVI PP3/BP4"
    assert calibration.calibration_version == "PMID:36413997"


@pytest.mark.parametrize(
    ("name", "score", "bucket"),
    [
        ("CADD PHRED", 23.4, "VUS"),
        ("CADD", 28.1, "Likely pathogenic"),
        ("SpliceAI", 0.12, "VUS"),
        ("SpliceAI", 0.5, "Pathogenic"),
    ],
)
def test_calibrates_named_policy_engines(name: str, score: float, bucket: str) -> None:
    calibration = calibrate_predictor(name, score)

    assert calibration is not None
    assert calibration.calibration_bucket == bucket


@pytest.mark.parametrize("name", ["MetaLR", "PrimateAI-3D", "phyloP100way", "Unknown"])
def test_unknown_or_unapproved_engines_return_explicit_null_fields(name: str) -> None:
    assert calibrate_predictor(name, 0.9) is None
    assert calibration_field_values(name, 0.9) == {
        "calibrated_label": None,
        "calibration_bucket": None,
        "calibration_method": None,
        "calibration_version": None,
    }


def test_non_numeric_scores_return_explicit_null_fields() -> None:
    assert calibration_field_values("REVEL", "not-a-number") == {
        "calibrated_label": None,
        "calibration_bucket": None,
        "calibration_method": None,
        "calibration_version": None,
    }
