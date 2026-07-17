from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Any, Literal, Mapping

EvidenceCode = Literal["PP3", "BP4", "SPLICE"]
ProfileStatus = Literal["published", "applied", "future_point_ready"]

PEJAVER_METHOD = "Pejaver 2022 / ClinGen SVI PP3/BP4"
PEJAVER_VERSION = "PMID:36413997"
PEJAVER_PUBLICATION = "https://pmc.ncbi.nlm.nih.gov/articles/PMC9748256/"
SPLICE_METHOD = "Walker 2023 / ClinGen SVI splicing"
SPLICE_VERSION = "PMID:37352859"
SPLICE_PUBLICATION = "https://pubmed.ncbi.nlm.nih.gov/37352859/"
BERGQUIST_METHOD = "Bergquist 2025 / ClinGen SVI PP3/BP4"
BERGQUIST_VERSION = "doi:10.1016/j.gim.2025.101402"
BERGQUIST_PUBLICATION = "https://doi.org/10.1016/j.gim.2025.101402"


@dataclass(frozen=True)
class CalibrationInterval:
    lower: Decimal | None
    lower_inclusive: bool
    upper: Decimal | None
    upper_inclusive: bool
    evidence_code: EvidenceCode | None
    evidence_points: Decimal
    evidence_label: str

    def contains(self, score: Decimal) -> bool:
        if self.lower is not None:
            if score < self.lower or (score == self.lower and not self.lower_inclusive):
                return False
        if self.upper is not None:
            if score > self.upper or (score == self.upper and not self.upper_inclusive):
                return False
        return True


