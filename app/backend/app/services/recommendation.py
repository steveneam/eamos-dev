from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.schemas.draft import ClinicianReviewPayload, ReviewResult


class RecommendationService:
    def __init__(self, run_repo, search_index_service=None) -> None:
        self.run_repo = run_repo
        self.search_index_service = search_index_service

    def apply_review(self, run_id: str, payload: ClinicianReviewPayload) -> ReviewResult:
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
        if run.review_status.value == "dropped":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Dropped run cannot be reviewed."
            )

        note = (payload.review_note or "").strip()
        if not note:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="review_note is required."
            )

        result = self.run_repo.add_review(
            run_id=run_id,
            review_note=note,
            reviewed_at=datetime.now(timezone.utc),
        )
        if self.search_index_service is not None:
            self.search_index_service.refresh_run(run_id)
        return result
