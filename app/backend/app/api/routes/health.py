from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from app.core.db import ping_database
from app.data_sources.local_inventory import LOCAL_HG38_2BIT_SOURCE_ID
from app.data_sources.runtime_assets import (
    inspect_hg38_runtime_asset,
    probe_hg38_materialization_status,
)
from app.services.predictor_runtime import (
    inspect_alphamissense_runtime_asset,
    inspect_capice_runtime_assets,
    inspect_ci_spliceai_runtime_assets,
    inspect_esm1b_runtime_asset,
)
from app.services.pvs1_nmd import inspect_pvs1_nmd_runtime
from app.services.build_ledger import build_backend_build_ledger
from app.services.compact_coordinate_index import inspect_compact_coordinate_index
from app.services.clingen_local import inspect_clingen_local_store
from app.services.pubmed_local import inspect_pubmed_local_store
from app.services.crispr_design import (
    CRISPR_PROVIDER_CRISPRSCORE_R,
    CRISPR_PROVIDER_LOCAL_DETERMINISTIC,
    inspect_crisprscore_r_runtime,
)
from app.services.crispr_offtarget_index import inspect_crispr_offtarget_index
from app.services.crispr_offtarget_screening import (
    CRISPR_OFFTARGET_PROVIDER_AUTO,
    CRISPR_OFFTARGET_PROVIDER_INDEXED_SQLITE,
    CRISPR_OFFTARGET_PROVIDER_MOCK,
)
from app.services.workbench_design import (
    PRIMER_SPECIFICITY_TEMPLATE,
    PRIMER_SPECIFICITY_UCSC_ISPCR,
)

router = APIRouter(tags=["health"])


# NOTE: This endpoint is intentionally public in dev so the frontend can probe
# mode flags (llm_provider, use_real_apis) without auth. If /healthz is ever
# auth-gated for production, split the mode flags into a separate public
# GET /api/v1/runtime-info behind no auth dependency.
@router.get("/healthz")
def healthz(request: Request) -> dict[str, object]:
    ping_database(request.app.state.db_session_factory)
    settings = request.app.state.settings
    return {
        "status": "ok",
        "database": "ok",
        "llm_provider": settings.llm_provider,
        "use_real_apis": settings.use_real_apis,
    }


@router.get("/api/v1/health/provider-cache")
def provider_cache_health(request: Request) -> dict[str, object]:
    ping_database(request.app.state.db_session_factory)
    settings = request.app.state.settings
    materialization_store = getattr(request.app.state, "supabase_local_model_cache_store", None)
    protein_annotation_status = _protein_annotation_health(
        settings,
        getattr(request.app.state, "protein_annotation_service", None),
    )
    source_cache_repo = getattr(request.app.state, "source_cache_repo", None)
    source_cache: dict[str, Any] = {"enabled": source_cache_repo is not None}
    if source_cache_repo is not None:
        source_cache.update(source_cache_repo.health_summary())

    return {
        "status": "ok",
        "database": "ok",
        "source_cache": source_cache,
        "source_assets": _source_asset_health(
            settings,
            materialization_store,
        ),
        "build_ledger": build_backend_build_ledger(
            settings,
            materialization_store=materialization_store,
            protein_annotation_status=protein_annotation_status,
        ),
        "providers": {
            "crispr": _crispr_provider_health(settings),
            "indexed_predictors": _indexed_predictor_health(
                settings,
                materialization_store,
            ),
            "protein_annotation": protein_annotation_status,
        },
    }


def _source_asset_health(settings, materialization_store) -> dict[str, object]:
    try:
        inspection = inspect_hg38_runtime_asset(settings, verify_checksum=False)
        source_id = inspection.source_id
        mode = inspection.mode
        local_cache_ready = inspection.ready
        local_cache_status = inspection.status.value
        expected_size_bytes = inspection.expected_size_bytes
        actual_size_bytes = inspection.actual_size_bytes
        reader_requires_local_path = inspection.reader_requires_local_path
    except Exception:
        source_id = LOCAL_HG38_2BIT_SOURCE_ID
        mode = settings.hg38_2bit_runtime_asset_mode
        local_cache_ready = False
        local_cache_status = "runtime_asset_probe_failed"
        expected_size_bytes = None
        actual_size_bytes = None
        reader_requires_local_path = True

    metadata = probe_hg38_materialization_status(
        settings,
        materialization_store,
        verify_checksum=False,
    )

    return {
        "hg38_2bit": {
            "source_id": source_id,
            "mode": mode,
            "local_cache_ready": local_cache_ready,
            "local_cache_status": local_cache_status,
            "expected_size_bytes": expected_size_bytes,
            "actual_size_bytes": actual_size_bytes,
            "checksum_verified": False,
            "reader_requires_local_path": reader_requires_local_path,
            "materialization_metadata": metadata,
        },
        "compact_coordinate_index": _compact_coordinate_index_health(settings),
        "clingen_local": _clingen_local_health(settings),
        "pubmed_local": _pubmed_local_health(settings),
    }


