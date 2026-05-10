from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.core.config import Settings
from app.main import create_app

pytestmark = pytest.mark.skipif(
    os.getenv("HSIL_RUN_LIVE_API_SMOKE") != "1",
    reason="Set HSIL_RUN_LIVE_API_SMOKE=1 to exercise live ClinVar/VEP/SpliceAI calls.",
)


def build_pdf_bytes() -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, "Sydney Genomics Centre")
    pdf.drawString(72, 700, "Patient: Ravi demo case")
    pdf.drawString(72, 680, "Phenotype: inherited retinal dystrophy, nyctalopia")
    pdf.drawString(72, 660, "Variant: RPE65 NM_000329.3:c.260A>G (p.Asp87Gly)")
    pdf.save()
    return buffer.getvalue()


def test_live_evidence_run_uses_real_apis_except_franklin() -> None:
    settings = Settings(
        upload_dir=Path("/tmp") / "hsil_live_uploads",
        final_report_dir=Path("/tmp") / "hsil_live_final_reports",
        database_url="sqlite+pysqlite:////tmp/hsil_live_api_smoke.db",
        llm_provider="mock",
        use_real_apis=True,
        franklin_api_token=None,
        max_upload_mb=20,
        debug=True,
    )
    app = create_app(settings)

    with TestClient(app) as client:
        upload = client.post(
            "/api/v1/reports/upload",
            files={"file": ("ravi-live-api.pdf", build_pdf_bytes(), "application/pdf")},
            data={"report_kind": "test"},
        )
        assert upload.status_code == 201
        report_id = upload.json()["report"]["report_id"]

        response = client.post(
            "/api/v1/runs",
            json={"patient_id": "LIVE-EVIDENCE-001", "report_ids": [report_id]},
        )
        assert response.status_code == 200

        evidence = {item["source"]: item for item in response.json()["evidence"]}
        assert evidence["vep"]["status"] == "live"
        assert evidence["spliceai"]["status"] == "live"
        assert evidence["clinvar"]["status"] == "live"
        assert evidence["franklin"]["status"] == "fallback"
        assert "franklin_auth_unavailable" in evidence["franklin"]["warnings"]
