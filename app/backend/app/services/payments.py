from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException, status

from app.core.deps import AuthenticatedPrincipal
from app.schemas.payments import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    CurrentPlanResponse,
    PlanContract,
    PlanLimits,
    StripeWebhookResponse,
)

_ACTIVE_STATUSES = {"active", "trialing", "past_due", "incomplete", "unpaid"}
_PLAN_CATALOG: dict[str, PlanContract] = {
    "free": PlanContract(
        plan_key="free",
        display_name="Free",
        monthly_price_aud_cents=0,
        limits=PlanLimits(
            ai_queries_per_day=3,
            quiet_free_search_rate_limit=True,
            evidence_submissions_enabled=False,
            vcf_uploads_enabled=False,
            vcf_variants_per_upload=0,
            vcf_cap_policy="disabled",
        ),
    ),
    "pro": PlanContract(
        plan_key="pro",
        display_name="Pro",
        monthly_price_aud_cents=995,
        limits=PlanLimits(
            ai_queries_per_day=10,
            evidence_submissions_enabled=True,
            vcf_uploads_enabled=True,
            vcf_cap_policy="numeric_cap_pending",
        ),
    ),
    "max": PlanContract(
        plan_key="max",
        display_name="Max",
        monthly_price_aud_cents=2495,
        limits=PlanLimits(
            ai_queries_per_day=100,
            ai_queries_fair_use=True,
            evidence_submissions_enabled=True,
            vcf_uploads_enabled=True,
            vcf_cap_policy="fair_use",
        ),
    ),
}


