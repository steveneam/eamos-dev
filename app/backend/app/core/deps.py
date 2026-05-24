from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.schemas.auth import AuthUser

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: str
    provider: str
    token: str
    email: str | None = None


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
    token = _extract_bearer_token(credentials)

    try:
        user = request.app.state.auth_service.get_current_user(token)
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


def require_authenticated_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedPrincipal:
    token = _extract_bearer_token(credentials)
    local_user = _local_principal(request, token)
    if local_user is not None:
        return local_user

    supabase_user = _supabase_principal(request, token)
    if supabase_user is not None:
        return supabase_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _extract_bearer_token(
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def _local_principal(request: Request, token: str) -> AuthenticatedPrincipal | None:
    try:
        user = request.app.state.auth_service.get_current_user(token)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return None
        raise
    return AuthenticatedPrincipal(
        user_id=user.user_id,
        provider="eamos",
        token=token,
        email=user.username if "@" in user.username else None,
    )


def _supabase_principal(request: Request, token: str) -> AuthenticatedPrincipal | None:
    settings = request.app.state.settings
    if not settings.supabase_jwt_secret:
        return None
    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=[settings.supabase_jwt_algorithm],
            audience="authenticated",
        )
    except InvalidTokenError:
        return None
    if not isinstance(claims, dict):
        return None
    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id:
        return None
    role = claims.get("role")
    if role not in (None, "authenticated"):
        return None
    email = claims.get("email") if isinstance(claims.get("email"), str) else None
    return AuthenticatedPrincipal(
        user_id=user_id,
        provider="supabase",
        token=token,
        email=email,
    )
