from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

RENDER_BIO_ASSET_ROOT = "/var/data/eamos/bio_assets"
RENDER_BACKEND_URL = "https://eamos-dev-sg.onrender.com"
VERCEL_APP_URL = "https://eamos-dev.vercel.app"


def build_render_approval_bundle(
    *,
    render_backend_url: str = RENDER_BACKEND_URL,
    vercel_app_url: str = VERCEL_APP_URL,
    asset_root: str = RENDER_BIO_ASSET_ROOT,
    generated_at: str | None = None,
) -> dict[str, object]:
    asset_root = asset_root.rstrip("/")
    render_backend_url = render_backend_url.rstrip("/")
    vercel_app_url = vercel_app_url.rstrip("/")
    paths = _render_paths(asset_root)
    return {
        "mode": "workbench_render_approval_bundle",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "guardrails": {
            "network_used": False,
            "mutations_performed": False,
            "render_env_changed": False,
            "provider_flip_performed": False,
            "startup_downloads_allowed": False,
            "request_time_source_search_allowed": False,
            "generated_assets_committed": False,
            "local_path_values_emitted": False,
            "secret_values_emitted": False,
        },
        "approval_scope": {
            "owner": "Codex",
            "scope": "Workbench CRISPR, primer, alignment, and viewer source-asset readiness",
            "out_of_scope": [
                "AI gateway production enablement",
                "Supabase corpus/vector expansion",
                "startup or request-time genome/protein downloads",
                "committing generated genome, SQLite, VCF, Pfam, or predictor artifacts",
            ],
            "current_required_state": {
                "llm_provider": "mock",
                "crispr_offtarget_provider": "auto",
                "primer_specificity_provider": "template",
            },
        },
        "render_disk_layout": paths,
        "env_changes": _env_changes(paths),
        "crispr_offtarget_full_index_runbook": _crispr_offtarget_full_index_runbook(paths),
        "operator_preflight": _operator_preflight(paths),
        "approval_questions": [
            "Confirm the SG Render service has a persistent disk mounted at /var/data.",
            "Confirm where the full SpCas9 SQLite index will be built and copied from.",
            "Confirm the off-peak maintenance window for any disk attach or env flip.",
            "Confirm UCSC/Kent isPcr licensing comfort before enabling whole-genome primer specificity.",
            "Confirm ClinVar, dbSNP, Pfam/HMMER, and optional AlphaMissense assets are materialized before removing track-level fallback labels.",
        ],
        "post_flip_smoke": _post_flip_smoke(render_backend_url, vercel_app_url),
        "rollback": {
            "crispr_offtarget_provider": "Set CRISPR_OFFTARGET_PROVIDER=auto.",
            "primer_specificity_provider": "Set PRIMER_SPECIFICITY_PROVIDER=template.",
            "protein_annotation": "Set PROTEIN_ANNOTATION_ENABLED=false.",
            "gateway": "Leave LLM_PROVIDER=mock unless Claude's AI security gate has separately passed.",
            "verify": [
                f"curl -fsS {render_backend_url}/healthz",
                f"curl -fsS {render_backend_url}/api/v1/health/provider-cache",
            ],
        },
        "ready_to_flip_when": [
            "CRISPR off-target manifest ready=true and actual_sha256 is recorded.",
            "Provider-cache indexed_sqlite.ready=true on the Render-mounted artifact.",
            "No provider-cache response emits local paths, object URIs, or secrets.",
            "Workbench primer, CRISPR design, off-target, screening-primer, ssODN, align, and TIDE probes pass through SG and Vercel.",
            "Rollback env values are documented before the env change.",
        ],
    }


