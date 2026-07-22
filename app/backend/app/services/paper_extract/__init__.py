"""Deterministic, page-preserving Paper → Variants extraction primitives."""

from app.services.paper_extract.document import (
    PaperInputDocument,
    PaperInputPage,
    pdf_document,
    text_document,
)
from app.services.paper_extract.pipeline import PaperExtractionDraft, build_extraction_draft

__all__ = [
    "PaperExtractionDraft",
    "PaperInputDocument",
    "PaperInputPage",
    "build_extraction_draft",
    "pdf_document",
    "text_document",
]
