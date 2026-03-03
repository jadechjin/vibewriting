"""Section model for paper structure."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field

from .base import BaseEntity


class Section(BaseEntity):
    """Paper section with status tracking and cross-references."""

    model_config = ConfigDict(extra="forbid")

    section_id: str
    title: str
    outline: list[str] = Field(default_factory=list)
    status: Literal["draft", "review", "complete"] = "draft"
    claim_ids: list[str] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)
    citation_keys: list[str] = Field(default_factory=list)
