from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.duckdb_analytical import inspect_duckdb_analytical_release


def build_duckdb_analytical_preflight_report(
    *,
    settings: Settings,
    verify_checksums: bool = True,
    generated_at: str | None = None,
) -> dict[str, Any]:
    inspection = inspect_duckdb_analytical_release(
        settings,
        verify_checksums=verify_checksums,
    ).to_sanitized_dict()
    return {
        "mode": "duckdb_analytical_release_preflight",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "ready": inspection["ready"],
        "status": inspection["status"],
        "release": inspection,
        "guardrails": {
            "network_used": False,
            "mutations_performed": False,
            "render_env_changed": False,
            "supabase_mutation_performed": False,
            "duckdb_database_opened": False,
            "multi_gb_materialization_performed": False,
            "startup_downloads_allowed": False,
            "request_time_materialization_allowed": False,
            "secret_values_emitted": False,
            "local_path_values_emitted": False,
            "object_uri_values_emitted": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only DuckDB/Parquet analytical release preflight. Validates the "
            "manifest, medallion layout, row-count totals, and checksums without "
            "network calls, database writes, or materialization."
        )
    )
    parser.add_argument("--release-root", type=Path)
    parser.add_argument("--manifest-path", type=Path)
    parser.add_argument("--skip-checksum", action="store_true")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    args = parser.parse_args(argv)

    settings_kwargs: dict[str, Any] = {"jwt_secret": "duckdb-analytical-preflight-local"}
    if args.release_root is not None:
        settings_kwargs["duckdb_analytical_release_root"] = args.release_root
    if args.manifest_path is not None:
        settings_kwargs["duckdb_analytical_release_manifest_path"] = args.manifest_path
    settings = Settings(**settings_kwargs)
    report = build_duckdb_analytical_preflight_report(
        settings=settings,
        verify_checksums=not args.skip_checksum,
    )
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0 if report["ready"] or not args.require_ready else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
