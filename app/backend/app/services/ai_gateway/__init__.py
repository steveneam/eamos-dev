"""Vercel AI Gateway integration for Eamos chat.

Foundation for the AI-gateway build (docs/ai-gateway/plan.md): an OpenAI-compatible
broker (`engine.py`) that points the variant-chat LLM at the Vercel AI Gateway with
provider failover, plus the outbound evidence-only allowlist guard (`guard.py`).
"""

from app.services.ai_gateway.engine import (
    AIGatewayEngine,
    GatewayError,
    GatewayResult,
)
from app.services.ai_gateway.guard import (
    ALLOWED_CONTEXT_KEYS,
    EvidenceContextError,
    assert_evidence_only,
)

__all__ = [
    "AIGatewayEngine",
    "GatewayError",
    "GatewayResult",
    "ALLOWED_CONTEXT_KEYS",
    "EvidenceContextError",
    "assert_evidence_only",
]
