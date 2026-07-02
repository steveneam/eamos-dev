from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import status
from pydantic import ValidationError

from app.schemas.workbench import (
    AlignRequest,
    AlignResponse,
    CrisprRequest,
    CrisprResponse,
    PrimerRequest,
    PrimerResponse,
)
from app.services.workbench_design_common import (
    WORKBENCH_PROVIDER_MALFORMED,
    WORKBENCH_PROVIDER_UNAVAILABLE,
    WorkbenchDesignError,
    WorkbenchModel,
)


class WorkbenchFixtureProvider:
    def __init__(self, fixtures_dir: Path | None = None) -> None:
        self.fixtures_dir = fixtures_dir or (
            Path(__file__).resolve().parents[1] / "fixtures" / "workbench"
        )

    def primers(self, _payload: PrimerRequest) -> PrimerResponse:
        return self._validate_fixture("primer_rpe65.json", PrimerResponse)

    def crispr(self, _payload: CrisprRequest) -> CrisprResponse:
        return self._validate_fixture("crispr_rpe65.json", CrisprResponse)

    def align(self, _payload: AlignRequest) -> AlignResponse:
        return self._validate_fixture("align_rpe65.json", AlignResponse)

    def _validate_fixture(
        self,
        name: str,
        model: type[WorkbenchModel],
    ) -> WorkbenchModel:
        try:
            return model(**self._load(name))
        except ValidationError as exc:
            raise WorkbenchDesignError(
                code=WORKBENCH_PROVIDER_MALFORMED,
                message=f"Workbench fixture is malformed: {name}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            ) from exc

    def _load(self, name: str) -> dict[str, Any]:
        try:
            return json.loads((self.fixtures_dir / name).read_text(encoding="utf-8"))
        except OSError as exc:
            raise WorkbenchDesignError(
                code=WORKBENCH_PROVIDER_UNAVAILABLE,
                message=f"Workbench fixture is unavailable: {name}",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc
        except ValueError as exc:
            raise WorkbenchDesignError(
                code=WORKBENCH_PROVIDER_MALFORMED,
                message=f"Workbench fixture is malformed: {name}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            ) from exc
