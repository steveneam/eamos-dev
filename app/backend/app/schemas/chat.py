from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.run import ReportPayload

WorkbenchTool = Literal["viewer", "primer", "crispr", "align", "compare"]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4_000)


class WorkbenchEdit(BaseModel):
    position: int
    ref_base: Literal["A", "T", "C", "G"]
    new_base: Literal["A", "T", "C", "G", "del"]
    consequence: str = Field(max_length=256)


class WorkbenchContext(BaseModel):
    active_tool: WorkbenchTool
    scratchpad: list[WorkbenchEdit] = Field(default_factory=list, max_length=200)
    selected_primer_pair: int | None = None
    selected_guide: int | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4_000)
    # Optional so report-less surfaces (Workbench tool context today; cohort /
    # paper contexts later) can ground a chat in their own scope. The /report
    # surface still sends the full payload exactly as before.
    variant_context: ReportPayload | None = None
    history: list[ChatMessage] = Field(default_factory=list, max_length=24)
    workbench: WorkbenchContext | None = None

    @model_validator(mode="after")
    def _require_scoped_context(self) -> "ChatRequest":
        # Ask-Eamos is scoped per surface, never a free-floating assistant: every
        # request must carry at least one grounding context (a report payload for
        # /report, or a Workbench tool context for /workbench). This keeps the
        # evidence-only guard meaningful and the prompt window tight.
        if self.variant_context is None and self.workbench is None:
            raise ValueError("ChatRequest requires a scoped context: variant_context or workbench.")
        return self


class ChatResponse(BaseModel):
    answer: str


class LookupChatAnswerDraft(BaseModel):
    answer: str


class RunChatRequest(BaseModel):
    question: str = Field(min_length=1)


class RunChatCitation(BaseModel):
    title: str
    snippet: str
    source_type: Literal["run_section", "report_extract", "evidence"]
    section: str | None = None


class RunChatAnswerDraft(BaseModel):
    answer: str
    grounded: bool = True
    cited_chunk_ids: list[int] = Field(default_factory=list)


class RunChatResponse(BaseModel):
    question: str
    answer: str
    grounded: bool = True
    citations: list[RunChatCitation] = Field(default_factory=list)
