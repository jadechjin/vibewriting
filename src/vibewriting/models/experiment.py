"""Experiment data models."""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field

from .base import BaseEntity


class Experiment(BaseEntity):
    """Experiment run configuration and results."""

    model_config = ConfigDict(extra="forbid")

    experiment_id: str
    config: dict[str, Any] = Field(default_factory=dict)
    results: dict[str, Any] = Field(default_factory=dict)
    data_fingerprint: str = ""
    asset_ids: list[str] = Field(default_factory=list)
