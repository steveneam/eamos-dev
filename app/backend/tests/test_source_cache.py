from __future__ import annotations

from pathlib import Path

from sqlalchemy import event

from app.core.config import Settings
from app.core.db import (
    build_session_factory,
    initialize_database,
)
from app.repos.source_cache_repo import SourceCacheRepo
from app.rules.clinic_rules import ClinicRules
from app.schemas.lookup import LookupRequest, LookupResponse
from app.schemas.run import ReportPayload
from app.services.lookup_service import LookupService
from app.services.source_cache import (
    HERO_EXAMPLE_VARIANTS,
    HeroExampleSourceCacheWarmer,
    clingen_vcep_source_cache_key,
)
from app.tools.base import ToolResult


class _StaticTool:
    def __init__(
        self,
        source: str,
        summary: dict | None = None,
        *,
        status: str = "live",
        raw=None,
        warnings: list[str] | None = None,
    ) -> None:
        self.source = source
        self.summary = summary or {}
        self.status = status
        self.raw = raw
        self.warnings = list(warnings or [])
        self.calls = 0

    def get_evidence(self, variant=None, **_kwargs) -> ToolResult:
        self.calls += 1
        return ToolResult(
            source=self.source,
            status=self.status,
            request_identity={"source": self.source},
            summary=self.summary,
            raw=self.raw,
            warnings=list(self.warnings),
            source_url=f"https://example.test/{self.source}",
        )


class _MutatingVariantValidatorTool(_StaticTool):
    def get_evidence(self, variant=None, **_kwargs) -> ToolResult:
        result = super().get_evidence(variant=variant)
        if variant is not None:
            variant.genomic_hg38 = "1-68444869-T-C"
            variant.genomic_hgvs = "NC_000001.11:g.68444869T>C"
            variant.variation_type = "single nucleotide variant"
            variant.consequence = "missense_variant"
        result.summary = {
            **result.summary,
            "variant_id": "1-68444869-T-C",
            "hgvs_genomic_description": "NC_000001.11:g.68444869T>C",
            "variation_type": "single nucleotide variant",
            "consequence": "missense_variant",
        }
        return result


class _ClinicalTrialsTool:
    def get_trials_summary(self, gene: str) -> str:
        return ""


class _NoopFunctionalEvidenceExtractor:
    def build_for_lookup(self, *args, **kwargs):
        from app.schemas.run import FunctionalEvidenceSummary

        return FunctionalEvidenceSummary(total_count=0)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}",
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "reports",
        jwt_secret="test-secret",
        use_real_apis=True,
        llm_provider="mock",
        cache_ttl_days=30,
        clingen_local_enabled=False,
        clingen_local_sqlite_path=tmp_path / "missing-clingen.sqlite",
        clingen_local_manifest_path=tmp_path / "missing-clingen.manifest.json",
    )


def _service(
    tmp_path: Path,
    repo: SourceCacheRepo,
    *,
    pubmed_tool: _StaticTool | None = None,
    tool_overrides: dict[str, object] | None = None,
) -> LookupService:
    settings = _settings(tmp_path)
    pubmed = pubmed_tool or _StaticTool("pubmed", {"articles": [], "total": 0})
    tools = {
        "vep": _StaticTool("vep", {"most_severe_consequence": "missense_variant"}),
        "variant_validator": _MutatingVariantValidatorTool("variant_validator"),
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
                "classification": "Uncertain significance",
                "review_status": "criteria provided, single submitter",
            },
            raw={"variation_set": []},
        ),
        "clingen": _StaticTool("clingen"),
        "gene_disease": _StaticTool("gene_disease"),
        "molecular_context": _StaticTool("molecular_context"),
        "computational_annotations": _StaticTool("computational_annotations"),
        "pubmed": pubmed,
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
    tools.update(tool_overrides or {})
    return LookupService(
        tools,
        ClinicRules(),
        source_cache_repo=repo,
        settings=settings,
        functional_evidence_extractor=_NoopFunctionalEvidenceExtractor(),
    )


def _repo(tmp_path: Path) -> SourceCacheRepo:
    session_factory = build_session_factory(
        f"sqlite+pysqlite:///{(tmp_path / 'source-cache.db').as_posix()}"
    )
    initialize_database(session_factory)
    return SourceCacheRepo(session_factory)


