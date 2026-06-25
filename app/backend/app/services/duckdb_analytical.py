from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import Settings

DUCKDB_ANALYTICAL_SOURCE_ID = "eamos_duckdb_analytical"
DUCKDB_ANALYTICAL_SCHEMA_VERSION = "eamos.duckdb_analytical.v1"
DUCKDB_ANALYTICAL_RELEASE_MANIFEST_SCHEMA_VERSION = "eamos.analytical_release_manifest.v1"
DUCKDB_ANALYTICAL_RELEASE_LAYERS = ("bronze", "silver", "gold")
DUCKDB_ANALYTICAL_QUERY_ROLES = (
    "bulk_variant_annotation",
    "region_cohort_aggregation",
    "reporting",
    "artifact_validation",
)


@dataclass(frozen=True)
class DuckDbAnalyticalInspection:
    source_id: str
    status: str
    ready: bool
    enabled: bool
    available: bool
    database_present: bool
    database_size_bytes: int | None
    database_path_configured: bool
    temp_directory_configured: bool
    memory_limit: str
    threads: int
    schema_version: str = DUCKDB_ANALYTICAL_SCHEMA_VERSION
    engine: str = "duckdb"
    access_mode: str = "READ_ONLY"
    query_roles: tuple[str, ...] = DUCKDB_ANALYTICAL_QUERY_ROLES
    message: str | None = None
    warnings: tuple[str, ...] = ()
    release: Mapping[str, Any] | None = None

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "ready": self.ready,
            "enabled": self.enabled,
            "available": self.available,
            "schema_version": self.schema_version,
            "engine": self.engine,
            "access_mode": self.access_mode,
            "workload_boundary": "analytical_batch_only",
            "query_roles": list(self.query_roles),
            "database_present": self.database_present,
            "database_size_bytes": self.database_size_bytes,
            "database_path_configured": self.database_path_configured,
            "temp_directory_configured": self.temp_directory_configured,
            "memory_limit": self.memory_limit,
            "threads": self.threads,
            "point_lookup_engine": "tabix_sqlite_report_cache",
            "single_coordinate_hot_path_allowed": False,
            "request_time_materialization_allowed": False,
            "startup_download_allowed": False,
            "remote_httpfs_allowed": False,
            "motherduck_allowed": False,
            "spark_required": False,
            "secret_values_emitted": False,
            "local_path_values_emitted": False,
            "message": self.message,
            "notices": list(self.warnings),
            "release": dict(self.release or {}),
        }


@dataclass(frozen=True)
class DuckDbAnalyticalReleaseInspection:
    source_id: str
    status: str
    ready: bool
    manifest_present: bool
    release_id: str | None
    manifest_schema_version: str | None
    source_ids: tuple[str, ...] = ()
    source_versions: Mapping[str, Any] | None = None
    layer_counts: Mapping[str, int] | None = None
    partition_count: int = 0
    artifact_count: int = 0
    row_count_total: int = 0
    output_size_bytes_total: int = 0
    checksum_verified: bool = False
    row_count_verified: bool = False
    warnings: tuple[str, ...] = ()

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "ready": self.ready,
            "manifest_present": self.manifest_present,
            "release_id": self.release_id,
            "manifest_schema_version": self.manifest_schema_version,
            "source_ids": list(self.source_ids),
            "source_versions": dict(self.source_versions or {}),
            "layer_counts": dict(self.layer_counts or {}),
            "partition_count": self.partition_count,
            "artifact_count": self.artifact_count,
            "row_count_total": self.row_count_total,
            "output_size_bytes_total": self.output_size_bytes_total,
            "checksum_verified": self.checksum_verified,
            "row_count_verified": self.row_count_verified,
            "layout_root": "data/bio_assets/analytical",
            "layout_pattern": "{bronze,silver,gold}/<release>/chrom=<chrom>/",
            "startup_download_allowed": False,
            "request_time_materialization_allowed": False,
            "source_runtime_scan_allowed": False,
            "secret_values_emitted": False,
            "local_path_values_emitted": False,
            "object_uri_values_emitted": False,
            "notices": list(self.warnings),
        }


