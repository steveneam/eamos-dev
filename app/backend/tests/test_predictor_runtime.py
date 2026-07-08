from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import md5, sha256
import json
from pathlib import Path

from app.core.config import Settings
from app.data_sources import (
    DEFAULT_SOURCE_RECORDS,
    DataSourceRegistry,
    SourceAssetMaterializationRecord,
)
from app.services.esm1b_assembly import (
    ESM1B_LICENSE_GATE,
    ESM1B_REGENERATION_REQUIRED_GATE,
)
from app.services.predictor_runtime import (
    ALPHAMISSENSE_ASSET_ROLE,
    ALPHAMISSENSE_SOURCE_ID,
    CAPICE_FEATURE_CACHE_ASSET_ROLE,
    CAPICE_FEATURE_CACHE_SOURCE_ID,
    CAPICE_LAUNCH_GATE,
    CAPICE_MODEL_ASSET_ROLE,
    CAPICE_SOURCE_ID,
    CI_SPLICEAI_LAUNCH_GATE,
    CI_SPLICEAI_MODEL_ASSET_ROLE,
    CI_SPLICEAI_REFERENCE_ASSET_ROLE,
    CI_SPLICEAI_SCORE_CACHE_ASSET_ROLE,
    CI_SPLICEAI_SOURCE_ID,
    ESM1B_ASSET_ROLE,
    ESM1B_SOURCE_ID,
    GPN_MSA_SOURCE_ID,
    PANGOLIN_SOURCE_ID,
    PRIMATEAI3D_LAUNCH_GATE,
    PRIMATEAI3D_SCORE_CACHE_ASSET_ROLE,
    PRIMATEAI3D_SOURCE_ID,
    PredictorRuntimeStatus,
    REVEL_LAUNCH_GATE,
    REVEL_SCORE_CACHE_ASSET_ROLE,
    REVEL_SOURCE_ID,
    build_alphamissense_runtime_plan,
    build_esm1b_runtime_plan,
    inspect_alphamissense_runtime_asset,
    inspect_capice_runtime_assets,
    inspect_ci_spliceai_runtime_assets,
    inspect_esm1b_runtime_asset,
    inspect_gpn_msa_runtime_assets,
    inspect_pangolin_runtime_assets,
    inspect_primateai3d_runtime_assets,
    inspect_revel_runtime_assets,
)


def test_alphamissense_runtime_plan_records_source_md5_and_bucket_limit() -> None:
    settings = Settings(jwt_secret="test-secret")

    plan = build_alphamissense_runtime_plan(settings, bucket_file_size_limit=1234)

    assert plan.source_id == ALPHAMISSENSE_SOURCE_ID
    assert plan.asset_role == ALPHAMISSENSE_ASSET_ROLE
    assert plan.path == (
        settings.backend_root
        / "data"
        / "bio_assets"
        / "predictors"
        / "alphamissense"
        / "AlphaMissense_hg38.tsv.gz"
    )
    assert plan.index_path == Path(f"{plan.path}.tbi")
    assert plan.manifest_path.name == "AlphaMissense_hg38.tsv.gz.manifest.json"
    assert plan.expected_md5 == "9fd167735f16a1b87da6eb3e4c25fcb5"
    assert plan.bucket_file_size_limit == 1234
    assert plan.reader_requires_local_path is True


def test_esm1b_runtime_plan_is_gated_indexed_predictor_asset() -> None:
    settings = Settings(jwt_secret="test-secret")

    plan = build_esm1b_runtime_plan(settings)

    assert plan.source_id == ESM1B_SOURCE_ID
    assert plan.asset_role == ESM1B_ASSET_ROLE
    assert plan.path == (
        settings.backend_root / "data" / "bio_assets" / "predictors" / "esm1b" / "esm1b_hg38.tsv.gz"
    )
    assert plan.index_path == Path(f"{plan.path}.tbi")
    assert plan.manifest_path.name == "esm1b_hg38.tsv.gz.manifest.json"
    assert plan.expected_md5 is None
    assert plan.reader_requires_local_path is True


