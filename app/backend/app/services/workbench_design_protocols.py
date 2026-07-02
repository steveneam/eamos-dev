from __future__ import annotations

from typing import Protocol

from app.schemas.workbench import (
    AlignRequest,
    AlignResponse,
    CrisprOffTargetRequest,
    CrisprOffTargetResponse,
    CrisprRequest,
    CrisprResponse,
    PrimerRequest,
    PrimerResponse,
)
from app.services.sequence_context import SequenceContext


class PrimerDesignProvider(Protocol):
    def design(self, payload: PrimerRequest, context: SequenceContext) -> PrimerResponse: ...


class CrisprDesignProvider(Protocol):
    def design(self, payload: CrisprRequest, context: SequenceContext) -> CrisprResponse: ...


class CrisprOffTargetProvider(Protocol):
    def enumerate(self, payload: CrisprOffTargetRequest) -> CrisprOffTargetResponse: ...


class AlignProvider(Protocol):
    def align(self, payload: AlignRequest, context: SequenceContext) -> AlignResponse: ...
