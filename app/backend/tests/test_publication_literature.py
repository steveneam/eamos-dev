from __future__ import annotations

from types import SimpleNamespace

from app.core.config import Settings
from app.services.publication_literature import (
    EamosProprietaryVariantLiteratureExtractor,
    VariantLiteratureTerms,
)
from app.tools.litvar2 import LitVar2Tool
from app.tools.pubmed import PubmedTool


def _settings(**overrides) -> Settings:
    return Settings(jwt_secret="test-secret", **overrides)


def _variant(
    *,
    gene: str = "RPE65",
    transcript_hgvs: str = "NM_000329.3:c.260A>G",
    protein_change: str = "p.Asp87Gly",
    dbsnp_rsid: str = "rs1645931040",
    genomic_hg38: str = "1-68444869-T-C",
):
    return SimpleNamespace(
        gene=gene,
        transcript_hgvs=transcript_hgvs,
        protein_change=protein_change,
        dbsnp_rsid=dbsnp_rsid,
        genomic_hg38=genomic_hg38,
    )


def test_variant_literature_terms_include_cdna_protein_rsid_and_genomic_aliases() -> None:
    terms = VariantLiteratureTerms.build(_variant())

    assert "RPE65" in terms.terms
    assert "NM_000329.3:c.260A>G" in terms.terms
    assert "c.260A>G" in terms.terms
    assert "p.Asp87Gly" in terms.terms
    assert "D87G" in terms.terms
    assert "p.D87G" in terms.terms
    assert "rs1645931040" in terms.terms
    assert "1-68444869-T-C" in terms.terms
    assert "RPE65" not in terms.snippet_terms


def test_variant_literature_terms_build_one_letter_alias_for_user_ush2a_variant() -> None:
    terms = VariantLiteratureTerms.build(
        _variant(
            gene="USH2A",
            transcript_hgvs="c.2276G>T",
            protein_change="p.Cys759Phe",
            dbsnp_rsid="",
            genomic_hg38="",
        )
    )

    assert "p.Cys759Phe" in terms.terms
    assert "C759F" in terms.terms
    assert "p.C759F" in terms.terms


def test_pubmed_variant_no_hit_keeps_gene_scope_out_of_variant_articles(monkeypatch) -> None:
    class Response:
        def __init__(self, payload) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self.payload

    calls: list[dict] = []

    def fake_get(*args, **kwargs):
        params = dict(kwargs.get("params") or {})
        calls.append(params)
        if len(calls) == 1:
            assert "c.260A>G" in params["term"]
            return Response({"esearchresult": {"idlist": [], "count": "0"}})
        assert params["term"] == "RPE65[Gene Name]"
        assert params["retmax"] == 0
        return Response({"esearchresult": {"idlist": ["37042101"], "count": "816"}})

    monkeypatch.setattr("app.tools.pubmed.httpx.get", fake_get)

    result = PubmedTool(_settings(use_real_apis=True)).get_evidence(_variant())

    assert len(calls) == 2
    assert result.status == "live"
    assert result.summary["articles"] == []
    assert result.summary["total"] == 0
    assert result.summary["gene_scope"]["total_count"] == 816


