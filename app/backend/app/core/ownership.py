from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OwnerIdentity:
    """Server-derived namespace for a user-owned resource."""

    provider: str
    user_id: str

    def __post_init__(self) -> None:
        if not self.provider or not self.user_id:
            raise ValueError("Owner identity requires provider and user_id.")
