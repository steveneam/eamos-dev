from __future__ import annotations

import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient

from app.core.rate_limit import InMemoryRateLimiter
from app.schemas.chat import ChatResponse, RunChatResponse


def _set_limit(client: TestClient, scope: str, max_requests: int = 1) -> None:
    setattr(client.app.state.settings, f"rate_limit_{scope}_max_requests", max_requests)
    client.app.state.settings.rate_limit_window_seconds = 60


def _evidence_payload() -> dict:
    return {"variant_hgvs": "NM_000492.4:c.199C>T", "submitted_pmid": "35901234"}


def _stripe_signature(payload: bytes, secret: str) -> str:
    timestamp = int(time.time())
    signed = f"{timestamp}.".encode("utf-8") + payload
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


class FakeChatService:
    def respond(self, _payload):
        return ChatResponse(answer="Mock answer.")

    def respond_stream(self, _payload):
        yield "Mock answer."


class FakeRunChatService:
    def answer(self, _run_id, payload, *, owner):
        return RunChatResponse(question=payload.question, answer="Mock run answer.")

    def stream(self, _run_id, _payload, *, owner):
        yield "Mock run answer."


def test_auth_register_is_rate_limited_per_ip(client: TestClient) -> None:
    _set_limit(client, "auth")

    first = client.post(
        "/api/v1/auth/register",
        json={"username": "rate-limit-1", "password": "Testpass123!"},
    )
    second = client.post(
        "/api/v1/auth/register",
        json={"username": "rate-limit-2", "password": "Testpass123!"},
    )

    assert first.status_code == 201
    assert second.status_code == 429
    assert second.headers["Retry-After"]


def test_lookup_parse_rate_limit_keeps_ips_independent(client: TestClient) -> None:
    _set_limit(client, "lookup")
    client.app.state.settings.rate_limit_trust_proxy_headers = True

    first = client.post(
        "/api/v1/lookup/parse",
        json={"search_text": "rs61752871"},
        headers={"X-Forwarded-For": "203.0.113.10"},
    )
    second_same_ip = client.post(
        "/api/v1/lookup/parse",
        json={"search_text": "rs1801133"},
        headers={"X-Forwarded-For": "203.0.113.10"},
    )
    third_new_ip = client.post(
        "/api/v1/lookup/parse",
        json={"search_text": "rs1801133"},
        headers={"X-Forwarded-For": "203.0.113.11"},
    )

    assert first.status_code == 200
    assert second_same_ip.status_code == 429
    assert third_new_ip.status_code == 200


def test_rate_limit_ignores_proxy_headers_by_default(client: TestClient) -> None:
    _set_limit(client, "lookup")

    first = client.post(
        "/api/v1/lookup/parse",
        json={"search_text": "rs61752871"},
        headers={"X-Forwarded-For": "203.0.113.30"},
    )
    second_spoofed_ip = client.post(
        "/api/v1/lookup/parse",
        json={"search_text": "rs1801133"},
        headers={"X-Forwarded-For": "203.0.113.31"},
    )

    assert first.status_code == 200
    assert second_spoofed_ip.status_code == 429


def _chat_payload() -> dict:
    return {
        "question": "What does this variant mean?",
        "variant_context": {
            "patient_id": "rate-limit-chat",
            "variant_summary_rows": [{"gene": "RPE65"}],
        },
    }


def test_chat_endpoint_requires_authentication(client: TestClient) -> None:
    client.app.state.chat_service = FakeChatService()

    assert client.post("/api/v1/chat", json=_chat_payload()).status_code == 401
    assert client.post("/api/v1/chat/stream", json=_chat_payload()).status_code == 401


def test_chat_endpoint_is_rate_limited(auth_client: TestClient) -> None:
    _set_limit(auth_client, "chat")
    auth_client.app.state.chat_service = FakeChatService()

    first = auth_client.post("/api/v1/chat", json=_chat_payload())
    second = auth_client.post("/api/v1/chat", json=_chat_payload())

    assert first.status_code == 200
    assert second.status_code == 429


def test_chat_is_rate_limited_per_user_across_ips(auth_client: TestClient) -> None:
    _set_limit(auth_client, "chat")
    auth_client.app.state.settings.rate_limit_trust_proxy_headers = True
    auth_client.app.state.chat_service = FakeChatService()

    first = auth_client.post(
        "/api/v1/chat",
        json=_chat_payload(),
        headers={"X-Forwarded-For": "203.0.113.40"},
    )
    second = auth_client.post(
        "/api/v1/chat",
        json=_chat_payload(),
        headers={"X-Forwarded-For": "203.0.113.41"},
    )

    assert first.status_code == 200
    assert second.status_code == 429