def test_free_planned_predictors_report_precise_not_ready_statuses() -> None:
    settings = Settings(jwt_secret="test-secret")

    gpn_msa = inspect_gpn_msa_runtime_assets(settings)
    pangolin = inspect_pangolin_runtime_assets(settings)

    assert gpn_msa.source_id == GPN_MSA_SOURCE_ID
    assert gpn_msa.status == "remote_range_reader_planned"
    assert gpn_msa.available is False
    assert gpn_msa.runtime_wired is False
    assert gpn_msa.public_serialization_allowed is False
    assert "byte_range_reader_proof_required" in gpn_msa.status_notes
    assert gpn_msa.components == ()

    assert pangolin.source_id == PANGOLIN_SOURCE_ID
    assert pangolin.status == "source_decision_required"
    assert pangolin.available is False
    assert pangolin.runtime_wired is False
    assert pangolin.public_serialization_allowed is False
    assert "source_and_terms_review_required" in pangolin.status_notes
    assert pangolin.components == ()


def test_alphamissense_preflight_reports_missing_file(tmp_path: Path) -> None:
    settings = Settings(
        jwt_secret="test-secret",
        alphamissense_hg38_runtime_asset_path=tmp_path / "missing.tsv.gz",
    )

    inspection = inspect_alphamissense_runtime_asset(settings)

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.MISSING_SOURCE_FILE
    assert inspection.actual_size_bytes is None


def test_esm1b_preflight_reports_missing_file(tmp_path: Path) -> None:
    settings = Settings(
        jwt_secret="test-secret",
        esm1b_hg38_runtime_asset_path=tmp_path / "missing.tsv.gz",
    )

    inspection = inspect_esm1b_runtime_asset(settings)

    assert inspection.source_id == ESM1B_SOURCE_ID
    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.MISSING_SOURCE_FILE
    assert inspection.actual_size_bytes is None
    assert inspection.launch_gate == ESM1B_REGENERATION_REQUIRED_GATE


def test_ci_spliceai_runtime_reports_missing_artifacts(tmp_path: Path) -> None:
    settings = Settings(
        jwt_secret="test-secret",
        ci_spliceai_model_path=tmp_path / "missing-model.keras",
        ci_spliceai_reference_path=tmp_path / "missing-reference.json",
        ci_spliceai_score_cache_path=tmp_path / "missing-score-cache.vcf.gz",
    )

    inspection = inspect_ci_spliceai_runtime_assets(settings)

    assert inspection.source_id == CI_SPLICEAI_SOURCE_ID
    assert inspection.available is False
    assert inspection.status == "score_cache_missing"
    assert inspection.launch_gate == CI_SPLICEAI_LAUNCH_GATE
    assert inspection.status_notes == (
        "model_reference_materialization_required",
        "score_cache_materialization_required",
    )
    components = {component.asset_role: component for component in inspection.components}
    assert components[CI_SPLICEAI_MODEL_ASSET_ROLE].status == "model_artifact_missing"
    assert components[CI_SPLICEAI_REFERENCE_ASSET_ROLE].status == "reference_artifact_missing"
    assert components[CI_SPLICEAI_SCORE_CACHE_ASSET_ROLE].status == "score_cache_missing"


def test_ci_spliceai_runtime_reports_ready_when_all_artifacts_exist(tmp_path: Path) -> None:
    model = _write_plain_file(tmp_path / "ci_spliceai.keras", b"model")
    reference = _write_plain_file(tmp_path / "hg38_reference.json", b"reference")
    score_cache = _write_indexed_cache(tmp_path / "ci_spliceai_hg38_scores.vcf.gz", b"scores")
    _write_admin_manifest(
        model,
        artifact_id="ci_spliceai",
        component_id="model",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_keras_model",
        role=CI_SPLICEAI_MODEL_ASSET_ROLE,
        launch_gate=CI_SPLICEAI_LAUNCH_GATE,
    )
    _write_admin_manifest(
        reference,
        artifact_id="ci_spliceai",
        component_id="reference_bundle",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_reference_bundle",
        role=CI_SPLICEAI_REFERENCE_ASSET_ROLE,
        launch_gate=CI_SPLICEAI_LAUNCH_GATE,
    )
    _write_admin_manifest(
        score_cache,
        artifact_id="ci_spliceai",
        component_id="score_cache",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_hg38_score_cache_vcf_gz",
        role=CI_SPLICEAI_SCORE_CACHE_ASSET_ROLE,
        launch_gate=CI_SPLICEAI_LAUNCH_GATE,
    )
    settings = Settings(
        jwt_secret="test-secret",
        ci_spliceai_model_path=model,
        ci_spliceai_reference_path=reference,
        ci_spliceai_score_cache_path=score_cache,
    )

    inspection = inspect_ci_spliceai_runtime_assets(settings)
    sanitized = inspection.to_sanitized_dict()

    assert inspection.available is True
    assert inspection.status == "ready"
    assert inspection.status_notes == ()
    assert sanitized["status"] == "ready"
    assert str(tmp_path).lower() not in str(sanitized).lower()
    assert all(component.manifest_status == "ready" for component in inspection.components)


