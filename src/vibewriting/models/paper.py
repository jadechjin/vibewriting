"""Paper metadata and structure models."""

from __future__ import annotations

from pydantic import ConfigDict, Field

from .base import BaseEntity


class Paper(BaseEntity):
    """Academic paper metadata."""

    model_config = ConfigDict(extra="forbid")

    title: str
    authors: list[str]
    abstract: str
    bib_key: str = Field(pattern=r"^[a-zA-Z0-9_:\-]+$")
    quality_score: float = Field(ge=0, le=10)
    sections: list[str] = Field(default_factory=list)
