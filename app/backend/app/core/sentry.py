"""Sentry error/performance monitoring for the FastAPI backend.

Env-gated: with no ``SENTRY_DSN`` set, :func:`init_sentry` is a no-op and
nothing is sent. Mirrors the frontend posture (``app/web/lib/sentry.shared.ts``)
— the queried variant (``?q=GENE:c.cdna``) and other query-string / PII data are
scrubbed before any event leaves the process.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger("eamos.sentry")


def _strip_query(url: str) -> str:
    """Drop the query + fragment from a URL, keeping scheme/host/path."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _scrub_event(event: dict[str, Any], _hint: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Strip query strings (incl. the queried variant) from outgoing events."""
    request = event.get("request")
    if isinstance(request, dict):
        url = request.get("url")
        if isinstance(url, str):
            request["url"] = _strip_query(url)
        request.pop("query_string", None)
    transaction = event.get("transaction")
    if isinstance(transaction, str) and "?" in transaction:
        event["transaction"] = transaction.split("?", 1)[0]
    return event


def init_sentry() -> bool:
    """Initialise Sentry when ``SENTRY_DSN`` is set. Returns True when enabled."""
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return False
    try:
        import sentry_sdk
    except ImportError:
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed; skipping init")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        # Never attach cookies/headers/client IP or other default PII.
        send_default_pii=False,
        before_send=_scrub_event,
    )
    return True
