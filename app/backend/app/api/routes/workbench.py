from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from app.schemas.workbench import (
    AlignRequest,
    AlignResponse,
    CrisprRequest,
    CrisprResponse,
    PrimerRequest,
    PrimerResponse,
)

router = APIRouter(prefix="/api/v1", tags=["workbench"])

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "workbench"


def _load(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


@router.post("/primer", response_model=PrimerResponse)
def design_primers(payload: PrimerRequest) -> PrimerResponse:
    return PrimerResponse(**_load("primer_rpe65.json"))


@router.post("/crispr", response_model=CrisprResponse)
def design_guides(payload: CrisprRequest) -> CrisprResponse:
    return CrisprResponse(**_load("crispr_rpe65.json"))


@router.post("/align", response_model=AlignResponse)
def align(payload: AlignRequest) -> AlignResponse:
    return AlignResponse(**_load("align_rpe65.json"))
