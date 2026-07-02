from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.repos.source_cache_repo import SourceCachePayload
from app.services.lookup_service_source_cache import LookupSourceCacheOrchestrator
from app.tools.base import ToolResult


class _MemorySourceCacheRepo:
    def __init__(self) -> None:
        self.fresh: dict[tuple[str, str], SourceCachePayload] = {}
        self.stale: dict[tuple[str, str], SourceCachePayload] = {}
        self.upserts: list[dict[str, Any]] = []

    def get_fresh(self, source: str, cache_key: str) -> SourceCachePayload | None:
        return self.fresh.get((source, cache_key))

    def get_stale(self, source: str, cache_key: str) -> SourceCachePayload | None:
        return self.stale.get((source, cache_key))

    def upsert(self, source: str, cache_key: str, **kwargs: Any) -> None:
        self.upserts.append({"source": source, "cache_key": cache_key, **kwargs})


def _variant() -> SimpleNamespace:
    return SimpleNamespace(
        gene="CFTR",
        transcript_hgvs="NM_000492.4:c.1521_1523delCTT",
        genomic_hg38="1-68444869-T-C",
        genomic_hgvs="NC_000001.11:g.68444869T>C",
    )


def _payload(
    *,
    source: str = "gnomad",
    cache_key: str = "gnomad:gnomad_r4:1-68444869-t-c",
    expires_delta: timedelta = timedelta(days=30),
) -> SourceCachePayload:
    now = datetime.now(timezone.utc)
    return SourceCachePayload(
        source=source,
        cache_key=cache_key,
        normalized_identity={"query": cache_key},
        request_identity={"variant_id": "1-68444869-T-C", "dataset": "gnomad_r4"},
        status="live",
        source_version="gnomad_r4",
        summary={"variant_id": "1-68444869-T-C", "dataset": "gnomad_r4"},
        raw={"cached": True},
        warnings=["cached_warning"],
        source_url="https://gnomad.example.test/variant/1-68444869-T-C",
        fetched_at=now,
        expires_at=now + expires_delta,
    )


def _orchestrator(
    repo: _MemorySourceCacheRepo,
    *,
    writer_calls: list[dict[str, Any]] | None = None,
    refresh: bool = False,
    settings: Any | None = None,
) -> LookupSourceCacheOrchestrator:
    if writer_calls is None:
        writer_calls = []

    def write_report_source_result_cache(cache_key: str, **kwargs: Any) -> None:
        writer_calls.append({"cache_key": cache_key, **kwargs})

    return LookupSourceCacheOrchestrator(
        settings=settings
        or SimpleNamespace(
            use_real_apis=True,
            cache_ttl_days=30,
            clingen_local_enabled=False,
        ),
        source_cache_repo=repo,
        tool_registry={"gnomad": SimpleNamespace(DATASET="gnomad_r4")},
        report_source_result_cache_writer=write_report_source_result_cache,
        cache_key="CFTR:c.1521_1523delCTT",
        gene="CFTR",
        cdna="c.1521_1523delCTT",
        variant=_variant(),
        evidence_map={},
        evidence_raw={},
        warnings=[],
        refresh=refresh,
        species="human",
    )


def test_lookup_source_cache_orchestrator_serves_fresh_hit_without_producer() -> None:
    repo = _MemorySourceCacheRepo()
    writer_calls: list[dict[str, Any]] = []
    cache_key = "gnomad:gnomad_r4:1-68444869-t-c"
    repo.fresh[("gnomad", cache_key)] = _payload(cache_key=cache_key)
    orchestrator = _orchestrator(repo, writer_calls=writer_calls)

    result = orchestrator.cached_result(
        "gnomad",
        lambda: pytest.fail("fresh source cache should bypass the producer"),
    )

    assert result.status == "cache"
    assert result.cache_status == "cache_hit"
    assert result.source_version == "gnomad_r4"
    assert repo.upserts == []
    assert writer_calls == []


def test_lookup_source_cache_orchestrator_serves_stale_cache_on_exception() -> None:
    repo = _MemorySourceCacheRepo()
    writer_calls: list[dict[str, Any]] = []
    cache_key = "gnomad:gnomad_r4:1-68444869-t-c"
    repo.stale[("gnomad", cache_key)] = _payload(
        cache_key=cache_key,
        expires_delta=timedelta(days=-1),
    )
    orchestrator = _orchestrator(repo, writer_calls=writer_calls)

    def raise_timeout() -> ToolResult:
        raise TimeoutError("live gnomAD timed out")

    result = orchestrator.cached_result("gnomad", raise_timeout)

    assert result.status == "stale"
    assert result.cache_status == "stale_on_failure"
    assert "source_cache_stale_on_failure:gnomad" in result.warnings
    assert "live_fetch_failed:TimeoutError" in result.warnings
    assert repo.upserts == []
    assert writer_calls == []


def test_lookup_source_cache_orchestrator_persists_success_and_report_snapshot() -> None:
    repo = _MemorySourceCacheRepo()
    writer_calls: list[dict[str, Any]] = []
    orchestrator = _orchestrator(repo, writer_calls=writer_calls)

    result = orchestrator.cached_result(
        "gnomad",
        lambda: ToolResult(
            source="gnomad",
            status="live",
            request_identity={"variant_id": "1-68444869-T-C", "dataset": "gnomad_r4"},
            summary={"variant_id": "1-68444869-T-C", "dataset": "gnomad_r4"},
            warnings=[],
            raw={"live": True},
            source_url="https://gnomad.example.test/variant/1-68444869-T-C",
        ),
    )

    assert result.status == "live"
    assert [item["cache_key"] for item in repo.upserts] == ["gnomad:gnomad_r4:1-68444869-t-c"]
    upsert = repo.upserts[0]
    assert upsert["normalized_identity"] == {
        "query": "gnomad:gnomad_r4:1-68444869-t-c",
        "gene": "CFTR",
        "cdna": "c.1521_1523delCTT",
        "genomic_hg38": "1-68444869-T-C",
        "genomic_hgvs": "NC_000001.11:g.68444869T>C",
    }
    assert upsert["source_version"] == "gnomad_r4"
    assert len(writer_calls) == 1
    assert writer_calls[0]["cache_key"] == "CFTR:c.1521_1523delCTT"
    assert writer_calls[0]["result"] is result
