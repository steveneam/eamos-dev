from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings
from app.main import create_app


@pytest.fixture()
def app(tmp_path: Path):
    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        llm_provider="mock",
        use_real_apis=False,
        max_upload_mb=5,
        debug=True,
    )
    return create_app(settings)


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def pdf_bytes() -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, "HSIL demo PDF fixture")
    pdf.drawString(72, 700, "RPE65 c.260A>G / p.Asp87Gly")
    pdf.save()
    return buffer.getvalue()
