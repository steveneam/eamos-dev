from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from app.core.db import build_session_factory, initialize_database
from app.core.ownership import OwnerIdentity


def _register(client: TestClient, username: str) -> tuple[dict[str, str], str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "test-password"},
    )
    assert response.status_code == 201
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["user_id"]


def _upload_report(client: TestClient, headers: dict[str, str], pdf_bytes: bytes) -> str:
    response = client.post(
        "/api/v1/reports/upload",
        files={"file": ("owner-test.pdf", pdf_bytes, "application/pdf")},
        data={"report_kind": "test"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["report"]["report_id"]


def _create_run(
    client: TestClient,
    headers: dict[str, str],
    report_id: str,
) -> str:
    response = client.post(
        "/api/v1/runs",
        json={"patient_id": "OWNER-001", "report_ids": [report_id]},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["run_id"]


def _supabase_headers(client: TestClient, user_id: str) -> dict[str, str]:
    secret = "supabase-owner-test-secret-at-least-32-bytes"
    issuer = "https://owner-test.supabase.co/auth/v1"
    client.app.state.settings.supabase_jwt_secret = secret
    client.app.state.settings.supabase_jwt_algorithm = "HS256"
    client.app.state.settings.supabase_url = "https://owner-test.supabase.co"
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "iss": issuer,
            "aud": "authenticated",
            "sub": user_id,
            "role": "authenticated",
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_other_user_cannot_read_or_mutate_run(
    client: TestClient,
    pdf_bytes: bytes,
) -> None:
    owner_headers, _owner_user_id = _register(client, "run-owner")
    other_headers, _other_user_id = _register(client, "run-other")
    report_id = _upload_report(client, owner_headers, pdf_bytes)
    run_id = _create_run(client, owner_headers, report_id)

    attempts = [
        ("GET", f"/api/v1/runs/{run_id}", None),
        (
            "POST",
            f"/api/v1/runs/{run_id}/review",
            {"reviewer_name": "Other", "review_note": "Cross-tenant review"},
        ),
        (
            "POST",
            f"/api/v1/reports/{run_id}/review",
            {"reviewer_name": "Other", "review_note": "Legacy cross-tenant review"},
        ),
        (
            "PATCH",
            f"/api/v1/runs/{run_id}/report-payload",
            {"ai_clinical_summary": "Cross-tenant edit"},
        ),
        ("POST", f"/api/v1/runs/{run_id}/chat", {"question": "Show the report"}),
        (
            "POST",
            f"/api/v1/runs/{run_id}/chat/stream",
            {"question": "Stream the report"},
        ),
        ("POST", f"/api/v1/runs/{run_id}/approve", None),
        ("POST", f"/api/v1/runs/{run_id}/drop", {"review_note": "Cross-tenant drop"}),
        ("GET", f"/api/v1/runs/{run_id}/pdf", None),
        ("HEAD", f"/api/v1/runs/{run_id}/pdf", None),
    ]

    for method, path, payload in attempts:
        response = client.request(method, path, json=payload, headers=other_headers)
        assert response.status_code == 404, (method, path, response.text)
        if method == "HEAD":
            assert response.content == b""
        else:
            assert response.json()["detail"] == "Run not found."

    owner_response = client.get(f"/api/v1/runs/{run_id}", headers=owner_headers)
    assert owner_response.status_code == 200
    assert owner_response.json()["review_status"] == "pending_review"


def test_other_user_cannot_create_run_from_foreign_report(
    client: TestClient,
    pdf_bytes: bytes,
) -> None:
    owner_headers, _owner_user_id = _register(client, "report-owner")
    other_headers, _other_user_id = _register(client, "report-other")
    report_id = _upload_report(client, owner_headers, pdf_bytes)

    response = client.post(
        "/api/v1/runs",
        json={"patient_id": "CROSS-TENANT", "report_ids": [report_id]},
        headers=other_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == f"Reports not found: {report_id}"


def test_ownerless_legacy_run_fails_closed(
    client: TestClient,
    pdf_bytes: bytes,
) -> None:
    owner_headers, _owner_user_id = _register(client, "legacy-run-owner")
    report_id = _upload_report(client, owner_headers, pdf_bytes)
    run_id = _create_run(client, owner_headers, report_id)
    engine = client.app.state.db_session_factory.kw["bind"]
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE report_runs SET owner_user_id = NULL, owner_provider = NULL "
                "WHERE run_id = :run_id"
            ),
            {"run_id": run_id},
        )

    response = client.get(f"/api/v1/runs/{run_id}", headers=owner_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Run not found."


def test_initialize_database_backfills_unambiguous_legacy_local_owner(
    client: TestClient,
    pdf_bytes: bytes,
) -> None:
    owner_headers, _owner_user_id = _register(client, "legacy-backfill-owner")
    other_headers, _other_user_id = _register(client, "legacy-backfill-other")
    report_id = _upload_report(client, owner_headers, pdf_bytes)
    run_id = _create_run(client, owner_headers, report_id)
    engine = client.app.state.db_session_factory.kw["bind"]
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE reports SET owner_user_id = NULL, owner_provider = NULL "
                "WHERE report_id = :report_id"
            ),
            {"report_id": report_id},
        )
        connection.execute(
            text(
                "UPDATE report_runs SET owner_user_id = NULL, owner_provider = NULL "
                "WHERE run_id = :run_id"
            ),
            {"run_id": run_id},
        )

    initialize_database(client.app.state.db_session_factory)

    owner_response = client.get(f"/api/v1/runs/{run_id}", headers=owner_headers)
    other_response = client.get(f"/api/v1/runs/{run_id}", headers=other_headers)
    assert owner_response.status_code == 200
    assert other_response.status_code == 404


def test_supabase_principal_isolated_from_same_user_id_in_local_namespace(
    client: TestClient,
    pdf_bytes: bytes,
) -> None:
    user_id = "7ce9bf16-f54a-4db7-a56d-63ca63ef8ef3"
    headers = _supabase_headers(client, user_id)
    report_id = _upload_report(client, headers, pdf_bytes)
    run_id = _create_run(client, headers, report_id)

    response = client.get(f"/api/v1/runs/{run_id}", headers=headers)

    assert response.status_code == 200
    local_identity = OwnerIdentity(provider="eamos", user_id=user_id)
    assert client.app.state.reports_repo.get_for_owner(report_id, owner=local_identity) is None
    assert client.app.state.run_repo.get_run_for_owner(run_id, owner=local_identity) is None


def test_run_review_route_is_registered_once(app) -> None:
    def walk_routes(routes):
        for route in routes:
            original_router = getattr(route, "original_router", None)
            if original_router is not None:
                yield from walk_routes(original_router.routes)
            else:
                yield route

    matches = [
        route
        for route in walk_routes(app.routes)
        if getattr(route, "path", None) == "/api/v1/runs/{run_id}/review"
        and "POST" in getattr(route, "methods", set())
    ]

    assert len(matches) == 1


def test_initialize_database_adds_owner_columns_to_legacy_tables(tmp_path) -> None:
    session_factory = build_session_factory(
        f"sqlite+pysqlite:///{(tmp_path / 'legacy-owner.db').as_posix()}"
    )
    engine = session_factory.kw["bind"]
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE reports (report_id VARCHAR(64) PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE report_runs (run_id VARCHAR(64) PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE search_documents ("
                "doc_id INTEGER PRIMARY KEY, "
                "source_key VARCHAR(96), "
                "report_id VARCHAR(64), "
                "run_id VARCHAR(64)"
                ")"
            )
        )

    initialize_database(session_factory)

    report_columns = {column["name"] for column in inspect(engine).get_columns("reports")}
    run_columns = {column["name"] for column in inspect(engine).get_columns("report_runs")}
    search_columns = {column["name"] for column in inspect(engine).get_columns("search_documents")}
    assert {"owner_user_id", "owner_provider"} <= report_columns
    assert {"owner_user_id", "owner_provider"} <= run_columns
    assert {"visibility_scope", "owner_user_id", "metadata_json"} <= search_columns