def test_ci_spliceai_runtime_rejects_bare_files_without_manifests(
    tmp_path: Path,
) -> None:
    model = _write_plain_file(tmp_path / "ci_spliceai.keras", b"model")
    reference = _write_plain_file(tmp_path / "hg38_reference.json", b"reference")
    score_cache = _write_indexed_cache(tmp_path / "ci_spliceai_hg38_scores.vcf.gz", b"scores")
    settings = Settings(
        jwt_secret="test-secret",
        ci_spliceai_model_path=model,
        ci_spliceai_reference_path=reference,
        ci_spliceai_score_cache_path=score_cache,
    )

    inspection = inspect_ci_spliceai_runtime_assets(settings)
    components = {component.asset_role: component for component in inspection.components}

    assert inspection.available is False
    assert inspection.status == "score_cache_manifest_missing"
    assert components[CI_SPLICEAI_MODEL_ASSET_ROLE].status == "model_manifest_missing"
    assert components[CI_SPLICEAI_REFERENCE_ASSET_ROLE].status == "reference_manifest_missing"
    assert components[CI_SPLICEAI_SCORE_CACHE_ASSET_ROLE].status == "score_cache_manifest_missing"


def test_capice_runtime_reports_missing_model_and_feature_cache(tmp_path: Path) -> None:
    settings = Settings(
        jwt_secret="test-secret",
        capice_model_path=tmp_path / "missing-capice-model.json",
        capice_feature_cache_path=tmp_path / "missing-capice-features.tsv.gz",
    )

    inspection = inspect_capice_runtime_assets(settings)

    assert inspection.source_id == CAPICE_SOURCE_ID
    assert inspection.available is False
    assert inspection.status == "model_artifact_missing"
    assert inspection.launch_gate == CAPICE_LAUNCH_GATE
    assert inspection.status_notes == (
        "capice_model_materialization_required",
        "spliceai_feature_cache_materialization_required",
    )
    components = {component.asset_role: component for component in inspection.components}
    assert components[CAPICE_MODEL_ASSET_ROLE].status == "model_artifact_missing"
    assert components[CAPICE_FEATURE_CACHE_ASSET_ROLE].source_id == CAPICE_FEATURE_CACHE_SOURCE_ID
    assert components[CAPICE_FEATURE_CACHE_ASSET_ROLE].status == "feature_cache_missing"


def test_capice_runtime_reports_ready_when_model_and_feature_cache_exist(
    tmp_path: Path,
) -> None:
    model = _write_plain_file(tmp_path / "capice_model.json", b"model")
    feature_cache = _write_indexed_cache(tmp_path / "capice_hg38_features.tsv.gz", b"features")
    _write_admin_manifest(
        model,
        artifact_id="capice",
        component_id="model",
        source_id=CAPICE_SOURCE_ID,
        asset_id="capice_xgboost_model",
        role=CAPICE_MODEL_ASSET_ROLE,
        launch_gate=CAPICE_LAUNCH_GATE,
    )
    _write_admin_manifest(
        feature_cache,
        artifact_id="capice",
        component_id="feature_cache",
        source_id=CAPICE_FEATURE_CACHE_SOURCE_ID,
        asset_id="capice_hg38_feature_cache_tsv_gz",
        role=CAPICE_FEATURE_CACHE_ASSET_ROLE,
        launch_gate=CAPICE_LAUNCH_GATE,
    )
    settings = Settings(
        jwt_secret="test-secret",
        capice_model_path=model,
        capice_feature_cache_path=feature_cache,
    )

    inspection = inspect_capice_runtime_assets(settings)
    sanitized = inspection.to_sanitized_dict()

    assert inspection.available is True
    assert inspection.status == "ready"
    assert inspection.status_notes == ()
    assert sanitized["status"] == "ready"
    assert str(tmp_path).lower() not in str(sanitized).lower()
    assert all(component.manifest_status == "ready" for component in inspection.components)


