"""Bounded, page-preserving PDF text extraction.

The release path supports the permissive pypdf baseline and an optional PDFium
adapter. PyMuPDF/fitz is deliberately prohibited pending a separate licence
decision. Parser failures return typed, payload-free warnings; paths and source
text are never logged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)

DEFAULT_ENGINE = "pypdf"
SUPPORTED_ENGINES = ("pypdf", "pdfium")
PROHIBITED_ENGINES = ("fitz", "pymupdf")


@dataclass(frozen=True, slots=True)
class PdfTextLimits:
    max_file_bytes: int = 50_000_000
    max_pages: int = 500
    max_objects: int = 200_000
    max_declared_page_stream_bytes: int = 20_000_000
    max_declared_total_stream_bytes: int = 50_000_000
    max_page_characters: int = 500_000
    max_total_characters: int = 2_000_000
    max_images_per_page: int = 200


def extract_pdf_text(
    file_path: Any,
    *,
    engine: str = DEFAULT_ENGINE,
    limits: PdfTextLimits | None = None,
) -> dict[str, Any]:
    """Return page text, quality, metadata, and typed warnings for one PDF."""
    normalized_engine = str(engine or DEFAULT_ENGINE).strip().lower()
    if normalized_engine in PROHIBITED_ENGINES:
        return _empty(normalized_engine, f"pdf_engine_prohibited:{normalized_engine}")
    if normalized_engine not in SUPPORTED_ENGINES:
        return _empty(normalized_engine, f"unsupported_pdf_engine:{normalized_engine}")

    path = Path(file_path)
    if not path.is_file():
        return _empty(normalized_engine, "pdf_file_missing")
    active_limits = limits or PdfTextLimits()
    try:
        size = path.stat().st_size
        if size <= 0:
            return _empty(normalized_engine, "pdf_file_empty")
        if size > active_limits.max_file_bytes:
            return _empty(normalized_engine, "pdf_file_size_limit_exceeded")
        with path.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                return _empty(normalized_engine, "pdf_signature_invalid")
        if normalized_engine == "pdfium":
            return _extract_pdfium(path, active_limits)
        return _extract_pypdf(path, active_limits)
    except Exception as exc:  # parser boundary: never echo payload, path, or exception text
        logger.warning(
            "pdf extraction failed (engine=%s, error_type=%s)",
            normalized_engine,
            type(exc).__name__,
        )
        return _empty(normalized_engine, f"pdf_parse_failed:{type(exc).__name__}")


def _empty(engine: str, warning: str) -> dict[str, Any]:
    return {
        "text": "",
        "pages": [],
        "page_count": 0,
        "engine": engine,
        "engine_version": "unavailable",
        "metadata": {},
        "warnings": [warning],
    }


def _extract_pypdf(path: Path, limits: PdfTextLimits) -> dict[str, Any]:
    import pypdf
    from pypdf import PdfReader

    reader = PdfReader(str(path), strict=False)
    if reader.is_encrypted and reader.decrypt("") == 0:
        return _empty("pypdf", "pdf_encrypted")
    page_count = len(reader.pages)
    if page_count < 1:
        return _empty("pypdf", "pdf_has_no_pages")
    if page_count > limits.max_pages:
        return _limited(
            engine="pypdf",
            engine_version=pypdf.__version__,
            page_count=page_count,
            metadata=_pypdf_metadata(reader),
            warning="pdf_page_limit_exceeded",
        )
    if _pypdf_object_count(reader) > limits.max_objects:
        return _limited(
            engine="pypdf",
            engine_version=pypdf.__version__,
            page_count=page_count,
            metadata=_pypdf_metadata(reader),
            warning="pdf_object_limit_exceeded",
        )

    pages: list[dict[str, Any]] = []
    warnings: list[str] = []
    total_characters = 0
    total_declared_stream_bytes = 0
    for index, page in enumerate(reader.pages, start=1):
        declared_stream_bytes = _declared_content_bytes(page)
        total_declared_stream_bytes += declared_stream_bytes
        if (
            declared_stream_bytes > limits.max_declared_page_stream_bytes
            or total_declared_stream_bytes > limits.max_declared_total_stream_bytes
        ):
            return _limited(
                engine="pypdf",
                engine_version=pypdf.__version__,
                page_count=page_count,
                metadata=_pypdf_metadata(reader),
                warning=f"pdf_stream_limit_exceeded:page:{index}",
            )
        image_count = _image_count(page)
        if image_count > limits.max_images_per_page:
            return _limited(
                engine="pypdf",
                engine_version=pypdf.__version__,
                page_count=page_count,
                metadata=_pypdf_metadata(reader),
                warning=f"pdf_image_count_limit_exceeded:page:{index}",
            )
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # per-page fail closed without exception detail
            text = ""
            warnings.append(f"pdf_page_parse_failed:{index}:{type(exc).__name__}")
        if len(text) > limits.max_page_characters:
            return _limited(
                engine="pypdf",
                engine_version=pypdf.__version__,
                page_count=page_count,
                metadata=_pypdf_metadata(reader),
                warning=f"pdf_character_limit_exceeded:page:{index}",
            )
        total_characters += len(text)
        if total_characters > limits.max_total_characters:
            return _limited(
                engine="pypdf",
                engine_version=pypdf.__version__,
                page_count=page_count,
                metadata=_pypdf_metadata(reader),
                warning="pdf_character_limit_exceeded:document",
            )
        page_row = _page_row(index=index, text=text, image_count=image_count)
        pages.append(page_row)
        warnings.extend(page_row["warnings"])
    return _result(
        engine="pypdf",
        engine_version=pypdf.__version__,
        pages=pages,
        metadata=_pypdf_metadata(reader),
        warnings=warnings,
    )


def _extract_pdfium(path: Path, limits: PdfTextLimits) -> dict[str, Any]:
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return _empty("pdfium", "pdf_engine_unavailable:pdfium:pypdfium2")

    version = str(getattr(getattr(pdfium, "PYPDFIUM_INFO", None), "version", "unknown"))
    document = pdfium.PdfDocument(str(path))
    try:
        page_count = len(document)
        if page_count < 1:
            return _empty("pdfium", "pdf_has_no_pages")
        if page_count > limits.max_pages:
            return _limited(
                engine="pdfium",
                engine_version=version,
                page_count=page_count,
                metadata={},
                warning="pdf_page_limit_exceeded",
            )
        pages: list[dict[str, Any]] = []
        warnings: list[str] = []
        total_characters = 0
        for index in range(page_count):
            page = document[index]
            try:
                text_page = page.get_textpage()
                try:
                    text = text_page.get_text_range() or ""
                finally:
                    text_page.close()
            finally:
                page.close()
            if len(text) > limits.max_page_characters:
                return _limited(
                    engine="pdfium",
                    engine_version=version,
                    page_count=page_count,
                    metadata={},
                    warning=f"pdf_character_limit_exceeded:page:{index + 1}",
                )
            total_characters += len(text)
            if total_characters > limits.max_total_characters:
                return _limited(
                    engine="pdfium",
                    engine_version=version,
                    page_count=page_count,
                    metadata={},
                    warning="pdf_character_limit_exceeded:document",
                )
            page_row = _page_row(index=index + 1, text=text, image_count=0)
            pages.append(page_row)
            warnings.extend(page_row["warnings"])
        metadata = _clean_metadata(document.get_metadata_dict())
        return _result(
            engine="pdfium",
            engine_version=version,
            pages=pages,
            metadata=metadata,
            warnings=warnings,
        )
    finally:
        document.close()


def _result(
    *,
    engine: str,
    engine_version: str,
    pages: list[dict[str, Any]],
    metadata: Mapping[str, str],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "text": "\n".join(page["text"] for page in pages if page["text"]).strip(),
        "pages": pages,
        "page_count": len(pages),
        "engine": engine,
        "engine_version": engine_version,
        "metadata": dict(metadata),
        "warnings": list(dict.fromkeys(warnings)),
    }


def _limited(
    *,
    engine: str,
    engine_version: str,
    page_count: int,
    metadata: Mapping[str, str],
    warning: str,
) -> dict[str, Any]:
    return {
        "text": "",
        "pages": [],
        "page_count": page_count,
        "engine": engine,
        "engine_version": engine_version,
        "metadata": dict(metadata),
        "warnings": [warning],
    }


def _page_row(*, index: int, text: str, image_count: int) -> dict[str, Any]:
    replacement_ratio = text.count("\ufffd") / max(1, len(text))
    printable_ratio = sum(char.isprintable() or char in "\n\r\t" for char in text) / max(
        1, len(text)
    )
    control_count = sum(1 for char in text if ord(char) < 32 and char not in {"\n", "\r", "\t"})
    warnings: list[str] = []
    if not text.strip():
        quality = "image_only" if image_count else "empty"
        warnings.append(f"ocr_required:page:{index}")
    elif replacement_ratio > 0.02 or printable_ratio < 0.85 or control_count > len(text) * 0.01:
        quality = "garbled"
        warnings.append(f"text_ambiguous:page:{index}")
    elif len(text.strip()) < 24:
        quality = "degraded"
    else:
        quality = "good"
    return {
        "page_number": index,
        "text": text,
        "quality": quality,
        "replacement_character_ratio": replacement_ratio,
        "image_count": image_count,
        "warnings": warnings,
    }


def _pypdf_object_count(reader: Any) -> int:
    xref = getattr(reader, "xref", {})
    if not isinstance(xref, Mapping):
        return 0
    return sum(len(bucket) for bucket in xref.values() if isinstance(bucket, Mapping))


def _declared_content_bytes(page: Any) -> int:
    try:
        contents = page.get("/Contents")
        if contents is None:
            return 0
        objects = list(contents) if isinstance(contents, list) else [contents]
        total = 0
        for item in objects:
            resolved = item.get_object() if hasattr(item, "get_object") else item
            length = resolved.get("/Length", 0) if hasattr(resolved, "get") else 0
            if hasattr(length, "get_object"):
                length = length.get_object()
            if isinstance(length, int) and length > 0:
                total += length
        return total
    except Exception:
        return 0


def _image_count(page: Any) -> int:
    try:
        resources = page.get("/Resources")
        resources = resources.get_object() if hasattr(resources, "get_object") else resources
        xobjects = resources.get("/XObject") if hasattr(resources, "get") else None
        xobjects = xobjects.get_object() if hasattr(xobjects, "get_object") else xobjects
        count = 0
        for item in xobjects.values() if hasattr(xobjects, "values") else ():
            resolved = item.get_object() if hasattr(item, "get_object") else item
            if hasattr(resolved, "get") and str(resolved.get("/Subtype")) == "/Image":
                count += 1
        return count
    except Exception:
        return 0


def _pypdf_metadata(reader: Any) -> dict[str, str]:
    metadata = _clean_metadata(getattr(reader, "metadata", None) or {})
    try:
        xmp = getattr(reader, "xmp_metadata", None)
        if xmp is not None:
            if getattr(xmp, "dc_title", None):
                title = getattr(xmp, "dc_title")
                metadata.setdefault(
                    "title", str(title.get("x-default") or next(iter(title.values())))
                )
            if getattr(xmp, "dc_creator", None):
                metadata.setdefault("author", "; ".join(map(str, getattr(xmp, "dc_creator"))))
    except Exception:
        pass
    return metadata


def _clean_metadata(value: Mapping[str, Any]) -> dict[str, str]:
    clean: dict[str, str] = {}
    for key, raw in value.items():
        if raw is None:
            continue
        safe_key = str(key).strip().lower().lstrip("/")[:64]
        safe_value = str(raw).replace("\x00", " ").strip()[:512]
        if safe_key and safe_value:
            clean[safe_key] = safe_value
    return clean
