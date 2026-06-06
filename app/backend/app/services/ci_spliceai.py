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
    provenance: tuple[str, ...] = ("eamos_ci_spliceai_admin_lane_v1",)
    public_serialization_allowed: bool = True
    launch_gate: str | None = "ci_spliceai_launch_filter_metadata"


class CiSpliceAiLane:
    """Admin-enabled CI-SpliceAI score lane.

    The lane preserves launch-gate metadata, but it is not license-blocked for
    backend/admin use. It still requires a local score or cache hit.
    """

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    def lookup(self, score: CiSpliceAiScore | None) -> CiSpliceAiLookup:
        if not self.enabled:
            return CiSpliceAiLookup(
                available=False,
                score=None,
                unavailable_reason="ci_spliceai_lane_disabled",
                warnings=("ci_spliceai_admin_lane_disabled",),
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