def test_capice_runtime_rejects_bare_files_without_manifests(
    tmp_path: Path,
) -> None:
    model = _write_plain_file(tmp_path / "capice_model.json", b"model")
    feature_cache = _write_indexed_cache(tmp_path / "capice_hg38_features.tsv.gz", b"features")
    settings = Settings(
        jwt_secret="test-secret",
        capice_model_path=model,
        capice_feature_cache_path=feature_cache,
    )

    inspection = inspect_capice_runtime_assets(settings)
    components = {component.asset_role: component for component in inspection.components}

    assert inspection.available is False
    assert inspection.status == "model_manifest_missing"
    assert components[CAPICE_MODEL_ASSET_ROLE].status == "model_manifest_missing"
    assert components[CAPICE_FEATURE_CACHE_ASSET_ROLE].status == "feature_cache_manifest_missing"


def test_revel_runtime_reports_missing_score_cache(tmp_path: Path) -> None:
    settings = Settings(
        jwt_secret="test-secret",
        revel_score_cache_path=tmp_path / "missing-revel.tsv.gz",
    )

    inspection = inspect_revel_runtime_assets(settings)

    assert inspection.source_id == REVEL_SOURCE_ID
    assert inspection.available is False
    assert inspection.status == "score_cache_missing"
    assert inspection.launch_gate == REVEL_LAUNCH_GATE
    assert inspection.status_notes == ("score_cache_materialization_required",)
    assert inspection.components[0].asset_role == REVEL_SCORE_CACHE_ASSET_ROLE


def test_revel_runtime_reports_ready_when_score_cache_exists(tmp_path: Path) -> None:
    score_cache = _write_indexed_cache(tmp_path / "revel_hg38_scores.tsv.gz", b"scores")
    _write_admin_manifest(
        score_cache,
        artifact_id="revel",
        component_id="score_cache",
        source_id=REVEL_SOURCE_ID,
        asset_id="revel_hg38_score_cache_tsv_gz",
        role=REVEL_SCORE_CACHE_ASSET_ROLE,
        launch_gate=REVEL_LAUNCH_GATE,
    )
    settings = Settings(jwt_secret="test-secret", revel_score_cache_path=score_cache)

    inspection = inspect_revel_runtime_assets(settings)
    sanitized = inspection.to_sanitized_dict()

    assert inspection.available is True
    assert inspection.status == "ready"
    assert inspection.status_notes == ()
    assert sanitized["status"] == "ready"
    assert str(tmp_path).lower() not in str(sanitized).lower()
    assert inspection.components[0].manifest_status == "ready"


def test_primateai3d_runtime_reports_missing_score_cache(tmp_path: Path) -> None:
    settings = Settings(
        jwt_secret="test-secret",
        primateai3d_score_cache_path=tmp_path / "missing-primateai3d.tsv.gz",
    )

    inspection = inspect_primateai3d_runtime_assets(settings)

    assert inspection.source_id == PRIMATEAI3D_SOURCE_ID
    assert inspection.available is False
    assert inspection.status == "score_cache_missing"
    assert inspection.launch_gate == PRIMATEAI3D_LAUNCH_GATE
    assert inspection.status_notes == ("score_cache_materialization_required",)
    assert inspection.components[0].asset_role == PRIMATEAI3D_SCORE_CACHE_ASSET_ROLE


