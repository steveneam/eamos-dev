from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.computational_calibration import (
    ACTIVE_PROFILE_BY_PREDICTOR,
    CALIBRATION_PROFILES,
    calibration_field_values,
    calibrate_predictor,
)


@pytest.mark.parametrize(
    ("score", "label", "code", "points"),
    [
        ("0.000", "BP4 Strong", "BP4", "-4"),
        ("0.016", "BP4 Strong", "BP4", "-4"),
        ("0.017", "BP4 Moderate", "BP4", "-2"),
        ("0.183", "BP4 Moderate", "BP4", "-2"),
        ("0.184", "BP4 Supporting", "BP4", "-1"),
        ("0.290", "BP4 Supporting", "BP4", "-1"),
        ("0.291", "Indeterminate", None, "0"),
        ("0.643", "Indeterminate", None, "0"),
        ("0.644", "PP3 Supporting", "PP3", "1"),
        ("0.772", "PP3 Supporting", "PP3", "1"),
        ("0.773", "PP3 Moderate", "PP3", "2"),
        ("0.931", "PP3 Moderate", "PP3", "2"),
        ("0.932", "PP3 Strong", "PP3", "4"),
        ("1.000", "PP3 Strong", "PP3", "4"),
    ],
)
def test_applied_revel_capped_profile_boundaries(
    score: str,
    label: str,
    code: str | None,
    points: str,
) -> None:
    calibration = calibrate_predictor("REVEL", score)

    assert calibration is not None
    assert calibration.calibration_id == "revel_pejaver_2022_capped"
    assert calibration.calibrated_label == label
    assert calibration.evidence_code == code
    assert calibration.evidence_points == Decimal(points)
    assert calibration.calibration_bucket is None


def test_empirical_revel_profile_preserves_distinct_minus_eight_interval() -> None:
    empirical = calibrate_predictor(
        "REVEL",
        "0.003",
        profile_id="revel_pejaver_2022_empirical",
    )
    capped = calibrate_predictor("REVEL", "0.003")

    assert empirical is not None
    assert capped is not None
    assert empirical.evidence_points == Decimal("-8")
    assert empirical.calibrated_label == "BP4 Very Strong"
    assert capped.evidence_points == Decimal("-4")


@pytest.mark.parametrize(
    ("score", "label", "code", "points"),
    [
        ("0.070", "BP4 3 points", "BP4", "-3"),
        ("0.071", "BP4 Moderate", "BP4", "-2"),
        ("0.099", "BP4 Moderate", "BP4", "-2"),
        ("0.100", "BP4 Supporting", "BP4", "-1"),
        ("0.169", "BP4 Supporting", "BP4", "-1"),
        ("0.170", "Indeterminate", None, "0"),
        ("0.791", "Indeterminate", None, "0"),
        ("0.792", "PP3 Supporting", "PP3", "1"),
        ("0.905", "PP3 Supporting", "PP3", "1"),
        ("0.906", "PP3 Moderate", "PP3", "2"),
        ("0.971", "PP3 Moderate", "PP3", "2"),
        ("0.972", "PP3 3 points", "PP3", "3"),
        ("0.989", "PP3 3 points", "PP3", "3"),
        ("0.990", "PP3 Strong", "PP3", "4"),
    ],
)
def test_alphamissense_peer_reviewed_bergquist_boundaries(
    score: str,
    label: str,
    code: str | None,
    points: str,
) -> None:
    calibration = calibrate_predictor("AlphaMissense", score)

    assert calibration is not None
    assert calibration.calibrated_label == label
    assert calibration.evidence_code == code
    assert calibration.evidence_points == Decimal(points)
    assert calibration.calibration_version == "doi:10.1016/j.gim.2025.101402"


