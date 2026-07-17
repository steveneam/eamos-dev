from __future__ import annotations

import json
import os
import stat
from datetime import datetime, timezone
from hashlib import md5, sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.services.build_ledger as build_ledger_module
from app.core.config import Settings
from app.data_sources.runtime_assets import SourceAssetMaterializationRecord
from app.main import create_app
from app.services.ai_gateway.retrieval import LiteratureEmbeddingStore, LiteratureSourceRecord
from app.services.clinvar_local import (
    DEFAULT_CLINVAR_VCF_FIXTURE_PATH,
    materialize_clinvar_gene_distribution_index,
)
from app.services.crispr_offtarget_index import build_spcas9_offtarget_index_from_sequences
from app.services.duckdb_analytical import DUCKDB_ANALYTICAL_RELEASE_MANIFEST_SCHEMA_VERSION
from app.services.esm1b_assembly import ESM1B_REGENERATION_REQUIRED_GATE
from app.services.predictor_runtime import (
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
    ESM1B_LICENSE_GATE,
)

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
    source_cache = body["source_cache"]
    assert {
        key: source_cache[key]
        for key in (
            "enabled",
            "total_rows",
            "fresh_rows",
            "stale_rows",
            "versioned_rows",
            "oldest_fetched_at",
            "latest_fetched_at",
            "sources",
        )
    } == {
        "enabled": True,
        "total_rows": 0,
        "fresh_rows": 0,
        "stale_rows": 0,
        "versioned_rows": 0,
        "oldest_fetched_at": None,
        "latest_fetched_at": None,
        "sources": {},
    }
    assert "remote_supabase_cache" not in source_cache
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
    clinvar_gene_index = body["source_assets"]["clinvar_gene_distribution_index"]
    assert clinvar_gene_index["source_id"] == "eamos_clinvar_gene_distribution_index"
    assert clinvar_gene_index["ready"] is False
    assert clinvar_gene_index["status"] == "missing"
    assert clinvar_gene_index["startup_download_allowed"] is False
    assert clinvar_gene_index["request_time_materialization_allowed"] is False
    assert clinvar_gene_index["source_runtime_scan_allowed"] is False
    assert clinvar_gene_index["local_path_values_emitted"] is False
    assert clinvar_gene_index["raw_source_rows_emitted"] is False
    assert clinvar_gene_index["launch_gate"] == "clinvar_gene_distribution_index_materialization"
    duckdb_analytical = body["source_assets"]["duckdb_analytical"]
    assert duckdb_analytical["source_id"] == "eamos_duckdb_analytical"
    assert duckdb_analytical["ready"] is False
    assert duckdb_analytical["enabled"] is False
    assert duckdb_analytical["status"] == "disabled"
    assert duckdb_analytical["access_mode"] == "READ_ONLY"
    assert duckdb_analytical["point_lookup_engine"] == "tabix_sqlite_report_cache"
    assert duckdb_analytical["single_coordinate_hot_path_allowed"] is False
    assert duckdb_analytical["request_time_materialization_allowed"] is False
    assert duckdb_analytical["startup_download_allowed"] is False
    assert duckdb_analytical["remote_httpfs_allowed"] is False
    assert duckdb_analytical["motherduck_allowed"] is False
    assert duckdb_analytical["local_path_values_emitted"] is False
    assert duckdb_analytical["release"]["status"] == "manifest_missing"
    assert duckdb_analytical["release"]["local_path_values_emitted"] is False
    literature_embeddings = body["source_assets"]["literature_embeddings"]
    assert literature_embeddings["source_id"] == "eamos_literature_embeddings"
    assert literature_embeddings["ready"] is False
    assert literature_embeddings["enabled"] is False
    assert literature_embeddings["status"] == "db_missing"
    assert literature_embeddings["startup_download_allowed"] is False
    assert literature_embeddings["request_time_materialization_allowed"] is False
    assert literature_embeddings["local_path_values_emitted"] is False
    assert literature_embeddings["abstract_values_emitted"] is False
    assert literature_embeddings["vector_values_emitted"] is False
    local_runtime = body["source_assets"]["local_evidence_runtime_assets"]
    assert local_runtime["ready"] is False
    assert local_runtime["local_path_values_emitted"] is False
    assert local_runtime["object_uri_values_emitted"] is False
    local_runtime_sources = {item["item_id"]: item for item in local_runtime["sources"]}
    assert {
        item_id: item["freshness"]["status"] for item_id, item in local_runtime_sources.items()
    } == {
        "dbsnp_local_adapter": "unknown",
        "clinvar_local_adapter": "unknown",
        "repeatmasker_local_adapter": "unknown",
        "phylop_conservation_reader": "unknown",
    }
    assert local_runtime_sources["clinvar_local_adapter"]["freshness"] == {
        "tier": "volatile",
        "sla_days": 8,
        "status": "unknown",
        "staleness_days": None,
        "materialized_at": None,
        "upstream_released_at": None,
        "upstream_version": None,
        "source_version": None,
    }
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
    assert indexed["esm1b"]["launch_gate"] == ESM1B_REGENERATION_REQUIRED_GATE
    assert indexed["ci_spliceai"]["status"] == "score_cache_missing"
    assert indexed["ci_spliceai"]["runtime_wired"] is True
    assert indexed["ci_spliceai"]["public_serialization_allowed"] is True
    assert indexed["ci_spliceai"]["launch_gate"] == "ci_spliceai_launch_filter_metadata"
    assert indexed["gpn_msa"]["status"] == "remote_range_reader_planned"
    assert indexed["gpn_msa"]["runtime_wired"] is False
    assert indexed["gpn_msa"]["public_serialization_allowed"] is False
    assert indexed["gpn_msa"]["launch_gate"] is None
    assert indexed["pangolin"]["status"] == "source_decision_required"
    assert indexed["pangolin"]["runtime_wired"] is False
    assert indexed["pangolin"]["public_serialization_allowed"] is False
    assert indexed["pangolin"]["launch_gate"] is None
    assert indexed["capice"]["status"] == "model_artifact_missing"
    assert indexed["capice"]["runtime_wired"] is True
    assert indexed["capice"]["public_serialization_allowed"] is True
    assert indexed["capice"]["launch_gate"] == "capice_launch_filter_metadata"
    assert indexed["revel"]["status"] == "score_cache_missing"
    assert indexed["revel"]["runtime_wired"] is True
    assert indexed["revel"]["public_serialization_allowed"] is True
    assert indexed["revel"]["launch_gate"] == "revel_launch_filter_metadata"
    assert indexed["primateai3d"]["status"] == "score_cache_missing"
    assert indexed["primateai3d"]["runtime_wired"] is True
    assert indexed["primateai3d"]["public_serialization_allowed"] is True
    assert indexed["primateai3d"]["launch_gate"] == "primateai3d_launch_filter_metadata"
    assert indexed["pvs1_nmd"]["status"] == "pure_code_available"
    assert indexed["pvs1_nmd"]["source_id"] == "nmdetective_b_pvs1"
    assert indexed["pvs1_nmd"]["storage_required"] is False
    assert indexed["pvs1_nmd"]["status_notes"] == [
        "advisory_engine_only",
        "autopvs1_code_not_used",
    ]
    assert indexed["mavedb"]["status"] == "cc0_import_not_materialized"
    assert indexed["mavedb"]["runtime_wired"] is True
    assert indexed["mavedb"]["public_serialization_allowed"] is False
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
        "gpn_msa",
        "literature_rag_embeddings",
        "nmdetective_pvs1",
        "pangolin",
        "primateai3d",
        "protein_pfam",
        "revel",
    }
    assert required_items <= items.keys()
    assert items["alphamissense"]["status"] == "missing_source_file"
    assert items["alphamissense"]["runtime_wired"] is True
    assert items["alphamissense"]["public_serialization_allowed"] is True
    assert items["esm1b"]["runtime_wired"] is True
    assert items["esm1b"]["public_serialization_allowed"] is True
    assert items["esm1b"]["launch_gate"] == ESM1B_REGENERATION_REQUIRED_GATE
    assert items["ci_spliceai"]["runtime_wired"] is True
    assert items["ci_spliceai"]["public_serialization_allowed"] is True
    assert items["ci_spliceai"]["launch_gate"] == "ci_spliceai_launch_filter_metadata"
    assert items["gpn_msa"]["status"] == "remote_range_reader_planned"
    assert items["gpn_msa"]["runtime_wired"] is False
    assert items["gpn_msa"]["public_serialization_allowed"] is False
    assert items["gpn_msa"]["blockers"] == ["byte_range_reader_proof", "terms_review"]
    assert items["pangolin"]["status"] == "source_decision_required"
    assert items["pangolin"]["runtime_wired"] is False
    assert items["pangolin"]["public_serialization_allowed"] is False
    assert items["pangolin"]["blockers"] == [
        "source_terms_review",
        "runtime_design",
        "score_cache_or_model_materialization",
    ]
    assert items["capice"]["runtime_wired"] is True
    assert items["capice"]["public_serialization_allowed"] is True
    assert items["capice"]["launch_gate"] == "capice_launch_filter_metadata"
    assert items["revel"]["runtime_wired"] is True
    assert items["revel"]["public_serialization_allowed"] is True
    assert items["revel"]["launch_gate"] == "revel_launch_filter_metadata"
    assert items["primateai3d"]["runtime_wired"] is True
    assert items["primateai3d"]["public_serialization_allowed"] is True
    assert items["primateai3d"]["launch_gate"] == "primateai3d_launch_filter_metadata"
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
    assert items["literature_rag_embeddings"]["status"] == "rag_disabled"
    assert items["literature_rag_embeddings"]["runtime_wired"] is True
    assert items["literature_rag_embeddings"]["render_disk_role"] == "runtime_cache_required"
    assert items["literature_rag_embeddings"]["blockers"] == [
        "literature_embedding_materialization"
    ]
    encoded_ledger = json.dumps(ledger).lower()
    assert "supabase://" not in encoded_ledger
    assert "service_role" not in encoded_ledger


