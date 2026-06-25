from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from app.cli.eamos_duckdb_analytical_preflight import main as duckdb_preflight_main
from app.core.config import Settings
import app.services.duckdb_analytical as duckdb_analytical
from app.services.duckdb_analytical import (
    DuckDbAnalyticalAdapter,
    DUCKDB_ANALYTICAL_RELEASE_MANIFEST_SCHEMA_VERSION,
    inspect_duckdb_analytical_release,
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


def test_duckdb_analytical_release_missing_manifest_is_sanitized(tmp_path: Path):
    settings = Settings(
        jwt_secret="test-secret",
        duckdb_analytical_release_root=tmp_path / "analytical",
        duckdb_analytical_release_manifest_path=tmp_path / "analytical" / "missing.json",
    )

    payload = inspect_duckdb_analytical_release(settings).to_sanitized_dict()

    assert payload["ready"] is False
    assert payload["status"] == "manifest_missing"
    assert payload["manifest_present"] is False
    assert payload["local_path_values_emitted"] is False
    assert str(tmp_path).lower() not in json.dumps(payload).lower()


def test_duckdb_analytical_release_validates_tiny_fixture_without_paths(
    tmp_path: Path,
    capsys,
) -> None:
    root, manifest_path = _write_tiny_release(tmp_path)
    settings = Settings(
        jwt_secret="test-secret",
        duckdb_analytical_release_root=root,
        duckdb_analytical_release_manifest_path=manifest_path,
    )

    payload = inspect_duckdb_analytical_release(settings).to_sanitized_dict()

    assert payload["ready"] is True
    assert payload["status"] == "ready"
    assert payload["release_id"] == "pytest-mini"
    assert payload["manifest_schema_version"] == DUCKDB_ANALYTICAL_RELEASE_MANIFEST_SCHEMA_VERSION
    assert payload["source_ids"] == ["clinvar", "dbsnp"]
    assert payload["source_versions"] == {"clinvar": "pytest", "dbsnp": "pytest"}
    assert payload["layer_counts"] == {"bronze": 1, "silver": 1, "gold": 1}
    assert payload["partition_count"] == 3
    assert payload["artifact_count"] == 3
    assert payload["row_count_total"] == 6
    assert payload["checksum_verified"] is True
    assert payload["row_count_verified"] is True
    assert payload["local_path_values_emitted"] is False
    assert str(tmp_path).lower() not in json.dumps(payload).lower()

    exit_code = duckdb_preflight_main(
        [
            "--release-root",
            str(root),
            "--manifest-path",
            str(manifest_path),
            "--compact",
            "--require-ready",
        ]
    )
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert '"ready": true' in captured
    assert '"local_path_values_emitted": false' in captured
    assert str(tmp_path).lower() not in captured.lower()


def test_duckdb_analytical_release_checksum_mismatch_fails_closed(tmp_path: Path) -> None:
    root, manifest_path = _write_tiny_release(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    settings = Settings(
        jwt_secret="test-secret",
        duckdb_analytical_release_root=root,
        duckdb_analytical_release_manifest_path=manifest_path,
    )

    payload = inspect_duckdb_analytical_release(settings).to_sanitized_dict()

    assert payload["ready"] is False
    assert payload["status"] == "validation_failed"
    assert payload["checksum_verified"] is False
    assert "duckdb_analytical_release_artifact_checksum_mismatch" in payload["notices"]


def _write_tiny_release(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "analytical"
    release_id = "pytest-mini"
    artifacts = [
        ("bronze", "1", "clinvar-bronze.parquet", b"bronze-clinvar\n", 1),
        ("silver", "1", "clinvar-silver.parquet", b"silver-clinvar\n", 2),
        ("gold", "2", "clinvar-dbsnp-gold.parquet", b"gold-join\n", 3),
    ]
    manifest_artifacts = []
    for layer, chrom, filename, content, row_count in artifacts:
        relative_path = f"{layer}/{release_id}/chrom={chrom}/{filename}"
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        manifest_artifacts.append(
            {
                "path": relative_path,
                "layer": layer,
                "chrom": chrom,
                "format": "parquet",
                "source_id": "clinvar" if layer != "gold" else "clinvar_dbsnp_gold",
                "schema_version": "pytest.v1",
                "row_count": row_count,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )

    manifest = {
        "schema_version": DUCKDB_ANALYTICAL_RELEASE_MANIFEST_SCHEMA_VERSION,
        "release_id": release_id,
        "source_ids": ["clinvar", "dbsnp"],
        "source_versions": {"clinvar": "pytest", "dbsnp": "pytest"},
        "input_checksums": {"clinvar": "sha256:fixture", "dbsnp": "sha256:fixture"},
        "build": {"command": "pytest tiny fixture", "host": "pytest"},
        "required_layers": ["bronze", "silver", "gold"],
        "row_count_total": 6,
        "artifacts": manifest_artifacts,
    }
    manifest_path = root / "manifests" / "current.manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return root, manifest_path
