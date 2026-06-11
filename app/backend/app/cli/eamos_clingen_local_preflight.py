from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.clingen_local import inspect_clingen_local_store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only ClinGen local source-asset preflight. Output is sanitized "
            "and never includes local paths, secrets, object URIs, or source rows."
        )
    )
    parser.add_argument("--db-path", type=Path)
    parser.add_argument("--manifest-path", type=Path)
    parser.add_argument("--enabled", action="store_true")
    parser.add_argument("--skip-checksum", action="store_true")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    args = parser.parse_args(argv)

    settings_kwargs: dict[str, Any] = {"jwt_secret": "clingen-local-preflight-local"}
    if args.db_path is not None:
        settings_kwargs["clingen_local_sqlite_path"] = args.db_path
    if args.manifest_path is not None:
        settings_kwargs["clingen_local_manifest_path"] = args.manifest_path
    if args.enabled:
        settings_kwargs["clingen_local_enabled"] = True
    settings = Settings(**settings_kwargs)

    inspection = inspect_clingen_local_store(settings, verify_checksum=not args.skip_checksum)
    report = {
        "mode": "clingen_local_preflight",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ready": inspection.ready,
        "status": inspection.status,
        "enabled": inspection.enabled,
        "schema_version": inspection.schema_version,
        "source_version": inspection.source_version,
        "classification_count": inspection.classification_count,
        "cspec_entity_count": inspection.cspec_entity_count,
        "cspec_link_count": inspection.cspec_link_count,
        "checksum_verified": inspection.checksum_verified,
        "startup_download_allowed": False,
        "request_time_materialization_allowed": False,
        "secret_values_emitted": False,
        "local_path_values_emitted": False,
        "raw_source_rows_emitted": False,
        "warnings": list(inspection.warnings),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0 if inspection.ready or not args.require_ready else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
