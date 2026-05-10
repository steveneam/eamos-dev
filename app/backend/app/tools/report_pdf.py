from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


class ReportPdfTool:
    def extract(self, file_path: Path) -> dict[str, object]:
        warnings: list[str] = []
        text_parts: list[str] = []
        page_count = 0
        try:
            reader = PdfReader(str(file_path))
            page_count = len(reader.pages)
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
        except Exception as exc:  # pragma: no cover - exercised indirectly via upload path
            warnings.append(f"pdf_parse_failed:{type(exc).__name__}")
        return {
            "text": "\n".join(part for part in text_parts if part).strip(),
            "page_count": page_count,
            "warnings": warnings,
        }
