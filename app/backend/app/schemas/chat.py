from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
