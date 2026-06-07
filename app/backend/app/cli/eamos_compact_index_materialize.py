from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.compact_coordinate_index_materialization import (
    materialize_compact_coordinate_index,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize the compact coordinate index through an explicit "
            "off-startup action. Output is sanitized and never includes local "
            "paths, object URIs, signed URLs, or secrets."
        )
    )
    parser.add_argument("--source-artifact-path", type=Path)
    parser.add_argument("--source-object-uri")
    parser.add_argument("--compact-index-path", type=Path)
    parser.add_argument("--expected-size-bytes", type=int)
    parser.add_argument("--expected-md5")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--force", action="store_true", help="replace an existing artifact")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    args = parser.parse_args(argv)

    settings_kwargs: dict[str, Any] = {"jwt_secret": "compact-index-materialize-local"}
    if args.compact_index_path is not None:
        settings_kwargs["coordinate_resolver_compact_index_path"] = args.compact_index_path
    if args.source_object_uri is not None:
        settings_kwargs["coordinate_resolver_compact_index_object_uri"] = args.source_object_uri
    settings = Settings(**settings_kwargs)

    materialized = materialize_compact_coordinate_index(
        settings,
        source_artifact_path=args.source_artifact_path,
        source_object_uri=args.source_object_uri,
        force=args.force,
        expected_size_bytes=args.expected_size_bytes,
        expected_md5=args.expected_md5,
        expected_sha256=args.expected_sha256,
    )

    report = {
        "mode": "eamos_compact_index_materialize",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "guardrails": {
            "startup_downloads": "not_used",
            "raw_gff_runtime_scan": "not_used",
            "network": "supabase_private_storage_only_when_source_object_uri_used",
            "public_bucket": "blocked",
            "signed_frontend_url": "not_created",
            "frontend_direct_access": "blocked",
            "secrets_in_output": "blocked",
            "local_paths_in_output": "blocked",
            "object_uri_values_in_output": "blocked",
            "restricted_predictor_unlocks": "not_used",
        },
        "materialization": asdict(materialized),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))

    return 0 if materialized.ready or not args.require_ready else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
