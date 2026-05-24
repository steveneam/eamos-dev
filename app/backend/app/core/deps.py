from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKClient, PyJWKClientError

from app.schemas.auth import AuthUser

bearer_scheme = HTTPBearer(auto_error=False)
_SUPPORTED_SUPABASE_ALGORITHMS = {"HS256", "ES256"}


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
    algorithm = _supabase_token_algorithm(settings, token)
    if algorithm is None:
        return None
    key = _supabase_verification_key(settings, token, algorithm)
    if key is None:
        return None
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[algorithm],
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


def _supabase_token_algorithm(settings, token: str) -> str | None:
    configured = str(getattr(settings, "supabase_jwt_algorithm", "") or "").upper()
    if configured and configured != "AUTO":
        return configured if configured in _SUPPORTED_SUPABASE_ALGORITHMS else None
    try:
        header = jwt.get_unverified_header(token)
    except InvalidTokenError:
        return None
    algorithm = str(header.get("alg") or "").upper()
    return algorithm if algorithm in _SUPPORTED_SUPABASE_ALGORITHMS else None


def _supabase_verification_key(settings, token: str, algorithm: str):
    if algorithm == "HS256":
        return settings.supabase_jwt_secret

    if algorithm == "ES256" and settings.supabase_jwt_public_key:
        return _normalized_pem(settings.supabase_jwt_public_key)

    jwks_url = settings.supabase_jwks_url or _default_supabase_jwks_url(settings.supabase_url)
    if not jwks_url:
        return None
    try:
        return _jwk_client_for_url(jwks_url).get_signing_key_from_jwt(token).key
    except (InvalidTokenError, PyJWKClientError, ValueError):
        return None


def _default_supabase_jwks_url(supabase_url: str | None) -> str | None:
    if not supabase_url:
        return None
    return f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


def _normalized_pem(value: str) -> str:
    return value.replace("\\n", "\n").strip()


@lru_cache(maxsize=8)
def _jwk_client_for_url(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)
