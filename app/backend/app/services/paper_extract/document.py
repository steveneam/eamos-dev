"""Request-lifetime document types for deterministic paper extraction.

These dataclasses may hold extracted text while one request is running. They are
never API or persistence models. Durable output is built from the frozen V2
schemas and contains only hashes, safe metadata, and bounded evidence spans.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence

PaperKind = Literal["pdf", "text", "csv", "xlsx"]
PaperRole = Literal["main", "supplement"]
PageQuality = Literal["good", "degraded", "garbled", "image_only", "empty"]


@dataclass(frozen=True, slots=True)
class PaperInputPage:
    page_number: int
    text: str
    quality: PageQuality
    replacement_character_ratio: float = 0.0
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PaperInputDocument:
    document_id: str
    role: PaperRole
    kind: PaperKind
    safe_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    extraction_engine: str
    extraction_engine_version: str
    pages: tuple[PaperInputPage, ...]
    embedded_metadata: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def text(self) -> str:
        return "\n".join(page.text for page in self.pages if page.text).strip()


def text_document(
    text: str,
    *,
    document_id: str = "main-text",
    role: PaperRole = "main",
    kind: Literal["text", "csv"] = "text",
) -> PaperInputDocument:
    payload = text.encode("utf-8")
    return PaperInputDocument(
        document_id=document_id,
        role=role,
        kind=kind,
        safe_filename=f"{document_id}.{'csv' if kind == 'csv' else 'txt'}",
        media_type="text/csv" if kind == "csv" else "text/plain",
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        extraction_engine="eamos_text",
        extraction_engine_version="2.0.0",
        pages=(
            PaperInputPage(
                page_number=1,
                text=text,
                quality=_text_quality(text),
                replacement_character_ratio=_replacement_ratio(text),
            ),
        ),
    )


def pdf_document(
    extracted: Mapping[str, Any],
    *,
    size_bytes: int,
    sha256: str,
    document_id: str = "main-pdf",
    role: PaperRole = "main",
) -> PaperInputDocument:
    pages = tuple(
        PaperInputPage(
            page_number=int(page["page_number"]),
            text=str(page.get("text") or ""),
            quality=str(page.get("quality") or "empty"),  # type: ignore[arg-type]
            replacement_character_ratio=float(page.get("replacement_character_ratio") or 0.0),
            warnings=tuple(str(item) for item in page.get("warnings", ())),
        )
        for page in extracted.get("pages", ())
    )
    return PaperInputDocument(
        document_id=document_id,
        role=role,
        kind="pdf",
        safe_filename=f"{document_id}.pdf",
        media_type="application/pdf",
        size_bytes=size_bytes,
        sha256=sha256,
        extraction_engine=str(extracted.get("engine") or "pypdf"),
        extraction_engine_version=str(extracted.get("engine_version") or "unknown"),
        pages=pages,
        embedded_metadata=dict(extracted.get("metadata") or {}),
        warnings=tuple(str(item) for item in extracted.get("warnings", ())),
    )


def bundle_input_digest(documents: Sequence[PaperInputDocument]) -> str:
    digest = hashlib.sha256()
    for document in documents:
        digest.update(document.document_id.encode("ascii"))
        digest.update(b"\0")
        digest.update(document.role.encode("ascii"))
        digest.update(b"\0")
        digest.update(document.kind.encode("ascii"))
        digest.update(b"\0")
        digest.update(document.sha256.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _replacement_ratio(text: str) -> float:
    return text.count("\ufffd") / max(1, len(text))


def _text_quality(text: str) -> PageQuality:
    if not text.strip():
        return "empty"
    replacement_ratio = _replacement_ratio(text)
    control_count = sum(1 for char in text if ord(char) < 32 and char not in {"\n", "\r", "\t"})
    printable_ratio = sum(char.isprintable() or char in "\n\r\t" for char in text) / len(text)
    if replacement_ratio > 0.02 or printable_ratio < 0.85 or control_count > len(text) * 0.01:
        return "garbled"
    if len(text.strip()) < 24:
        return "degraded"
    return "good"
