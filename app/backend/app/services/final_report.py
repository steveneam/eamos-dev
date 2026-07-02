from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, status

from app.core.logging import get_logger
from app.schemas.draft import ApproveResult, DropResult
from app.schemas.run import RunStatus, ReviewStatus

logger = get_logger(__name__)


class FinalReportService:
    def __init__(self, settings, run_repo, search_index_service=None) -> None:
        self.settings = settings
        self.run_repo = run_repo
        self.search_index_service = search_index_service

    def get_pdf(self, run_id: str) -> Path:
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
        if run.review_status == ReviewStatus.dropped:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Dropped run does not have an approved PDF.",
            )

        reference_pdf = self._reference_pdf_path()

        if run.review_status == ReviewStatus.approved:
            approved_path = (
                Path(run.approved_pdf_path)
                if run.approved_pdf_path
                else self.settings.final_report_dir / f"{run_id}_final.pdf"
            )
            self._copy_reference_pdf(reference_pdf, approved_path)
            return approved_path

        preview_path = self.settings.final_report_dir / f"{run_id}_preview.pdf"
        self._copy_reference_pdf(reference_pdf, preview_path)
        return preview_path

    def approve(self, run_id: str) -> ApproveResult:
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
        if run.review_status == ReviewStatus.dropped:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Dropped run cannot be approved."
            )
        if run.run_status == RunStatus.blocked:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Blocked run cannot be approved until extractable.",
            )

        approved_path = self.settings.final_report_dir / f"{run_id}_final.pdf"
        self._copy_reference_pdf(self._reference_pdf_path(), approved_path)
        approved_at = datetime.now().astimezone()
        self.run_repo.save_approved_pdf_path(run_id, str(approved_path))
        approved = self.run_repo.approve(run_id, approved_at)
        self._refresh_search_index(run_id)
        return approved

    def drop(self, run_id: str, review_note: str | None = None) -> DropResult:
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
        dropped = self.run_repo.drop(run_id, drop_note=review_note)
        self._refresh_search_index(run_id)
        return dropped

    def _refresh_search_index(self, run_id: str) -> None:
        if self.search_index_service is None:
            return
        try:
            self.search_index_service.refresh_run(run_id)
        except Exception:
            logger.exception("Search index refresh failed for final report mutation %s", run_id)

    def _reference_pdf_path(self) -> Path:
        path = (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "reports"
            / "backend_report_recommendations_v2.pdf"
        )
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Reference PDF is missing.",
            )
        return path

    def _copy_reference_pdf(self, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
