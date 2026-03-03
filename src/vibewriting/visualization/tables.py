"""LaTeX table generation using Jinja2 templates.

Generates .tex table files in booktabs style.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from vibewriting.config import settings

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


@dataclass
class TableResult:
    """Result of table generation."""

    path: Path
    content_hash: str
    semantic_description: str


def _compute_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get_env(templates_dir: Path | None = None) -> Environment:
    """Create a Jinja2 environment for LaTeX templates."""
    tpl_dir = templates_dir or TEMPLATES_DIR
    return Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape([]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def generate_latex_table(
    data: pd.DataFrame,
    template_name: str = "booktabs.tex.j2",
    config: dict[str, Any] | None = None,
    output_path: Path | None = None,
    templates_dir: Path | None = None,
) -> TableResult:
    """Generate a LaTeX table from a DataFrame using a Jinja2 template.

    Args:
        data: DataFrame to render.
        template_name: Name of the template file.
        config: Optional config dict with keys: caption, label, title.
        output_path: Where to write the .tex file.
        templates_dir: Override the templates directory.

    Returns:
        TableResult with path, hash, and description.
    """
    config = config or {}
    env = _get_env(templates_dir)
    template = env.get_template(template_name)

    precision = settings.float_precision
    formatted_data = data.copy()
    for col in formatted_data.select_dtypes(include=["float"]).columns:
        formatted_data[col] = formatted_data[col].map(lambda x: f"{x:.{precision}f}")

    rendered = template.render(
        columns=list(formatted_data.columns),
        rows=formatted_data.values.tolist(),
        caption=config.get("caption", ""),
        label=config.get("label", ""),
        title=config.get("title", ""),
        column_count=len(formatted_data.columns),
    )

    path = output_path or Path(settings.output_dir / "tables" / "table.tex")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")

    return TableResult(
        path=path,
        content_hash=_compute_hash(path),
        semantic_description=f"Table: {config.get('caption', 'data table')}",
    )
