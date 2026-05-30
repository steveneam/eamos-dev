from __future__ import annotations

import json
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
    assert body["source_assets"]["hg38_2bit"]["materialization_metadata"] == {"enabled": False}
    crispr = body["providers"]["crispr"]
    assert crispr["configured_provider"] == "local_deterministic"
    assert crispr["available"] is True
    assert crispr["providers"]["local_deterministic"]["available"] is True
    assert crispr["providers"]["crisprscore_r"]["status"] == "disabled"


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
        "ready": False,
        "status": "runtime_asset_size_mismatch",
    }

    encoded = json.dumps(response.json()).lower()
    assert str(tmp_path).lower() not in encoded
    assert object_path not in encoded


class FakeMaterializationStore:
    def __init__(self, record: SourceAssetMaterializationRecord | None) -> None:
        self.record = record

    def get_source_asset_materialization(self, **kwargs) -> SourceAssetMaterializationRecord | None:
        return self.record
