from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.rate_limit import RATE_LIMIT_CHAT, enforce_rate_limit
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    enforce_rate_limit(request, RATE_LIMIT_CHAT)
    service = getattr(request.app.state, "chat_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is unavailable.",
        )
    return service.respond(payload)


@router.post("/stream")
def chat_stream(payload: ChatRequest, request: Request) -> StreamingResponse:
    enforce_rate_limit(request, RATE_LIMIT_CHAT)
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