def test_litvar2_hydrates_pmids_with_bounded_pubmed_metadata(monkeypatch) -> None:
    calls: list[str] = []

    class Response:
        def __init__(self, payload=None, *, text: str = "") -> None:
            self.payload = payload or {}
            self.text = text

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self.payload

    class Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def get(self, url, params=None):
            calls.append(url)
            if url.endswith("/variant/autocomplete/"):
                return Response([{"litvar_id": "litvar-rpe65-c260ag", "rsid": "rs1645931040"}])
            if url.endswith("/variant/get/litvar-rpe65-c260ag/publications"):
                return Response({"pmids": ["38191234", "37042101"], "pmids_count": 2})
            if url.endswith("/esummary.fcgi"):
                return Response(
                    {
                        "result": {
                            "uids": ["38191234", "37042101"],
                            "38191234": {
                                "title": "RPE65 c.260A>G genotype-phenotype correlations.",
                                "authors": [{"name": "Walia S"}, {"name": "Smith J"}],
                                "source": "Ophthalmology",
                                "pubdate": "2024 Jan 15",
                                "sortpubdate": "2024/01/15 00:00",
                            },
                            "37042101": {
                                "title": "Long-term RPE65 gene therapy outcomes.",
                                "authors": [{"name": "Maguire AM"}],
                                "source": "N Engl J Med",
                                "pubdate": "2023 Apr",
                            },
                        }
                    }
                )
            if url.endswith("/efetch.fcgi"):
                return Response(
                    text=(
                        "<PubmedArticleSet>"
                        "<PubmedArticle><MedlineCitation><PMID>38191234</PMID>"
                        "<Article><Abstract><AbstractText>"
                        "The c.260A&gt;G variant was recurrent."
                        "</AbstractText></Abstract></Article></MedlineCitation></PubmedArticle>"
                        "</PubmedArticleSet>"
                    )
                )
            raise AssertionError(f"unexpected URL {url}")

    monkeypatch.setattr("app.tools.litvar2.httpx.Client", Client)

    result = LitVar2Tool(_settings(use_real_apis=True)).get_evidence(_variant())

    assert result.status == "live"
    assert result.warnings == []
    assert len(calls) == 4
    assert result.summary["total_publications"] == 2
    article = result.summary["articles"][0]
    assert article["pmid"] == "38191234"
    assert article["title"] == "RPE65 c.260A>G genotype-phenotype correlations."
    assert article["authors"] == "Walia S et al."
    assert article["journal"] == "Ophthalmology"
    assert article["year"] == "2024"
    assert "c.260A>G variant was recurrent" in article["abstract"]


def test_litvar2_hydration_failure_keeps_pmid_rows_and_warns(monkeypatch) -> None:
    class Response:
        def __init__(self, payload=None) -> None:
            self.payload = payload or {}

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self.payload

    class Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def get(self, url, params=None):
            if url.endswith("/variant/autocomplete/"):
                return Response([{"litvar_id": "litvar-rpe65-c260ag"}])
            if url.endswith("/variant/get/litvar-rpe65-c260ag/publications"):
                return Response({"pmids": ["38191234"], "pmids_count": 1})
            if url.endswith("/esummary.fcgi"):
                raise TimeoutError("PubMed metadata unavailable")
            raise AssertionError(f"unexpected URL {url}")

    monkeypatch.setattr("app.tools.litvar2.httpx.Client", Client)

    result = LitVar2Tool(_settings(use_real_apis=True)).get_evidence(_variant())

    assert result.status == "live"
    assert result.summary["articles"] == [
        {
            "pmid": "38191234",
            "title": "",
            "authors": "",
            "journal": "",
            "year": "",
            "url": "https://pubmed.ncbi.nlm.nih.gov/38191234/",
            "abstract": None,
        }
    ]
    assert result.warnings == ["litvar2_pubmed_hydration_failed:TimeoutError"]


def test_ep_vlex_dedupes_sources_sorts_recent_first_and_extracts_snippets() -> None:
    evidence_map = {
        "pubmed": {
            "gene_scope": {
                "query": "RPE65[Gene Name]",
                "total_count": 816,
                "source_status": "fixture",
            },
            "articles": [
                {
                    "pmid": "37042101",
                    "title": "Long-term RPE65 therapy follow-up.",
                    "authors": "Maguire AM et al.",
                    "journal": "N Engl J Med",
                    "year": "2023",
                    "abstract": "RPE65 p.Asp87Gly was included in the treated cohort.",
                },
                {
                    "pmid": "38191234",
                    "title": "Biallelic RPE65 variants causing Leber congenital amaurosis.",
                    "authors": "Walia S et al.",
                    "journal": "Ophthalmology",
                    "year": "2024",
                    "abstract": "The c.260A>G (p.Asp87Gly) missense variant was recurrent.",
                },
            ],
        },
        "litvar2": {
            "articles": [
                {"pmid": "38191234", "title": ""},
                {"pmid": "35901234", "title": "Functional classification of RPE65 missense."},
            ]
        },
        "clinvar": {"citations": [{"pmid": "37042101"}]},
    }

    literature = EamosProprietaryVariantLiteratureExtractor().build_for_lookup(
        _variant(),
        evidence_map,
        limit=2,
    )

    assert literature.total_count == 3
    assert literature.shown_count == 2
    assert [article.pmid for article in literature.articles] == ["38191234", "37042101"]
    assert literature.source_breakdown.pubmed == 2
    assert literature.source_breakdown.litvar2 == 2
    assert literature.source_breakdown.clinvar == 1
    assert literature.scope == "variant"
    assert literature.scope_counts is not None
    assert literature.scope_counts.variant.total_count == 3
    assert literature.scope_counts.variant.count_kind == "deduped_pmids"
    assert literature.scope_counts.gene.total_count == 816
    assert literature.scope_counts.gene.count_kind == "gene_wide_source_count"
    assert literature.scope_counts.gene.source_breakdown.pubmed == 816
    assert [item.model_dump() for item in literature.publication_timeline.publications_by_year] == [
        {"year": 2023, "count": 1},
        {"year": 2024, "count": 1},
    ]
    assert literature.publication_timeline.total_with_year == 2
    assert literature.publication_timeline.total_without_year == 1
    assert literature.articles[0].url == "https://pubmed.ncbi.nlm.nih.gov/38191234/"
    assert literature.articles[0].source_tags == ["litvar2", "pubmed"]
    assert literature.articles[0].snippets[0].matched_terms
    assert "c.260A>G" in literature.articles[0].snippets[0].matched_terms
    assert literature.articles[0].snippet_status == "exact_variant_snippet"
    assert literature.articles[1].snippet_status == "exact_variant_snippet"


