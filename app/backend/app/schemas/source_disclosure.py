from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

WorkbenchSourceStatus = Literal[
    "source_backed",
    "local_provider",
    "fallback",
    "fixture",
    "gated",
    "unavailable",
]


class SourceDisclosure(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_status: WorkbenchSourceStatus
    provider_id: str = Field(min_length=1, max_length=128)
    provider_label: str = Field(min_length=1, max_length=160)
    source_version: str | None = Field(default=None, min_length=1, max_length=128)
    cache_status: str | None = Field(default=None, min_length=1, max_length=128)
    warnings: list[Annotated[str, Field(min_length=1, max_length=512)]] = Field(
        default_factory=list, max_length=64
    )
    requirements: list[Annotated[str, Field(min_length=1, max_length=512)]] = Field(
        default_factory=list, max_length=64
    )
