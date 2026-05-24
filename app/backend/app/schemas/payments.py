from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

PlanKey = Literal["free", "starter", "pro"]
PaidPlanKey = Literal["starter", "pro"]
BillingInterval = Literal["monthly", "yearly"]
CheckoutMode = Literal["stripe", "mock"]
SubscriptionStatus = Literal[
    "free",
    "active",
    "trialing",
    "past_due",
    "canceled",
    "incomplete",
    "incomplete_expired",
    "unpaid",
    "unknown",
]


class CheckoutSessionRequest(BaseModel):
    plan_key: PaidPlanKey
    billing_interval: BillingInterval = "monthly"
    success_url: str | None = Field(default=None, max_length=500)
    cancel_url: str | None = Field(default=None, max_length=500)

    @field_validator("success_url", "cancel_url", mode="before")
    @classmethod
    def _strip_url(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None


class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str | None
    mode: CheckoutMode
    plan_key: PaidPlanKey
    billing_interval: BillingInterval
    warnings: list[str] = Field(default_factory=list)


class CurrentPlanResponse(BaseModel):
    user_id: str
    plan_key: PlanKey = "free"
    billing_interval: BillingInterval | None = None
    status: SubscriptionStatus = "free"
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    current_period_end: datetime | None = None
    updated_at: datetime | None = None


class StripeWebhookResponse(BaseModel):
    received: bool = True
    event_id: str
    event_type: str
    processed: bool
    plan_state: CurrentPlanResponse | None = None
    warnings: list[str] = Field(default_factory=list)
