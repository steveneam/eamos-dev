from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.schemas.draft import ReportDraftUpdatePayload
from app.schemas.run import ReviewStatus, RunResponse


class ReportDraftService:
    def __init__(self, run_repo) -> None:
        self.run_repo = run_repo

    def update_report_payload(self, run_id: str, payload: ReportDraftUpdatePayload) -> RunResponse:
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Run not found.')

        if run.review_status in {ReviewStatus.approved, ReviewStatus.dropped}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Approved or dropped runs can no longer be edited.',
            )

        updates = payload.model_dump(exclude_unset=True)
        review_note = updates.pop('review_note', None) if 'review_note' in updates else None
        updated_at = datetime.now(timezone.utc)
        return self.run_repo.update_report_payload(
            run_id=run_id,
            payload_updates=updates,
            review_note=review_note,
            updated_at=updated_at,
        )