def _enable_dev_cap(client: TestClient, cap: int = 1) -> None:
    # Isolate the GLOBAL dev spend-cap from the per-user chat limit: make the
    # per-user limit generous so only the dev cap can trip the 429.
    client.app.state.rate_limiter = InMemoryRateLimiter()
    client.app.state.settings.rate_limit_chat_max_requests = 100
    client.app.state.settings.rate_limit_window_seconds = 60
    client.app.state.settings.ai_chat_dev_daily_cap_enabled = True
    client.app.state.settings.ai_chat_dev_daily_cap = cap
    client.app.state.settings.ai_chat_dev_daily_cap_window_seconds = 86_400


def test_chat_dev_daily_cap_blocks_after_global_limit(auth_client: TestClient) -> None:
    _enable_dev_cap(auth_client, cap=1)
    auth_client.app.state.chat_service = FakeChatService()

    first = auth_client.post("/api/v1/chat", json=_chat_payload())
    second = auth_client.post("/api/v1/chat", json=_chat_payload())

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["Retry-After"]


def test_chat_stream_dev_daily_cap_blocks_after_global_limit(auth_client: TestClient) -> None:
    _enable_dev_cap(auth_client, cap=1)
    auth_client.app.state.chat_service = FakeChatService()

    first = auth_client.post("/api/v1/chat/stream", json=_chat_payload())
    second = auth_client.post("/api/v1/chat/stream", json=_chat_payload())

    assert first.status_code == 200
    assert second.status_code == 429


def test_chat_dev_daily_cap_off_by_default(auth_client: TestClient) -> None:
    auth_client.app.state.rate_limiter = InMemoryRateLimiter()
    auth_client.app.state.settings.rate_limit_chat_max_requests = 100
    auth_client.app.state.settings.rate_limit_window_seconds = 60
    auth_client.app.state.settings.ai_chat_dev_daily_cap_enabled = False
    auth_client.app.state.chat_service = FakeChatService()

    statuses = [
        auth_client.post("/api/v1/chat", json=_chat_payload()).status_code for _ in range(3)
    ]

    assert statuses == [200, 200, 200]


def _enable_user_cap(client: TestClient, cap: int = 1) -> None:
    # Isolate the per-USER daily budget from the per-user burst limit and the
    # global dev cap: make the burst limit generous and leave the dev cap off so
    # only the per-user daily budget can trip the 429.
    client.app.state.rate_limiter = InMemoryRateLimiter()
    client.app.state.settings.rate_limit_chat_max_requests = 100
    client.app.state.settings.rate_limit_window_seconds = 60
    client.app.state.settings.ai_chat_dev_daily_cap_enabled = False
    client.app.state.settings.ai_chat_user_daily_cap_enabled = True
    client.app.state.settings.ai_chat_user_daily_cap = cap
    client.app.state.settings.ai_chat_user_daily_cap_window_seconds = 86_400


def test_chat_user_daily_cap_blocks_after_user_limit(auth_client: TestClient) -> None:
    _enable_user_cap(auth_client, cap=1)
    auth_client.app.state.chat_service = FakeChatService()

    first = auth_client.post("/api/v1/chat", json=_chat_payload())
    second = auth_client.post("/api/v1/chat", json=_chat_payload())

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["Retry-After"]


def test_chat_stream_user_daily_cap_blocks_after_user_limit(auth_client: TestClient) -> None:
    _enable_user_cap(auth_client, cap=1)
    auth_client.app.state.chat_service = FakeChatService()

    first = auth_client.post("/api/v1/chat/stream", json=_chat_payload())
    second = auth_client.post("/api/v1/chat/stream", json=_chat_payload())

    assert first.status_code == 200
    assert second.status_code == 429


def test_chat_user_daily_cap_off_by_default(auth_client: TestClient) -> None:
    auth_client.app.state.rate_limiter = InMemoryRateLimiter()
    auth_client.app.state.settings.rate_limit_chat_max_requests = 100
    auth_client.app.state.settings.rate_limit_window_seconds = 60
    auth_client.app.state.settings.ai_chat_user_daily_cap_enabled = False
    auth_client.app.state.chat_service = FakeChatService()

    statuses = [
        auth_client.post("/api/v1/chat", json=_chat_payload()).status_code for _ in range(3)
    ]

    assert statuses == [200, 200, 200]


