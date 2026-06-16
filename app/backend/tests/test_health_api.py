from __future__ import annotations

import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.services.build_ledger as build_ledger_module
from app.core.config import Settings
from app.data_sources.runtime_assets import SourceAssetMaterializationRecord
from app.main import create_app
from app.services.crispr_offtarget_index import build_spcas9_offtarget_index_from_sequences

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures"
COMPACT_INDEX_FIXTURE = FIXTURES_DIR / "coordinate_index" / "eamos_coordinate_index_tiny.jsonl"


def test_healthz_returns_mode_flags(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["llm_provider"] == "mock"
    assert body["use_real_apis"] is False


def test_provider_cache_health_returns_sanitized_empty_aggregates(client) -> None:
    response = client.get("/api/v1/health/provider-cache")
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["source_cache"] == {
        "enabled": True,
        "total_rows": 0,
        "fresh_rows": 0,
        "stale_rows": 0,
        "versioned_rows": 0,
        "oldest_fetched_at": None,
        "latest_fetched_at": None,
        "sources": {},
    }
    assert body["source_assets"]["hg38_2bit"]["materialization_metadata"] == {
        "enabled": False,
        "failure_boundaries": {
            "health_and_preflight_probe": "sanitized_status_no_exception",
            "lookup_sequence_context_runtime": "fail_open",
            "metadata_and_local_cache_resolution": "fail_closed",
        },
        "probe_performed": False,
        "ready": False,
        "status": "materialization_store_unavailable",
    }
    compact_index = body["source_assets"]["compact_coordinate_index"]
    assert compact_index["source_id"] == "eamos_compact_coordinate_index"
    assert compact_index["ready"] is False
    assert compact_index["status"] == "missing"
    assert compact_index["source_runtime_scan_allowed"] is False
    assert compact_index["startup_download_allowed"] is False
    pubmed_local = body["source_assets"]["pubmed_local"]
    assert pubmed_local["source_id"] == "eamos_pubmed_local"
    assert pubmed_local["ready"] is False
    assert pubmed_local["enabled"] is False
    assert pubmed_local["status"] == "db_missing"
    assert pubmed_local["startup_download_allowed"] is False
    assert pubmed_local["request_time_materialization_allowed"] is False
    assert pubmed_local["local_path_values_emitted"] is False
    assert pubmed_local["abstract_values_emitted"] is False
    clingen_local = body["source_assets"]["clingen_local"]
    assert clingen_local["source_id"] == "eamos_clingen_local"
    assert clingen_local["ready"] is False
    assert clingen_local["enabled"] is False
    assert clingen_local["status"] == "db_missing"
    assert clingen_local["startup_download_allowed"] is False
    assert clingen_local["request_time_materialization_allowed"] is False
    assert clingen_local["local_path_values_emitted"] is False
    assert clingen_local["raw_source_rows_emitted"] is False
    crispr = body["providers"]["crispr"]
    assert crispr["configured_provider"] == "local_deterministic"
    assert crispr["available"] is True
    assert crispr["providers"]["local_deterministic"]["available"] is True
    assert crispr["providers"]["crisprscore_r"]["status"] == "disabled"
    assert crispr["providers"]["crisprscore_r"]["local_path_values_emitted"] is False
    assert crispr["providers"]["crisprscore_r"]["score_families"]["ruleset1"]["available"] is False
    assert crispr["primer_specificity"]["configured_provider"] == "template"
    assert crispr["primer_specificity"]["status"] == "template_window"
    assert crispr["primer_specificity"]["whole_genome_specificity"] is False
    assert crispr["primer_specificity"]["local_path_values_emitted"] is False
    indexed = body["providers"]["indexed_predictors"]
    assert indexed["alphamissense"]["status"] == "missing_source_file"
    assert indexed["alphamissense"]["public_serialization_allowed"] is True
    assert indexed["esm1b"]["status"] == "missing_source_file"
    assert indexed["esm1b"]["public_serialization_allowed"] is True
    assert indexed["esm1b"]["launch_gate"] == "esm1b_score_file_terms_unconfirmed"
    assert indexed["ci_spliceai"]["status"] == "score_cache_missing"
    assert indexed["ci_spliceai"]["runtime_wired"] is True
    assert indexed["ci_spliceai"]["public_serialization_allowed"] is True
    assert indexed["ci_spliceai"]["launch_gate"] == "ci_spliceai_launch_filter_metadata"
    assert indexed["capice"]["status"] == "model_artifact_missing"
    assert indexed["capice"]["runtime_wired"] is True
    assert indexed["capice"]["public_serialization_allowed"] is True
    assert indexed["capice"]["launch_gate"] == "capice_launch_filter_metadata"
    assert indexed["pvs1_nmd"]["status"] == "pure_code_available"
    assert indexed["pvs1_nmd"]["source_id"] == "nmdetective_b_pvs1"
    assert indexed["pvs1_nmd"]["storage_required"] is False
    assert indexed["pvs1_nmd"]["status_notes"] == [
        "advisory_engine_only",
        "autopvs1_code_not_used",
    ]
    assert indexed["mavedb"]["status"] == "cc0_import_not_materialized"
    protein = body["providers"]["protein_annotation"]
    assert protein["enabled"] is False
    assert protein["available"] is False
    assert protein["status"] == "disabled"
    assert protein["cache_enabled"] is True
    assert protein["hmmer"]["ready"] is False
    assert "path" not in json.dumps(protein).lower()

    ledger = body["build_ledger"]
    assert ledger["mode"] == "backend_build_ledger"
    assert ledger["startup_downloads_allowed"] is False
    assert ledger["gff_runtime_scans_allowed"] is False
    assert ledger["render_disk_is_runtime_cache_only"] is True
    items = {item["item_id"]: item for item in ledger["items"]}
    required_items = {
        "alphamissense",
        "capice",
        "clingen_local_adapter",
        "clinical_source_tables",
        "coordinate_compact_index",
        "ci_spliceai",
        "esm1b",
        "gene_view",
        "nmdetective_pvs1",
        "protein_pfam",
    }
    assert required_items <= items.keys()
    assert items["alphamissense"]["status"] == "missing_source_file"
    assert items["alphamissense"]["runtime_wired"] is True
    assert items["alphamissense"]["public_serialization_allowed"] is True
    assert items["esm1b"]["runtime_wired"] is True
    assert items["esm1b"]["public_serialization_allowed"] is True
    assert items["esm1b"]["launch_gate"] == "esm1b_score_file_terms_unconfirmed"
    assert items["ci_spliceai"]["runtime_wired"] is True
    assert items["ci_spliceai"]["public_serialization_allowed"] is True
    assert items["ci_spliceai"]["launch_gate"] == "ci_spliceai_launch_filter_metadata"
    assert items["capice"]["runtime_wired"] is True
    assert items["capice"]["public_serialization_allowed"] is True
    assert items["capice"]["launch_gate"] == "capice_launch_filter_metadata"
    assert items["clingen_local_adapter"]["status"] == "local_adapter_disabled"
    assert items["clingen_local_adapter"]["runtime_wired"] is True
    assert items["clingen_local_adapter"]["public_serialization_allowed"] is True
    assert items["clingen_local_adapter"]["launch_gate"] == "clingen_local_materialization"
    assert items["alphamissense"]["durable_source"] == "supabase_private_storage"
    assert items["clinical_source_tables"]["durable_source"] == "supabase_postgres"
    assert items["clinical_source_tables"]["render_disk_role"] == "not_required"
    assert "mondo_disease_ontology" in items["clinical_source_tables"]["source_ids"]
    assert items["coordinate_compact_index"]["source_runtime_scan_allowed"] is False
    assert items["coordinate_compact_index"]["runtime_source"] == (
        "render_disk_compact_immutable_index"
    )
    assert items["coordinate_compact_index"]["runtime_wired"] is True
    assert items["gene_view"]["runtime_wired"] is True
    assert items["nmdetective_pvs1"]["status"] == "pure_code_available"
    assert items["nmdetective_pvs1"]["render_disk_role"] == "not_required"
    assert items["protein_pfam"]["runtime_source"] == "render_disk_hmmer_indexes"
    assert items["literature_engine"]["status"] == "local_adapter_disabled"
    assert items["literature_engine"]["runtime_wired"] is True
    assert items["literature_engine"]["blockers"] == ["pubmed_local_materialization"]
    encoded_ledger = json.dumps(ledger).lower()
    assert "supabase://" not in encoded_ledger
    assert "service_role" not in encoded_ledger


def test_provider_cache_health_reports_crispr_offtarget_index_ready_without_paths(
    tmp_path: Path,
) -> None:
    guide = "GAGTCCGAGCAGAAGAAGAT"
    index_path = tmp_path / "spcas9_offtargets.sqlite"
    build_spcas9_offtarget_index_from_sequences(
        [("1", f"{guide}AGG{'N' * 40}")],
        index_path,
        genome_build="GRCh38",
        source_version="pytest-mini",
    )
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        crispr_offtarget_provider="indexed_sqlite",
        crispr_offtarget_index_path=index_path,
        crispr_offtarget_index_object_uri=(
            "supabase://eamos-source-assets/crispr/spcas9_offtargets.sqlite"
        ),
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    off_target = response.json()["providers"]["crispr"]["off_target_screening"]
    assert off_target["configured_provider"] == "indexed_sqlite"
    assert off_target["available"] is True
    assert off_target["status"] == "indexed_ready"
    assert off_target["indexed_sqlite"]["ready"] is True
    assert off_target["indexed_sqlite"]["target_count"] == 1
    assert off_target["indexed_sqlite"]["max_mismatches_supported"] == 3
    assert off_target["supabase_storage_object_uri_configured"] is True
    assert off_target["render_materialization_required"] is False
    assert off_target["request_time_supabase_search"] is False
    encoded = json.dumps(response.json()).lower()
    assert str(tmp_path).lower() not in encoded
    assert "supabase://" not in encoded


def test_provider_cache_health_reports_crispr_offtarget_auto_missing_as_mock_fallback(
    tmp_path: Path,
) -> None:
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        crispr_offtarget_provider="auto",
        crispr_offtarget_index_path=tmp_path / "missing.sqlite",
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    off_target = response.json()["providers"]["crispr"]["off_target_screening"]
    assert off_target["configured_provider"] == "auto"
    assert off_target["available"] is True
    assert off_target["status"] == "mock_fallback"
    assert off_target["mock_fallback_enabled"] is True
    assert off_target["render_materialization_required"] is True
    assert off_target["request_time_supabase_search"] is False
    assert off_target["launch_gate"] == "crispr_offtarget_index_artifact_not_materialized"
    assert off_target["indexed_sqlite"]["ready"] is False
    encoded = json.dumps(response.json()).lower()
    assert str(tmp_path).lower() not in encoded


def test_provider_cache_health_reports_forced_crispr_offtarget_index_missing_as_unavailable(
    tmp_path: Path,
) -> None:
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        crispr_offtarget_provider="indexed_sqlite",
        crispr_offtarget_index_path=tmp_path / "missing.sqlite",
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    off_target = response.json()["providers"]["crispr"]["off_target_screening"]
    assert off_target["configured_provider"] == "indexed_sqlite"
    assert off_target["available"] is False
    assert off_target["status"] == "unavailable"
    assert off_target["mock_fallback_enabled"] is False
    assert off_target["render_materialization_required"] is True
    assert off_target["request_time_supabase_search"] is False
    assert off_target["launch_gate"] == "crispr_offtarget_index_artifact_not_materialized"
    assert off_target["indexed_sqlite"]["ready"] is False
    encoded = json.dumps(response.json()).lower()
    assert str(tmp_path).lower() not in encoded


def test_provider_cache_health_reports_compact_coordinate_index_ready_without_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_full_load(*_args, **_kwargs):
        raise AssertionError("provider-cache health must not full-load the compact index")

    monkeypatch.setattr("app.services.compact_coordinate_index._load_index", fail_full_load)
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        coordinate_resolver_compact_index_path=COMPACT_INDEX_FIXTURE,
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    body = response.json()
    compact_index = body["source_assets"]["compact_coordinate_index"]
    assert compact_index["ready"] is True
    assert compact_index["status"] == "ready"
    assert compact_index["schema_version"] == "eamos.coordinate_index.v1"
    assert compact_index["variant_count"] == 2
    assert compact_index["transcript_count"] == 2
    assert compact_index["checksum_verified"] is False
    assert compact_index["source_runtime_scan_allowed"] is False
    assert compact_index["startup_download_allowed"] is False
    ledger_items = {item["item_id"]: item for item in body["build_ledger"]["items"]}
    assert ledger_items["coordinate_compact_index"]["status"] == "ready"
    encoded = json.dumps(body).lower()
    assert str(COMPACT_INDEX_FIXTURE).lower() not in encoded
    assert "eamos-coordinate-index" not in encoded


def test_build_ledger_marks_gene_view_ready_when_runtime_dependencies_are_ready(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
    )

    monkeypatch.setattr(
        build_ledger_module,
        "inspect_hg38_runtime_asset",
        lambda *args, **kwargs: SimpleNamespace(status=SimpleNamespace(value="ready")),
    )
    monkeypatch.setattr(
        build_ledger_module,
        "_compact_coordinate_index_status",
        lambda settings: "ready",
    )

    ledger = build_ledger_module.build_backend_build_ledger(
        settings,
        protein_annotation_status={"status": "available"},
    )

    items = {item["item_id"]: item for item in ledger["items"]}
    assert items["gene_view"]["status"] == "ready"
    assert items["gene_view"]["blockers"] == []
    assert items["gene_view"]["next_action"] is None


def test_pubmed_local_startup_materialization_flag_fails_closed(tmp_path: Path) -> None:
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        pubmed_local_startup_materialization_enabled=True,
    )

    with pytest.raises(RuntimeError, match="PubMed local startup materialization is disabled"):
        with TestClient(create_app(settings)):
            pass


