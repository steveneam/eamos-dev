from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_upload_test_report_returns_report_id_and_extraction_summary(
    client: TestClient, pdf_bytes: bytes
) -> None:
    response = client.post(
        "/api/v1/reports/upload",
        files={"file": ("ravi-report.pdf", pdf_bytes, "application/pdf")},
        data={"report_kind": "test"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["report"]["report_id"].startswith("report_")
    assert body["report"]["report_kind"] == "test"
    assert body["report"]["extraction_status"] == "completed"
    assert body["report"]["extracted_case"]["variants"][0]["gene"] == "RPE65"


def test_upload_patient_report_is_blocked_without_ai(client: TestClient, pdf_bytes: bytes) -> None:
    response = client.post(
        "/api/v1/reports/upload",
        files={"file": ("patient.pdf", pdf_bytes, "application/pdf")},
        data={"report_kind": "patient"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["report"]["report_kind"] == "patient"
    assert body["report"]["extraction_status"] == "blocked"
    assert body["report"]["extracted_case"]["issues"][0]["code"] == "patient_extraction_unavailable"


def test_upload_rejects_invalid_file_type(client: TestClient) -> None:
    response = client.post(
        "/api/v1/reports/upload",
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 415


def test_upload_rejects_oversize_payload(tmp_path: Path, pdf_bytes: bytes) -> None:
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'oversize.db').as_posix()}",
        llm_provider="mock",
        use_real_apis=False,
        max_upload_mb=0,
        debug=True,
    )
    app = create_app(settings)
    with TestClient(app) as local_client:
        response = local_client.post(
            "/api/v1/reports/upload",
            files={"file": ("too-big.pdf", pdf_bytes, "application/pdf")},
        )
    assert response.status_code == 413
