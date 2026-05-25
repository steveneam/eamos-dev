from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.deps import AuthenticatedPrincipal, require_authenticated_principal
from app.core.rate_limit import (
    RATE_LIMIT_PAYMENTS_CHECKOUT,
    RATE_LIMIT_PAYMENTS_WEBHOOK,
    enforce_rate_limit,
)
from app.schemas.payments import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    CurrentPlanResponse,
    StripeWebhookResponse,
)

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
def create_checkout_session(
    payload: CheckoutSessionRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> CheckoutSessionResponse:
    enforce_rate_limit(request, RATE_LIMIT_PAYMENTS_CHECKOUT, subject=principal.user_id)
    service = getattr(request.app.state, "payments_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payments service is unavailable.",
        )
    return service.create_checkout_session(payload, principal)


@router.get("/plan", response_model=CurrentPlanResponse)
def current_plan(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> CurrentPlanResponse:
    service = getattr(request.app.state, "payments_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payments service is unavailable.",
        )
    return service.current_plan(principal)


@router.post("/stripe/webhook", response_model=StripeWebhookResponse)
async def stripe_webhook(request: Request) -> StripeWebhookResponse:
    enforce_rate_limit(request, RATE_LIMIT_PAYMENTS_WEBHOOK)
    service = getattr(request.app.state, "payments_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payments service is unavailable.",
        )
    body = await request.body()
    return service.process_stripe_webhook(body, request.headers.get("stripe-signature"))