def _rpe65_identity_match() -> dict:
    return {
        "tier": "transcript_hgvs",
        "source_field": "hgvs",
        "requested": "NM_000329.3:c.260A>G",
        "matched": "NM_000329.3:c.260A>G",
        "normalized_requested": "nm_000329.3:c.260a>g",
        "normalized_matched": "nm_000329.3:c.260a>g",
        "auto_attach_allowed": True,
    }


def _expert_panel_summary(identity_match: dict | None = None) -> dict:
    identity_match = identity_match or _rpe65_identity_match()
    return {
        "identity_match": identity_match,
        "expert_panel": {
            "vcep": {
                "id": "ClinGen:IRD",
                "name": "Inherited Retinal Dystrophies VCEP",
                "affiliation_id": "50039",
                "last_curated_date": "2023-08-14",
                "vcep_url": "https://erepo.clinicalgenome.org/evrepo/ui/classifications/CA189146",
            },
            "final_classification": "likely_pathogenic",
            "narrative": "Cached ClinGen VCEP assertion.",
            "criteria": [
                {
                    "code": "PM2",
                    "applied_strength": "PM2_Moderate",
                    "default_strength": "PM2_Moderate",
                    "state": "met",
                    "assertion_level": "vcep_specified",
                    "rationale": "Cached PM2 rationale.",
                    "source": "ClinGen Evidence Repository",
                    "evidence_refs": ["cached-clingen"],
                    "warnings": [],
                }
            ],
            "source_scope": "ClinGen Evidence Repository - cached VCEP curation",
            "provenance": {
                "source_url": "https://erepo.clinicalgenome.org/evrepo/api/classifications/CA189146",
                "fetched_at": "2026-05-27T22:14:00Z",
                "source_version": "ClinGen Evidence Repo cached",
                "cache_record_id": "clingen:clinvar:VCV001421454",
                "raw_jsonld_ref": "fixture:cached-clingen",
                "identity_match": identity_match,
            },
            "freshness": "fresh",
            "freshness_reason": "cache_hit",
        }
    }


