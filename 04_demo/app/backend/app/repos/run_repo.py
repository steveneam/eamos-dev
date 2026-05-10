from __future__ import annotations

from datetime import datetime, timezone


from app.core.db import RunRecord, session_scope
from app.schemas.draft import ApproveResult, DropResult, ReviewResult
from app.schemas.run import RunResponse, RunStatus, ReviewStatus


def _record_to_run_response(record: RunRecord) -> RunResponse:
    from app.schemas.run import EvidenceSourceSummary, ReportPayload

    evidence = [
        EvidenceSourceSummary.model_validate(item)
        for item in record.evidence or []
    ]
    payload = ReportPayload.model_validate(record.report_payload)
    return RunResponse(
        run_id=record.run_id,
        patient_id=record.patient_id,
        report_ids=list(record.report_ids or []),
        run_status=RunStatus(record.run_status),
        review_status=ReviewStatus(record.review_status),
        report_payload=payload,
        evidence=evidence,
        warnings=list(record.warnings or []),
        review_note=record.review_note,
        reviewed_at=record.reviewed_at,
        approved_pdf_path=record.approved_pdf_path,
    )


class RunRepo:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def create_run(
        self,
        run_id: str,
        patient_id: str,
        report_ids: list[str],
        run_status: RunStatus,
        report_payload,
        evidence,
        warnings: list[str],
    ) -> RunResponse:
        with session_scope(self.session_factory) as session:
            record = RunRecord(
                run_id=run_id,
                patient_id=patient_id,
                report_ids=report_ids,
                run_status=run_status.value,
                review_status=ReviewStatus.pending_review.value,
                report_payload=report_payload.model_dump(mode='json'),
                evidence=[item.model_dump(mode='json') for item in evidence],
                warnings=warnings,
                updated_at=datetime.now(timezone.utc),
            )
            session.merge(record)

            return RunResponse(
                run_id=run_id,
                patient_id=patient_id,
                report_ids=report_ids,
                run_status=RunStatus(record.run_status),
                review_status=ReviewStatus(record.review_status),
                report_payload=report_payload,
                evidence=evidence,
                warnings=warnings,
                review_note=None,
                reviewed_at=None,
                approved_pdf_path=None,
            )

    def get(self, run_id: str) -> RunRecord | None:
        with session_scope(self.session_factory) as session:
            return session.get(RunRecord, run_id)

    def get_run(self, run_id: str) -> RunResponse | None:
        with session_scope(self.session_factory) as session:
            record = session.get(RunRecord, run_id)
            if record is None:
                return None
            return _record_to_run_response(record)

    def update_report_payload(
        self,
        run_id: str,
        payload_updates: dict,
        review_note: str | None,
        updated_at: datetime,
    ) -> RunResponse:
        with session_scope(self.session_factory) as session:
            record = session.get(RunRecord, run_id)
            if record is None:
                raise KeyError(run_id)

            from app.schemas.run import ReportPayload

            payload = ReportPayload.model_validate(record.report_payload)
            for key, value in payload_updates.items():
                if hasattr(payload, key):
                    setattr(payload, key, value)
            record.report_payload = payload.model_dump(mode='json')
            if review_note is not None:
                record.review_note = review_note.strip() or None
            record.updated_at = updated_at
            session.add(record)
            return _record_to_run_response(record)

    def add_review(self, run_id: str, review_note: str, reviewed_at: datetime) -> ReviewResult:
        with session_scope(self.session_factory) as session:
            record = session.get(RunRecord, run_id)
            if record is None:
                raise KeyError(run_id)
            record.review_status = ReviewStatus.reviewed.value
            record.review_note = review_note
            record.reviewed_at = reviewed_at
            record.updated_at = datetime.now(timezone.utc)
            session.add(record)
            return ReviewResult(
                run_id=run_id,
                review_status='reviewed',
                review_note=review_note,
                reviewed_at=reviewed_at,
            )

    def approve(self, run_id: str, approved_at: datetime) -> ApproveResult:
        with session_scope(self.session_factory) as session:
            record = session.get(RunRecord, run_id)
            if record is None:
                raise KeyError(run_id)
            record.review_status = ReviewStatus.approved.value
            if record.reviewed_at is None:
                record.reviewed_at = approved_at
            record.approved_at = approved_at
            record.updated_at = approved_at
            session.add(record)
            return ApproveResult(
                run_id=run_id,
                review_status='approved',
                review_note=record.review_note,
                reviewed_at=record.reviewed_at,
                download_path=f'/api/v1/runs/{run_id}/pdf',
            )

    def drop(self, run_id: str, drop_note: str | None = None) -> DropResult:
        with session_scope(self.session_factory) as session:
            record = session.get(RunRecord, run_id)
            if record is None:
                raise KeyError(run_id)
            record.review_status = ReviewStatus.dropped.value
            if drop_note:
                note = drop_note.strip()
                if note:
                    if record.review_note:
                        record.review_note = f'{record.review_note}\n\n{note}'
                    else:
                        record.review_note = note
            record.updated_at = datetime.now(timezone.utc)
            session.add(record)
            return DropResult(
                run_id=run_id,
                review_status='dropped',
                review_note=record.review_note,
                reviewed_at=record.reviewed_at,
            )

    def save_approved_pdf_path(self, run_id: str, path: str) -> None:
        with session_scope(self.session_factory) as session:
            record = session.get(RunRecord, run_id)
            if record is None:
                raise KeyError(run_id)
            record.approved_pdf_path = path
            session.add(record)

    def get_approved_pdf_path(self, run_id: str) -> str | None:
        with session_scope(self.session_factory) as session:
            record = session.get(RunRecord, run_id)
            if record is None:
                return None
            return record.approved_pdf_path

    def reset(self) -> None:
        with session_scope(self.session_factory) as session:
            session.query(RunRecord).delete()
