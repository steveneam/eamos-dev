from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from app.cli.eamos_search_index_backfill import run_backfill
from app.core.rate_limit import InMemoryRateLimiter
from app.schemas.report import ExtractedCase, ExtractedVariant, UploadedReport
from app.schemas.run import (
    PublicationLiterature,
    PublicationSnippet,
    PubMedArticle,
    ReportDataCurrency,
    ReportDataCurrencySource,
    ReportPayload,
    ReportSectionSignal,
    RunResponse,
    RunStatus,
    TherapiesTrialsSection,
    TrialMatch,
    VariantReportProfile,
    VariantSummaryRow,
)
from app.schemas.search import SearchDocumentWrite


def _register_user(client: TestClient, username: str) -> tuple[dict[str, str], str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "test-password"},
    )
    assert response.status_code == 201
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["user_id"]


def _auth_headers(client: TestClient, username: str) -> dict[str, str]:
    headers, _user_id = _register_user(client, username)
    return headers


def _set_search_limit(client: TestClient, max_requests: int = 1) -> None:
    client.app.state.rate_limiter = InMemoryRateLimiter()
    client.app.state.settings.rate_limit_search_max_requests = max_requests
    client.app.state.settings.rate_limit_window_seconds = 60


class FakeSearchAnswerChain:
    def __init__(self, citations: list[dict[str, str | None]]) -> None:
        self.citations = citations
        self.invocations: list[dict[str, str]] = []

    def invoke(self, payload: dict[str, str]) -> dict[str, object]:
        self.invocations.append(payload)
        return {
            "answer": "The indexed RPE65 run supports a grounded answer.",
            "grounded": True,
            "citations": self.citations,
        }


def _current_user_id(client: TestClient) -> str:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    return response.json()["user_id"]


def _enable_fake_search_answer(
    client: TestClient,
    answer_chain: FakeSearchAnswerChain | None,
) -> None:
    client.app.state.settings.search_answer_enabled = True
    client.app.state.search_answer_service.answer_chain = answer_chain


def _index_answer_fixture(client: TestClient) -> None:
    owner_user_id = _current_user_id(client)
    client.app.state.search_repo.upsert_document(
        SearchDocumentWrite(
            source_key="run:answer-grounded",
            doc_type="run",
            visibility_scope="private",
            owner_user_id=owner_user_id,
            run_id="run_answer_grounded",
            patient_id="ANSWER-001",
            report_title="Grounded RPE65 answer run",
            identifier_text="ANSWER-001 run_answer_grounded RPE65 answerhardening",
            search_text="RPE65 answerhardening grounded run evidence.",
        )
    )
    client.app.state.search_repo.upsert_document(
        SearchDocumentWrite(
            source_key="gene:rpe65-answer",
            doc_type="gene",
            visibility_scope="public",
            report_title="RPE65",
            identifier_text="RPE65 answerhardening",
            search_text="RPE65 answerhardening public gene row.",
        )
    )


def _save_search_fixture_report(client: TestClient, report_id: str = "report_search_local") -> None:
    report = UploadedReport(
        report_id=report_id,
        filename="search-local.pdf",
        content_type="application/pdf",
        size_bytes=256,
        created_at=datetime.now(timezone.utc),
        report_kind="test",
        source_pdf_path="search-local.pdf",
        extraction_status="completed",
        extracted_case=ExtractedCase(
            case_label="search-local-case",
            report_title="Search Local RPE65 Case",
            patient_context="Patient with inherited retinal disease.",
            clinical_findings="RPE65 NM_000329.3:c.260A>G was reported.",
            summary="Search fixture report for RPE65 c.260A>G.",
            variants=[
                ExtractedVariant(
                    gene="RPE65",
                    transcript_hgvs="NM_000329.3:c.260A>G",
                    protein_change="p.Asp87Gly",
                    genomic_hg38="1-68444869-T-C",
                    variation_type="SNV",
                    consequence="missense_variant",
                )
            ],
        ),
        raw_extracted_text="RPE65 NM_000329.3:c.260A>G p.Asp87Gly search fixture.",
    )
    client.app.state.reports_repo.save(report)


