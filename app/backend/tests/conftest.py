from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(autouse=True)
def _local_test_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SUPABASE_LOCAL_MODEL_CACHE_ENABLED", "false")
    monkeypatch.delenv("SUPABASE_LOCAL_MODEL_CACHE_DATABASE_URL", raising=False)


@pytest.fixture()
def app(tmp_path: Path):
    from app.core.config import Settings
    from app.main import create_app

    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        llm_provider="mock",
        use_real_apis=False,
        workbench_live_design_enabled=False,
        clingen_local_enabled=False,
        clingen_local_sqlite_path=tmp_path / "missing-clingen.sqlite",
        clingen_local_manifest_path=tmp_path / "missing-clingen.manifest.json",
        max_upload_mb=5,
        debug=True,
        jwt_secret="test-secret",
        supabase_local_model_cache_enabled=False,
        supabase_local_model_cache_database_url=None,
        supabase_jwt_secret=None,
        supabase_url=None,
        supabase_service_role_key=None,
    )
    return create_app(settings)


@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/auth/register",
            json={"username": "test-user", "password": "test-password"},
        )
        assert response.status_code == 201
        token = response.json()["access_token"]
        test_client.headers.update({"Authorization": f"Bearer {token}"})
        yield test_client


@pytest.fixture()
def pdf_bytes() -> bytes:
    from io import BytesIO

    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, "HSIL demo PDF fixture")
    pdf.drawString(72, 700, "RPE65 c.260A>G / p.Asp87Gly")
    pdf.save()
    return buffer.getvalue()
