"""Outbound allowlist guard for the variant-chat gateway context.

`/report` is variant-centric (no patient), so the chat context built by
`ChatService._build_bounded_context` is inherently non-PHI. This guard is an
allowlist *assertion* on what leaves the server, not name/DOB/MRN stripping
(that belongs to the patient-report flow). It fails closed: if a non-allowlisted
top-level key, or a PHI/secret-looking token, reaches the serialized payload, we
refuse to send it to the gateway. See docs/ai-gateway/plan.md P2.
"""

from __future__ import annotations

import re

# The exact set of top-level keys ChatService._build_bounded_context emits.
# Adding a key to the bounded context means adding it here, deliberately.
ALLOWED_CONTEXT_KEYS = frozenset(
    {
        "variant_summary_rows",
        "call_cards",
        "population_frequency",
        "publications",
        "functional_evidence",
        "computational_predictors",
        "expert_panel",
        "workbench",
        "warnings",
    }
)

# Substrings that must never appear in the outbound payload. Patient-identifying
# fields from ReportPayload (patient_id / patient_context) and credential markers.
_FORBIDDEN_SUBSTRINGS = (
    "patient_id",
    "patient_context",
    "date_of_birth",
    '"mrn"',
)

# Credential-shaped tokens (API keys / bearer secrets).
_SECRET_PATTERNS = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{12,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}"),
    re.compile(r"\bvck_[A-Za-z0-9._\-]{12,}"),  # Vercel AI Gateway key prefix
)


class EvidenceContextError(RuntimeError):
    """Raised when the outbound chat context fails the evidence-only allowlist."""


def assert_evidence_only(context: dict, serialized: str) -> None:
    """Fail closed unless `context`/`serialized` is evidence-only.

    Args:
        context: the bounded-context dict before serialization.
        serialized: its JSON serialization (what would be sent to the gateway).
    """
    stray = set(context) - ALLOWED_CONTEXT_KEYS
    if stray:
        raise EvidenceContextError(
            f"Non-allowlisted key(s) in outbound chat context: {sorted(stray)}"
        )
    for needle in _FORBIDDEN_SUBSTRINGS:
        if needle in serialized:
            raise EvidenceContextError(
                f"PHI-shaped field reached outbound chat context: {needle!r}"
            )
    for pattern in _SECRET_PATTERNS:
        if pattern.search(serialized):
            raise EvidenceContextError(
                "Secret-shaped token reached outbound chat context"
            )
