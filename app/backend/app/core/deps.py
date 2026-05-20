from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.auth import AuthUser

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request):
    return request.app.state.settings


def get_reports_repo(request: Request):
    return request.app.state.reports_repo


def get_run_repo(request: Request):
    return request.app.state.run_repo


def require_authenticated_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthUser:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = request.app.state.auth_service.get_current_user(credentials.credentials)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        raise

    # TODO: Add patient/run ownership checks once ownership metadata is modeled.
    return user
