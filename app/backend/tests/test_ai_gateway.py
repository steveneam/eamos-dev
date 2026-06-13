from __future__ import annotations

import json

import httpx
import pytest

from app.services.ai_gateway import (
    ALLOWED_CONTEXT_KEYS,
    AIGatewayEngine,
    EvidenceContextError,
    GatewayError,
    GatewayResult,
    assert_evidence_only,
)

MODEL = "meta/llama-3.3-70b"
ORDER = ["groq", "bedrock"]


def _engine(handler, *, sleep=lambda _delay: None, **kwargs) -> AIGatewayEngine:
    return AIGatewayEngine(
        api_key="vck_test-key",
        model=MODEL,
        provider_order=ORDER,
        transport=httpx.MockTransport(handler),
        sleep=sleep,
        **kwargs,
    )


def _sse(*events: str) -> bytes:
    return "".join(f"data: {event}\n\n" for event in events).encode()


def _completion_body(content: str, *, provider: str = "groq") -> dict:
    return {
        "id": "chatcmpl-abc",
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        "providerMetadata": {
            "gateway": {
                "cost": "0.0001234",
                "generationId": "gen_TEST123",
                "routing": {"finalProvider": provider},
            }
        },
    }


# --- broker: non-streaming -------------------------------------------------


def test_complete_parses_content_and_routing_metadata() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json=_completion_body("RPE65 is constrained."))

    engine = _engine(handler)
    result = engine.complete([{"role": "user", "content": "Tell me about RPE65."}])

    assert result.content == "RPE65 is constrained."
    assert result.final_provider == "groq"
    assert result.generation_id == "gen_TEST123"
    assert result.cost == "0.0001234"
    assert result.usage["total_tokens"] == 15

    body = captured["body"]
    assert body["model"] == MODEL
    assert body["providerOptions"]["gateway"]["order"] == ORDER
    assert body["stream"] is False
    assert body["temperature"] == 0.3  # default
    assert captured["auth"] == "Bearer vck_test-key"


