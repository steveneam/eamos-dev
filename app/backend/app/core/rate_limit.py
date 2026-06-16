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
RATE_LIMIT_EVIDENCE = "evidence"
RATE_LIMIT_LIBRARY = "library"
RATE_LIMIT_LOOKUP = "lookup"
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