def test_provider_cache_health_reports_ready_admin_predictors_without_paths(
    tmp_path: Path,
) -> None:
    ci_model = _write_runtime_file(tmp_path / "ci" / "model.keras", b"model")
    ci_reference = _write_runtime_file(tmp_path / "ci" / "reference.json", b"reference")
    ci_cache = _write_indexed_runtime_file(tmp_path / "ci" / "scores.vcf.gz", b"scores")
    capice_model = _write_runtime_file(tmp_path / "capice" / "model.json", b"model")
    capice_features = _write_indexed_runtime_file(
        tmp_path / "capice" / "features.tsv.gz",
        b"features",
    )
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        ci_spliceai_model_path=ci_model,
        ci_spliceai_reference_path=ci_reference,
        ci_spliceai_score_cache_path=ci_cache,
        capice_model_path=capice_model,
        capice_feature_cache_path=capice_features,
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    body = response.json()
    indexed = body["providers"]["indexed_predictors"]
    assert indexed["ci_spliceai"]["status"] == "ready"
    assert indexed["ci_spliceai"]["available"] is True
    assert indexed["ci_spliceai"]["status_notes"] == []
    assert indexed["capice"]["status"] == "ready"
    assert indexed["capice"]["available"] is True
    assert indexed["capice"]["status_notes"] == []
    ledger_items = {item["item_id"]: item for item in body["build_ledger"]["items"]}
    assert ledger_items["ci_spliceai"]["status"] == "ready"
    assert ledger_items["ci_spliceai"]["blockers"] == []
    assert ledger_items["capice"]["status"] == "ready"
    assert ledger_items["capice"]["blockers"] == []
    encoded = json.dumps(body).lower()
    assert str(tmp_path).lower() not in encoded
    assert "supabase://" not in encoded


