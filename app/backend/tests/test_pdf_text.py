from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.services.pdf_text import PdfTextLimits, extract_pdf_text


def _fixture_pdf() -> Path:
    return (
        Settings(jwt_secret="pdf-test").fixtures_root
        / "reports"
        / "backend_report_recommendations_v2.pdf"
    )


def test_extract_pypdf_default() -> None:
    result = extract_pdf_text(_fixture_pdf())
    assert result["engine"] == "pypdf"
    assert result["engine_version"]
    assert result["page_count"] >= 1
    assert isinstance(result["text"], str)
    assert len(result["pages"]) == result["page_count"]
    assert result["pages"][0]["page_number"] == 1
    assert result["pages"][0]["quality"] in {"good", "degraded"}
    assert result["pages"][0]["text"] in result["text"]
    assert isinstance(result["metadata"], dict)
    assert result["warnings"] == []


def test_fitz_engine_is_prohibited_even_if_importable() -> None:
    result = extract_pdf_text(_fixture_pdf(), engine="fitz")

    assert result["text"] == ""
    assert result["page_count"] == 0
    assert result["warnings"] == ["pdf_engine_prohibited:fitz"]


def test_pdfium_missing_dependency_is_typed_unavailable() -> None:
    result = extract_pdf_text(_fixture_pdf(), engine="pdfium")

    if result["page_count"] == 0:
        assert result["warnings"] == ["pdf_engine_unavailable:pdfium:pypdfium2"]
    else:
        assert result["engine"] == "pdfium"
        assert result["engine_version"]


def test_unsupported_engine_warns() -> None:
    result = extract_pdf_text(_fixture_pdf(), engine="bogus")
    assert result["page_count"] == 0
    assert result["warnings"] == ["unsupported_pdf_engine:bogus"]


def test_missing_file_warns(tmp_path: Path) -> None:
    result = extract_pdf_text(tmp_path / "nope.pdf")
    assert result["text"] == ""
    assert result["warnings"] == ["pdf_file_missing"]


def test_character_budget_fails_closed_without_partial_text() -> None:
    result = extract_pdf_text(
        _fixture_pdf(),
        limits=PdfTextLimits(max_page_characters=20, max_total_characters=20),
    )

    assert result["text"] == ""
    assert any(
        warning.startswith("pdf_character_limit_exceeded:") for warning in result["warnings"]
    )


def test_file_page_and_object_budgets_fail_closed() -> None:
    size_limited = extract_pdf_text(
        _fixture_pdf(),
        limits=PdfTextLimits(max_file_bytes=4),
    )
    page_limited = extract_pdf_text(
        _fixture_pdf(),
        limits=PdfTextLimits(max_pages=0),
    )
    object_limited = extract_pdf_text(
        _fixture_pdf(),
        limits=PdfTextLimits(max_objects=0),
    )

    assert size_limited["warnings"] == ["pdf_file_size_limit_exceeded"]
    assert size_limited["pages"] == []
    assert page_limited["warnings"] == ["pdf_page_limit_exceeded"]
    assert page_limited["pages"] == []
    assert object_limited["warnings"] == ["pdf_object_limit_exceeded"]
    assert object_limited["pages"] == []


def test_password_encrypted_pdf_fails_closed(tmp_path: Path) -> None:
    from pypdf import PdfWriter

    path = tmp_path / "encrypted.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("not-the-empty-password")
    with path.open("wb") as handle:
        writer.write(handle)

    result = extract_pdf_text(path)

    assert result["warnings"] == ["pdf_encrypted"]
    assert result["pages"] == []


def test_blank_pdf_reports_ocr_requirement(tmp_path: Path) -> None:
    from pypdf import PdfWriter

    path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with path.open("wb") as handle:
        writer.write(handle)

    result = extract_pdf_text(path)

    assert result["page_count"] == 1
    assert result["pages"][0]["quality"] == "empty"
    assert "ocr_required:page:1" in result["warnings"]


def test_parse_errors_do_not_echo_host_path(tmp_path: Path) -> None:
    path = tmp_path / "PRIVATE_FILENAME.pdf"
    path.write_bytes(b"%PDF-not-really-a-pdf")

    result = extract_pdf_text(path)

    assert result["text"] == ""
    assert "PRIVATE_FILENAME" not in " ".join(result["warnings"])
