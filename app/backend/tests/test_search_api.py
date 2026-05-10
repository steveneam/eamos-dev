from __future__ import annotations

from io import BytesIO
import os

import httpx
import pytest
from reportlab.pdfgen import canvas


BASE_URL = os.getenv("HSIL_DOCKER_BASE_URL")
pytestmark = pytest.mark.skipif(
    not BASE_URL,
    reason="Set HSIL_DOCKER_BASE_URL after docker compose up.",
)


def _build_pdf_bytes() -> bytes:
    stream = BytesIO()
    pdf = canvas.Canvas(stream)
    pdf.drawString(72, 720, "Ravi demo report")
    pdf.drawString(72, 700, "Case for search indexing")
    pdf.drawString(72, 680, "RPE65 NM_000329.3:c.260A>G")
    pdf.save()
    return stream.getvalue()


def test_search_endpoint_returns_created_runs(_tmp_dir=None) -> None:  # noqa: ARG001
    assert BASE_URL is not None
    client = httpx.Client(base_url=BASE_URL, timeout=120)
    try:
        upload = client.post(
            "/api/v1/reports/upload",
            files={
                "file": (
                    "search-case.pdf",
                    _build_pdf_bytes(),
                    "application/pdf",
                )
            },
            data={"report_kind": "test"},
        )
        assert upload.status_code == 201
        report = upload.json()["report"]
        report_id = report["report_id"]

        run_resp = client.post(
            "/api/v1/runs",
            json={
                "patient_id": "SEARCH-INTG-001",
                "report_ids": [report_id],
            },
        )
        assert run_resp.status_code == 200
        run_body = run_resp.json()
        run_id = run_body["run_id"]
        evidence = {item["source"]: item for item in run_body["evidence"]}
        assert evidence["vep"]["status"] == "live"
        assert evidence["spliceai"]["status"] == "live"
        assert evidence["clinvar"]["status"] == "live"
        assert evidence["franklin"]["status"] == "fallback"

        search = client.get(
            "/api/v1/search",
            params={"q": run_id, "limit": 5},
        )
        assert search.status_code == 200
        search_json = search.json()
        assert search_json["query"] == run_id
        assert len(search_json["results"]) >= 1

        by_term = client.get(
            "/api/v1/search",
            params={"q": "RPE65", "limit": 5},
        )
        assert by_term.status_code == 200
        by_term_json = by_term.json()
        assert any(
            item.get("run_id") == run_id or item.get("report_id") == report_id
            for item in by_term_json.get("results", [])
        )
    finally:
        client.close()


def test_search_answer_endpoint_with_real_api() -> None:
    assert BASE_URL is not None
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is required for answer endpoint with real model.")

    client = httpx.Client(base_url=BASE_URL, timeout=120)
    try:
        # This endpoint should be available when USE_REAL_APIS/search enabled in compose env
        payload = {"query": "RPE65 run_id", "limit": 5}
        answer = client.post("/api/v1/search/answer", json=payload)
        if answer.status_code == 503:
            pytest.skip("search answer disabled in this environment")

        assert answer.status_code == 200
        body = answer.json()
        assert "answer" in body
        assert isinstance(body.get("citations", []), list)
    finally:
        client.close()
