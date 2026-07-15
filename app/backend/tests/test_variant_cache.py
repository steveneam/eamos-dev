from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.core.db import (
    NormalizedVariantRecord,
    ReportSectionCacheRecord,
    ReportShellCacheRecord,
    SourceResultCacheRecord,
    VariantCacheRecord,
    build_session_factory,
    initialize_database,
    session_scope,
)
from app.repos.report_cache_repo import ReportCacheRepo
from app.repos.variant_cache_repo import VariantCacheRepo
from app.rules.clinic_rules import ClinicRules
from app.schemas.lookup import LookupRequest, LookupSectionFetchRequest
from app.schemas.run import (
    FunctionalEvidenceCodeRestsOn,
    FunctionalEvidenceDisplayMetrics,
    FunctionalEvidenceSourceBreakdown,
    FunctionalEvidenceSummary,
    FunctionalStudy,
    GeneContextSnapshot,
    GeneContextVariantProjection,
)
from app.schemas.protein_annotation import ProteinDomainTrack, ProteinDomainTrackFeature
from app.services.clinical_consensus import ClinicalConsensusBuilder
from app.services.gene_context_snapshot import GeneContextSnapshotService
from app.services.lookup_service import (
    FUNCTIONAL_EVIDENCE_CACHE_VERSION,
    GENE_CONTEXT_SNAPSHOT_CACHE_VERSION,
    LEGACY_REPORT_SECTIONS_CACHE_READ_WARNING,
    LEGACY_REPORT_SHELL_CACHE_READ_WARNING,
    PUBLICATION_DATA_CACHE_VERSION,
    REPORT_SECTION_CACHE_VERSION,
    REPORT_SHELL_CACHE_VERSION,
    SOURCE_RESULT_CACHE_VERSION,
    STRICT_GENOMIC_CACHE_VERSION,
    LookupService,
)
from app.services.search_input_resolver import EamosSearchInputResolver
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
    with session_scope(session_factory) as session:
        assert session.execute(select(VariantCacheRecord)).scalar_one().query_string == (
            "RPE65:c.260A>G"
        )


class _StaticTool:
    def __init__(self, source: str, summary: dict | None = None, raw=None) -> None:
        self.source = source
        self.summary = summary or {}
        self.raw = raw
        self.calls = 0

    def get_evidence(self, variant=None, **_kwargs) -> ToolResult:
        self.calls += 1
        return ToolResult(
            source=self.source,
            status="live",
            request_identity={},
            summary=self.summary,
            raw=self.raw,
        )


class _MutatingVariantValidatorTool(_StaticTool):
    def get_evidence(self, variant=None, **_kwargs) -> ToolResult:
        result = super().get_evidence(variant=variant)
        if variant is not None:
            variant.genomic_hg38 = "1-68444869-T-C"
            variant.variation_type = "single nucleotide variant"
            variant.consequence = "missense variant"
        return result


def _cached_evidence(source: str, summary: dict | None = None) -> dict:
    return {
        "source": source,
        "status": "live",
        "request_identity": {},
        "summary": summary or {},
        "warnings": [],
        "raw": None,
        "source_url": None,
    }


class _ClinicalTrialsTool:
    def get_trials_summary(self, gene: str) -> str:
        return ""


class _CountingClinicalTrialsTool:
    def __init__(self, summary: dict | None = None, status: str = "live") -> None:
        self.summary = summary or {
            "trial_rows": [],
            "query_executions": [
                {
                    "query_id": "gene_term:rpe65",
                    "lane": "gene_term",
                    "query_term": "RPE65",
                    "params": {"query.term": "RPE65"},
                    "status": "ok",
                    "result_count": 0,
                }
            ],
            "warnings": ["clinical_trials_no_active_matches"],
            "query_term": "RPE65",
            "source_url": "https://clinicaltrials.gov/search?term=RPE65",
        }
        self.status = status
        self.calls = 0
        self.summary_calls = 0

    def get_trial_matches(self, *args, **kwargs) -> ToolResult:
        self.calls += 1
        return ToolResult(
            source="clinical_trials",
            status=self.status,
            request_identity={"gene": kwargs.get("gene")},
            summary=self.summary,
            warnings=list(self.summary.get("warnings", [])),
            raw=None,
            source_url=self.summary.get("source_url"),
        )

    def get_trials_summary(self, gene: str) -> str:
        self.summary_calls += 1
        return ""


class _NoopFunctionalEvidenceExtractor:
    def __init__(self, summary: FunctionalEvidenceSummary | None = None) -> None:
        self.calls = 0
        self.summary = summary or FunctionalEvidenceSummary(total_count=0)

    def build_for_lookup(self, *args, **kwargs) -> FunctionalEvidenceSummary:
        self.calls += 1
        return self.summary


def _hermetic_lookup_service(tool_registry, rule_engine, **kwargs) -> LookupService:
    """Exercise live-cache behavior without coordinate-provider requests."""
    kwargs.setdefault("clinical_consensus_builder", ClinicalConsensusBuilder(settings=None))
    kwargs.setdefault("gene_context_snapshot", GeneContextSnapshotService(settings=None))
    service = LookupService(tool_registry, rule_engine, **kwargs)
    service.search_input_resolver = EamosSearchInputResolver(
        settings=kwargs.get("settings"),
        resolve_coordinates=False,
    )
    return service


def _report_cache_identity(query: str) -> dict:
    gene, _, cdna = query.partition(":")
    return {
        "identity_version": 1,
        "query_string": query,
        "species": "human",
        "genome_build": "GRCh38",
        "gene": gene or None,
        "cdna": cdna or None,
        "request_identity": {"query": query},
    }


def _seed_no_active_trials_snapshot(report_repo: ReportCacheRepo, query: str) -> None:
    report_repo.upsert_source_result(
        query,
        normalized_identity=_report_cache_identity(query),
        source_id="clinical_trials",
        schema_version=SOURCE_RESULT_CACHE_VERSION,
        status="live",
        payload={
            "trial_rows": [],
            "query_executions": [
                {
                    "query_id": "gene_term:rpe65",
                    "lane": "gene_term",
                    "query_term": "RPE65",
                    "params": {"query.term": "RPE65"},
                    "status": "ok",
                    "result_count": 0,
                }
            ],
            "warnings": ["clinical_trials_no_active_matches"],
            "query_term": "RPE65",
            "source_url": "https://clinicaltrials.gov/search?term=RPE65",
        },
        raw=None,
        warnings=["clinical_trials_no_active_matches"],
        ttl_days=30,
        freshness={
            "source_status": "live",
            "source_url": "https://clinicaltrials.gov/search?term=RPE65",
            "source_version": "clinicaltrials-v2-snapshot",
        },
        source_versions={"source_version": "clinicaltrials-v2-snapshot"},
    )


