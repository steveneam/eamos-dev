from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.data_sources import (
    DEFAULT_DATA_SOURCE_REGISTRY,
    HG38_MATERIALIZATION_FAILURE_BOUNDARIES,
    PROTEIN_ANNOTATION_SOURCE_IDS,
    POST_REFERENCE_DAY1_SOURCE_IDS,
    ProteinAssetInspection,
    SourceAssetReadiness,
    SourceAssetMaterializationStore,
    docx_blueprint_summary,
    inspect_hg38_runtime_asset,
    inspect_protein_annotation_assets,
    probe_hg38_materialization_status,
)
from app.data_sources.registry import RESTRICTED_PREDICTOR_SOURCE_IDS, DataSourceRegistry
from app.data_sources.source_manifest import build_post_reference_source_readiness
from app.repos.supabase_local_model_cache_repo import build_supabase_local_model_cache_store
from app.services.build_ledger import build_backend_build_ledger
from app.services.compact_coordinate_index import inspect_compact_coordinate_index
from app.services.local_evidence_orchestrator import (
    LOCAL_EVIDENCE_RUNTIME_FLOWS,
    LocalEvidenceRuntimeGate,
)
from app.services.predictor_runtime import (
    inspect_alphamissense_runtime_asset,
    inspect_esm1b_runtime_asset,
)
from app.services.pvs1_nmd import inspect_pvs1_nmd_runtime
from app.services.source_downloads import (
    SourceDownloadStatus,
    build_source_download_items,
    execute_source_downloads,
)
from app.services.source_reader_proofs import execute_source_reader_proofs
from app.services.source_storage_uploads import (
    SourceStorageUploadStatus,
    build_source_storage_upload_items,
    execute_source_storage_uploads,
)

CURRENT_WEB_RUNTIME_RENDER_DISK_GB = 15
FULL_NONCOMMERCIAL_RENDER_DISK_GB = 60

_RENDER_RUNTIME_ENV_NAMES = (
    "HG38_2BIT_RUNTIME_ASSET_MODE",
    "HG38_2BIT_RUNTIME_ASSET_PATH",
    "HG38_2BIT_RUNTIME_ASSET_OBJECT_URI",
    "PROTEIN_ANNOTATION_ENABLED",
    "PROTEIN_ANNOTATION_HMMSCAN_PATH",
    "PROTEIN_ANNOTATION_HMMPRESS_PATH",
    "PROTEIN_ANNOTATION_PFAM_HMM_PATH",
    "PROTEIN_ANNOTATION_PFAM_HMM_GZ_PATH",
    "PROTEIN_ANNOTATION_PFAM_HMM_GZ_OBJECT_URI",
)

_FULL_STACK_RENDER_BLOCKERS = (
    "terms_review",
    "backend_storage_policy_review",
    "reader_compatibility_proof",
    "explicit_download_or_import_approval",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Eamos source asset readiness preflight for the local-first "
            "source/model rollout."
        )
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument(
        "--hg38-path",
        type=Path,
        help="optional hg38.2bit runtime path override for inspection",
    )
    parser.add_argument(
        "--verify-hg38-checksum",
        action="store_true",
        help="compute hg38.2bit MD5 during inspection; omitted by default for speed",
    )
    parser.add_argument(
        "--verify-protein-checksums",
        action="store_true",
        help=(
            "compute MD5 and SHA256 for staged protein annotation assets; "
            "omitted by default because the bundle is large"
        ),
    )
    parser.add_argument(
        "--probe-supabase-materialization",
        action="store_true",
        help=(
            "perform a read-only private Supabase materialization metadata probe. "
            "No uploads, imports, bucket changes, or secrets are emitted."
        ),
    )
    args = parser.parse_args(argv)

    settings_kwargs: dict[str, Any] = {"jwt_secret": "source-preflight-local"}
    if args.hg38_path is not None:
        settings_kwargs["hg38_2bit_runtime_asset_path"] = args.hg38_path
    settings = Settings(**settings_kwargs)
    materialization_store = (
        build_supabase_local_model_cache_store(settings)
        if args.probe_supabase_materialization
        else None
    )

    report = build_source_asset_preflight_report(
        settings=settings,
        verify_hg38_checksum=args.verify_hg38_checksum,
        verify_protein_checksums=args.verify_protein_checksums,
        probe_materialization=args.probe_supabase_materialization,
        materialization_store=materialization_store,
    )
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0


