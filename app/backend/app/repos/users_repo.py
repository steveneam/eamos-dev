from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select

from app.core.db import UserRecord, session_scope


class UsersRepo:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def create_user(self, user_id: str, username: str, hashed_password: str) -> UserRecord:
        now = datetime.now(timezone.utc)
        with session_scope(self.session_factory) as session:
            record = UserRecord(
                user_id=user_id,
                username=username,
                hashed_password=hashed_password,
                is_active=True,
                token_version=0,
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            session.flush()
            return record

    def get_by_username(self, username: str) -> UserRecord | None:
        with session_scope(self.session_factory) as session:
            stmt = select(UserRecord).where(func.lower(UserRecord.username) == username.lower())
            return session.execute(stmt).scalar_one_or_none()

    def get_by_user_id(self, user_id: str) -> UserRecord | None:
        with session_scope(self.session_factory) as session:
            return session.get(UserRecord, user_id)

    def record_login(self, user_id: str) -> UserRecord:
        now = datetime.now(timezone.utc)
        with session_scope(self.session_factory) as session:
            record = session.get(UserRecord, user_id)
            if record is None:
                raise KeyError(user_id)
            record.last_login_at = now
            record.updated_at = now
            session.add(record)
            session.flush()
            return record

    def bump_token_version(self, user_id: str) -> UserRecord:
        now = datetime.now(timezone.utc)
        with session_scope(self.session_factory) as session:
            record = session.get(UserRecord, user_id)
            if record is None:
                raise KeyError(user_id)
            record.token_version += 1
            record.updated_at = now
            session.add(record)
            session.flush()
            return record