class PaymentsService:
    def __init__(self, settings, subscriptions_repo) -> None:
        self.settings = settings
        self.subscriptions_repo = subscriptions_repo

    def create_checkout_session(
        self,
        payload: CheckoutSessionRequest,
        principal: AuthenticatedPrincipal,
    ) -> CheckoutSessionResponse:
        plan = _plan_contract(payload.plan_key)
        price_id = self._price_id(payload.plan_key)
        if not self.settings.stripe_secret_key or not price_id:
            return CheckoutSessionResponse(
                session_id=f"mock_cs_{uuid4().hex}",
                checkout_url=None,
                mode="mock",
                plan_key=payload.plan_key,
                billing_interval=payload.billing_interval,
                plan=plan,
                warnings=["stripe_checkout_not_configured"],
            )

        data = {
            "mode": "subscription",
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "success_url": self.settings.stripe_checkout_success_url,
            "cancel_url": self.settings.stripe_checkout_cancel_url,
            "client_reference_id": principal.user_id,
            "metadata[user_id]": principal.user_id,
            "metadata[plan_key]": payload.plan_key,
            "metadata[billing_interval]": "monthly",
            "subscription_data[metadata][user_id]": principal.user_id,
            "subscription_data[metadata][plan_key]": payload.plan_key,
            "subscription_data[metadata][billing_interval]": "monthly",
        }
        if principal.email:
            data["customer_email"] = principal.email

        try:
            response = httpx.post(
                "https://api.stripe.com/v1/checkout/sessions",
                data=data,
                headers={"Authorization": f"Bearer {self.settings.stripe_secret_key}"},
                timeout=12.0,
            )
            response.raise_for_status()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Stripe checkout session creation failed: {type(exc).__name__}",
            ) from exc

        session = response.json()
        return CheckoutSessionResponse(
            session_id=str(session.get("id") or ""),
            checkout_url=session.get("url"),
            mode="stripe",
            plan_key=payload.plan_key,
            billing_interval=payload.billing_interval,
            plan=plan,
        )

    def current_plan(self, principal: AuthenticatedPrincipal) -> CurrentPlanResponse:
        record = self.subscriptions_repo.get_by_user_id(principal.user_id)
        if record is None:
            return CurrentPlanResponse(
                user_id=principal.user_id,
                plan=_plan_contract("free"),
            )
        return _record_to_plan_response(record, principal.user_id)

    def process_stripe_webhook(
        self,
        body: bytes,
        stripe_signature: str | None,
    ) -> StripeWebhookResponse:
        if not self.settings.stripe_webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe webhook secret is not configured.",
            )
        _verify_stripe_signature(
            body,
            stripe_signature,
            secret=self.settings.stripe_webhook_secret,
            tolerance_seconds=self.settings.stripe_webhook_tolerance_seconds,
        )
        try:
            event = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Stripe webhook JSON.",
            ) from exc

        event_id = str(event.get("id") or "")
        event_type = str(event.get("type") or "")
        data_object = event.get("data", {}).get("object", {})
        if not event_id or not event_type or not isinstance(data_object, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Stripe webhook event envelope.",
            )

        if event_type == "checkout.session.completed":
            plan_state = self._record_checkout_completed(event, data_object)
        elif event_type.startswith("customer.subscription."):
            plan_state = self._record_subscription_event(event, data_object)
        elif event_type in {"invoice.paid", "invoice.payment_failed"}:
            plan_state = self._record_invoice_event(event, data_object)
        else:
            return StripeWebhookResponse(
                event_id=event_id,
                event_type=event_type,
                processed=False,
                warnings=["stripe_event_ignored"],
            )

        return StripeWebhookResponse(
            event_id=event_id,
            event_type=event_type,
            processed=plan_state is not None,
            plan_state=plan_state,
        )

    def _record_checkout_completed(
        self,
        event: dict[str, Any],
        session: dict[str, Any],
    ) -> CurrentPlanResponse | None:
        metadata = _metadata(session)
        user_id = _text(session.get("client_reference_id")) or metadata.get("user_id")
        if not user_id:
            return None
        plan_key = _normalize_plan(metadata.get("plan_key"))
        billing_interval = _billing_interval_for_plan(
            plan_key,
            metadata.get("billing_interval"),
        )
        status_value = "active" if session.get("payment_status") == "paid" else "incomplete"
        record = self.subscriptions_repo.upsert_state(
            user_id=user_id,
            stripe_customer_id=_text(session.get("customer")),
            stripe_subscription_id=_text(session.get("subscription")),
            plan_key=plan_key,
            billing_interval=billing_interval,
            status=status_value,
            current_period_end=None,
            last_event_id=str(event["id"]),
            raw_event=event,
        )
        return _record_to_plan_response(record, user_id)

    def _record_subscription_event(
        self,
        event: dict[str, Any],
        subscription: dict[str, Any],
    ) -> CurrentPlanResponse | None:
        metadata = _metadata(subscription)
        user_id = metadata.get("user_id")
        plan_key = _normalize_plan(
            metadata.get("plan_key") or self._plan_from_subscription(subscription)
        )
        billing_interval = _normalize_interval(
            metadata.get("billing_interval") or _interval_from_subscription(subscription)
        )
        billing_interval = _billing_interval_for_plan(plan_key, billing_interval)
        status_value = _normalize_subscription_status(subscription.get("status"))
        record = self.subscriptions_repo.upsert_state(
            user_id=user_id,
            stripe_customer_id=_text(subscription.get("customer")),
            stripe_subscription_id=_text(subscription.get("id")),
            plan_key=plan_key,
            billing_interval=billing_interval,
            status=status_value,
            current_period_end=_datetime_from_stripe_ts(subscription.get("current_period_end")),
            last_event_id=str(event["id"]),
            raw_event=event,
        )
        return _record_to_plan_response(record, user_id or "")

    def _record_invoice_event(
        self,
        event: dict[str, Any],
        invoice: dict[str, Any],
    ) -> CurrentPlanResponse | None:
        metadata = _metadata(invoice)
        user_id = metadata.get("user_id")
        status_value = "active" if event.get("type") == "invoice.paid" else "past_due"
        plan_key = _normalize_plan(metadata.get("plan_key"))
        billing_interval = _billing_interval_for_plan(
            plan_key,
            metadata.get("billing_interval"),
        )
        record = self.subscriptions_repo.upsert_state(
            user_id=user_id,
            stripe_customer_id=_text(invoice.get("customer")),
            stripe_subscription_id=_text(invoice.get("subscription")),
            plan_key=plan_key,
            billing_interval=billing_interval,
            status=status_value,
            current_period_end=None,
            last_event_id=str(event["id"]),
            raw_event=event,
        )
        return _record_to_plan_response(record, user_id or "")

    def _price_id(self, plan_key: str) -> str | None:
        attr = f"stripe_price_{plan_key}_monthly"
        return getattr(self.settings, attr, None)

    def _plan_from_subscription(self, subscription: dict[str, Any]) -> str | None:
        price_id = _price_id_from_subscription(subscription)
        if not price_id:
            return None
        price_to_plan = {
            self.settings.stripe_price_pro_monthly: "pro",
            self.settings.stripe_price_max_monthly: "max",
        }
        return price_to_plan.get(price_id)