def test_provider_cache_health_summarizes_source_cache_without_identity_leaks(client) -> None:
    repo = client.app.state.source_cache_repo
    repo.upsert(
        "gnomad",
        "gnomad:gnomad_r4:1-68444869-t-c",
        normalized_identity={"gene": "RPE65", "cdna": "c.260A>G"},
        request_identity={"variant_id": "1-68444869-T-C", "dataset": "gnomad_r4"},
        status="live",
        summary={"variant_id": "1-68444869-T-C", "allele_frequency": 0.00001},
        raw={"cached": True, "variant": "RPE65 c.260A>G"},
        warnings=["cached_warning"],
        source_url="https://gnomad.example.test/variant/1-68444869-T-C",
        ttl_days=30,
        source_version="gnomad_r4",
    )
    repo.upsert(
        "pubmed",
        "RPE65:c.260A>G",
        normalized_identity={"gene": "RPE65", "cdna": "c.260A>G"},
        request_identity={"query": "RPE65 c.260A>G"},
        status="fallback",
        summary={"total": 0},
        raw={"cached": True, "query": "RPE65 c.260A>G"},
        warnings=["old_warning"],
        source_url="https://pubmed.example.test/?term=RPE65+c.260A%3EG",
        ttl_days=-1,
    )

    response = client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    source_cache = response.json()["source_cache"]
    assert source_cache["total_rows"] == 2
    assert source_cache["fresh_rows"] == 1
    assert source_cache["stale_rows"] == 1
    assert source_cache["versioned_rows"] == 1
    assert source_cache["sources"]["gnomad"]["rows"] == 1
    assert source_cache["sources"]["gnomad"]["status_counts"] == {"live": 1}
    assert source_cache["sources"]["pubmed"]["stale_rows"] == 1
    assert source_cache["sources"]["pubmed"]["status_counts"] == {"fallback": 1}

    encoded = json.dumps(response.json()).lower()
    forbidden = [
        "cache_key",
        "normalized_identity",
        "request_identity",
        '"raw":',
        "warnings",
        "source_url",
        "1-68444869",
        "rpe65",
        "c.260a>g",
    ]
    for item in forbidden:
        assert item not in encoded


