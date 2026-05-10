from __future__ import annotations

import os
from io import BytesIO

import httpx
import pytest
from reportlab.pdfgen import canvas

BASE_URL = os.getenv("HSIL_DOCKER_BASE_URL")
pytestmark = pytest.mark.skipif(
    not BASE_URL, reason="Set HSIL_DOCKER_BASE_URL after docker compose up."
)


def build_pdf_bytes() -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, "HSIL demo upload fixture")
    pdf.drawString(72, 700, "RPE65 c.260A>G / p.Asp87Gly")
    pdf.drawString(72, 680, "Retinal dystrophy review case")
    pdf.save()
    return buffer.getvalue()


PDF_BYTES = build_pdf_bytes()


def test_docker_stack_upload_run_review_approve_preview_pdf() -> None:
    assert BASE_URL is not None
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        health = client.get("/healthz")
        assert health.status_code == 200
        assert health.json()["database"] == "ok"

        upload_1 = client.post(
            "/api/v1/reports/upload",
            files={"file": ("test.pdf", PDF_BYTES, "application/pdf")},
            data={"report_kind": "test"},
        )
        upload_2 = client.post(
            "/api/v1/reports/upload",
            files={"file": ("test-2.pdf", PDF_BYTES, "application/pdf")},
            data={"report_kind": "test"},
        )
        assert upload_1.status_code == 201
        assert upload_2.status_code == 201

        run = client.post(
            "/api/v1/runs",
            json={
                "patient_id": "RID-001",
                "report_ids": [
                    upload_1.json()["report"]["report_id"],
                    upload_2.json()["report"]["report_id"],
                ],
            },
        )
        assert run.status_code == 200
        run_id = run.json()["run_id"]

        review = client.post(
            f"/api/v1/runs/{run_id}/review",
            json={"reviewer_name": "integration", "review_note": "Looks clinically coherent."},
        )
        assert review.status_code == 200

        preview = client.get(f"/api/v1/runs/{run_id}/pdf")
        assert preview.status_code == 200
        assert preview.content.startswith(b"%PDF")

        approve = client.post(f"/api/v1/runs/{run_id}/approve")
        assert approve.status_code == 200

        pdf = client.get(approve.json()["download_path"])
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")