def test_provider_cache_health_reports_duckdb_release_ready_without_paths(
    client,
    tmp_path: Path,
) -> None:
    root, manifest_path = _write_tiny_duckdb_release(tmp_path)
    client.app.state.settings.duckdb_analytical_release_root = root
    client.app.state.settings.duckdb_analytical_release_manifest_path = manifest_path

    response = client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    duckdb_analytical = response.json()["source_assets"]["duckdb_analytical"]
    assert duckdb_analytical["status"] == "disabled"
    release = duckdb_analytical["release"]
    assert release["ready"] is True
    assert release["status"] == "ready"
    assert release["release_id"] == "pytest-mini"
    assert release["layer_counts"] == {"bronze": 1, "silver": 1, "gold": 1}
    assert release["row_count_total"] == 6
    assert release["checksum_verified"] is False
    assert release["local_path_values_emitted"] is False
    assert str(tmp_path).lower() not in json.dumps(duckdb_analytical).lower()


def test_provider_cache_health_reports_clinvar_gene_index_ready_without_paths(
    tmp_path: Path,
) -> None:
    index_path = tmp_path / "clinvar-gene-distribution.sqlite"
    manifest_path = tmp_path / "clinvar-gene-distribution.manifest.json"
    materialize_clinvar_gene_distribution_index(
        vcf_path=DEFAULT_CLINVAR_VCF_FIXTURE_PATH,
        index_path=index_path,
        manifest_path=manifest_path,
        force=True,
    )
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        llm_provider="mock",
        use_real_apis=False,
        workbench_live_design_enabled=False,
        clinvar_gene_distribution_index_path=index_path,
        clinvar_gene_distribution_manifest_path=manifest_path,
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    index_health = response.json()["source_assets"]["clinvar_gene_distribution_index"]
    assert index_health["source_id"] == "eamos_clinvar_gene_distribution_index"
    assert index_health["status"] == "ready"
    assert index_health["ready"] is True
    assert index_health["schema_version"] == "eamos.clinvar_gene_distribution.v1"
    assert index_health["gene_count"] == 1
    assert index_health["variant_count"] == 1
    assert index_health["local_path_values_emitted"] is False
    assert index_health["raw_source_rows_emitted"] is False
    assert str(tmp_path).lower() not in json.dumps(response.json()).lower()


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