def test_provider_cache_health_reports_unavailable_crisprscore_without_paths(
    tmp_path: Path,
) -> None:
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        llm_provider="mock",
        use_real_apis=True,
        jwt_secret="test-secret",
        crispr_provider="crisprscore_r",
        crispr_rscript_path=tmp_path / "missing-rscript",
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    crispr = response.json()["providers"]["crispr"]
    assert crispr["configured_provider"] == "crisprscore_r"
    assert crispr["available"] is False
    assert crispr["status"] == "unavailable"
    assert crispr["providers"]["crisprscore_r"]["status"] == "unavailable"
    assert crispr["providers"]["crisprscore_r"]["checks"]["rscript"] is False
    assert crispr["providers"]["crisprscore_r"]["request_time_install_allowed"] is False
    assert crispr["providers"]["crisprscore_r"]["score_families"]["ruleset3"]["available"] is False
    assert str(tmp_path).lower() not in json.dumps(response.json()).lower()


def test_provider_cache_health_reports_primer_specificity_assets_without_paths(
    tmp_path: Path,
) -> None:
    binary_path = tmp_path / "isPcr"
    reference_path = tmp_path / "hg38.2bit"
    binary_path.write_bytes(b"tiny-binary")
    reference_path.write_bytes(b"tiny-reference")
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        primer_specificity_provider="ucsc_ispcr",
        ucsc_ispcr_binary_path=binary_path,
        ucsc_ispcr_hg38_path=reference_path,
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    specificity = response.json()["providers"]["crispr"]["primer_specificity"]
    assert specificity["configured_provider"] == "ucsc_ispcr"
    assert specificity["available"] is True
    assert specificity["status"] == "ucsc_ispcr_ready"
    assert specificity["whole_genome_specificity"] is True
    assert specificity["local_path_values_emitted"] is False
    assert str(tmp_path).lower() not in json.dumps(response.json()).lower()


