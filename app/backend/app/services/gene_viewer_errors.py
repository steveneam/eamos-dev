from __future__ import annotations

from typing import Any

from fastapi import status

from app.services.sequence_context import unsupported_input_warning
from app.services.workbench_design import (
    WORKBENCH_PROVIDER_FAILED_PREFIX,
    WORKBENCH_PROVIDER_MALFORMED,
    WORKBENCH_PROVIDER_UNAVAILABLE,
)

GENE_VIEWER_PROVIDER_UNAVAILABLE = WORKBENCH_PROVIDER_UNAVAILABLE
GENE_VIEWER_PROVIDER_MALFORMED = WORKBENCH_PROVIDER_MALFORMED
GENE_VIEWER_PROVIDER_FAILED_PREFIX = WORKBENCH_PROVIDER_FAILED_PREFIX
GENE_VIEWER_SERVICE_UNAVAILABLE = "workbench_viewer_service_unavailable"
GENE_VIEWER_LIVE_UNAVAILABLE = "workbench_viewer_live_unavailable"
GENE_VIEWER_REFERENCE_MISMATCH = unsupported_input_warning("reference_mismatch")
GENE_VIEWER_UNSUPPORTED_VARIANT = unsupported_input_warning("variant_type")
GENE_VIEWER_CURATED_FIXTURE_FALLBACK = "gene_viewer_curated_fixture_fallback"
GENE_VIEWER_LIVE_PROVIDER_FALLBACK_PREFIX = "gene_viewer_live_provider_failed_fallback"
HTTP_UNPROCESSABLE_ENTITY = 422


class GeneViewerError(Exception):
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


def raise_unsupported_gene_viewer_input(kind: str, message: str) -> None:
    code = unsupported_input_warning(kind)
    raise GeneViewerError(
        code=code,
        message=message,
        status_code=HTTP_UNPROCESSABLE_ENTITY,
        warnings=[code],
    )
