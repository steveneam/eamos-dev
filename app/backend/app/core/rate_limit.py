from __future__ import annotations

import hashlib
import math
import time
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Iterable

from fastapi import HTTPException, Request, status

RATE_LIMIT_AUTH = "auth"
RATE_LIMIT_BATCH_UPLOAD = "batch_upload"
RATE_LIMIT_CHAT = "chat"
RATE_LIMIT_CHAT_DEV_DAILY = "chat_dev_daily"
RATE_LIMIT_CHAT_USER_DAILY = "chat_user_daily"
RATE_LIMIT_EVIDENCE = "evidence"
RATE_LIMIT_LIBRARY = "library"
RATE_LIMIT_LOOKUP = "lookup"
RATE_LIMIT_MATERIALIZATION_ADMIN = "materialization_admin"
RATE_LIMIT_PAYMENTS_CHECKOUT = "payments_checkout"
RATE_LIMIT_PAYMENTS_WEBHOOK = "payments_webhook"
RATE_LIMIT_WORKBENCH = "workbench"

_MAX_REQUESTS_BY_SCOPE = {
    RATE_LIMIT_AUTH: "rate_limit_auth_max_requests",
    RATE_LIMIT_BATCH_UPLOAD: "rate_limit_batch_upload_max_requests",
    RATE_LIMIT_CHAT: "rate_limit_chat_max_requests",
    RATE_LIMIT_EVIDENCE: "rate_limit_evidence_max_requests",
    RATE_LIMIT_LIBRARY: "rate_limit_library_max_requests",
    RATE_LIMIT_LOOKUP: "rate_limit_lookup_max_requests",
    RATE_LIMIT_MATERIALIZATION_ADMIN: "rate_limit_materialization_admin_max_requests",
    RATE_LIMIT_PAYMENTS_CHECKOUT: "rate_limit_payments_checkout_max_requests",
    RATE_LIMIT_PAYMENTS_WEBHOOK: "rate_limit_payments_webhook_max_requests",
    RATE_LIMIT_WORKBENCH: "rate_limit_workbench_max_requests",
}


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: float = 0.0


class InMemoryRateLimiter:
    """Small first-launch limiter for single-instance deployments."""

    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(
        self,
        keys: Iterable[str],
        *,
        max_requests: int,
        window_seconds: int,
    ) -> RateLimitResult:
        now = time.monotonic()
        normalized_keys = tuple(dict.fromkeys(keys))
        if not normalized_keys:
            return RateLimitResult(allowed=True)

        with self._lock:
            retry_after = 0.0
            for key in normalized_keys:
                bucket = self._buckets.setdefault(key, deque())
                _prune_bucket(bucket, now=now, window_seconds=window_seconds)
                if len(bucket) >= max_requests:
                    retry_after = max(
                        retry_after,
                        window_seconds - (now - bucket[0]),
                    )

            if retry_after > 0:
                return RateLimitResult(
                    allowed=False,
                    retry_after_seconds=max(1.0, retry_after),
                )

            for key in normalized_keys:
                self._buckets[key].append(now)
            return RateLimitResult(allowed=True)


def enforce_rate_limit(
    request: Request,
    scope: str,
    *,
    subject: str | None = None,
) -> None:
    settings = request.app.state.settings
    if not getattr(settings, "rate_limit_enabled", True):
        return

    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        limiter = InMemoryRateLimiter()
        request.app.state.rate_limiter = limiter

    max_requests = _scope_max_requests(settings, scope)
    window_seconds = max(1, int(getattr(settings, "rate_limit_window_seconds", 60)))
    result = limiter.check(
        _rate_limit_keys(request, scope=scope, subject=subject),
        max_requests=max_requests,
        window_seconds=window_seconds,
    )
    if result.allowed:
        return

    retry_after = str(max(1, math.ceil(result.retry_after_seconds)))
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests.",
        headers={"Retry-After": retry_after},
    )


