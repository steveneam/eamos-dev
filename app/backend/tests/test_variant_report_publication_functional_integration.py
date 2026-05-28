from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.services.functional_evidence import FunctionalEvidenceExtractor
from app.services.publication_literature import EamosProprietaryVariantLiteratureExtractor


def _section_targets(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        target["section_id"]: target for target in profile["extraction_plan"]["section_targets"]
    }


def _report_call_card(payload: dict[str, Any], card_id: str) -> dict[str, Any]:
    return next(card for card in payload["call_cards"]["cards"] if card["card_id"] == card_id)


def _variant(
    *,
    gene: str,
    transcript_hgvs: str,
    protein_change: str,
    dbsnp_rsid: str = "",
    genomic_hg38: str = "",
) -> SimpleNamespace:
    return SimpleNamespace(
        gene=gene,
        transcript_hgvs=transcript_hgvs,
        protein_change=protein_change,
        dbsnp_rsid=dbsnp_rsid,
        genomic_hg38=genomic_hg38,
    )


def test_lookup_keeps_publication_inventory_and_functional_count_distinct(
    client,
) -> None:
    response = client.post(
        "/api/v1/lookup",
        json={"gene": "RPE65", "cdna": "c.260A>G"},
    )

    assert response.status_code == 200
    payload = response.json()["report_payload"]
    publications = payload["publications_literature"]
    functional = payload["functional_evidence"]
    profile = payload["report_profile"]

    assert publications["total_count"] == 3
    assert publications["limit"] == 5
    assert publications["shown_count"] == min(publications["total_count"], 5)
    assert len(publications["articles"]) == publications["shown_count"]
    assert payload["publications_callout"]["total_count"] == publications["total_count"]
    assert publications["scope"] == "variant"
    assert publications["scope_counts"]["variant"]["total_count"] == 3
    assert publications["scope_counts"]["variant"]["count_kind"] == "deduped_pmids"
    assert publications["scope_counts"]["gene"]["total_count"] == 816
    assert publications["scope_counts"]["gene"]["count_kind"] == "gene_wide_source_count"
    assert payload["publications_callout"]["scope_counts"] == publications["scope_counts"]

    assert functional["total_count"] == 1
    assert functional["total_count"] != publications["total_count"]
    publication_pmids = {article["pmid"] for article in publications["articles"]}
    functional_pmids = {
        study["pmid"] for study in functional["studies"] if study["pmid"] is not None
    }
    assert functional_pmids == {"35901234"}
    assert functional_pmids < publication_pmids

    targets = _section_targets(profile)
    assert targets["publications"]["match_level"] == "variant_level"
    assert targets["publications"]["required_sources"] == ["pubmed", "litvar2", "clinvar"]
    assert targets["lab_functional"]["match_level"] == "variant_level"
    assert targets["lab_functional"]["required_sources"] == [
        "clingen",
        "clinvar",
        "pubmed",
    ]

    summary = profile["interpretation_summary"]
    assert "publications" in summary["fact_refs"]
    assert "3 publication(s) identified" in summary["text"]

    functional_card = _report_call_card(payload, "lab_functional")
    badge_texts = {badge["text"] for badge in functional_card["support_badges"]}
    assert "1 Unique" in badge_texts
    assert "3 Unique" not in badge_texts


