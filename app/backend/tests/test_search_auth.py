from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.core import deps as deps_module
from app.schemas.search import SearchDocumentWrite


class _SearchAnswerChain:
    def invoke(self, _payload: dict[str, str]) -> dict[str, object]:
        return {
            "answer": "Only the caller's indexed evidence was used.",
            "grounded": True,
            "citations": [],
        }


def _register(client: TestClient, username: str) -> tuple[dict[str, str], str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "test-password"},
    )
    assert response.status_code == 201
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["user_id"]


def _index_private_result(
    client: TestClient,
    *,
    owner_user_id: str,
    source_key: str,
    run_id: str,
    search_term: str,
) -> None:
    client.app.state.search_repo.upsert_document(
        SearchDocumentWrite(
            source_key=source_key,
            doc_type="run",
            visibility_scope="private",
            owner_user_id=owner_user_id,
            run_id=run_id,
            report_title=f"Private result for {owner_user_id}",
            identifier_text=f"{run_id} {search_term}",
            search_text=f"{search_term} owner-scoped evidence",
        )
    )


def _supabase_es256_headers(
    client: TestClient,
    monkeypatch,
    *,
    user_id: str,
) -> tuple[dict[str, str], dict[str, str]]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    supabase_url = "https://search-auth-test.supabase.co"
    client.app.state.settings.supabase_jwt_algorithm = "auto"
    client.app.state.settings.supabase_jwt_secret = None
    client.app.state.settings.supabase_url = supabase_url
    client.app.state.settings.supabase_jwks_url = None
    client.app.state.settings.supabase_jwt_public_key = None

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "iss": f"{supabase_url}/auth/v1",
            "aud": "authenticated",
            "sub": user_id,
            "role": "authenticated",
            "email": "search-owner@example.com",
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        private_key,
        algorithm="ES256",
        headers={"kid": "search-auth-test-key"},
    )
    seen: dict[str, str] = {}

    class _JwkClient:
        def get_signing_key_from_jwt(self, received_token: str):
            seen["token"] = received_token
            return SimpleNamespace(key=public_key)

    def _fake_jwk_client_for_url(jwks_url: str):
        seen["jwks_url"] = jwks_url
        return _JwkClient()

    monkeypatch.setattr(deps_module, "_jwk_client_for_url", _fake_jwk_client_for_url)
    return {"Authorization": f"Bearer {token}"}, seen


def test_search_accepts_local_token_and_keeps_private_results_owner_scoped(
    client: TestClient,
) -> None:
    owner_headers, owner_user_id = _register(client, "search-auth-local-owner")
    other_headers, other_user_id = _register(client, "search-auth-local-other")
    search_term = "local-auth-owner-boundary"
    _index_private_result(
        client,
        owner_user_id=owner_user_id,
        source_key="run:local-auth-owner",
        run_id="run_local_auth_owner",
        search_term=search_term,
    )
    _index_private_result(
        client,
        owner_user_id=other_user_id,
        source_key="run:local-auth-other",
        run_id="run_local_auth_other",
        search_term=search_term,
    )

    owner_response = client.get(
        "/api/v1/search",
        params={"q": search_term},
        headers=owner_headers,
    )
    other_response = client.get(
        "/api/v1/search",
        params={"q": search_term},
        headers=other_headers,
    )

    assert owner_response.status_code == 200
    assert {item["source_key"] for item in owner_response.json()["results"]} == {
        "run:local-auth-owner"
    }
    assert other_response.status_code == 200
    assert {item["source_key"] for item in other_response.json()["results"]} == {
        "run:local-auth-other"
    }


def test_search_accepts_supabase_jwt_for_query_and_answer_without_cross_user_leak(
    client: TestClient,
    monkeypatch,
) -> None:
    supabase_user_id = "7ce9bf16-f54a-4db7-a56d-63ca63ef8ef3"
    other_user_id = "e7d28e42-8800-4af0-b419-6e9507ee99df"
    headers, seen = _supabase_es256_headers(
        client,
        monkeypatch,
        user_id=supabase_user_id,
    )
    search_term = "supabase-auth-owner-boundary"
    _index_private_result(
        client,
        owner_user_id=supabase_user_id,
        source_key="run:supabase-auth-owner",
        run_id="run_supabase_auth_owner",
        search_term=search_term,
    )
    _index_private_result(
        client,
        owner_user_id=other_user_id,
        source_key="run:supabase-auth-other",
        run_id="run_supabase_auth_other",
        search_term=search_term,
    )
    client.app.state.settings.search_answer_enabled = True
    client.app.state.search_answer_service.answer_chain = _SearchAnswerChain()

    query_response = client.get(
        "/api/v1/search",
        params={"q": search_term},
        headers=headers,
    )
    answer_response = client.post(
        "/api/v1/search/answer",
        json={"query": search_term},
        headers=headers,
    )

    assert query_response.status_code == 200
    assert {item["source_key"] for item in query_response.json()["results"]} == {
        "run:supabase-auth-owner"
    }
    assert answer_response.status_code == 200
    assert {item["source_key"] for item in answer_response.json()["results"]} == {
        "run:supabase-auth-owner"
    }
    assert seen["jwks_url"] == (
        "https://search-auth-test.supabase.co/auth/v1/.well-known/jwks.json"
    )
    assert seen["token"] == headers["Authorization"].removeprefix("Bearer ")
