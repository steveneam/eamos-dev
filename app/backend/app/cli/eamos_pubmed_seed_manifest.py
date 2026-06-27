from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from app.services.pubmed_seed_manifest import PubMedSeedManifestError, load_seed_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate an Eamos PubMed/LitVar/PubTator/ClinicalTrials seed manifest "
            "and optionally write the TSV query file consumed by PubMed-local tooling. "
            "This command performs no network, source download, materialization, "
            "storage upload, runtime seeding, or flag change."
        )
    )
    parser.add_argument("--manifest-path", type=Path, required=True)
    parser.add_argument("--write-query-file", type=Path)
    parser.add_argument("--force", action="store_true", help="replace an existing query file")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless valid")
    args = parser.parse_args(argv)

    try:
        manifest = load_seed_manifest(args.manifest_path)
        output_file_name = None
        if args.write_query_file is not None:
            manifest.write_pubmed_query_tsv(args.write_query_file, force=args.force)
            output_file_name = args.write_query_file.name
        report = {
            "mode": "pubmed_seed_manifest_validate",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "ready",
            "manifest_file_name": args.manifest_path.name,
            "pubmed_query_file_name": output_file_name,
            "validation": manifest.to_sanitized_dict(),
        }
        _print_report(report, compact=args.compact)
        return 0
    except PubMedSeedManifestError as exc:
        report = {
            "mode": "pubmed_seed_manifest_validate",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "ready": False,
            "manifest_file_name": args.manifest_path.name,
            "errors": list(exc.errors),
            "guardrails": {
                "network": {"used": False, "provider": None},
                "source_download": "not_used",
                "materialization": "not_used",
                "storage_upload": "not_used",
                "runtime_flag_change": "not_used",
            },
        }
        _print_report(report, compact=args.compact)
        return 2 if args.require_ready else 0


def _print_report(report: dict, *, compact: bool) -> None:
    print(json.dumps(report, indent=None if compact else 2, sort_keys=True))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
