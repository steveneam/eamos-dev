from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.core.config import Settings
from app.services.computational_calibration import calibration_field_values
from app.services.indexed_sources import (
    IndexedPredictorScore,
    IndexedSourceError,
    TabixTsvPredictorColumns,
    TabixTsvPredictorReader,
)
from app.services.predictor_runtime import (
    AdminPredictorRuntimeInspection,
    PRIMATEAI3D_LAUNCH_GATE,
    PRIMATEAI3D_SOURCE_ID,
    REVEL_LAUNCH_GATE,
    REVEL_SOURCE_ID,
    inspect_primateai3d_runtime_assets,
    inspect_revel_runtime_assets,
)


class RestrictedPredictorReader(Protocol):
    def close(self) -> None: ...

    def query_variant(
        self,
        chrom: str,
        position: int,
        ref: str,
        alt: str,
    ) -> tuple[IndexedPredictorScore, ...]: ...


@dataclass(frozen=True)
class RestrictedPredictorConfig:
    name: str
    source_label: str
    source_id: str
    launch_gate: str
    warning_prefix: str
    threshold: float | None = None


@dataclass(frozen=True)
class RestrictedPredictorScore:
    chrom: str
    position: int
    ref: str
    alt: str
    name: str
    score: float | None
    source_label: str
    source_version: str | None = None
    threshold: float | None = None
    interpretation: str | None = None


@dataclass(frozen=True)
class RestrictedPredictorProvenance:
    source_id: str
    source_version: str | None
    source_url: str | None
    file_name: str
    reader: str
    launch_gate: str | None


@dataclass(frozen=True)
class RestrictedPredictorLookup:
    available: bool
    score: RestrictedPredictorScore | None
    calibrated_label: str | None = None
    calibration_bucket: str | None = None
    calibration_method: str | None = None
    calibration_version: str | None = None
    unavailable_reason: str | None = None
    warnings: tuple[str, ...] = ()
    provenance_details: RestrictedPredictorProvenance | None = None
    public_serialization_allowed: bool = True
    launch_gate: str | None = None


class RestrictedPredictorLocalAdapter:
    """Local adapter for coordinate-keyed restricted predictor score caches.

    This reads normalized bgzip/tabix TSV caches only after runtime inspection
    passes. It does not download upstream data or derive model scores.
    """

    def __init__(
        self,
        inspection: AdminPredictorRuntimeInspection,
        *,
        score_cache_path: Path,
        config: RestrictedPredictorConfig,
        reader_factory: Any | None = None,
    ) -> None:
        self._inspection = inspection
        self._score_cache_path = score_cache_path
        self._config = config
        self._reader_factory = reader_factory or _default_reader_factory(config.source_id)
        self._reader_lock = threading.RLock()
        self._reader_path: Path | None = None
        self._reader: RestrictedPredictorReader | None = None

    def lookup(
        self,
        *,
        chrom: str,
        position: int,
        ref: str,
        alt: str,
    ) -> RestrictedPredictorLookup:
        if not self._inspection.available:
            return RestrictedPredictorLookup(
                available=False,
                score=None,
                unavailable_reason=self._inspection.status,
                warnings=(f"{self._config.warning_prefix}_{self._inspection.status}",),
                launch_gate=self._config.launch_gate,
            )
        if position < 1:
            return RestrictedPredictorLookup(
                available=False,
                score=None,
                unavailable_reason="invalid_coordinates",
                warnings=(f"{self._config.warning_prefix}_invalid_coordinates",),
                launch_gate=self._config.launch_gate,
            )
        try:
            with self._reader_lock:
                reader = self._reader_for_ready_asset()
                matches = reader.query_variant(chrom, position, ref, alt)
        except IndexedSourceError as exc:
            return RestrictedPredictorLookup(
                available=False,
                score=None,
                unavailable_reason=exc.code,
                warnings=(f"{self._config.warning_prefix}_{exc.code}",),
                launch_gate=self._config.launch_gate,
            )

        if not matches:
            return RestrictedPredictorLookup(
                available=False,
                score=None,
                unavailable_reason="variant_not_found",
                warnings=(f"{self._config.warning_prefix}_variant_not_found",),
                launch_gate=self._config.launch_gate,
            )
        if len(matches) > 1:
            return RestrictedPredictorLookup(
                available=False,
                score=None,
                unavailable_reason="duplicate_variant_records",
                warnings=(f"{self._config.warning_prefix}_duplicate_variant_records",),
                launch_gate=self._config.launch_gate,
            )
        score = _score_from_row(
            matches[0],
            config=self._config,
            source_version=_manifest_text(self._score_cache_path, "source_version"),
        )
        if score is None or score.score is None:
            return RestrictedPredictorLookup(
                available=False,
                score=None,
                unavailable_reason="score_missing",
                warnings=(f"{self._config.warning_prefix}_score_missing",),
                launch_gate=self._config.launch_gate,
            )
        if not 0.0 <= score.score <= 1.0:
            return RestrictedPredictorLookup(
                available=False,
                score=None,
                unavailable_reason="score_out_of_range",
                warnings=(f"{self._config.warning_prefix}_score_out_of_range",),
                launch_gate=self._config.launch_gate,
            )

        calibration = calibration_field_values(self._config.name, score.score)
        return RestrictedPredictorLookup(
            available=True,
            score=score,
            calibrated_label=calibration["calibrated_label"],
            calibration_bucket=calibration["calibration_bucket"],
            calibration_method=calibration["calibration_method"],
            calibration_version=calibration["calibration_version"],
            warnings=(
                f"{self._config.warning_prefix}_launch_gate_metadata",
                self._config.launch_gate,
            ),
            provenance_details=RestrictedPredictorProvenance(
                source_id=self._config.source_id,
                source_version=score.source_version,
                source_url=_manifest_text(self._score_cache_path, "source_url"),
                file_name=self._score_cache_path.name,
                reader="tabix_tsv_predictor_reader",
                launch_gate=self._config.launch_gate,
            ),
            public_serialization_allowed=True,
            launch_gate=self._config.launch_gate,
        )

    def close(self) -> None:
        with self._reader_lock:
            reader = self._reader
            self._reader = None
            self._reader_path = None
            close = getattr(reader, "close", None)
            if callable(close):
                close()

    def _reader_for_ready_asset(self) -> RestrictedPredictorReader:
        if self._reader is None or self._reader_path != self._score_cache_path:
            self.close()
            self._reader = self._reader_factory(self._score_cache_path)
            self._reader_path = self._score_cache_path
        return self._reader


