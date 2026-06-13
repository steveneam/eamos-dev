"""Pluggable PDF → text extraction (decision D1, docs/ai-gateway-paper-variants/spec.md).

One ingestion seam for paper/report PDFs. The default engine is **pypdf** (BSD,
already a dependency, commercial-safe) and reuses the existing `ReportPdfTool`.
`pdfplumber` (MIT, better layout) and `fitz`/PyMuPDF (fastest, **AGPL — needs an
Artifex commercial licence for production SaaS use**) can be selected via
`settings.pdf_text_engine` with no caller changes. Never raises on a parse
failure — returns a warning so callers degrade gracefully.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_ENGINE = "pypdf"
SUPPORTED_ENGINES = ("pypdf", "pdfplumber", "fitz")


def extract_pdf_text(file_path: Any, *, engine: str = DEFAULT_ENGINE) -> dict[str, Any]:
    """Return ``{text, page_count, engine, warnings}`` for a PDF path."""
    path = Path(file_path)
    if engine not in SUPPORTED_ENGINES:
        return _empty(engine, f"unsupported_pdf_engine:{engine}")
    if not path.is_file():
        return _empty(engine, "pdf_file_missing")
    try:
        if engine == "pypdf":
            return _extract_pypdf(path)
        if engine == "pdfplumber":
            return _extract_pdfplumber(path)
        return _extract_fitz(path)
    except Exception as exc:  # noqa: BLE001 - ingestion boundary, never crash a request
        logger.warning("pdf extraction failed (engine=%s)", engine, exc_info=True)
        return _empty(engine, f"pdf_parse_failed:{type(exc).__name__}")


def _empty(engine: str, warning: str) -> dict[str, Any]:
    return {"text": "", "page_count": 0, "engine": engine, "warnings": [warning]}


def _extract_pypdf(path: Path) -> dict[str, Any]:
    # Reuse the existing pypdf-backed extractor so there's a single pypdf seam.
    from app.tools.report_pdf import ReportPdfTool

    result = ReportPdfTool().extract(path)
    return {
        "text": result.get("text", ""),
        "page_count": result.get("page_count", 0),
        "engine": "pypdf",
        "warnings": list(result.get("warnings", [])),
    }


def _extract_pdfplumber(path: Path) -> dict[str, Any]:
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
        page_count = len(pdf.pages)
    return {
        "text": "\n".join(part for part in parts if part).strip(),
        "page_count": page_count,
        "engine": "pdfplumber",
        "warnings": [],
    }


def _extract_fitz(path: Path) -> dict[str, Any]:
    import fitz

    doc = fitz.open(str(path))
    try:
        parts = [page.get_text() for page in doc]
        page_count = doc.page_count
    finally:
        doc.close()
    return {
        "text": "\n".join(part for part in parts if part).strip(),
        "page_count": page_count,
        "engine": "fitz",
        "warnings": [],
    }
