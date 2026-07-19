from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient


def test_protected_route_rejects_missing_bearer_token(client: TestClient) -> None:
    response = client.post("/api/v1/runs", json={"patient_id": "AUTH-001", "report_ids": []})

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_supabase_token_requires_configured_issuer_and_expiry(client: TestClient) -> None:
    issuer = "https://workflow-auth.supabase.co/auth/v1"
    secret = "workflow-auth-secret-with-at-least-32-bytes"
    client.app.state.settings.supabase_jwt_secret = secret
    client.app.state.settings.supabase_jwt_algorithm = "HS256"
    client.app.state.settings.supabase_jwt_issuer = issuer
    now = datetime.now(UTC)

    valid = _supabase_token(
        secret,
        issuer=issuer,
        expires_at=now + timedelta(minutes=10),
    )
    wrong_issuer = _supabase_token(
        secret,
        issuer="https://attacker.invalid/auth/v1",
        expires_at=now + timedelta(minutes=10),
    )
    missing_issuer = _supabase_token(
        secret,
        issuer=None,
        expires_at=now + timedelta(minutes=10),
    )
    missing_expiry = _supabase_token(secret, issuer=issuer, expires_at=None)

    assert client.get(
        "/api/v1/batch/missing",
        headers={"Authorization": f"Bearer {valid}"},
    ).status_code == 404
    for token in (wrong_issuer, missing_issuer, missing_expiry):
        response = client.get(
            "/api/v1/batch/missing",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"


def _supabase_token(
    secret: str,
    *,
    issuer: str | None,
    expires_at: datetime | None,
) -> str:
    now = datetime.now(UTC)
    claims = {
        "aud": "authenticated",
        "sub": "00000000-0000-4000-8000-000000000001",
        "role": "authenticated",
        "iat": now,
    }
    if issuer is not None:
        claims["iss"] = issuer
    if expires_at is not None:
        claims["exp"] = expires_at
    return jwt.encode(claims, secret, algorithm="HS256")
