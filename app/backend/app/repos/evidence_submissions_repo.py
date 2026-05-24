from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.db import UserEvidenceSubmissionRecord, session_scope


class EvidenceSubmissionWriteError(RuntimeError):
    pass


@dataclass(frozen=True)
class EvidenceSubmissionLedgerRecord:
    id: str
    created_at: datetime


class EvidenceSubmissionsRepo:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def create_submission(
        self,
        *,
        submission_id: str,
        user_id: str,
        variant_hgvs: str,
        submitted_pmid: str,
        curator_notes: str | None,
        clinvar_tracking_id: str,
        pubmed_validation: dict,
        clinvar_payload: dict,
        submission_payload: dict,
    ) -> EvidenceSubmissionLedgerRecord:
        with session_scope(self.session_factory) as session:
            record = UserEvidenceSubmissionRecord(
                id=submission_id,
                user_id=user_id,
                variant_hgvs=variant_hgvs,
                submitted_pmid=submitted_pmid,
                curator_notes=curator_notes,
                clinvar_tracking_id=clinvar_tracking_id,
                pubmed_validation=pubmed_validation,
                clinvar_payload=clinvar_payload,
                submission_payload=submission_payload,
            )
            session.add(record)
            session.flush()
            return EvidenceSubmissionLedgerRecord(id=record.id, created_at=record.created_at)


class SupabaseEvidenceSubmissionsRepo:
    def __init__(
        self,
        *,
        supabase_url: str,
        service_role_key: str,
        timeout_seconds: float = 10.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self.service_role_key = service_role_key
        self.timeout_seconds = timeout_seconds
        self.http_client = http_client

    def create_submission(
        self,
        *,
        submission_id: str,
        user_id: str,
        variant_hgvs: str,
        submitted_pmid: str,
        curator_notes: str | None,
        clinvar_tracking_id: str,
        pubmed_validation: dict,
        clinvar_payload: dict,
        submission_payload: dict,
    ) -> EvidenceSubmissionLedgerRecord:
        row = {
            "id": submission_id,
            "user_id": user_id,
            "variant_hgvs": variant_hgvs,
            "submitted_pmid": submitted_pmid,
            "curator_notes": curator_notes,
            "clinvar_tracking_id": clinvar_tracking_id,
            "submission_payload": submission_payload,
        }
        response = self._post_row(row)
        returned = self._extract_returned_row(response)
        return EvidenceSubmissionLedgerRecord(
            id=str(returned.get("id") or submission_id),
            created_at=_parse_created_at(returned.get("created_at")),
        )

    def _post_row(self, row: dict[str, Any]) -> httpx.Response:
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        try:
            if self.http_client is None:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(
                        f"{self.supabase_url}/rest/v1/user_evidence_submissions",
                        headers=headers,
                        json=row,
                    )
            else:
                response = self.http_client.post(
                    f"{self.supabase_url}/rest/v1/user_evidence_submissions",
                    headers=headers,
                    json=row,
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EvidenceSubmissionWriteError(
                f"Supabase evidence submission write failed: {type(exc).__name__}"
            ) from exc
        return response

    def _extract_returned_row(self, response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError as exc:
            raise EvidenceSubmissionWriteError(
                "Supabase evidence submission write returned invalid JSON."
            ) from exc

        if isinstance(body, list) and body and isinstance(body[0], dict):
            return body[0]
        if isinstance(body, dict):
            return body
        raise EvidenceSubmissionWriteError(
            "Supabase evidence submission write returned no row representation."
        )


def _parse_created_at(value: Any) -> datetime:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)
