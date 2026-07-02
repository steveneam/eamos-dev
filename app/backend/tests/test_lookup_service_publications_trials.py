from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.schemas.run import PublicationLiterature, PubMedArticle, ReportPayload
from app.services.lookup_service_publications_trials import (
    build_publications_callout,
    build_publications_section_literature,
    build_therapeutic_landscape,
    trials_section_from_result,
)
from app.tools.base import ToolResult


def _variant() -> SimpleNamespace:
    return SimpleNamespace(
        gene="ABCA4",
        transcript_hgvs="NM_000350.3:c.5461-10T>C",
        protein_change="",
        genomic_hg38="1-68444869-T-C",
        genomic_hgvs="NC_000001.11:g.68444869T>C",
        dbsnp_rsid=None,
    )


def test_publications_section_uses_current_cached_literature_without_tools() -> None:
    cached = PublicationLiterature(
        total_count=1,
        shown_count=1,
        articles=[
            PubMedArticle(
                pmid="38191234",
                title="Cached variant publication",
                authors="Walia S et al.",
                journal="Ophthalmology",
                year="2024",
                url="https://pubmed.ncbi.nlm.nih.gov/38191234/",
            )
        ],
    )
    warnings: list[str] = []

    result = build_publications_section_literature(
        _variant(),
        publication_cache={"ep_vlex": cached.model_dump(mode="json")},
        tool_registry={},
        publication_literature=SimpleNamespace(
            build_for_lookup=lambda *_args, **_kwargs: pytest.fail("cache should be used")
        ),
        report_source_result_cache_writer=lambda *_args, **_kwargs: pytest.fail(
            "cache should not write source snapshots"
        ),
        evidence=[],
        evidence_map={},
        evidence_raw={},
        evidence_statuses={},
        warnings=warnings,
        cache_key="ABCA4:c.5461-10T>C",
        species="human",
        refresh=False,
    )

    assert result.total_count == 1
    assert result.articles[0].pmid == "38191234"
    assert warnings == []


def test_trials_section_result_adds_source_fetched_at_and_gene_level_warning() -> None:
    result = ToolResult(
        source="clinical_trials",
        status="live",
        request_identity={"gene": "ABCA4"},
        summary={
            "trial_rows": [
                {
                    "nct_id": "NCT06388083",
                    "title": "Tinlarebant in Stargardt disease",
                    "status": "ACTIVE_NOT_RECRUITING",
                    "phase": "Phase 2/Phase 3",
                    "match_level": "disease_level",
                    "matched_terms": ["Tinlarebant"],
                    "source_url": "https://clinicaltrials.gov/study/NCT06388083",
                }
            ],
            "query_executions": [
                {
                    "query_id": "disease_term:tinlarebant",
                    "lane": "disease_term",
                    "query_term": "Tinlarebant",
                    "status": "ok",
                    "result_count": 1,
                }
            ],
            "query_term": "Tinlarebant",
            "source_url": "https://clinicaltrials.gov/search?term=Tinlarebant",
            "warnings": ["variant_level_trial_not_found:using_lower_match_level"],
        },
        warnings=["variant_level_trial_not_found:using_lower_match_level"],
        raw=None,
        source_url="https://clinicaltrials.gov/search?term=Tinlarebant",
        fetched_at="2026-06-24T12:34:56Z",
    )

    section = trials_section_from_result(result)

    assert section.trial_rows[0].fetched_at == "2026-06-24T12:34:56Z"
    assert section.query_executions[0].query_id == "disease_term:tinlarebant"
    assert "clinical_trials_gene_level_target_only" in section.warnings
    assert "variant_level_trial_not_found:using_lower_match_level" in section.warnings
    assert section.provenance[0].source_url == (
        "https://clinicaltrials.gov/search?term=Tinlarebant"
    )


def test_therapeutic_landscape_can_render_cached_trials_without_tool() -> None:
    recorded: list[tuple[str, ToolResult]] = []
    cached = ToolResult(
        source="clinical_trials",
        status="cache",
        request_identity={"gene": "ABCA4"},
        summary={
            "trial_rows": [
                {
                    "nct_id": "NCT00000001",
                    "title": "Cached ABCA4 trial",
                    "status": "RECRUITING",
                    "phase": "Phase 1",
                    "match_level": "gene_level",
                    "matched_terms": ["ABCA4"],
                    "source_url": "https://clinicaltrials.gov/study/NCT00000001",
                }
            ]
        },
        warnings=[],
        raw=None,
    )

    landscape = build_therapeutic_landscape(
        gene="ABCA4",
        variant=_variant(),
        evidence_map={},
        tool_registry={},
        cached_report_source_results={"clinical_trials": cached},
        source_cached_result=lambda *_args, **_kwargs: pytest.fail("cached result should be used"),
        record_result=lambda name, result: recorded.append((name, result)),
    )

    assert "Cached ABCA4 trial" in landscape.text
    assert landscape.clinical_trials_tool_present is False
    assert recorded == [("clinical_trials", cached)]


def test_publications_callout_preserves_existing_blurb_and_scope_counts() -> None:
    payload = ReportPayload(
        patient_id="lookup_test",
        publications_literature=PublicationLiterature(total_count=0, shown_count=0),
    )
    callout = build_publications_callout(
        payload=payload,
        litvar_summary={},
        gene="CFTR",
        cdna="c.1521_1523delCTT",
    )

    assert callout.total_count == 0
    assert callout.scholar_url.endswith("CFTR+c.1521_1523delCTT")
    assert "CFTR c.1521_1523delCTT" in callout.blurb
