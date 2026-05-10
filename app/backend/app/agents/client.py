from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.agents.prompts import current_run_chat_prompt, draft_prompt, extraction_prompt
from app.core.config import Settings
from app.schemas.chat import RunChatAnswerDraft
from app.schemas.draft import DraftPayload
from app.schemas.report import ExtractedCase
from pydantic import SecretStr


class MockExtractionChain:
    def __init__(self, fixture_path: Path) -> None:
        self.fixture_path = fixture_path

    def invoke(self, _: dict[str, Any]) -> dict[str, Any]:
        return json.loads(self.fixture_path.read_text())


class MockDraftChain:
    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload


def build_tool_enabled_llm(settings: Settings):
    if settings.llm_provider == 'mock' or not settings.openai_api_key:
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

            prompt = ChatPromptTemplate.from_messages([
                ('system', extraction_prompt()),
                ('human', 'Filename: {filename}\nReport text:\n{report_text}'),
            ])
            chain = prompt | model.with_structured_output(ExtractedCase)
            result = chain.invoke(payload)
            if isinstance(result, ExtractedCase):
                return result.model_dump(mode='json')
            return dict(result)

    return LiveExtractionChain()


def build_draft_chain(settings: Settings):
    if settings.llm_provider == 'mock' or not settings.openai_api_key:
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

            prompt = ChatPromptTemplate.from_messages([
                ('system', draft_prompt()),
                (
                    'human',
                    'Case title: {case_title}\n'
                    'Patient context: {patient_context}\n'
                    'Clinical phenotype: {clinical_phenotype}\n'
                    'Variant summary: {variant_summary}\n'
                    'Deterministic recommendation: {recommendation}\n'
                    'Evidence lines: {evidence_lines}\n'
                    'Uncertainty: {uncertainty}\n'
                    'Next step: {next_step}\n'
                    'Confidence label: {confidence_label}\n'
                    'Evidence statuses: {evidence_statuses}\n'
                    'Warnings: {warnings}\n'
                    'Compose these into distinct report narrative sections only.',
                ),
                (
                    'human',
                    'Current deterministic base text:\n'
                    'AI clinical summary: {ai_clinical_summary}\n'
                    'Expanded evidence: {expanded_evidence}\n'
                    'Clinical integration: {clinical_integration}\n'
                    'Recommendations: {recommendations}\n'
                    'Limitations: {limitations}\n'
                    'Improve the writing quality while staying grounded in this material.',
                ),
            ])
            chain = prompt | model.with_structured_output(DraftPayload)
            result = chain.invoke(payload)
            if isinstance(result, DraftPayload):
                return result.model_dump(mode='json')
            return dict(result)

    return LiveDraftChain()


def build_embeddings_model(settings: Settings):
    if settings.llm_provider == 'mock' or not settings.openai_api_key:
        return None
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=settings.openai_embeddings_model,
        api_key=SecretStr(settings.openai_api_key),
    )


def build_run_chat_chain(settings: Settings):
    if settings.llm_provider == 'mock' or not settings.openai_api_key:
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

            prompt = ChatPromptTemplate.from_messages([
                ('system', current_run_chat_prompt()),
                (
                    'human',
                    'Question: {question}\n\n'
                    'Retrieved context:\n{retrieved_context}\n\n'
                    'Use only this material when answering.',
                ),
            ])
            chain = prompt | model.with_structured_output(RunChatAnswerDraft)
            result = chain.invoke(payload)
            if isinstance(result, RunChatAnswerDraft):
                return result.model_dump(mode='json')
            return dict(result)

    return LiveRunChatChain()
