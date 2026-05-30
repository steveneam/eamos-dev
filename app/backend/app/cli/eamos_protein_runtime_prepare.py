from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.protein_runtime import prepare_protein_annotation_runtime


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare the local Pfam/HMMER runtime from already-staged private assets. "
            "This command performs no downloads and creates no buckets."
        )
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--force-hmmpress", action="store_true", help="rerun hmmpress indexes")
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="exit non-zero unless hmmscan, Pfam-A.hmm, and hmmpress indexes are ready",
    )
    parser.add_argument("--hmmscan-path", type=Path, help="override hmmscan executable path")
    parser.add_argument("--hmmpress-path", type=Path, help="override hmmpress executable path")
    parser.add_argument("--pfam-hmm-path", type=Path, help="override runtime Pfam-A.hmm path")
    parser.add_argument("--pfam-hmm-gz-path", type=Path, help="override staged Pfam-A.hmm.gz path")
    args = parser.parse_args(argv)

    settings_kwargs: dict[str, Any] = {"jwt_secret": "protein-runtime-prepare-local"}
    if args.hmmscan_path is not None:
        settings_kwargs["protein_annotation_hmmscan_path"] = args.hmmscan_path
    if args.hmmpress_path is not None:
        settings_kwargs["protein_annotation_hmmpress_path"] = args.hmmpress_path
    if args.pfam_hmm_path is not None:
        settings_kwargs["protein_annotation_pfam_hmm_path"] = args.pfam_hmm_path
    if args.pfam_hmm_gz_path is not None:
        settings_kwargs["protein_annotation_pfam_hmm_gz_path"] = args.pfam_hmm_gz_path
    settings = Settings(**settings_kwargs)

    result = prepare_protein_annotation_runtime(settings, force_hmmpress=args.force_hmmpress)
    report = {
        "mode": "protein_annotation_runtime_prepare",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "guardrails": {
            "network": "not_used",
            "downloads": "not_used",
            "storage_buckets": "not_used",
            "secrets": "not_used",
            "restricted_predictor_unlocks": "not_used",
            "alphamissense": "not_used",
        },
        "runtime": asdict(result),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0 if result.ready or not args.require_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