def _saved_library_variant_payload(**overrides) -> dict:
    payload = {
        "id": "ush2a:c.2276g>t",
        "gene": "USH2A",
        "variant": "c.2276G>T",
        "query": "USH2A c.2276G>T",
        "raw": "USH2A NM_206933.4:c.2276G>T p.Cys759Phe search fixture.",
        "savedAt": 1_780_000_000_000,
        "folderId": None,
        "classification": "likely_pathogenic",
        "hgvs_full": "NM_206933.4:c.2276G>T",
    }
    payload.update(overrides)
    return payload


def _source_backed_report_payload(*, summary: str = "Original indexed source summary"):
    publication = PubMedArticle(
        pmid="12345678",
        title="RPE65 gene therapy in inherited retinal dystrophy",
        authors="Example A; Example B",
        journal="Journal of Retinal Evidence",
        year="2025",
        url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        abstract="RPE65 NM_000329.3:c.260A>G is discussed in a source-backed article.",
        snippets=[
            PublicationSnippet(
                section="abstract",
                text="The RPE65 c.260A>G variant appears in the source-backed abstract.",
                matched_terms=["RPE65", "NM_000329.3:c.260A>G"],
                source="pubmed_efetch",
                confidence="exact_variant",
            )
        ],
        source_tags=["pubmed"],
        snippet_status="source_backed",
    )
    trial = TrialMatch(
        nct_id="NCT01234567",
        title="RPE65 retinal dystrophy registry study",
        status="Recruiting",
        phase="Phase 2",
        conditions=["Inherited retinal dystrophy"],
        interventions=["Gene therapy"],
        locations=["Sydney"],
        match_level="variant_level",
        matched_terms=["RPE65", "c.260A>G"],
        source_url="https://clinicaltrials.gov/study/NCT01234567",
        evidence_snippet="RPE65 c.260A>G source-backed trial match.",
        fetched_at="2026-07-01T00:00:00Z",
    )
    return ReportPayload(
        patient_id="SEARCH-SOURCE-001",
        report_title="Source-backed search fixture",
        report_data_currency=ReportDataCurrency(
            generated_at="2026-07-01T00:00:00Z",
            sources=[
                ReportDataCurrencySource(
                    source="gnomad",
                    label="gnomAD population frequencies",
                    materialized_at="2026-06-30T00:00:00Z",
                    upstream_released_at="2026-05-01",
                    tier="static",
                    status="fresh",
                    staleness_days=30,
                    source_version="gnomAD v4.1.1",
                )
            ],
        ),
        source_versions={"gnomad": "gnomAD v4.1.1"},
        ai_clinical_summary=summary,
        variant_summary_rows=[
            VariantSummaryRow(
                gene="RPE65",
                transcript_hgvs="NM_000329.3:c.260A>G",
                protein_change="p.Asp87Gly",
                consequence="missense_variant",
            )
        ],
        publications_literature=PublicationLiterature(
            total_count=1,
            shown_count=1,
            articles=[publication],
        ),
        report_profile=VariantReportProfile(
            therapies_trials=TherapiesTrialsSection(trial_rows=[trial]),
            section_signals=[
                ReportSectionSignal(
                    section_id="publications",
                    label="Publication Literature",
                    priority=52,
                    confidence=0.58,
                    relevance="exact_variant",
                    source_strength="literature",
                    status="ready",
                    headline="1 publication(s)",
                    data_notes=["source-backed publication row indexed"],
                    source_refs=["publications"],
                )
            ],
        ),
    )


def _persist_source_backed_run(
    client: TestClient,
    *,
    owner_user_id: str,
    run_id: str = "run_source_backed",
    summary: str = "Original indexed source summary",
) -> RunResponse:
    run = client.app.state.run_repo.create_run(
        run_id=run_id,
        patient_id="SEARCH-SOURCE-001",
        report_ids=[],
        run_status=RunStatus.completed,
        report_payload=_source_backed_report_payload(summary=summary),
        evidence=[],
        warnings=[],
    )
    client.app.state.search_index_service.index_run(
        run,
        reports=[],
        owner_user_id=owner_user_id,
    )
    return run