def test_primateai3d_runtime_reports_ready_when_score_cache_exists(tmp_path: Path) -> None:
    score_cache = _write_indexed_cache(
        tmp_path / "primateai3d_hg38_scores.tsv.gz",
        b"scores",
    )
    _write_admin_manifest(
        score_cache,
        artifact_id="primateai3d",
        component_id="score_cache",
        source_id=PRIMATEAI3D_SOURCE_ID,
        asset_id="primateai3d_hg38_score_cache_tsv_gz",
        role=PRIMATEAI3D_SCORE_CACHE_ASSET_ROLE,
        launch_gate=PRIMATEAI3D_LAUNCH_GATE,
    )
    settings = Settings(jwt_secret="test-secret", primateai3d_score_cache_path=score_cache)

    inspection = inspect_primateai3d_runtime_assets(settings)
    sanitized = inspection.to_sanitized_dict()

    assert inspection.available is True
    assert inspection.status == "ready"
    assert inspection.status_notes == ()
    assert sanitized["status"] == "ready"
    assert str(tmp_path).lower() not in str(sanitized).lower()
    assert inspection.components[0].manifest_status == "ready"


def test_alphamissense_preflight_reports_missing_index_before_manifest(
    tmp_path: Path,
) -> None:
    asset = tmp_path / "AlphaMissense_hg38.tsv.gz"
    asset.write_bytes(b"tiny")
    settings = Settings(jwt_secret="test-secret", alphamissense_hg38_runtime_asset_path=asset)

    inspection = inspect_alphamissense_runtime_asset(settings)

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.MISSING_INDEX
    assert inspection.actual_size_bytes == len(b"tiny")


def test_alphamissense_preflight_reports_missing_manifest(tmp_path: Path) -> None:
    asset = tmp_path / "AlphaMissense_hg38.tsv.gz"
    asset.write_bytes(b"tiny")
    Path(f"{asset}.tbi").write_bytes(b"index")
    settings = Settings(jwt_secret="test-secret", alphamissense_hg38_runtime_asset_path=asset)

    inspection = inspect_alphamissense_runtime_asset(settings)

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.MISSING_MANIFEST


def test_alphamissense_preflight_reports_ready_and_checksum_match(
    tmp_path: Path,
) -> None:
    payload = b"tiny-alphamissense"
    asset = _write_materialized_asset(tmp_path, payload)
    settings = Settings(jwt_secret="test-secret", alphamissense_hg38_runtime_asset_path=asset)

    inspection = inspect_alphamissense_runtime_asset(
        settings,
        registry=_tiny_registry(payload),
        verify_checksum=True,
    )

    assert inspection.ready is True
    assert inspection.status is PredictorRuntimeStatus.READY
    assert inspection.actual_size_bytes == len(payload)
    assert inspection.actual_md5 == _md5(payload)


def test_alphamissense_preflight_reports_checksum_mismatch(tmp_path: Path) -> None:
    payload = b"tiny-alphamissense"
    asset = _write_materialized_asset(tmp_path, payload)
    settings = Settings(jwt_secret="test-secret", alphamissense_hg38_runtime_asset_path=asset)

    inspection = inspect_alphamissense_runtime_asset(
        settings,
        registry=_tiny_registry(payload, expected_md5="0" * 32),
        verify_checksum=True,
    )

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.CHECKSUM_MISMATCH
    assert inspection.actual_md5 == _md5(payload)


def test_alphamissense_object_mode_requires_materialization_metadata(
    tmp_path: Path,
) -> None:
    payload = b"tiny-alphamissense"
    asset = _write_materialized_asset(tmp_path, payload)
    settings = Settings(
        jwt_secret="test-secret",
        alphamissense_hg38_runtime_asset_mode="object_storage_local_cache",
        alphamissense_hg38_runtime_asset_path=asset,
        alphamissense_hg38_runtime_asset_object_uri=(
            "supabase://eamos-source-assets/google_deepmind_alphamissense_hg38/"
            "md5-test/AlphaMissense_hg38.tsv.gz"
        ),
    )

    inspection = inspect_alphamissense_runtime_asset(
        settings,
        registry=_tiny_registry(payload),
    )

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.MATERIALIZATION_STORE_UNAVAILABLE
    assert inspection.materialization_status == "metadata_store_unavailable"


def test_alphamissense_materialization_read_failure_degrades_to_not_ready(
    tmp_path: Path,
) -> None:
    payload = b"tiny-alphamissense"
    asset = _write_materialized_asset(tmp_path, payload)
    object_path = "google_deepmind_alphamissense_hg38/md5-test/AlphaMissense_hg38.tsv.gz"
    settings = Settings(
        jwt_secret="test-secret",
        alphamissense_hg38_runtime_asset_path=asset,
        alphamissense_hg38_runtime_asset_object_uri=f"supabase://eamos-source-assets/{object_path}",
    )

    inspection = inspect_alphamissense_runtime_asset(
        settings,
        registry=_tiny_registry(payload),
        materialization_store=ExplodingMaterializationStore(),
    )

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.MATERIALIZATION_STORE_UNAVAILABLE
    assert inspection.materialization_status == "materialization_metadata_unavailable"
    encoded = str(inspection).lower()
    assert "private.example" not in encoded
    assert "postgresql://" not in encoded