def _compact_coordinate_index_health(settings) -> dict[str, object]:
    try:
        return inspect_compact_coordinate_index(
            settings,
            verify_checksum=False,
            load_records=False,
        ).to_sanitized_dict()
    except Exception:
        return {
            "source_id": "eamos_compact_coordinate_index",
            "status": "runtime_asset_probe_failed",
            "ready": False,
            "schema_version": None,
            "artifact_version": None,
            "genome_build": None,
            "variant_count": 0,
            "transcript_count": 0,
            "actual_size_bytes": None,
            "checksum_verified": False,
            "actual_sha256": None,
            "message": "compact coordinate index probe failed",
            "status_notes": [],
            "source_runtime_scan_allowed": False,
            "startup_download_allowed": False,
        }


def _pubmed_local_health(settings) -> dict[str, object]:
    try:
        return inspect_pubmed_local_store(settings, verify_checksum=False).to_sanitized_dict()
    except Exception:
        return {
            "source_id": "eamos_pubmed_local",
            "status": "runtime_asset_probe_failed",
            "ready": False,
            "enabled": bool(settings.pubmed_local_enabled),
            "schema_version": None,
            "source_version": None,
            "article_count": 0,
            "licensed_abstract_count": 0,
            "metadata_only_count": 0,
            "deleted_count": 0,
            "coverage_count": 0,
            "domain_filtered_count": 0,
            "pmc_license_overlay_count": 0,
            "source_file_count": 0,
            "source_kind_counts": {},
            "import_stats_by_source": {},
            "fts_status": "unavailable",
            "actual_size_bytes": None,
            "checksum_verified": False,
            "checksum_value": None,
            "startup_download_allowed": False,
            "request_time_materialization_allowed": False,
            "secret_values_emitted": False,
            "local_path_values_emitted": False,
            "abstract_values_emitted": False,
        }


def _clingen_local_health(settings) -> dict[str, object]:
    try:
        return inspect_clingen_local_store(settings, verify_checksum=False).to_sanitized_dict()
    except Exception:
        return {
            "source_id": "eamos_clingen_local",
            "status": "runtime_asset_probe_failed",
            "ready": False,
            "enabled": bool(settings.clingen_local_enabled),
            "schema_version": None,
            "source_version": None,
            "classification_count": 0,
            "cspec_entity_count": 0,
            "cspec_link_count": 0,
            "actual_size_bytes": None,
            "checksum_verified": False,
            "checksum_algorithm": None,
            "checksum_value": None,
            "message": "ClinGen local source asset probe failed",
            "notices": [],
            "startup_download_allowed": False,
            "request_time_materialization_allowed": False,
            "secret_values_emitted": False,
            "local_path_values_emitted": False,
            "raw_source_rows_emitted": False,
            "public_serialization_allowed": True,
            "launch_gate": "clingen_local_materialization",
        }


def _indexed_predictor_health(settings, materialization_store) -> dict[str, object]:
    pvs1_nmd = inspect_pvs1_nmd_runtime()
    return {
        "alphamissense": _predictor_inspection_health(
            inspect_alphamissense_runtime_asset(
                settings,
                materialization_store=materialization_store,
                verify_checksum=False,
            ),
            public_serialization_allowed=True,
        ),
        "esm1b": _predictor_inspection_health(
            inspect_esm1b_runtime_asset(
                settings,
                materialization_store=materialization_store,
                verify_checksum=False,
            ),
            public_serialization_allowed=True,
            launch_gate="esm1b_score_file_terms_unconfirmed",
        ),
        "ci_spliceai": inspect_ci_spliceai_runtime_assets(settings).to_sanitized_dict(),
        "pvs1_nmd": {
            "available": pvs1_nmd.available,
            "status": pvs1_nmd.status,
            "source_id": pvs1_nmd.source_id,
            "runtime_wired": pvs1_nmd.runtime_wired,
            "public_serialization_allowed": pvs1_nmd.public_serialization_allowed,
            "engine": pvs1_nmd.engine,
            "storage_required": pvs1_nmd.storage_required,
            "status_notes": list(pvs1_nmd.warnings),
        },
        "mavedb": {
            "available": False,
            "status": "cc0_import_not_materialized",
            "runtime_wired": False,
            "public_serialization_allowed": False,
        },
        "capice": inspect_capice_runtime_assets(settings).to_sanitized_dict(),
    }


