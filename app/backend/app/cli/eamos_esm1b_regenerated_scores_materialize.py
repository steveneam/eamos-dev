from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from app.core.config import Settings
from app.services.esm1b_assembly import (
    ESM1B_ASSEMBLY_CODE_VERSION,
    ESM1B_MODEL_NAME,
    ESM1B_MODEL_SOURCE_URL,
    ESM1B_SCORING_CODE_SOURCE_URL,
    load_esm1b_codon_contexts_from_jsonl,
    load_esm1b_score_rows_from_csv,
    materialize_regenerated_esm1b_runtime_asset,
)
from app.services.predictor_runtime import inspect_esm1b_runtime_asset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a commercial-safe ESM1b hg38 bgzip/tabix runtime asset "
            "from MIT-regenerated score rows. This command does not download the "
            "Hugging Face precomputed score zip, upload to Storage, mutate "
            "Supabase metadata, seed Render disk, or flip providers."
        )
    )
    parser.add_argument("--score-csv", type=Path, required=True)
    parser.add_argument("--codon-context-jsonl", type=Path, required=True)
    parser.add_argument("--target-path", type=Path)
    parser.add_argument("--score-source-sha256")
    parser.add_argument("--mane-version", required=True)
    parser.add_argument("--grch38-reference-sha256", required=True)
    parser.add_argument("--code-version", default=ESM1B_ASSEMBLY_CODE_VERSION)
    parser.add_argument("--model-name", default=ESM1B_MODEL_NAME)
    parser.add_argument("--model-source-url", default=ESM1B_MODEL_SOURCE_URL)
    parser.add_argument("--model-source-license", default="MIT")
    parser.add_argument("--scoring-code-source-url", default=ESM1B_SCORING_CODE_SOURCE_URL)
    parser.add_argument("--scoring-code-license", default="MIT")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)

    settings = Settings(jwt_secret="esm1b-regenerated-materialize-local")
    target_path = (
        args.target_path.resolve()
        if args.target_path is not None
        else settings.backend_root / settings.esm1b_hg38_runtime_asset_path
    )
    score_checksum = args.score_source_sha256 or _sha256_file(args.score_csv)
    result = materialize_regenerated_esm1b_runtime_asset(
        score_rows=load_esm1b_score_rows_from_csv(args.score_csv),
        codon_contexts=load_esm1b_codon_contexts_from_jsonl(args.codon_context_jsonl),
        target_path=target_path,
        score_source_checksum=score_checksum,
        mane_version=args.mane_version,
        grch38_reference_checksum=args.grch38_reference_sha256,
        code_version=args.code_version,
        model_name=args.model_name,
        model_source_url=args.model_source_url,
        model_source_license=args.model_source_license,
        scoring_code_source_url=args.scoring_code_source_url,
        scoring_code_license=args.scoring_code_license,
    )
    preflight = inspect_esm1b_runtime_asset(
        Settings(
            jwt_secret="esm1b-regenerated-materialize-preflight",
            esm1b_hg38_runtime_asset_path=target_path,
        ),
        verify_checksum=False,
        require_manifest=True,
    )
    ready = preflight.ready and preflight.launch_gate is None
    report = {
        "mode": "eamos_esm1b_regenerated_scores_materialize",
        "status": "ready" if ready else "failed",
        "guardrails": {
            "precomputed_huggingface_score_zip": "not_used",
            "score_generation_method": "mit_model_regeneration",
            "supabase_metadata_mutation": "not_used",
            "storage_upload": "not_used",
            "render_env_or_deploy_mutation": "not_used",
            "render_disk_seeding": "not_used",
            "provider_flip": "not_used",
            "startup_download": "not_used",
            "secrets_in_output": "blocked",
            "local_paths_in_output": "blocked",
        },
        "artifact": result.to_sanitized_dict(),
        "preflight": {
            "source_id": preflight.source_id,
            "asset_role": preflight.asset_role,
            "status": preflight.status.value,
            "ready": preflight.ready,
            "actual_size_bytes": preflight.actual_size_bytes,
            "launch_gate": preflight.launch_gate,
            "reader_requires_local_path": preflight.reader_requires_local_path,
        },
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0 if ready or not args.require_ready else 2


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