def test_alphamissense_materialization_rejects_public_metadata(
    tmp_path: Path,
) -> None:
    payload = b"tiny-alphamissense"
    asset = _write_materialized_asset(tmp_path, payload)
    object_path = "google_deepmind_alphamissense_hg38/md5-test/AlphaMissense_hg38.tsv.gz"
    settings = Settings(
        jwt_secret="test-secret",
        alphamissense_hg38_runtime_asset_path=asset,
        alphamissense_hg38_runtime_asset_object_uri=f"supabase://eamos-source-assets/{object_path}",
    )
    record = replace(
        _materialization_record(payload, asset, object_path),
        public_access_allowed=True,
    )

    inspection = inspect_alphamissense_runtime_asset(
        settings,
        registry=_tiny_registry(payload),
        materialization_store=FakeMaterializationStore(record),
    )

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.MATERIALIZATION_PUBLIC_ACCESS_BLOCKED
    assert inspection.materialization_status == "materialization_public_access_blocked"


def test_alphamissense_materialization_rejects_size_mismatch(
    tmp_path: Path,
) -> None:
    payload = b"tiny-alphamissense"
    asset = _write_materialized_asset(tmp_path, payload)
    object_path = "google_deepmind_alphamissense_hg38/md5-test/AlphaMissense_hg38.tsv.gz"
    settings = Settings(
        jwt_secret="test-secret",
        alphamissense_hg38_runtime_asset_path=asset,
        alphamissense_hg38_runtime_asset_object_uri=f"supabase://eamos-source-assets/{object_path}",
    )
    record = replace(
        _materialization_record(payload, asset, object_path),
        byte_size=len(payload) + 1,
    )

    inspection = inspect_alphamissense_runtime_asset(
        settings,
        registry=_tiny_registry(payload),
        materialization_store=FakeMaterializationStore(record),
    )

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.MATERIALIZATION_SIZE_MISMATCH
    assert inspection.materialization_status == "materialization_size_mismatch"


def test_alphamissense_materialization_reports_ready_without_sensitive_checksum(
    tmp_path: Path,
) -> None:
    payload = b"tiny-alphamissense"
    asset = _write_materialized_asset(tmp_path, payload)
    object_path = "google_deepmind_alphamissense_hg38/md5-test/AlphaMissense_hg38.tsv.gz"
    settings = Settings(
        jwt_secret="test-secret",
        alphamissense_hg38_runtime_asset_path=asset,
        alphamissense_hg38_runtime_asset_object_uri=f"supabase://eamos-source-assets/{object_path}",
    )

    inspection = inspect_alphamissense_runtime_asset(
        settings,
        registry=_tiny_registry(payload),
        materialization_store=FakeMaterializationStore(
            _materialization_record(payload, asset, object_path)
        ),
        verify_checksum=True,
    )

    assert inspection.ready is True
    assert inspection.status is PredictorRuntimeStatus.READY
    assert inspection.materialization_status == "ready"
    assert inspection.bucket_file_size_limit == 50 * 1024 * 1024 * 1024


def test_esm1b_materialization_reports_ready_without_requiring_expected_registry_md5(
    tmp_path: Path,
) -> None:
    payload = b"tiny-esm1b"
    asset = _write_materialized_asset(
        tmp_path,
        payload,
        file_name="esm1b_hg38.tsv.gz",
    )
    object_path = "esm1b_hg38_assembled_scores/md5-test/esm1b_hg38.tsv.gz"
    settings = Settings(
        jwt_secret="test-secret",
        esm1b_hg38_runtime_asset_path=asset,
        esm1b_hg38_runtime_asset_object_uri=f"supabase://eamos-source-assets/{object_path}",
    )

    inspection = inspect_esm1b_runtime_asset(
        settings,
        materialization_store=FakeMaterializationStore(
            _materialization_record(
                payload,
                asset,
                object_path,
                source_id=ESM1B_SOURCE_ID,
                asset_role=ESM1B_ASSET_ROLE,
            )
        ),
        verify_checksum=True,
    )

    assert inspection.ready is True
    assert inspection.status is PredictorRuntimeStatus.READY
    assert inspection.actual_md5 == _md5(payload)
    assert inspection.materialization_status == "ready"
    assert inspection.bucket_file_size_limit == 50 * 1024 * 1024 * 1024
    assert inspection.launch_gate == ESM1B_LICENSE_GATE