def test_ep_vlex_marks_pubmed_gene_only_rows_without_fabricating_snippets() -> None:
    literature = EamosProprietaryVariantLiteratureExtractor().build_for_lookup(
        _variant(),
        {
            "pubmed": {
                "articles": [
                    {
                        "pmid": "37042101",
                        "title": "Long-term outcomes of RPE65 gene therapy.",
                        "authors": "Maguire AM et al.",
                        "journal": "N Engl J Med",
                        "year": "2023",
                        "abstract": (
                            "We report 5-year follow-up data from a phase 3 trial "
                            "in patients with biallelic RPE65-associated retinal dystrophy."
                        ),
                    }
                ]
            },
            "litvar2": {"articles": [{"pmid": "37042101", "title": ""}]},
        },
    )

    article = literature.articles[0]
    assert article.snippets == []
    assert article.snippet_status == "gene_only_no_variant"


def test_ep_vlex_marks_abstract_text_without_variant_or_gene() -> None:
    literature = EamosProprietaryVariantLiteratureExtractor().build_for_lookup(
        _variant(),
        {
            "pubmed": {
                "articles": [
                    {
                        "pmid": "37042102",
                        "title": "Long-term gene therapy outcomes.",
                        "year": "2023",
                        "abstract": (
                            "The primary endpoint was multi-luminance mobility testing "
                            "after bilateral subretinal injection."
                        ),
                    }
                ]
            }
        },
    )

    article = literature.articles[0]
    assert article.snippets == []
    assert article.snippet_status == "abstract_only_no_variant"


def test_ep_vlex_extracts_exact_variant_snippet_from_table_text() -> None:
    literature = EamosProprietaryVariantLiteratureExtractor().build_for_lookup(
        _variant(),
        {
            "pubmed": {
                "articles": [
                    {
                        "pmid": "37042103",
                        "title": "Functional variant table.",
                        "year": "2023",
                        "table_text": "Variant c.260A>G retained 12% of wild-type activity.",
                    }
                ]
            }
        },
    )

    snippet = literature.articles[0].snippets[0]
    assert snippet.section == "table"
    assert snippet.source == "pmc_bioc"
    assert snippet.matched_terms == ["c.260A>G"]
    assert literature.articles[0].snippet_status == "exact_variant_snippet"


def test_ep_vlex_marks_litvar_only_rows_without_fabricating_snippets() -> None:
    literature = EamosProprietaryVariantLiteratureExtractor().build_for_lookup(
        _variant(),
        {"litvar2": {"articles": [{"pmid": "12345678"}]}},
    )

    article = literature.articles[0]
    assert article.snippets == []
    assert article.snippet_status == "reported_in_litvar2_no_text"
    assert article.url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"
    assert literature.publication_timeline.publications_by_year == []
    assert literature.publication_timeline.total_with_year == 0
    assert literature.publication_timeline.total_without_year == 1


