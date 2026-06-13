"""Structured-output extraction over the AI Gateway broker (validate + repair).

The reusable substrate for the gateway's structured features (messy-text→JSON,
NL→QuerySpec, paper→variants, report-narrative): prompt the model for a single
JSON object, parse + validate it against a Pydantic schema, and on failure send
one bounded "repair" turn quoting the error before giving up. The gateway broker
is OpenAI-compatible REST (no LangChain `with_structured_output`), so validation
is enforced here rather than by the provider. See docs/ai-gateway/plan.md §1.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_FENCE_OPEN = re.compile(r"^```[a-zA-Z0-9]*\n?")
_FENCE_CLOSE = re.compile(r"\n?```$")


class StructuredOutputError(RuntimeError):
    """Raised when the model cannot produce schema-valid JSON after repairs."""


def _coerce_json_object(text: str) -> tuple[dict[str, Any] | None, str | None]:
    """Best-effort extraction of one JSON object from a model response."""
    candidate = (text or "").strip()
    if candidate.startswith("```"):
        candidate = _FENCE_CLOSE.sub("", _FENCE_OPEN.sub("", candidate)).strip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None, "no JSON object found in response"
    try:
        obj = json.loads(candidate[start : end + 1])
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(obj, dict):
        return None, "JSON root is not an object"
    return obj, None


def _repair_instruction(error: str) -> str:
    return (
        f"Your previous response could not be used: {error}. "
        "Return ONLY a single valid JSON object with the required fields — "
        "no prose, no explanation, and no code fences."
    )


def extract_structured(
    engine: Any,
    *,
    system_prompt: str,
    user_content: str,
    schema: type[T],
    max_repairs: int = 1,
    temperature: float = 0.0,
) -> T:
    """Return a validated `schema` instance from a gateway completion.

    Parses the model's JSON, validates it against `schema`, and retries up to
    `max_repairs` times with the validation/parse error fed back. Raises
    `StructuredOutputError` if it never validates (callers treat that as a
    graceful "extraction unavailable", not a crash)."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    last_error = "no response"
    for attempt in range(max_repairs + 1):
        result = engine.complete(messages, temperature=temperature)
        parsed, error = _coerce_json_object(result.content)
        if error is None:
            try:
                return schema.model_validate(parsed)
            except ValidationError as exc:
                error = "; ".join(
                    f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
                    for err in exc.errors()[:5]
                )
        last_error = error
        if attempt < max_repairs:
            messages.append({"role": "assistant", "content": result.content})
            messages.append({"role": "user", "content": _repair_instruction(error)})

    raise StructuredOutputError(
        f"gateway structured output failed after {max_repairs + 1} attempt(s): {last_error}"
    )