def test_esm1b_materialization_reads_clean_regenerated_manifest_launch_gate(
    tmp_path: Path,
) -> None:
    payload = b"tiny-esm1b"
    asset = _write_materialized_asset(
        tmp_path,
        payload,
        file_name="esm1b_hg38.tsv.gz",
        manifest_extra={
            "license_gate": None,
            "score_generation_method": "mit_model_regeneration",
            "model_source_license": "MIT",
        },
    )
    settings = Settings(jwt_secret="test-secret", esm1b_hg38_runtime_asset_path=asset)

    inspection = inspect_esm1b_runtime_asset(settings)

    assert inspection.ready is True
    assert inspection.status is PredictorRuntimeStatus.READY
    assert inspection.launch_gate is None


def test_esm1b_materialization_rejects_public_metadata(
    tmp_path: Path,
) -> None:
    payload = b"tiny-esm1b"
    asset = _write_materialized_asset(
        tmp_path,
        payload,
        file_name="esm1b_hg38.tsv.gz",
    )
    object_path = "esm1b_hg38_assembled_scores/md5-test/esm1b_hg38.tsv.gz"
    settings = Settings(
        jwt_secret="test-secret",
        esm1b_hg38_runtime_asset_path=asset,
        esm1b_hg38_runtime_asset_object_uri=f"supabase://eamos-source-assets/{object_path}",
    )
    record = replace(
        _materialization_record(
            payload,
            asset,
            object_path,
            source_id=ESM1B_SOURCE_ID,
            asset_role=ESM1B_ASSET_ROLE,
        ),
        frontend_direct_access_allowed=True,
    )

    inspection = inspect_esm1b_runtime_asset(
        settings,
        materialization_store=FakeMaterializationStore(record),
    )

    assert inspection.ready is False
    assert inspection.status is PredictorRuntimeStatus.MATERIALIZATION_PUBLIC_ACCESS_BLOCKED
    assert inspection.materialization_status == "materialization_public_access_blocked"


def test_alphamissense_materialization_filters_runtime_local_cache_path(
    tmp_path: Path,
) -> None:
    payload = b"tiny-alphamissense"
    stale_asset = _write_materialized_asset(tmp_path / "old", payload)
    asset = _write_materialized_asset(tmp_path / "current", payload)
    object_path = "google_deepmind_alphamissense_hg38/md5-test/AlphaMissense_hg38.tsv.gz"
    settings = Settings(
        jwt_secret="test-secret",
        alphamissense_hg38_runtime_asset_path=asset,
        alphamissense_hg38_runtime_asset_object_uri=f"supabase://eamos-source-assets/{object_path}",
    )
    store = FakeMaterializationStore(
        _materialization_record(payload, stale_asset, object_path),
        _materialization_record(payload, asset, object_path),
    )

    inspection = inspect_alphamissense_runtime_asset(
        settings,
        registry=_tiny_registry(payload),
        materialization_store=store,
    )

    assert inspection.ready is True
    assert store.calls == [
        {
            "source_id": ALPHAMISSENSE_SOURCE_ID,
            "asset_role": ALPHAMISSENSE_ASSET_ROLE,
            "bucket_id": "eamos-source-assets",
            "object_path": object_path,
            "environment": None,
            "local_cache_path": str(asset),
        }
    ]


