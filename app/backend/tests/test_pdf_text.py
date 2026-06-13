from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.services.pdf_text import extract_pdf_text


def _fixture_pdf() -> Path:
    return (
        Settings(jwt_secret="pdf-test").fixtures_root
        / "reports"
        / "backend_report_recommendations_v2.pdf"
    )


def test_extract_pypdf_default() -> None:
    result = extract_pdf_text(_fixture_pdf())
    assert result["engine"] == "pypdf"
    assert result["page_count"] >= 1
    assert isinstance(result["text"], str)
    assert result["warnings"] == []


def test_extract_fitz_engine() -> None:
    result = extract_pdf_text(_fixture_pdf(), engine="fitz")
    assert result["engine"] == "fitz"
    assert result["page_count"] >= 1


def test_unsupported_engine_warns() -> None:
    result = extract_pdf_text(_fixture_pdf(), engine="bogus")
    assert result["page_count"] == 0
    assert result["warnings"] == ["unsupported_pdf_engine:bogus"]


def test_missing_file_warns(tmp_path: Path) -> None:
    result = extract_pdf_text(tmp_path / "nope.pdf")
    assert result["text"] == ""
    assert result["warnings"] == ["pdf_file_missing"]
