from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.schemas.protein_annotation import ProteinAnnotationRequest
from app.services.pfam_materialization import materialize_pfam_hmm_gz_from_private_storage
from app.services.protein_annotation import ProteinAnnotationService
from app.services.protein_runtime import prepare_protein_annotation_runtime

PCARE_SMOKE_SEQUENCE = "M" + "P" * 719


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize Pfam-A.hmm.gz from private Supabase Storage and, "
            "optionally, prepare/smoke the local HMMER runtime. No public bucket "
            "or signed frontend URL is created."
        )
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument(
        "--source-object-uri", help="supabase://bucket/object-path for Pfam-A.hmm.gz"
    )
    parser.add_argument(
        "--force-download", action="store_true", help="replace an existing staged gz"
    )
    parser.add_argument(
        "--prepare", action="store_true", help="extract Pfam-A.hmm and run hmmpress"
    )
    parser.add_argument("--force-hmmpress", action="store_true", help="rerun hmmpress indexes")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    parser.add_argument(
        "--smoke-pcare", action="store_true", help="run a bounded PCARE HMMER smoke"
    )
    parser.add_argument("--hmmscan-timeout-seconds", type=float)
    parser.add_argument("--hmmpress-timeout-seconds", type=float)
    parser.add_argument("--pfam-hmm-path", type=Path)
    parser.add_argument("--pfam-hmm-gz-path", type=Path)
    args = parser.parse_args(argv)

    settings_kwargs: dict[str, Any] = {"jwt_secret": "pfam-runtime-materialize-local"}
    if args.hmmscan_timeout_seconds is not None:
        settings_kwargs["protein_annotation_hmmscan_timeout_seconds"] = args.hmmscan_timeout_seconds
    if args.hmmpress_timeout_seconds is not None:
        settings_kwargs["protein_annotation_hmmpress_timeout_seconds"] = (
            args.hmmpress_timeout_seconds
        )
    if args.pfam_hmm_path is not None:
        settings_kwargs["protein_annotation_pfam_hmm_path"] = args.pfam_hmm_path
    if args.pfam_hmm_gz_path is not None:
        settings_kwargs["protein_annotation_pfam_hmm_gz_path"] = args.pfam_hmm_gz_path
    if args.source_object_uri is not None:
        settings_kwargs["protein_annotation_pfam_hmm_gz_object_uri"] = args.source_object_uri
    settings = Settings(**settings_kwargs)

    materialized = materialize_pfam_hmm_gz_from_private_storage(
        settings,
        source_object_uri=args.source_object_uri,
        force=args.force_download,
    )
    prepared = None
    if args.prepare and materialized.ready:
        prepared = prepare_protein_annotation_runtime(settings, force_hmmpress=args.force_hmmpress)
    smoke = None
    if args.smoke_pcare:
        smoke = _pcare_smoke(settings, prepared_ready=bool(prepared and prepared.ready))

    report = {
        "mode": "pfam_runtime_materialize",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "guardrails": {
            "network": "supabase_private_storage_only",
            "public_bucket": "not_used",
            "signed_frontend_url": "not_used",
            "frontend_direct_access": "not_used",
            "secrets_in_output": "blocked",
            "restricted_predictor_unlocks": "not_used",
            "alphamissense": "not_used",
        },
        "materialization": asdict(materialized),
        "runtime_prepare": asdict(prepared) if prepared is not None else None,
        "pcare_smoke": smoke,
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))

    ready = materialized.ready and (prepared is None or prepared.ready)
    if args.smoke_pcare:
        ready = ready and bool(smoke and smoke.get("status") in {"available", "cache_hit"})
    return 0 if ready or not args.require_ready else 2


def _pcare_smoke(settings: Settings, *, prepared_ready: bool) -> dict[str, object]:
    if not prepared_ready:
        return {"status": "skipped", "reason": "runtime_prepare_not_ready"}

    smoke_settings = settings.model_copy(update={"protein_annotation_enabled": True})
    service = ProteinAnnotationService(settings=smoke_settings, cache_repo=None)
    track = service.annotate(
        ProteinAnnotationRequest(
            sequence=PCARE_SMOKE_SEQUENCE,
            input_type="protein",
            sequence_label="PCARE NM_001029883 reference smoke",
            gene_symbol="PCARE",
            transcript="NM_001029883",
            use_cache=False,
            allow_run=True,
        )
    )
    return {
        "status": track.status,
        "gene_symbol": track.gene_symbol,
        "transcript": track.transcript,
        "feature_count": len(track.features),
        "warning_count": len(track.warnings),
        "fail_closed_reason": track.fail_closed_reason,
    }


if __name__ == "__main__":
    raise SystemExit(main())
