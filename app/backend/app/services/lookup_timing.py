from __future__ import annotations

import json
import re
from time import perf_counter
from typing import Any

LOOKUP_TIMING_HEADER = "X-Eamos-Lookup-Timing"
LOOKUP_TIMING_SCHEMA_VERSION = "lookup_timing_v1"

_SAFE_TEXT_RE = re.compile(r"[^a-zA-Z0-9_.:-]+")
_MAX_HEADER_CHARS = 7500


class LookupTimingCollector:
    """Collect compact lookup timing diagnostics for an opt-in response header."""

    def __init__(self, *, max_entries: int = 80) -> None:
        self._started_at = perf_counter()
        self._max_entries = max(1, max_entries)
        self._phases: list[dict[str, Any]] = []
        self._providers: list[dict[str, Any]] = []
        self._truncated = False

    def start(self) -> float:
        return perf_counter()

    def record_phase(
        self,
        name: str,
        started_at: float,
        *,
        outcome: str = "ok",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._append(
            self._phases,
            {
                "name": _safe_text(name),
                "ms": _duration_ms(started_at),
                "outcome": _safe_text(outcome),
                **_safe_metadata(metadata or {}),
            },
        )

    def record_provider(
        self,
        name: str,
        started_at: float,
        *,
        status: str | None = None,
        cache_status: str | None = None,
        outcome: str = "ok",
        warning_count: int = 0,
        error_type: str | None = None,
    ) -> None:
        item: dict[str, Any] = {
            "name": _safe_text(name),
            "ms": _duration_ms(started_at),
            "outcome": _safe_text(outcome),
            "warning_count": max(0, int(warning_count)),
        }
        if status:
            item["status"] = _safe_text(status)
        if cache_status:
            item["cache_status"] = _safe_text(cache_status)
        if error_type:
            item["error_type"] = _safe_text(error_type)
        self._append(self._providers, item)

    def header_value(self) -> str:
        payload = {
            "schema_version": LOOKUP_TIMING_SCHEMA_VERSION,
            "total_ms": _duration_ms(self._started_at),
            "phases": self._phases,
            "providers": self._providers,
            "truncated": self._truncated,
        }
        value = _compact_json(payload)
        while len(value) > _MAX_HEADER_CHARS and payload["providers"]:
            payload["providers"].pop()
            payload["truncated"] = True
            value = _compact_json(payload)
        while len(value) > _MAX_HEADER_CHARS and payload["phases"]:
            payload["phases"].pop()
            payload["truncated"] = True
            value = _compact_json(payload)
        if len(value) > _MAX_HEADER_CHARS:
            value = _compact_json(
                {
                    "schema_version": LOOKUP_TIMING_SCHEMA_VERSION,
                    "total_ms": payload["total_ms"],
                    "phases": [],
                    "providers": [],
                    "truncated": True,
                }
            )
        return value

    def _append(self, items: list[dict[str, Any]], item: dict[str, Any]) -> None:
        if len(items) >= self._max_entries:
            self._truncated = True
            return
        items.append(item)


def _duration_ms(started_at: float) -> int:
    return max(0, int(round((perf_counter() - started_at) * 1000)))


def _safe_text(value: Any, *, max_length: int = 96) -> str:
    text = _SAFE_TEXT_RE.sub("_", str(value or "").strip())[:max_length]
    return text or "unknown"


def _safe_metadata(values: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in values.items():
        safe_key = _safe_text(key, max_length=48)
        if isinstance(value, bool):
            safe[safe_key] = value
        elif isinstance(value, int):
            safe[safe_key] = value
        elif value is not None:
            safe[safe_key] = _safe_text(value)
    return safe


def _compact_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)
