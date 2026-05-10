from __future__ import annotations

from app.core.db import ReportRecord, session_scope
from app.schemas.report import UploadedReport


class ReportsRepo:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def save(self, report: UploadedReport) -> UploadedReport:
        payload = report.model_dump(mode="json")
        with session_scope(self.session_factory) as session:
            record = ReportRecord(
                report_id=report.report_id,
                filename=report.filename,
                content_type=report.content_type,
                size_bytes=report.size_bytes,
                created_at=report.created_at,
                extraction_status=report.extraction_status,
                report_data=payload,
            )
            session.merge(record)
        return report

    def get(self, report_id: str) -> UploadedReport | None:
        with session_scope(self.session_factory) as session:
            record = session.get(ReportRecord, report_id)
            if record is None:
                return None
            return UploadedReport.model_validate(record.report_data)

    def update(self, report: UploadedReport) -> UploadedReport:
        return self.save(report)