def test_provider_cache_health_reports_literature_embeddings_ready_without_paths(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "literature.sqlite"
    manifest_path = tmp_path / "literature.manifest.json"
    store = LiteratureEmbeddingStore(db_path, manifest_path=manifest_path)
    store.write(
        [
            (
                LiteratureSourceRecord(
                    pmid="111",
                    genes=["RPE65"],
                    title="RPE65 retinal study",
                    snippet="Licensed abstract snippet",
                    embed_text="",
                    year=2022,
                    source_url="https://pubmed.ncbi.nlm.nih.gov/111/",
                    license_profile="cc_by",
                ),
                [1.0, 0.0, 0.0, 0.0],
            )
        ],
        embedding_model="test-embed",
        embedding_dim=4,
        source_version="lit-v1",
    )
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        rag_sqlite_path=db_path,
        rag_manifest_path=manifest_path,
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    body = response.json()
    source_asset = body["source_assets"]["literature_embeddings"]
    assert source_asset["ready"] is True
    assert source_asset["status"] == "ready"
    assert source_asset["enabled"] is False
    assert source_asset["article_count"] == 1
    assert source_asset["gene_pair_count"] == 1
    assert source_asset["embedding_model"] == "test-embed"
    assert source_asset["embedding_dim"] == 4
    assert source_asset["actual_size_bytes"] > 0
    ledger_items = {item["item_id"]: item for item in body["build_ledger"]["items"]}
    assert ledger_items["literature_rag_embeddings"]["status"] == "ready"
    assert ledger_items["literature_rag_embeddings"]["blockers"] == []
    encoded = json.dumps(body).lower()
    assert str(tmp_path).lower() not in encoded
    assert "literature.sqlite" not in encoded
    assert "supabase://" not in encoded


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


def test_build_ledger_enabled_local_evidence_omits_excluded_flow_blockers(
    tmp_path: Path,
) -> None:
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        use_real_apis=True,
        local_evidence_enabled=True,
        local_evidence_allowed_flows_raw="lookup,gene-viewer",
        local_evidence_require_real_apis=True,
    )

    ledger = build_ledger_module.build_backend_build_ledger(settings)

    items = {item["item_id"]: item for item in ledger["items"]}
    orchestrator = items["local_evidence_orchestrator"]
    assert orchestrator["status"] == "enabled"
    assert orchestrator["wired_surfaces"] == ["lookup", "gene_viewer"]
    assert orchestrator["blockers"] == []
    assert orchestrator["next_action"] is None


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
    _write_admin_predictor_manifest(
        ci_model,
        artifact_id="ci_spliceai",
        component_id="model",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_keras_model",
        role=CI_SPLICEAI_MODEL_ASSET_ROLE,
        launch_gate=CI_SPLICEAI_LAUNCH_GATE,
    )
    _write_admin_predictor_manifest(
        ci_reference,
        artifact_id="ci_spliceai",
        component_id="reference_bundle",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_reference_bundle",
        role=CI_SPLICEAI_REFERENCE_ASSET_ROLE,
        launch_gate=CI_SPLICEAI_LAUNCH_GATE,
    )
    _write_admin_predictor_manifest(
        ci_cache,
        artifact_id="ci_spliceai",
        component_id="score_cache",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_hg38_score_cache_vcf_gz",
        role=CI_SPLICEAI_SCORE_CACHE_ASSET_ROLE,
        launch_gate=CI_SPLICEAI_LAUNCH_GATE,
    )
    _write_admin_predictor_manifest(
        capice_model,
        artifact_id="capice",
        component_id="model",
        source_id=CAPICE_SOURCE_ID,
        asset_id="capice_xgboost_model",
        role=CAPICE_MODEL_ASSET_ROLE,
        launch_gate=CAPICE_LAUNCH_GATE,
    )
    _write_admin_predictor_manifest(
        capice_features,
        artifact_id="capice",
        component_id="feature_cache",
        source_id=CAPICE_FEATURE_CACHE_SOURCE_ID,
        asset_id="capice_hg38_feature_cache_tsv_gz",
        role=CAPICE_FEATURE_CACHE_ASSET_ROLE,
        launch_gate=CAPICE_LAUNCH_GATE,
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


def test_provider_cache_health_does_not_trust_legacy_nullable_esm1b_launch_gate(
    tmp_path: Path,
) -> None:
    esm1b = _write_indexed_runtime_file(tmp_path / "esm1b" / "esm1b_hg38.tsv.gz", b"scores")
    esm1b.with_suffix(esm1b.suffix + ".manifest.json").write_text(
        '{"license_gate": null, "score_generation_method": "mit_model_regeneration"}',
        encoding="utf-8",
    )
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        esm1b_hg38_runtime_asset_path=esm1b,
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    body = response.json()
    indexed = body["providers"]["indexed_predictors"]
    assert indexed["esm1b"]["status"] == "ready"
    assert indexed["esm1b"]["launch_gate"] == ESM1B_LICENSE_GATE
    ledger_items = {item["item_id"]: item for item in body["build_ledger"]["items"]}
    assert ledger_items["esm1b"]["status"] == "ready"
    assert ledger_items["esm1b"]["launch_gate"] == ESM1B_LICENSE_GATE


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


def test_provider_cache_health_survives_predictor_materialization_read_failure(
    tmp_path: Path,
) -> None:
    alphamissense = _write_indexed_runtime_file(
        tmp_path / "predictors" / "AlphaMissense_hg38.tsv.gz",
        b"tiny-alphamissense",
    )
    alphamissense.with_suffix(alphamissense.suffix + ".manifest.json").write_text(
        "{}",
        encoding="utf-8",
    )
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        alphamissense_hg38_runtime_asset_path=alphamissense,
        alphamissense_hg38_runtime_asset_object_uri=(
            "supabase://eamos-source-assets/google_deepmind_alphamissense_hg38/"
            "md5-test/AlphaMissense_hg38.tsv.gz"
        ),
    )

    with TestClient(create_app(settings)) as test_client:
        test_client.app.state.supabase_local_model_cache_store = ExplodingMaterializationStore()
        response = test_client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    body = response.json()
    alphamissense_status = body["providers"]["indexed_predictors"]["alphamissense"]
    assert alphamissense_status["available"] is False
    assert alphamissense_status["status"] == "materialization_store_unavailable"
    assert alphamissense_status["materialization_status"] == (
        "materialization_metadata_unavailable"
    )
    encoded = json.dumps(body).lower()
    assert "private.example" not in encoded
    assert "postgresql://" not in encoded
    assert "supabase://" not in encoded
    assert str(tmp_path).lower() not in encoded