def _render_paths(asset_root: str) -> dict[str, object]:
    return {
        "mount_root": "/var/data",
        "asset_root": asset_root,
        "required_for_crispr_offtarget_flip": {
            "spcas9_sqlite": f"{asset_root}/crispr/spcas9_offtargets.sqlite",
            "manifest": f"{asset_root}/crispr/spcas9_offtargets.manifest.json",
        },
        "required_for_reference_window_tools": {
            "hg38_2bit": f"{asset_root}/genomes/hg38.2bit",
            "mane_gff": f"{asset_root}/transcripts/MANE.GRCh38.v1.5.refseq_genomic.gff.gz",
            "refseq_gff": (f"{asset_root}/transcripts/GCF_000001405.40_GRCh38.p14_genomic.gff.gz"),
            "coordinate_index": f"{asset_root}/transcripts/eamos-coordinate-index.latest.jsonl.gz",
        },
        "optional_for_primer_specificity": {
            "ucsc_ispcr_binary": f"{asset_root}/bin/isPcr",
            "ucsc_ispcr_hg38": f"{asset_root}/genomes/hg38.2bit",
        },
        "planned_for_primer_snp_masking": {
            "dbsnp_vcf_gz": f"{asset_root}/dbsnp/GCF_000001405.40.gz",
            "dbsnp_vcf_tbi": f"{asset_root}/dbsnp/GCF_000001405.40.gz.tbi",
        },
        "planned_for_gene_viewer_tracks": {
            "clinvar_vcf_gz": f"{asset_root}/clinvar/clinvar.vcf.gz",
            "clinvar_vcf_tbi": f"{asset_root}/clinvar/clinvar.vcf.gz.tbi",
            "pfam_hmm": f"{asset_root}/protein_annotation/Pfam-A.hmm",
            "pfam_hmmpress_indexes": f"{asset_root}/protein_annotation/Pfam-A.hmm.h3*",
            "alphamissense_hg38_tsv_gz": (
                f"{asset_root}/predictors/alphamissense/AlphaMissense_hg38.tsv.gz"
            ),
        },
    }


def _env_changes(paths: dict[str, object]) -> dict[str, object]:
    crispr = paths["required_for_crispr_offtarget_flip"]
    reference = paths["required_for_reference_window_tools"]
    primer = paths["optional_for_primer_specificity"]
    viewer = paths["planned_for_gene_viewer_tracks"]
    assert isinstance(crispr, dict)
    assert isinstance(reference, dict)
    assert isinstance(primer, dict)
    assert isinstance(viewer, dict)
    return {
        "do_not_change_before_approval": {
            "LLM_PROVIDER": "mock",
            "CRISPR_OFFTARGET_PROVIDER": "auto",
            "PRIMER_SPECIFICITY_PROVIDER": "template",
        },
        "crispr_offtarget_flip_after_ready": {
            "CRISPR_OFFTARGET_PROVIDER": "indexed_sqlite",
            "CRISPR_OFFTARGET_INDEX_PATH": crispr["spcas9_sqlite"],
        },
        "reference_window_support": {
            "HG38_2BIT_RUNTIME_ASSET_MODE": "mounted_volume",
            "HG38_2BIT_RUNTIME_ASSET_PATH": reference["hg38_2bit"],
            "COORDINATE_RESOLVER_HG38_2BIT_PATH": reference["hg38_2bit"],
            "COORDINATE_RESOLVER_MANE_GFF_PATH": reference["mane_gff"],
            "COORDINATE_RESOLVER_REFSEQ_GFF_PATH": reference["refseq_gff"],
            "COORDINATE_RESOLVER_COMPACT_INDEX_PATH": reference["coordinate_index"],
        },
        "optional_primer_specificity_after_license_approval": {
            "PRIMER_SPECIFICITY_PROVIDER": "ucsc_ispcr",
            "UCSC_ISPCR_BINARY_PATH": primer["ucsc_ispcr_binary"],
            "UCSC_ISPCR_HG38_PATH": primer["ucsc_ispcr_hg38"],
        },
        "optional_protein_annotation_after_hmmer_ready": {
            "PROTEIN_ANNOTATION_ENABLED": "true",
            "PROTEIN_ANNOTATION_PFAM_HMM_PATH": viewer["pfam_hmm"],
        },
        "not_finalized_in_code_yet": [
            "dbSNP runtime VCF/TBI env names for primer SNP masking",
            "ClinVar gene-window VCF/TBI env names for viewer tracks",
            "AlphaMissense viewer heatmap env names",
        ],
    }