class FakeMaterializationStore:
    def __init__(self, *records: SourceAssetMaterializationRecord | None) -> None:
        self.records = tuple(record for record in records if record is not None)
        self.calls: list[dict[str, object]] = []

    def get_source_asset_materialization(self, **kwargs) -> SourceAssetMaterializationRecord | None:
        self.calls.append(dict(kwargs))
        for record in self.records:
            if record.source_id != kwargs.get("source_id"):
                continue
            if record.asset_role != kwargs.get("asset_role"):
                continue
            bucket_id = kwargs.get("bucket_id")
            if bucket_id is not None and record.bucket_id != bucket_id:
                continue
            object_path = kwargs.get("object_path")
            if object_path is not None and record.object_path != object_path:
                continue
            environment = kwargs.get("environment")
            if environment is not None and record.environment != environment:
                continue
            local_cache_path = kwargs.get("local_cache_path")
            if local_cache_path is not None and record.local_cache_path != local_cache_path:
                continue
            return record
        return None


class ExplodingMaterializationStore:
    def get_source_asset_materialization(self, **kwargs) -> SourceAssetMaterializationRecord:
        raise RuntimeError(
            "database unavailable at postgresql://postgres:secret@private.example/path"
        )


def _write_materialized_asset(
    tmp_path: Path,
    payload: bytes,
    *,
    file_name: str = "AlphaMissense_hg38.tsv.gz",
    manifest_extra: dict[str, object] | None = None,
) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    asset = tmp_path / file_name
    asset.write_bytes(payload)
    Path(f"{asset}.tbi").write_bytes(b"index")
    manifest = {"md5": _md5(payload), "sha256": "a" * 64}
    manifest.update(manifest_extra or {})
    asset.with_suffix(asset.suffix + ".manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    return asset


def _write_plain_file(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _write_indexed_cache(path: Path, payload: bytes) -> Path:
    _write_plain_file(path, payload)
    Path(f"{path}.tbi").write_bytes(b"index")
    return path


def _write_admin_manifest(
    path: Path,
    *,
    artifact_id: str,
    component_id: str,
    source_id: str,
    asset_id: str,
    role: str,
    launch_gate: str,
) -> None:
    payload = path.read_bytes()
    md5_value = _md5(payload)
    sha256_value = sha256(payload).hexdigest()
    path.with_suffix(path.suffix + ".manifest.json").write_text(
        json.dumps(
            {
                "artifact_id": artifact_id,
                "component_id": component_id,
                "source_id": source_id,
                "asset_id": asset_id,
                "role": role,
                "byte_size": len(payload),
                "md5": md5_value,
                "sha256": sha256_value,
                "checksums": {"md5": md5_value, "sha256": sha256_value},
                "launch_gate": launch_gate,
                "storage_contract": {
                    "bucket_policy": "private",
                    "frontend_direct_access_allowed": False,
                    "signed_urls_created": False,
                    "startup_download_allowed": False,
                    "request_time_materialization_allowed": False,
                    "runtime_sync_required": True,
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _tiny_registry(payload: bytes, *, expected_md5: str | None = None) -> DataSourceRegistry:
    checksum = expected_md5 or _md5(payload)
    return DataSourceRegistry(
        [
            (
                replace(
                    record,
                    checksum_plan=f"Verify Zenodo MD5 {checksum} for fixture",
                )
                if record.source_id == ALPHAMISSENSE_SOURCE_ID
                else record
            )
            for record in DEFAULT_SOURCE_RECORDS
        ]
    )


def _materialization_record(
    payload: bytes,
    asset_path: Path,
    object_path: str,
    *,
    source_id: str = ALPHAMISSENSE_SOURCE_ID,
    asset_role: str = ALPHAMISSENSE_ASSET_ROLE,
) -> SourceAssetMaterializationRecord:
    return SourceAssetMaterializationRecord(
        source_id=source_id,
        asset_role=asset_role,
        bucket_id="eamos-source-assets",
        object_path=object_path,
        upload_status="verified",
        approval_status="approved",
        public_access_allowed=False,
        frontend_direct_access_allowed=False,
        environment="dev-local",
        backend_runtime="render_backend",
        local_cache_path=str(asset_path),
        materialization_status="ready",
        byte_size=len(payload),
        checksum_algorithm="md5",
        checksum_value=_md5(payload),
        verified_at=datetime(2026, 6, 3, tzinfo=timezone.utc),
        fail_closed_reason=None,
        metadata={"fixture": True},
        warnings=[],
    )


def _md5(payload: bytes) -> str:
    return md5(payload).hexdigest()
