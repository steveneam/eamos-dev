from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

ReportSourceCategory = Literal[
    "current",
    "stale",
    "fixture",
    "failed",
    "unavailable",
]

_CURRENT_STATUSES = frozenset({"live", "local", "cache"})
_FAILED_STATUSES = frozenset({"error", "failed"})
_UNAVAILABLE_STATUSES = frozenset({"fallback", "live_stub", "missing"})


def normalize_report_source_status(value: str | None) -> str:
    """Return the one canonical status vocabulary used by report surfaces."""

    status = str(value or "missing").strip().lower().replace("-", "_")
    if status == "source_table":
        return "local"
    if status == "timeout":
        return "error"
    if status in {"degraded", "stub", "unavailable"}:
        return "fallback"
    if status in {
        *_CURRENT_STATUSES,
        *_FAILED_STATUSES,
        *_UNAVAILABLE_STATUSES,
        "fixture",
        "stale",
    }:
        return status
    return "fallback"


def report_source_category(value: str | None) -> ReportSourceCategory:
    status = normalize_report_source_status(value)
    if status in _CURRENT_STATUSES:
        return "current"
    if status == "stale":
        return "stale"
    if status == "fixture":
        return "fixture"
    if status in _FAILED_STATUSES:
        return "failed"
    return "unavailable"


def report_source_allows_payload(
    value: str | None,
    *,
    allow_fixture: bool = True,
) -> bool:
    """Whether scientific fields may be rendered from this source result.

    Stale source-backed records remain renderable with a stale disclosure. A
    fixture is renderable only for explicit fixture/test flows; callers that
    construct release-only output can disable it.
    """

    category = report_source_category(value)
    return category in {"current", "stale"} or (allow_fixture and category == "fixture")


def report_source_is_weak(value: str | None) -> bool:
    return report_source_category(value) in {"failed", "unavailable"}


def combined_report_source_status(values: Iterable[str | None]) -> str:
    """Conservatively summarize multiple report-source results.

    A successful source never masks a failed, unavailable, stale, or fixture
    peer. Homogeneous statuses remain specific so local execution cannot be
    mislabeled as fallback.
    """

    statuses = [normalize_report_source_status(value) for value in values]
    if not statuses:
        return "missing"
    unique = set(statuses)
    if len(unique) == 1:
        return statuses[0]

    categories = {report_source_category(status) for status in statuses}
    has_renderable = bool(categories & {"current", "stale", "fixture"})
    has_weak = bool(categories & {"failed", "unavailable"})
    if has_renderable and has_weak:
        return "partial"
    if "current" in categories and categories & {"stale", "fixture"}:
        return "partial"
    if "stale" in categories and "fixture" in categories:
        return "partial"
    if categories <= {"failed", "unavailable"}:
        return "failed" if "failed" in categories else "fallback"
    if categories == {"current"}:
        return "mixed"
    return "partial"
