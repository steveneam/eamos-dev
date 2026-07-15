from __future__ import annotations

from app.core.db import ReportRecord, session_scope
from app.core.ownership import OwnerIdentity
from app.schemas.report import UploadedReport


class ReportsRepo:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def save(
        self,
        report: UploadedReport,
        *,
        owner: OwnerIdentity | None = None,
    ) -> UploadedReport:
        payload = report.model_dump(mode="json")
        with session_scope(self.session_factory) as session:
            existing = session.get(ReportRecord, report.report_id)
            owner_user_id = owner.user_id if owner is not None else None
            owner_provider = owner.provider if owner is not None else None
            if existing is not None:
                existing_owner = (existing.owner_provider, existing.owner_user_id)
                requested_owner = (owner_provider, owner_user_id)
                if owner is None:
                    owner_provider, owner_user_id = existing_owner
                elif existing_owner not in {(None, None), requested_owner}:
                    raise PermissionError(report.report_id)
            record = ReportRecord(
                report_id=report.report_id,
                filename=report.filename,
                content_type=report.content_type,
                size_bytes=report.size_bytes,
                created_at=report.created_at,
                extraction_status=report.extraction_status,
                report_data=payload,
                owner_user_id=owner_user_id,
                owner_provider=owner_provider,
            )
            session.merge(record)
        return report

    def get(self, report_id: str) -> UploadedReport | None:
        with session_scope(self.session_factory) as session:
            record = session.get(ReportRecord, report_id)
            if record is None:
                return None
            return UploadedReport.model_validate(record.report_data)

    def get_for_owner(
        self,
        report_id: str,
        *,
        owner: OwnerIdentity,
    ) -> UploadedReport | None:
        with session_scope(self.session_factory) as session:
            record = (
                session.query(ReportRecord)
                .filter(
                    ReportRecord.report_id == report_id,
                    ReportRecord.owner_user_id == owner.user_id,
                    ReportRecord.owner_provider == owner.provider,
                )
                .one_or_none()
            )
            if record is None:
                return None
            return UploadedReport.model_validate(record.report_data)

    def list_all(self) -> list[UploadedReport]:
        with session_scope(self.session_factory) as session:
            records = (
                session.query(ReportRecord)
                .order_by(ReportRecord.created_at.asc(), ReportRecord.report_id.asc())
                .all()
            )
            return [UploadedReport.model_validate(record.report_data) for record in records]

    def update(
        self,
        report: UploadedReport,
        *,
        owner: OwnerIdentity | None = None,
    ) -> UploadedReport:
        return self.save(report, owner=owner)
