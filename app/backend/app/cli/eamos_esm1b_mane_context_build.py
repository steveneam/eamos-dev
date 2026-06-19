from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import Settings
from app.services.esm1b_mane_contexts import write_esm1b_mane_context_artifacts
from app.services.reference_genome import TwoBitReferenceGenomeStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build MANE codon contexts and matching protein FASTA for the "
            "commercial-safe MIT ESM1b scoring path. This command does not run "
            "ESM1b scoring, download the Hugging Face score zip, upload to "
            "Storage, mutate Supabase metadata, seed Render disk, or flip providers."
        )
    )
    parser.add_argument("--mane-gff", type=Path)
    parser.add_argument("--hg38-2bit", type=Path)
    parser.add_argument("--context-jsonl", type=Path, required=True)
    parser.add_argument("--protein-fasta", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mane-version", required=True)
    parser.add_argument(
        "--sequence-id-field",
        choices=("protein_id", "ensembl_protein_id", "mane_tx"),
        default="protein_id",
        help=(
            "Identifier written as FASTA seq_id and context uniprot_isoform. "
            "The regenerated score CSV must use the same seq_id values."
        ),
    )
    parser.add_argument(
        "--gene",
        action="append",
        default=None,
        help="Optional gene symbol filter; repeat for multiple genes.",
    )
    parser.add_argument(
        "--nonstandard-codon-policy",
        choices=("fail", "skip"),
        default="fail",
        help=(
            "Use skip only for operator-reviewed nonstandard CDS codons; skipped "
            "positions are written as X in FASTA and omitted from codon contexts."
        ),
    )
    parser.add_argument(
        "--invalid-cds-policy",
        choices=("fail", "skip"),
        default="fail",
        help=(
            "Use skip for reviewed MANE CDS exceptions that cannot produce a "
            "normal genome-derived triplet context."
        ),
    )
    parser.add_argument(
        "--primary-chromosomes-only",
        action="store_true",
        help=(
            "Skip MANE records on alternate/fix/unplaced contigs that are not "
            "available in the local UCSC hg38.2bit primary-chromosome asset."
        ),
    )
    parser.add_argument(
        "--reference-sha256",
        help="Precomputed hg38.2bit SHA256 to record instead of hashing the reference file.",
    )
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)

    settings = Settings(jwt_secret="esm1b-mane-context-build-local")
    mane_gff = _resolve_backend_path(
        settings,
        args.mane_gff or settings.coordinate_resolver_mane_gff_path,
    )
    hg38_2bit = _resolve_backend_path(
        settings,
        args.hg38_2bit
        or settings.coordinate_resolver_hg38_2bit_path
        or settings.hg38_2bit_runtime_asset_path,
    )
    context_path = args.context_jsonl.resolve()
    protein_fasta_path = args.protein_fasta.resolve()
    manifest_path = args.manifest.resolve()

    reference_store = TwoBitReferenceGenomeStore(
        hg38_2bit,
        source_version="UCSC hg38.2bit",
    )
    try:
        result = write_esm1b_mane_context_artifacts(
            mane_gff_path=mane_gff,
            reference_path=hg38_2bit,
            reference_store=reference_store,
            context_path=context_path,
            protein_fasta_path=protein_fasta_path,
            manifest_path=manifest_path,
            sequence_id_field=args.sequence_id_field,
            mane_version=args.mane_version,
            genes=args.gene,
            nonstandard_codon_policy=args.nonstandard_codon_policy,
            invalid_cds_policy=args.invalid_cds_policy,
            primary_chromosomes_only=args.primary_chromosomes_only,
            reference_sha256=args.reference_sha256,
        )
    finally:
        reference_store.close()

    report = {
        "mode": "eamos_esm1b_mane_context_build",
        "status": "ready",
        "guardrails": {
            "precomputed_huggingface_score_zip": "not_used",
            "esm1b_scoring": "not_run",
            "supabase_metadata_mutation": "not_used",
            "storage_upload": "not_used",
            "render_env_or_deploy_mutation": "not_used",
            "render_disk_seeding": "not_used",
            "provider_flip": "not_used",
            "startup_download": "not_used",
            "secrets_in_output": "blocked",
            "local_paths_in_output": "blocked",
        },
        "artifacts": result.to_sanitized_dict(),
        "next_step": (
            "Run the MIT ESM1b scoring pipeline against the emitted FASTA, with "
            "CSV seq_id values matching sequence_id_field, then run "
            "eamos_esm1b_regenerated_scores_materialize with this JSONL."
        ),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0


def _resolve_backend_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