def test_provider_cache_health_reports_local_evidence_runtime_assets_without_paths(
    tmp_path: Path,
) -> None:
    materialized_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    upstream_released_at = datetime.now(timezone.utc).date().isoformat()
    dbsnp_vcf = _write_indexed_runtime_file(tmp_path / "dbsnp" / "GCF_000001405.40.gz", b"vcf")
    _write_local_evidence_manifest(
        dbsnp_vcf,
        source_version="dbSNP pytest",
        materialized_at=materialized_at,
        upstream_released_at=upstream_released_at,
    )
    _write_local_evidence_manifest(
        Path(f"{dbsnp_vcf}.tbi"),
        source_version="dbSNP pytest",
        materialized_at=materialized_at,
        upstream_released_at=upstream_released_at,
    )
    clinvar_vcf = _write_indexed_runtime_file(
        tmp_path / "clinvar" / "clinvar.vcf.gz",
        b"clinvar",
    )
    _write_local_evidence_manifest(
        clinvar_vcf,
        source_version="ClinVar pytest",
        materialized_at=materialized_at,
        upstream_released_at=upstream_released_at,
    )
    _write_local_evidence_manifest(
        Path(f"{clinvar_vcf}.tbi"),
        source_version="ClinVar pytest",
        materialized_at=materialized_at,
        upstream_released_at=upstream_released_at,
    )
    repeatmasker_index = _write_runtime_file(
        tmp_path / "repeatmasker" / "repeatmasker.interval-index.jsonl",
        b"index",
    )
    _write_local_evidence_manifest(
        repeatmasker_index,
        source_version="RepeatMasker pytest",
        materialized_at=materialized_at,
        upstream_released_at=upstream_released_at,
    )
    phylop_bigwig = _write_runtime_file(tmp_path / "phylop" / "hg38.phyloP100way.bw", b"bw")
    _write_local_evidence_manifest(
        phylop_bigwig,
        source_version="phyloP pytest",
        materialized_at=materialized_at,
    )
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        supabase_local_model_cache_enabled=False,
        dbsnp_runtime_vcf_path=dbsnp_vcf,
        dbsnp_runtime_index_path=Path(f"{dbsnp_vcf}.tbi"),
        clinvar_runtime_vcf_path=clinvar_vcf,
        clinvar_runtime_index_path=Path(f"{clinvar_vcf}.tbi"),
        repeatmasker_runtime_index_path=repeatmasker_index,
        phylop_runtime_bigwig_path=phylop_bigwig,
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    runtime = response.json()["source_assets"]["local_evidence_runtime_assets"]
    assert runtime["ready"] is True
    assert runtime["ready_count"] == 4
    assert runtime["runtime_reader_opened"] is False
    assert runtime["source_runtime_scan_allowed"] is False
    assert runtime["local_path_values_emitted"] is False
    by_item = {item["item_id"]: item for item in runtime["sources"]}
    assert {item["status"] for item in by_item.values()} == {"ready"}
    assert by_item["clinvar_local_adapter"]["freshness"] == {
        "tier": "volatile",
        "sla_days": 8,
        "status": "fresh",
        "staleness_days": 0,
        "materialized_at": materialized_at,
        "upstream_released_at": upstream_released_at,
        "upstream_version": "ClinVar pytest",
        "source_version": "ClinVar pytest",
    }
    assert by_item["dbsnp_local_adapter"]["freshness"]["tier"] == "static"
    assert by_item["dbsnp_local_adapter"]["freshness"]["sla_days"] is None
    assert by_item["dbsnp_local_adapter"]["freshness"]["status"] == "fresh"
    assert by_item["repeatmasker_local_adapter"]["freshness"]["status"] == "fresh"
    assert by_item["phylop_conservation_reader"]["freshness"] == {
        "tier": "static",
        "sla_days": None,
        "status": "unknown",
        "staleness_days": None,
        "materialized_at": materialized_at,
        "upstream_released_at": None,
        "upstream_version": "phyloP pytest",
        "source_version": "phyloP pytest",
    }
    for source in by_item.values():
        assert "freshness" in source
        for asset in source["assets"]:
            assert "freshness" in asset
            assert "manifest" not in json.dumps(asset).lower()
    ledger_items = {item["item_id"]: item for item in response.json()["build_ledger"]["items"]}
    assert ledger_items["dbsnp_local_adapter"]["status"] == "ready"
    assert ledger_items["clinvar_local_adapter"]["status"] == "ready"
    assert ledger_items["repeatmasker_local_adapter"]["status"] == "ready"
    assert ledger_items["phylop_conservation_reader"]["status"] == "ready"
    assert str(tmp_path).lower() not in json.dumps(response.json()).lower()


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


