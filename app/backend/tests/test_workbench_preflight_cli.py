from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.cli.eamos_workbench_preflight import main
from app.services.gene_viewer import GeneViewerFixtureProvider


def test_workbench_preflight_reports_fixture_timings(tmp_path: Path, capsys) -> None:
    exit_code = main(
        [
            "--iterations",
            "1",
            "--cache-db",
            str(tmp_path / "missing.db"),
            "--compact",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "fixture"
    assert output["guardrails"]["network"] == "not_used"
    assert output["caches"]["state"] == "missing"

    timings = {item["gene"]: item for item in output["full_gene_viewer"]}
    assert timings["RPE65"]["state"] == "ok"
    assert timings["RPE65"]["locus_bp"] == 21139
    assert timings["ABCA4"]["state"] == "ok"
    assert timings["ABCA4"]["locus_bp"] == 128315
    assert timings["ABCA4"]["load_ms"]["first"] is not None
    assert (
        timings["ABCA4"]["estimated_rows_at_min_hint"]
        > timings["RPE65"]["estimated_rows_at_min_hint"]
    )


def test_workbench_preflight_summarizes_sqlite_caches(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "cache.db"
    now = datetime.now(timezone.utc)
    future = (now + timedelta(days=1)).isoformat()
    past = (now - timedelta(days=1)).isoformat()
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE variant_cache (query_string TEXT, created_at TEXT)")
        connection.execute(
            "INSERT INTO variant_cache (query_string, created_at) VALUES (?, ?)",
            ("RPE65:c.260A>G", now.isoformat()),
        )
        connection.execute(
            "CREATE TABLE source_cache "
            "(source TEXT, status TEXT, source_version TEXT, fetched_at TEXT, expires_at TEXT)"
        )
        connection.execute(
            "INSERT INTO source_cache VALUES (?, ?, ?, ?, ?)",
            ("clingen", "live", "2026-05", now.isoformat(), future),
        )
        connection.execute(
            "INSERT INTO source_cache VALUES (?, ?, ?, ?, ?)",
            ("pubmed", "stale", None, past, past),
        )

    exit_code = main(["--iterations", "1", "--cache-db", str(db_path), "--compact"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["caches"]["state"] == "present"
    assert output["caches"]["variant_cache"]["rows"] == 1
    assert output["caches"]["source_cache"]["rows"] == 2
    assert output["caches"]["source_cache"]["fresh_rows"] == 1
    assert output["caches"]["source_cache"]["sources"]["clingen"]["status_counts"] == {"live": 1}


def test_gene_viewer_fixture_provider_caches_large_json(tmp_path: Path) -> None:
    fixture = tmp_path / "sample.json"
    fixture.write_text('{"version": 1}', encoding="utf-8")
    provider = GeneViewerFixtureProvider(fixtures_dir=tmp_path)

    first = provider._load("sample.json")
    fixture.write_text('{"version": 2}', encoding="utf-8")
    second = provider._load("sample.json")

    assert first is second
    assert second["version"] == 1
