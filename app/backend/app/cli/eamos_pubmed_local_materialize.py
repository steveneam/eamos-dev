from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.pubmed_local import materialize_pubmed_local_store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a local PubMed SQLite source asset through an explicit "
            "off-startup action. Output is sanitized and never includes seed rows, "
            "raw abstracts, local paths, API keys, object URIs, signed URLs, or secrets."
        )
    )
    parser.add_argument("--from-xml-file", action="append", type=Path, default=[])
    parser.add_argument("--from-xml-dir", type=Path)
    parser.add_argument("--from-jsonl-file", action="append", type=Path, default=[])
    parser.add_argument(
        "--from-pubtator-edge-jsonl-file",
        action="append",
        type=Path,
        default=[],
        help="operator-supplied PubTator-style entity edge JSONL attached to imported PMIDs",
    )
    parser.add_argument(
        "--from-litvar-edge-jsonl-file",
        action="append",
        type=Path,
        default=[],
        help="operator-supplied LitVar-style variant edge JSONL attached to imported PMIDs",
    )
    parser.add_argument(
        "--pmc-license-file",
        action="append",
        type=Path,
        default=[],
        help="operator-supplied PMC OA license metadata CSV/TSV/JSONL keyed by PMCID",
    )
    parser.add_argument("--query-file", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--source-version")
    parser.add_argument(
        "--domain-filter",
        choices=("none", "biomedical"),
        default="none",
        help="optional pre-packaging domain filter; default keeps all seed-matched rows",
    )
    parser.add_argument(
        "--allowed-domain",
        action="append",
        default=[],
        help="allowed biomedical domain bucket when --domain-filter=biomedical "
        "(repeatable: gene, biology, biochemistry, chemistry)",
    )
    parser.add_argument(
        "--verify-md5-sidecars",
        action="store_true",
        help="verify operator-staged PubMed XML .md5 sidecars before importing",
    )
    parser.add_argument(
        "--xml-source-kind",
        choices=("auto", "baseline", "update", "pubmed_xml"),
        default="auto",
        help=(
            "label PubMed XML shards for the source-file manifest; auto infers "
            "baseline/update from file or directory names"
        ),
    )
    parser.add_argument(
        "--coverage-completeness",
        choices=("partial", "complete"),
        default="partial",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    args = parser.parse_args(argv)

    xml_files = list(args.from_xml_file)
    if args.from_xml_dir is not None:
        xml_files.extend(
            sorted(
                path
                for path in args.from_xml_dir.iterdir()
                if path.is_file() and (path.suffix == ".xml" or path.name.endswith(".xml.gz"))
            )
        )

    settings_kwargs: dict[str, Any] = {"jwt_secret": "pubmed-local-materialize-local"}
    if args.output is not None:
        settings_kwargs["pubmed_local_sqlite_path"] = args.output
    if args.manifest is not None:
        settings_kwargs["pubmed_local_manifest_path"] = args.manifest
    settings = Settings(**settings_kwargs)

    result = materialize_pubmed_local_store(
        settings,
        xml_files=xml_files,
        jsonl_files=args.from_jsonl_file,
        pmc_license_files=args.pmc_license_file,
        pubtator_edge_files=args.from_pubtator_edge_jsonl_file,
        litvar_edge_files=args.from_litvar_edge_jsonl_file,
        query_file=args.query_file,
        output_path=args.output,
        manifest_path=args.manifest,
        source_version=args.source_version,
        coverage_completeness=args.coverage_completeness,
        domain_filter=args.domain_filter,
        allowed_domains=args.allowed_domain or None,
        verify_md5_sidecars=args.verify_md5_sidecars,
        xml_source_kind=args.xml_source_kind,
        force=args.force,
    )

    report = {
        "mode": "pubmed_local_materialize",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "guardrails": {
            "startup_download": "not_used",
            "request_time_materialization": "not_used",
            "patient_data": "not_used",
            "abstract_license_gate": "enforced",
            "bulk_ftp_download": "not_performed_by_this_cli",
            "network": {"used": False, "provider": None},
            "secrets_in_output": "blocked",
            "local_paths_in_output": "blocked",
            "seed_rows_in_output": "blocked",
            "abstract_text_in_output": "blocked",
        },
        "materialization": result.to_sanitized_dict(),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0 if result.ready or not args.require_ready else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