class RevelLocalAdapter(RestrictedPredictorLocalAdapter):
    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        reader_factory: Any | None = None,
    ) -> RevelLocalAdapter:
        path = _resolve_backend_path(settings, settings.revel_score_cache_path)
        return cls(
            inspect_revel_runtime_assets(settings),
            score_cache_path=path,
            config=REVEL_CONFIG,
            reader_factory=reader_factory,
        )


class PrimateAi3dLocalAdapter(RestrictedPredictorLocalAdapter):
    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        reader_factory: Any | None = None,
    ) -> PrimateAi3dLocalAdapter:
        path = _resolve_backend_path(settings, settings.primateai3d_score_cache_path)
        return cls(
            inspect_primateai3d_runtime_assets(settings),
            score_cache_path=path,
            config=PRIMATEAI3D_CONFIG,
            reader_factory=reader_factory,
        )


REVEL_CONFIG = RestrictedPredictorConfig(
    name="REVEL",
    source_label="dbNSFP",
    source_id=REVEL_SOURCE_ID,
    launch_gate=REVEL_LAUNCH_GATE,
    warning_prefix="revel",
    threshold=0.5,
)
PRIMATEAI3D_CONFIG = RestrictedPredictorConfig(
    name="PrimateAI-3D",
    source_label="PrimateAI-3D",
    source_id=PRIMATEAI3D_SOURCE_ID,
    launch_gate=PRIMATEAI3D_LAUNCH_GATE,
    warning_prefix="primateai3d",
    threshold=0.5,
)


def _score_from_row(
    row: IndexedPredictorScore,
    *,
    config: RestrictedPredictorConfig,
    source_version: str | None,
) -> RestrictedPredictorScore | None:
    if isinstance(row.score, str):
        return None
    return RestrictedPredictorScore(
        chrom=row.chrom,
        position=row.position,
        ref=row.ref.upper(),
        alt=row.alt.upper(),
        name=config.name,
        score=float(row.score),
        source_label=config.source_label,
        source_version=_optional_extra(row, "source_version") or source_version,
        threshold=config.threshold,
        interpretation=(
            _optional_extra(row, "interpretation")
            or _optional_extra(row, "prediction")
            or _optional_extra(row, "class")
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


def _default_reader_factory(source_id: str) -> Any:
    return lambda path: TabixTsvPredictorReader(
        path,
        source_id=source_id,
        columns=TabixTsvPredictorColumns(
            score=4,
            extra_columns=(
                ("interpretation", 5),
                ("source_version", 6),
            ),
        ),
    )
