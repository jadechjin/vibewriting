"""Figure asset model."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict

from .base import AssetBase


class Figure(AssetBase):
    """Figure asset with chart metadata."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["figure"] = "figure"
    chart_type: Literal["line", "bar", "scatter", "heatmap"]
    data_source: str
    x_label: str
    y_label: str
