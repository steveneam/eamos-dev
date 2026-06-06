from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapiceScore:
    chrom: str
    position: int
    ref: str
    alt: str
    score: float | None
    source_version: str | None = None


@dataclass(frozen=True)
class CapiceLookup:
    available: bool
    score: CapiceScore | None
    unavailable_reason: str | None = None
    warnings: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ("eamos_capice_admin_lane_v1",)
    public_serialization_allowed: bool = True
    launch_gate: str | None = "capice_launch_filter_metadata"


class CapiceLane:
    """Admin-enabled CAPICE score lane.

    This is the runtime scaffold for CAPICE evidence once model/feature assets
    are materialized. License metadata is launch-gate data, not a backend block.
    """

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    def lookup(self, score: CapiceScore | None) -> CapiceLookup:
        if not self.enabled:
            return CapiceLookup(
                available=False,
                score=None,
                unavailable_reason="capice_lane_disabled",
                warnings=("capice_admin_lane_disabled",),
            )
        if score is None or score.score is None:
            return CapiceLookup(
                available=False,
                score=None,
                unavailable_reason="capice_score_missing",
                warnings=("capice_score_missing",),
            )
        if not 0.0 <= score.score <= 1.0:
            return CapiceLookup(
                available=False,
                score=None,
                unavailable_reason="capice_score_out_of_range",
                warnings=("capice_score_out_of_range",),
            )
        return CapiceLookup(available=True, score=score)