class _CountingGeneContextSnapshotService:
    def __init__(self) -> None:
        self.calls = 0

    def build(
        self,
        *,
        gene: str,
        cdna: str,
        transcript: str | None = None,
        species: str = "human",
    ) -> GeneContextSnapshot:
        self.calls += 1
        return GeneContextSnapshot(
            source_status="live",
            gene=gene,
            transcript=transcript,
            variant=GeneContextVariantProjection(hgvs_c=cdna, membership="exon"),
            protein_domain_track=ProteinDomainTrack(
                status="cache_hit",
                gene_symbol=gene,
                protein_length=533,
                features=[
                    ProteinDomainTrackFeature(
                        feature_id="pfam-fn3",
                        kind="domain",
                        label="Fibronectin type III",
                        aa_start=20,
                        aa_end=90,
                        source="pfam",
                    )
                ],
            ),
            warnings=[f"snapshot_build_species:{species}"],
        )


@pytest.mark.slow
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
                "scholar_url": "https://scholar.google.com/scholar?q=RPE65+c.9999A%3EG",
            },
        ),
        "clinical_trials": _ClinicalTrialsTool(),
    }
    functional_evidence = _NoopFunctionalEvidenceExtractor()
    service = _hermetic_lookup_service(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        settings=settings,
        functional_evidence_extractor=functional_evidence,
    )
    request = LookupRequest(gene="RPE65", cdna="c.9999A>G")

    first = service.lookup(request)
    second = service.lookup(request)

    assert first.report_payload.variant_summary_rows[0].genomic_hg38 is None
    assert second.report_payload.variant_summary_rows[0].genomic_hg38 is None
    assert vep_tool.calls == 2
    assert all(item.status != "cache" for item in second.evidence)
    assert repo.get_fresh("RPE65:c.9999A>G", ttl_days=30) is None
    with session_scope(session_factory) as session:
        assert session.execute(select(VariantCacheRecord)).scalars().all() == []


@pytest.mark.slow
def test_resolved_lookup_reuses_cached_publication_data(tmp_path: Path) -> None:
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
    pubmed_tool = _StaticTool(
        "pubmed",
        {
            "articles": [
                {
                    "pmid": "38191234",
                    "title": "RPE65 c.260A>G report.",
                    "authors": "Walia S et al.",
                    "journal": "Ophthalmology",
                    "year": "2024",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/38191234/",
                    "abstract": "The c.260A>G variant was recurrent.",
                }
            ],
            "total": 1,
        },
    )
    litvar_tool = _StaticTool(
        "litvar2",
        {
            "litvar_id": "litvar-rpe65-c260ag",
            "total_publications": 1,
            "articles": [{"pmid": "38191234"}],
            "scholar_url": "https://scholar.google.com/scholar?q=RPE65+c.260A%3EG",
        },
    )
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
        ),
        "pubmed": pubmed_tool,
        "litvar2": litvar_tool,
        "clinical_trials": _ClinicalTrialsTool(),
    }
    functional_evidence = _NoopFunctionalEvidenceExtractor(
        FunctionalEvidenceSummary(
            total_count=1,
            source_breakdown=FunctionalEvidenceSourceBreakdown(clingen=1),
            evidence_codes=["PS3"],
            source_asserted_codes=["PS3_Supporting"],
            display_metrics=FunctionalEvidenceDisplayMetrics(
                state="emerging_deficit",
                primary_label="Functional Deficit",
                acmg_badge_text="PS3_Supporting",
                verdict_source="clingen",
                study_count_badge_text="1 Unique",
                ui_color_theme="risk_red_state",
            ),
            studies=[
                FunctionalStudy(
                    id="functional-study-1",
                    citation="Guan et al., 2024",
                    source_tags=["clingen"],
                    evidence_codes=["PS3"],
                    asserted_codes=["PS3_Supporting"],
                )
            ],
        )
    )
    service = _hermetic_lookup_service(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        settings=settings,
        functional_evidence_extractor=functional_evidence,
    )
    request = LookupRequest(gene="RPE65", cdna="c.260A>G")

    first = service.lookup(request)
    second = service.lookup(request)

    assert first.report_payload.publications_literature is not None
    assert second.report_payload.publications_literature is not None
    assert second.report_payload.publications_literature.total_count == 1
    assert second.report_payload.publications_literature.scope_counts is not None
    assert second.report_payload.publications_literature.scope_counts.variant.total_count == 1
    assert (
        second.report_payload.publications_literature.scope_counts.variant.count_kind
        == "deduped_pmids"
    )
    assert second.report_payload.publications_literature.scope_counts.gene.total_count is None
    assert second.report_payload.publications_literature.scope_counts.gene.count_kind == (
        "unavailable"
    )
    assert "gene_scope_count_unavailable:source_count_missing" in (
        second.report_payload.publications_literature.scope_counts.gene.warnings
    )
    assert second.report_payload.publications_callout is not None
    assert second.report_payload.publications_callout.scope_counts == (
        second.report_payload.publications_literature.scope_counts
    )
    assert second.report_payload.functional_evidence is not None
    assert second.report_payload.functional_evidence.total_count == 1
    assert second.report_payload.functional_evidence.display_metrics.primary_label == (
        "Functional Deficit"
    )
    assert second.report_payload.functional_evidence.display_metrics.acmg_badge_text == (
        "PS3_Supporting"
    )
    assert second.report_payload.functional_evidence.studies[0].citation == "Guan et al., 2024"
    assert pubmed_tool.calls == 1
    assert litvar_tool.calls == 1
    assert functional_evidence.calls == 1
    assert {item.source: item.status for item in second.evidence}["pubmed"] == "cache"
    assert {item.source: item.status for item in second.evidence}["litvar2"] == "cache"
    hit = repo.get_fresh("RPE65:c.260A>G", ttl_days=30)
    assert hit is not None
    assert hit["publication_data"]["ep_vlex"]["total_count"] == 1
    assert hit["publication_data"]["ep_vlex"]["scope_counts"]["variant"]["total_count"] == 1
    assert hit["publication_data"]["ep_vlex"]["scope_counts"]["gene"]["total_count"] is None
    assert hit["publication_data"]["ep_vlex"]["scope_counts"]["gene"]["count_kind"] == (
        "unavailable"
    )
    assert (
        hit["publication_data"]["publication_data_cache_version"] == PUBLICATION_DATA_CACHE_VERSION
    )
    assert (
        hit["publication_data"]["functional_evidence_cache_version"]
        == FUNCTIONAL_EVIDENCE_CACHE_VERSION
    )
    assert hit["publication_data"]["functional_evidence"]["total_count"] == 1