class ExplodingMaterializationStore:
    def get_source_asset_materialization(self, **kwargs) -> SourceAssetMaterializationRecord:
        raise RuntimeError(
            "database unavailable at postgresql://postgres:secret@private.example/path "
            "for supabase://eamos-source-assets/private/object and D:\\secret\\asset"
        )


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


def _write_local_evidence_manifest(
    path: Path,
    *,
    source_version: str,
    materialized_at: str,
    upstream_released_at: str | None = None,
) -> None:
    payload = {
        "schema_version": "pytest.local-evidence-freshness.v1",
        "source_version": source_version,
        "upstream_version": source_version,
        "materialized_at": materialized_at,
    }
    if upstream_released_at is not None:
        payload["upstream_released_at"] = upstream_released_at
    path.with_suffix(path.suffix + ".manifest.json").write_text(
        json.dumps(payload, sort_keys=True),
        encoding="utf-8",
    )


def _write_tiny_duckdb_release(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "analytical"
    release_id = "pytest-mini"
    artifacts = [
        ("bronze", "1", "clinvar-bronze.parquet", b"bronze-clinvar\n", 1),
        ("silver", "1", "clinvar-silver.parquet", b"silver-clinvar\n", 2),
        ("gold", "2", "clinvar-dbsnp-gold.parquet", b"gold-join\n", 3),
    ]
    manifest_artifacts = []
    for layer, chrom, filename, content, row_count in artifacts:
        relative_path = f"{layer}/{release_id}/chrom={chrom}/{filename}"
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        manifest_artifacts.append(
            {
                "path": relative_path,
                "layer": layer,
                "chrom": chrom,
                "format": "parquet",
                "schema_version": "pytest.v1",
                "row_count": row_count,
                "sha256": sha256(content).hexdigest(),
            }
        )

    manifest_path = root / "manifests" / "current.manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": DUCKDB_ANALYTICAL_RELEASE_MANIFEST_SCHEMA_VERSION,
                "release_id": release_id,
                "source_ids": ["clinvar", "dbsnp"],
                "source_versions": {"clinvar": "pytest", "dbsnp": "pytest"},
                "input_checksums": {"clinvar": "sha256:fixture", "dbsnp": "sha256:fixture"},
                "build": {"command": "pytest tiny fixture", "host": "pytest"},
                "required_layers": ["bronze", "silver", "gold"],
                "row_count_total": 6,
                "artifacts": manifest_artifacts,
            }
        ),
        encoding="utf-8",
    )
    return root, manifest_path


def _write_admin_predictor_manifest(
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
    md5_value = md5(payload, usedforsecurity=False).hexdigest()
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