def _predictor_inspection_health(
    inspection,
    *,
    public_serialization_allowed: bool,
    launch_gate: str | None = None,
) -> dict[str, object]:
    return {
        "available": inspection.ready,
        "status": inspection.status.value,
        "source_id": inspection.source_id,
        "asset_role": inspection.asset_role,
        "mode": inspection.mode,
        "local_cache_ready": inspection.ready,
        "local_cache_status": inspection.status.value,
        "actual_size_bytes": inspection.actual_size_bytes,
        "reader_requires_local_path": inspection.reader_requires_local_path,
        "materialization_status": inspection.materialization_status,
        "public_serialization_allowed": public_serialization_allowed,
        "launch_gate": launch_gate,
    }


def _crispr_provider_health(settings) -> dict[str, object]:
    configured_provider = (settings.crispr_provider or "").strip().lower()
    if not configured_provider:
        configured_provider = CRISPR_PROVIDER_LOCAL_DETERMINISTIC

    local_provider = {
        "available": True,
        "status": "available",
        "score_sources": {
            "on_target": "heuristic",
            "off_target": "local_hsu_mit_in_context",
        },
    }
    crisprscore_provider = _crisprscore_r_health(settings, configured_provider)
    providers = {
        CRISPR_PROVIDER_LOCAL_DETERMINISTIC: local_provider,
        CRISPR_PROVIDER_CRISPRSCORE_R: crisprscore_provider,
    }
    configured_status = providers.get(configured_provider)
    configured_available = (
        bool(configured_status and configured_status["available"])
        if configured_provider in providers
        else False
    )
    return {
        "configured_provider": configured_provider,
        "available": configured_available,
        "status": "available" if configured_available else "unavailable",
        "providers": providers,
        "off_target_screening": _crispr_offtarget_health(settings),
        "primer_specificity": _primer_specificity_health(settings),
        "platform_gated_models": ["DeepHF", "DeepCpf1", "enPAM+GB"],
    }


def _crispr_offtarget_health(settings) -> dict[str, object]:
    configured_provider = (settings.crispr_offtarget_provider or "").strip().lower()
    if not configured_provider:
        configured_provider = CRISPR_OFFTARGET_PROVIDER_AUTO
    index_path = _settings_path(settings, settings.crispr_offtarget_index_path)
    try:
        inspection = inspect_crispr_offtarget_index(index_path)
    except Exception:
        inspection = None

    index_status = (
        inspection.to_sanitized_dict()
        if inspection is not None
        else {
            "source_id": "eamos_crispr_spcas9_offtarget_index",
            "ready": False,
            "status": "runtime_asset_probe_failed",
            "schema_version": None,
            "genome_build": None,
            "target_count": 0,
            "max_mismatches_supported": None,
            "actual_size_bytes": None,
            "request_time_supabase_search": False,
            "request_time_materialization_allowed": False,
            "startup_materialization_allowed": False,
            "reader_requires_local_path": True,
            "local_path_values_emitted": False,
        }
    )
    index_ready = bool(index_status["ready"])
    mock_fallback = configured_provider in {
        CRISPR_OFFTARGET_PROVIDER_AUTO,
        CRISPR_OFFTARGET_PROVIDER_MOCK,
    }
    available = (
        configured_provider == CRISPR_OFFTARGET_PROVIDER_MOCK
        or index_ready
        or (configured_provider == CRISPR_OFFTARGET_PROVIDER_AUTO and mock_fallback)
    )
    if configured_provider == CRISPR_OFFTARGET_PROVIDER_INDEXED_SQLITE:
        status = "indexed_ready" if index_ready else "unavailable"
    elif configured_provider == CRISPR_OFFTARGET_PROVIDER_MOCK:
        status = "mock_fixture"
    elif index_ready:
        status = "indexed_ready"
    else:
        status = "mock_fallback"

    return {
        "configured_provider": configured_provider,
        "available": available,
        "status": status,
        "indexed_sqlite": index_status,
        "mock_fallback_enabled": mock_fallback,
        "supabase_storage_object_uri_configured": bool(settings.crispr_offtarget_index_object_uri),
        "render_materialization_required": not index_ready
        and configured_provider != CRISPR_OFFTARGET_PROVIDER_MOCK,
        "request_time_supabase_search": False,
        "launch_gate": (
            None
            if index_ready or configured_provider == CRISPR_OFFTARGET_PROVIDER_MOCK
            else "crispr_offtarget_index_artifact_not_materialized"
        ),
    }