def _operator_preflight(paths: dict[str, object]) -> list[dict[str, object]]:
    crispr = paths["required_for_crispr_offtarget_flip"]
    assert isinstance(crispr, dict)
    index = crispr["spcas9_sqlite"]
    manifest = crispr["manifest"]
    return [
        {
            "name": "offtarget_index_verify",
            "command": (
                "python -m app.cli.eamos_crispr_offtarget_index verify "
                f"--index {index} --genome-build GRCh38 --min-target-count <manifest_target_count>"
            ),
            "expects": {
                "verification_ready": True,
                "genome_build_matches": True,
                "target_count_meets_min": True,
                "local_path_values_emitted": False,
            },
        },
        {
            "name": "offtarget_index_manifest",
            "command": (
                "python -m app.cli.eamos_crispr_offtarget_index manifest "
                f"--index {index} --artifact-uri <private_artifact_uri> "
                "--source-version <source_genome_version> > "
                f"{manifest}"
            ),
            "expects": {
                "ready": True,
                "actual_sha256": "recorded",
                "launch_gate": None,
                "local_path_values_emitted": False,
            },
        },
        {
            "name": "advanced_crispr_score_preflight",
            "command": "python -m app.cli.eamos_crispr_score_preflight --compact",
            "expects": {
                "local_deterministic_default_remains_available": True,
                "crisprscore_r_unavailable_is_not_fatal": True,
            },
        },
        {
            "name": "source_asset_preflight",
            "command": "python -m app.cli.eamos_source_asset_preflight --compact",
            "expects": {
                "startup_downloads": "not_used",
                "uploads_or_imports": "not_used",
                "local_path_values_emitted": False,
            },
        },
    ]


def _crispr_offtarget_full_index_runbook(paths: dict[str, object]) -> dict[str, object]:
    crispr = paths["required_for_crispr_offtarget_flip"]
    reference = paths["required_for_reference_window_tools"]
    assert isinstance(crispr, dict)
    assert isinstance(reference, dict)
    index = crispr["spcas9_sqlite"]
    manifest = crispr["manifest"]
    source = reference["hg38_2bit"]
    source_version = "ucsc-hg38-md5-dcc3ea27079aa6dc3f9deccd7275e0f8"
    return {
        "input_source": {
            "kind": "twobit",
            "genome_build": "GRCh38",
            "source_name": "UCSC hg38.2bit",
            "source_version": source_version,
            "expected_path_on_build_host": source,
            "expected_size_bytes": 835_393_456,
            "expected_md5": "dcc3ea27079aa6dc3f9deccd7275e0f8",
            "verify_before_build": f"Get-FileHash -Algorithm MD5 {source}",
        },
        "full_build": {
            "working_directory": "app/backend",
            "command": (
                "python -m app.cli.eamos_crispr_offtarget_index build "
                f"--twobit {source} --output {index} --genome-build GRCh38 "
                f"--source-version {source_version}"
            ),
            "expected_output_path": index,
            "expected_ready_field": "ready=true",
            "artifact_policy": "Build outside web deploy/startup; do not commit generated SQLite, genome, or manifest artifacts.",
        },
        "checksum_manifest_flow": [
            {
                "step": "estimate",
                "command": (
                    "python -m app.cli.eamos_crispr_offtarget_index estimate "
                    f"--twobit {source} --genome-build GRCh38 "
                    f"--source-version {source_version}"
                ),
                "records": ["target_count", "estimated_sqlite_bytes"],
            },
            {
                "step": "build",
                "command": (
                    "python -m app.cli.eamos_crispr_offtarget_index build "
                    f"--twobit {source} --output {index} --genome-build GRCh38 "
                    f"--source-version {source_version}"
                ),
                "records": ["target_count", "actual_size_bytes"],
            },
            {
                "step": "verify",
                "command": (
                    "python -m app.cli.eamos_crispr_offtarget_index verify "
                    f"--index {index} --genome-build GRCh38 "
                    "--min-target-count <estimate_target_count>"
                ),
                "expects": {
                    "verification_ready": True,
                    "genome_build_matches": True,
                    "target_count_meets_min": True,
                    "local_path_values_emitted": False,
                },
            },
            {
                "step": "manifest",
                "command": (
                    "python -m app.cli.eamos_crispr_offtarget_index manifest "
                    f"--index {index} --artifact-uri <private_artifact_uri> "
                    f"--source-version {source_version} > {manifest}"
                ),
                "records": ["actual_sha256", "target_count", "source_version"],
            },
        ],
        "pilot_tiny_proof": {
            "purpose": "Use when a full hg38 build is impractical on the local machine.",
            "input": "Synthetic FASTA containing one SpCas9 NGG target.",
            "commands": [
                "python -m app.cli.eamos_crispr_offtarget_index estimate --fasta <tiny.fa> --genome-build GRCh38 --source-version pilot-tiny",
                "python -m app.cli.eamos_crispr_offtarget_index build --fasta <tiny.fa> --output <scratch>/spcas9_offtargets.sqlite --genome-build GRCh38 --source-version pilot-tiny",
                "python -m app.cli.eamos_crispr_offtarget_index verify --index <scratch>/spcas9_offtargets.sqlite --genome-build GRCh38 --min-target-count 1",
                "python -m app.cli.eamos_crispr_offtarget_index manifest --index <scratch>/spcas9_offtargets.sqlite --artifact-uri <private_artifact_uri> --source-version pilot-tiny",
            ],
            "expects": {
                "estimate_target_count_at_least": 1,
                "verify_verification_ready": True,
                "manifest_ready": True,
                "manifest_actual_sha256_length": 64,
                "local_path_values_emitted": False,
            },
        },
        "render_copy_mount": {
            "target_path": index,
            "manifest_path": manifest,
            "instructions": [
                "Copy the built SQLite file and manifest onto the mounted Render disk under /var/data/eamos/bio_assets/crispr/.",
                "Use Render Shell, scp, or a controlled runtime copy command during an off-peak maintenance window.",
                "Do not build or download the full index during Render build, predeploy, app startup, or request handling.",
                "Run verify and manifest on the mounted file before changing CRISPR_OFFTARGET_PROVIDER.",
            ],
        },
        "provider_cache_readiness": {
            "pre_flip_expected": {
                "configured_provider": "auto",
                "status": "mock_fallback",
                "indexed_sqlite.ready": False,
                "request_time_supabase_search": False,
            },
            "post_flip_required": {
                "configured_provider": "indexed_sqlite",
                "status": "indexed_ready",
                "indexed_sqlite.ready": True,
                "indexed_sqlite.genome_build": "GRCh38",
                "indexed_sqlite.target_count": ">= <manifest_target_count>",
                "indexed_sqlite.local_path_values_emitted": False,
                "request_time_supabase_search": False,
                "launch_gate": None,
            },
        },
        "rollback_values": {
            "CRISPR_OFFTARGET_PROVIDER": "auto",
            "PRIMER_SPECIFICITY_PROVIDER": "template",
            "LLM_PROVIDER": "mock",
        },
    }


