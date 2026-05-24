from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import httpx
from fastapi import HTTPException, status

from app.core.deps import AuthenticatedPrincipal
from app.repos.evidence_submissions_repo import EvidenceSubmissionWriteError
from app.schemas.evidence import (
    ClinvarSubmissionDraft,
    EvidenceSubmissionRequest,
    EvidenceSubmissionResponse,
    PubMedValidation,
)

_CLINVAR_REQUIRED_FIELDS = (
    "condition_name",
    "assay_type",
    "method",
    "result",
    "functional_consequence",
)


class PubMedValidationClient:
    def __init__(self, settings) -> None:
        self.settings = settings

    def validate(self, pmid: str) -> PubMedValidation:
        source_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        if not self.settings.use_real_apis:
            return PubMedValidation(
                pmid=pmid,
                status="unchecked",
                source_url=source_url,
                warnings=["pubmed_live_validation_disabled"],
            )

        try:
            response = httpx.get(
                f"{self.settings.clinvar_base_url}/esummary.fcgi",
                params={"db": "pubmed", "id": pmid, "retmode": "json"},
                timeout=10.0,
            )
            response.raise_for_status()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"PubMed validation failed: {type(exc).__name__}",
            ) from exc

        entry = response.json().get("result", {}).get(pmid)
        if not isinstance(entry, dict) or entry.get("error"):
            return PubMedValidation(
                pmid=pmid,
                status="not_found",
                source_url=source_url,
                warnings=["pubmed_pmid_not_found"],
            )

        return PubMedValidation(
            pmid=pmid,
            status="validated",
            title=entry.get("title"),
            journal=entry.get("source"),
            publication_date=entry.get("pubdate"),
            source_url=source_url,
        )


class EvidenceSubmissionService:
    def __init__(self, settings, submissions_repo) -> None:
        self.settings = settings
        self.submissions_repo = submissions_repo
        self.pubmed_client = PubMedValidationClient(settings)

    def submit(
        self,
        payload: EvidenceSubmissionRequest,
        principal: AuthenticatedPrincipal,
    ) -> EvidenceSubmissionResponse:
        pubmed = self.pubmed_client.validate(payload.submitted_pmid)
        if pubmed.status == "not_found":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="submitted_pmid was not found in PubMed.",
            )

        created_at = datetime.now(timezone.utc)
        tracking_id = f"EAMOS-EVS-{created_at:%Y%m%d}-{uuid4().hex[:12].upper()}"
        clinvar_payload = build_clinvar_submission_payload(payload, tracking_id)
        warnings = list(pubmed.warnings)
        if clinvar_payload.payload_status == "draft_needs_curator_fields":
            warnings.append("clinvar_payload_needs_curator_fields")

        pubmed_validation = pubmed.model_dump(mode="json")
        clinvar_payload_json = clinvar_payload.model_dump(mode="json")
        submission_payload = build_submission_payload(
            payload=payload,
            pubmed_validation=pubmed_validation,
            clinvar_payload=clinvar_payload_json,
            warnings=warnings,
        )
        try:
            record = self.submissions_repo.create_submission(
                submission_id=str(uuid4()),
                user_id=principal.user_id,
                variant_hgvs=payload.variant_hgvs,
                submitted_pmid=payload.submitted_pmid,
                curator_notes=payload.curator_notes,
                clinvar_tracking_id=tracking_id,
                pubmed_validation=pubmed_validation,
                clinvar_payload=clinvar_payload_json,
                submission_payload=submission_payload,
            )
        except EvidenceSubmissionWriteError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Evidence submission ledger write failed.",
            ) from exc
        return EvidenceSubmissionResponse(
            submission_id=record.id,
            user_id=principal.user_id,
            variant_hgvs=payload.variant_hgvs,
            submitted_pmid=payload.submitted_pmid,
            curator_notes=payload.curator_notes,
            pubmed=pubmed,
            clinvar_tracking_id=tracking_id,
            clinvar_payload=clinvar_payload,
            created_at=record.created_at,
            warnings=warnings,
        )


def build_submission_payload(
    *,
    payload: EvidenceSubmissionRequest,
    pubmed_validation: dict,
    clinvar_payload: dict,
    warnings: list[str],
) -> dict:
    return {
        "schema_version": "eamos_user_evidence_submission_v1",
        "payload_status": clinvar_payload.get("payload_status"),
        "pubmed": pubmed_validation,
        "clinvar_payload": clinvar_payload,
        "submitted_fields": {
            "condition_name": payload.condition_name,
            "assay_type": payload.assay_type,
            "collection_method": payload.collection_method,
            "functional_effect": payload.functional_effect,
            "functional_consequence": payload.functional_consequence,
            "method": payload.method,
            "result": payload.result,
            "evidence_codes": payload.evidence_codes,
        },
        "warnings": warnings,
    }


def build_clinvar_submission_payload(
    payload: EvidenceSubmissionRequest,
    tracking_id: str,
) -> ClinvarSubmissionDraft:
    missing = [
        field_name
        for field_name in _CLINVAR_REQUIRED_FIELDS
        if not _has_clinvar_required_value(payload, field_name)
    ]
    payload_status = "draft_needs_curator_fields" if missing else "ready_for_clinvar_dry_run"
    functional_record = {
        "collectionMethod": payload.collection_method,
        "assayType": payload.assay_type or "assay type pending curator review",
        "method": payload.method or payload.curator_notes or "method pending curator review",
        "functionalEffect": payload.functional_effect,
        "functionalConsequence": payload.functional_consequence
        or ["functional consequence pending curator review"],
        "result": payload.result or "result pending curator review",
        "methodCitation": [{"db": "PubMed", "id": payload.submitted_pmid}],
    }
    if payload.curator_notes:
        functional_record["functionalConsequenceComment"] = payload.curator_notes

    clinvar_payload = {
        "submissionName": tracking_id,
        "noClassificationSubmission": [
            {
                "localKey": tracking_id,
                "recordStatus": "novel",
                "noClassification": "evidence_only",
                "variantSet": {"variant": [{"hgvs": payload.variant_hgvs}]},
                "conditionSet": {
                    "condition": [
                        {"name": payload.condition_name or "condition pending curator review"}
                    ]
                },
                "functionalObservedIn": [functional_record],
            }
        ],
    }
    if payload.evidence_codes:
        clinvar_payload["eamosEvidenceCodes"] = payload.evidence_codes

    return ClinvarSubmissionDraft(
        tracking_id=tracking_id,
        payload_status=payload_status,
        missing_required_fields=missing,
        payload=clinvar_payload,
    )


def _has_clinvar_required_value(payload: EvidenceSubmissionRequest, field_name: str) -> bool:
    value = getattr(payload, field_name)
    if isinstance(value, list):
        return bool(value)
    return bool(value)
