from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.agents.prompts import (
    current_run_chat_prompt,
    draft_prompt,
    extraction_prompt,
    gateway_chat_prompt,
    lookup_chat_prompt,
    search_input_extraction_prompt,
)

from app.core.config import Settings
from app.schemas.chat import LookupChatAnswerDraft, RunChatAnswerDraft
from app.schemas.draft import DraftPayload
from app.schemas.lookup import SearchInputAiExtraction
from app.schemas.report import ExtractedCase
from pydantic import SecretStr

logger = logging.getLogger(__name__)


class MockExtractionChain:
    def __init__(self, fixture_path: Path) -> None:
        self.fixture_path = fixture_path

    def invoke(self, _: dict[str, Any]) -> dict[str, Any]:
        return json.loads(self.fixture_path.read_text())


class MockDraftChain:
    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload


def build_tool_enabled_llm(settings: Settings):
    if settings.llm_provider == "mock" or not settings.openai_api_key:
        return None
    from langchain_openai import ChatOpenAI

    api_key = SecretStr(settings.openai_api_key)
    return ChatOpenAI(model=settings.openai_model, api_key=api_key, temperature=0)


def build_extraction_chain(settings: Settings):
    model = build_tool_enabled_llm(settings)
    if model is None:
        return None

    class LiveExtractionChain:
        def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
            from langchain_core.prompts import ChatPromptTemplate

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", extraction_prompt()),
                    ("human", "Filename: {filename}\nReport text:\n{report_text}"),
                ]
            )
            chain = prompt | model.with_structured_output(ExtractedCase)
            result = chain.invoke(payload)
            if isinstance(result, ExtractedCase):
                return result.model_dump(mode="json")
            return dict(result)

    return LiveExtractionChain()


def build_draft_chain(settings: Settings):
    if settings.llm_provider == "mock" or not settings.openai_api_key:
        return None
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=settings.openai_model,
        api_key=SecretStr(settings.openai_api_key),
        temperature=0.2,
    )

    class LiveDraftChain:
        def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
            from langchain_core.prompts import ChatPromptTemplate

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", draft_prompt()),
                    (
                        "human",
                        "Case title: {case_title}\n"
                        "Patient context: {patient_context}\n"
                        "Clinical phenotype: {clinical_phenotype}\n"
                        "Variant summary: {variant_summary}\n"
                        "Deterministic recommendation: {recommendation}\n"
                        "Evidence lines: {evidence_lines}\n"
                        "Uncertainty: {uncertainty}\n"
                        "Next step: {next_step}\n"
                        "Confidence label: {confidence_label}\n"
                        "Evidence statuses: {evidence_statuses}\n"
                        "Warnings: {warnings}\n"
                        "Compose these into distinct report narrative sections only.",
                    ),
                    (
                        "human",
                        "Current deterministic base text:\n"
                        "AI clinical summary: {ai_clinical_summary}\n"
                        "Expanded evidence: {expanded_evidence}\n"
                        "Clinical integration: {clinical_integration}\n"
                        "Recommendations: {recommendations}\n"
                        "Limitations: {limitations}\n"
                        "Improve the writing quality while staying grounded in this material.",
                    ),
                ]
            )
            chain = prompt | model.with_structured_output(DraftPayload)
            result = chain.invoke(payload)
            if isinstance(result, DraftPayload):
                return result.model_dump(mode="json")
            return dict(result)

    return LiveDraftChain()


def build_embeddings_model(settings: Settings):
    if settings.llm_provider == "mock" or not settings.openai_api_key:
        return None
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=settings.openai_embeddings_model,
        api_key=SecretStr(settings.openai_api_key),
    )


def build_run_chat_chain(settings: Settings):
    if settings.llm_provider == "mock" or not settings.openai_api_key:
        return None
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=settings.openai_model,
        api_key=SecretStr(settings.openai_api_key),
        temperature=0,
    )

    class LiveRunChatChain:
        def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
            from langchain_core.prompts import ChatPromptTemplate

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", current_run_chat_prompt()),
                    (
                        "human",
                        "Question: {question}\n\n"
                        "Retrieved context:\n{retrieved_context}\n\n"
                        "Use only this material when answering.",
                    ),
                ]
            )
            chain = prompt | model.with_structured_output(RunChatAnswerDraft)
            result = chain.invoke(payload)
            if isinstance(result, RunChatAnswerDraft):
                return result.model_dump(mode="json")
            return dict(result)

    return LiveRunChatChain()


