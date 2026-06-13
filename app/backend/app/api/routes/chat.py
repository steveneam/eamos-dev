from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.deps import AuthenticatedPrincipal, require_authenticated_principal
from app.core.rate_limit import RATE_LIMIT_CHAT, enforce_rate_limit
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# Ask-Eamos chat reaches the paid AI gateway, so both entry points require auth and
# are rate-limited per authenticated user (docs/ai-gateway/pre-launch-security.md):
# login is the gate that makes every request attributable and closes the anonymous
# rotating-IP cost-abuse vector before LLM_PROVIDER is ever set to "gateway".
@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> ChatResponse:
    enforce_rate_limit(request, RATE_LIMIT_CHAT, subject=principal.user_id)
    service = getattr(request.app.state, "chat_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is unavailable.",
        )
    return service.respond(payload)


@router.post("/stream")
def chat_stream(
    payload: ChatRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
) -> StreamingResponse:
    enforce_rate_limit(request, RATE_LIMIT_CHAT, subject=principal.user_id)
    service = getattr(request.app.state, "chat_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is unavailable.",
        )
    return StreamingResponse(
        service.respond_stream(payload),
        media_type="text/plain",
        headers={
            # Disable proxy/CDN buffering so tokens reach the client as they stream.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