def test_source_cache_repo_returns_fresh_and_stale_rows(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    repo.upsert(
        "pubmed",
        "RPE65:c.260A>G",
        normalized_identity={"gene": "RPE65", "cdna": "c.260A>G"},
        request_identity={"query": "RPE65 c.260A>G"},
        status="live",
        summary={"total": 1},
        raw={"source": "pubmed"},
        warnings=[],
        source_url="https://pubmed.ncbi.nlm.nih.gov/",
        ttl_days=30,
        source_version="pubmed-live",
    )

    fresh = repo.get_fresh("pubmed", "RPE65:c.260A>G")
    assert fresh is not None
    assert fresh.summary == {"total": 1}
    assert fresh.to_tool_result(status="cache", cache_status="cache_hit").status == "cache"

    repo.upsert(
        "pubmed",
        "RPE65:c.260A>G",
        normalized_identity={"gene": "RPE65", "cdna": "c.260A>G"},
        request_identity={"query": "RPE65 c.260A>G"},
        status="live",
        summary={"total": 2},
        raw={"source": "pubmed"},
        warnings=["old_warning"],
        source_url="https://pubmed.ncbi.nlm.nih.gov/",
        ttl_days=-1,
    )

    assert repo.get_fresh("pubmed", "RPE65:c.260A>G") is None
    stale = repo.get_stale("pubmed", "RPE65:c.260A>G")
    assert stale is not None
    stale_result = stale.to_tool_result(
        status="stale",
        cache_status="stale_on_failure",
        extra_warnings=["live_status:fallback"],
    )
    assert stale_result.status == "stale"
    assert stale_result.summary == {"total": 2}
    assert stale_result.warnings == ["old_warning", "live_status:fallback"]


def test_source_cache_health_summary_uses_aggregate_queries(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
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

    engine = repo.session_factory.kw["bind"]
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(str(statement).lower())

    event.listen(engine, "before_cursor_execute", capture_sql)
    try:
        summary = repo.health_summary()
    finally:
        event.remove(engine, "before_cursor_execute", capture_sql)

    assert summary["total_rows"] == 2
    assert summary["fresh_rows"] == 1
    assert summary["sources"]["gnomad"]["status_counts"] == {"live": 1}
    assert summary["sources"]["pubmed"]["status_counts"] == {"fallback": 1}
    selected_sql = "\n".join(statement for statement in statements if "source_cache" in statement)
    assert "group by source_cache.source" in selected_sql
    assert "group by source_cache.source, source_cache.status" in selected_sql
    for column in (
        "source_cache.cache_key",
        "source_cache.normalized_identity",
        "source_cache.request_identity",
        "source_cache.summary",
        "source_cache.raw",
        "source_cache.warnings",
        "source_cache.source_url",
    ):
        assert column not in selected_sql


def test_hero_example_lookup_uses_fresh_source_cache(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    pubmed_tool = _StaticTool("pubmed", {"articles": [], "total": 0})
    repo.upsert(
        "pubmed",
        "RPE65:c.11+5G>A",
        normalized_identity={"gene": "RPE65", "cdna": "c.11+5G>A"},
        request_identity={"query": "cached RPE65 c.11+5G>A"},
        status="live",
        summary={
            "articles": [
                {
                    "pmid": "38191234",
                    "title": "Cached RPE65 c.11+5G>A report",
                    "authors": "Eamos",
                    "journal": "Cache",
                    "year": "2026",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/38191234/",
                }
            ],
            "total": 1,
        },
        raw={"cached": True},
        warnings=[],
        source_url="https://pubmed.ncbi.nlm.nih.gov/?term=RPE65+c.11%2B5G%3EA",
        ttl_days=30,
    )
    service = _service(tmp_path, repo, pubmed_tool=pubmed_tool)

    response = service.lookup(LookupRequest(gene="RPE65", cdna="c.11+5G>A"))

    pubmed = next(item for item in response.evidence if item.source == "pubmed")
    assert pubmed_tool.calls == 0
    assert pubmed.status == "cache"
    assert pubmed.cache_status == "cache_hit"
    assert pubmed.fetched_at is not None
    assert pubmed.summary["total"] == 1
    assert response.report_payload.pubmed_articles[0].title == "Cached RPE65 c.11+5G>A report"


def test_hero_example_lookup_serves_stale_cache_when_live_source_fails(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    pubmed_tool = _StaticTool(
        "pubmed",
        {"articles": [], "total": 0},
        status="fallback",
        warnings=["live_fetch_failed:TimeoutException"],
    )
    repo.upsert(
        "pubmed",
        "RPE65:c.11+5G>A",
        normalized_identity={"gene": "RPE65", "cdna": "c.11+5G>A"},
        request_identity={"query": "cached RPE65 c.11+5G>A"},
        status="live",
        summary={
            "articles": [
                {
                    "pmid": "38191234",
                    "title": "Stale RPE65 c.11+5G>A report",
                    "authors": "Eamos",
                    "journal": "Cache",
                    "year": "2026",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/38191234/",
                }
            ],
            "total": 1,
        },
        raw={"cached": True},
        warnings=["cached_warning"],
        source_url="https://pubmed.ncbi.nlm.nih.gov/?term=RPE65+c.11%2B5G%3EA",
        ttl_days=-1,
    )
    service = _service(tmp_path, repo, pubmed_tool=pubmed_tool)

    response = service.lookup(LookupRequest(gene="RPE65", cdna="c.11+5G>A"))

    pubmed = next(item for item in response.evidence if item.source == "pubmed")
    assert pubmed_tool.calls == 1
    assert pubmed.status == "stale"
    assert pubmed.cache_status == "stale_on_failure"
    assert pubmed.fetched_at is not None
    assert pubmed.summary["total"] == 1
    assert "source_cache_stale_on_failure:pubmed" in pubmed.warnings
    assert response.report_payload.pubmed_articles[0].title == "Stale RPE65 c.11+5G>A report"
    stored = repo.get_any("pubmed", "RPE65:c.11+5G>A")
    assert stored is not None
    assert stored.summary["articles"][0]["title"] == "Stale RPE65 c.11+5G>A report"


def test_arbitrary_lookup_uses_fresh_source_cache_for_selected_sources(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    gnomad_tool = _StaticTool(
        "gnomad",
        {
            "variant_id": "live-should-not-be-used",
            "dataset": "gnomad_r4",
        },
    )
    repo.upsert(
        "gnomad",
        "gnomad:gnomad_r4:1-68444869-t-c",
        normalized_identity={"gene": "CFTR", "cdna": "c.1521_1523delCTT"},
        request_identity={"variant_id": "1-68444869-T-C", "dataset": "gnomad_r4"},
        status="live",
        summary={
            "gene": "CFTR",
            "variant_id": "1-68444869-T-C",
            "dataset": "gnomad_r4",
            "allele_frequency": 0.00001,
        },
        raw={"cached": True},
        warnings=[],
        source_url="https://gnomad.broadinstitute.org/variant/1-68444869-T-C?dataset=gnomad_r4",
        ttl_days=30,
        source_version="gnomad_r4",
    )
    service = _service(tmp_path, repo, tool_overrides={"gnomad": gnomad_tool})

    response = service.lookup(LookupRequest(gene="CFTR", cdna="c.1521_1523delCTT"))

    gnomad = next(item for item in response.evidence if item.source == "gnomad")
    assert gnomad_tool.calls == 0
    assert gnomad.status == "cache"
    assert gnomad.cache_status == "cache_hit"
    assert gnomad.source_version == "gnomad_r4"
    assert gnomad.summary["allele_frequency"] == 0.00001


def test_arbitrary_lookup_serves_stale_cache_for_selected_source_failure(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    gnomad_tool = _StaticTool(
        "gnomad",
        {"variant_id": "1-68444869-T-C", "dataset": "gnomad_r4"},
        status="fallback",
        raw=None,
        warnings=["live_fetch_failed:ReadTimeout"],
    )
    repo.upsert(
        "gnomad",
        "gnomad:gnomad_r4:1-68444869-t-c",
        normalized_identity={"gene": "CFTR", "cdna": "c.1521_1523delCTT"},
        request_identity={"variant_id": "1-68444869-T-C", "dataset": "gnomad_r4"},
        status="live",
        summary={
            "gene": "CFTR",
            "variant_id": "1-68444869-T-C",
            "dataset": "gnomad_r4",
            "allele_frequency": 0.00001,
        },
        raw={"cached": True},
        warnings=["cached_warning"],
        source_url="https://gnomad.broadinstitute.org/variant/1-68444869-T-C?dataset=gnomad_r4",
        ttl_days=-1,
    )
    service = _service(tmp_path, repo, tool_overrides={"gnomad": gnomad_tool})

    response = service.lookup(LookupRequest(gene="CFTR", cdna="c.1521_1523delCTT"))

    gnomad = next(item for item in response.evidence if item.source == "gnomad")
    assert gnomad_tool.calls == 1
    assert gnomad.status == "stale"
    assert gnomad.cache_status == "stale_on_failure"
    assert gnomad.summary["allele_frequency"] == 0.00001
    assert "source_cache_stale_on_failure:gnomad" in gnomad.warnings
    assert "live_status:fallback" in gnomad.warnings
    population = response.report_payload.report_profile.population_frequency
    assert population is not None
    assert population.source_status == "stale"
    assert population.unavailable_reason is None
    population_card = next(
        card
        for card in response.report_payload.call_cards.cards
        if card.card_id == "population_frequency"
    )
    assert population_card.source_status == "stale"
    currency = response.report_payload.report_data_currency
    assert currency is not None
    currency_sources = {source.source: source for source in currency.sources}
    assert currency_sources["gnomad"].status == "stale"
    assert currency_sources["gnomad"].source_version == "gnomad_r4"


def test_clingen_vcep_cache_key_prefers_clinvar_vcv_over_hgvs() -> None:
    cache_key = clingen_vcep_source_cache_key(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.260A>G",
        clinvar_summary={"accession": "VCV001421454"},
    )

    assert cache_key == "clinvar:VCV001421454"


def test_clingen_vcep_lookup_uses_fresh_source_cache(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    cache_key = "clinvar:VCV001421454"
    repo.upsert(
        "clingen",
        cache_key,
        normalized_identity={"gene": "RPE65", "clinvar_accession": "VCV001421454"},
        request_identity={"cache_key": cache_key},
        status="live",
        summary=_expert_panel_summary(),
        raw={"cached": True},
        warnings=[],
        source_url="https://erepo.clinicalgenome.org/evrepo/api/classifications/CA189146",
        ttl_days=30,
        source_version="ClinGen Evidence Repo cached",
    )
    clingen_tool = _StaticTool("clingen", _expert_panel_summary())
    service = _service(
        tmp_path,
        repo,
        tool_overrides={
            "clinvar": _StaticTool(
                "clinvar",
                {
                    "classification": "Uncertain significance",
                    "review_status": "criteria provided, single submitter",
                    "accession": "VCV001421454",
                },
                raw={"variation_set": []},
            ),
            "clingen": clingen_tool,
        },
    )

    response = service.lookup(LookupRequest(gene="RPE65", cdna="c.260A>G"))

    clingen = next(item for item in response.evidence if item.source == "clingen")
    assert clingen_tool.calls == 0
    assert clingen.status == "cache"
    assert clingen.cache_status == "cache_hit"
    assert response.report_payload.report_profile is not None
    expert_panel = response.report_payload.report_profile.expert_panel
    assert expert_panel is not None
    assert expert_panel.provenance.source_version == "ClinGen Evidence Repo cached"
    assert expert_panel.freshness == "fresh"
    assert expert_panel.freshness_reason == "cache_hit"


def test_clingen_vcep_lookup_rejects_identity_mismatched_source_cache(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    cache_key = "clinvar:VCV001421454"
    mismatched_identity = {
        **_rpe65_identity_match(),
        "requested": "NM_000350.3:c.4253+43G>A",
        "matched": "NM_000350.3:c.4253+43G>A",
        "normalized_requested": "nm_000350.3:c.4253+43g>a",
        "normalized_matched": "nm_000350.3:c.4253+43g>a",
    }
    repo.upsert(
        "clingen",
        cache_key,
        normalized_identity={"gene": "RPE65", "clinvar_accession": "VCV001421454"},
        request_identity={"cache_key": cache_key},
        status="live",
        summary=_expert_panel_summary(identity_match=mismatched_identity),
        raw={"cached": True},
        warnings=[],
        source_url="https://erepo.clinicalgenome.org/evrepo/api/classifications/CA189146",
        ttl_days=30,
        source_version="ClinGen Evidence Repo cached",
    )
    clingen_tool = _StaticTool(
        "clingen",
        status="missing",
        warnings=["clingen_variant_not_found"],
    )
    service = _service(
        tmp_path,
        repo,
        tool_overrides={
            "clinvar": _StaticTool(
                "clinvar",
                {
                    "classification": "Uncertain significance",
                    "review_status": "criteria provided, single submitter",
                    "accession": "VCV001421454",
                },
                raw={"variation_set": []},
            ),
            "clingen": clingen_tool,
        },
    )

    response = service.lookup(LookupRequest(gene="RPE65", cdna="c.260A>G"))

    clingen = next(item for item in response.evidence if item.source == "clingen")
    assert clingen_tool.calls == 1
    assert clingen.status == "missing"
    assert response.report_payload.report_profile is not None
    assert response.report_payload.report_profile.expert_panel is None
    assert "source_cache_identity_mismatch:clingen" in response.warnings


def test_clingen_vcep_lookup_serves_stale_cache_when_live_source_fails(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    cache_key = "clinvar:VCV001421454"
    repo.upsert(
        "clingen",
        cache_key,
        normalized_identity={"gene": "RPE65", "clinvar_accession": "VCV001421454"},
        request_identity={"cache_key": cache_key},
        status="live",
        summary=_expert_panel_summary(),
        raw={"cached": True},
        warnings=["cached_warning"],
        source_url="https://erepo.clinicalgenome.org/evrepo/api/classifications/CA189146",
        ttl_days=-1,
        source_version="ClinGen Evidence Repo cached",
    )
    clingen_tool = _StaticTool(
        "clingen",
        status="fallback",
        warnings=["live_fetch_failed:ReadTimeout"],
    )
    service = _service(
        tmp_path,
        repo,
        tool_overrides={
            "clinvar": _StaticTool(
                "clinvar",
                {
                    "classification": "Uncertain significance",
                    "review_status": "criteria provided, single submitter",
                    "accession": "VCV001421454",
                },
                raw={"variation_set": []},
            ),
            "clingen": clingen_tool,
        },
    )

    response = service.lookup(LookupRequest(gene="RPE65", cdna="c.260A>G"))

    clingen = next(item for item in response.evidence if item.source == "clingen")
    assert clingen_tool.calls == 1
    assert clingen.status == "stale"
    assert clingen.cache_status == "stale_on_failure"
    assert "source_cache_stale_on_failure:clingen" in clingen.warnings
    assert response.report_payload.report_profile is not None
    expert_panel = response.report_payload.report_profile.expert_panel
    assert expert_panel is not None
    assert expert_panel.freshness == "stale"
    assert expert_panel.freshness_reason == "stale_on_failure"


def test_arbitrary_lookup_ignores_source_cache_for_unselected_sources(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    pubmed_tool = _StaticTool(
        "pubmed",
        {
            "articles": [
                {
                    "pmid": "39999998",
                    "title": "Live arbitrary publication",
                    "authors": "Eamos",
                    "journal": "Live",
                    "year": "2026",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/39999998/",
                }
            ],
            "total": 1,
        },
    )
    repo.upsert(
        "pubmed",
        "CFTR:c.1521_1523delCTT",
        normalized_identity={"gene": "CFTR", "cdna": "c.1521_1523delCTT"},
        request_identity={"query": "cached CFTR c.1521_1523delCTT"},
        status="live",
        summary={"articles": [], "total": 0},
        raw={"cached": True},
        warnings=[],
        source_url="https://pubmed.ncbi.nlm.nih.gov/?term=CFTR+c.1521_1523delCTT",
        ttl_days=30,
    )
    service = _service(tmp_path, repo, pubmed_tool=pubmed_tool)

    response = service.lookup(LookupRequest(gene="CFTR", cdna="c.1521_1523delCTT"))

    pubmed = next(item for item in response.evidence if item.source == "pubmed")
    assert pubmed_tool.calls == 1
    assert pubmed.status == "live"
    assert pubmed.cache_status is None
    assert response.report_payload.pubmed_articles[0].title == "Live arbitrary publication"


def test_arbitrary_gnomad_no_hit_is_not_persisted_as_fresh_success(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    gnomad_tool = _StaticTool(
        "gnomad",
        {
            "gene": "CFTR",
            "variant_id": "1-68444869-T-C",
            "dataset": "gnomad_r4",
        },
        warnings=["gnomad_variant_not_found"],
    )
    service = _service(tmp_path, repo, tool_overrides={"gnomad": gnomad_tool})

    response = service.lookup(LookupRequest(gene="CFTR", cdna="c.1521_1523delCTT"))

    gnomad = next(item for item in response.evidence if item.source == "gnomad")
    assert gnomad_tool.calls == 1
    assert gnomad.status == "live"
    assert "gnomad_variant_not_found" in gnomad.warnings
    assert repo.get_any("gnomad", "gnomad:gnomad_r4:1-68444869-t-c") is None


def test_refresh_bypasses_fresh_source_cache_and_rewrites_on_success(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    pubmed_tool = _StaticTool(
        "pubmed",
        {
            "articles": [
                {
                    "pmid": "39999999",
                    "title": "Fresh live RPE65 c.11+5G>A report",
                    "authors": "Eamos",
                    "journal": "Live",
                    "year": "2026",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/39999999/",
                }
            ],
            "total": 1,
        },
    )
    repo.upsert(
        "pubmed",
        "RPE65:c.11+5G>A",
        normalized_identity={"gene": "RPE65", "cdna": "c.11+5G>A"},
        request_identity={"query": "cached RPE65 c.11+5G>A"},
        status="live",
        summary={"articles": [], "total": 0},
        raw={"cached": True},
        warnings=[],
        source_url="https://pubmed.ncbi.nlm.nih.gov/?term=RPE65+c.11%2B5G%3EA",
        ttl_days=30,
    )
    service = _service(tmp_path, repo, pubmed_tool=pubmed_tool)

    response = service.lookup(LookupRequest(gene="RPE65", cdna="c.11+5G>A"), refresh=True)

    pubmed = next(item for item in response.evidence if item.source == "pubmed")
    assert pubmed_tool.calls == 1
    assert pubmed.status == "live"
    assert pubmed.summary["articles"][0]["title"] == "Fresh live RPE65 c.11+5G>A report"
    stored = repo.get_fresh("pubmed", "RPE65:c.11+5G>A")
    assert stored is not None
    assert stored.summary["articles"][0]["title"] == "Fresh live RPE65 c.11+5G>A report"


def test_source_cache_warmer_scope_is_landing_hero_examples() -> None:
    class _Lookup:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, bool]] = []

        def lookup(self, request: LookupRequest, refresh: bool = False) -> LookupResponse:
            self.calls.append((request.gene or "", request.cdna or "", refresh))
            return LookupResponse(
                query=f"{request.gene}:{request.cdna}",
                species="human",
                report_payload=ReportPayload(patient_id="warm_test"),
                evidence=[],
                warnings=[],
            )

    lookup = _Lookup()
    results = HeroExampleSourceCacheWarmer(lookup).warm(refresh=True)

    assert lookup.calls == [(item.gene, item.cdna, True) for item in HERO_EXAMPLE_VARIANTS]
    assert [item["cache_key"] for item in results] == [
        item.cache_key for item in HERO_EXAMPLE_VARIANTS
    ]
