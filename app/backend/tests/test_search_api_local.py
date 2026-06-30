from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.cli.eamos_search_index_backfill import run_backfill
from app.core.rate_limit import InMemoryRateLimiter
from app.schemas.report import ExtractedCase, ExtractedVariant, UploadedReport
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
