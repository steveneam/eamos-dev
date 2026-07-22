from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import sqlite3
from typing import Literal
from uuid import uuid4

BatchLeaseState = Literal["queued", "running", "completed", "failed", "cancelled"]
_ACTIVE_STATES = ("queued", "running")
_TERMINAL_STATES = ("completed", "failed", "cancelled")


@dataclass(frozen=True)
class BatchLease:
    job_id: str
    owner_user_id: str
    owner_provider: str
    state: BatchLeaseState
    attempt: int
    worker_instance_id: str | None
    lease_expires_at: datetime | None
    updated_at: datetime


class BatchLeaseStore:
    """Small owner-bound recovery ledger that never stores VCF bytes or genotypes.

    Scientific task/result state remains in the existing owner-scoped workflow
    repository. This ledger only identifies work that another process instance
    must resume or truthfully fail after a restart.
    """

    def __init__(
        self,
        path: Path,
        *,
        lease_seconds: int = 120,
        worker_instance_id: str | None = None,
    ) -> None:
        self.path = path
        self.lease_seconds = max(1, min(int(lease_seconds), 3600))
        self.worker_instance_id = worker_instance_id or f"worker-{uuid4().hex}"
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.path.parent, 0o700)
        except OSError:
            pass
        self._initialize()

    def enqueue(self, *, job_id: str, owner_user_id: str, owner_provider: str) -> BatchLease:
        _validate_identifier(job_id, "job_id", max_length=128)
        _validate_identifier(owner_user_id, "owner_user_id", max_length=128)
        _validate_identifier(owner_provider, "owner_provider", max_length=32)
        now = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO batch_job_lease (
                    job_id, owner_user_id, owner_provider, state, attempt,
                    worker_instance_id, lease_expires_at, updated_at
                ) VALUES (?, ?, ?, 'queued', 0, NULL, NULL, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    owner_user_id = excluded.owner_user_id,
                    owner_provider = excluded.owner_provider,
                    state = 'queued',
                    worker_instance_id = NULL,
                    lease_expires_at = NULL,
                    updated_at = excluded.updated_at
                """,
                (job_id, owner_user_id, owner_provider, _iso(now)),
            )
        lease = self.get(job_id)
        if lease is None:  # pragma: no cover - SQLite acknowledged the insert
            raise RuntimeError("Batch lease could not be read after enqueue.")
        return lease

    def reserve(self, job_id: str) -> bool:
        """Reserve queued work for this process before submitting it locally."""

        now = _now()
        expires_at = now + timedelta(seconds=self.lease_seconds)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM batch_job_lease WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if row is None or row["state"] != "queued":
                connection.rollback()
                return False
            existing_expiry = _optional_datetime(row["lease_expires_at"])
            owned_by_other_live_worker = (
                row["worker_instance_id"] not in {None, self.worker_instance_id}
                and existing_expiry is not None
                and existing_expiry > now
            )
            if owned_by_other_live_worker:
                connection.rollback()
                return False
            connection.execute(
                """
                UPDATE batch_job_lease
                SET worker_instance_id = ?, lease_expires_at = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (self.worker_instance_id, _iso(expires_at), _iso(now), job_id),
            )
            connection.commit()
        return True

    def claim(self, job_id: str) -> BatchLease | None:
        _validate_identifier(job_id, "job_id", max_length=128)
        now = _now()
        expires_at = now + timedelta(seconds=self.lease_seconds)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM batch_job_lease WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if row is None or row["state"] not in _ACTIVE_STATES:
                connection.rollback()
                return None
            existing_expiry = _optional_datetime(row["lease_expires_at"])
            owned_by_other_live_worker = (
                row["worker_instance_id"] not in {None, self.worker_instance_id}
                and existing_expiry is not None
                and existing_expiry > now
            )
            if owned_by_other_live_worker:
                connection.rollback()
                return None
            connection.execute(
                """
                UPDATE batch_job_lease
                SET state = 'running', attempt = attempt + 1,
                    worker_instance_id = ?, lease_expires_at = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (self.worker_instance_id, _iso(expires_at), _iso(now), job_id),
            )
            connection.commit()
        return self.get(job_id)

    def renew(self, job_id: str) -> bool:
        now = _now()
        expires_at = now + timedelta(seconds=self.lease_seconds)
        with self._connect() as connection:
            result = connection.execute(
                """
                UPDATE batch_job_lease
                SET lease_expires_at = ?, updated_at = ?
                WHERE job_id = ? AND state = 'running' AND worker_instance_id = ?
                """,
                (_iso(expires_at), _iso(now), job_id, self.worker_instance_id),
            )
        return bool(result.rowcount)

    def finish(self, job_id: str, *, state: Literal["completed", "failed", "cancelled"]) -> bool:
        if state not in _TERMINAL_STATES:  # defensive for untyped callers
            raise ValueError("Batch lease terminal state is invalid.")
        with self._connect() as connection:
            result = connection.execute(
                """
                UPDATE batch_job_lease
                SET state = ?, worker_instance_id = NULL,
                    lease_expires_at = NULL, updated_at = ?
                WHERE job_id = ?
                """,
                (state, _iso(_now()), job_id),
            )
        return bool(result.rowcount)

    def orphaned(self) -> list[BatchLease]:
        """Return active records not owned by this process instance.

        A process-local identifier makes restart detection immediate. An active
        lease from the same process remains protected until it expires.
        """

        now = _now()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM batch_job_lease
                WHERE state IN ('queued', 'running')
                  AND (worker_instance_id IS NULL OR worker_instance_id != ?)
                  AND (lease_expires_at IS NULL OR lease_expires_at <= ?)
                ORDER BY updated_at ASC, job_id ASC
                """,
                (self.worker_instance_id, _iso(now)),
            ).fetchall()
        return [_lease_from_row(row) for row in rows]

    def get(self, job_id: str) -> BatchLease | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM batch_job_lease WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return _lease_from_row(row) if row is not None else None

    def delete(self, job_id: str) -> bool:
        with self._connect() as connection:
            result = connection.execute(
                "DELETE FROM batch_job_lease WHERE job_id = ?",
                (job_id,),
            )
        return bool(result.rowcount)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS batch_job_lease (
                    job_id TEXT PRIMARY KEY,
                    owner_user_id TEXT NOT NULL,
                    owner_provider TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (
                        state IN ('queued', 'running', 'completed', 'failed', 'cancelled')
                    ),
                    attempt INTEGER NOT NULL CHECK (attempt >= 0),
                    worker_instance_id TEXT,
                    lease_expires_at TEXT,
                    updated_at TEXT NOT NULL
                )
                """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS ix_batch_job_lease_recovery
                ON batch_job_lease (state, updated_at)
                """)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _lease_from_row(row: sqlite3.Row) -> BatchLease:
    return BatchLease(
        job_id=str(row["job_id"]),
        owner_user_id=str(row["owner_user_id"]),
        owner_provider=str(row["owner_provider"]),
        state=str(row["state"]),
        attempt=int(row["attempt"]),
        worker_instance_id=(
            str(row["worker_instance_id"]) if row["worker_instance_id"] is not None else None
        ),
        lease_expires_at=_optional_datetime(row["lease_expires_at"]),
        updated_at=_datetime(row["updated_at"]),
    )


def _validate_identifier(value: str, field_name: str, *, max_length: int) -> None:
    if not value or len(value) > max_length or any(ord(char) < 32 for char in value):
        raise ValueError(f"{field_name} is invalid for the Batch lease ledger.")


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Batch lease timestamp must include a timezone.")
    return parsed.astimezone(UTC)


def _optional_datetime(value: str | None) -> datetime | None:
    return _datetime(value) if value is not None else None
