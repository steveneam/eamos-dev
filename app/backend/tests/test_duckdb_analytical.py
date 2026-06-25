from __future__ import annotations

import sys
from types import SimpleNamespace

from app.core.config import Settings
import app.services.duckdb_analytical as duckdb_analytical
from app.services.duckdb_analytical import (
    DuckDbAnalyticalAdapter,
    inspect_duckdb_analytical_adapter,
)


def test_duckdb_analytical_inspection_disabled_is_sanitized(tmp_path):
    settings = Settings(
        jwt_secret="test-secret",
        duckdb_analytical_enabled=False,
        duckdb_analytical_database_path=tmp_path / "missing.duckdb",
        duckdb_analytical_temp_directory=tmp_path / "duckdb-tmp",
    )

    payload = inspect_duckdb_analytical_adapter(settings).to_sanitized_dict()

    assert payload["status"] == "disabled"
    assert payload["ready"] is False
    assert payload["enabled"] is False
    assert payload["access_mode"] == "READ_ONLY"
    assert payload["point_lookup_engine"] == "tabix_sqlite_report_cache"
    assert payload["single_coordinate_hot_path_allowed"] is False
    assert payload["request_time_materialization_allowed"] is False
    assert payload["startup_download_allowed"] is False
    assert payload["remote_httpfs_allowed"] is False
    assert payload["motherduck_allowed"] is False
    assert payload["local_path_values_emitted"] is False
    assert "database_path" not in payload
    assert "temp_directory" not in payload


def test_duckdb_analytical_enabled_missing_database(monkeypatch, tmp_path):
    monkeypatch.setattr(duckdb_analytical, "_duckdb_module_available", lambda: True)
    settings = Settings(
        jwt_secret="test-secret",
        duckdb_analytical_enabled=True,
        duckdb_analytical_database_path=tmp_path / "missing.duckdb",
        duckdb_analytical_temp_directory=tmp_path / "duckdb-tmp",
    )

    payload = inspect_duckdb_analytical_adapter(settings).to_sanitized_dict()

    assert payload["status"] == "database_missing"
    assert payload["ready"] is False
    assert payload["enabled"] is True
    assert payload["available"] is True
    assert payload["database_present"] is False
    assert "duckdb_database_missing" in payload["notices"]


def test_duckdb_analytical_adapter_opens_read_only_and_uses_cursor(monkeypatch, tmp_path):
    database_path = tmp_path / "eamos-reference.duckdb"
    database_path.write_bytes(b"duckdb")
    temp_directory = tmp_path / "duckdb-tmp"
    calls: dict[str, object] = {}

    class FakeCursor:
        description = [("answer",)]

        def execute(self, sql, parameters=None):
            calls["sql"] = sql
            calls["parameters"] = parameters
            return self

        def fetchmany(self, max_rows):
            calls["max_rows"] = max_rows
            return [(7,)]

        def close(self):
            calls["cursor_closed"] = True

    class FakeConnection:
        def cursor(self):
            calls["cursor_requested"] = True
            return FakeCursor()

        def close(self):
            calls["connection_closed"] = True

    def connect(*, database, read_only, config):
        calls["database"] = database
        calls["read_only"] = read_only
        calls["config"] = dict(config)
        return FakeConnection()

    monkeypatch.setitem(sys.modules, "duckdb", SimpleNamespace(connect=connect))
    monkeypatch.setattr(duckdb_analytical, "_duckdb_module_available", lambda: True)
    settings = Settings(
        jwt_secret="test-secret",
        duckdb_analytical_enabled=True,
        duckdb_analytical_database_path=database_path,
        duckdb_analytical_temp_directory=temp_directory,
        duckdb_analytical_memory_limit="1500MB",
        duckdb_analytical_threads=2,
    )

    adapter = DuckDbAnalyticalAdapter(settings)
    rows = adapter.query("select ? as answer", [7], max_rows=1)
    adapter.close()

    assert rows == [{"answer": 7}]
    assert calls["database"] == str(database_path)
    assert calls["read_only"] is True
    assert calls["config"] == {
        "access_mode": "READ_ONLY",
        "memory_limit": "1500MB",
        "threads": "2",
        "temp_directory": str(temp_directory),
    }
    assert calls["cursor_requested"] is True
    assert calls["sql"] == "select ? as answer"
    assert calls["parameters"] == [7]
    assert calls["max_rows"] == 1
    assert calls["cursor_closed"] is True
    assert calls["connection_closed"] is True
    assert temp_directory.is_dir()