@pytest.mark.parametrize(
    ("score", "label", "code", "points"),
    [
        ("-24.0", "PP3 Strong", "PP3", "4"),
        ("-23.9", "PP3 3 points", "PP3", "3"),
        ("-14.0", "PP3 3 points", "PP3", "3"),
        ("-13.9", "PP3 Moderate", "PP3", "2"),
        ("-12.2", "PP3 Moderate", "PP3", "2"),
        ("-12.1", "PP3 Supporting", "PP3", "1"),
        ("-10.7", "PP3 Supporting", "PP3", "1"),
        ("-10.6", "Indeterminate", None, "0"),
        ("-6.4", "Indeterminate", None, "0"),
        ("-6.3", "BP4 Supporting", "BP4", "-1"),
        ("-3.2", "BP4 Supporting", "BP4", "-1"),
        ("-3.1", "BP4 Moderate", "BP4", "-2"),
        ("8.7", "BP4 Moderate", "BP4", "-2"),
        ("8.8", "BP4 3 points", "BP4", "-3"),
    ],
)
def test_esm1b_peer_reviewed_bergquist_boundaries(
    score: str,
    label: str,
    code: str | None,
    points: str,
) -> None:
    calibration = calibrate_predictor("ESM1b", score)

    assert calibration is not None
    assert calibration.calibrated_label == label
    assert calibration.evidence_code == code
    assert calibration.evidence_points == Decimal(points)
    assert calibration.score_native_precision == Decimal("0.1")


@pytest.mark.parametrize(
    ("score", "points"),
    [
        ("0.016", "-4"),
        ("0.017", "-3"),
        ("0.052", "-3"),
        ("0.053", "-2"),
        ("0.878", "2"),
        ("0.879", "3"),
        ("0.931", "3"),
        ("0.932", "4"),
    ],
)
def test_revel_bergquist_profile_remains_separate_and_three_point_ready(
    score: str,
    points: str,
) -> None:
    calibration = calibrate_predictor(
        "REVEL",
        score,
        profile_id="revel_bergquist_2025_three_point",
    )

    assert calibration is not None
    assert calibration.evidence_points == Decimal(points)
    assert calibration.calibration_id == "revel_bergquist_2025_three_point"


def test_decimal_input_preserves_raw_score_and_records_quantization() -> None:
    calibration = calibrate_predictor("REVEL", Decimal("0.8224"))

    assert calibration is not None
    assert calibration.raw_score == Decimal("0.8224")
    assert calibration.calibration_normalized_score == Decimal("0.822")
    assert calibration.score_quantization_rule == "decimal_round_half_even_to_0.001"
    assert len(calibration.profile_checksum) == 64
    assert calibration.interval_lower == Decimal("0.773")
    assert calibration.interval_upper == Decimal("0.932")
    assert calibration.interval_lower_inclusive is True
    assert calibration.interval_upper_inclusive is False


@pytest.mark.parametrize("score", ["NaN", "Infinity", "-Infinity", "bad", True, None])
def test_non_finite_and_non_numeric_scores_fail_closed(score: object) -> None:
    assert calibrate_predictor("REVEL", score) is None


@pytest.mark.parametrize("score", ["-0.001", "1.001"])
def test_probability_scores_outside_native_domain_fail_closed(score: str) -> None:
    assert calibrate_predictor("REVEL", score) is None


def test_unknown_or_mismatched_profiles_fail_closed() -> None:
    assert calibrate_predictor("MetaLR", "0.9") is None
    assert calibrate_predictor("REVEL", "0.9", profile_id="esm1b_bergquist_2025") is None
    assert calibrate_predictor("REVEL", "0.9", profile_id="missing") is None


def test_null_fields_include_the_frozen_phase_zero_contract() -> None:
    fields = calibration_field_values("Unknown", "0.9")

    assert fields == {
        "calibrated_label": None,
        "calibration_bucket": None,
        "calibration_method": None,
        "calibration_version": None,
        "calibration_id": None,
        "calibration_profile_checksum": None,
        "calibration_normalized_score": None,
        "score_unit": None,
        "score_native_precision": None,
        "score_quantization_rule": None,
        "evidence_code": None,
        "evidence_points": None,
        "interval_lower": None,
        "interval_lower_inclusive": None,
        "interval_upper": None,
        "interval_upper_inclusive": None,
    }


def test_registry_and_active_selector_are_immutable() -> None:
    assert ACTIVE_PROFILE_BY_PREDICTOR["revel"] == "revel_pejaver_2022_capped"
    assert CALIBRATION_PROFILES["revel_pejaver_2022_empirical"].status == "published"
    assert CALIBRATION_PROFILES["revel_bergquist_2025_three_point"].status == ("future_point_ready")
    with pytest.raises(TypeError):
        ACTIVE_PROFILE_BY_PREDICTOR["revel"] = "other"  # type: ignore[index]
