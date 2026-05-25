from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PlanKey = Literal["free", "pro", "max"]
PaidPlanKey = Literal["pro", "max"]
BillingInterval = Literal["monthly"]
CheckoutMode = Literal["stripe", "mock"]
VcfCapPolicy = Literal["disabled", "numeric_cap_pending", "fair_use"]
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


class PlanLimits(BaseModel):
    ai_queries_per_day: int = Field(ge=0)
    ai_queries_fair_use: bool = False
    quiet_free_search_rate_limit: bool = False
    evidence_submissions_enabled: bool = False
    evidence_submission_requires_active_subscription: bool = True
    evidence_submission_requires_identity_verification: bool = True
    vcf_uploads_enabled: bool = False
    vcf_variants_per_upload: int | None = Field(default=None, ge=0)
    vcf_cap_policy: VcfCapPolicy = "disabled"


class PlanContract(BaseModel):
    plan_key: PlanKey
    display_name: str
    monthly_price_aud_cents: int = Field(ge=0)
    currency: Literal["AUD"] = "AUD"
    billing_interval: BillingInterval = "monthly"
    limits: PlanLimits


class CheckoutSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_key: PaidPlanKey
    billing_interval: BillingInterval = "monthly"


class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str | None
    mode: CheckoutMode
    plan_key: PaidPlanKey
    billing_interval: BillingInterval
    plan: PlanContract
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
    plan: PlanContract


class StripeWebhookResponse(BaseModel):
    received: bool = True
    event_id: str
    event_type: str
    processed: bool
    plan_state: CurrentPlanResponse | None = None
    warnings: list[str] = Field(default_factory=list)