@dataclass(frozen=True)
class PredictorCalibrationProfile:
    profile_id: str
    predictor_id: str
    calibration_version: str
    calibration_method: str
    publication_url: str
    score_unit: str
    native_precision: Decimal
    quantization_rule: str
    status: ProfileStatus
    intervals: tuple[CalibrationInterval, ...]
    minimum_score: Decimal | None = None
    maximum_score: Decimal | None = None

    @property
    def checksum(self) -> str:
        payload = {
            "profile_id": self.profile_id,
            "predictor_id": self.predictor_id,
            "calibration_version": self.calibration_version,
            "calibration_method": self.calibration_method,
            "publication_url": self.publication_url,
            "score_unit": self.score_unit,
            "native_precision": _canonical_decimal(self.native_precision),
            "quantization_rule": self.quantization_rule,
            "status": self.status,
            "minimum_score": _optional_decimal_text(self.minimum_score),
            "maximum_score": _optional_decimal_text(self.maximum_score),
            "intervals": [
                {
                    "lower": _optional_decimal_text(interval.lower),
                    "lower_inclusive": interval.lower_inclusive,
                    "upper": _optional_decimal_text(interval.upper),
                    "upper_inclusive": interval.upper_inclusive,
                    "evidence_code": interval.evidence_code,
                    "evidence_points": _canonical_decimal(interval.evidence_points),
                    "evidence_label": interval.evidence_label,
                }
                for interval in self.intervals
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PredictorCalibration:
    raw_score: Decimal
    calibration_normalized_score: Decimal
    calibrated_label: str
    evidence_code: EvidenceCode | None
    evidence_points: Decimal
    calibration_method: str
    calibration_version: str
    calibration_id: str
    profile_checksum: str
    score_unit: str
    score_native_precision: Decimal
    score_quantization_rule: str
    interval_lower: Decimal | None
    interval_lower_inclusive: bool
    interval_upper: Decimal | None
    interval_upper_inclusive: bool

    @property
    def calibration_bucket(self) -> None:
        """Retired compatibility property.

        A predictor contributes one PP3/BP4 evidence line. It is not itself a
        final Pathogenic, VUS, or Benign classification.
        """

        return None


def _interval(
    lower: str | None,
    lower_inclusive: bool,
    upper: str | None,
    upper_inclusive: bool,
    code: EvidenceCode | None,
    points: str,
    label: str,
) -> CalibrationInterval:
    return CalibrationInterval(
        lower=Decimal(lower) if lower is not None else None,
        lower_inclusive=lower_inclusive,
        upper=Decimal(upper) if upper is not None else None,
        upper_inclusive=upper_inclusive,
        evidence_code=code,
        evidence_points=Decimal(points),
        evidence_label=label,
    )


_PROFILES = (
    PredictorCalibrationProfile(
        profile_id="revel_pejaver_2022_empirical",
        predictor_id="revel",
        calibration_version=PEJAVER_VERSION,
        calibration_method=PEJAVER_METHOD,
        publication_url=PEJAVER_PUBLICATION,
        score_unit="probability",
        native_precision=Decimal("0.001"),
        quantization_rule="decimal_round_half_even_to_0.001",
        status="published",
        minimum_score=Decimal("0"),
        maximum_score=Decimal("1"),
        intervals=(
            _interval(None, False, "0.003", True, "BP4", "-8", "BP4 Very Strong"),
            _interval("0.003", False, "0.016", True, "BP4", "-4", "BP4 Strong"),
            _interval("0.016", False, "0.183", True, "BP4", "-2", "BP4 Moderate"),
            _interval("0.183", False, "0.290", True, "BP4", "-1", "BP4 Supporting"),
            _interval("0.290", False, "0.644", False, None, "0", "Indeterminate"),
            _interval("0.644", True, "0.773", False, "PP3", "1", "PP3 Supporting"),
            _interval("0.773", True, "0.932", False, "PP3", "2", "PP3 Moderate"),
            _interval("0.932", True, None, False, "PP3", "4", "PP3 Strong"),
        ),
    ),
    PredictorCalibrationProfile(
        profile_id="revel_pejaver_2022_capped",
        predictor_id="revel",
        calibration_version="eamos-revel-capped-v1+PMID:36413997",
        calibration_method="Eamos capped REVEL profile / Pejaver 2022",
        publication_url=PEJAVER_PUBLICATION,
        score_unit="probability",
        native_precision=Decimal("0.001"),
        quantization_rule="decimal_round_half_even_to_0.001",
        status="applied",
        minimum_score=Decimal("0"),
        maximum_score=Decimal("1"),
        intervals=(
            _interval(None, False, "0.016", True, "BP4", "-4", "BP4 Strong"),
            _interval("0.016", False, "0.183", True, "BP4", "-2", "BP4 Moderate"),
            _interval("0.183", False, "0.290", True, "BP4", "-1", "BP4 Supporting"),
            _interval("0.290", False, "0.644", False, None, "0", "Indeterminate"),
            _interval("0.644", True, "0.773", False, "PP3", "1", "PP3 Supporting"),
            _interval("0.773", True, "0.932", False, "PP3", "2", "PP3 Moderate"),
            _interval("0.932", True, None, False, "PP3", "4", "PP3 Strong"),
        ),
    ),
    PredictorCalibrationProfile(
        profile_id="revel_bergquist_2025_three_point",
        predictor_id="revel",
        calibration_version=BERGQUIST_VERSION,
        calibration_method=BERGQUIST_METHOD,
        publication_url=BERGQUIST_PUBLICATION,
        score_unit="probability",
        native_precision=Decimal("0.001"),
        quantization_rule="decimal_round_half_even_to_0.001",
        status="future_point_ready",
        minimum_score=Decimal("0"),
        maximum_score=Decimal("1"),
        intervals=(
            _interval(None, False, "0.016", True, "BP4", "-4", "BP4 Strong"),
            _interval("0.016", False, "0.052", True, "BP4", "-3", "BP4 3 points"),
            _interval("0.052", False, "0.183", True, "BP4", "-2", "BP4 Moderate"),
            _interval("0.183", False, "0.290", True, "BP4", "-1", "BP4 Supporting"),
            _interval("0.290", False, "0.644", False, None, "0", "Indeterminate"),
            _interval("0.644", True, "0.773", False, "PP3", "1", "PP3 Supporting"),
            _interval("0.773", True, "0.879", False, "PP3", "2", "PP3 Moderate"),
            _interval("0.879", True, "0.932", False, "PP3", "3", "PP3 3 points"),
            _interval("0.932", True, None, False, "PP3", "4", "PP3 Strong"),
        ),
    ),
    PredictorCalibrationProfile(
        profile_id="alphamissense_bergquist_2025",
        predictor_id="alphamissense",
        calibration_version=BERGQUIST_VERSION,
        calibration_method=BERGQUIST_METHOD,
        publication_url=BERGQUIST_PUBLICATION,
        score_unit="probability",
        native_precision=Decimal("0.001"),
        quantization_rule="decimal_round_half_even_to_0.001",
        status="published",
        minimum_score=Decimal("0"),
        maximum_score=Decimal("1"),
        intervals=(
            _interval(None, False, "0.070", True, "BP4", "-3", "BP4 3 points"),
            _interval("0.070", False, "0.099", True, "BP4", "-2", "BP4 Moderate"),
            _interval("0.099", False, "0.169", True, "BP4", "-1", "BP4 Supporting"),
            _interval("0.169", False, "0.792", False, None, "0", "Indeterminate"),
            _interval("0.792", True, "0.906", False, "PP3", "1", "PP3 Supporting"),
            _interval("0.906", True, "0.972", False, "PP3", "2", "PP3 Moderate"),
            _interval("0.972", True, "0.990", False, "PP3", "3", "PP3 3 points"),
            _interval("0.990", True, None, False, "PP3", "4", "PP3 Strong"),
        ),
    ),
    PredictorCalibrationProfile(
        profile_id="esm1b_bergquist_2025",
        predictor_id="esm1b",
        calibration_version=BERGQUIST_VERSION,
        calibration_method=BERGQUIST_METHOD,
        publication_url=BERGQUIST_PUBLICATION,
        score_unit="wt_marginal_llr",
        native_precision=Decimal("0.1"),
        quantization_rule="decimal_round_half_even_to_0.1",
        status="published",
        intervals=(
            _interval(None, False, "-24.0", True, "PP3", "4", "PP3 Strong"),
            _interval("-23.9", True, "-14.0", True, "PP3", "3", "PP3 3 points"),
            _interval("-13.9", True, "-12.2", True, "PP3", "2", "PP3 Moderate"),
            _interval("-12.1", True, "-10.7", True, "PP3", "1", "PP3 Supporting"),
            _interval("-10.6", True, "-6.4", True, None, "0", "Indeterminate"),
            _interval("-6.3", True, "-3.2", True, "BP4", "-1", "BP4 Supporting"),
            _interval("-3.1", True, "8.7", True, "BP4", "-2", "BP4 Moderate"),
            _interval("8.8", True, None, False, "BP4", "-3", "BP4 3 points"),
        ),
    ),
    PredictorCalibrationProfile(
        profile_id="cadd_pejaver_2022",
        predictor_id="caddphred",
        calibration_version=PEJAVER_VERSION,
        calibration_method=PEJAVER_METHOD,
        publication_url=PEJAVER_PUBLICATION,
        score_unit="phred",
        native_precision=Decimal("0.1"),
        quantization_rule="decimal_round_half_even_to_0.1",
        status="published",
        intervals=(
            _interval(None, False, "0.15", True, "BP4", "-4", "BP4 Strong"),
            _interval("0.15", False, "17.3", True, "BP4", "-2", "BP4 Moderate"),
            _interval("17.3", False, "22.7", True, "BP4", "-1", "BP4 Supporting"),
            _interval("22.7", False, "25.3", False, None, "0", "Indeterminate"),
            _interval("25.3", True, "28.1", False, "PP3", "1", "PP3 Supporting"),
            _interval("28.1", True, None, False, "PP3", "2", "PP3 Moderate"),
        ),
    ),
    PredictorCalibrationProfile(
        profile_id="primateai_pejaver_2022",
        predictor_id="primateai",
        calibration_version=PEJAVER_VERSION,
        calibration_method=PEJAVER_METHOD,
        publication_url=PEJAVER_PUBLICATION,
        score_unit="probability",
        native_precision=Decimal("0.001"),
        quantization_rule="decimal_round_half_even_to_0.001",
        status="published",
        minimum_score=Decimal("0"),
        maximum_score=Decimal("1"),
        intervals=(
            _interval(None, False, "0.362", True, "BP4", "-2", "BP4 Moderate"),
            _interval("0.362", False, "0.483", True, "BP4", "-1", "BP4 Supporting"),
            _interval("0.483", False, "0.790", False, None, "0", "Indeterminate"),
            _interval("0.790", True, "0.867", False, "PP3", "1", "PP3 Supporting"),
            _interval("0.867", True, None, False, "PP3", "2", "PP3 Moderate"),
        ),
    ),
    PredictorCalibrationProfile(
        profile_id="spliceai_walker_2023",
        predictor_id="spliceai",
        calibration_version=SPLICE_VERSION,
        calibration_method=SPLICE_METHOD,
        publication_url=SPLICE_PUBLICATION,
        score_unit="max_delta",
        native_precision=Decimal("0.01"),
        quantization_rule="decimal_round_half_even_to_0.01",
        status="published",
        minimum_score=Decimal("0"),
        maximum_score=Decimal("1"),
        intervals=(
            _interval(None, False, "0.1", False, "SPLICE", "0", "Moderate no-splice-impact"),
            _interval("0.1", True, "0.2", False, None, "0", "Indeterminate"),
            _interval("0.2", True, "0.5", False, "SPLICE", "0", "Supporting splice impact"),
            _interval("0.5", True, None, False, "SPLICE", "0", "Strong splice impact"),
        ),
    ),
)

CALIBRATION_PROFILES: Mapping[str, PredictorCalibrationProfile] = MappingProxyType(
    {profile.profile_id: profile for profile in _PROFILES}
)

ACTIVE_PROFILE_BY_PREDICTOR: Mapping[str, str] = MappingProxyType(
    {
        "revel": "revel_pejaver_2022_capped",
        "alphamissense": "alphamissense_bergquist_2025",
        "esm1b": "esm1b_bergquist_2025",
        "caddphred": "cadd_pejaver_2022",
        "primateai": "primateai_pejaver_2022",
        "spliceai": "spliceai_walker_2023",
    }
)


def calibration_field_values(name: Any, score: Any) -> dict[str, Any]:
    calibration = calibrate_predictor(name, score)
    if calibration is None:
        return _empty_calibration_fields()
    return {
        "calibrated_label": calibration.calibrated_label,
        "calibration_bucket": None,
        "calibration_method": calibration.calibration_method,
        "calibration_version": calibration.calibration_version,
        "calibration_id": calibration.calibration_id,
        "calibration_profile_checksum": calibration.profile_checksum,
        "calibration_normalized_score": calibration.calibration_normalized_score,
        "score_unit": calibration.score_unit,
        "score_native_precision": calibration.score_native_precision,
        "score_quantization_rule": calibration.score_quantization_rule,
        "evidence_code": calibration.evidence_code,
        "evidence_points": calibration.evidence_points,
        "interval_lower": calibration.interval_lower,
        "interval_lower_inclusive": calibration.interval_lower_inclusive,
        "interval_upper": calibration.interval_upper,
        "interval_upper_inclusive": calibration.interval_upper_inclusive,
    }


def calibrate_predictor(
    name: Any,
    score: Any,
    *,
    profile_id: str | None = None,
) -> PredictorCalibration | None:
    normalized_name = _normalize_name(name)
    raw_score = _optional_decimal(score)
    if normalized_name is None or raw_score is None:
        return None
    predictor_id = _predictor_id(normalized_name)
    selected_profile_id = profile_id or ACTIVE_PROFILE_BY_PREDICTOR.get(predictor_id)
    if selected_profile_id is None:
        return None
    profile = CALIBRATION_PROFILES.get(selected_profile_id)
    if profile is None or profile.predictor_id != predictor_id:
        return None
    if profile.minimum_score is not None and raw_score < profile.minimum_score:
        return None
    if profile.maximum_score is not None and raw_score > profile.maximum_score:
        return None

    normalized_score = raw_score.quantize(profile.native_precision, rounding=ROUND_HALF_EVEN)
    interval = next(
        (candidate for candidate in profile.intervals if candidate.contains(normalized_score)),
        None,
    )
    if interval is None:
        return None
    return PredictorCalibration(
        raw_score=raw_score,
        calibration_normalized_score=normalized_score,
        calibrated_label=interval.evidence_label,
        evidence_code=interval.evidence_code,
        evidence_points=interval.evidence_points,
        calibration_method=profile.calibration_method,
        calibration_version=profile.calibration_version,
        calibration_id=profile.profile_id,
        profile_checksum=profile.checksum,
        score_unit=profile.score_unit,
        score_native_precision=profile.native_precision,
        score_quantization_rule=profile.quantization_rule,
        interval_lower=interval.lower,
        interval_lower_inclusive=interval.lower_inclusive,
        interval_upper=interval.upper,
        interval_upper_inclusive=interval.upper_inclusive,
    )


def _empty_calibration_fields() -> dict[str, Any]:
    return {
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


def _predictor_id(normalized_name: str) -> str:
    if normalized_name in {"cadd", "caddphred"}:
        return "caddphred"
    if normalized_name in {"esm1b", "esm1bllr"}:
        return "esm1b"
    if normalized_name in {"primateai", "primateai3d"}:
        return "primateai"
    return normalized_name


def _normalize_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if not text:
        return None
    return text.replace("-", "").replace("_", "").replace(" ", "")


def _optional_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None
    return parsed if parsed.is_finite() else None


def _canonical_decimal(value: Decimal) -> str:
    if value.is_zero():
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _optional_decimal_text(value: Decimal | None) -> str | None:
    return _canonical_decimal(value) if value is not None else None
