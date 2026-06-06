from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status

from app.schemas.chat import ChatRequest, ChatResponse

UNSUPPORTED_QUESTION_TERMS = (
    "diagnose",
    "diagnosis",
    "what medication",
    "which medication",
    "what drug",
    "which drug",
    "start treatment",
    "treatment should",
    "therapy should",
    "prescribe",
)


class ChatService:
    def __init__(self, settings, llm_client) -> None:
        self.settings = settings
        self.llm = llm_client

    def respond(self, payload: ChatRequest) -> ChatResponse:
        if self.settings.llm_provider == "mock":
            return ChatResponse(answer=self._mock_answer(payload))
        if self._is_unsupported_question(payload.question):
            return ChatResponse(answer=self._unsupported_answer())
        if self.llm is None or not hasattr(self.llm, "invoke"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Lookup chat model is not configured.",
            )

        try:
            draft = self.llm.invoke(
                {
                    "question": payload.question,
                    "bounded_context": self._build_bounded_context(payload),
                }
            )
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Lookup chat model failed.",
            ) from exc

        if hasattr(draft, "model_dump"):
            draft = draft.model_dump(mode="json")
        draft_payload = draft if isinstance(draft, dict) else {}
        answer = str(draft_payload.get("answer", "")).strip()
        if not answer:
            answer = "Eamos cannot confirm that from the current variant evidence."
        return ChatResponse(answer=answer)

    def respond_stream(self, payload: ChatRequest):
        text = self.respond(payload).answer
        if not text:
            yield ""
            return
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

    def _build_bounded_context(self, payload: ChatRequest) -> str:
        report = payload.variant_context
        profile = report.report_profile
        computational = (
            profile.computational_deep_dive.predictors
            if profile and profile.computational_deep_dive
            else []
        )
        expert_panel = profile.expert_panel if profile else None
        context: dict[str, Any] = {
            "variant_summary_rows": [
                row.model_dump(mode="json", exclude_none=True)
                for row in report.variant_summary_rows[:5]
            ],
            "call_cards": [
                {
                    "title": card.title,
                    "primary_label": card.primary_label,
                    "source_status": card.source_status,
                    "support_badges": [
                        badge.model_dump(mode="json", exclude_none=True)
                        for badge in card.support_badges[:5]
                    ],
                    "warnings": card.warnings[:5],
                }
                for card in (report.call_cards.cards if report.call_cards else [])[:4]
            ],
            "population_frequency": (
                report.population_frequency_detail.model_dump(mode="json", exclude_none=True)
                if report.population_frequency_detail
                else None
            ),
            "publications": self._publication_context(report),
            "functional_evidence": (
                {
                    "total_count": report.functional_evidence.total_count,
                    "evidence_codes": report.functional_evidence.evidence_codes,
                    "source_asserted_codes": report.functional_evidence.source_asserted_codes,
                    "warnings": report.functional_evidence.warnings[:5],
                }
                if report.functional_evidence
                else None
            ),
            "computational_predictors": [
                item.model_dump(mode="json", exclude_none=True)
                for item in computational
            ][:8],
            "expert_panel": (
                {
                    "vcep": expert_panel.vcep.model_dump(mode="json", exclude_none=True),
                    "final_classification": expert_panel.final_classification,
                    "freshness": expert_panel.freshness,
                    "source_scope": expert_panel.source_scope,
                }
                if expert_panel
                else None
            ),
            "workbench": self._workbench_context(payload),
            "warnings": self._context_warnings(report),
        }
        return json.dumps(context, sort_keys=True, default=str)

    def _publication_context(self, payload) -> dict[str, Any] | None:
        if not payload.publications_callout and not payload.publications_literature:
            return None
        return {
            "callout": (
                {
                    "total_count": payload.publications_callout.total_count,
                    "scope_counts": (
                        payload.publications_callout.scope_counts.model_dump(
                            mode="json", exclude_none=True
                        )
                        if payload.publications_callout.scope_counts
                        else None
                    ),
                }
                if payload.publications_callout
                else None
            ),
            "literature": (
                {
                    "total_count": payload.publications_literature.total_count,
                    "shown_count": payload.publications_literature.shown_count,
                    "scope": payload.publications_literature.scope,
                    "source_breakdown": payload.publications_literature.source_breakdown.model_dump(
                        mode="json"
                    ),
                    "scope_counts": (
                        payload.publications_literature.scope_counts.model_dump(
                            mode="json", exclude_none=True
                        )
                        if payload.publications_literature.scope_counts
                        else None
                    ),
                    "warnings": payload.publications_literature.warnings[:5],
                }
                if payload.publications_literature
                else None
            ),
        }

    def _workbench_context(self, payload: ChatRequest) -> dict[str, Any] | None:
        if payload.workbench is None:
            return None
        return {
            "active_tool": payload.workbench.active_tool,
            "scratchpad_edit_count": len(payload.workbench.scratchpad),
            "selected_primer_pair": payload.workbench.selected_primer_pair,
            "selected_guide": payload.workbench.selected_guide,
        }

    def _context_warnings(self, payload) -> list[str]:
        warnings: list[str] = []
        if payload.publications_literature:
            warnings.extend(payload.publications_literature.warnings[:5])
        if payload.functional_evidence:
            warnings.extend(payload.functional_evidence.warnings[:5])
        if payload.population_frequency_detail:
            warnings.extend(payload.population_frequency_detail.warnings[:5])
        return warnings[:12]

    def _is_unsupported_question(self, question: str) -> bool:
        normalized = question.lower()
        return any(term in normalized for term in UNSUPPORTED_QUESTION_TERMS)

    def _unsupported_answer(self) -> str:
        return (
            "Eamos cannot provide diagnosis, prescribing, or treatment guidance from this chat. "
            "Ask about the current variant evidence, source status, or Workbench context instead."
        )