def enforce_chat_dev_daily_cap(request: Request) -> None:
    """Global (cross-user) daily spend backstop for the gateway chat path.

    A blunt guard that caps TOTAL chat requests in a rolling window so the AI
    Gateway credit cannot be drained while developing against the real gateway or
    running the gated shared-Render demo. No-op unless
    ``ai_chat_dev_daily_cap_enabled`` (default False), so free local fake-gateway
    iteration stays unlimited. Reuses the shared in-memory limiter with a single
    global key and the configured window — independent of the per-user
    ``RATE_LIMIT_CHAT`` limit (both apply) and of the launch per-user/tier budget
    (docs/ai-gateway/pre-launch-security.md), which is separate and still pending.
    """
    settings = request.app.state.settings
    if not getattr(settings, "ai_chat_dev_daily_cap_enabled", False):
        return

    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        limiter = InMemoryRateLimiter()
        request.app.state.rate_limiter = limiter

    max_requests = max(1, int(getattr(settings, "ai_chat_dev_daily_cap", 1)))
    window_seconds = max(1, int(getattr(settings, "ai_chat_dev_daily_cap_window_seconds", 86_400)))
    result = limiter.check(
        [f"{RATE_LIMIT_CHAT_DEV_DAILY}:global"],
        max_requests=max_requests,
        window_seconds=window_seconds,
    )
    if result.allowed:
        return

    retry_after = str(max(1, math.ceil(result.retry_after_seconds)))
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=(
            "Ask-Eamos daily development cap reached. This is a temporary spend "
            "guardrail while the AI gateway is in development — please try again later."
        ),
        headers={"Retry-After": retry_after},
    )


def enforce_chat_user_daily_cap(request: Request, *, subject: str) -> None:
    """Per-user daily request budget for the gateway chat path (launch gate).

    The launch HIGH item from docs/ai-gateway/pre-launch-security.md: caps how many
    chat requests a single authenticated user may make per rolling window so one
    account cannot drain the gateway credit. Keyed on the authenticated ``subject``
    (user id) — independent of the per-user burst ``RATE_LIMIT_CHAT`` limit and the
    GLOBAL ``enforce_chat_dev_daily_cap`` backstop (all apply when enabled). No-op
    unless ``ai_chat_user_daily_cap_enabled`` (default False); flat across users for
    first launch. Reuses the shared in-memory limiter with the configured window.
    """
    settings = request.app.state.settings
    if not getattr(settings, "ai_chat_user_daily_cap_enabled", False):
        return

    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        limiter = InMemoryRateLimiter()
        request.app.state.rate_limiter = limiter

    max_requests = max(1, int(getattr(settings, "ai_chat_user_daily_cap", 50)))
    window_seconds = max(1, int(getattr(settings, "ai_chat_user_daily_cap_window_seconds", 86_400)))
    result = limiter.check(
        [f"{RATE_LIMIT_CHAT_USER_DAILY}:subject:{_digest(subject.strip().lower())}"],
        max_requests=max_requests,
        window_seconds=window_seconds,
    )
    if result.allowed:
        return

    retry_after = str(max(1, math.ceil(result.retry_after_seconds)))
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Ask-Eamos daily limit reached for your account. Please try again tomorrow.",
        headers={"Retry-After": retry_after},
    )


def _scope_max_requests(settings, scope: str) -> int:
    attr = _MAX_REQUESTS_BY_SCOPE.get(scope, "rate_limit_default_max_requests")
    value = getattr(settings, attr, getattr(settings, "rate_limit_default_max_requests", 60))
    return max(1, int(value))


def _rate_limit_keys(
    request: Request,
    *,
    scope: str,
    subject: str | None,
) -> list[str]:
    keys = [f"{scope}:ip:{_digest(_client_identifier(request))}"]
    if subject:
        keys.append(f"{scope}:subject:{_digest(subject.strip().lower())}")
    return keys


def _client_identifier(request: Request) -> str:
    settings = request.app.state.settings
    if getattr(settings, "rate_limit_trust_proxy_headers", True):
        for header_name in ("cf-connecting-ip", "x-real-ip", "x-forwarded-for"):
            header_value = request.headers.get(header_name)
            if header_value:
                candidate = header_value.split(",", 1)[0].strip()
                if candidate:
                    return candidate
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def _prune_bucket(bucket: deque[float], *, now: float, window_seconds: int) -> None:
    while bucket and now - bucket[0] >= window_seconds:
        bucket.popleft()
