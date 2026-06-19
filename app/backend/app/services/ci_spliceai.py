from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.services.computational_calibration import calibration_field_values
from app.core.config import Settings
from app.services.indexed_sources import (
    IndexedSourceError,
    IndexedVcfRecord,
    PysamIndexedVcfReader,
)
from app.services.predictor_runtime import (
    AdminPredictorRuntimeInspection,
    CI_SPLICEAI_LAUNCH_GATE,
    CI_SPLICEAI_SOURCE_ID,
    inspect_ci_spliceai_runtime_assets,
)


class CiSpliceAiReader(Protocol):
    def close(self) -> None: ...

    def query_position(self, chrom: str, position: int) -> tuple[IndexedVcfRecord, ...]: ...


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
    dp_ag: int | None = None
    dp_al: int | None = None
    dp_dg: int | None = None
    dp_dl: int | None = None

    @property
    def max_delta(self) -> float | None:
        values = [
            value for value in (self.ds_ag, self.ds_al, self.ds_dg, self.ds_dl) if value is not None
        ]
        return max(values) if values else None

    @property
    def max_component(self) -> str | None:
        values = {
            "acceptor_gain": self.ds_ag,
            "acceptor_loss": self.ds_al,
            "donor_gain": self.ds_dg,
            "donor_loss": self.ds_dl,
        }
        scored = {key: value for key, value in values.items() if value is not None}
        if not scored:
            return None
        return max(scored, key=lambda key: scored[key] if scored[key] is not None else -1.0)


@dataclass(frozen=True)
class CiSpliceAiProvenance:
    source_id: str
    source_version: str | None
    source_url: str | None
    file_name: str
    reader: str
    launch_gate: str | None


@dataclass(frozen=True)
class CiSpliceAiLookup:
    available: bool
    score: CiSpliceAiScore | None
    calibrated_label: str | None = None
    calibration_bucket: str | None = None
    calibration_method: str | None = None
    calibration_version: str | None = None
    unavailable_reason: str | None = None
    warnings: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ("eamos_ci_spliceai_admin_lane_v1",)
    provenance_details: CiSpliceAiProvenance | None = None
    public_serialization_allowed: bool = True
    launch_gate: str | None = CI_SPLICEAI_LAUNCH_GATE


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
            calibration_method=calibration["calibration_method"],
            calibration_version=calibration["calibration_version"],
        )