def test_ep_vlex_skips_failed_live_source_fallback_fixture_rows() -> None:
    literature = EamosProprietaryVariantLiteratureExtractor().build_for_lookup(
        _variant(gene="USH2A", transcript_hgvs="c.2276G>T", protein_change="p.Cys759Phe"),
        {
            "pubmed": {
                "articles": [
                    {
                        "pmid": "38191234",
                        "title": "RPE65 c.260A>G fixture row from a failed live source.",
                        "year": "2024",
                    }
                ]
            },
            "litvar2": {"articles": [{"pmid": "41234567", "title": "USH2A p.Cys759Phe"}]},
        },
        source_statuses={"pubmed": "fallback", "litvar2": "live"},
    )

    assert literature.total_count == 1
    assert [article.pmid for article in literature.articles] == ["41234567"]
    assert literature.source_breakdown.pubmed == 0
    assert literature.scope_counts is not None
    assert literature.scope_counts.gene.total_count is None
    assert literature.scope_counts.gene.count_kind == "unavailable"
    assert "gene_scope_count_unavailable:pubmed_failed" in literature.scope_counts.gene.warnings


def test_ep_vlex_skips_failed_clinvar_citation_rows() -> None:
    literature = EamosProprietaryVariantLiteratureExtractor().build_for_lookup(
        _variant(),
        {"clinvar": {"citations": [{"pmid": "12345678"}]}},
        source_statuses={"clinvar": "error"},
    )

    assert literature.total_count == 0
    assert literature.source_breakdown.clinvar == 0


def test_ep_vlex_clinvar_pmid_extraction_ignores_reference_allele_numbers() -> None:
    literature = EamosProprietaryVariantLiteratureExtractor().build_for_lookup(
        _variant(),
        {"clinvar": {"citations": [{"pmid": "12345678"}]}},
        evidence_raw={
            "clinvar": {
                "reference_allele": {"position": 68444869},
                "references": [{"pubmed_id": "23456789"}],
            }
        },
    )

    assert literature.total_count == 2
    assert {article.pmid for article in literature.articles} == {"12345678", "23456789"}
    assert "68444869" not in {article.pmid for article in literature.articles}


def test_ep_vlex_gene_scope_returns_source_count_without_articles() -> None:
    literature = EamosProprietaryVariantLiteratureExtractor().build_for_lookup(
        _variant(),
        {
            "pubmed": {
                "gene_scope": {
                    "query": "RPE65[Gene Name]",
                    "total_count": 816,
                    "source_status": "fixture",
                },
                "articles": [{"pmid": "38191234", "title": "RPE65 c.260A>G"}],
            }
        },
        scope="gene",
    )

    assert literature.scope == "gene"
    assert literature.total_count == 816
    assert literature.shown_count == 0
    assert literature.articles == []
    assert literature.source_breakdown.pubmed == 816
    assert literature.scope_counts is not None
    assert literature.scope_counts.variant.total_count == 1
    assert literature.scope_counts.gene.total_count == 816


def test_ep_vlex_pagination_uses_deduped_rows_without_page_overlap() -> None:
    evidence_map = {
        "pubmed": {
            "articles": [
                {
                    "pmid": "39000001",
                    "title": "RPE65 c.260A>G first report.",
                    "publication_date": "2025-01-01",
                },
                {
                    "pmid": "39000002",
                    "title": "RPE65 c.260A>G follow-up.",
                    "publication_date": "2024-01-01",
                },
                {
                    "pmid": "39000003",
                    "title": "RPE65 c.260A>G assay.",
                    "publication_date": "2023-01-01",
                },
            ]
        },
        "litvar2": {
            "articles": [
                {"pmid": "39000002", "title": ""},
                {"pmid": "39000004", "title": "RPE65 c.260A>G LitVar row."},
            ]
        },
        "clinvar": {"citations": [{"pmid": "39000004"}, {"pmid": "39000005"}]},
    }
    extractor = EamosProprietaryVariantLiteratureExtractor()

    first_page = extractor.build_for_lookup(_variant(), evidence_map, limit=2, offset=0)
    second_page = extractor.build_for_lookup(_variant(), evidence_map, limit=2, offset=2)

    first_pmids = {article.pmid for article in first_page.articles}
    second_pmids = {article.pmid for article in second_page.articles}
    assert first_page.total_count == 5
    assert second_page.total_count == 5
    assert len(first_pmids) == len(first_page.articles)
    assert len(second_pmids) == len(second_page.articles)
    assert first_pmids.isdisjoint(second_pmids)
    assert first_page.source_breakdown.pubmed == 3
    assert first_page.source_breakdown.litvar2 == 2
    assert first_page.source_breakdown.clinvar == 2
