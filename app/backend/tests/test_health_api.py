from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
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