def test_chat_user_daily_cap_is_per_user(auth_client: TestClient) -> None:
    # The default auth_client user is capped at 1; a second registered user gets
    # an independent budget (flat-per-user, keyed on the authenticated subject).
    _enable_user_cap(auth_client, cap=1)
    auth_client.app.state.chat_service = FakeChatService()

    other = auth_client.post(
        "/api/v1/auth/register",
        json={"username": "user-cap-other", "password": "test-password"},
    )
    assert other.status_code == 201
    other_auth = {"Authorization": f"Bearer {other.json()['access_token']}"}

    first_user_first = auth_client.post("/api/v1/chat", json=_chat_payload())
    first_user_second = auth_client.post("/api/v1/chat", json=_chat_payload())
    other_user_first = auth_client.post("/api/v1/chat", json=_chat_payload(), headers=other_auth)

    assert first_user_first.status_code == 200
    assert first_user_second.status_code == 429
    assert other_user_first.status_code == 200


def test_run_chat_endpoint_uses_chat_rate_limit(auth_client: TestClient) -> None:
    _set_limit(auth_client, "chat")
    auth_client.app.state.run_chat_service = FakeRunChatService()

    first = auth_client.post("/api/v1/runs/run_rate/chat", json={"question": "What changed?"})
    second = auth_client.post("/api/v1/runs/run_rate/chat", json={"question": "What changed?"})

    assert first.status_code == 200
    assert second.status_code == 429


def test_run_chat_stream_endpoint_uses_chat_rate_limit(auth_client: TestClient) -> None:
    _set_limit(auth_client, "chat")
    auth_client.app.state.rate_limiter = InMemoryRateLimiter()
    auth_client.app.state.run_chat_service = FakeRunChatService()

    first = auth_client.post(
        "/api/v1/runs/run_rate/chat/stream",
        json={"question": "What changed?"},
    )
    second = auth_client.post(
        "/api/v1/runs/run_rate/chat/stream",
        json={"question": "What changed?"},
    )

    assert first.status_code == 200
    assert second.status_code == 429


def test_paper_variants_extract_uses_chat_user_rate_limit(auth_client: TestClient) -> None:
    _set_limit(auth_client, "chat")

    first = auth_client.post(
        "/api/v1/paper-variants/extract",
        json={"text": "RPE65 c.260A>G was identified in a patient."},
    )
    second = auth_client.post(
        "/api/v1/paper-variants/extract",
        json={"text": "RPE65 c.260A>G was identified in a patient."},
    )

    assert first.status_code == 200
    assert second.status_code == 429


def test_evidence_submission_is_rate_limited_per_user_across_ips(
    auth_client: TestClient,
) -> None:
    _set_limit(auth_client, "evidence")

    first = auth_client.post(
        "/api/v1/evidence-submissions",
        json=_evidence_payload(),
        headers={"X-Forwarded-For": "203.0.113.20"},
    )
    second = auth_client.post(
        "/api/v1/evidence-submissions",
        json=_evidence_payload(),
        headers={"X-Forwarded-For": "203.0.113.21"},
    )

    assert first.status_code == 201
    assert second.status_code == 429


def test_payment_checkout_is_rate_limited_per_user(auth_client: TestClient) -> None:
    _set_limit(auth_client, "payments_checkout")

    first = auth_client.post("/api/v1/payments/checkout-session", json={"plan_key": "max"})
    second = auth_client.post("/api/v1/payments/checkout-session", json={"plan_key": "max"})

    assert first.status_code == 200
    assert second.status_code == 429


def test_stripe_webhook_is_rate_limited(client: TestClient) -> None:
    _set_limit(client, "payments_webhook")
    secret = "whsec_test"
    client.app.state.settings.stripe_webhook_secret = secret
    event = {"id": "evt_ignored", "type": "ping", "data": {"object": {}}}
    body = json.dumps(event, separators=(",", ":")).encode("utf-8")
    headers = {"Stripe-Signature": _stripe_signature(body, secret)}

    first = client.post("/api/v1/payments/stripe/webhook", content=body, headers=headers)
    second = client.post("/api/v1/payments/stripe/webhook", content=body, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 429


def test_workbench_endpoint_is_rate_limited(client: TestClient) -> None:
    _set_limit(client, "workbench")
    payload = {"gene": "RPE65", "cdna": "c.260A>G"}

    first = client.post("/api/v1/align", json=payload)
    second = client.post("/api/v1/align", json=payload)

    assert first.status_code == 200
    assert second.status_code == 429


def test_viewer_endpoint_uses_workbench_rate_limit(client: TestClient) -> None:
    _set_limit(client, "workbench")
    payload = {"gene": "RPE65", "cdna": "c.260A>G", "transcript": "NM_000329.3"}

    first = client.post("/api/v1/viewer", json=payload)
    second = client.post("/api/v1/viewer", json=payload)

    assert first.status_code == 200
    assert second.status_code == 429
