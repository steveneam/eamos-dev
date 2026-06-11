from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.clingen_source_fetch import (
    DEFAULT_CSPEC_DETAIL,
    DEFAULT_CSPEC_PAGE_SIZE,
    DEFAULT_EREPO_PAGE_SIZE,
    fetch_clingen_source_snapshots,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Operator-initiated ClinGen eRepo/CSpec source snapshot fetch. "
            "This is not used by app startup or lookup requests. Output is "
            "sanitized and never includes source rows, local paths, object URIs, "
            "signed URLs, API keys, or secrets."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./data/bio_assets/clingen/source"),
    )
    parser.add_argument("--skip-erepo", action="store_true")
    parser.add_argument("--skip-cspec", action="store_true")
    parser.add_argument("--erepo-base-url")
    parser.add_argument("--cspec-base-url")
    parser.add_argument("--erepo-page-size", type=int, default=DEFAULT_EREPO_PAGE_SIZE)
    parser.add_argument("--cspec-page-size", type=int, default=DEFAULT_CSPEC_PAGE_SIZE)
    parser.add_argument(
        "--cspec-detail",
        choices=("low", "med", "high"),
        default=DEFAULT_CSPEC_DETAIL,
    )
    parser.add_argument(
        "--cspec-entity-type",
        action="append",
        default=None,
        help="Fetch only this CSpec entity type; repeat for multiple types.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Limit pages per eRepo/CSpec entity type, primarily for smoke tests.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=0.5)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    args = parser.parse_args(argv)

    settings_kwargs: dict[str, Any] = {"jwt_secret": "clingen-local-fetch-local"}
    if args.erepo_base_url:
        settings_kwargs["clingen_erepo_base_url"] = args.erepo_base_url
    if args.cspec_base_url:
        settings_kwargs["clingen_cspec_base_url"] = args.cspec_base_url
    settings = Settings(**settings_kwargs)

    result = fetch_clingen_source_snapshots(
        settings,
        output_dir=args.output_dir,
        include_erepo=not args.skip_erepo,
        include_cspec=not args.skip_cspec,
        erepo_page_size=args.erepo_page_size,
        cspec_page_size=args.cspec_page_size,
        cspec_detail=args.cspec_detail,
        cspec_entity_types=args.cspec_entity_type,
        max_pages=args.max_pages,
        force=args.force,
        timeout_seconds=args.timeout_seconds,
        retries=args.retries,
        backoff_seconds=args.backoff_seconds,
    )
    report = {
        "mode": "clingen_local_fetch",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "guardrails": {
            "startup_download": "not_used",
            "request_time_materialization": "not_used",
            "operator_initiated_download": True,
            "patient_data": "not_used",
            "secrets_in_output": "blocked",
            "local_paths_in_output": "blocked",
            "raw_source_rows_in_output": "blocked",
        },
        "snapshot": result.to_sanitized_dict(),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0 if result.ready or not args.require_ready else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
