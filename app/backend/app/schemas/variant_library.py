from __future__ import annotations

import time
from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

ClassificationTier = Literal[
    "pathogenic",
    "likely_pathogenic",
    "vus",
    "likely_benign",
    "benign",
]


class SavedVariant(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(min_length=1, max_length=512)
    gene: str | None = Field(default=None, max_length=64)
    variant: str | None = Field(default=None, max_length=512)
    query: str = Field(min_length=1, max_length=512)
    raw: str = Field(default="", max_length=4000)
    savedAt: int = Field(default_factory=lambda: int(time.time() * 1000), ge=0)
    folderId: str | None = Field(
        default=None,
        max_length=64,
        validation_alias=AliasChoices("folderId", "folder_id"),
    )
    classification: ClassificationTier | None = None
    hgvs_full: str | None = Field(default=None, max_length=512)

    @field_validator("id", "gene", "variant", "query", "folderId", "hgvs_full", mode="before")
    @classmethod
    def _strip_text(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("raw", mode="before")
    @classmethod
    def _strip_raw(cls, value):
        if value is None:
            return ""
        if not isinstance(value, str):
            return value
        return value.strip()

    @field_validator("id")
    @classmethod
    def _normalize_id(cls, value: str) -> str:
        return value.strip().lower()


class Folder(BaseModel):
    id: str
    name: str
    createdAt: int


class LibraryStore(BaseModel):
    variants: list[SavedVariant] = Field(default_factory=list)
    folders: list[Folder] = Field(default_factory=list)


class SaveVariantsRequest(BaseModel):
    variants: list[SavedVariant] = Field(min_length=1, max_length=100)


class SaveVariantsResponse(BaseModel):
    added: int
    variants: list[SavedVariant]
    library: LibraryStore


class CreateFolderRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be empty")
        return stripped


class RenameFolderRequest(CreateFolderRequest):
    pass


class MoveVariantRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    folderId: str | None = Field(
        default=None,
        max_length=64,
        validation_alias=AliasChoices("folderId", "folder_id"),
    )

    @field_validator("folderId", mode="before")
    @classmethod
    def _strip_folder(cls, value):
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None


class VariantPopularity(BaseModel):
    query_id: str
    view_count: int
    last_viewed: datetime


class PopularVariantsResponse(BaseModel):
    variants: list[VariantPopularity]


class VariantViewResponse(BaseModel):
    variant: VariantPopularity