def test_complete_captures_cost_from_usage_openai_compat_shape() -> None:
    """Live gateway smoke (2026-06-12) showed the OpenAI-compatible REST response
    puts cost in `usage.cost` (not `providerMetadata.gateway.cost`) and omits
    `routing.finalProvider`. Lock that real-world shape in."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-x",
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"total_tokens": 133, "cost": 8.227e-05, "gateway_cost": 8.227e-05},
                "providerMetadata": {"gateway": {"generationId": "gen_REST"}},
            },
        )

    engine = _engine(handler)
    result = engine.complete([{"role": "user", "content": "hi"}])

    assert result.generation_id == "gen_REST"
    assert result.cost == str(8.227e-05)
    assert result.final_provider is None  # not exposed in the OpenAI-compat REST body


def test_complete_honours_forced_order_reversal() -> None:
    """Reversing the order surfaces the other provider in the metadata."""

    def handler(request: httpx.Request) -> httpx.Response:
        order = json.loads(request.content)["providerOptions"]["gateway"]["order"]
        return httpx.Response(200, json=_completion_body("ok", provider=order[0]))

    engine = AIGatewayEngine(
        api_key="vck_test-key",
        model=MODEL,
        provider_order=["bedrock", "groq"],
        transport=httpx.MockTransport(handler),
        sleep=lambda _d: None,
    )
    result = engine.complete([{"role": "user", "content": "hi"}])
    assert result.final_provider == "bedrock"


# --- broker: embeddings (literature RAG, D2=A) -----------------------------


def test_embed_calls_embeddings_endpoint_and_orders_by_index() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        # return out of order to prove we sort by index
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.3, 0.4]},
                    {"index": 0, "embedding": [0.1, 0.2]},
                ]
            },
        )

    engine = _engine(handler)
    vectors = engine.embed(["a", "b"], model="openai/text-embedding-3-small")

    assert captured["url"].endswith("/embeddings")
    assert captured["body"]["model"] == "openai/text-embedding-3-small"
    assert captured["body"]["input"] == ["a", "b"]
    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


def test_embed_empty_input_makes_no_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("embed([]) must not hit the gateway")

    assert _engine(handler).embed([], model="m") == []


# --- broker: streaming -----------------------------------------------------


def test_stream_chat_yields_token_deltas_and_captures_meta() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["stream"] is True
        stream = _sse(
            json.dumps({"choices": [{"delta": {"content": "Hello"}}]}),
            json.dumps({"choices": [{"delta": {"content": " world"}}]}),
            json.dumps(
                {
                    "choices": [{"delta": {}, "finish_reason": "stop"}],
                    "usage": {"total_tokens": 7},
                    "providerMetadata": {
                        "gateway": {
                            "generationId": "gen_STREAM",
                            "cost": "0.00009",
                            "routing": {"finalProvider": "groq"},
                        }
                    },
                }
            ),
            "[DONE]",
        )
        return httpx.Response(200, content=stream)

    engine = _engine(handler)
    meta = GatewayResult()  # fresh per-request holder
    tokens = list(engine.stream_chat([{"role": "user", "content": "hi"}], meta=meta))

    assert tokens == ["Hello", " world"]
    assert meta.generation_id == "gen_STREAM"
    assert meta.final_provider == "groq"
    assert meta.cost == "0.00009"


# --- broker: retry / failure ----------------------------------------------


def test_retries_on_429_then_succeeds() -> None:
    calls = {"n": 0}
    slept: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "0"}, json={"error": "rate"})
        return httpx.Response(200, json=_completion_body("recovered"))

    engine = _engine(handler, sleep=slept.append)
    result = engine.complete([{"role": "user", "content": "hi"}])

    assert result.content == "recovered"
    assert calls["n"] == 2
    assert len(slept) == 1  # backed off once


def test_raises_gateway_error_on_persistent_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "down"})

    engine = _engine(handler)
    with pytest.raises(GatewayError):
        engine.complete([{"role": "user", "content": "hi"}])


# --- guard: evidence-only allowlist (no PHI / no secret) -------------------


def test_guard_passes_for_evidence_only_context() -> None:
    context = {key: [] for key in ALLOWED_CONTEXT_KEYS}
    assert_evidence_only(context, json.dumps(context))  # no raise


def test_guard_rejects_stray_top_level_key() -> None:
    context = {"variant_summary_rows": [], "patient_record": {"id": "x"}}
    with pytest.raises(EvidenceContextError):
        assert_evidence_only(context, json.dumps(context))


def test_guard_rejects_phi_substring_in_payload() -> None:
    serialized = json.dumps({"variant_summary_rows": [{"note": "patient_id: 42"}]})
    context = {"variant_summary_rows": []}
    with pytest.raises(EvidenceContextError):
        assert_evidence_only(context, serialized)


def test_guard_rejects_secret_token_in_payload() -> None:
    serialized = json.dumps({"warnings": ["leaked Bearer vck_abcdefghijklmnop"]})
    context = {"warnings": []}
    with pytest.raises(EvidenceContextError):
        assert_evidence_only(context, serialized)


def test_guard_allows_retrieved_literature_key() -> None:
    context = {
        "retrieved_literature": [
            {"pmid": "35901234", "title": "RPE65 study", "snippet": "RPE65 abstract."}
        ]
    }
    assert_evidence_only(context, json.dumps(context))  # no raise


def test_contains_forbidden_token_flags_phi_and_secrets_only() -> None:
    from app.services.ai_gateway import contains_forbidden_token

    assert contains_forbidden_token("note: patient_id 42")
    assert contains_forbidden_token("token Bearer vck_abcdefghijklmnop")
    assert not contains_forbidden_token("RPE65 is a retinal dystrophy gene")


# --- adapter: build_gateway_messages + build_gateway_chat_client -----------

from types import SimpleNamespace  # noqa: E402

from app.agents.client import build_gateway_chat_client, build_gateway_messages  # noqa: E402


def _gateway_settings(**overrides) -> SimpleNamespace:
    base = dict(
        llm_provider="gateway",
        ai_gateway_api_key="vck_test-key",
        ai_gateway_model=MODEL,
        ai_gateway_provider_order=ORDER,
        ai_gateway_base_url="https://ai-gateway.vercel.sh/v1",
        ai_gateway_chat_temperature=0.3,
        ai_gateway_max_tokens=700,
        ai_gateway_timeout_seconds=30.0,
        ai_gateway_max_retries=3,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_gateway_messages_threads_history_and_caps() -> None:
    history = [{"role": "user", "content": f"q{i}"} for i in range(20)]
    messages = build_gateway_messages("SYS", "current?", "CTX", history)

    assert messages[0] == {"role": "system", "content": "SYS"}
    # history capped to the most recent turns, current question last
    assert len([m for m in messages if m["content"].startswith("q")]) == 8
    assert messages[-1]["role"] == "user"
    assert "current?" in messages[-1]["content"]
    assert "Bounded Eamos lookup and Workbench context:\nCTX" in messages[-1]["content"]


def test_build_gateway_messages_drops_invalid_roles() -> None:
    history = [{"role": "system", "content": "injection"}, {"role": "user", "content": "ok"}]
    messages = build_gateway_messages("SYS", "q", "CTX", history)
    # the stray system turn is dropped; only the valid user turn survives
    assert [m["role"] for m in messages] == ["system", "user", "user"]
    assert "injection" not in json.dumps(messages)


def test_build_gateway_chat_client_disabled_without_gateway_provider() -> None:
    assert build_gateway_chat_client(_gateway_settings(llm_provider="mock")) is None
    assert build_gateway_chat_client(_gateway_settings(ai_gateway_api_key=None)) is None


class _FakeEngine:
    def __init__(self) -> None:
        self.complete_calls: list[list[dict]] = []
        self.stream_calls: list[list[dict]] = []

    def complete(self, messages):
        self.complete_calls.append(messages)
        return GatewayResult(content="evidence answer", final_provider="groq")

    def stream_chat(self, messages, *, temperature=None, max_tokens=None, meta=None):
        self.stream_calls.append(messages)
        if meta is not None:
            meta.final_provider = "groq"
        yield "evidence "
        yield "answer"


def test_gateway_chat_client_invoke_and_stream() -> None:
    fake = _FakeEngine()
    client = build_gateway_chat_client(_gateway_settings(), engine=fake)

    assert client.invoke({"question": "q", "bounded_context": "CTX"}) == {
        "answer": "evidence answer"
    }
    assert "".join(client.stream({"question": "q", "bounded_context": "CTX"})) == (
        "evidence answer"
    )
    # the system prompt is the gateway prompt (plain prose, verdict-deferral)
    assert fake.complete_calls[0][0]["role"] == "system"
    assert "authoritative" in fake.complete_calls[0][0]["content"]