class DuckDbAnalyticalAdapter:
    """Per-worker read-only DuckDB connection for analytical/batch workloads."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.database_path = _settings_path(settings, settings.duckdb_analytical_database_path)
        self.temp_directory = _settings_path(settings, settings.duckdb_analytical_temp_directory)
        self.memory_limit = str(settings.duckdb_analytical_memory_limit or "1500MB")
        self.threads = max(1, int(settings.duckdb_analytical_threads or 1))
        self._connection: Any | None = None
        self._lock = Lock()

    def connection(self):
        if self._connection is not None:
            return self._connection

        with self._lock:
            if self._connection is not None:
                return self._connection
            inspection = inspect_duckdb_analytical_adapter(self.settings)
            if not inspection.ready:
                raise RuntimeError(f"DuckDB analytical adapter is not ready: {inspection.status}")
            self.temp_directory.mkdir(parents=True, exist_ok=True)
            duckdb = importlib.import_module("duckdb")
            config = {
                "access_mode": "READ_ONLY",
                "memory_limit": self.memory_limit,
                "threads": str(self.threads),
                "temp_directory": str(self.temp_directory),
            }
            self._connection = duckdb.connect(
                database=str(self.database_path),
                read_only=True,
                config=config,
            )
            return self._connection

    def query(
        self,
        sql: str,
        parameters: Sequence[Any] | Mapping[str, Any] | None = None,
        *,
        max_rows: int | None = 10_000,
    ) -> list[dict[str, Any]]:
        cursor = self.connection().cursor()
        try:
            if parameters is None:
                cursor.execute(sql)
            else:
                cursor.execute(sql, parameters)
            description = cursor.description or ()
            if not description:
                return []
            columns = [column[0] for column in description]
            rows = cursor.fetchall() if max_rows is None else cursor.fetchmany(max_rows)
            return [dict(zip(columns, row, strict=False)) for row in rows]
        finally:
            close = getattr(cursor, "close", None)
            if close is not None:
                close()

    def close(self) -> None:
        with self._lock:
            if self._connection is None:
                return
            close = getattr(self._connection, "close", None)
            if close is not None:
                close()
            self._connection = None


def inspect_duckdb_analytical_adapter(settings: Settings) -> DuckDbAnalyticalInspection:
    enabled = bool(settings.duckdb_analytical_enabled)
    database_path = _settings_path(settings, settings.duckdb_analytical_database_path)
    temp_directory = _settings_path(settings, settings.duckdb_analytical_temp_directory)
    database_present = database_path.is_file()
    database_size_bytes = database_path.stat().st_size if database_present else None
    available = _duckdb_module_available()
    memory_limit = str(settings.duckdb_analytical_memory_limit or "1500MB")
    threads = max(1, int(settings.duckdb_analytical_threads or 1))
    warnings: list[str] = []
    if threads > 2:
        warnings.append("duckdb_threads_above_render_standard_default")
    release = inspect_duckdb_analytical_release(
        settings,
        verify_checksums=False,
    ).to_sanitized_dict()

    if not enabled:
        return DuckDbAnalyticalInspection(
            source_id=DUCKDB_ANALYTICAL_SOURCE_ID,
            status="disabled",
            ready=False,
            enabled=False,
            available=available,
            database_present=database_present,
            database_size_bytes=database_size_bytes,
            database_path_configured=bool(settings.duckdb_analytical_database_path),
            temp_directory_configured=bool(settings.duckdb_analytical_temp_directory),
            memory_limit=memory_limit,
            threads=threads,
            message="DuckDB analytical adapter disabled; tabix/SQLite remain the point lookup path.",
            warnings=tuple(warnings),
            release=release,
        )

    if not available:
        warnings.append("duckdb_dependency_missing")
        return DuckDbAnalyticalInspection(
            source_id=DUCKDB_ANALYTICAL_SOURCE_ID,
            status="dependency_missing",
            ready=False,
            enabled=True,
            available=False,
            database_present=database_present,
            database_size_bytes=database_size_bytes,
            database_path_configured=bool(settings.duckdb_analytical_database_path),
            temp_directory_configured=bool(settings.duckdb_analytical_temp_directory),
            memory_limit=memory_limit,
            threads=threads,
            message="Install the duckdb Python package before enabling the analytical adapter.",
            warnings=tuple(warnings),
            release=release,
        )

    if not database_present:
        warnings.append("duckdb_database_missing")
        return DuckDbAnalyticalInspection(
            source_id=DUCKDB_ANALYTICAL_SOURCE_ID,
            status="database_missing",
            ready=False,
            enabled=True,
            available=True,
            database_present=False,
            database_size_bytes=None,
            database_path_configured=bool(settings.duckdb_analytical_database_path),
            temp_directory_configured=bool(settings.duckdb_analytical_temp_directory),
            memory_limit=memory_limit,
            threads=threads,
            message="Materialize the local DuckDB database before enabling analytical reads.",
            warnings=tuple(warnings),
            release=release,
        )

    temp_parent_exists = temp_directory.parent.exists()
    if not temp_parent_exists:
        warnings.append("duckdb_temp_directory_parent_missing")

    return DuckDbAnalyticalInspection(
        source_id=DUCKDB_ANALYTICAL_SOURCE_ID,
        status="ready" if temp_parent_exists else "temp_directory_parent_missing",
        ready=temp_parent_exists,
        enabled=True,
        available=True,
        database_present=True,
        database_size_bytes=database_size_bytes,
        database_path_configured=bool(settings.duckdb_analytical_database_path),
        temp_directory_configured=bool(settings.duckdb_analytical_temp_directory),
        memory_limit=memory_limit,
        threads=threads,
        message=(
            "DuckDB analytical adapter ready for batch/reporting workloads."
            if temp_parent_exists
            else "Create the DuckDB temp-directory parent on the persistent disk."
        ),
        warnings=tuple(warnings),
        release=release,
    )


def inspect_duckdb_analytical_release(
    settings: Settings,
    *,
    verify_checksums: bool = True,
) -> DuckDbAnalyticalReleaseInspection:
    """Validate the local analytical release manifest without building artifacts."""

    release_root = _settings_path(settings, settings.duckdb_analytical_release_root)
    manifest_path = _settings_path(settings, settings.duckdb_analytical_release_manifest_path)
    if not manifest_path.is_file():
        return DuckDbAnalyticalReleaseInspection(
            source_id=DUCKDB_ANALYTICAL_SOURCE_ID,
            status="manifest_missing",
            ready=False,
            manifest_present=False,
            release_id=None,
            manifest_schema_version=None,
            warnings=("duckdb_analytical_release_manifest_missing",),
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DuckDbAnalyticalReleaseInspection(
            source_id=DUCKDB_ANALYTICAL_SOURCE_ID,
            status="manifest_invalid",
            ready=False,
            manifest_present=True,
            release_id=None,
            manifest_schema_version=None,
            warnings=("duckdb_analytical_release_manifest_unreadable",),
        )
    if not isinstance(manifest, dict):
        return DuckDbAnalyticalReleaseInspection(
            source_id=DUCKDB_ANALYTICAL_SOURCE_ID,
            status="manifest_invalid",
            ready=False,
            manifest_present=True,
            release_id=None,
            manifest_schema_version=None,
            warnings=("duckdb_analytical_release_manifest_not_object",),
        )

    release_id = _text_or_none(manifest.get("release_id"))
    schema_version = _text_or_none(manifest.get("schema_version"))
    manifest_source_ids = manifest.get("source_ids")
    source_ids = (
        tuple(sorted({str(value) for value in manifest_source_ids if str(value).strip()}))
        if isinstance(manifest_source_ids, list)
        else ()
    )
    source_versions = manifest.get("source_versions")
    if not isinstance(source_versions, dict):
        source_versions = {}
    artifacts = manifest.get("artifacts")
    warnings: list[str] = []
    if schema_version != DUCKDB_ANALYTICAL_RELEASE_MANIFEST_SCHEMA_VERSION:
        warnings.append("duckdb_analytical_release_manifest_schema_mismatch")
    if not release_id:
        warnings.append("duckdb_analytical_release_id_missing")
    if not isinstance(artifacts, list) or not artifacts:
        warnings.append("duckdb_analytical_release_artifacts_missing")
        artifacts = []

    layer_counts = {layer: 0 for layer in DUCKDB_ANALYTICAL_RELEASE_LAYERS}
    partitions: set[tuple[str, str]] = set()
    row_count_total = 0
    output_size_total = 0
    checksums_checked = 0
    checksums_ok = 0
    row_counts_checked = 0
    row_counts_ok = 0

    for artifact in artifacts:
        if not isinstance(artifact, dict):
            warnings.append("duckdb_analytical_release_artifact_not_object")
            continue
        relative_path = _text_or_none(artifact.get("path") or artifact.get("relative_path"))
        layer = _text_or_none(artifact.get("layer"))
        chrom = _text_or_none(artifact.get("chrom"))
        expected_sha256 = _text_or_none(artifact.get("sha256"))
        row_count = artifact.get("row_count")
        if not relative_path:
            warnings.append("duckdb_analytical_release_artifact_path_missing")
            continue
        safe_relative = _safe_relative_path(relative_path)
        if safe_relative is None:
            warnings.append("duckdb_analytical_release_artifact_path_invalid")
            continue
        layout = _artifact_layout(safe_relative)
        if (
            release_id
            and (
                layout is None
                or layout["layer"] not in DUCKDB_ANALYTICAL_RELEASE_LAYERS
                or layout["release_id"] != release_id
                or not layout["chrom"]
            )
        ):
            warnings.append("duckdb_analytical_release_artifact_layout_invalid")
        if layer and layout is not None and layer != layout["layer"]:
            warnings.append("duckdb_analytical_release_artifact_layer_mismatch")
        if chrom and layout is not None and chrom != layout["chrom"]:
            warnings.append("duckdb_analytical_release_artifact_chrom_mismatch")
        if layout is not None and layout["layer"] in layer_counts:
            layer_counts[layout["layer"]] += 1
            partitions.add((layout["layer"], layout["chrom"]))

        artifact_path = release_root / safe_relative
        if not artifact_path.is_file():
            warnings.append("duckdb_analytical_release_artifact_missing")
            continue
        output_size_total += artifact_path.stat().st_size
        if verify_checksums:
            checksums_checked += 1
            if expected_sha256 and _sha256_file(artifact_path) == expected_sha256:
                checksums_ok += 1
            else:
                warnings.append("duckdb_analytical_release_artifact_checksum_mismatch")
        if isinstance(row_count, int) and row_count >= 0:
            row_counts_checked += 1
            row_counts_ok += 1
            row_count_total += row_count
        else:
            warnings.append("duckdb_analytical_release_artifact_row_count_invalid")

    manifest_row_count_total = manifest.get("row_count_total")
    if isinstance(manifest_row_count_total, int) and manifest_row_count_total >= 0:
        if manifest_row_count_total != row_count_total:
            warnings.append("duckdb_analytical_release_manifest_row_count_mismatch")
        else:
            row_counts_checked += 1
            row_counts_ok += 1

    manifest_required_layers = manifest.get("required_layers")
    required_layers = (
        tuple(str(layer) for layer in manifest_required_layers)
        if isinstance(manifest_required_layers, list)
        else DUCKDB_ANALYTICAL_RELEASE_LAYERS
    )
    missing_layers = [
        layer
        for layer in required_layers
        if layer in DUCKDB_ANALYTICAL_RELEASE_LAYERS and layer_counts.get(layer, 0) == 0
    ]
    if missing_layers:
        warnings.append("duckdb_analytical_release_required_layer_missing")

    checksum_verified = checksums_checked > 0 and checksums_checked == checksums_ok
    checksum_passed = checksum_verified if verify_checksums else True
    row_count_verified = row_counts_checked > 0 and row_counts_checked == row_counts_ok
    blocking_warnings = list(warnings)
    ready = (
        bool(artifacts)
        and schema_version == DUCKDB_ANALYTICAL_RELEASE_MANIFEST_SCHEMA_VERSION
        and bool(release_id)
        and not blocking_warnings
        and checksum_passed
        and row_count_verified
    )
    return DuckDbAnalyticalReleaseInspection(
        source_id=DUCKDB_ANALYTICAL_SOURCE_ID,
        status="ready" if ready else "validation_failed",
        ready=ready,
        manifest_present=True,
        release_id=release_id,
        manifest_schema_version=schema_version,
        source_ids=source_ids,
        source_versions=source_versions,
        layer_counts=layer_counts,
        partition_count=len(partitions),
        artifact_count=sum(layer_counts.values()),
        row_count_total=row_count_total,
        output_size_bytes_total=output_size_total,
        checksum_verified=checksum_verified,
        row_count_verified=row_count_verified,
        warnings=tuple(_dedupe(warnings)),
    )


def _duckdb_module_available() -> bool:
    try:
        return importlib.util.find_spec("duckdb") is not None
    except (ImportError, ValueError):
        return False


def _settings_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def _text_or_none(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _safe_relative_path(value: str) -> Path | None:
    candidate = Path(value)
    if candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        return None
    return candidate


def _artifact_layout(relative_path: Path) -> dict[str, str] | None:
    parts = relative_path.parts
    if len(parts) < 4:
        return None
    layer, release_id, chrom_part = parts[0], parts[1], parts[2]
    if layer not in DUCKDB_ANALYTICAL_RELEASE_LAYERS or not chrom_part.startswith("chrom="):
        return None
    chrom = chrom_part.partition("=")[2]
    if not release_id or not chrom:
        return None
    return {"layer": layer, "release_id": release_id, "chrom": chrom}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
