from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.auth import AuthUser, LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix='/api/v1/auth', tags=['auth'])
bearer_scheme = HTTPBearer(auto_error=False)


def _get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None or credentials.scheme.lower() != 'bearer' or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing bearer token.',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return credentials.credentials


@router.post('/register', response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request) -> TokenResponse:
    return request.app.state.auth_service.register(payload)


@router.post('/login', response_model=TokenResponse)
def login(payload: LoginRequest, request: Request) -> TokenResponse:
    return request.app.state.auth_service.login(payload)


@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    token: str = Depends(_get_bearer_token),
) -> Response:
    request.app.state.auth_service.logout(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/me', response_model=AuthUser)
def me(request: Request, token: str = Depends(_get_bearer_token)) -> AuthUser:
    return request.app.state.auth_service.get_current_user(token)
