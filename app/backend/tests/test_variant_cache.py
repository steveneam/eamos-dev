from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.config import Settings
from app.core.db import VariantCacheRecord, build_session_factory, initialize_database, session_scope
from app.repos.variant_cache_repo import VariantCacheRepo
from app.rules.clinic_rules import ClinicRules
from app.schemas.lookup import LookupRequest
from app.services.lookup_service import LookupService
from app.tools.base import ToolResult


def test_variant_cache_hit_miss_and_expiry(tmp_path: Path) -> None:
    session_factory = build_session_factory(
        f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}"
    )
    initialize_database(session_factory)
    repo = VariantCacheRepo(session_factory)

    assert repo.get_fresh("RPE65:c.260A>G", ttl_days=30) is None

    repo.upsert(
        "RPE65:c.260A>G",
        litvar_id="litvar-rpe65-c260ag",
        total_publications=816,
        publication_data={"summary": {"total_publications": 816}},
        strict_genomic_cache={"variant": {"genomic_hg38": "1-68444869-T-C"}},
    )
    hit = repo.get_fresh("RPE65:c.260A>G", ttl_days=30)

    assert hit is not None
    assert hit["total_publications"] == 816
    assert hit["strict_genomic_cache"]["variant"]["genomic_hg38"] == "1-68444869-T-C"

    with session_scope(session_factory) as session:
        record = session.execute(select(VariantCacheRecord)).scalar_one()
        record.created_at = datetime.now(timezone.utc) - timedelta(days=31)

    assert repo.get_fresh("RPE65:c.260A>G", ttl_days=30) is None


class _StaticTool:
    def __init__(self, source: str, summary: dict | None = None, raw=None) -> None:
        self.source = source
        self.summary = summary or {}
        self.raw = raw
        self.calls = 0

    def get_evidence(self, variant=None) -> ToolResult:
        self.calls += 1
        return ToolResult(
            source=self.source,
            status="live",
            request_identity={},
            summary=self.summary,
            raw=self.raw,
        )


class _ClinicalTrialsTool:
    def get_trials_summary(self, gene: str) -> str:
        return ""


def test_unresolved_lookup_is_not_persisted_or_served_from_cache(tmp_path: Path) -> None:
    session_factory = build_session_factory(
        f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}"
    )
    initialize_database(session_factory)
    repo = VariantCacheRepo(session_factory)
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}",
        jwt_secret="test-secret",
        use_real_apis=True,
    )
    vep_tool = _StaticTool("vep", {"most_severe_consequence": "", "biotype": ""})
    tools = {
        "vep": vep_tool,
        "variant_validator": _StaticTool("variant_validator"),
        "gnomad": _StaticTool("gnomad"),
        "spliceai": _StaticTool(
            "spliceai",
            {
                "acceptor_loss": 0.0,
                "donor_loss": 0.0,
                "acceptor_gain": 0.0,
                "donor_gain": 0.0,
            },
        ),
        "clinvar": _StaticTool(
            "clinvar",
            {
                "classification": "Unavailable",
                "review_status": "review status unavailable",
            },
            raw={
                "variation_set": [
                    {
                        "variation_xrefs": [
                            {"db_source": "dbSNP", "db_id": "1645931040"},
                        ],
                    },
                ],
            },
        ),
        "pubmed": _StaticTool("pubmed", {"articles": [], "total": 0}),
        "litvar2": _StaticTool(
            "litvar2",
            {
                "litvar_id": None,
                "total_publications": 0,
                "articles": [],
                "scholar_url": "https://scholar.google.com/scholar?q=RPE65+c.260A%3EG",
            },
        ),
        "clinical_trials": _ClinicalTrialsTool(),
    }
    service = LookupService(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        settings=settings,
    )
    request = LookupRequest(gene="RPE65", cdna="c.260A>G")

    first = service.lookup(request)
    second = service.lookup(request)

    assert first.report_payload.variant_summary_rows[0].genomic_hg38 is None
    assert second.report_payload.variant_summary_rows[0].genomic_hg38 is None
    assert vep_tool.calls == 2
    assert all(item.status != "cache" for item in second.evidence)
    assert repo.get_fresh("RPE65:c.260A>G", ttl_days=30) is None
    with session_scope(session_factory) as session:
        assert session.execute(select(VariantCacheRecord)).scalars().all() == []
