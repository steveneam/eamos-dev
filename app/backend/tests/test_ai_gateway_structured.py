from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.agents.client import (
    build_gateway_search_input_chain,
    build_search_input_ai_chain,
)
from app.schemas.lookup import SearchInputAiExtraction
from app.services.ai_gateway import GatewayResult
from app.services.ai_gateway.structured import (
    StructuredOutputError,
    extract_structured,
)

MODEL = "meta/llama-3.3-70b"
ORDER = ["groq", "bedrock"]


class ScriptedEngine:
    """Returns queued completion contents in order; records each call."""

    def __init__(self, *contents: str) -> None:
        self.contents = list(contents)
        self.calls: list[list[dict]] = []

    def complete(self, messages, *, temperature=None, max_tokens=None) -> GatewayResult:
        self.calls.append(messages)
        return GatewayResult(content=self.contents[len(self.calls) - 1])


class _Need(BaseModel):
    gene: str


# --- extract_structured: parse + validate + repair -------------------------


def test_extract_structured_succeeds_first_try() -> None:
    engine = ScriptedEngine('{"gene": "RPE65", "confidence": "high"}')
    out = extract_structured(
        engine, system_prompt="SYS", user_content="text", schema=SearchInputAiExtraction
    )
    assert out.gene == "RPE65"
    assert out.confidence == "high"
    assert len(engine.calls) == 1


def test_extract_structured_strips_code_fences() -> None:
    engine = ScriptedEngine('```json\n{"gene": "ABCA4"}\n```')
    out = extract_structured(
        engine, system_prompt="SYS", user_content="t", schema=SearchInputAiExtraction
    )
    assert out.gene == "ABCA4"


def test_extract_structured_ignores_prose_around_object() -> None:
    engine = ScriptedEngine('Here you go: {"gene": "USH2A"} — hope that helps!')
    out = extract_structured(
        engine, system_prompt="SYS", user_content="t", schema=SearchInputAiExtraction
    )
    assert out.gene == "USH2A"


def test_extract_structured_repairs_after_unparseable_json() -> None:
    engine = ScriptedEngine("not json at all", '{"gene": "RPE65"}')
    out = extract_structured(
        engine, system_prompt="SYS", user_content="t", schema=SearchInputAiExtraction
    )
    assert out.gene == "RPE65"
    assert len(engine.calls) == 2
    # the repair turn quotes the failure and re-asks for JSON
    repair_turn = engine.calls[1][-1]
    assert repair_turn["role"] == "user"
    assert "JSON" in repair_turn["content"]


def test_extract_structured_repairs_after_validation_error() -> None:
    engine = ScriptedEngine('{"not_gene": 1}', '{"gene": "RPE65"}')
    out = extract_structured(engine, system_prompt="SYS", user_content="t", schema=_Need)
    assert out.gene == "RPE65"
    assert len(engine.calls) == 2


def test_extract_structured_raises_after_repairs_exhausted() -> None:
    engine = ScriptedEngine("nope", "still bad")
    with pytest.raises(StructuredOutputError):
        extract_structured(
            engine, system_prompt="SYS", user_content="t", schema=_Need, max_repairs=1
        )
    assert len(engine.calls) == 2


# --- gateway search-input chain wiring -------------------------------------


def _settings(**overrides) -> SimpleNamespace:
    base = dict(
        llm_provider="gateway",
        search_input_ai_enabled=True,
        ai_gateway_api_key="vck_test-key",
        ai_gateway_model=MODEL,
        ai_gateway_provider_order=ORDER,
        ai_gateway_base_url="https://ai-gateway.vercel.sh/v1",
        ai_gateway_max_tokens=700,
        ai_gateway_max_retries=3,
        search_input_ai_timeout_seconds=8.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_gateway_search_input_chain_returns_validated_dict() -> None:
    engine = ScriptedEngine('{"gene": "RPE65", "cdna": "c.260A>G", "confidence": "high"}')
    chain = build_gateway_search_input_chain(_settings(), engine=engine)

    result = chain.invoke({"search_text": "RPE65 c.260A>G", "reference_context": "{}"})

    assert result["gene"] == "RPE65"
    assert result["cdna"] == "c.260A>G"
    # output round-trips through the real schema
    assert SearchInputAiExtraction.model_validate(result).gene == "RPE65"
    # the submitted text reached the user message
    assert "RPE65 c.260A>G" in engine.calls[0][1]["content"]


def test_gateway_search_input_chain_disabled_without_gateway() -> None:
    assert build_gateway_search_input_chain(_settings(llm_provider="mock")) is None
    assert build_gateway_search_input_chain(_settings(ai_gateway_api_key=None)) is None


def test_build_search_input_ai_chain_routes_to_gateway() -> None:
    chain = build_search_input_ai_chain(_settings())
    assert chain is not None
    assert type(chain).__name__ == "GatewaySearchInputChain"


def test_build_search_input_ai_chain_none_when_feature_disabled() -> None:
    assert build_search_input_ai_chain(_settings(search_input_ai_enabled=False)) is None