def build_source_asset_preflight_report(
    *,
    settings: Settings,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    verify_hg38_checksum: bool = False,
    verify_protein_checksums: bool = False,
    probe_materialization: bool = False,
    materialization_store: SourceAssetMaterializationStore | None = None,
) -> dict[str, Any]:
    readiness = build_post_reference_source_readiness(registry=registry)
    gate = LocalEvidenceRuntimeGate.from_settings(settings)
    hg38 = inspect_hg38_runtime_asset(
        settings,
        registry=registry,
        verify_checksum=verify_hg38_checksum,
    )
    protein_assets = inspect_protein_annotation_assets(
        registry=registry,
        verify_checksums=verify_protein_checksums,
    )
    source_manifest = _readiness_summary(readiness)
    hg38_summary = _runtime_asset_summary(
        hg38,
        checksum_verified=verify_hg38_checksum,
    )
    compact_coordinate_index = inspect_compact_coordinate_index(
        settings,
        verify_checksum=False,
    )
    protein_summary = _protein_asset_summary(
        protein_assets,
        checksum_verified=verify_protein_checksums,
    )
    build_ledger = build_backend_build_ledger(
        settings,
        registry=registry,
        materialization_store=materialization_store,
    )
    predictor_runtime_assets = _predictor_runtime_asset_summary(
        settings=settings,
        registry=registry,
        materialization_store=materialization_store,
    )
    return {
        "mode": "source_asset_readiness",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "docx_blueprint": docx_blueprint_summary(registry=registry),
        "guardrails": {
            "network": (
                "read_only_supabase_materialization_probe" if probe_materialization else "not_used"
            ),
            "supabase": (
                "read_only_materialization_probe" if probe_materialization else "not_used"
            ),
            "production_downloads": "not_used",
            "runtime_local_source_wiring": "not_used",
            "uploads_or_imports": "not_used",
            "restricted_predictor_unlocks": "not_used",
        },
        "source_manifest": source_manifest,
        "download_staging": _download_staging_summary(),
        "reader_compatibility_proofs": _reader_compatibility_proof_summary(),
        "private_storage_upload_plan": _private_storage_upload_plan_summary(),
        "hg38_runtime_asset": hg38_summary,
        "runtime_materialization_probe": _runtime_materialization_probe_summary(
            settings=settings,
            materialization_store=materialization_store,
            registry=registry,
            probe_materialization=probe_materialization,
            verify_checksum=verify_hg38_checksum,
        ),
        "compact_coordinate_index": compact_coordinate_index.to_sanitized_dict(),
        "predictor_runtime_assets": predictor_runtime_assets,
        "protein_annotation_assets": protein_summary,
        "build_ledger": build_ledger,
        "render_persistent_disk_gate": _render_persistent_disk_gate_summary(
            readiness=readiness,
            hg38=hg38,
            protein_assets=protein_assets,
            verify_hg38_checksum=verify_hg38_checksum,
            verify_protein_checksums=verify_protein_checksums,
        ),
        "local_evidence_gate": _local_evidence_gate_summary(gate),
        "restricted_predictors": _restricted_predictor_summary(registry),
        "myvariant_policy": _myvariant_policy_summary(registry),
    }


def _readiness_summary(readiness: tuple[SourceAssetReadiness, ...]) -> dict[str, Any]:
    missing_counts = Counter(
        requirement for item in readiness for requirement in item.missing_requirements
    )
    storage_targets = Counter(item.storage_target for item in readiness)
    return {
        "source_ids": list(POST_REFERENCE_DAY1_SOURCE_IDS),
        "total_sources": len(readiness),
        "ready_for_download_or_import_count": sum(
            1 for item in readiness if item.ready_for_download_or_import
        ),
        "download_approved_count": sum(1 for item in readiness if item.download_approved),
        "backend_owned_storage_count": sum(1 for item in readiness if item.backend_owned_storage),
        "requires_c_drive_staging": [
            item.source_id for item in readiness if item.requires_c_drive_staging
        ],
        "storage_targets": dict(sorted(storage_targets.items())),
        "missing_requirement_counts": dict(sorted(missing_counts.items())),
        "sources": [_source_summary(item) for item in readiness],
    }


def _source_summary(item: SourceAssetReadiness) -> dict[str, Any]:
    return {
        "source_id": item.source_id,
        "display_name": item.display_name,
        "files_or_api": list(item.files_or_api),
        "source_url": item.source_url,
        "source_url_status": item.source_url_status,
        "source_version": item.source_version,
        "storage_target": item.storage_target,
        "temporary_staging": item.temporary_staging,
        "adapter": item.adapter,
        "license_status": item.license_status.value,
        "download_approved": item.download_approved,
        "ready_for_download_or_import": item.ready_for_download_or_import,
        "backend_owned_storage": item.backend_owned_storage,
        "missing_requirements": list(item.missing_requirements),
    }


