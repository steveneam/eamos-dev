from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.paper_extract.document import PaperInputDocument, pdf_document, text_document
from app.services.paper_variants import PaperVariantsService
from app.services.pdf_text import PdfTextLimits, extract_pdf_text

_MAX_TEXT_BYTES = 1_000_000
_FILE_CHUNK_BYTES = 64 * 1024


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run Eamos deterministic L1-L3 publication extraction, then separately "
            "gate each mention through source-backed allele resolution. Output is sanitized."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="publication text to scan")
    source.add_argument("--text-file", type=Path, help="path to a text file to scan")
    source.add_argument("--pdf", type=Path, help="path to a PDF to extract then scan")
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="skip search-input/source-backed candidate resolution",
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument(
        "--require-validated",
        action="store_true",
        help="exit non-zero unless >=1 variant validates",
    )
    args = parser.parse_args(argv)

    settings = Settings(jwt_secret="paper-variants-cli-local-only-not-a-secret")

    pdf_meta: dict[str, Any] | None = None
    if args.pdf is not None:
        pdf_limits = PdfTextLimits()
        extracted = extract_pdf_text(
            args.pdf,
            engine=settings.pdf_text_engine,
            limits=pdf_limits,
        )
        pdf_meta = {
            "page_count": extracted["page_count"],
            "engine": extracted["engine"],
            "warnings": extracted["warnings"],
        }
        if not extracted["pages"] or len(extracted["pages"]) != extracted["page_count"]:
            print(
                json.dumps(
                    {
                        "mode": "paper_variants_extract",
                        "error": "paper_pdf_unavailable",
                        "requirements": extracted["warnings"],
                    },
                    sort_keys=True,
                )
            )
            return 3
        source_info = _bounded_file_digest(args.pdf, max_bytes=pdf_limits.max_file_bytes)
        if source_info is None:
            _print_error("paper_pdf_unavailable", requirements=["pdf_file_read_failed"])
            return 3
        source_size, source_sha256 = source_info
        document = pdf_document(
            extracted,
            size_bytes=source_size,
            sha256=source_sha256,
        )
    elif args.text is not None:
        if len(args.text.encode("utf-8")) > _MAX_TEXT_BYTES:
            _print_error("text_size_limit")
            return 3
        document = text_document(args.text)
    else:
        read_status, source_bytes = _read_bounded_file(
            args.text_file,
            max_bytes=_MAX_TEXT_BYTES,
        )
        if read_status == "unavailable":
            _print_error("text_file_unavailable")
            return 3
        if read_status == "too_large":
            _print_error("text_size_limit")
            return 3
        assert source_bytes is not None
        try:
            source_text = source_bytes.decode("utf-8")
        except UnicodeDecodeError:
            _print_error("text_encoding_invalid", requirements=["utf_8_text"])
            return 3
        document = text_document(source_text)

    input_error = _document_input_error(document)
    if input_error is not None:
        error, requirements = input_error
        _print_error(error, requirements=requirements)
        return 3

    document_run = PaperVariantsService(settings).extract_document(
        document,
        validate=not args.no_validate,
    )
    result = document_run.result

    validated_count = sum(
        resolution.status == "resolved"
        for resolution in document_run.document_extraction.resolutions
    )
    report: dict[str, Any] = {
        "mode": "paper_variants_extract",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "llm_provider": "eamos_deterministic",
        "pdf": pdf_meta,
        "source_metadata": (
            document_run.source_metadata.model_dump(mode="json")
            if document_run.source_metadata is not None
            else None
        ),
        "guardrails": {
            "patient_data": "not_used",
            "raw_paper_text_in_output": "blocked",
            "secrets_in_output": "blocked",
        },
        "candidate_count": len(document_run.document_extraction.mentions),
        "validated_count": validated_count,
        "variants": [v.model_dump(mode="json") for v in result.variants],
        "warnings": result.warnings,
        "provenance": result.provenance,
        "document_extraction": document_run.document_extraction.model_dump(mode="json"),
        "execution_disclosure": document_run.document_extraction.execution_disclosure.model_dump(
            mode="json"
        ),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    if args.require_validated and validated_count == 0:
        return 2
    return 0


def _read_bounded_file(path: Path, *, max_bytes: int) -> tuple[str, bytes | None]:
    try:
        if path.stat().st_size > max_bytes:
            return "too_large", None
        with path.open("rb") as handle:
            payload = handle.read(max_bytes + 1)
    except OSError:
        return "unavailable", None
    if len(payload) > max_bytes:
        return "too_large", None
    return "ok", payload


def _bounded_file_digest(path: Path, *, max_bytes: int) -> tuple[int, str] | None:
    total = 0
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(_FILE_CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    return None
                digest.update(chunk)
    except OSError:
        return None
    return total, digest.hexdigest()


def _print_error(error: str, *, requirements: list[str] | None = None) -> None:
    payload: dict[str, Any] = {"mode": "paper_variants_extract", "error": error}
    if requirements:
        payload["requirements"] = requirements
    print(json.dumps(payload, sort_keys=True))


def _document_input_error(document: PaperInputDocument) -> tuple[str, list[str]] | None:
    qualities = {page.quality for page in document.pages}
    if not document.pages or qualities <= {"empty", "image_only"}:
        if document.kind == "pdf":
            return "ocr_required", ["local_ocr_or_selectable_text"]
        return "paper_text_empty", ["non_empty_utf_8_text"]
    if qualities <= {"garbled", "empty", "image_only"}:
        return "paper_text_ambiguous", ["clean_selectable_text_or_human_review"]
    return None


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
