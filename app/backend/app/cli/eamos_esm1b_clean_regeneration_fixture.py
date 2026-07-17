from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.esm1b_clean_regeneration import (
    ESM1B_CLEAN_SOURCE_ROUTE,
    build_clean_esm1b_regeneration_fixture,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build deterministic, raw ESM-1b genomic shards from small synthetic "
            "fixtures. This command does not run ESM-1b, download source artifacts, "
            "create bgzip/Tabix runtime assets, upload data, or change providers."
        )
    )
    parser.add_argument("--fixture-only", action="store_true", required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--score-csv", type=Path, required=True)
    parser.add_argument("--context-jsonl", type=Path, required=True)
    parser.add_argument("--context-manifest", type=Path, required=True)
    parser.add_argument("--scorer-proof", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--max-score-rows", type=int, default=100_000)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)

    result = build_clean_esm1b_regeneration_fixture(
        input_root=args.input_root,
        score_csv_path=args.score_csv,
        context_jsonl_path=args.context_jsonl,
        context_manifest_path=args.context_manifest,
        scorer_proof_path=args.scorer_proof,
        output_root=args.output_root,
        max_score_rows=args.max_score_rows,
    )
    report = {
        "mode": "eamos_esm1b_clean_regeneration_fixture",
        "status": "fixture_ready",
        "source_route": {
            "route_id": ESM1B_CLEAN_SOURCE_ROUTE.route_id,
            "sha256": ESM1B_CLEAN_SOURCE_ROUTE.checksum(),
            "release_gates": list(ESM1B_CLEAN_SOURCE_ROUTE.release_gates),
        },
        "artifacts": result.to_sanitized_dict(),
        "guardrails": {
            "model_execution": "not_run",
            "precomputed_score_archive": "not_used",
            "bgzip_tabix_materialization": "not_used",
            "storage_upload": "not_used",
            "supabase_metadata_mutation": "not_used",
            "provider_flip": "not_used",
            "local_paths_in_output": "blocked",
            "secrets_in_output": "blocked",
        },
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
