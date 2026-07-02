from __future__ import annotations

import re
from pathlib import Path
from typing import Any, TypeVar

from fastapi import status
from pydantic import BaseModel

from app.core.config import Settings

WORKBENCH_PROVIDER_FAILED_PREFIX = "workbench_provider_failed"
WORKBENCH_PROVIDER_MALFORMED = "workbench_provider_malformed"
WORKBENCH_PROVIDER_UNAVAILABLE = "workbench_provider_unavailable"
WORKBENCH_SERVICE_UNAVAILABLE = "workbench_service_unavailable"
HTTP_UNPROCESSABLE_ENTITY = 422
PRIMER_SPECIFICITY_TEMPLATE = "template"
PRIMER_SPECIFICITY_UCSC_ISPCR = "ucsc_ispcr"
ALIGN_MAX_SEQUENCE_BASES = 5000
ALIGN_MAX_MATRIX_CELLS = 4_000_000
ALIGN_MATCH_SCORE = 2
ALIGN_MISMATCH_SCORE = -1
ALIGN_GAP_SCORE = -2
WorkbenchModel = TypeVar("WorkbenchModel", bound=BaseModel)


class WorkbenchDesignError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE,
        warnings: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.warnings = warnings if warnings is not None else [code]

    def to_http_detail(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "warnings": self.warnings,
        }


def _clean_template(sequence: str) -> str:
    return re.sub(r"[^ACGTN]", "N", sequence.upper())


_COMPLEMENT = str.maketrans("ACGTN", "TGCAN")


def _reverse_complement(sequence: str) -> str:
    return sequence.translate(_COMPLEMENT)[::-1]


def _settings_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path