def _post_flip_smoke(render_backend_url: str, vercel_app_url: str) -> list[dict[str, object]]:
    return [
        {
            "name": "sg_healthz",
            "command": f"curl -fsS {render_backend_url}/healthz",
            "expects": {"status": "ok", "llm_provider": "mock"},
        },
        {
            "name": "sg_provider_cache",
            "command": f"curl -fsS {render_backend_url}/api/v1/health/provider-cache",
            "expects": {
                "providers.crispr.off_target_screening.indexed_sqlite.ready": True,
                "providers.crispr.off_target_screening.request_time_supabase_search": False,
            },
        },
        {
            "name": "vercel_provider_cache_proxy",
            "command": f"curl -fsS {vercel_app_url}/api/v1/health/provider-cache",
            "expects": {
                "providers.crispr.off_target_screening.indexed_sqlite.ready": True,
            },
        },
        {
            "name": "workbench_api_probes",
            "commands": [
                "POST /api/v1/primer/design",
                "POST /api/v1/crispr/design",
                "POST /api/v1/crispr/offtargets",
                "POST /api/v1/crispr/screening-primers",
                "POST /api/v1/crispr/ssodn",
                "POST /api/v1/align/reference",
                "POST /api/v1/crispr/tide",
            ],
            "expects": {
                "source_backed_or_warning_labeled": True,
                "no_startup_downloads": True,
                "no_raw_local_paths": True,
            },
        },
    ]


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Emit the Eamos Workbench Render approval bundle without mutating "
            "Render, env vars, storage, or source assets."
        )
    )
    parser.add_argument("--render-backend-url", default=RENDER_BACKEND_URL)
    parser.add_argument("--vercel-app-url", default=VERCEL_APP_URL)
    parser.add_argument("--asset-root", default=RENDER_BIO_ASSET_ROOT)
    parser.add_argument("--compact", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    bundle = build_render_approval_bundle(
        render_backend_url=args.render_backend_url,
        vercel_app_url=args.vercel_app_url,
        asset_root=args.asset_root,
    )
    print(json.dumps(bundle, indent=None if args.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
