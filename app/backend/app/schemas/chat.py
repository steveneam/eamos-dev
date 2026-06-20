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


class PaperCandidateContext(BaseModel):
    """One resolved Paper → Variants candidate, bounded + sanitized for the chat
    context: identity, resolution status, a short evidence quote, and which papers
    mentioned it — never the full paper body (spec §8: provenance, not raw text)."""

    gene: str | None = Field(default=None, max_length=64)
    hgvs: str | None = Field(default=None, max_length=256)
    level: str = Field(default="unknown", max_length=32)
    context: str = Field(default="unknown", max_length=32)
    validation_status: str = Field(default="missing", max_length=32)
    validated: bool = False
    evidence_quote: str | None = Field(default=None, max_length=400)
    source_support: list[str] = Field(default_factory=list, max_length=12)
    papers: list[str] = Field(default_factory=list, max_length=12)


class PaperContext(BaseModel):
    """The /paper Ask-Eamos scope: this run's resolved candidates plus their source
    provenance, never a free-floating chat or the raw paper text (spec §8). The
    chat *adjudicates* over what the extractor already resolved; it does not
    re-extract."""

    candidates: list[PaperCandidateContext] = Field(default_factory=list, max_length=50)
    source_count: int = Field(default=0, ge=0)
    sources: list[str] = Field(default_factory=list, max_length=24)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4_000)
    # Optional so report-less surfaces (Workbench tool context, Paper → Variants;
    # cohort contexts later) can ground a chat in their own scope. The /report
    # surface still sends the full payload exactly as before.
    variant_context: ReportPayload | None = None
    history: list[ChatMessage] = Field(default_factory=list, max_length=24)
    workbench: WorkbenchContext | None = None
    paper: PaperContext | None = None

    @model_validator(mode="after")
    def _require_scoped_context(self) -> "ChatRequest":
        # Ask-Eamos is scoped per surface, never a free-floating assistant: every
        # request must carry at least one grounding context (a report payload for
        # /report, a Workbench tool context for /workbench, or this paper's resolved
        # candidates for /paper). This keeps the evidence-only guard meaningful and
        # the prompt window tight.
        if self.variant_context is None and self.workbench is None and self.paper is None:
            raise ValueError(
                "ChatRequest requires a scoped context: variant_context, workbench, or paper."
            )
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