@pytest.mark.parametrize(
    ("variant", "evidence_map", "expected_publication_pmids", "expected_functional_pmids"),
    [
        (
            _variant(
                gene="USH2A",
                transcript_hgvs="NM_206933.4:c.2276G>T",
                protein_change="p.Cys759Phe",
                dbsnp_rsid="rs752238803",
            ),
            {
                "pubmed": {
                    "articles": [
                        {
                            "pmid": "35672333",
                            "title": "Functional assay of USH2A c.2276G>T.",
                            "abstract": (
                                "A zebrafish knock-in assay for c.2276G>T showed altered "
                                "expression and impaired visual function."
                            ),
                            "year": "2022",
                        },
                        {
                            "pmid": "12525556",
                            "title": "USH2A c.2276G>T in inherited retinal disease.",
                            "abstract": "A cohort report described the c.2276G>T allele.",
                            "year": "2003",
                        },
                    ]
                },
                "litvar2": {
                    "articles": [
                        {"pmid": "35672333", "title": ""},
                        {"pmid": "25262649", "title": "USH2A variant spectrum."},
                    ]
                },
                "clinvar": {"citations": [{"pmid": "25262649"}]},
            },
            {"35672333", "12525556", "25262649"},
            {"35672333"},
        ),
        (
            _variant(
                gene="BRCA1",
                transcript_hgvs="NM_007294.4:c.5266dup",
                protein_change="p.Gln1756ProfsTer74",
            ),
            {
                "pubmed": {
                    "articles": [
                        {
                            "pmid": "20104584",
                            "title": "Functional assay of BRCA1 c.5266dup.",
                            "abstract": (
                                "The c.5266dup variant was tested in a protein function "
                                "assay and showed loss of normal activity."
                            ),
                            "year": "2010",
                        },
                        {
                            "pmid": "31234567",
                            "title": "BRCA1 c.5266dup founder variant review.",
                            "abstract": "A review summarized clinical observations for c.5266dup.",
                            "year": "2019",
                        },
                    ]
                },
                "litvar2": {"articles": [{"pmid": "39876543", "title": "BRCA1 c.5266dup"}]},
                "clinvar": {},
            },
            {"20104584", "31234567", "39876543"},
            {"20104584"},
        ),
    ],
)
def test_non_rpe65_publication_inventory_is_not_the_functional_count(
    variant: SimpleNamespace,
    evidence_map: dict[str, dict[str, Any]],
    expected_publication_pmids: set[str],
    expected_functional_pmids: set[str],
) -> None:
    publications = EamosProprietaryVariantLiteratureExtractor().build_for_lookup(
        variant,
        evidence_map,
    )
    functional = FunctionalEvidenceExtractor().build_for_lookup(variant, evidence_map)

    publication_pmids = {article.pmid for article in publications.articles}
    functional_pmids = {study.pmid for study in functional.studies if study.pmid is not None}

    assert publication_pmids == expected_publication_pmids
    assert functional_pmids == expected_functional_pmids
    assert functional.total_count == len(expected_functional_pmids)
    assert publications.total_count == len(expected_publication_pmids)
    assert functional.total_count != publications.total_count
    assert functional_pmids < publication_pmids
    assert functional.display_metrics.study_count_badge_text == (f"{functional.total_count} Unique")


@pytest.mark.parametrize(
    ("gene", "cdna"),
    [
        ("USH2A", "c.2276G>T"),
        ("BRCA1", "c.5266dup"),
    ],
)
def test_lookup_non_rpe65_publication_and_functional_sections_do_not_use_rpe65_counts(
    client,
    gene: str,
    cdna: str,
) -> None:
    response = client.post("/api/v1/lookup", json={"gene": gene, "cdna": cdna})

    assert response.status_code == 200
    payload = response.json()["report_payload"]
    publications = payload["publications_literature"]
    functional = payload["functional_evidence"]

    assert publications["total_count"] == 0
    assert publications["articles"] == []
    assert payload["publications_callout"]["total_count"] == 0
    assert functional["total_count"] == 0
    assert functional["studies"] == []

    serialized = json.dumps(payload)
    for rpe65_fixture_pmid in ("38191234", "37042101", "35901234"):
        assert rpe65_fixture_pmid not in serialized


def test_report_profile_references_publication_and_functional_sections_without_rows(
    client,
) -> None:
    response = client.post(
        "/api/v1/lookup",
        json={"gene": "RPE65", "cdna": "c.260A>G"},
    )

    assert response.status_code == 200
    payload = response.json()["report_payload"]
    profile = payload["report_profile"]

    assert "publications_literature" not in profile
    assert "functional_evidence" not in profile
    assert "publications" in _section_targets(profile)
    assert "lab_functional" in _section_targets(profile)

    profile_json = json.dumps(profile)
    for article in payload["publications_literature"]["articles"]:
        assert article["title"] not in profile_json
    for study in payload["functional_evidence"]["studies"]:
        if study["snippet"] is not None:
            assert study["snippet"] not in profile_json


def test_publication_expansion_endpoint_paginates_epvlex_inventory(client) -> None:
    response = client.post(
        "/api/v1/lookup/publications",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "transcript": "NM_000329.3",
            "protein_change": "p.Asp87Gly",
            "limit": 1,
            "offset": 1,
        },
    )

    assert response.status_code == 200
    page = response.json()
    assert page["total_count"] == 3
    assert page["shown_count"] == 1
    assert page["limit"] == 1
    assert page["offset"] == 1
    assert [article["pmid"] for article in page["articles"]] == ["37042101"]
    assert page["articles"][0]["url"] == "https://pubmed.ncbi.nlm.nih.gov/37042101/"


def test_publication_expansion_endpoint_returns_gene_scope_count(client) -> None:
    response = client.post(
        "/api/v1/lookup/publications",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "protein_change": "p.Asp87Gly",
            "scope": "gene",
        },
    )

    assert response.status_code == 200
    page = response.json()
    assert page["scope"] == "gene"
    assert page["total_count"] == 816
    assert page["shown_count"] == 0
    assert page["articles"] == []
    assert page["scope_counts"]["variant"]["total_count"] == 3
    assert page["scope_counts"]["gene"]["total_count"] == 816
    assert page["scope_counts"]["gene"]["count_kind"] == "gene_wide_source_count"
