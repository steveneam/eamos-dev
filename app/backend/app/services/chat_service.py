from __future__ import annotations

from app.schemas.chat import ChatRequest, ChatResponse


class ChatService:
    def __init__(self, settings, llm_client) -> None:
        self.settings = settings
        self.llm = llm_client

    def respond(self, payload: ChatRequest) -> ChatResponse:
        if self.settings.llm_provider == "mock":
            return ChatResponse(answer=self._mock_answer(payload))
        return ChatResponse(answer=self.llm.complete(self._build_prompt(payload)))

    def respond_stream(self, payload: ChatRequest):
        text = self.respond(payload).answer
        for word in text.split():
            yield word + " "

    def _mock_answer(self, payload: ChatRequest) -> str:
        gene = (
            payload.variant_context.variant_summary_rows[0].gene
            if payload.variant_context.variant_summary_rows
            else "this variant"
        )
        tool = payload.workbench.active_tool if payload.workbench else "lookup"
        return f"[mock] Asked about {gene} in {tool} mode: {payload.question}"

    def _build_prompt(self, payload: ChatRequest) -> str:
        base = (
            "You are Eamos, a genomic evidence assistant. Cite source databases with bracket tags like "
            "[CV] [gn] [SA] [AM] [RV] [OM] [CT] [UP] [PP]. Never provide diagnoses."
        )
        if payload.workbench:
            wb = payload.workbench
            base += f"\nWorkbench context: active tool = {wb.active_tool}. Scratchpad has {len(wb.scratchpad)} edits."
        return f"{base}\n\nQuestion: {payload.question}"