@pytest.mark.slow
def test_resolved_lookup_reuses_cached_gene_context_snapshot(tmp_path: Path) -> None:
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
    gene_context_snapshot = _CountingGeneContextSnapshotService()
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
        ),
        "pubmed": _StaticTool("pubmed", {"articles": [], "total": 0}),
        "litvar2": _StaticTool("litvar2", {"articles": [], "total_publications": 0}),
        "clinical_trials": _ClinicalTrialsTool(),
    }
    service = _hermetic_lookup_service(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        settings=settings,
        functional_evidence_extractor=_NoopFunctionalEvidenceExtractor(),
        gene_context_snapshot=gene_context_snapshot,
    )

    first = service.lookup(LookupRequest(gene="RPE65", cdna="c.260A>G"))
    second = service.lookup(LookupRequest(gene="RPE65", cdna="c.260A>G"))

    assert gene_context_snapshot.calls == 1
    assert first.report_payload.report_profile is not None
    assert second.report_payload.report_profile is not None
    first_snapshot = first.report_payload.report_profile.gene_context_snapshot
    second_snapshot = second.report_payload.report_profile.gene_context_snapshot
    assert first_snapshot is not None
    assert second_snapshot is not None
    assert second_snapshot.protein_domain_track is not None
    assert second_snapshot.protein_domain_track.status == "cache_hit"
    assert second_snapshot.protein_domain_track.features[0].label == "Fibronectin type III"

    hit = repo.get_fresh("RPE65:c.260A>G", ttl_days=30)
    assert hit is not None
    cached_snapshot = hit["gene_context_snapshot"]
    assert (
        cached_snapshot["gene_context_snapshot_cache_version"]
        == GENE_CONTEXT_SNAPSHOT_CACHE_VERSION
    )
    assert cached_snapshot["snapshot"]["protein_domain_track"]["features"][0]["label"] == (
        "Fibronectin type III"
    )


@pytest.mark.slow
def test_lookup_summary_reuses_prepared_report_shell_without_provider_calls(
    tmp_path: Path,
) -> None:
    session_factory = build_session_factory(
        f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}"
    )
    initialize_database(session_factory)
    repo = VariantCacheRepo(session_factory)
    report_repo = ReportCacheRepo(session_factory)
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}",
        jwt_secret="test-secret",
        use_real_apis=True,
    )
    tools = {
        "vep": _StaticTool("vep", {"most_severe_consequence": "missense_variant"}),
        "variant_validator": _MutatingVariantValidatorTool("variant_validator"),
        "gnomad": _StaticTool(
            "gnomad",
            {
                "dataset": "gnomAD v4.1",
                "allele_frequency": 0.0000159,
                "allele_count": 2,
                "allele_number": 125000,
            },
        ),
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
        ),
        "pubmed": _StaticTool("pubmed", {"articles": [], "total": 0}),
        "litvar2": _StaticTool(
            "litvar2",
            {
                "litvar_id": "litvar-rpe65-c260ag",
                "total_publications": 0,
                "articles": [],
            },
        ),
        "clinical_trials": _ClinicalTrialsTool(),
    }
    service = _hermetic_lookup_service(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        report_cache_repo=report_repo,
        settings=settings,
        functional_evidence_extractor=_NoopFunctionalEvidenceExtractor(),
    )
    request = LookupRequest(gene="RPE65", cdna="c.260A>G")

    service.lookup(request)
    hit = repo.get_fresh("RPE65:c.260A>G", ttl_days=30)
    assert hit is not None
    assert "report_shell" not in hit["publication_data"]
    with session_scope(session_factory) as session:
        assert session.execute(select(NormalizedVariantRecord)).scalars().all()
        assert session.execute(select(ReportShellCacheRecord)).scalar_one().query_string == (
            "RPE65:c.260A>G"
        )
    calls_before = {
        name: tool.calls for name, tool in tools.items() if isinstance(tool, _StaticTool)
    }

    summary = service.lookup_summary(request)

    calls_after = {
        name: tool.calls for name, tool in tools.items() if isinstance(tool, _StaticTool)
    }
    assert calls_after == calls_before
    assert summary.query == "RPE65:c.260A>G"
    assert summary.header is not None
    assert summary.header["gene"] == "RPE65"
    assert summary.header["cdna"] == "c.260A>G"
    assert {tile.tile_id for tile in summary.tiles} == {
        "population_frequency",
        "computational",
        "lab_functional",
        "clinical_consensus",
    }
    assert [section.section_id for section in summary.lazy_sections] == [
        "publications",
        "therapies_trials",
        "computational_deep_dive",
        "clingen_vcep",
    ]


def test_lookup_summary_reads_legacy_publication_data_shell_when_table_repo_missing(
    tmp_path: Path,
) -> None:
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
    repo.upsert(
        "RPE65:c.260A>G",
        litvar_id="litvar-rpe65-c260ag",
        total_publications=0,
        publication_data={"publication_data_cache_version": PUBLICATION_DATA_CACHE_VERSION},
        strict_genomic_cache={"variant": {"genomic_hg38": "1-68444869-T-C"}},
    )
    repo.update_report_shell(
        "RPE65:c.260A>G",
        report_shell={
            "report_shell_cache_version": REPORT_SHELL_CACHE_VERSION,
            "summary": {
                "query": "RPE65:c.260A>G",
                "species": "human",
                "header": {"gene": "RPE65", "cdna": "c.260A>G"},
                "tiles": [],
                "lazy_sections": [],
                "warnings": ["legacy_fixture_summary"],
            },
        },
    )
    service = _hermetic_lookup_service(
        {},
        ClinicRules(),
        variant_cache_repo=repo,
        settings=settings,
    )

    summary = service.lookup_summary(LookupRequest(gene="RPE65", cdna="c.260A>G"))

    assert summary.query == "RPE65:c.260A>G"
    assert summary.header == {"gene": "RPE65", "cdna": "c.260A>G"}
    assert summary.warnings == [
        "legacy_fixture_summary",
        LEGACY_REPORT_SHELL_CACHE_READ_WARNING,
    ]


