from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.clingen_local import materialize_clingen_local_store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize local ClinGen eRepo/CSpec source rows through an explicit "
            "off-startup action. Output is sanitized and never includes source rows, "
            "local paths, API keys, object URIs, signed URLs, or secrets."
        )
    )
    parser.add_argument("--from-erepo-jsonl-file", action="append", type=Path, default=[])
    parser.add_argument("--from-cspec-jsonl-file", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--source-version")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    args = parser.parse_args(argv)

    settings_kwargs: dict[str, Any] = {"jwt_secret": "clingen-local-materialize-local"}
    if args.output is not None:
        settings_kwargs["clingen_local_sqlite_path"] = args.output
    if args.manifest is not None:
        settings_kwargs["clingen_local_manifest_path"] = args.manifest
    settings = Settings(**settings_kwargs)

    result = materialize_clingen_local_store(
        settings,
        erepo_jsonl_files=args.from_erepo_jsonl_file,
        cspec_jsonl_files=args.from_cspec_jsonl_file,
        output_path=args.output,
        manifest_path=args.manifest,
        source_version=args.source_version,
        force=args.force,
    )
    report = {
        "mode": "clingen_local_materialize",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "guardrails": {
            "startup_download": "not_used",
            "request_time_materialization": "not_used",
            "patient_data": "not_used",
            "network": {"used": False, "provider": None},
            "secrets_in_output": "blocked",
            "local_paths_in_output": "blocked",
            "raw_source_rows_in_output": "blocked",
        },
        "materialization": result.to_sanitized_dict(),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0 if result.ready or not args.require_ready else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