def _clinical_search_asset_root(tmp_path: Path) -> Path:
    root = tmp_path / "source_assets"
    (root / "mondo_disease_ontology").mkdir(parents=True)
    (root / "human_phenotype_ontology").mkdir(parents=True)
    (root / "clingen_gene_validity").mkdir(parents=True)
    (root / "gencc_download").mkdir(parents=True)
    (root / "mondo_disease_ontology" / "mondo.json").write_text(
        """
        {
          "graphs": [
            {
              "nodes": [
                {
                  "id": "http://purl.obolibrary.org/obo/MONDO_0008765",
                  "lbl": "Leber congenital amaurosis 2",
                  "meta": {
                    "definition": {
                      "val": "A retinal dystrophy associated with biallelic RPE65 variants."
                    },
                    "xrefs": [{"val": "OMIM:204100"}]
                  }
                }
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    (root / "human_phenotype_ontology" / "hp.json").write_text(
        """
        {
          "graphs": [
            {
              "nodes": [
                {
                  "id": "http://purl.obolibrary.org/obo/HP_0000510",
                  "lbl": "Visual impairment"
                }
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    (root / "human_phenotype_ontology" / "phenotype.hpoa").write_text(
        "\n".join(
            [
                "#version: 2026-02-16",
                "database_id\tdisease_name\tqualifier\thpo_id\treference\tevidence\tonset\t"
                "frequency\tsex\tmodifier\taspect\tbiocuration",
                (
                    "OMIM:204100\tLeber congenital amaurosis 2\t\tHP:0000510\t"
                    "PMID:1\tPCS\t\t1/2\t\t\tP\tHPO:test"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "human_phenotype_ontology" / "genes_to_phenotype.txt").write_text(
        "\n".join(
            [
                "ncbi_gene_id\tgene_symbol\thpo_id\thpo_name\tfrequency\tdisease_id",
                "6121\tRPE65\tHP:0000510\tVisual impairment\t1/2\tOMIM:204100",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "clingen_gene_validity" / "clingen_gene_validity.csv").write_text(
        "\n".join(
            [
                '"CLINGEN GENE DISEASE VALIDITY CURATIONS","","","","","","","","",""',
                (
                    '"GENE SYMBOL","GENE ID (HGNC)","DISEASE LABEL","DISEASE ID (MONDO)",'
                    '"MOI","SOP","CLASSIFICATION","ONLINE REPORT","CLASSIFICATION DATE","GCEP"'
                ),
                (
                    '"RPE65","HGNC:10294","Leber congenital amaurosis 2","MONDO:0008765",'
                    '"Autosomal recessive","SOP10","Definitive","https://example.test",'
                    '"2024-03-14","Panel"'
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "gencc_download" / "gencc-download.csv").write_text(
        "\n".join(
            [
                "uuid,gene_curie,gene_symbol,disease_curie,disease_title,"
                "classification_title,moi_title,submitter_title,submitted_as_date,"
                "submitted_as_public_report_url",
                "GENCC_1,HGNC:10294,RPE65,MONDO:0008765,Leber congenital amaurosis 2,"
                "Definitive,Autosomal recessive inheritance,ClinGen,2024-03-14,"
                "https://example.test/gencc",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return root


def test_local_search_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/search", params={"q": "RPE65"})

    assert response.status_code == 401


def test_local_app_wires_search_services(auth_client: TestClient) -> None:
    assert getattr(auth_client.app.state, "search_service", None) is not None
    assert getattr(auth_client.app.state, "search_index_service", None) is not None
    assert getattr(auth_client.app.state, "search_answer_service", None) is not None

    response = auth_client.get("/api/v1/search", params={"q": "not-indexed"})

    assert response.status_code == 200
    assert response.json() == {"query": "not-indexed", "results": []}


def test_local_search_limit_bounds_are_enforced(auth_client: TestClient) -> None:
    too_small = auth_client.get("/api/v1/search", params={"q": "RPE65", "limit": 0})
    too_large = auth_client.get("/api/v1/search", params={"q": "RPE65", "limit": 51})

    assert too_small.status_code == 422
    assert too_large.status_code == 422


def test_local_search_route_is_rate_limited(auth_client: TestClient) -> None:
    _set_search_limit(auth_client)

    first = auth_client.get("/api/v1/search", params={"q": "RPE65"})
    second = auth_client.get("/api/v1/search", params={"q": "RPE65"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["Retry-After"]


def test_local_search_answer_stays_disabled_without_answer_chain(
    auth_client: TestClient,
) -> None:
    response = auth_client.post("/api/v1/search/answer", json={"query": "RPE65"})

    assert response.status_code == 503
    assert response.json()["detail"] == "AI search answers are disabled."


def test_local_search_answer_enabled_without_chain_returns_stable_503(
    auth_client: TestClient,
) -> None:
    _enable_fake_search_answer(auth_client, None)

    response = auth_client.post("/api/v1/search/answer", json={"query": "RPE65"})

    assert response.status_code == 503
    assert response.json()["detail"] == "AI search answer model is not configured."


def test_local_search_answer_fake_chain_returns_grounded_results_and_citations(
    auth_client: TestClient,
) -> None:
    _index_answer_fixture(auth_client)
    fake_chain = FakeSearchAnswerChain(citations=[{"run_id": "run_answer_grounded"}])
    _enable_fake_search_answer(auth_client, fake_chain)

    response = auth_client.post(
        "/api/v1/search/answer",
        json={"query": "answerhardening", "limit": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "answerhardening"
    assert body["grounded"] is True
    assert body["answer"] == "The indexed RPE65 run supports a grounded answer."
    assert body["citations"] == [
        {
            "run_id": "run_answer_grounded",
            "report_id": None,
            "title": "Grounded RPE65 answer run",
        }
    ]
    assert {
        "run:answer-grounded",
        "gene:rpe65-answer",
    }.issubset({item["source_key"] for item in body["results"]})

    assert len(fake_chain.invocations) == 1
    context = json.loads(fake_chain.invocations[0]["results_context"])
    assert {item["doc_type"] for item in context} >= {"run", "gene"}
    assert any(item["run_id"] == "run_answer_grounded" for item in context)


def test_local_search_answer_drops_model_citations_not_tied_to_returned_hits(
    auth_client: TestClient,
) -> None:
    _index_answer_fixture(auth_client)
    fake_chain = FakeSearchAnswerChain(
        citations=[
            {"run_id": "run_answer_grounded"},
            {"run_id": "run_missing"},
            {},
        ]
    )
    _enable_fake_search_answer(auth_client, fake_chain)

    response = auth_client.post(
        "/api/v1/search/answer",
        json={"query": "answerhardening", "limit": 5},
    )

    assert response.status_code == 200
    assert response.json()["citations"] == [
        {
            "run_id": "run_answer_grounded",
            "report_id": None,
            "title": "Grounded RPE65 answer run",
        }
    ]


def test_run_creation_indexes_new_run_for_local_search(auth_client: TestClient) -> None:
    _save_search_fixture_report(auth_client)

    created = auth_client.post(
        "/api/v1/runs",
        json={"patient_id": "SEARCH-LOCAL-001", "report_ids": ["report_search_local"]},
    )
    assert created.status_code == 200
    run_id = created.json()["run_id"]

    by_run_id = auth_client.get("/api/v1/search", params={"q": run_id, "limit": 5})
    assert by_run_id.status_code == 200
    assert any(item["run_id"] == run_id for item in by_run_id.json()["results"])

    by_gene = auth_client.get("/api/v1/search", params={"q": "RPE65", "limit": 5})
    assert by_gene.status_code == 200
    assert any(item["run_id"] == run_id for item in by_gene.json()["results"])


def test_search_filters_private_run_results_by_authenticated_owner(client: TestClient) -> None:
    owner_headers = _auth_headers(client, "search-owner")
    other_headers = _auth_headers(client, "search-other")
    _save_search_fixture_report(client, report_id="report_search_owner")

    created = client.post(
        "/api/v1/runs",
        json={"patient_id": "SEARCH-PRIVATE-001", "report_ids": ["report_search_owner"]},
        headers=owner_headers,
    )
    assert created.status_code == 200
    run_id = created.json()["run_id"]

    owner_result = client.get(
        "/api/v1/search",
        params={"q": "SEARCH-PRIVATE-001", "limit": 5},
        headers=owner_headers,
    )
    assert owner_result.status_code == 200
    assert [item["run_id"] for item in owner_result.json()["results"]] == [run_id]
    assert owner_result.json()["results"][0]["visibility_scope"] == "private"

    other_result = client.get(
        "/api/v1/search",
        params={"q": "SEARCH-PRIVATE-001", "limit": 5},
        headers=other_headers,
    )
    assert other_result.status_code == 200
    assert other_result.json()["results"] == []

    raw_text_result = client.get(
        "/api/v1/search",
        params={"q": "Asp87Gly search fixture", "limit": 5},
        headers=other_headers,
    )
    assert raw_text_result.status_code == 200
    assert raw_text_result.json()["results"] == []


def test_ownerless_private_search_rows_are_hidden_and_reported_by_health(
    auth_client: TestClient,
) -> None:
    auth_client.app.state.search_repo.upsert_document(
        SearchDocumentWrite(
            source_key="run:ownerless",
            doc_type="run",
            run_id="run_ownerless",
            patient_id="OWNERLESS-001",
            report_title="Ownerless private row",
            summary_text="Ownerless private search content",
            search_text="Ownerless private search content",
        )
    )

    response = auth_client.get("/api/v1/search", params={"q": "OWNERLESS-001", "limit": 5})
    assert response.status_code == 200
    assert response.json()["results"] == []

    health = auth_client.get("/api/v1/health/provider-cache")
    assert health.status_code == 200
    search = health.json()["search"]
    assert search["private_rows_without_owner_count"] == 1
    assert search["backfill_required_for_ownerless_private_rows"] is True


def test_search_index_backfill_is_dry_run_first_and_owner_scoped(client: TestClient) -> None:
    owner_headers, owner_user_id = _register_user(client, "search-backfill-owner")
    _save_search_fixture_report(client, report_id="report_search_backfill")

    dry_run = run_backfill(
        apply=False,
        owner_user_id=owner_user_id,
        settings=client.app.state.settings,
    )
    assert dry_run["dry_run"] is True
    assert dry_run["documents_planned"] == 1
    assert dry_run["documents_indexed"] == 0
    assert dry_run["source_downloads_performed"] is False
    assert dry_run["provider_calls_performed"] is False
    assert dry_run["supabase_mutation_performed"] is False

    missing = client.get(
        "/api/v1/search",
        params={"q": "Search Local RPE65 Case", "limit": 5},
        headers=owner_headers,
    )
    assert missing.status_code == 200
    assert missing.json()["results"] == []

    applied = run_backfill(
        apply=True,
        owner_user_id=owner_user_id,
        settings=client.app.state.settings,
    )
    assert applied["dry_run"] is False
    assert applied["documents_indexed"] == 1
    assert applied["ownerless_private_rows"] == 0

    found = client.get(
        "/api/v1/search",
        params={"q": "Search Local RPE65 Case", "limit": 5},
        headers=owner_headers,
    )
    assert found.status_code == 200
    assert [item["report_id"] for item in found.json()["results"]] == ["report_search_backfill"]


def test_search_index_backfill_includes_public_gene_and_source_rows(client: TestClient) -> None:
    headers, owner_user_id = _register_user(client, "search-backfill-source-owner")
    client.app.state.run_repo.create_run(
        run_id="run_search_backfill_source",
        patient_id="SEARCH-BACKFILL-SOURCE-001",
        report_ids=[],
        run_status=RunStatus.completed,
        report_payload=_source_backed_report_payload(),
        evidence=[],
        warnings=[],
    )

    dry_run = run_backfill(
        apply=False,
        owner_user_id=owner_user_id,
        settings=client.app.state.settings,
    )
    assert dry_run["documents_planned"] == 5
    assert dry_run["source_downloads_performed"] is False
    assert dry_run["provider_calls_performed"] is False
    assert dry_run["supabase_mutation_performed"] is False

    applied = run_backfill(
        apply=True,
        owner_user_id=owner_user_id,
        settings=client.app.state.settings,
    )
    assert applied["documents_indexed"] == 5

    gene = client.get(
        "/api/v1/search",
        params={"q": "RPE65", "doc_type": "gene", "limit": 5},
        headers=headers,
    )
    assert gene.status_code == 200
    assert [item["source_key"] for item in gene.json()["results"]] == ["gene:rpe65"]

    source = client.get(
        "/api/v1/search",
        params={"q": "gnomAD", "doc_type": "source", "limit": 5},
        headers=headers,
    )
    assert source.status_code == 200
    assert [item["source_key"] for item in source.json()["results"]] == ["source:gnomad"]


def test_search_index_backfill_includes_public_clinical_source_asset_rows(
    client: TestClient,
    tmp_path: Path,
) -> None:
    headers = _auth_headers(client, "search-clinical-source")
    source_asset_root = _clinical_search_asset_root(tmp_path)

    dry_run = run_backfill(
        apply=False,
        include_clinical_source_assets=True,
        clinical_source_asset_root=source_asset_root,
        settings=client.app.state.settings,
    )
    assert dry_run["documents_planned"] == 2
    assert dry_run["clinical_source_assets_included"] is True
    assert dry_run["clinical_source_documents_planned"] == 2
    assert dry_run["clinical_source_documents_indexed"] == 0
    assert dry_run["source_downloads_performed"] is False
    assert dry_run["provider_calls_performed"] is False
    assert dry_run["supabase_mutation_performed"] is False
    assert dry_run["startup_backfill"] is False

    applied = run_backfill(
        apply=True,
        include_clinical_source_assets=True,
        clinical_source_asset_root=source_asset_root,
        settings=client.app.state.settings,
    )
    assert applied["clinical_source_documents_indexed"] == 2

    condition = client.get(
        "/api/v1/search",
        params={"q": "Leber congenital amaurosis", "doc_type": "condition", "limit": 5},
        headers=headers,
    )
    assert condition.status_code == 200
    assert [
        (item["doc_type"], item["visibility_scope"], item["title"])
        for item in condition.json()["results"]
    ] == [("condition", "public", "Leber congenital amaurosis 2")]
    condition_hit = condition.json()["results"][0]
    assert condition_hit["source_key"] == "condition:mondo:0008765"
    assert condition_hit["target_href"] == "/report?q=Leber%20congenital%20amaurosis%202"
    assert condition_hit["metadata"]["condition_id"] == "MONDO:0008765"
    assert condition_hit["metadata"]["hpo_phenotype_count"] == 1
    assert condition_hit["metadata"]["gene_count"] == 1
    assert condition_hit["metadata"]["source_status"] == "tracked_clinical_source_asset"

    gene_disease = client.get(
        "/api/v1/search",
        params={"q": "RPE65", "doc_type": "gene_disease", "limit": 5},
        headers=headers,
    )
    assert gene_disease.status_code == 200
    assert [
        (item["doc_type"], item["visibility_scope"], item["title"])
        for item in gene_disease.json()["results"]
    ] == [("gene_disease", "public", "RPE65 - Leber congenital amaurosis 2")]
    gene_disease_hit = gene_disease.json()["results"][0]
    assert gene_disease_hit["metadata"]["gene"] == "RPE65"
    assert gene_disease_hit["metadata"]["disease_id"] == "MONDO:0008765"
    assert gene_disease_hit["metadata"]["clingen_classification"] == "Definitive"
    assert gene_disease_hit["metadata"]["gencc_assertions"] == "Definitive"
    assert gene_disease_hit["target_href"] == (
        "/report?q=RPE65%20Leber%20congenital%20amaurosis%202"
    )


def test_source_backed_publication_trial_and_section_rows_are_indexed(
    client: TestClient,
) -> None:
    owner_headers, owner_user_id = _register_user(client, "search-source-owner")
    other_headers = _auth_headers(client, "search-source-other")
    _persist_source_backed_run(client, owner_user_id=owner_user_id)

    publication = client.get(
        "/api/v1/search",
        params={"q": "retinal dystrophy", "doc_type": "publication", "limit": 5},
        headers=other_headers,
    )
    assert publication.status_code == 200
    assert [
        (item["doc_type"], item["visibility_scope"], item["title"])
        for item in publication.json()["results"]
    ] == [
        (
            "publication",
            "public",
            "RPE65 gene therapy in inherited retinal dystrophy",
        )
    ]
    publication_hit = publication.json()["results"][0]
    assert publication_hit["source_key"] == "publication:pmid:12345678"
    assert publication_hit["target_href"] == "https://pubmed.ncbi.nlm.nih.gov/12345678/"
    assert publication_hit["metadata"]["pmid"] == "12345678"
    assert publication_hit["metadata"]["source_status"] == "source_backed"

    trial = client.get(
        "/api/v1/search",
        params={"q": "NCT01234567", "doc_type": "trial", "limit": 5},
        headers=other_headers,
    )
    assert trial.status_code == 200
    assert [
        (item["doc_type"], item["visibility_scope"], item["title"])
        for item in trial.json()["results"]
    ] == [("trial", "public", "RPE65 retinal dystrophy registry study")]
    trial_hit = trial.json()["results"][0]
    assert trial_hit["source_key"] == "trial:NCT01234567"
    assert trial_hit["target_href"] == "https://clinicaltrials.gov/study/NCT01234567"
    assert trial_hit["metadata"]["nct_id"] == "NCT01234567"
    assert trial_hit["metadata"]["match_level"] == "variant_level"

    gene = client.get(
        "/api/v1/search",
        params={"q": "RPE65", "doc_type": "gene", "limit": 5},
        headers=other_headers,
    )
    assert gene.status_code == 200
    assert [
        (item["doc_type"], item["visibility_scope"], item["title"])
        for item in gene.json()["results"]
    ] == [("gene", "public", "RPE65")]
    gene_hit = gene.json()["results"][0]
    assert gene_hit["source_key"] == "gene:rpe65"
    assert gene_hit["subtitle"] == "1 publication | 1 trial"
    assert gene_hit["target_href"] == "/report?q=RPE65"
    assert gene_hit["metadata"]["gene"] == "RPE65"
    assert gene_hit["metadata"]["source_status"] == "source_backed_public_payload"

    source = client.get(
        "/api/v1/search",
        params={"q": "gnomAD", "doc_type": "source", "limit": 5},
        headers=other_headers,
    )
    assert source.status_code == 200
    assert [
        (item["doc_type"], item["visibility_scope"], item["title"])
        for item in source.json()["results"]
    ] == [("source", "public", "gnomAD population frequencies")]
    source_hit = source.json()["results"][0]
    assert source_hit["source_key"] == "source:gnomad"
    assert source_hit["subtitle"] == "fresh | static | gnomAD v4.1.1"
    assert source_hit["metadata"]["source_id"] == "gnomad"
    assert source_hit["metadata"]["source_version"] == "gnomAD v4.1.1"
    assert source_hit["metadata"]["source_status"] == "report_data_currency"

    owner_section = client.get(
        "/api/v1/search",
        params={"q": "source-backed publication row", "doc_type": "report_section", "limit": 5},
        headers=owner_headers,
    )
    assert owner_section.status_code == 200
    assert [
        (item["doc_type"], item["visibility_scope"], item["title"])
        for item in owner_section.json()["results"]
    ] == [("report_section", "private", "Publication Literature: 1 publication(s)")]

    other_section = client.get(
        "/api/v1/search",
        params={"q": "source-backed publication row", "doc_type": "report_section", "limit": 5},
        headers=other_headers,
    )
    assert other_section.status_code == 200
    assert other_section.json()["results"] == []


def test_variant_view_counter_indexes_public_popular_variant_metadata(
    client: TestClient,
) -> None:
    headers = _auth_headers(client, "search-popular-viewer")
    query_id = "USH2A c.2276G>T"

    first = client.post(f"/api/v1/library/views/{quote(query_id, safe='')}")
    second = client.post(f"/api/v1/library/views/{quote(query_id, safe='')}")
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["variant"]["view_count"] == 2

    result = client.get(
        "/api/v1/search",
        params={"q": "USH2A", "doc_type": "popular_variant", "limit": 5},
        headers=headers,
    )

    assert result.status_code == 200
    assert [
        (item["doc_type"], item["visibility_scope"], item["title"])
        for item in result.json()["results"]
    ] == [("popular_variant", "public", "USH2A c.2276G>T")]
    hit = result.json()["results"][0]
    assert hit["source_key"].startswith("popular_variant:")
    assert hit["subtitle"] == "2 views"
    assert hit["target_href"] == f"/report?q={quote('ush2a c.2276g>t')}"
    assert hit["metadata"]["query_id"] == "ush2a c.2276g>t"
    assert hit["metadata"]["view_count"] == 2
    assert hit["metadata"]["source_status"] == "public_view_counter"
    assert hit["metadata"]["last_viewed"] is not None


def test_run_report_payload_approve_and_drop_refresh_search_rows(client: TestClient) -> None:
    owner_headers, owner_user_id = _register_user(client, "search-refresh-owner")
    run_id = "run_search_refresh"
    _persist_source_backed_run(
        client,
        owner_user_id=owner_user_id,
        run_id=run_id,
        summary="Original indexed source summary",
    )

    updated = client.patch(
        f"/api/v1/runs/{run_id}/report-payload",
        json={"ai_clinical_summary": "Updated indexed source summary"},
        headers=owner_headers,
    )
    assert updated.status_code == 200

    updated_hit = client.get(
        "/api/v1/search",
        params={"q": "Updated indexed source summary", "doc_type": "run", "limit": 5},
        headers=owner_headers,
    )
    assert updated_hit.status_code == 200
    assert [item["run_id"] for item in updated_hit.json()["results"]] == [run_id]

    approved = client.post(f"/api/v1/runs/{run_id}/approve", headers=owner_headers)
    assert approved.status_code == 200
    approved_hit = client.get(
        "/api/v1/search",
        params={
            "q": run_id,
            "doc_type": "run",
            "review_status": "approved",
            "limit": 5,
        },
        headers=owner_headers,
    )
    assert approved_hit.status_code == 200
    assert [item["run_id"] for item in approved_hit.json()["results"]] == [run_id]

    dropped = client.post(
        f"/api/v1/runs/{run_id}/drop",
        json={"review_note": "Search refresh drop note"},
        headers=owner_headers,
    )
    assert dropped.status_code == 200
    dropped_hit = client.get(
        "/api/v1/search",
        params={
            "q": "Search refresh drop note",
            "doc_type": "run",
            "review_status": "dropped",
            "limit": 5,
        },
        headers=owner_headers,
    )
    assert dropped_hit.status_code == 200
    assert [item["run_id"] for item in dropped_hit.json()["results"]] == [run_id]


def test_saved_library_variant_is_indexed_for_owner_search(client: TestClient) -> None:
    owner_headers, _owner_user_id = _register_user(client, "search-library-owner")
    other_headers, _other_user_id = _register_user(client, "search-library-other")

    saved = client.post(
        "/api/v1/library/variants",
        json=_saved_library_variant_payload(),
        headers=owner_headers,
    )
    assert saved.status_code == 201

    owner_result = client.get(
        "/api/v1/search",
        params={"q": "USH2A", "doc_type": "library_variant", "limit": 5},
        headers=owner_headers,
    )
    assert owner_result.status_code == 200
    assert [
        (item["doc_type"], item["visibility_scope"], item["title"])
        for item in owner_result.json()["results"]
    ] == [("library_variant", "private", "USH2A c.2276G>T")]
    assert "likely pathogenic" in owner_result.json()["results"][0]["snippet"]

    other_result = client.get(
        "/api/v1/search",
        params={"q": "USH2A", "doc_type": "library_variant", "limit": 5},
        headers=other_headers,
    )
    assert other_result.status_code == 200
    assert other_result.json()["results"] == []

    removed = client.delete(
        f"/api/v1/library/variants/{quote('ush2a:c.2276g>t', safe='')}",
        headers=owner_headers,
    )
    assert removed.status_code == 204

    after_delete = client.get(
        "/api/v1/search",
        params={"q": "USH2A", "doc_type": "library_variant", "limit": 5},
        headers=owner_headers,
    )
    assert after_delete.status_code == 200
    assert after_delete.json()["results"] == []


def test_library_replace_refreshes_library_variant_search_rows(client: TestClient) -> None:
    owner_headers, _owner_user_id = _register_user(client, "search-library-replace")

    replaced = client.put(
        "/api/v1/library",
        json={
            "variants": [
                _saved_library_variant_payload(
                    id="rpe65:c.260a>g",
                    gene="RPE65",
                    variant="c.260A>G",
                    query="RPE65 c.260A>G",
                    raw="RPE65 NM_000329.3:c.260A>G p.Asp87Gly search fixture.",
                    classification=None,
                    hgvs_full="NM_000329.3:c.260A>G",
                )
            ],
            "folders": [],
        },
        headers=owner_headers,
    )
    assert replaced.status_code == 200

    found = client.get(
        "/api/v1/search",
        params={"q": "RPE65", "doc_type": "library_variant", "limit": 5},
        headers=owner_headers,
    )
    assert found.status_code == 200
    assert [item["title"] for item in found.json()["results"]] == ["RPE65 c.260A>G"]

    cleared = client.put(
        "/api/v1/library",
        json={"variants": [], "folders": []},
        headers=owner_headers,
    )
    assert cleared.status_code == 200

    after_clear = client.get(
        "/api/v1/search",
        params={"q": "RPE65", "doc_type": "library_variant", "limit": 5},
        headers=owner_headers,
    )
    assert after_clear.status_code == 200
    assert after_clear.json()["results"] == []
