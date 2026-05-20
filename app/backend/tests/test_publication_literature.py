from __future__ import annotations

from types import SimpleNamespace

from app.services.publication_literature import (
    EamosProprietaryVariantLiteratureExtractor,
    VariantLiteratureTerms,
)


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


def test_ep_vlex_dedupes_sources_sorts_recent_first_and_extracts_snippets() -> None:
    evidence_map = {
        "pubmed": {
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
            ]
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
    assert literature.articles[0].url == "https://pubmed.ncbi.nlm.nih.gov/38191234/"
    assert literature.articles[0].source_tags == ["litvar2", "pubmed"]
    assert literature.articles[0].snippets[0].matched_terms
    assert "c.260A>G" in literature.articles[0].snippets[0].matched_terms


def test_ep_vlex_marks_litvar_only_rows_without_fabricating_snippets() -> None:
    literature = EamosProprietaryVariantLiteratureExtractor().build_for_lookup(
        _variant(),
        {"litvar2": {"articles": [{"pmid": "12345678"}]}},
    )

    article = literature.articles[0]
    assert article.snippets == []
    assert article.snippet_status == "reported_in_litvar2_no_text"
    assert article.url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"


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
