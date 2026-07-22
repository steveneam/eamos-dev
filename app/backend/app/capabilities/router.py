from __future__ import annotations

from fastapi import APIRouter, Request

from app.capabilities.models import RuntimeCapabilityRegistryV1

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/capabilities", response_model=RuntimeCapabilityRegistryV1)
def runtime_capabilities(request: Request) -> RuntimeCapabilityRegistryV1:
    """Return bounded runtime truth without paths, secrets, or source payloads."""

    return request.app.state.runtime_capability_registry