@pytest.mark.slow
def test_lookup_sections_reuses_prepared_envelopes_without_provider_calls(
    tmp_path: Path,
) -> None:
    session_factory = build_session_factory(
        f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}"
    )
    initialize_database(session_factory)
    repo = VariantCacheRepo(session_factory)
    report_repo = ReportCacheRepo(session_factory)
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}",
        jwt_secret="test-secret",
        use_real_apis=True,
    )
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
        ),
        "pubmed": _StaticTool("pubmed", {"articles": [], "total": 0}),
        "litvar2": _StaticTool(
            "litvar2",
            {
                "litvar_id": "litvar-rpe65-c260ag",
                "total_publications": 0,
                "articles": [],
            },
        ),
        "clinical_trials": _ClinicalTrialsTool(),
    }
    service = _hermetic_lookup_service(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        report_cache_repo=report_repo,
        settings=settings,
        functional_evidence_extractor=_NoopFunctionalEvidenceExtractor(),
    )

    service.lookup(LookupRequest(gene="RPE65", cdna="c.260A>G"))
    hit = repo.get_fresh("RPE65:c.260A>G", ttl_days=30)
    assert hit is not None
    assert "report_sections" not in hit["publication_data"]
    with session_scope(session_factory) as session:
        table_sections = session.execute(select(ReportSectionCacheRecord)).scalars().all()
        assert {row.section_id for row in table_sections} >= {
            "publications",
            "therapies_trials",
            "computational_deep_dive",
            "clingen_vcep",
        }
    calls_before = {
        name: tool.calls for name, tool in tools.items() if isinstance(tool, _StaticTool)
    }

    sections = service.lookup_sections(
        LookupSectionFetchRequest(
            gene="RPE65",
            cdna="c.260A>G",
            include=["publications"],
        )
    )

    calls_after = {
        name: tool.calls for name, tool in tools.items() if isinstance(tool, _StaticTool)
    }
    assert calls_after == calls_before
    assert sections.query == "RPE65:c.260A>G"
    assert set(sections.sections) == {"publications"}
    assert sections.sections["publications"].section_id == "publications"


def test_lookup_sections_reads_legacy_publication_data_sections_when_table_repo_missing(
    tmp_path: Path,
) -> None:
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
    repo.upsert(
        "RPE65:c.260A>G",
        litvar_id="litvar-rpe65-c260ag",
        total_publications=0,
        publication_data={"publication_data_cache_version": PUBLICATION_DATA_CACHE_VERSION},
        strict_genomic_cache={"variant": {"genomic_hg38": "1-68444869-T-C"}},
    )
    repo.update_report_sections(
        "RPE65:c.260A>G",
        report_sections={
            "report_section_cache_version": REPORT_SECTION_CACHE_VERSION,
            "response": {
                "query": "RPE65:c.260A>G",
                "species": "human",
                "sections": {
                    "publications": {
                        "section_id": "publications",
                        "status": "missing",
                        "payload": None,
                        "freshness": {},
                        "warnings": ["legacy_publications_missing"],
                    },
                },
                "warnings": ["legacy_fixture_sections"],
            },
        },
    )
    service = _hermetic_lookup_service(
        {},
        ClinicRules(),
        variant_cache_repo=repo,
        settings=settings,
    )

    sections = service.lookup_sections(
        LookupSectionFetchRequest(
            gene="RPE65",
            cdna="c.260A>G",
            include=["publications"],
        )
    )

    assert set(sections.sections) == {"publications"}
    assert sections.sections["publications"].warnings == ["legacy_publications_missing"]
    assert sections.warnings == [
        "legacy_fixture_sections",
        LEGACY_REPORT_SECTIONS_CACHE_READ_WARNING,
    ]


@pytest.mark.slow
def test_lookup_sections_publication_miss_builds_only_publication_sources(
    tmp_path: Path,
) -> None:
    session_factory = build_session_factory(
        f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}"
    )
    initialize_database(session_factory)
    repo = VariantCacheRepo(session_factory)
    report_repo = ReportCacheRepo(session_factory)
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}",
        jwt_secret="test-secret",
        use_real_apis=True,
    )
    trial_tool = _CountingClinicalTrialsTool()
    tools = {
        "vep": _StaticTool("vep", {"most_severe_consequence": "missense_variant"}),
        "variant_validator": _MutatingVariantValidatorTool("variant_validator"),
        "gnomad": _StaticTool("gnomad"),
        "spliceai": _StaticTool("spliceai"),
        "clinvar": _StaticTool(
            "clinvar",
            {
                "classification": "Uncertain significance",
                "review_status": "criteria provided, single submitter",
            },
        ),
        "pubmed": _StaticTool("pubmed", {"articles": [], "total": 0}),
        "litvar2": _StaticTool(
            "litvar2",
            {
                "litvar_id": "litvar-rpe65-c260ag",
                "total_publications": 0,
                "articles": [],
            },
        ),
        "clinical_trials": trial_tool,
    }
    service = _hermetic_lookup_service(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        report_cache_repo=report_repo,
        settings=settings,
        functional_evidence_extractor=_NoopFunctionalEvidenceExtractor(),
    )

    sections = service.lookup_sections(
        LookupSectionFetchRequest(
            gene="RPE65",
            cdna="c.260A>G",
            include=["publications"],
        )
    )

    assert tools["vep"].calls == 0
    assert tools["variant_validator"].calls == 0
    assert tools["gnomad"].calls == 0
    assert tools["spliceai"].calls == 0
    assert tools["clinvar"].calls == 1
    assert tools["pubmed"].calls == 1
    assert tools["litvar2"].calls == 1
    assert trial_tool.calls == 0
    assert set(sections.sections) == {"publications"}
    assert sections.sections["publications"].status == "available"
    assert sections.sections["publications"].payload is not None
    with session_scope(session_factory) as session:
        source_rows = session.execute(select(SourceResultCacheRecord)).scalars().all()
        assert {row.source_id for row in source_rows} == {"clinvar", "pubmed", "litvar2"}
        assert session.execute(select(ReportSectionCacheRecord)).scalar_one().section_id == (
            "publications"
        )


