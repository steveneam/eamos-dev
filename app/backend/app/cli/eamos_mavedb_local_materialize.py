from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import Settings
from app.services.mavedb_local import materialize_mavedb_local_store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a local MaveDB CC0 SQLite source asset from operator-supplied "
            "JSONL rows. This performs no network, Supabase, Render, or provider mutation."
        )
    )
    parser.add_argument(
        "--input-jsonl",
        action="append",
        type=Path,
        required=True,
        help="MaveDB JSONL file; may be repeated",
    )
    parser.add_argument("--output", type=Path, help="destination SQLite path")
    parser.add_argument("--manifest-path", type=Path, help="destination manifest sidecar path")
    parser.add_argument("--source-version", help="source version label for the manifest")
    parser.add_argument("--force", action="store_true", help="replace an existing destination")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero if not ready")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    args = parser.parse_args(argv)

    settings = Settings(jwt_secret="mavedb-local-materialize")
    result = materialize_mavedb_local_store(
        settings,
        jsonl_files=args.input_jsonl,
        output_path=args.output,
        manifest_path=args.manifest_path,
        source_version=args.source_version,
        force=args.force,
    )
    payload = {
        "mode": "eamos_mavedb_local_materialize",
        "guardrails": {
            "network": "not_used",
            "supabase": "not_used",
            "render": "not_used",
            "provider_flips": "not_used",
            "startup_downloads": "not_used",
        },
        "materialization": result.to_sanitized_dict(),
    }
    print(json.dumps(payload, indent=None if args.compact else 2, sort_keys=True))
    return 1 if args.require_ready and not result.ready else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