def _primer_specificity_health(settings) -> dict[str, object]:
    configured_provider = (settings.primer_specificity_provider or "").strip().lower()
    if not configured_provider:
        configured_provider = PRIMER_SPECIFICITY_TEMPLATE

    if configured_provider == PRIMER_SPECIFICITY_TEMPLATE:
        return {
            "configured_provider": configured_provider,
            "available": True,
            "status": "template_window",
            "whole_genome_specificity": False,
            "request_time_external_calls": False,
            "startup_download_allowed": False,
            "local_path_values_emitted": False,
        }

    if configured_provider == PRIMER_SPECIFICITY_UCSC_ISPCR:
        binary_present = _settings_path(settings, settings.ucsc_ispcr_binary_path).is_file()
        reference_present = _settings_path(settings, settings.ucsc_ispcr_hg38_path).is_file()
        available = bool(binary_present and reference_present)
        return {
            "configured_provider": configured_provider,
            "available": available,
            "status": "ucsc_ispcr_ready" if available else "ucsc_ispcr_unavailable",
            "whole_genome_specificity": available,
            "checks": {
                "binary_present": binary_present,
                "reference_present": reference_present,
                "min_perfect": settings.ucsc_ispcr_min_perfect,
                "min_good": settings.ucsc_ispcr_min_good,
            },
            "request_time_external_calls": False,
            "startup_download_allowed": False,
            "local_path_values_emitted": False,
            "launch_gate": None if available else "ucsc_ispcr_assets_not_materialized",
        }

    return {
        "configured_provider": configured_provider,
        "available": False,
        "status": "unknown_provider",
        "whole_genome_specificity": False,
        "request_time_external_calls": False,
        "startup_download_allowed": False,
        "local_path_values_emitted": False,
    }


def _settings_path(settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def _protein_annotation_health(settings, service) -> dict[str, object]:
    enabled = bool(settings.protein_annotation_enabled)
    uniprot_feature_index_ready = _settings_path(
        settings,
        settings.protein_annotation_uniprot_feature_index_path,
    ).is_file()
    result: dict[str, object] = {
        "enabled": enabled,
        "available": False,
        "status": "disabled" if not enabled else "unavailable",
        "cache_enabled": bool(getattr(service, "cache_repo", None) is not None),
        "uniprot_features_enabled": bool(settings.protein_annotation_uniprot_features_enabled),
        "uniprot_feature_index": {
            "configured": bool(settings.protein_annotation_uniprot_feature_index_path),
            "ready": uniprot_feature_index_ready,
        },
        "hmmer": {
            "ready": False,
            "reason": "protein_annotation_disabled" if not enabled else "runner_unconfigured",
            "missing_index_count": 0,
        },
    }
    if service is None:
        result["status"] = "service_unavailable"
        result["hmmer"] = {
            "ready": False,
            "reason": "service_unavailable",
            "missing_index_count": 0,
        }
        return result

    runner = getattr(service, "runner", None)
    if runner is None:
        return result
    try:
        runtime = runner.status()
    except Exception:
        result["hmmer"] = {
            "ready": False,
            "reason": "runtime_probe_failed",
            "missing_index_count": 0,
        }
        return result

    hmmer_available = bool(enabled and runtime.ready)
    uniprot_partial_available = bool(
        enabled
        and settings.protein_annotation_uniprot_features_enabled
        and uniprot_feature_index_ready
    )
    available = hmmer_available or uniprot_partial_available
    status = (
        "available"
        if hmmer_available
        else (
            "partial" if uniprot_partial_available else "disabled" if not enabled else "unavailable"
        )
    )
    result.update(
        {
            "available": available,
            "status": status,
            "hmmer": {
                "ready": bool(runtime.ready),
                "reason": runtime.reason,
                "missing_index_count": len(runtime.missing_indexes),
            },
        }
    )
    return result


def _crisprscore_r_health(settings, configured_provider: str) -> dict[str, object]:
    return inspect_crisprscore_r_runtime(
        configured_provider=configured_provider,
        rscript_path=settings.crispr_rscript_path,
        rule_set3_conda_env=settings.crispr_ruleset3_conda_env,
        lindel_conda_env=settings.crispr_lindel_conda_env,
    ).to_sanitized_dict()
