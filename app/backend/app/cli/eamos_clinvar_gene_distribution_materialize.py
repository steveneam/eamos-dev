from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.clinvar_local import materialize_clinvar_gene_distribution_index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize the bounded ClinVar gene-distribution SQLite index from "
            "an already-present local ClinVar VCF. This command performs no "
            "downloads and emits sanitized readiness only."
        )
    )
    parser.add_argument("--from-vcf", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    args = parser.parse_args(argv)

    settings_kwargs: dict[str, Any] = {"jwt_secret": "clinvar-gene-distribution-local"}
    if args.from_vcf is not None:
        settings_kwargs["clinvar_runtime_vcf_path"] = args.from_vcf
    if args.output is not None:
        settings_kwargs["clinvar_gene_distribution_index_path"] = args.output
    if args.manifest is not None:
        settings_kwargs["clinvar_gene_distribution_manifest_path"] = args.manifest
    settings = Settings(**settings_kwargs)

    vcf_path = args.from_vcf or settings.clinvar_runtime_vcf_path
    output_path = args.output or settings.clinvar_gene_distribution_index_path
    manifest_path = args.manifest or settings.clinvar_gene_distribution_manifest_path
    result = materialize_clinvar_gene_distribution_index(
        vcf_path=vcf_path,
        index_path=output_path,
        manifest_path=manifest_path,
        force=args.force,
    )
    report = {
        "mode": "clinvar_gene_distribution_materialize",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "guardrails": {
            "startup_download": "not_used",
            "request_time_materialization": "not_used",
            "patient_data": "not_used",
            "network": {"used": False, "provider": None},
            "secrets_in_output": "blocked",
            "local_paths_in_output": "blocked",
            "object_uris_in_output": "blocked",
            "raw_source_rows_in_output": "blocked",
        },
        "materialization": result.to_sanitized_dict(),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0 if result.ready or not args.require_ready else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