class CiSpliceAiLocalAdapter:
    """Local CI-SpliceAI score-cache adapter.

    The adapter reads materialized coordinate-keyed VCF scores only after the
    full admin-lane artifact set passes runtime inspection. It does not run or
    reimplement CI-SpliceAI model math.
    """

    def __init__(
        self,
        inspection: AdminPredictorRuntimeInspection,
        *,
        score_cache_path: Path,
        reader_factory: Any | None = None,
    ) -> None:
        self._inspection = inspection
        self._score_cache_path = score_cache_path
        self._reader_factory = reader_factory or _default_reader_factory
        self._reader_lock = threading.RLock()
        self._reader_path: Path | None = None
        self._reader: CiSpliceAiReader | None = None
        self._lane = CiSpliceAiLane(enabled=True)

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        reader_factory: Any | None = None,
    ) -> CiSpliceAiLocalAdapter:
        inspection = inspect_ci_spliceai_runtime_assets(settings)
        path = _resolve_backend_path(settings, settings.ci_spliceai_score_cache_path)
        return cls(inspection, score_cache_path=path, reader_factory=reader_factory)

    def lookup(
        self,
        *,
        chrom: str,
        position: int,
        ref: str,
        alt: str,
    ) -> CiSpliceAiLookup:
        if not self._inspection.available:
            return CiSpliceAiLookup(
                available=False,
                score=None,
                unavailable_reason=self._inspection.status,
                warnings=(f"ci_spliceai_{self._inspection.status}",),
            )
        if position < 1:
            return CiSpliceAiLookup(
                available=False,
                score=None,
                unavailable_reason="invalid_coordinates",
                warnings=("ci_spliceai_invalid_coordinates",),
            )
        try:
            with self._reader_lock:
                reader = self._reader_for_ready_asset()
                records = reader.query_position(chrom, position)
        except IndexedSourceError as exc:
            return CiSpliceAiLookup(
                available=False,
                score=None,
                unavailable_reason=exc.code,
                warnings=(f"ci_spliceai_{exc.code}",),
            )

        matches = tuple(
            score
            for record in records
            for score in (_score_from_record(record, ref=ref, alt=alt),)
            if score is not None
        )
        if not matches:
            return CiSpliceAiLookup(
                available=False,
                score=None,
                unavailable_reason="variant_not_found",
                warnings=("ci_spliceai_variant_not_found",),
            )
        if len(matches) > 1:
            return CiSpliceAiLookup(
                available=False,
                score=None,
                unavailable_reason="duplicate_variant_records",
                warnings=("ci_spliceai_duplicate_variant_records",),
            )

        lookup = self._lane.lookup(matches[0])
        if not lookup.available:
            return lookup
        return CiSpliceAiLookup(
            available=True,
            score=lookup.score,
            calibrated_label=lookup.calibrated_label,
            calibration_bucket=lookup.calibration_bucket,
            calibration_method=lookup.calibration_method,
            calibration_version=lookup.calibration_version,
            warnings=("ci_spliceai_launch_gate_metadata", CI_SPLICEAI_LAUNCH_GATE),
            provenance_details=CiSpliceAiProvenance(
                source_id=CI_SPLICEAI_SOURCE_ID,
                source_version=_manifest_text(self._score_cache_path, "source_version"),
                source_url=_manifest_text(self._score_cache_path, "source_url"),
                file_name=self._score_cache_path.name,
                reader="pysam_indexed_vcf_reader",
                launch_gate=CI_SPLICEAI_LAUNCH_GATE,
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

    def _reader_for_ready_asset(self) -> CiSpliceAiReader:
        if self._reader is None or self._reader_path != self._score_cache_path:
            self.close()
            self._reader = self._reader_factory(self._score_cache_path)
            self._reader_path = self._score_cache_path
        return self._reader


def _score_from_record(
    record: IndexedVcfRecord,
    *,
    ref: str,
    alt: str,
) -> CiSpliceAiScore | None:
    requested_ref = ref.strip().upper()
    requested_alt = alt.strip().upper()
    if record.ref.upper() != requested_ref:
        return None
    alts = tuple(item.upper() for item in record.alts)
    if requested_alt not in alts:
        return None
    alt_index = alts.index(requested_alt)
    direct = CiSpliceAiScore(
        chrom=record.chrom,
        position=record.position,
        ref=record.ref.upper(),
        alt=requested_alt,
        ds_ag=_info_float(record.info, "DS_AG", alt_index=alt_index),
        ds_al=_info_float(record.info, "DS_AL", alt_index=alt_index),
        ds_dg=_info_float(record.info, "DS_DG", alt_index=alt_index),
        ds_dl=_info_float(record.info, "DS_DL", alt_index=alt_index),
        dp_ag=_info_int(record.info, "DP_AG", alt_index=alt_index),
        dp_al=_info_int(record.info, "DP_AL", alt_index=alt_index),
        dp_dg=_info_int(record.info, "DP_DG", alt_index=alt_index),
        dp_dl=_info_int(record.info, "DP_DL", alt_index=alt_index),
    )
    if direct.max_delta is not None:
        return direct
    return _score_from_spliceai_info(record, requested_alt)


def _score_from_spliceai_info(record: IndexedVcfRecord, alt: str) -> CiSpliceAiScore | None:
    value = record.info.get("SpliceAI") or record.info.get("CI_SPLICEAI")
    for entry in _iter_info_entries(value):
        fields = entry.split("|")
        if len(fields) < 6 or fields[0].strip().upper() != alt:
            continue
        score = CiSpliceAiScore(
            chrom=record.chrom,
            position=record.position,
            ref=record.ref.upper(),
            alt=alt,
            ds_ag=_float_text(fields[2]),
            ds_al=_float_text(fields[3]),
            ds_dg=_float_text(fields[4]),
            ds_dl=_float_text(fields[5]),
            dp_ag=_int_text(fields[6]) if len(fields) > 6 else None,
            dp_al=_int_text(fields[7]) if len(fields) > 7 else None,
            dp_dg=_int_text(fields[8]) if len(fields) > 8 else None,
            dp_dl=_int_text(fields[9]) if len(fields) > 9 else None,
        )
        if score.max_delta is not None:
            return score
    return None


def _iter_info_entries(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    if isinstance(value, tuple | list):
        out: list[str] = []
        for item in value:
            out.extend(_iter_info_entries(item))
        return tuple(out)
    return (str(value),)


def _info_float(info: dict[str, object] | Any, key: str, *, alt_index: int) -> float | None:
    return _float_text(_indexed_info_value(info.get(key), alt_index=alt_index))


def _info_int(info: dict[str, object] | Any, key: str, *, alt_index: int) -> int | None:
    return _int_text(_indexed_info_value(info.get(key), alt_index=alt_index))


def _indexed_info_value(value: object, *, alt_index: int) -> object:
    if isinstance(value, tuple | list):
        if not value:
            return None
        if len(value) > alt_index:
            return value[alt_index]
        return value[0]
    return value


def _float_text(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_text(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _manifest_text(path: Path, key: str) -> str | None:
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    try:
        import json

        value = json.loads(manifest_path.read_text(encoding="utf-8")).get(key)
    except (OSError, ValueError, AttributeError):
        return None
    text = str(value).strip() if value is not None else ""
    return text or None


def _resolve_backend_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def _default_reader_factory(path: Path) -> CiSpliceAiReader:
    return PysamIndexedVcfReader(path, source_id=CI_SPLICEAI_SOURCE_ID)