@pytest.mark.slow
def test_lookup_sections_trials_miss_builds_only_trials_source(
    tmp_path: Path,
) -> None:
    session_factory = build_session_factory(
        f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}"
    )
    initialize_database(session_factory)
    repo = VariantCacheRepo(session_factory)
    report_repo = ReportCacheRepo(session_factory)
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}",
        jwt_secret="test-secret",
        use_real_apis=True,
    )
    trial_tool = _CountingClinicalTrialsTool()
    tools = {
        "vep": _StaticTool("vep", {"most_severe_consequence": "missense_variant"}),
        "variant_validator": _MutatingVariantValidatorTool("variant_validator"),
        "gnomad": _StaticTool("gnomad"),
        "spliceai": _StaticTool("spliceai"),
        "clinvar": _StaticTool("clinvar"),
        "pubmed": _StaticTool("pubmed", {"articles": [], "total": 0}),
        "litvar2": _StaticTool("litvar2", {"articles": [], "total_publications": 0}),
        "clinical_trials": trial_tool,
    }
    service = _hermetic_lookup_service(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        report_cache_repo=report_repo,
        settings=settings,
        functional_evidence_extractor=_NoopFunctionalEvidenceExtractor(),
    )

    sections = service.lookup_sections(
        LookupSectionFetchRequest(
            gene="RPE65",
            cdna="c.260A>G",
            include=["therapies_trials"],
        )
    )

    assert tools["vep"].calls == 0
    assert tools["variant_validator"].calls == 0
    assert tools["gnomad"].calls == 0
    assert tools["spliceai"].calls == 0
    assert tools["clinvar"].calls == 0
    assert tools["pubmed"].calls == 0
    assert tools["litvar2"].calls == 0
    assert trial_tool.calls == 1
    assert set(sections.sections) == {"therapies_trials"}
    trials = sections.sections["therapies_trials"]
    assert trials.status == "available"
    assert trials.payload is not None
    assert trials.payload["query_executions"][0]["query_id"] == "gene_term:rpe65"
    with session_scope(session_factory) as session:
        source_rows = session.execute(select(SourceResultCacheRecord)).scalars().all()
        assert [row.source_id for row in source_rows] == ["clinical_trials"]
        assert session.execute(select(ReportSectionCacheRecord)).scalar_one().section_id == (
            "therapies_trials"
        )


@pytest.mark.slow
def test_lookup_sections_trials_uses_cached_snapshot_without_provider_calls(
    tmp_path: Path,
) -> None:
    session_factory = build_session_factory(
        f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}"
    )
    initialize_database(session_factory)
    repo = VariantCacheRepo(session_factory)
    report_repo = ReportCacheRepo(session_factory)
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}",
        jwt_secret="test-secret",
        use_real_apis=True,
    )
    query = "RPE65:c.260A>G"
    _seed_no_active_trials_snapshot(report_repo, query)
    trial_tool = _CountingClinicalTrialsTool()
    tools = {
        "vep": _StaticTool("vep"),
        "variant_validator": _MutatingVariantValidatorTool("variant_validator"),
        "gnomad": _StaticTool("gnomad"),
        "spliceai": _StaticTool("spliceai"),
        "clinvar": _StaticTool("clinvar"),
        "pubmed": _StaticTool("pubmed"),
        "litvar2": _StaticTool("litvar2"),
        "clinical_trials": trial_tool,
    }
    service = _hermetic_lookup_service(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        report_cache_repo=report_repo,
        settings=settings,
        functional_evidence_extractor=_NoopFunctionalEvidenceExtractor(),
    )

    sections = service.lookup_sections(
        LookupSectionFetchRequest(
            gene="RPE65",
            cdna="c.260A>G",
            include=["therapies_trials"],
        )
    )

    assert trial_tool.calls == 0
    assert trial_tool.summary_calls == 0
    trials = sections.sections["therapies_trials"]
    assert trials.status == "available"
    assert trials.payload is not None
    assert trials.payload["trial_rows"] == []
    assert trials.payload["query_executions"][0]["query_id"] == "gene_term:rpe65"
    assert trials.freshness.source_status == "cache"
    assert trials.freshness.source_version == "clinicaltrials-v2-snapshot"
    with session_scope(session_factory) as session:
        source_rows = session.execute(select(SourceResultCacheRecord)).scalars().all()
        assert [row.source_id for row in source_rows] == ["clinical_trials"]
        assert session.execute(select(ReportSectionCacheRecord)).scalar_one().section_id == (
            "therapies_trials"
        )


@pytest.mark.slow
def test_lookup_report_uses_cached_trials_snapshot_on_first_payload(
    tmp_path: Path,
) -> None:
    session_factory = build_session_factory(
        f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}"
    )
    initialize_database(session_factory)
    repo = VariantCacheRepo(session_factory)
    report_repo = ReportCacheRepo(session_factory)
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}",
        jwt_secret="test-secret",
        use_real_apis=True,
    )
    query = "RPE65:c.260A>G"
    _seed_no_active_trials_snapshot(report_repo, query)
    trial_tool = _CountingClinicalTrialsTool()
    tools = {
        "vep": _StaticTool("vep", {"most_severe_consequence": "missense_variant"}),
        "variant_validator": _MutatingVariantValidatorTool("variant_validator"),
        "gnomad": _StaticTool("gnomad"),
        "spliceai": _StaticTool("spliceai"),
        "clinvar": _StaticTool(
            "clinvar",
            {
                "classification": "Uncertain significance",
                "review_status": "criteria provided, single submitter",
            },
        ),
        "pubmed": _StaticTool("pubmed", {"articles": [], "total": 0}),
        "litvar2": _StaticTool("litvar2", {"articles": [], "total_publications": 0}),
        "clinical_trials": trial_tool,
    }
    service = _hermetic_lookup_service(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        report_cache_repo=report_repo,
        settings=settings,
        functional_evidence_extractor=_NoopFunctionalEvidenceExtractor(),
    )

    response = service.lookup(LookupRequest(gene="RPE65", cdna="c.260A>G"))

    assert trial_tool.calls == 0
    assert trial_tool.summary_calls == 0
    trials = response.report_payload.report_profile.therapies_trials
    assert trials is not None
    assert trials.trial_rows == []
    assert trials.query_executions[0].query_id == "gene_term:rpe65"
    assert trials.provenance[0].status == "cache"
    assert "No active trials found for RPE65 on ClinicalTrials.gov." in (
        response.report_payload.therapeutic_landscape or ""
    )


