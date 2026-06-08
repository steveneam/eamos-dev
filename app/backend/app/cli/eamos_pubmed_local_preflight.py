from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.pubmed_local import inspect_pubmed_local_store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only PubMed local source-asset preflight. Output is sanitized "
            "and never includes local paths, API keys, seed rows, or raw abstracts."
        )
    )
    parser.add_argument("--db-path", type=Path)
    parser.add_argument("--manifest-path", type=Path)
    parser.add_argument("--enabled", action="store_true")
    parser.add_argument("--skip-checksum", action="store_true")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    args = parser.parse_args(argv)

    settings_kwargs: dict[str, Any] = {"jwt_secret": "pubmed-local-preflight-local"}
    if args.db_path is not None:
        settings_kwargs["pubmed_local_sqlite_path"] = args.db_path
    if args.manifest_path is not None:
        settings_kwargs["pubmed_local_manifest_path"] = args.manifest_path
    if args.enabled:
        settings_kwargs["pubmed_local_enabled"] = True
    settings = Settings(**settings_kwargs)

    inspection = inspect_pubmed_local_store(settings, verify_checksum=not args.skip_checksum)
    report = {
        "mode": "pubmed_local_preflight",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ready": inspection.ready,
        "status": inspection.status,
        "enabled": inspection.enabled,
        "startup_download_allowed": False,
        "network_used": False,
        "schema_version": inspection.schema_version,
        "article_count": inspection.article_count,
        "licensed_abstract_count": inspection.licensed_abstract_count,
        "metadata_only_count": inspection.metadata_only_count,
        "deleted_count": inspection.deleted_count,
        "domain_filtered_count": inspection.domain_filtered_count,
        "pmc_license_overlay_count": inspection.pmc_license_overlay_count,
        "literature_edge_count": inspection.literature_edge_count,
        "source_file_count": inspection.source_file_count,
        "source_kind_counts": inspection.source_kind_counts,
        "import_stats_by_source": inspection.import_stats_by_source,
        "coverage": {
            "queries": inspection.coverage_count,
        },
        "fts_status": inspection.fts_status,
        "source_version": inspection.source_version,
        "checksum_verified": inspection.checksum_verified,
        "input_checksum_status": inspection.input_checksum_status,
        "input_checksum_verified_count": inspection.input_checksum_verified_count,
        "input_checksum_missing_count": inspection.input_checksum_missing_count,
        "secret_values_emitted": False,
        "local_path_values_emitted": False,
        "abstract_values_emitted": False,
        "warnings": list(inspection.warnings),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0 if inspection.ready or not args.require_ready else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
