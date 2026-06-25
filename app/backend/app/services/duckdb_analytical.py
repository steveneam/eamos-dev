from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import importlib
import importlib.util
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import Settings

DUCKDB_ANALYTICAL_SOURCE_ID = "eamos_duckdb_analytical"
DUCKDB_ANALYTICAL_SCHEMA_VERSION = "eamos.duckdb_analytical.v1"
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
    )


def _duckdb_module_available() -> bool:
    try:
        return importlib.util.find_spec("duckdb") is not None
    except (ImportError, ValueError):
        return False


def _settings_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path
