from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("eamos-ci")
    group.addoption(
        "--eamos-shard-count",
        type=int,
        default=1,
        help="Split the collected backend tests into this many stable CI shards.",
    )
    group.addoption(
        "--eamos-shard-index",
        type=int,
        default=0,
        help="Run this zero-based Eamos CI shard.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    shard_count = config.getoption("--eamos-shard-count")
    shard_index = config.getoption("--eamos-shard-index")
    if shard_count < 1:
        raise pytest.UsageError("--eamos-shard-count must be at least 1")
    if not 0 <= shard_index < shard_count:
        raise pytest.UsageError("--eamos-shard-index must be between 0 and --eamos-shard-count - 1")
    if shard_count == 1:
        return

    selected: list[pytest.Item] = []
    deselected: list[pytest.Item] = []
    for item in items:
        digest = hashlib.sha256(item.nodeid.encode("utf-8")).digest()
        assigned_shard = int.from_bytes(digest[:8], byteorder="big") % shard_count
        (selected if assigned_shard == shard_index else deselected).append(item)

    config.hook.pytest_deselected(items=deselected)
    items[:] = selected


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
        clinvar_gene_distribution_index_path=tmp_path / "missing-clinvar-gene-distribution.sqlite",
        clinvar_gene_distribution_manifest_path=(
            tmp_path / "missing-clinvar-gene-distribution.manifest.json"
        ),
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
