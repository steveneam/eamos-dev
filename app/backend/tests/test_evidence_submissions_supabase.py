from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.deps import AuthenticatedPrincipal
from app.repos.evidence_submissions_repo import (
    EvidenceSubmissionLedgerRecord,
    EvidenceSubmissionWriteError,
    SupabaseEvidenceSubmissionsRepo,
)
from app.schemas.evidence import EvidenceSubmissionRequest
from app.services.evidence_submissions import EvidenceSubmissionService


class CapturingEvidenceLedgerRepo:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def create_submission(self, **kwargs) -> EvidenceSubmissionLedgerRecord:
        self.rows.append(kwargs)
        return EvidenceSubmissionLedgerRecord(
            id=kwargs["submission_id"],
            created_at=datetime(2026, 5, 24, 6, 15, tzinfo=timezone.utc),
        )


def test_evidence_submission_service_builds_supabase_payload() -> None:
    repo = CapturingEvidenceLedgerRepo()
    service = EvidenceSubmissionService(
        settings=Settings(jwt_secret="test-secret", use_real_apis=False),
        submissions_repo=repo,
    )

    response = service.submit(
        EvidenceSubmissionRequest(
            variant_hgvs="NM_000492.4:c.199C>T",
            submitted_pmid="PMID:35901234",
            curator_notes="Functional assay supports PS3_Supporting.",
            condition_name="Cystic fibrosis",
            assay_type="protein activity assay",
            functional_consequence=["SO:0002218"],
            method="Variant activity was measured in a validated in vitro assay.",
            result="reduced activity compared with wild type",
            evidence_codes=["PS3_Supporting"],
        ),
        AuthenticatedPrincipal(
            user_id="23fc93e9-d351-4a9f-b5a7-f23dd7ceab11",
            provider="supabase",
            token="supabase-access-token",
            email="curator@example.com",
        ),
    )

    assert response.ledger_status == "recorded"
    assert len(repo.rows) == 1
    row = repo.rows[0]
    assert row["submission_id"] == response.submission_id
    assert row["user_id"] == "23fc93e9-d351-4a9f-b5a7-f23dd7ceab11"
    assert row["clinvar_tracking_id"] == response.clinvar_tracking_id

    submission_payload = row["submission_payload"]
    assert submission_payload["schema_version"] == "eamos_user_evidence_submission_v1"
    assert submission_payload["payload_status"] == "ready_for_clinvar_dry_run"
    assert submission_payload["pubmed"]["status"] == "unchecked"
    assert submission_payload["clinvar_payload"]["tracking_id"] == response.clinvar_tracking_id
    assert submission_payload["submitted_fields"]["evidence_codes"] == ["PS3_Supporting"]


def test_supabase_repo_posts_ledger_row_to_postgrest() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content.decode("utf-8"))
        assert body["id"] == "8c2695fb-72b7-47a8-aa29-6f1d5797127c"
        assert body["user_id"] == "23fc93e9-d351-4a9f-b5a7-f23dd7ceab11"
        assert body["clinvar_tracking_id"] == "EAMOS-EVS-20260524-ABC123"
        assert body["submission_payload"]["schema_version"] == "eamos_user_evidence_submission_v1"
        assert "pubmed_validation" not in body
        assert "clinvar_payload" not in body
        return httpx.Response(
            status_code=201,
            json=[
                {
                    "id": body["id"],
                    "created_at": "2026-05-24T06:20:00Z",
                }
            ],
        )

    repo = SupabaseEvidenceSubmissionsRepo(
        supabase_url="https://cpdjxsgasaesysvxkpmi.supabase.co/",
        service_role_key="service-role-key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    record = repo.create_submission(
        submission_id="8c2695fb-72b7-47a8-aa29-6f1d5797127c",
        user_id="23fc93e9-d351-4a9f-b5a7-f23dd7ceab11",
        variant_hgvs="NM_000492.4:c.199C>T",
        submitted_pmid="35901234",
        curator_notes="Curator note.",
        clinvar_tracking_id="EAMOS-EVS-20260524-ABC123",
        pubmed_validation={"status": "unchecked"},
        clinvar_payload={"payload_status": "draft_needs_curator_fields"},
        submission_payload={
            "schema_version": "eamos_user_evidence_submission_v1",
            "pubmed": {"status": "unchecked"},
        },
    )

    assert record.id == "8c2695fb-72b7-47a8-aa29-6f1d5797127c"
    assert record.created_at == datetime(2026, 5, 24, 6, 20, tzinfo=timezone.utc)
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == (
        "https://cpdjxsgasaesysvxkpmi.supabase.co/rest/v1/user_evidence_submissions"
    )
    assert request.headers["apikey"] == "service-role-key"
    assert request.headers["authorization"] == "Bearer service-role-key"
    assert request.headers["prefer"] == "return=representation"


def test_evidence_submission_returns_503_when_ledger_write_fails(
    auth_client: TestClient,
) -> None:
    class FailingRepo:
        def create_submission(self, **kwargs):
            raise EvidenceSubmissionWriteError("boom")

    auth_client.app.state.evidence_submission_service = EvidenceSubmissionService(
        settings=auth_client.app.state.settings,
        submissions_repo=FailingRepo(),
    )

    response = auth_client.post(
        "/api/v1/evidence-submissions",
        json={"variant_hgvs": "NM_000492.4:c.199C>T", "submitted_pmid": "35901234"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Evidence submission ledger write failed."
