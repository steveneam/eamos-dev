from __future__ import annotations

import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.data_sources.runtime_assets import SourceAssetMaterializationRecord
from app.main import create_app


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
    crispr = body["providers"]["crispr"]
    assert crispr["configured_provider"] == "local_deterministic"
    assert crispr["available"] is True
    assert crispr["providers"]["local_deterministic"]["available"] is True
    assert crispr["providers"]["crisprscore_r"]["status"] == "disabled"
    indexed = body["providers"]["indexed_predictors"]
    assert indexed["alphamissense"]["status"] == "missing_source_file"
    assert indexed["alphamissense"]["public_serialization_allowed"] is False
    assert indexed["esm1b"]["status"] == "missing_source_file"
    assert indexed["esm1b"]["public_serialization_allowed"] is False
    assert indexed["ci_spliceai"]["status"] == "restricted_unlicensed"
    assert indexed["pvs1_nmd"]["status"] == "pure_code_available"
    assert indexed["mavedb"]["status"] == "cc0_import_not_materialized"
    protein = body["providers"]["protein_annotation"]
    assert protein["enabled"] is False
    assert protein["available"] is False
    assert protein["status"] == "disabled"
    assert protein["cache_enabled"] is True
    assert protein["hmmer"]["ready"] is False
    assert "path" not in json.dumps(protein).lower()


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
        "raw",
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
