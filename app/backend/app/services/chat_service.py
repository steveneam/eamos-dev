from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import HTTPException, status

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_gateway.guard import EvidenceContextError, assert_evidence_only

logger = logging.getLogger(__name__)

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
    def __init__(self, settings, llm_client, literature_retriever=None) -> None:
        self.settings = settings
        self.llm = llm_client
        # Literature RAG retriever (gateway path only; None otherwise — see
        # build_literature_retriever). docs/ai-gateway-rag/spec.md.
        self.literature_retriever = literature_retriever

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
                    "history": self._history(payload),
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
        if self.settings.llm_provider == "mock":
            yield from self._word_chunks(self._mock_answer(payload))
            return
        if self._is_unsupported_question(payload.question):
            yield from self._word_chunks(self._unsupported_answer())
            return
        if self.llm is not None and hasattr(self.llm, "stream"):
            yield from self._stream_from_client(payload)
            return
        # Clients without native token streaming: word-chunk the full answer.
        yield from self._word_chunks(self.respond(payload).answer)

    def _stream_from_client(self, payload: ChatRequest):
        try:
            bounded_context = self._build_bounded_context(payload)
        except EvidenceContextError:
            logger.error("chat context failed evidence-only guard", exc_info=True)
            yield "Eamos could not prepare a safe evidence context for this chat."
            return
        request = {
            "question": payload.question,
            "bounded_context": bounded_context,
            "history": self._history(payload),
        }
        produced = False
        try:
            for token in self.llm.stream(request):
                if token:
                    produced = True
                    yield token
        except Exception:  # provider/transport boundary — cannot 503 mid-stream
            logger.warning("chat stream failed", exc_info=True)
            if not produced:
                yield "Eamos could not reach the chat model. Please try again."
            return
        if not produced:
            yield "Eamos cannot confirm that from the current variant evidence."

    @staticmethod
    def _word_chunks(text: str):
        if not text:
            yield ""
            return
        for word in text.split():
            yield word + " "

    @staticmethod
    def _history(payload: ChatRequest) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in payload.history]

    def _mock_answer(self, payload: ChatRequest) -> str:
        report = payload.variant_context
        gene = (
            report.variant_summary_rows[0].gene
            if report and report.variant_summary_rows
            else "this variant"
        )
        tool = payload.workbench.active_tool if payload.workbench else "lookup"
        return f"[mock] Asked about {gene} in {tool} mode: {payload.question}"

    def _build_bounded_context(self, payload: ChatRequest) -> str:
        report = payload.variant_context
        if report is None:
            # Report-less surfaces ground the chat in their own scoped context
            # only (Workbench active tool today; cohort / paper contexts later).
            # No report payload means no call cards / predictors / publications /
            # literature retrieval — just the surface scope, evidence-only.
            context = {
                "workbench": self._workbench_context(payload),
                "warnings": [],
            }
            serialized = json.dumps(context, sort_keys=True, default=str)
            assert_evidence_only(context, serialized)
            return serialized
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
                item.model_dump(mode="json", exclude_none=True) for item in computational
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
        retrieved = self._retrieved_literature(payload, report)
        if retrieved:
            context["retrieved_literature"] = retrieved
        serialized = json.dumps(context, sort_keys=True, default=str)
        assert_evidence_only(context, serialized)
        return serialized

    def _retrieved_literature(self, payload: ChatRequest, report) -> list[dict[str, Any]]:
        """Gene-scoped literature snippets for the gateway RAG path.

        Empty (the chat falls back to report-only grounding) when no retriever is
        configured, the variant has no gene, or retrieval finds nothing — never
        raises, so a retrieval miss can't break a chat turn.
        """
        if self.literature_retriever is None:
            return []
        genes = [row.gene for row in report.variant_summary_rows[:5] if getattr(row, "gene", None)]
        if not genes:
            return []
        hits = self.literature_retriever.retrieve(payload.question, genes)
        if hits:
            # Provenance: pmid + score only, never abstract text (spec §7).
            logger.info(
                "ai_gateway chat retrieval %s",
                {"retrieved": [{"pmid": hit.pmid, "score": hit.score} for hit in hits]},
            )
        return [hit.to_context_dict() for hit in hits]

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
