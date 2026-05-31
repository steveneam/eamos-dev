from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.data_sources.source_manifest import POST_REFERENCE_DAY1_SOURCE_IDS
from app.services.source_downloads import (
    DEFAULT_LARGE_STAGING_ROOT,
    DEFAULT_SMALL_STAGING_ROOT,
    build_source_download_items,
    execute_source_downloads,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Guarded Eamos source download/staging CLI for reviewed source assets."
    )
    parser.add_argument(
        "--source",
        action="append",
        choices=POST_REFERENCE_DAY1_SOURCE_IDS,
        help="source id to stage; may be repeated. Defaults to all post-reference sources.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="perform downloads. Without this flag the command only prints the plan.",
    )
    parser.add_argument(
        "--include-large",
        action="store_true",
        help="include large C-drive staged assets such as dbSNP and phyloP.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-download even when the destination file is already present.",
    )
    parser.add_argument(
        "--small-staging-root",
        type=Path,
        default=DEFAULT_SMALL_STAGING_ROOT,
        help="staging root for non-large assets.",
    )
    parser.add_argument(
        "--large-staging-root",
        type=Path,
        default=DEFAULT_LARGE_STAGING_ROOT,
        help="staging root for large assets.",
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    args = parser.parse_args(argv)

    source_ids = tuple(args.source) if args.source else POST_REFERENCE_DAY1_SOURCE_IDS
    items = build_source_download_items(
        source_ids=source_ids,
        small_staging_root=args.small_staging_root,
        large_staging_root=args.large_staging_root,
        include_large=args.include_large,
    )
    result = execute_source_downloads(items, download=args.download, force=args.force)
    report = {
        "mode": "eamos_source_download",
        "status": "downloaded" if args.download else "planned",
        "download_performed": bool(args.download),
        "include_large": bool(args.include_large),
        "small_staging_root": str(args.small_staging_root),
        "large_staging_root": str(args.large_staging_root),
        "guardrails": {
            "supabase_mutation": "not_used",
            "storage_uploads": "not_used",
            "public_bucket": "blocked",
            "render_env_or_deploy_mutation": "not_used",
            "restricted_predictor_unlocks": "not_used",
            "secrets_in_output": "blocked",
        },
        "result": result.to_dict(),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
