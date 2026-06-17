from __future__ import annotations

import json
from pathlib import Path

import httpx

from app.cli import eamos_tier2_predictor_artifact_upload
from app.core.config import Settings
from app.services.esm1b_assembly import ESM1B_REGENERATION_REQUIRED_GATE
from app.services.tier2_predictor_artifacts import (
    Tier2PredictorArtifactStatus,
    build_tier2_predictor_artifact_upload_items,
    execute_tier2_predictor_artifact_uploads,
)


def test_tier2_predictor_upload_plan_blocks_missing_artifact_sets_without_paths(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)

    items = build_tier2_predictor_artifact_upload_items(
        settings,
        manifest_staging_root=tmp_path / "manifests",
    )
    result = execute_tier2_predictor_artifact_uploads(items, upload=False)
    payload = result.to_sanitized_dict()

    assert result.planned_count == 0
    assert result.blocked_count == 9
    assert payload["status_counts"] == {"missing_local_file": 9}
    encoded = json.dumps(payload).lower()
    assert str(tmp_path).lower() not in encoded
    assert "service_role" not in encoded
    assert all(item["local_path_values_emitted"] is False for item in payload["items"])


def test_tier2_predictor_upload_plan_includes_complete_esm1b_components(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    _write_file(settings.esm1b_hg38_runtime_asset_path, b"esm1b scores")
    _write_file(Path(f"{settings.esm1b_hg38_runtime_asset_path}.tbi"), b"esm1b index")

    items = build_tier2_predictor_artifact_upload_items(
        settings,
        artifact_ids=("esm1b_hg38_scores",),
        bucket_id="eamos-source-assets",
        manifest_staging_root=tmp_path / "manifests",
    )
    result = execute_tier2_predictor_artifact_uploads(items, upload=False)
    by_component = {item.component_id: item for item in result.items}

    assert result.planned_count == 2
    assert result.blocked_count == 0
    assert by_component["score_cache"].status is Tier2PredictorArtifactStatus.PLANNED
    assert by_component["score_cache_index"].status is Tier2PredictorArtifactStatus.PLANNED
    assert by_component["score_cache"].source_id == "esm1b_hg38_assembled_scores"
    assert by_component["score_cache"].object_path.startswith(
        "predictors/esm1b_hg38_assembled_scores/esm1b_hg38_tsv_gz/sha256-"
    )
    assert by_component["score_cache"].manifest_path is not None
    manifest = json.loads(by_component["score_cache"].manifest_path.read_text(encoding="utf-8"))
    assert manifest["tier"] == "tier_2_predictor_cache"
    assert manifest["launch_gate"] == ESM1B_REGENERATION_REQUIRED_GATE
    assert manifest["storage_contract"]["frontend_direct_access_allowed"] is False


def test_tier2_predictor_upload_plan_honors_clean_esm1b_runtime_manifest(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    _write_file(settings.esm1b_hg38_runtime_asset_path, b"esm1b scores")
    _write_file(Path(f"{settings.esm1b_hg38_runtime_asset_path}.tbi"), b"esm1b index")
    settings.esm1b_hg38_runtime_asset_path.with_suffix(
        settings.esm1b_hg38_runtime_asset_path.suffix + ".manifest.json"
    ).write_text(
        '{"license_gate": null, "score_generation_method": "mit_model_regeneration"}',
        encoding="utf-8",
    )

    items = build_tier2_predictor_artifact_upload_items(
        settings,
        artifact_ids=("esm1b_hg38_scores",),
        bucket_id="eamos-source-assets",
        manifest_staging_root=tmp_path / "manifests",
    )
    result = execute_tier2_predictor_artifact_uploads(items, upload=False)
    by_component = {item.component_id: item for item in result.items}

    assert result.planned_count == 2
    assert by_component["score_cache"].launch_gate is None
    assert by_component["score_cache_index"].launch_gate is None
    manifest = json.loads(by_component["score_cache"].manifest_path.read_text(encoding="utf-8"))
    assert manifest["launch_gate"] is None


def test_tier2_predictor_upload_blocks_partial_ci_spliceai_set(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    _write_file(settings.ci_spliceai_model_path, b"model")
    _write_file(settings.ci_spliceai_reference_path, b"{}")
    _write_file(settings.ci_spliceai_score_cache_path, b"scores")

    items = build_tier2_predictor_artifact_upload_items(
        settings,
        artifact_ids=("ci_spliceai",),
        manifest_staging_root=tmp_path / "manifests",
    )
    result = execute_tier2_predictor_artifact_uploads(items, upload=False)
    by_component = {item.component_id: item for item in result.items}

    assert result.planned_count == 0
    assert by_component["score_cache_index"].status is (
        Tier2PredictorArtifactStatus.MISSING_LOCAL_FILE
    )
    assert by_component["model"].status is (
        Tier2PredictorArtifactStatus.BLOCKED_INCOMPLETE_ARTIFACT_SET
    )
    assert by_component["reference_bundle"].status is (
        Tier2PredictorArtifactStatus.BLOCKED_INCOMPLETE_ARTIFACT_SET
    )
    assert "score_cache_index" in (by_component["model"].message or "")


def test_tier2_predictor_upload_posts_complete_capice_set(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    _write_file(settings.capice_model_path, b"{}")
    _write_file(settings.capice_feature_cache_path, b"features")
    _write_file(Path(f"{settings.capice_feature_cache_path}.tbi"), b"index")
    items = build_tier2_predictor_artifact_upload_items(
        settings,
        artifact_ids=("capice",),
        manifest_staging_root=tmp_path / "manifests",
    )
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"Key": "ok"})

    result = execute_tier2_predictor_artifact_uploads(
        items,
        upload=True,
        supabase_url="https://project.supabase.co",
        service_role_key="service-role-secret",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.uploaded_count == 3
    assert result.blocked_count == 0
    assert {item.status for item in result.items} == {Tier2PredictorArtifactStatus.UPLOADED}
    assert len(requests) == 6
    assert all(
        request.headers["authorization"] == "Bearer service-role-secret" for request in requests
    )
    encoded = json.dumps(result.to_sanitized_dict()).lower()
    assert str(tmp_path).lower() not in encoded
    assert "service-role-secret" not in encoded


def test_tier2_predictor_upload_cli_plans_without_paths(capsys) -> None:
    exit_code = eamos_tier2_predictor_artifact_upload.main(["--artifact", "capice", "--compact"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "eamos_tier2_predictor_artifact_upload"
    assert output["upload_performed"] is False
    assert output["guardrails"]["supabase_metadata_mutation"] == "not_used"
    assert output["guardrails"]["complete_artifact_set_required"] is True
    encoded = json.dumps(output).lower()
    assert "service_role" not in encoded
    assert "app/backend/data" not in encoded


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        jwt_secret="test-secret",
        esm1b_hg38_runtime_asset_path=tmp_path / "esm1b" / "esm1b_hg38.tsv.gz",
        ci_spliceai_model_path=tmp_path / "ci_spliceai" / "ci_spliceai.keras",
        ci_spliceai_reference_path=tmp_path / "ci_spliceai" / "hg38_reference.json",
        ci_spliceai_score_cache_path=(tmp_path / "ci_spliceai" / "ci_spliceai_hg38_scores.vcf.gz"),
        capice_model_path=tmp_path / "capice" / "capice_model.json",
        capice_feature_cache_path=tmp_path / "capice" / "capice_hg38_features.tsv.gz",
    )


def _write_file(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
