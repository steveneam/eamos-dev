from __future__ import annotations

import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient


def _stripe_signature(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    timestamp = timestamp or int(time.time())
    signed = f"{timestamp}.".encode("utf-8") + payload
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def test_current_plan_defaults_to_free(auth_client: TestClient) -> None:
    response = auth_client.get("/api/v1/payments/plan")

    assert response.status_code == 200
    body = response.json()
    assert body["plan_key"] == "free"
    assert body["status"] == "free"
    assert body["plan"]["display_name"] == "Free"
    assert body["plan"]["monthly_price_aud_cents"] == 0
    assert body["plan"]["limits"]["ai_queries_per_day"] == 3
    assert body["plan"]["limits"]["quiet_free_search_rate_limit"] is True
    assert body["plan"]["limits"]["evidence_submissions_enabled"] is False


def test_checkout_session_returns_mock_when_stripe_not_configured(
    auth_client: TestClient,
) -> None:
    response = auth_client.post(
        "/api/v1/payments/checkout-session",
        json={"plan_key": "max"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "mock"
    assert body["checkout_url"] is None
    assert body["plan_key"] == "max"
    assert body["billing_interval"] == "monthly"
    assert body["plan"]["monthly_price_aud_cents"] == 2495
    assert body["plan"]["limits"]["ai_queries_per_day"] == 100
    assert body["plan"]["limits"]["ai_queries_fair_use"] is True
    assert "stripe_checkout_not_configured" in body["warnings"]


def test_checkout_session_rejects_legacy_starter_and_yearly_cycle(
    auth_client: TestClient,
) -> None:
    legacy_plan = auth_client.post(
        "/api/v1/payments/checkout-session",
        json={"plan_key": "starter"},
    )
    legacy_cycle = auth_client.post(
        "/api/v1/payments/checkout-session",
        json={"plan_key": "pro", "billing_interval": "yearly"},
    )

    assert legacy_plan.status_code == 422
    assert legacy_cycle.status_code == 422


def test_stripe_webhook_rejects_missing_signature(client: TestClient) -> None:
    client.app.state.settings.stripe_webhook_secret = "whsec_test"
    response = client.post(
        "/api/v1/payments/stripe/webhook",
        content=b'{"id":"evt_missing","type":"ping","data":{"object":{}}}',
    )

    assert response.status_code == 400


def test_stripe_checkout_webhook_records_plan_state(auth_client: TestClient) -> None:
    auth_response = auth_client.get("/api/v1/auth/me")
    user_id = auth_response.json()["user_id"]
    secret = "whsec_test"
    auth_client.app.state.settings.stripe_webhook_secret = secret
    event = {
        "id": "evt_checkout_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_1",
                "customer": "cus_123",
                "subscription": "sub_123",
                "client_reference_id": user_id,
                "payment_status": "paid",
                "metadata": {
                    "user_id": user_id,
                    "plan_key": "max",
                },
            }
        },
    }
    body = json.dumps(event, separators=(",", ":")).encode("utf-8")

    response = auth_client.post(
        "/api/v1/payments/stripe/webhook",
        content=body,
        headers={"Stripe-Signature": _stripe_signature(body, secret)},
    )

    assert response.status_code == 200
    webhook = response.json()
    assert webhook["processed"] is True
    assert webhook["plan_state"]["plan_key"] == "max"
    assert webhook["plan_state"]["status"] == "active"
    assert webhook["plan_state"]["plan"]["monthly_price_aud_cents"] == 2495

    plan = auth_client.get("/api/v1/payments/plan")
    assert plan.status_code == 200
    plan_body = plan.json()
    assert plan_body["plan_key"] == "max"
    assert plan_body["billing_interval"] == "monthly"
    assert plan_body["plan"]["limits"]["evidence_submissions_enabled"] is True
    assert plan_body["plan"]["limits"]["evidence_submission_requires_identity_verification"] is True
    assert plan_body["stripe_subscription_id"] == "sub_123"
