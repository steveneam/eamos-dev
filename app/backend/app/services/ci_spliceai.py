from __future__ import annotations

from dataclasses import dataclass

from app.services.computational_calibration import calibration_field_values


@dataclass(frozen=True)
class CiSpliceAiScore:
    chrom: str
    position: int
    ref: str
    alt: str
    ds_ag: float | None = None
    ds_al: float | None = None
    ds_dg: float | None = None
    ds_dl: float | None = None

    @property
    def max_delta(self) -> float | None:
        values = [
            value for value in (self.ds_ag, self.ds_al, self.ds_dg, self.ds_dl) if value is not None
        ]
        return max(values) if values else None


@dataclass(frozen=True)
class CiSpliceAiLookup:
    available: bool
    score: CiSpliceAiScore | None
    calibrated_label: str | None = None
    calibration_bucket: str | None = None
    unavailable_reason: str | None = None
    warnings: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ("eamos_ci_spliceai_isolated_lane_v1",)


class CiSpliceAiLane:
    """Isolated CI-SpliceAI lane.

    The lane is intentionally not wired into the main report path. It only
    produces output when explicitly enabled and supplied with a local score.
    """

    def __init__(self, *, enabled: bool = False) -> None:
        self.enabled = enabled

    def lookup(self, score: CiSpliceAiScore | None) -> CiSpliceAiLookup:
        if not self.enabled:
            return CiSpliceAiLookup(
                available=False,
                score=None,
                unavailable_reason="ci_spliceai_lane_disabled",
                warnings=("ci_spliceai_isolated_from_main_api_path",),
            )
        if score is None or score.max_delta is None:
            return CiSpliceAiLookup(
                available=False,
                score=None,
                unavailable_reason="ci_spliceai_score_missing",
                warnings=("ci_spliceai_score_missing",),
            )
        calibration = calibration_field_values("SpliceAI", score.max_delta)
        return CiSpliceAiLookup(
            available=True,
            score=score,
            calibrated_label=calibration["calibrated_label"],
            calibration_bucket=calibration["calibration_bucket"],
        )
