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

TRANSCRIPT_MODELS_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "workbench"
    / "gene_viewer_transcript_models.json"
)

SMOKE_CONTROLS = {
    "PCARE": {
        "sequence": "M" + "P" * 719,
        "input_type": "protein",
        "label": "PCARE NM_001029883 reference smoke",
        "gene_symbol": "PCARE",
        "transcript": "NM_001029883",
        "protein_accession": None,
        "sequence_source": "runtime_length_control",
        "interpretation": "runtime_control_not_domain_truth",
    },
    "ABCA4": {
        "fixture_gene": "ABCA4",
        "expected_cds_length": 6822,
        "expected_protein_length": 2273,
        "input_type": "coding_dna",
        "label": "ABCA4 NM_000350.3 fixture CDS smoke",
        "gene_symbol": "ABCA4",
        "transcript": "NM_000350.3",
        "protein_accession": "ENSP00000359245",
        "sequence_source": "workbench_gene_viewer_transcript_model_cds",
        "interpretation": "real_fixture_coding_dna_not_domain_truth",
    },
}


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
    parser.add_argument(
        "--smoke-control",
        action="append",
        choices=tuple(SMOKE_CONTROLS),
        help="run a named bounded HMMER runtime smoke control",
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
    smoke_controls = list(args.smoke_control or [])
    if args.smoke_pcare and "PCARE" not in smoke_controls:
        smoke_controls.append("PCARE")
    smokes = []
    for control in smoke_controls:
        smokes.append(
            _protein_smoke(
                settings, control=control, prepared_ready=bool(prepared and prepared.ready)
            )
        )

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
        "protein_smokes": smokes,
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))

    ready = materialized.ready and (prepared is None or prepared.ready)
    if smoke_controls:
        ready = ready and all(smoke.get("status") in {"available", "cache_hit"} for smoke in smokes)
    return 0 if ready or not args.require_ready else 2


def _protein_smoke(settings: Settings, *, control: str, prepared_ready: bool) -> dict[str, object]:
    smoke_config = SMOKE_CONTROLS[control]
    if not prepared_ready:
        return {"control": control, "status": "skipped", "reason": "runtime_prepare_not_ready"}

    try:
        sequence = _resolve_smoke_sequence(smoke_config)
    except ValueError as exc:
        return {"control": control, "status": "failed", "reason": str(exc)}

    smoke_settings = settings.model_copy(update={"protein_annotation_enabled": True})
    service = ProteinAnnotationService(settings=smoke_settings, cache_repo=None)
    track = service.annotate(
        ProteinAnnotationRequest(
            sequence=sequence,
            input_type=smoke_config["input_type"],
            sequence_label=smoke_config["label"],
            gene_symbol=smoke_config["gene_symbol"],
            transcript=smoke_config["transcript"],
            protein_accession=smoke_config["protein_accession"],
            use_cache=False,
            allow_run=True,
        )
    )
    return {
        "control": control,
        "status": track.status,
        "gene_symbol": track.gene_symbol,
        "transcript": track.transcript,
        "protein_accession": track.protein_accession,
        "input_type": smoke_config["input_type"],
        "translated_from": track.translated_from,
        "sequence_source": smoke_config["sequence_source"],
        "interpretation": smoke_config["interpretation"],
        "feature_count": len(track.features),
        "warning_count": len(track.warnings),
        "fail_closed_reason": track.fail_closed_reason,
    }


def _resolve_smoke_sequence(smoke_config: dict[str, object]) -> str:
    sequence = smoke_config.get("sequence")
    if isinstance(sequence, str) and sequence:
        return sequence
    fixture_gene = smoke_config.get("fixture_gene")
    if isinstance(fixture_gene, str) and fixture_gene:
        return _load_fixture_coding_dna(
            gene=fixture_gene,
            transcript=_required_str(smoke_config.get("transcript")),
            expected_cds_length=_required_int(smoke_config.get("expected_cds_length")),
            expected_protein_length=_required_int(smoke_config.get("expected_protein_length")),
        )
    raise ValueError("smoke_sequence_unconfigured")


def _load_fixture_coding_dna(
    *,
    gene: str,
    transcript: str,
    expected_cds_length: int,
    expected_protein_length: int,
    fixture_path: Path = TRANSCRIPT_MODELS_FIXTURE,
) -> str:
    try:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("smoke_fixture_unavailable") from exc

    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("smoke_fixture_records_missing")

    record = next(
        (
            item
            for item in records
            if isinstance(item, dict)
            and str(item.get("gene") or "").upper() == gene.upper()
            and item.get("transcript") == transcript
        ),
        None,
    )
    if record is None:
        raise ValueError("smoke_fixture_record_missing")

    if _required_int(record.get("cds_length")) != expected_cds_length:
        raise ValueError("smoke_fixture_record_cds_length_mismatch")
    if _required_int(record.get("protein_length")) != expected_protein_length:
        raise ValueError("smoke_fixture_record_protein_length_mismatch")

    exons = record.get("exons")
    if not isinstance(exons, list) or not exons:
        raise ValueError("smoke_fixture_exons_missing")

    next_cds_start = 1
    sequence_parts: list[str] = []
    try:
        sorted_exons = sorted(exons, key=_fixture_cds_start_for_sort)
    except (AttributeError, ValueError) as exc:
        raise ValueError("smoke_fixture_exon_invalid") from exc
    for exon in sorted_exons:
        if not isinstance(exon, dict):
            raise ValueError("smoke_fixture_exon_invalid")
        cds_start = _required_int(exon.get("cds_start"))
        cds_end = _required_int(exon.get("cds_end"))
        sequence = _required_str(exon.get("sequence")).upper()
        if cds_start != next_cds_start:
            raise ValueError("smoke_fixture_cds_gap")
        if cds_end < cds_start:
            raise ValueError("smoke_fixture_cds_interval_invalid")
        if cds_end - cds_start + 1 != len(sequence):
            raise ValueError("smoke_fixture_exon_length_mismatch")
        if set(sequence) - {"A", "C", "G", "T", "N"}:
            raise ValueError("smoke_fixture_invalid_coding_dna")
        sequence_parts.append(sequence)
        next_cds_start = cds_end + 1

    coding_dna = "".join(sequence_parts)
    if len(coding_dna) != expected_cds_length:
        raise ValueError("smoke_fixture_cds_length_mismatch")
    if len(coding_dna) % 3 != 0:
        raise ValueError("smoke_fixture_cds_not_codon_aligned")
    if not coding_dna.startswith("ATG"):
        raise ValueError("smoke_fixture_missing_start_codon")
    if coding_dna[-3:] not in {"TAA", "TAG", "TGA"}:
        raise ValueError("smoke_fixture_missing_terminal_stop")
    if (len(coding_dna) // 3) - 1 != expected_protein_length:
        raise ValueError("smoke_fixture_translation_length_mismatch")
    return coding_dna


def _required_str(value: object) -> str:
    if isinstance(value, str) and value:
        return value
    raise ValueError("smoke_fixture_value_missing")


def _fixture_cds_start_for_sort(value: object) -> int:
    if not isinstance(value, dict):
        raise ValueError("smoke_fixture_exon_invalid")
    return _required_int(value.get("cds_start"))


def _required_int(value: object) -> int:
    if isinstance(value, int) and value > 0:
        return value
    raise ValueError("smoke_fixture_value_missing")


if __name__ == "__main__":
    raise SystemExit(main())
