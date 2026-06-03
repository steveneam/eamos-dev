from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

RampVerdict = Literal["Pathogenic", "Likely pathogenic", "VUS", "Likely benign", "Benign"]

PEJAVER_METHOD = "Pejaver 2022 / ClinGen SVI PP3/BP4"
PEJAVER_VERSION = "PMID:36413997"
SPLICE_METHOD = "Walker 2023 / ClinGen SVI splicing"
SPLICE_VERSION = "PMID:37352859"
BERGQUIST_METHOD = "Bergquist 2025 / ClinGen SVI PP3/BP4"
BERGQUIST_VERSION = "PMID:40084623"


@dataclass(frozen=True)
class PredictorCalibration:
    calibrated_label: str
    calibration_bucket: RampVerdict
    calibration_method: str
    calibration_version: str


def calibration_field_values(name: Any, score: Any) -> dict[str, str | None]:
    calibration = calibrate_predictor(name, score)
    if calibration is None:
        return {
            "calibrated_label": None,
            "calibration_bucket": None,
            "calibration_method": None,
            "calibration_version": None,
        }
    return {
        "calibrated_label": calibration.calibrated_label,
        "calibration_bucket": calibration.calibration_bucket,
        "calibration_method": calibration.calibration_method,
        "calibration_version": calibration.calibration_version,
    }


def calibrate_predictor(name: Any, score: Any) -> PredictorCalibration | None:
    normalized_name = _normalize_name(name)
    numeric_score = _optional_float(score)
    if normalized_name is None or numeric_score is None:
        return None

    if normalized_name == "revel":
        return _calibrate_revel(numeric_score)
    if normalized_name in {"cadd", "caddphred"}:
        return _calibrate_cadd_phred(numeric_score)
    if normalized_name == "primateai":
        return _calibrate_primateai(numeric_score)
    if normalized_name == "spliceai":
        return _calibrate_spliceai(numeric_score)
    if normalized_name == "alphamissense":
        return _calibrate_alphamissense(numeric_score)
    if normalized_name in {"esm1b", "esm1bllr"}:
        return _calibrate_esm1b(numeric_score)
    return None


def _calibrate_revel(score: float) -> PredictorCalibration:
    if score <= 0.003:
        return _pejaver("Very strong benign", "Benign")
    if score <= 0.016:
        return _pejaver("Strong benign", "Benign")
    if score <= 0.183:
        return _pejaver("Moderate benign", "Likely benign")
    if score <= 0.290:
        return _pejaver("Supporting benign", "Likely benign")
    if 0.644 <= score < 0.773:
        return _pejaver("Supporting damaging", "Likely pathogenic")
    if 0.773 <= score < 0.932:
        return _pejaver("Moderate damaging", "Likely pathogenic")
    if score >= 0.932:
        return _pejaver("Strong damaging", "Pathogenic")
    return _pejaver("Indeterminate", "VUS")


def _calibrate_cadd_phred(score: float) -> PredictorCalibration:
    if score <= 0.15:
        return _pejaver("Strong benign", "Benign")
    if score <= 17.3:
        return _pejaver("Moderate benign", "Likely benign")
    if score <= 22.7:
        return _pejaver("Supporting benign", "Likely benign")
    if 25.3 <= score < 28.1:
        return _pejaver("Supporting damaging", "Likely pathogenic")
    if score >= 28.1:
        return _pejaver("Moderate damaging", "Likely pathogenic")
    return _pejaver("Indeterminate", "VUS")


def _calibrate_primateai(score: float) -> PredictorCalibration:
    if score <= 0.362:
        return _pejaver("Moderate benign", "Likely benign")
    if score <= 0.483:
        return _pejaver("Supporting benign", "Likely benign")
    if 0.790 <= score < 0.867:
        return _pejaver("Supporting damaging", "Likely pathogenic")
    if score >= 0.867:
        return _pejaver("Moderate damaging", "Likely pathogenic")
    return _pejaver("Indeterminate", "VUS")


def _calibrate_spliceai(score: float) -> PredictorCalibration:
    if score >= 0.5:
        return PredictorCalibration(
            "Strong splice impact", "Pathogenic", SPLICE_METHOD, SPLICE_VERSION
        )
    if score >= 0.2:
        return PredictorCalibration(
            "Supporting splice impact",
            "Likely pathogenic",
            SPLICE_METHOD,
            SPLICE_VERSION,
        )
    if score < 0.1:
        return PredictorCalibration(
            "Moderate no-splice-impact",
            "Likely benign",
            SPLICE_METHOD,
            SPLICE_VERSION,
        )
    return PredictorCalibration("Indeterminate", "VUS", SPLICE_METHOD, SPLICE_VERSION)


def _calibrate_alphamissense(score: float) -> PredictorCalibration:
    if score <= 0.070:
        return _bergquist("BP4_Strong", "Benign")
    if score <= 0.099:
        return _bergquist("BP4_Moderate", "Likely benign")
    if score < 0.100:
        return _bergquist("Indeterminate", "VUS")
    if score <= 0.169:
        return _bergquist("PP3_Supporting", "Likely pathogenic")
    if score <= 0.791:
        return _bergquist("PP3_Moderate", "Likely pathogenic")
    if score <= 0.989:
        return _bergquist("PP3_Strong", "Pathogenic")
    return _bergquist("Indeterminate", "VUS")


def _calibrate_esm1b(score: float) -> PredictorCalibration:
    if score <= -14.0:
        return _bergquist("PP3_Strong", "Pathogenic")
    if score <= -12.2:
        return _bergquist("PP3_Moderate", "Likely pathogenic")
    if score <= -10.7:
        return _bergquist("PP3_Supporting", "Likely pathogenic")
    if score <= -6.4:
        return _bergquist("Indeterminate", "VUS")
    if score <= -3.2:
        return _bergquist("BP4_Supporting", "Likely benign")
    return _bergquist("BP4_Moderate", "Likely benign")


def _pejaver(label: str, bucket: RampVerdict) -> PredictorCalibration:
    return PredictorCalibration(label, bucket, PEJAVER_METHOD, PEJAVER_VERSION)


def _bergquist(label: str, bucket: RampVerdict) -> PredictorCalibration:
    return PredictorCalibration(label, bucket, BERGQUIST_METHOD, BERGQUIST_VERSION)


def _normalize_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if not text:
        return None
    return text.replace("-", "").replace("_", "").replace(" ", "")


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None
