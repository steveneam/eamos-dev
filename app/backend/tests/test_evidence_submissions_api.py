from __future__ import annotations

from types import SimpleNamespace

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core import deps as deps_module


def _evidence_payload() -> dict:
    return {"variant_hgvs": "NM_000492.4:c.199C>T", "submitted_pmid": "35901234"}


def test_evidence_submission_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/evidence-submissions",
        json=_evidence_payload(),
    )

    assert response.status_code == 401


def test_evidence_submission_accepts_supabase_hs256_token(client: TestClient) -> None:
    client.app.state.settings.supabase_jwt_secret = "supabase-test-secret"
    client.app.state.settings.supabase_jwt_algorithm = "auto"

    token = jwt.encode(
        {
            "sub": "supabase-user-hs256",
            "aud": "authenticated",
            "role": "authenticated",
            "email": "hs256@example.com",
        },
        "supabase-test-secret",
        algorithm="HS256",
    )
    response = client.post(
        "/api/v1/evidence-submissions",
        json=_evidence_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == "supabase-user-hs256"


def test_evidence_submission_accepts_supabase_es256_jwks_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ec = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ec")

    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    client.app.state.settings.supabase_jwt_algorithm = "auto"
    client.app.state.settings.supabase_jwt_secret = None
    client.app.state.settings.supabase_url = "https://cpdjxsgasaesysvxkpmi.supabase.co"
    client.app.state.settings.supabase_jwks_url = None
    client.app.state.settings.supabase_jwt_public_key = None

    token = jwt.encode(
        {
            "sub": "supabase-user-es256",
            "aud": "authenticated",
            "role": "authenticated",
            "email": "es256@example.com",
        },
        private_key,
        algorithm="ES256",
        headers={"kid": "test-key"},
    )

    seen: dict[str, str] = {}

    class FakeJwkClient:
        def get_signing_key_from_jwt(self, received_token: str):
            seen["token"] = received_token
            return SimpleNamespace(key=public_key)

    def fake_jwk_client_for_url(jwks_url: str):
        seen["jwks_url"] = jwks_url
        return FakeJwkClient()

    monkeypatch.setattr(deps_module, "_jwk_client_for_url", fake_jwk_client_for_url)

    response = client.post(
        "/api/v1/evidence-submissions",
        json=_evidence_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == "supabase-user-es256"
    assert seen == {
        "jwks_url": "https://cpdjxsgasaesysvxkpmi.supabase.co/auth/v1/.well-known/jwks.json",
        "token": token,
    }


def test_evidence_submission_records_pubmed_and_clinvar_draft(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/evidence-submissions",
        json={
            "variant_hgvs": "NM_000492.4:c.199C>T",
            "submitted_pmid": "35901234",
            "curator_notes": "Functional assay supports PS3_Supporting.",
            "condition_name": "Cystic fibrosis",
            "assay_type": "protein activity assay",
            "functional_consequence": ["SO:0002218"],
            "method": "Variant activity was measured in a validated in vitro assay.",
            "result": "reduced activity compared with wild type",
            "evidence_codes": ["PS3_Supporting"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ledger_status"] == "recorded"
    assert body["pubmed"]["status"] == "unchecked"
    assert body["clinvar_tracking_id"].startswith("EAMOS-EVS-")
    assert body["clinvar_payload"]["payload_status"] == "ready_for_clinvar_dry_run"

    payload = body["clinvar_payload"]["payload"]
    submission = payload["noClassificationSubmission"][0]
    assert submission["variantSet"]["variant"][0]["hgvs"] == "NM_000492.4:c.199C>T"
    assert submission["conditionSet"]["condition"][0]["name"] == "Cystic fibrosis"
    functional = submission["functionalObservedIn"][0]
    assert functional["methodCitation"] == [{"db": "PubMed", "id": "35901234"}]
    assert payload["eamosEvidenceCodes"] == ["PS3_Supporting"]


def test_evidence_submission_rejects_non_hgvs_variant(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/evidence-submissions",
        json={"variant_hgvs": "CFTR p.Leu441fs", "submitted_pmid": "35901234"},
    )

    assert response.status_code == 422


def test_evidence_submission_marks_incomplete_clinvar_payload(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/evidence-submissions",
        json={
            "variant_hgvs": "NM_000492.4:c.199C>T",
            "submitted_pmid": "PMID:35901234",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["submitted_pmid"] == "35901234"
    assert body["clinvar_payload"]["payload_status"] == "draft_needs_curator_fields"
    assert "condition_name" in body["clinvar_payload"]["missing_required_fields"]
    assert "clinvar_payload_needs_curator_fields" in body["warnings"]
