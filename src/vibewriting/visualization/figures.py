"""Figure generation with matplotlib.

Each function returns a FigureResult with path, content_hash, and description.
Uses Agg backend to avoid display issues in headless environments.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from vibewriting.config import settings


@dataclass
class FigureResult:
    """Result of figure generation."""

    path: Path
    content_hash: str
    semantic_description: str


def _compute_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _apply_seed() -> None:
    np.random.seed(settings.random_seed)


def _save_and_result(
    fig: plt.Figure,
    output_path: Path,
    description: str,
) -> FigureResult:
    """Save figure and return FigureResult."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_path), bbox_inches="tight", dpi=150)
    plt.close(fig)
    return FigureResult(
        path=output_path,
        content_hash=_compute_hash(output_path),
        semantic_description=description,
    )


def generate_line_chart(
    data: pd.DataFrame,
    config: dict[str, Any],
    output_path: Path | None = None,
) -> FigureResult:
    """Generate a line chart.

    Config keys: x_col, y_col(s), title, x_label, y_label.
    """
    _apply_seed()
    fig, ax = plt.subplots(figsize=config.get("figsize", (8, 5)))

    x_col = config["x_col"]
    y_cols = config.get("y_cols", [config.get("y_col")])

    for y_col in y_cols:
        ax.plot(data[x_col], data[y_col], label=y_col)

    ax.set_xlabel(config.get("x_label", x_col))
    ax.set_ylabel(config.get("y_label", ""))
    ax.set_title(config.get("title", ""))
    if len(y_cols) > 1:
        ax.legend()

    path = output_path or Path(settings.output_dir / "figures" / "line_chart.png")
    return _save_and_result(fig, path, f"Line chart: {config.get('title', '')}")


def generate_bar_chart(
    data: pd.DataFrame,
    config: dict[str, Any],
    output_path: Path | None = None,
) -> FigureResult:
    """Generate a bar chart.

    Config keys: x_col, y_col, title, x_label, y_label.
    """
    _apply_seed()
    fig, ax = plt.subplots(figsize=config.get("figsize", (8, 5)))

    ax.bar(data[config["x_col"]], data[config["y_col"]])
    ax.set_xlabel(config.get("x_label", config["x_col"]))
    ax.set_ylabel(config.get("y_label", config["y_col"]))
    ax.set_title(config.get("title", ""))

    path = output_path or Path(settings.output_dir / "figures" / "bar_chart.png")
    return _save_and_result(fig, path, f"Bar chart: {config.get('title', '')}")


def generate_scatter_plot(
    data: pd.DataFrame,
    config: dict[str, Any],
    output_path: Path | None = None,
) -> FigureResult:
    """Generate a scatter plot.

    Config keys: x_col, y_col, title, x_label, y_label, color_col (optional).
    """
    _apply_seed()
    fig, ax = plt.subplots(figsize=config.get("figsize", (8, 5)))

    kwargs: dict[str, Any] = {}
    if "color_col" in config and config["color_col"] in data.columns:
        kwargs["c"] = data[config["color_col"]]
        kwargs["cmap"] = "viridis"

    ax.scatter(data[config["x_col"]], data[config["y_col"]], **kwargs)
    ax.set_xlabel(config.get("x_label", config["x_col"]))
    ax.set_ylabel(config.get("y_label", config["y_col"]))
    ax.set_title(config.get("title", ""))

    path = output_path or Path(settings.output_dir / "figures" / "scatter_plot.png")
    return _save_and_result(fig, path, f"Scatter plot: {config.get('title', '')}")


def generate_heatmap(
    data: pd.DataFrame,
    config: dict[str, Any],
    output_path: Path | None = None,
) -> FigureResult:
    """Generate a heatmap from numeric columns.

    Config keys: title, cmap, annot.
    """
    _apply_seed()
    fig, ax = plt.subplots(figsize=config.get("figsize", (8, 6)))

    numeric = data.select_dtypes(include=[np.number])
    im = ax.imshow(numeric.values, cmap=config.get("cmap", "viridis"), aspect="auto")
    ax.set_xticks(range(len(numeric.columns)))
    ax.set_xticklabels(numeric.columns, rotation=45, ha="right")
    ax.set_title(config.get("title", ""))
    fig.colorbar(im, ax=ax)

    path = output_path or Path(settings.output_dir / "figures" / "heatmap.png")
    return _save_and_result(fig, path, f"Heatmap: {config.get('title', '')}")
