from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.core.config import Settings
from app.services.indexed_sources import (
    IndexedPredictorScore,
    IndexedSourceError,
    TabixTsvPredictorColumns,
    TabixTsvPredictorReader,
)
from app.services.predictor_runtime import (
    AdminPredictorRuntimeInspection,
    CAPICE_FEATURE_CACHE_SOURCE_ID,
    CAPICE_LAUNCH_GATE,
    CAPICE_SOURCE_ID,
    inspect_capice_runtime_assets,
)


class CapiceReader(Protocol):
    def close(self) -> None: ...

    def query_variant(
        self,
        chrom: str,
        position: int,
        ref: str,
        alt: str,
    ) -> tuple[IndexedPredictorScore, ...]: ...


@dataclass(frozen=True)
class CapiceScore:
    chrom: str
    position: int
    ref: str
    alt: str
    score: float | None
    source_version: str | None = None
    interpretation: str | None = None


@dataclass(frozen=True)
class CapiceProvenance:
    source_id: str
    feature_cache_source_id: str
    source_version: str | None
    source_url: str | None
    file_name: str
    reader: str
    launch_gate: str | None


@dataclass(frozen=True)
class CapiceLookup:
    available: bool
    score: CapiceScore | None
    unavailable_reason: str | None = None
    warnings: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ("eamos_capice_admin_lane_v1",)
    provenance_details: CapiceProvenance | None = None
    public_serialization_allowed: bool = True
    launch_gate: str | None = CAPICE_LAUNCH_GATE


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


class CapiceLocalAdapter:
    """Local CAPICE feature/score-cache adapter.

    The adapter only reads a materialized coordinate-keyed score cache. It does
    not run CAPICE/XGBoost inference or derive scores from SpliceAI features.
    """

    def __init__(
        self,
        inspection: AdminPredictorRuntimeInspection,
        *,
        feature_cache_path: Path,
        reader_factory: Any | None = None,
    ) -> None:
        self._inspection = inspection
        self._feature_cache_path = feature_cache_path
        self._reader_factory = reader_factory or _default_reader_factory
        self._reader_lock = threading.RLock()
        self._reader_path: Path | None = None
        self._reader: CapiceReader | None = None
        self._lane = CapiceLane(enabled=True)

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        reader_factory: Any | None = None,
    ) -> CapiceLocalAdapter:
        inspection = inspect_capice_runtime_assets(settings)
        path = _resolve_backend_path(settings, settings.capice_feature_cache_path)
        return cls(inspection, feature_cache_path=path, reader_factory=reader_factory)

    def lookup(
        self,
        *,
        chrom: str,
        position: int,
        ref: str,
        alt: str,
    ) -> CapiceLookup:
        if not self._inspection.available:
            return CapiceLookup(
                available=False,
                score=None,
                unavailable_reason=self._inspection.status,
                warnings=(f"capice_{self._inspection.status}",),
            )
        if position < 1:
            return CapiceLookup(
                available=False,
                score=None,
                unavailable_reason="invalid_coordinates",
                warnings=("capice_invalid_coordinates",),
            )
        try:
            with self._reader_lock:
                reader = self._reader_for_ready_asset()
                matches = reader.query_variant(chrom, position, ref, alt)
        except IndexedSourceError as exc:
            return CapiceLookup(
                available=False,
                score=None,
                unavailable_reason=exc.code,
                warnings=(f"capice_{exc.code}",),
            )

        if not matches:
            return CapiceLookup(
                available=False,
                score=None,
                unavailable_reason="variant_not_found",
                warnings=("capice_variant_not_found",),
            )
        if len(matches) > 1:
            return CapiceLookup(
                available=False,
                score=None,
                unavailable_reason="duplicate_variant_records",
                warnings=("capice_duplicate_variant_records",),
            )
        score = _score_from_row(
            matches[0], source_version=_manifest_text(self._feature_cache_path, "source_version")
        )
        lookup = self._lane.lookup(score)
        if not lookup.available:
            return lookup
        return CapiceLookup(
            available=True,
            score=lookup.score,
            warnings=("capice_launch_gate_metadata", CAPICE_LAUNCH_GATE),
            provenance_details=CapiceProvenance(
                source_id=CAPICE_SOURCE_ID,
                feature_cache_source_id=CAPICE_FEATURE_CACHE_SOURCE_ID,
                source_version=score.source_version if score is not None else None,
                source_url=_manifest_text(self._feature_cache_path, "source_url"),
                file_name=self._feature_cache_path.name,
                reader="tabix_tsv_predictor_reader",
                launch_gate=CAPICE_LAUNCH_GATE,
            ),
            public_serialization_allowed=lookup.public_serialization_allowed,
            launch_gate=lookup.launch_gate,
        )

    def close(self) -> None:
        with self._reader_lock:
            reader = self._reader
            self._reader = None
            self._reader_path = None
            close = getattr(reader, "close", None)
            if callable(close):
                close()

    def _reader_for_ready_asset(self) -> CapiceReader:
        if self._reader is None or self._reader_path != self._feature_cache_path:
            self.close()
            self._reader = self._reader_factory(self._feature_cache_path)
            self._reader_path = self._feature_cache_path
        return self._reader


def _score_from_row(
    row: IndexedPredictorScore,
    *,
    source_version: str | None,
) -> CapiceScore | None:
    if isinstance(row.score, str):
        return None
    return CapiceScore(
        chrom=row.chrom,
        position=row.position,
        ref=row.ref.upper(),
        alt=row.alt.upper(),
        score=float(row.score),
        source_version=_optional_extra(row, "source_version") or source_version,
        interpretation=(
            _optional_extra(row, "interpretation")
            or _optional_extra(row, "prediction")
            or _optional_extra(row, "capice_class")
        ),
    )


def _optional_extra(score: IndexedPredictorScore, key: str) -> str | None:
    value = score.extra.get(key)
    if value is None:
        return None
    text = value.strip()
    return text or None


def _manifest_text(path: Path, key: str) -> str | None:
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8")).get(key)
    except (OSError, ValueError, AttributeError):
        return None
    text = str(value).strip() if value is not None else ""
    return text or None


def _resolve_backend_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def _default_reader_factory(path: Path) -> CapiceReader:
    return TabixTsvPredictorReader(
        path,
        source_id=CAPICE_FEATURE_CACHE_SOURCE_ID,
        columns=TabixTsvPredictorColumns(
            score=4,
            extra_columns=(
                ("interpretation", 5),
                ("source_version", 6),
            ),
        ),
    )
