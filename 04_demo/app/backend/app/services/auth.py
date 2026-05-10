from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError, VerificationError
from fastapi import HTTPException, status
from jwt import InvalidTokenError

from app.schemas.auth import AuthUser, LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    def __init__(self, settings, users_repo) -> None:
        self.settings = settings
        self.users_repo = users_repo
        self.password_hasher = PasswordHasher()

    def register(self, payload: RegisterRequest) -> TokenResponse:
        existing_user = self.users_repo.get_by_username(payload.username)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Username already exists.',
            )

        user = self.users_repo.create_user(
            user_id=f'user_{uuid4().hex}',
            username=payload.username,
            hashed_password=self.password_hasher.hash(payload.password),
        )
        user = self.users_repo.record_login(user.user_id)
        return self._build_token_response(user)

    def login(self, payload: LoginRequest) -> TokenResponse:
        user = self.users_repo.get_by_username(payload.username)
        if user is None or not self._verify_password(payload.password, user.hashed_password):
            raise self._auth_error('Invalid username or password.')
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='User account is inactive.',
            )

        user = self.users_repo.record_login(user.user_id)
        return self._build_token_response(user)

    def get_current_user(self, token: str) -> AuthUser:
        claims = self._decode_token(token)
        user_id = claims.get('sub')
        token_version = claims.get('ver')
        if not isinstance(user_id, str) or not isinstance(token_version, int):
            raise self._auth_error('Invalid access token.')

        user = self.users_repo.get_by_user_id(user_id)
        if user is None or not user.is_active:
            raise self._auth_error('Invalid access token.')
        if user.token_version != token_version:
            raise self._auth_error('Access token has been revoked.')

        return self._to_auth_user(user)

    def logout(self, token: str) -> None:
        claims = self._decode_token(token)
        user_id = claims.get('sub')
        token_version = claims.get('ver')
        if not isinstance(user_id, str) or not isinstance(token_version, int):
            raise self._auth_error('Invalid access token.')

        user = self.users_repo.get_by_user_id(user_id)
        if user is None:
            raise self._auth_error('Invalid access token.')
        if user.token_version != token_version:
            raise self._auth_error('Access token has been revoked.')

        self.users_repo.bump_token_version(user_id)

    def _build_token_response(self, user) -> TokenResponse:
        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(days=self.settings.jwt_ttl_days)
        token = jwt.encode(
            {
                'sub': user.user_id,
                'username': user.username,
                'ver': user.token_version,
                'typ': 'access',
                'iat': issued_at,
                'exp': expires_at,
            },
            self.settings.jwt_secret,
            algorithm=self.settings.jwt_algorithm,
        )
        ttl_seconds = int((expires_at - issued_at).total_seconds())
        return TokenResponse(
            access_token=token,
            expires_at=expires_at,
            ttl_seconds=ttl_seconds,
            user=self._to_auth_user(user),
        )

    def _decode_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret,
                algorithms=[self.settings.jwt_algorithm],
            )
        except InvalidTokenError as exc:
            raise self._auth_error('Invalid or expired access token.') from exc
        if not isinstance(payload, dict) or payload.get('typ') != 'access':
            raise self._auth_error('Invalid access token.')
        return payload

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        try:
            return self.password_hasher.verify(hashed_password, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def _to_auth_user(self, user) -> AuthUser:
        return AuthUser(
            user_id=user.user_id,
            username=user.username,
            is_active=user.is_active,
            token_version=user.token_version,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
        )

    def _auth_error(self, detail: str) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={'WWW-Authenticate': 'Bearer'},
        )
