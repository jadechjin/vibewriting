"""Base entity models for the vibewriting system."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class BaseEntity(BaseModel):
    """Base entity with common audit fields."""

    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    tags: list[str] = Field(default_factory=list)


class AssetBase(BaseEntity):
    """Base class for data assets (figures, tables)."""

    asset_id: str = Field(pattern=r"^ASSET-\d{4}-\d{3,}$")
    kind: Literal["figure", "table"]
    path: str
    content_hash: str
    semantic_description: str
    generator_version: str