@pytest.mark.slow
def test_lookup_sections_computational_miss_uses_source_result_cache_without_provider_calls(
    tmp_path: Path,
) -> None:
    session_factory = build_session_factory(
        f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}"
    )
    initialize_database(session_factory)
    repo = VariantCacheRepo(session_factory)
    report_repo = ReportCacheRepo(session_factory)
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}",
        jwt_secret="test-secret",
        use_real_apis=True,
    )
    query = "RPE65:c.260A>G"
    report_repo.upsert_source_result(
        query,
        normalized_identity=_report_cache_identity(query),
        source_id="computational_annotations",
        schema_version=SOURCE_RESULT_CACHE_VERSION,
        status="live",
        payload={
            "predictors": [
                {
                    "name": "REVEL",
                    "score": 0.82,
                    "source": "REVEL",
                }
            ],
            "spliceai": {"max_delta": 0.12, "consequence": "acceptor_loss"},
            "conservation": [],
            "warnings": [],
        },
        raw=None,
        warnings=[],
        ttl_days=30,
        freshness={"source_status": "live", "source_version": "fixture-v1"},
        source_versions={"source_version": "fixture-v1"},
    )
    tools = {
        "vep": _StaticTool("vep"),
        "variant_validator": _MutatingVariantValidatorTool("variant_validator"),
        "gnomad": _StaticTool("gnomad"),
        "spliceai": _StaticTool("spliceai"),
        "clinvar": _StaticTool("clinvar"),
        "clingen": _StaticTool("clingen"),
        "pubmed": _StaticTool("pubmed"),
        "litvar2": _StaticTool("litvar2"),
        "clinical_trials": _CountingClinicalTrialsTool(),
        "computational_annotations": _StaticTool(
            "computational_annotations",
            {"predictors": [{"name": "CADD PHRED", "score": 12.0}]},
        ),
    }
    service = _hermetic_lookup_service(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        report_cache_repo=report_repo,
        settings=settings,
        functional_evidence_extractor=_NoopFunctionalEvidenceExtractor(),
    )

    sections = service.lookup_sections(
        LookupSectionFetchRequest(
            gene="RPE65",
            cdna="c.260A>G",
            include=["computational_deep_dive"],
        )
    )

    assert {name: tool.calls for name, tool in tools.items() if isinstance(tool, _StaticTool)} == {
        "vep": 0,
        "variant_validator": 0,
        "gnomad": 0,
        "spliceai": 0,
        "clinvar": 0,
        "clingen": 0,
        "pubmed": 0,
        "litvar2": 0,
        "computational_annotations": 0,
    }
    assert tools["clinical_trials"].calls == 0
    section = sections.sections["computational_deep_dive"]
    assert section.status == "available"
    assert section.payload is not None
    assert section.payload["predictors"][0]["name"] == "REVEL"
    assert section.freshness.source_status == "cache"
    with session_scope(session_factory) as session:
        assert session.execute(select(ReportSectionCacheRecord)).scalar_one().section_id == (
            "computational_deep_dive"
        )


@pytest.mark.slow
def test_lookup_sections_computational_miss_builds_only_computational_source(
    tmp_path: Path,
) -> None:
    session_factory = build_session_factory(
        f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}"
    )
    initialize_database(session_factory)
    repo = VariantCacheRepo(session_factory)
    report_repo = ReportCacheRepo(session_factory)
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}",
        jwt_secret="test-secret",
        use_real_apis=True,
    )
    tools = {
        "vep": _StaticTool("vep"),
        "variant_validator": _MutatingVariantValidatorTool("variant_validator"),
        "gnomad": _StaticTool("gnomad"),
        "spliceai": _StaticTool("spliceai"),
        "clinvar": _StaticTool("clinvar"),
        "clingen": _StaticTool("clingen"),
        "pubmed": _StaticTool("pubmed"),
        "litvar2": _StaticTool("litvar2"),
        "clinical_trials": _CountingClinicalTrialsTool(),
        "computational_annotations": _StaticTool(
            "computational_annotations",
            {
                "predictors": [
                    {
                        "name": "CADD PHRED",
                        "score": 14.2,
                        "source": "CADD",
                    }
                ],
                "spliceai": {"max_delta": 0.01, "consequence": "donor_loss"},
                "conservation": [],
                "warnings": [],
            },
        ),
    }
    service = _hermetic_lookup_service(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        report_cache_repo=report_repo,
        settings=settings,
        functional_evidence_extractor=_NoopFunctionalEvidenceExtractor(),
    )

    sections = service.lookup_sections(
        LookupSectionFetchRequest(
            gene="RPE65",
            cdna="c.260A>G",
            include=["computational_deep_dive"],
        )
    )

    assert tools["computational_annotations"].calls == 1
    assert tools["vep"].calls == 0
    assert tools["variant_validator"].calls == 0
    assert tools["gnomad"].calls == 0
    assert tools["spliceai"].calls == 0
    assert tools["clinvar"].calls == 0
    assert tools["clingen"].calls == 0
    assert tools["pubmed"].calls == 0
    assert tools["litvar2"].calls == 0
    assert tools["clinical_trials"].calls == 0
    section = sections.sections["computational_deep_dive"]
    assert section.status == "available"
    assert section.payload is not None
    assert section.payload["predictors"][0]["name"] == "CADD PHRED"
    with session_scope(session_factory) as session:
        source_rows = session.execute(select(SourceResultCacheRecord)).scalars().all()
        assert {row.source_id for row in source_rows} == {"computational_annotations"}
        assert session.execute(select(ReportSectionCacheRecord)).scalar_one().section_id == (
            "computational_deep_dive"
        )


@pytest.mark.slow
def test_lookup_sections_clingen_miss_builds_only_clinvar_and_clingen_sources(
    tmp_path: Path,
) -> None:
    session_factory = build_session_factory(
        f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}"
    )
    initialize_database(session_factory)
    repo = VariantCacheRepo(session_factory)
    report_repo = ReportCacheRepo(session_factory)
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}",
        jwt_secret="test-secret",
        use_real_apis=True,
    )
    tools = {
        "vep": _StaticTool("vep"),
        "variant_validator": _MutatingVariantValidatorTool("variant_validator"),
        "gnomad": _StaticTool("gnomad"),
        "spliceai": _StaticTool("spliceai"),
        "clinvar": _StaticTool(
            "clinvar",
            {
                "classification": "Uncertain significance",
                "review_status": "criteria provided, single submitter",
            },
        ),
        "clingen": _StaticTool("clingen"),
        "pubmed": _StaticTool("pubmed"),
        "litvar2": _StaticTool("litvar2"),
        "clinical_trials": _CountingClinicalTrialsTool(),
        "computational_annotations": _StaticTool("computational_annotations"),
    }
    service = _hermetic_lookup_service(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        report_cache_repo=report_repo,
        settings=settings,
        functional_evidence_extractor=_NoopFunctionalEvidenceExtractor(),
    )

    sections = service.lookup_sections(
        LookupSectionFetchRequest(
            gene="RPE65",
            cdna="c.260A>G",
            include=["clingen_vcep"],
        )
    )

    assert tools["clinvar"].calls == 1
    assert tools["clingen"].calls == 1
    assert tools["vep"].calls == 0
    assert tools["variant_validator"].calls == 0
    assert tools["gnomad"].calls == 0
    assert tools["spliceai"].calls == 0
    assert tools["pubmed"].calls == 0
    assert tools["litvar2"].calls == 0
    assert tools["computational_annotations"].calls == 0
    assert tools["clinical_trials"].calls == 0
    section = sections.sections["clingen_vcep"]
    assert section.status == "partial"
    assert section.payload is not None
    assert section.payload["classification"] == "Uncertain significance"
    assert section.payload["classification_source"] == "ClinVar"
    assert section.payload["source_scope"] == "current_clinical_consensus_snapshot"
    assert section.warnings == ["clingen_vcep_evidence_repo_source_cache_not_integrated"]
    with session_scope(session_factory) as session:
        source_rows = session.execute(select(SourceResultCacheRecord)).scalars().all()
        assert {row.source_id for row in source_rows} == {"clinvar", "clingen"}
        assert session.execute(select(ReportSectionCacheRecord)).scalar_one().section_id == (
            "clingen_vcep"
        )