def test_provider_cache_health_reports_sanitized_source_asset_materialization(
    tmp_path: Path,
) -> None:
    asset_path = tmp_path / "hg38.2bit"
    asset_path.write_bytes(b"tiny-hg38")
    object_path = "ucsc_hg38_2bit/hg38/md5-test/hg38.2bit"
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        hg38_2bit_runtime_asset_path=asset_path,
    )

    with TestClient(create_app(settings)) as test_client:
        test_client.app.state.supabase_local_model_cache_store = FakeMaterializationStore(
            SourceAssetMaterializationRecord(
                source_id="ucsc_hg38_2bit",
                asset_role="reference_genome_2bit",
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
                byte_size=835393456,
                checksum_algorithm="md5",
                checksum_value="dcc3ea27079aa6dc3f9deccd7275e0f8",
                verified_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
                fail_closed_reason=None,
                metadata={},
                warnings=[],
            )
        )
        response = test_client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    source_asset = response.json()["source_assets"]["hg38_2bit"]
    assert source_asset["materialization_metadata"] == {
        "enabled": True,
        "failure_boundaries": {
            "health_and_preflight_probe": "sanitized_status_no_exception",
            "lookup_sequence_context_runtime": "fail_open",
            "metadata_and_local_cache_resolution": "fail_closed",
        },
        "probe_performed": True,
        "ready": False,
        "status": "runtime_asset_size_mismatch",
    }

    encoded = json.dumps(response.json()).lower()
    assert str(tmp_path).lower() not in encoded
    assert object_path not in encoded