def _download_staging_summary() -> dict[str, Any]:
    result = execute_source_downloads(
        build_source_download_items(include_large=True),
        download=False,
    )
    status_counts = Counter(item.status.value for item in result.items)
    return {
        "network_used": False,
        "download_performed": False,
        "present_count": result.present_count,
        "downloaded_count": result.downloaded_count,
        "skipped_large_count": result.skipped_large_count,
        "partial_count": status_counts.get(SourceDownloadStatus.PARTIAL_DOWNLOAD.value, 0),
        "planned_count": status_counts.get(SourceDownloadStatus.PLANNED.value, 0),
        "status_counts": dict(sorted(status_counts.items())),
        "items": [
            {
                "source_id": item.source_id,
                "asset_id": item.asset_id,
                "role": item.role,
                "status": item.status.value,
                "large_asset": item.large_asset,
                "actual_size_bytes": item.actual_size_bytes,
                "expected_size_bytes": item.expected_size_bytes,
                "destination": str(item.destination),
                "message": item.message,
            }
            for item in result.items
        ],
    }


def _private_storage_upload_plan_summary() -> dict[str, Any]:
    result = execute_source_storage_uploads(
        build_source_storage_upload_items(),
        upload=False,
    )
    status_counts = Counter(item.status.value for item in result.items)
    return {
        "network_used": False,
        "upload_performed": False,
        "planned_count": result.planned_count,
        "uploaded_count": result.uploaded_count,
        "blocked_count": result.blocked_count,
        "failed_count": result.failed_count,
        "eligible_private_upload_count": status_counts.get(
            SourceStorageUploadStatus.PLANNED.value,
            0,
        ),
        "status_counts": dict(sorted(status_counts.items())),
        "items": [
            {
                "source_id": item.source_id,
                "asset_id": item.asset_id,
                "role": item.role,
                "status": item.status.value,
                "byte_size": item.byte_size,
                "bucket_id": item.bucket_id,
                "object_path": item.object_path,
                "manifest_object_path": item.manifest_object_path,
                "message": item.message,
            }
            for item in result.items
        ],
    }


def _reader_compatibility_proof_summary() -> dict[str, Any]:
    result = execute_source_reader_proofs()
    status_counts = Counter(item.status.value for item in result.items)
    return result.to_dict() | {
        "network_used": False,
        "runtime_mutation_performed": False,
        "status_counts": dict(sorted(status_counts.items())),
    }


def _runtime_asset_summary(inspection: Any, *, checksum_verified: bool) -> dict[str, Any]:
    return {
        "source_id": inspection.source_id,
        "mode": inspection.mode,
        "status": inspection.status.value,
        "ready": inspection.ready,
        "path": str(inspection.path),
        "expected_size_bytes": inspection.expected_size_bytes,
        "actual_size_bytes": inspection.actual_size_bytes,
        "checksum_verified": checksum_verified,
        "expected_md5": inspection.expected_md5,
        "actual_md5": inspection.actual_md5,
        "object_uri": inspection.object_uri,
        "reader_requires_local_path": inspection.reader_requires_local_path,
        "message": inspection.message,
    }


def _predictor_runtime_asset_summary(
    *,
    settings: Settings,
    registry: DataSourceRegistry,
    materialization_store: SourceAssetMaterializationStore | None,
) -> dict[str, Any]:
    alphamissense = inspect_alphamissense_runtime_asset(
        settings,
        registry=registry,
        materialization_store=materialization_store,
        verify_checksum=False,
    )
    esm1b = inspect_esm1b_runtime_asset(
        settings,
        registry=registry,
        materialization_store=materialization_store,
        verify_checksum=False,
    )
    pvs1_nmd = inspect_pvs1_nmd_runtime()
    return {
        "alphamissense": _predictor_runtime_summary(
            alphamissense,
            public_serialization_allowed=False,
        ),
        "esm1b": _predictor_runtime_summary(
            esm1b,
            public_serialization_allowed=False,
        ),
        "pvs1_nmd": {
            "source_id": pvs1_nmd.source_id,
            "status": pvs1_nmd.status,
            "available": pvs1_nmd.available,
            "runtime_wired": pvs1_nmd.runtime_wired,
            "public_serialization_allowed": pvs1_nmd.public_serialization_allowed,
            "engine": pvs1_nmd.engine,
            "storage_required": pvs1_nmd.storage_required,
            "status_notes": list(pvs1_nmd.warnings),
        },
        "public_serialization_locked": ["alphamissense", "esm1b"],
    }