@pytest.mark.slow
def test_legacy_cached_functional_evidence_rebuilds_and_refreshes_cache(
    tmp_path: Path,
) -> None:
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
    repo.upsert(
        "RPE65:c.260A>G",
        litvar_id="litvar-rpe65-c260ag",
        total_publications=1,
        publication_data={
            "functional_evidence": {
                "total_count": 3,
                "source_breakdown": {"clingen": 0, "clinvar": 1, "pubmed": 2},
                "evidence_codes": ["PS3"],
                "source_asserted_codes": ["PS3_Supporting"],
                "display_metrics": {
                    "primary_label": "Functional Deficit",
                    "acmg_badge_text": "PS3_Supporting",
                    "study_count_badge_text": "3 Unique",
                    "ui_color_theme": "danger_red_state",
                },
                "studies": [],
                "warnings": [],
            },
        },
        strict_genomic_cache={
            "strict_genomic_cache_version": STRICT_GENOMIC_CACHE_VERSION,
            "variant": {
                "genomic_hg38": "1-68444869-T-C",
                "genomic_hgvs": "NC_000001.11:g.68444869T>C",
                "variation_type": "single nucleotide variant",
                "consequence": "missense variant",
            },
            "evidence": {
                "vep": _cached_evidence("vep", {"most_severe_consequence": "missense_variant"}),
                "variant_validator": _cached_evidence("variant_validator"),
                "gnomad": _cached_evidence("gnomad"),
                "spliceai": _cached_evidence(
                    "spliceai",
                    {
                        "acceptor_loss": 0.0,
                        "donor_loss": 0.0,
                        "acceptor_gain": 0.0,
                        "donor_gain": 0.0,
                    },
                ),
            },
        },
    )
    rebuilt_summary = FunctionalEvidenceSummary(
        total_count=3,
        source_breakdown=FunctionalEvidenceSourceBreakdown(clinvar=1, pubmed=2),
        evidence_codes=["PS3"],
        source_asserted_codes=["PS3_Supporting"],
        display_metrics=FunctionalEvidenceDisplayMetrics(
            state="emerging_deficit",
            primary_label="Functional Deficit",
            acmg_badge_text="PS3_Supporting",
            verdict_source="clinvar",
            study_count_badge_text="3 Unique",
            code_rests_on=FunctionalEvidenceCodeRestsOn(cited=1, total=3),
            ui_color_theme="risk_red_state",
        ),
        studies=[
            FunctionalStudy(
                id="functional-study-1",
                citation="Guan et al., 2024",
                source_tags=["clinvar"],
                evidence_codes=["PS3"],
                asserted_codes=["PS3_Supporting"],
            )
        ],
    )
    functional_evidence = _NoopFunctionalEvidenceExtractor(rebuilt_summary)
    tools = {
        "vep": _StaticTool("vep"),
        "variant_validator": _StaticTool("variant_validator"),
        "gnomad": _StaticTool("gnomad"),
        "spliceai": _StaticTool("spliceai"),
        "clinvar": _StaticTool(
            "clinvar",
            {
                "classification": "Uncertain significance",
                "review_status": "criteria provided, single submitter",
            },
        ),
        "pubmed": _StaticTool("pubmed", {"articles": [], "total": 0}),
        "litvar2": _StaticTool("litvar2", {"articles": [], "total_publications": 0}),
        "clinical_trials": _ClinicalTrialsTool(),
    }
    service = _hermetic_lookup_service(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        settings=settings,
        functional_evidence_extractor=functional_evidence,
    )

    first = service.lookup(LookupRequest(gene="RPE65", cdna="c.260A>G"))
    second = service.lookup(LookupRequest(gene="RPE65", cdna="c.260A>G"))

    first_functional = first.report_payload.functional_evidence
    second_functional = second.report_payload.functional_evidence
    assert first_functional is not None
    assert second_functional is not None
    assert first_functional.display_metrics.state == "emerging_deficit"
    assert first_functional.display_metrics.verdict_source == "clinvar"
    assert second_functional.display_metrics.state == "emerging_deficit"
    assert functional_evidence.calls == 1

    hit = repo.get_fresh("RPE65:c.260A>G", ttl_days=30)
    assert hit is not None
    assert (
        hit["publication_data"]["functional_evidence_cache_version"]
        == FUNCTIONAL_EVIDENCE_CACHE_VERSION
    )
    cached_functional = hit["publication_data"]["functional_evidence"]
    assert cached_functional["display_metrics"]["state"] == "emerging_deficit"
    assert cached_functional["display_metrics"]["verdict_source"] == "clinvar"
    assert cached_functional["display_metrics"]["code_rests_on"] == {"cited": 1, "total": 3}


