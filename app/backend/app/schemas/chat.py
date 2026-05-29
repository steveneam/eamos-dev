from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.run import ReportPayload

WorkbenchTool = Literal["viewer", "primer", "crispr", "align", "compare"]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class WorkbenchEdit(BaseModel):
    position: int
    ref_base: Literal["A", "T", "C", "G"]
    new_base: Literal["A", "T", "C", "G", "del"]
    consequence: str


class WorkbenchContext(BaseModel):
    active_tool: WorkbenchTool
    scratchpad: list[WorkbenchEdit] = Field(default_factory=list)
    selected_primer_pair: int | None = None
    selected_guide: int | None = None


class ChatRequest(BaseModel):
    question: str
    variant_context: ReportPayload
    history: list[ChatMessage] = Field(default_factory=list)
    workbench: WorkbenchContext | None = None


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