def test_provider_cache_health_survives_source_asset_probe_failure(
    client,
    monkeypatch,
) -> None:
    def fail_probe(*args, **kwargs):
        raise RuntimeError("private filesystem permission error")

    monkeypatch.setattr("app.api.routes.health.inspect_hg38_runtime_asset", fail_probe)

    response = client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    source_asset = response.json()["source_assets"]["hg38_2bit"]
    assert source_asset["source_id"] == "ucsc_hg38_2bit"
    assert source_asset["local_cache_ready"] is False
    assert source_asset["local_cache_status"] == "runtime_asset_probe_failed"
    assert source_asset["materialization_metadata"]["status"] == (
        "materialization_store_unavailable"
    )


def test_provider_cache_health_reports_available_protein_annotation_without_paths(
    tmp_path: Path,
) -> None:
    hmmscan = _fake_executable(tmp_path, "hmmscan")
    pfam_hmm = tmp_path / "protein" / "Pfam-A.hmm"
    pfam_hmm.parent.mkdir()
    pfam_hmm.write_text("HMMER3/f [test]\n//\n", encoding="utf-8")
    for suffix in (".h3f", ".h3i", ".h3m", ".h3p"):
        pfam_hmm.with_suffix(pfam_hmm.suffix + suffix).write_text("", encoding="utf-8")
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        protein_annotation_enabled=True,
        protein_annotation_hmmscan_path=hmmscan,
        protein_annotation_pfam_hmm_path=pfam_hmm,
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    protein = response.json()["providers"]["protein_annotation"]
    assert protein["enabled"] is True
    assert protein["available"] is True
    assert protein["status"] == "available"
    assert protein["hmmer"] == {
        "ready": True,
        "reason": None,
        "missing_index_count": 0,
    }
    assert str(tmp_path).lower() not in json.dumps(response.json()).lower()


def test_provider_cache_health_reports_partial_uniprot_index_without_hmmer_paths(
    tmp_path: Path,
) -> None:
    feature_index = tmp_path / "uniprot_sprot.features.jsonl"
    feature_index.write_text(
        '{"primary_accession":"O75445","accessions":["O75445"],"genes":["USH2A"],"features":[]}\n',
        encoding="utf-8",
    )
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        protein_annotation_enabled=True,
        protein_annotation_hmmscan_path=tmp_path / "missing-hmmscan",
        protein_annotation_uniprot_features_enabled=True,
        protein_annotation_uniprot_feature_index_path=feature_index,
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    protein = response.json()["providers"]["protein_annotation"]
    assert protein["enabled"] is True
    assert protein["available"] is True
    assert protein["status"] == "partial"
    assert protein["uniprot_feature_index"] == {"configured": True, "ready": True}
    assert protein["hmmer"]["ready"] is False
    assert protein["hmmer"]["reason"] == "hmmscan_executable_missing"
    assert str(tmp_path).lower() not in json.dumps(response.json()).lower()


def test_coordinate_resolver_startup_materialization_flag_fails_closed(
    tmp_path: Path,
) -> None:
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        coordinate_resolver_asset_materialization_enabled=True,
    )

    with pytest.raises(RuntimeError, match="startup materialization is disabled"):
        with TestClient(create_app(settings)):
            pass


class FakeMaterializationStore:
    def __init__(self, record: SourceAssetMaterializationRecord | None) -> None:
        self.record = record

    def get_source_asset_materialization(self, **kwargs) -> SourceAssetMaterializationRecord | None:
        return self.record


def _fake_executable(tmp_path: Path, name: str) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    path = tmp_path / f"{name}{suffix}"
    if os.name == "nt":
        path.write_text("@echo off\r\nexit /b 0\r\n", encoding="utf-8")
    else:
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _write_runtime_file(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _write_indexed_runtime_file(path: Path, payload: bytes) -> Path:
    _write_runtime_file(path, payload)
    Path(f"{path}.tbi").write_bytes(b"index")
    return path