@pytest.mark.slow
def test_legacy_strict_genomic_cache_rebuilds_and_refreshes_cache(tmp_path: Path) -> None:
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
    repo.upsert(
        "RPE65:c.260A>G",
        litvar_id=None,
        total_publications=0,
        publication_data={},
        strict_genomic_cache={
            "variant": {
                "genomic_hg38": "legacy-coordinate",
                "variation_type": "legacy type",
                "consequence": "legacy consequence",
            },
            "evidence": {
                "vep": _cached_evidence("vep", {"most_severe_consequence": "legacy"}),
                "variant_validator": _cached_evidence("variant_validator"),
            },
        },
    )
    vep_tool = _StaticTool("vep", {"most_severe_consequence": "missense_variant"})
    variant_validator_tool = _MutatingVariantValidatorTool("variant_validator")
    tools = {
        "vep": vep_tool,
        "variant_validator": variant_validator_tool,
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
        ),
        "pubmed": _StaticTool("pubmed", {"articles": [], "total": 0}),
        "litvar2": _StaticTool("litvar2", {"articles": [], "total_publications": 0}),
        "clinical_trials": _ClinicalTrialsTool(),
    }
    service = _hermetic_lookup_service(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        settings=settings,
        functional_evidence_extractor=_NoopFunctionalEvidenceExtractor(),
    )

    first = service.lookup(LookupRequest(gene="RPE65", cdna="c.260A>G"))
    second = service.lookup(LookupRequest(gene="RPE65", cdna="c.260A>G"))

    assert first.report_payload.variant_summary_rows[0].genomic_hg38 == "1-68444869-T-C"
    assert vep_tool.calls == 1
    assert variant_validator_tool.calls == 1
    assert second.report_payload.variant_summary_rows[0].genomic_hg38 == "1-68444869-T-C"
    assert vep_tool.calls == 1
    assert variant_validator_tool.calls == 1

    hit = repo.get_fresh("RPE65:c.260A>G", ttl_days=30)
    assert hit is not None
    assert (
        hit["strict_genomic_cache"]["strict_genomic_cache_version"] == STRICT_GENOMIC_CACHE_VERSION
    )
    assert hit["strict_genomic_cache"]["variant"]["genomic_hg38"] == "1-68444869-T-C"


@pytest.mark.slow
def test_legacy_cached_ep_vlex_without_scope_counts_rebuilds_response_counts(
    tmp_path: Path,
) -> None:
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
    legacy_article = {
        "pmid": "38191234",
        "title": "Legacy cached RPE65 c.260A>G report.",
        "authors": "Walia S et al.",
        "journal": "Ophthalmology",
        "year": "2024",
        "url": "https://pubmed.ncbi.nlm.nih.gov/38191234/",
        "abstract": "The c.260A>G variant was recurrent.",
    }
    repo.upsert(
        "RPE65:c.260A>G",
        litvar_id="litvar-rpe65-c260ag",
        total_publications=999,
        publication_data={
            "publication_data_cache_version": PUBLICATION_DATA_CACHE_VERSION,
            "request_identity": {},
            "summary": {
                "litvar_id": "litvar-rpe65-c260ag",
                "total_publications": 999,
                "articles": [{"pmid": "38191234"}],
                "scholar_url": "https://scholar.google.com/scholar?q=RPE65+c.260A%3EG",
            },
            "raw": None,
            "source_url": "https://www.ncbi.nlm.nih.gov/research/litvar2/",
            "pubmed_request_identity": {},
            "pubmed_summary": {
                "articles": [legacy_article],
                "total": 999,
            },
            "pubmed_raw": None,
            "pubmed_source_url": "https://pubmed.ncbi.nlm.nih.gov/?term=RPE65+c.260A%3EG",
            "ep_vlex": {
                "total_count": 999,
                "shown_count": 1,
                "offset": 0,
                "limit": 5,
                "scope": "variant",
                "variant_terms": ["RPE65", "c.260A>G"],
                "source_breakdown": {"pubmed": 999, "litvar2": 1, "clinvar": 0, "clingen": 0},
                "publication_timeline": {
                    "publications_by_year": [{"year": 2024, "count": 1}],
                    "total_with_year": 1,
                    "total_without_year": 0,
                },
                "articles": [legacy_article],
                "warnings": [],
            },
        },
        strict_genomic_cache={
            "strict_genomic_cache_version": STRICT_GENOMIC_CACHE_VERSION,
            "variant": {
                "genomic_hg38": "1-68444869-T-C",
                "genomic_hgvs": "NC_000001.11:g.68444869T>C",
                "variation_type": "single nucleotide variant",
                "consequence": "missense variant",
            },
            "evidence": {
                "vep": _cached_evidence("vep", {"most_severe_consequence": "missense_variant"}),
                "variant_validator": _cached_evidence("variant_validator"),
                "gnomad": _cached_evidence("gnomad"),
                "spliceai": _cached_evidence(
                    "spliceai",
                    {
                        "acceptor_loss": 0.0,
                        "donor_loss": 0.0,
                        "acceptor_gain": 0.0,
                        "donor_gain": 0.0,
                    },
                ),
            },
        },
    )
    pubmed_tool = _StaticTool("pubmed", {"articles": [], "total": 0})
    litvar_tool = _StaticTool("litvar2", {"articles": [], "total_publications": 0})
    tools = {
        "vep": _StaticTool("vep"),
        "variant_validator": _StaticTool("variant_validator"),
        "gnomad": _StaticTool("gnomad"),
        "spliceai": _StaticTool("spliceai"),
        "clinvar": _StaticTool(
            "clinvar",
            {
                "classification": "Uncertain significance",
                "review_status": "criteria provided, single submitter",
            },
        ),
        "pubmed": pubmed_tool,
        "litvar2": litvar_tool,
        "clinical_trials": _ClinicalTrialsTool(),
    }
    service = _hermetic_lookup_service(
        tools,
        ClinicRules(),
        variant_cache_repo=repo,
        settings=settings,
        functional_evidence_extractor=_NoopFunctionalEvidenceExtractor(),
    )

    response = service.lookup(LookupRequest(gene="RPE65", cdna="c.260A>G"))

    literature = response.report_payload.publications_literature
    assert literature is not None
    assert literature.total_count == 1
    assert literature.scope_counts is not None
    assert literature.scope_counts.variant.total_count == 1
    assert literature.scope_counts.variant.count_kind == "deduped_pmids"
    assert literature.scope_counts.gene.total_count is None
    assert literature.scope_counts.gene.count_kind == "unavailable"
    assert "gene_scope_count_unavailable:source_count_missing" in (
        literature.scope_counts.gene.warnings
    )
    assert response.report_payload.publications_callout is not None
    assert response.report_payload.publications_callout.total_count == 1
    assert response.report_payload.publications_callout.scope_counts == literature.scope_counts
    assert pubmed_tool.calls == 0
    assert litvar_tool.calls == 0
    legacy_hit = repo.get_fresh("RPE65:c.260A>G", ttl_days=30)
    assert legacy_hit is not None
    assert "scope_counts" not in legacy_hit["publication_data"]["ep_vlex"]
