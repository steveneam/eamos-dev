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
    PROTEIN_ANNOTATION_SOURCE_IDS,
    POST_REFERENCE_DAY1_SOURCE_IDS,
    ProteinAssetInspection,
    SourceAssetReadiness,
    docx_blueprint_summary,
    inspect_hg38_runtime_asset,
    inspect_protein_annotation_assets,
)
from app.data_sources.registry import RESTRICTED_PREDICTOR_SOURCE_IDS, DataSourceRegistry
from app.data_sources.source_manifest import build_post_reference_source_readiness
from app.services.local_evidence_orchestrator import (
    LOCAL_EVIDENCE_RUNTIME_FLOWS,
    LocalEvidenceRuntimeGate,
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
    args = parser.parse_args(argv)

    settings_kwargs: dict[str, Any] = {"jwt_secret": "source-preflight-local"}
    if args.hg38_path is not None:
        settings_kwargs["hg38_2bit_runtime_asset_path"] = args.hg38_path
    settings = Settings(**settings_kwargs)

    report = build_source_asset_preflight_report(
        settings=settings,
        verify_hg38_checksum=args.verify_hg38_checksum,
        verify_protein_checksums=args.verify_protein_checksums,
    )
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0


def build_source_asset_preflight_report(
    *,
    settings: Settings,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    verify_hg38_checksum: bool = False,
    verify_protein_checksums: bool = False,
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
    return {
        "mode": "source_asset_readiness",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "docx_blueprint": docx_blueprint_summary(registry=registry),
        "guardrails": {
            "network": "not_used",
            "supabase": "not_used",
            "production_downloads": "not_used",
            "runtime_local_source_wiring": "not_used",
            "uploads_or_imports": "not_used",
            "restricted_predictor_unlocks": "not_used",
        },
        "source_manifest": _readiness_summary(readiness),
        "hg38_runtime_asset": _runtime_asset_summary(
            hg38,
            checksum_verified=verify_hg38_checksum,
        ),
        "protein_annotation_assets": _protein_asset_summary(
            protein_assets,
            checksum_verified=verify_protein_checksums,
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
