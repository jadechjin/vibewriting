"""Table asset model."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field

from .base import AssetBase


class Table(AssetBase):
    """Table asset with column metadata."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["table"] = "table"
    columns: list[str] = Field(default_factory=list)
    row_count: int = Field(ge=0, default=0)
    template_name: str = ""
