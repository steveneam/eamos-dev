from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.paper_variants import PaperVariantsService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract variant mentions from publication text and gate each candidate "
            "through Eamos search-input and source-backed candidate resolution. "
            "Mock-first (deterministic regex extractor); the gateway path activates "
            "only when LLM_PROVIDER=gateway. Output is sanitized."
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

    settings = Settings(jwt_secret="paper-variants-cli-local")

    pdf_meta: dict[str, Any] | None = None
    if args.pdf is not None:
        from app.services.pdf_text import extract_pdf_text

        extracted = extract_pdf_text(args.pdf, engine=settings.pdf_text_engine)
        paper_text = extracted["text"]
        pdf_meta = {
            "page_count": extracted["page_count"],
            "engine": extracted["engine"],
            "warnings": extracted["warnings"],
        }
    elif args.text is not None:
        paper_text = args.text
    else:
        paper_text = args.text_file.read_text(encoding="utf-8")

    result = PaperVariantsService(settings).extract(paper_text, validate=not args.no_validate)

    validated_count = sum(1 for v in result.variants if v.validated)
    report: dict[str, Any] = {
        "mode": "paper_variants_extract",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "llm_provider": settings.llm_provider,
        "pdf": pdf_meta,
        "source_metadata": None,
        "guardrails": {
            "patient_data": "not_used",
            "raw_paper_text_in_output": "blocked",
            "secrets_in_output": "blocked",
        },
        "candidate_count": len(result.variants),
        "validated_count": validated_count,
        "variants": [v.model_dump(mode="json") for v in result.variants],
        "warnings": result.warnings,
        "provenance": result.provenance,
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    if args.require_validated and validated_count == 0:
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
