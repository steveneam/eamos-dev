from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from app.core.config import Settings
from app.schemas.gene_viewer import GeneViewerRequest, ViewerWindowRequest
from app.services.gene_viewer import GeneViewerError, GeneViewerService

DEFAULT_CASES: tuple[tuple[str, str, str], ...] = (
    ("RPE65", "c.260A>G", "NM_000329.3"),
    ("ABCA4", "c.5435T>A", "NM_000350.3"),
)
FIXTURE_FILES: tuple[str, ...] = (
    "workbench/viewer_rpe65.json",
    "workbench/gene_viewer_transcript_models.json",
    "lookup_v2_modules.json",
    "tools/clinvar_fixtures.json",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fixture-only Workbench/evidence freshness and full-gene preflight."
    )
    parser.add_argument("--iterations", type=int, default=3, help="viewer timing iterations")
    parser.add_argument("--cache-db", type=Path, help="optional SQLite cache database to inspect")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    args = parser.parse_args(argv)

    settings = Settings(jwt_secret="preflight-local", use_real_apis=False)
    cache_db = args.cache_db or _sqlite_path_from_settings(settings)
    report = {
        "mode": "fixture",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "guardrails": {
            "use_real_apis": False,
            "network": "not_used",
            "runtime_local_source_wiring": "not_used",
            "production_downloads": "not_used",
            "supabase": "not_used",
        },
        "fixtures": _fixture_freshness(settings.fixtures_root),
        "caches": _cache_summary(cache_db),
        "full_gene_viewer": _full_gene_timings(settings, max(1, args.iterations)),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0


def _fixture_freshness(fixtures_root: Path) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    results: dict[str, Any] = {}
    for rel_name in FIXTURE_FILES:
        path = fixtures_root / rel_name
        if not path.exists():
            results[rel_name] = {"state": "missing", "path": str(path)}
            continue
        stat = path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        results[rel_name] = {
            "state": "present",
            "path": str(path),
            "size_bytes": stat.st_size,
            "mtime": mtime.isoformat(),
            "age_hours": round((now - mtime).total_seconds() / 3600, 3),
            "sha256_12": _sha256_prefix(path),
        }
    return results


def _sha256_prefix(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()[:12]


def _sqlite_path_from_settings(settings: Settings) -> Path | None:
    for prefix in ("sqlite+pysqlite:///", "sqlite:///"):
        if settings.database_url.startswith(prefix):
            raw = settings.database_url[len(prefix) :]
            path = Path(raw)
            return path if path.is_absolute() else settings.backend_root / path
    return None


def _cache_summary(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"state": "skipped", "reason": "non_sqlite_database_url"}
    if not path.exists():
        return {"state": "missing", "path": str(path)}

    uri = f"file:{path.as_posix()}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            return {
                "state": "present",
                "path": str(path),
                "variant_cache": _variant_cache_summary(connection, tables),
                "source_cache": _source_cache_summary(connection, tables),
            }
    except sqlite3.Error as exc:
        return {"state": "unreadable", "path": str(path), "error": str(exc)}


def _variant_cache_summary(connection: sqlite3.Connection, tables: set[str]) -> dict[str, Any]:
    if "variant_cache" not in tables:
        return {"state": "missing_table"}
    row = connection.execute(
        "SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM variant_cache"
    ).fetchone()
    return {
        "state": "present",
        "rows": int(row[0] or 0),
        "oldest_created_at": row[1],
        "latest_created_at": row[2],
    }


def _source_cache_summary(connection: sqlite3.Connection, tables: set[str]) -> dict[str, Any]:
    if "source_cache" not in tables:
        return {"state": "missing_table"}
    now = datetime.now(timezone.utc).isoformat()
    rows = connection.execute(
        "SELECT source, status, source_version, fetched_at, expires_at FROM source_cache"
    ).fetchall()
    sources: dict[str, dict[str, Any]] = {}
    fresh_rows = 0
    versioned_rows = 0
    for source, status, source_version, fetched_at, expires_at in rows:
        source_summary = sources.setdefault(
            str(source),
            {
                "rows": 0,
                "fresh_rows": 0,
                "status_counts": {},
                "latest_fetched_at": None,
            },
        )
        source_summary["rows"] += 1
        source_summary["status_counts"][str(status)] = (
            source_summary["status_counts"].get(str(status), 0) + 1
        )
        if expires_at and str(expires_at) > now:
            fresh_rows += 1
            source_summary["fresh_rows"] += 1
        if source_version:
            versioned_rows += 1
        if fetched_at and (
            source_summary["latest_fetched_at"] is None
            or str(fetched_at) > source_summary["latest_fetched_at"]
        ):
            source_summary["latest_fetched_at"] = str(fetched_at)

    return {
        "state": "present",
        "rows": len(rows),
        "fresh_rows": fresh_rows,
        "stale_rows": len(rows) - fresh_rows,
        "versioned_rows": versioned_rows,
        "sources": dict(sorted(sources.items())),
    }


def _full_gene_timings(settings: Settings, iterations: int) -> list[dict[str, Any]]:
    service = GeneViewerService(settings=settings)
    results = []
    for gene, cdna, transcript in DEFAULT_CASES:
        request = GeneViewerRequest(
            gene=gene,
            cdna=cdna,
            transcript=transcript,
            window=ViewerWindowRequest(kind="full_gene"),
        )
        load_ms: list[float] = []
        serialize_ms: list[float] = []
        last_payload = None
        error: dict[str, Any] | None = None
        for _ in range(iterations):
            try:
                start = perf_counter()
                response = service.build_viewer(request)
                load_ms.append(_elapsed_ms(start))
                start = perf_counter()
                last_payload = response.model_dump_json()
                serialize_ms.append(_elapsed_ms(start))
            except GeneViewerError as exc:
                error = exc.to_http_detail()
                break
        results.append(
            _timing_result(
                gene=gene,
                cdna=cdna,
                transcript=transcript,
                response_json=last_payload,
                load_ms=load_ms,
                serialize_ms=serialize_ms,
                error=error,
            )
        )
    return results


def _elapsed_ms(start: float) -> float:
    return (perf_counter() - start) * 1000


def _timing_result(
    *,
    gene: str,
    cdna: str,
    transcript: str,
    response_json: str | None,
    load_ms: list[float],
    serialize_ms: list[float],
    error: dict[str, Any] | None,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "gene": gene,
        "cdna": cdna,
        "transcript": transcript,
        "iterations": len(load_ms),
        "load_ms": _metric(load_ms),
        "serialize_ms": _metric(serialize_ms),
    }
    if error is not None:
        base["state"] = "error"
        base["error"] = error
        return base
    if response_json is None:
        base["state"] = "empty"
        return base
    payload = json.loads(response_json)
    full_locus = payload.get("full_locus") or {}
    locus = full_locus.get("locus") or {}
    hints = full_locus.get("rendering_hints") or {}
    sequence = str(locus.get("sequence") or "")
    bases_per_row = int(hints.get("bases_per_row_min") or 80)
    base.update(
        {
            "state": "ok",
            "locus_bp": len(sequence),
            "json_bytes": len(response_json.encode("utf-8")),
            "estimated_rows_at_min_hint": (
                math.ceil(len(sequence) / bases_per_row) if sequence else 0
            ),
            "bases_per_row_min": bases_per_row,
            "feature_intervals": len(full_locus.get("feature_intervals") or []),
            "codon_starts": len(
                ((full_locus.get("transcript_projection") or {}).get("codon_starts") or [])
            ),
        }
    )
    return base


def _metric(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"first": None, "min": None, "avg": None, "max": None}
    return {
        "first": round(values[0], 3),
        "min": round(min(values), 3),
        "avg": round(sum(values) / len(values), 3),
        "max": round(max(values), 3),
    }


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
