from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AuthUser(BaseModel):
    user_id: str
    username: str
    is_active: bool
    token_version: int
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=255)

    @field_validator('username')
    @classmethod
    def normalize_username(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError('Username must be at least 3 characters long.')
        return value

    @field_validator('password')
    @classmethod
    def normalize_password(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 8:
            raise ValueError('Password must be at least 8 characters long.')
        return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=255)

    @field_validator('username')
    @classmethod
    def normalize_username(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError('Username must be at least 3 characters long.')
        return value

    @field_validator('password')
    @classmethod
    def normalize_password(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 8:
            raise ValueError('Password must be at least 8 characters long.')
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    expires_at: datetime
    ttl_seconds: int
    user: AuthUser