def _verify_stripe_signature(
    payload: bytes,
    signature_header: str | None,
    *,
    secret: str,
    tolerance_seconds: int,
) -> None:
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header.",
        )
    values: dict[str, list[str]] = {}
    for chunk in signature_header.split(","):
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        values.setdefault(key, []).append(value)
    timestamp_values = values.get("t") or []
    signatures = values.get("v1") or []
    if not timestamp_values or not signatures:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe-Signature header.",
        )
    timestamp = int(timestamp_values[0])
    if abs(time.time() - timestamp) > tolerance_seconds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expired Stripe webhook signature.",
        )
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook signature.",
        )


def _record_to_plan_response(record, user_id: str) -> CurrentPlanResponse:
    active_plan_key = _normalize_plan(record.plan_key)
    plan_key = active_plan_key if record.status in _ACTIVE_STATUSES else "free"
    return CurrentPlanResponse(
        user_id=record.user_id or user_id,
        plan_key=plan_key,
        billing_interval=_billing_interval_for_plan(plan_key, record.billing_interval),
        status=record.status,
        stripe_customer_id=record.stripe_customer_id,
        stripe_subscription_id=record.stripe_subscription_id,
        current_period_end=record.current_period_end,
        updated_at=record.updated_at,
        plan=_plan_contract(plan_key),
    )


def _metadata(payload: dict[str, Any]) -> dict[str, str]:
    metadata = payload.get("metadata") or {}
    if not isinstance(metadata, dict):
        return {}
    return {str(key): str(value) for key, value in metadata.items() if value is not None}


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_plan(value: str | None) -> str:
    return value if value in {"pro", "max"} else "free"


def _normalize_interval(value: str | None) -> str | None:
    return value if value == "monthly" else None


def _billing_interval_for_plan(plan_key: str, value: str | None) -> str | None:
    interval = _normalize_interval(value)
    if plan_key in {"pro", "max"}:
        return interval or "monthly"
    return None


def _normalize_subscription_status(value: Any) -> str:
    status_value = _text(value) or "unknown"
    allowed = {
        "active",
        "trialing",
        "past_due",
        "canceled",
        "incomplete",
        "incomplete_expired",
        "unpaid",
    }
    return status_value if status_value in allowed else "unknown"


def _datetime_from_stripe_ts(value: Any) -> datetime | None:
    if not isinstance(value, int):
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc)


def _price_id_from_subscription(subscription: dict[str, Any]) -> str | None:
    items = subscription.get("items", {}).get("data", [])
    if not isinstance(items, list) or not items:
        return None
    first_item = items[0] if isinstance(items[0], dict) else {}
    price = first_item.get("price") if isinstance(first_item, dict) else None
    if not isinstance(price, dict):
        return None
    return _text(price.get("id"))


def _interval_from_subscription(subscription: dict[str, Any]) -> str | None:
    items = subscription.get("items", {}).get("data", [])
    if not isinstance(items, list) or not items:
        return None
    first_item = items[0] if isinstance(items[0], dict) else {}
    price = first_item.get("price") if isinstance(first_item, dict) else None
    recurring = price.get("recurring") if isinstance(price, dict) else None
    if not isinstance(recurring, dict):
        return None
    interval = recurring.get("interval")
    if interval == "month":
        return "monthly"
    return None


def _plan_contract(plan_key: str) -> PlanContract:
    return _PLAN_CATALOG.get(plan_key, _PLAN_CATALOG["free"]).model_copy(deep=True)