def _predictor_runtime_summary(
    inspection: Any,
    *,
    public_serialization_allowed: bool,
) -> dict[str, Any]:
    return {
        "source_id": inspection.source_id,
        "asset_role": inspection.asset_role,
        "mode": inspection.mode,
        "status": inspection.status.value,
        "ready": inspection.ready,
        "actual_size_bytes": inspection.actual_size_bytes,
        "reader_requires_local_path": inspection.reader_requires_local_path,
        "materialization_status": inspection.materialization_status,
        "public_serialization_allowed": public_serialization_allowed,
    }


def _runtime_materialization_probe_summary(
    *,
    settings: Settings,
    materialization_store: SourceAssetMaterializationStore | None,
    registry: DataSourceRegistry,
    probe_materialization: bool,
    verify_checksum: bool,
) -> dict[str, Any]:
    common = {
        "read_only": True,
        "mutations_performed": False,
        "secret_values_emitted": False,
        "local_path_values_emitted": False,
        "object_uri_values_emitted": False,
    }
    if not probe_materialization:
        return {
            "enabled": materialization_store is not None,
            "probe_performed": False,
            "ready": False,
            "status": "not_requested",
            "failure_boundaries": dict(HG38_MATERIALIZATION_FAILURE_BOUNDARIES),
            **common,
        }

    return {
        **probe_hg38_materialization_status(
            settings,
            materialization_store,
            registry=registry,
            verify_checksum=verify_checksum,
        ),
        **common,
    }


def _protein_asset_summary(
    inspections: tuple[ProteinAssetInspection, ...],
    *,
    checksum_verified: bool,
) -> dict[str, Any]:
    status_counts = Counter(item.status.value for item in inspections)
    return {
        "source_ids": list(PROTEIN_ANNOTATION_SOURCE_IDS),
        "asset_count": len(inspections),
        "present_count": sum(1 for item in inspections if item.present),
        "ready_count": sum(1 for item in inspections if item.ready),
        "all_present": all(item.present for item in inspections),
        "all_ready": all(item.ready for item in inspections),
        "checksum_verified": checksum_verified,
        "status_counts": dict(sorted(status_counts.items())),
        "assets": [
            {
                "asset_id": item.asset_id,
                "source_ids": list(item.source_ids),
                "role": item.role,
                "status": item.status.value,
                "ready": item.ready,
                "path": str(item.path),
                "expected_size_bytes": item.expected_size_bytes,
                "actual_size_bytes": item.actual_size_bytes,
                "expected_md5": item.expected_md5,
                "actual_md5": item.actual_md5,
                "expected_sha256": item.expected_sha256,
                "actual_sha256": item.actual_sha256,
                "checksum_verified": item.checksum_verified,
                "message": item.message,
            }
            for item in inspections
        ],
    }


