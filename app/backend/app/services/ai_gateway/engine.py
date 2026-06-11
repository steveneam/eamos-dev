"""OpenAI-compatible broker for the Vercel AI Gateway.

Points the variant-chat LLM at https://ai-gateway.vercel.sh/v1 with provider
failover (order: [groq, bedrock] by default — Groq primary, Bedrock fallback,
both serving meta/llama-3.3-70b). Exposes `complete()` (non-streaming) and
`stream_chat()` (true token streaming). Captures the gateway's routing metadata
(final provider, generation id, cost) best-effort for observability.

Zero Data Retention is a gateway team-level setting, not a per-request body
flag, so it is configured in the Vercel dashboard rather than sent here.
See docs/ai-gateway/plan.md P1.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterator

import httpx

logger = logging.getLogger(__name__)

GATEWAY_BASE_URL = "https://ai-gateway.vercel.sh/v1"
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


@dataclass
class GatewayResult:
    """Outcome of a gateway call: the text plus best-effort routing metadata."""

    content: str = ""
    generation_id: str | None = None
    final_provider: str | None = None
    cost: str | None = None
    usage: dict[str, Any] | None = None

    def log_fields(self, model: str) -> dict[str, Any]:
        return {
            "model": model,
            "final_provider": self.final_provider,
            "generation_id": self.generation_id,
            "cost": self.cost,
        }


class GatewayError(RuntimeError):
    """Raised when the gateway cannot serve a request after retries."""


def _extract_metadata(payload: dict[str, Any], into: GatewayResult) -> None:
    """Best-effort capture of gateway routing metadata from a response body.

    The OpenAI-compatible REST response exposes `generationId` under
    `providerMetadata.gateway`, but the inference cost arrives in `usage.cost`
    (a.k.a. `usage.gateway_cost`) — confirmed by live smoke 2026-06-12, where
    `providerMetadata.gateway.cost`/`routing.finalProvider` are absent in the
    OpenAI-compatible shape (those are AI-SDK-only fields). `finalProvider` is
    therefore not available from the REST body; correlate via the generation id
    against the Generation Lookup API if the serving provider is needed. Absence
    is non-fatal — token delivery is the critical path; metadata is obs-lite.
    """
    gateway = (payload.get("providerMetadata") or {}).get("gateway") or {}
    routing = gateway.get("routing") or {}
    final_provider = routing.get("finalProvider") or routing.get("resolvedProvider")
    if final_provider:
        into.final_provider = final_provider
    generation_id = gateway.get("generationId") or payload.get("id")
    if generation_id:
        into.generation_id = generation_id
    usage = payload.get("usage")
    if usage:
        into.usage = usage
    if into.cost is None:
        cost = gateway.get("cost")
        if cost is None and usage:
            cost = usage.get("cost") or usage.get("gateway_cost")
        if cost is not None:
            into.cost = str(cost)


class AIGatewayEngine:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        provider_order: list[str],
        base_url: str = GATEWAY_BASE_URL,
        temperature: float = 0.3,
        max_tokens: int = 700,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        backoff_base_seconds: float = 0.5,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.model = model
        self.provider_order = list(provider_order)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self._sleep = sleep
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    # -- request shaping ---------------------------------------------------

    def _body(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool,
        temperature: float | None,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "providerOptions": {"gateway": {"order": self.provider_order}},
        }
        if stream:
            body["stream_options"] = {"include_usage": True}
        return body

    # -- non-streaming -----------------------------------------------------

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> GatewayResult:
        body = self._body(
            messages, stream=False, temperature=temperature, max_tokens=max_tokens
        )
        response = self._send_with_retry(body)
        try:
            data = response.json()
        finally:
            response.close()
        choices = data.get("choices") or [{}]
        content = (choices[0].get("message") or {}).get("content") or ""
        result = GatewayResult(content=content)
        _extract_metadata(data, result)
        return result

    # -- streaming ---------------------------------------------------------

    def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        meta: GatewayResult | None = None,
    ) -> Iterator[str]:
        """Yield text-content deltas as they arrive.

        Pass a fresh `GatewayResult` as `meta` (one per request) to receive the
        routing metadata captured from the final chunk; read it after the
        generator is exhausted. Per-request `meta` avoids cross-request races on
        the shared engine.
        """
        body = self._body(
            messages, stream=True, temperature=temperature, max_tokens=max_tokens
        )
        response = self._send_with_retry(body, stream=True)
        try:
            for line in response.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if meta is not None:
                    _extract_metadata(chunk, meta)
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                token = (choices[0].get("delta") or {}).get("content")
                if token:
                    yield token
        finally:
            response.close()

    # -- transport with retry ---------------------------------------------

    def _send_with_retry(
        self, body: dict[str, Any], *, stream: bool = False
    ) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                request = self._client.build_request(
                    "POST", "/chat/completions", json=body
                )
                response = self._client.send(request, stream=stream)
            except httpx.TransportError as exc:
                last_error = exc
                self._backoff(attempt)
                continue
            if response.status_code in _RETRYABLE_STATUS and attempt < self.max_retries - 1:
                retry_after = _retry_after_seconds(response)
                response.close()
                self._backoff(attempt, retry_after)
                continue
            if response.status_code >= 400:
                detail = _safe_error_detail(response, stream)
                response.close()
                raise GatewayError(
                    f"AI Gateway returned {response.status_code}: {detail}"
                )
            return response
        raise GatewayError(
            f"AI Gateway unreachable after {self.max_retries} attempts: {last_error}"
        )

    def _backoff(self, attempt: int, retry_after: float | None = None) -> None:
        delay = retry_after if retry_after is not None else self.backoff_base_seconds * (2**attempt)
        self._sleep(delay)


def _retry_after_seconds(response: httpx.Response) -> float | None:
    raw = response.headers.get("retry-after")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _safe_error_detail(response: httpx.Response, stream: bool) -> str:
    try:
        if stream:
            response.read()
        return response.text[:500]
    except Exception:  # pragma: no cover - defensive
        return "<unreadable error body>"