def build_lookup_chat_chain(settings: Settings):
    if settings.llm_provider == "mock" or not settings.openai_api_key:
        return None
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=settings.openai_model,
        api_key=SecretStr(settings.openai_api_key),
        temperature=0,
        timeout=settings.lookup_chat_timeout_seconds,
    )

    class LiveLookupChatChain:
        def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
            from langchain_core.prompts import ChatPromptTemplate

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", lookup_chat_prompt()),
                    (
                        "human",
                        "Question:\n{question}\n\n"
                        "Bounded Eamos lookup and Workbench context:\n{bounded_context}",
                    ),
                ]
            )
            chain = prompt | model.with_structured_output(LookupChatAnswerDraft)
            result = chain.invoke(payload)
            if isinstance(result, LookupChatAnswerDraft):
                return result.model_dump(mode="json")
            return dict(result)

    return LiveLookupChatChain()


def build_search_input_ai_chain(settings: Settings):
    if (
        not settings.search_input_ai_enabled
        or settings.llm_provider == "mock"
        or not settings.openai_api_key
    ):
        return None
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=settings.openai_model,
        api_key=SecretStr(settings.openai_api_key),
        temperature=0,
        timeout=settings.search_input_ai_timeout_seconds,
    )

    class LiveSearchInputAiChain:
        def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
            from langchain_core.prompts import ChatPromptTemplate

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", search_input_extraction_prompt()),
                    (
                        "human",
                        "Submitted search text:\n{search_text}\n\n"
                        "Curated Eamos reference context:\n{reference_context}",
                    ),
                ]
            )
            chain = prompt | model.with_structured_output(SearchInputAiExtraction)
            result = chain.invoke(payload)
            if isinstance(result, SearchInputAiExtraction):
                return result.model_dump(mode="json")
            return dict(result)

    return LiveSearchInputAiChain()


_GATEWAY_HISTORY_TURNS = 8


def build_gateway_messages(
    system_prompt: str,
    question: str,
    bounded_context: str,
    history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Compose the OpenAI-style message list for a gateway variant-chat turn:
    system prompt, the most recent prior turns, then the current question with
    the bounded evidence context."""
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for turn in (history or [])[-_GATEWAY_HISTORY_TURNS:]:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append(
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\n"
                f"Bounded Eamos lookup and Workbench context:\n{bounded_context}"
            ),
        }
    )
    return messages


def build_gateway_chat_client(settings: Settings, *, engine=None):
    """Lookup-chat client backed by the Vercel AI Gateway broker.

    Returns None unless `llm_provider == "gateway"` and a gateway key is set, so
    the mock/OpenAI paths are unaffected. The `engine` seam lets tests inject a
    fake broker. Exposes `invoke` (non-streaming) and `stream` (token streaming),
    matching the ChatService client contract."""
    if settings.llm_provider != "gateway" or not settings.ai_gateway_api_key:
        return None

    if engine is None:
        from app.services.ai_gateway import AIGatewayEngine

        engine = AIGatewayEngine(
            api_key=settings.ai_gateway_api_key,
            model=settings.ai_gateway_model,
            provider_order=settings.ai_gateway_provider_order,
            base_url=settings.ai_gateway_base_url,
            temperature=settings.ai_gateway_chat_temperature,
            max_tokens=settings.ai_gateway_max_tokens,
            timeout_seconds=settings.ai_gateway_timeout_seconds,
            max_retries=settings.ai_gateway_max_retries,
        )

    from app.services.ai_gateway import GatewayResult

    system_prompt = gateway_chat_prompt()
    model_name = settings.ai_gateway_model

    def _messages(payload: dict[str, Any]) -> list[dict[str, str]]:
        return build_gateway_messages(
            system_prompt,
            payload.get("question", ""),
            payload.get("bounded_context", ""),
            payload.get("history"),
        )

    class GatewayChatClient:
        def invoke(self, payload: dict[str, Any]) -> dict[str, str]:
            result = engine.complete(_messages(payload))
            logger.info("ai_gateway chat complete %s", result.log_fields(model_name))
            return {"answer": result.content}

        def stream(self, payload: dict[str, Any]):
            meta = GatewayResult()
            try:
                yield from engine.stream_chat(_messages(payload), meta=meta)
            finally:
                logger.info("ai_gateway chat stream %s", meta.log_fields(model_name))

    return GatewayChatClient()