def _render_persistent_disk_gate_summary(
    *,
    readiness: tuple[SourceAssetReadiness, ...],
    hg38: Any,
    protein_assets: tuple[ProteinAssetInspection, ...],
    verify_hg38_checksum: bool,
    verify_protein_checksums: bool,
) -> dict[str, Any]:
    ready_for_import_count = sum(1 for item in readiness if item.ready_for_download_or_import)
    full_stack_ready_for_payment = ready_for_import_count == len(readiness)
    missing_requirement_counts = Counter(
        requirement for item in readiness for requirement in item.missing_requirements
    )
    full_stack_blockers = [
        requirement
        for requirement in _FULL_STACK_RENDER_BLOCKERS
        if missing_requirement_counts.get(requirement, 0)
    ]

    pfam_profile = next(
        (item for item in protein_assets if item.asset_id == "pfam_a_hmm_gz"),
        None,
    )
    current_runtime_ready_for_payment = bool(hg38.ready and pfam_profile and pfam_profile.present)
    current_runtime_missing = []
    if not hg38.ready:
        current_runtime_missing.append("hg38_runtime_asset_ready")
    if pfam_profile is None or not pfam_profile.present:
        current_runtime_missing.append("pfam_a_hmm_gz_present")
    if not verify_hg38_checksum:
        current_runtime_missing.append("hg38_checksum_verification_before_runtime_enablement")
    if not verify_protein_checksums:
        current_runtime_missing.append(
            "protein_asset_checksum_verification_before_runtime_enablement"
        )

    return {
        "status": (
            "full_tier_stack_ready_for_paid_render_disk"
            if full_stack_ready_for_payment
            else "full_tier_stack_not_ready_for_paid_render_disk"
        ),
        "summary": (
            "The narrow hg38+Pfam web-runtime proof can reach a paid Render disk "
            "decision separately from the larger Tier 1/2/3 source rollout."
        ),
        "mutations_performed": False,
        "network_used": False,
        "secret_values_emitted": False,
        "object_uri_values_emitted": False,
        "current_hg38_pfam_web_runtime": {
            "scope": "hg38_2bit_plus_local_hmmer_pfam_runtime",
            "ready_for_paid_render_disk_decision": current_runtime_ready_for_payment,
            "next_paid_step_if_approved": "provision_render_persistent_disk",
            "recommended_disk_gb": CURRENT_WEB_RUNTIME_RENDER_DISK_GB,
            "disk_mount_required_before_env_enablement": True,
            "required_env_names": list(_RENDER_RUNTIME_ENV_NAMES),
            "remaining_before_runtime_enablement": current_runtime_missing,
            "notes": (
                "Do not enable PROTEIN_ANNOTATION_ENABLED on the public web service "
                "until the Pfam HMM has a persistent mounted path and the startup or "
                "runtime materialization path has verified size and checksums."
            ),
        },
        "full_noncommercial_tier_stack": {
            "scope": "tier_1_2_3_sources_excluding_commercial_gated_predictors",
            "ready_for_paid_render_disk_decision": full_stack_ready_for_payment,
            "recommended_disk_gb_after_unpaid_readiness": FULL_NONCOMMERCIAL_RENDER_DISK_GB,
            "ready_for_download_or_import_count": ready_for_import_count,
            "total_sources": len(readiness),
            "blocking_requirement_counts": {
                requirement: missing_requirement_counts[requirement]
                for requirement in full_stack_blockers
            },
            "blocked_by": full_stack_blockers,
        },
        "excluded_from_disk_estimates": [
            "SpliceAI",
            "CADD",
            "REVEL",
            "PrimateAI-3D",
            "InterVar/ANNOVAR/OMIM restricted production use",
            "AlphaMissense",
            "InterProScan optional licensed apps",
            "future local LLM or transformer weights",
        ],
    }


def _local_evidence_gate_summary(gate: LocalEvidenceRuntimeGate) -> dict[str, Any]:
    decisions = [gate.for_flow(flow) for flow in LOCAL_EVIDENCE_RUNTIME_FLOWS]
    return {
        "enabled": gate.enabled,
        "allowed_flows": list(gate.allowed_flows),
        "require_real_apis": gate.require_real_apis,
        "use_real_apis": gate.use_real_apis,
        "configured_runtime_flows_enabled": any(decision.enabled for decision in decisions),
        "preflight_wires_runtime": False,
        "warnings": list(gate.warnings),
        "flows": [
            {
                "flow": decision.flow,
                "enabled": decision.enabled,
                "reason": decision.reason,
                "warnings": list(decision.warnings),
            }
            for decision in decisions
        ],
    }


def _restricted_predictor_summary(registry: DataSourceRegistry) -> dict[str, Any]:
    records = [registry.get(source_id) for source_id in sorted(RESTRICTED_PREDICTOR_SOURCE_IDS)]
    locked = all(not record.download_approved and not record.allowed_fields for record in records)
    return {
        "locked": locked,
        "source_ids": [record.source_id for record in records],
        "sources": [
            {
                "source_id": record.source_id,
                "license_status": record.license_status.value,
                "download_approved": record.download_approved,
                "allowed_fields": list(record.allowed_fields),
                "restricted_fields": list(record.restricted_fields),
            }
            for record in records
        ],
    }


def _myvariant_policy_summary(registry: DataSourceRegistry) -> dict[str, Any]:
    record = registry.get("myvariant_gnomad_only")
    return {
        "source_id": record.source_id,
        "enabled_for_runtime": False,
        "source_url_status": record.source_url_status,
        "license_status": record.license_status.value,
        "allowed_fields": list(record.allowed_fields),
        "restricted_fields": list(record.restricted_fields),
        "cache_policy": record.cache_policy,
        "note": "gnomAD-only after policy review; predictor fields remain denied",
    }


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
