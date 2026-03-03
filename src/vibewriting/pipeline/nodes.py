"""DAG node definitions for the data processing pipeline.

Each node is a pure function: (context: dict) -> dict.
Nodes read from and write to the shared context dict.
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from vibewriting.config import settings
from vibewriting.processing.cleaners import handle_missing, read_csv
from vibewriting.processing.statistics import descriptive_stats
from vibewriting.processing.transformers import aggregate
from vibewriting.visualization.figures import (
    generate_bar_chart,
    generate_line_chart,
)
from vibewriting.visualization.tables import generate_latex_table


def load_data(ctx: dict[str, Any]) -> dict[str, Any]:
    """Load raw data from CSV files in data_dir."""
    data_dir = Path(ctx.get("data_dir", settings.data_dir / "raw"))
    dfs: dict[str, Any] = {}
    for csv_file in sorted(data_dir.glob("*.csv")):
        dfs[csv_file.stem] = read_csv(csv_file)
    return {**ctx, "raw_data": dfs}


def clean_data(ctx: dict[str, Any]) -> dict[str, Any]:
    """Clean all loaded DataFrames: handle missing values."""
    raw = ctx.get("raw_data", {})
    cleaned = {}
    strategy = ctx.get("missing_strategy", "drop")
    for name, df in raw.items():
        cleaned[name] = handle_missing(df, strategy=strategy)
    return {**ctx, "cleaned_data": cleaned}


def transform_data(ctx: dict[str, Any]) -> dict[str, Any]:
    """Transform cleaned data: sort and reset index for determinism."""
    cleaned = ctx.get("cleaned_data", {})
    transformed = {}
    for name, df in cleaned.items():
        if not df.empty:
            transformed[name] = (
                df.sort_values(by=df.columns[0]).reset_index(drop=True)
            )
        else:
            transformed[name] = df
    return {**ctx, "transformed_data": transformed}


def compute_statistics(ctx: dict[str, Any]) -> dict[str, Any]:
    """Compute descriptive statistics for all datasets."""
    data = ctx.get("transformed_data", {})
    all_stats = {}
    for name, df in data.items():
        all_stats[name] = descriptive_stats(df)
    return {**ctx, "statistics": all_stats}


def generate_figures(ctx: dict[str, Any]) -> dict[str, Any]:
    """Generate figures from transformed data."""
    data = ctx.get("transformed_data", {})
    output_dir = Path(ctx.get("output_dir", settings.output_dir)) / "figures"
    figure_results = []

    for name, df in data.items():
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) >= 2:
            result = generate_line_chart(
                df,
                {
                    "x_col": numeric_cols[0],
                    "y_col": numeric_cols[1],
                    "title": f"{name}: {numeric_cols[1]} vs {numeric_cols[0]}",
                    "x_label": numeric_cols[0],
                    "y_label": numeric_cols[1],
                },
                output_path=output_dir / f"{name}_line.png",
            )
            figure_results.append({
                "asset_id": f"ASSET-{datetime.now(UTC).year}-{len(figure_results)+1:03d}",
                "kind": "figure",
                "path": str(result.path),
                "content_hash": result.content_hash,
                "semantic_description": result.semantic_description,
            })

    return {**ctx, "figure_results": figure_results}


def generate_tables(ctx: dict[str, Any]) -> dict[str, Any]:
    """Generate LaTeX tables from statistics."""
    stats = ctx.get("statistics", {})
    output_dir = Path(ctx.get("output_dir", settings.output_dir)) / "tables"
    table_results = []

    import pandas as pd

    for name, stat_dict in stats.items():
        if not stat_dict:
            continue
        rows = []
        for col, metrics in stat_dict.items():
            rows.append({"column": col, **metrics})
        stats_df = pd.DataFrame(rows)

        result = generate_latex_table(
            stats_df,
            config={"caption": f"Descriptive statistics for {name}", "label": f"tab:{name}"},
            output_path=output_dir / f"{name}_stats.tex",
        )
        asset_idx = len(ctx.get("figure_results", [])) + len(table_results) + 1
        table_results.append({
            "asset_id": f"ASSET-{datetime.now(UTC).year}-{asset_idx:03d}",
            "kind": "table",
            "path": str(result.path),
            "content_hash": result.content_hash,
            "semantic_description": result.semantic_description,
        })

    return {**ctx, "table_results": table_results}


def build_manifests(ctx: dict[str, Any]) -> dict[str, Any]:
    """Build asset_manifest.json and run_manifest.json."""
    output_dir = Path(ctx.get("output_dir", settings.output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Asset manifest
    assets = ctx.get("figure_results", []) + ctx.get("table_results", [])
    asset_manifest = {"assets": assets, "count": len(assets)}
    asset_path = output_dir / "asset_manifest.json"
    asset_path.write_text(
        json.dumps(asset_manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Run manifest
    run_manifest = {
        "run_id": hashlib.sha256(
            f"{datetime.now(UTC).isoformat()}-{settings.random_seed}".encode()
        ).hexdigest()[:16],
        "timestamp": datetime.now(UTC).isoformat(),
        "seed": settings.random_seed,
        "float_precision": settings.float_precision,
        "data_dir": str(ctx.get("data_dir", "")),
        "output_dir": str(output_dir),
        "asset_count": len(assets),
    }
    run_path = output_dir / "run_manifest.json"
    run_path.write_text(
        json.dumps(run_manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return {**ctx, "asset_manifest_path": str(asset_path), "run_manifest_path": str(run_path)}


def validate_contracts(ctx: dict[str, Any]) -> dict[str, Any]:
    """Validate all produced manifests against schemas."""
    # This is a placeholder that validates files exist and are valid JSON
    for key in ("asset_manifest_path", "run_manifest_path"):
        path = ctx.get(key)
        if path:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"Invalid manifest at {path}")
    return {**ctx, "validation_passed": True}
