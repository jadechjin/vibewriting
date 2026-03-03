"""Data cleaning utilities.

All functions are pure — they return new DataFrames without modifying inputs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pandas as pd


def read_csv(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read a CSV file with encoding detection, normalizing to UTF-8.

    Falls back to latin-1 if UTF-8 decoding fails.
    """
    path = Path(path)
    try:
        return pd.read_csv(path, encoding="utf-8", **kwargs)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", **kwargs)


def read_json(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read a JSON file into a DataFrame."""
    path = Path(path)
    return pd.read_json(path, **kwargs)


def handle_missing(
    df: pd.DataFrame,
    strategy: Literal["drop", "fill", "interpolate"] = "drop",
    fill_value: Any = 0,
) -> pd.DataFrame:
    """Handle missing values using the specified strategy.

    Args:
        df: Input DataFrame (not modified).
        strategy: One of 'drop', 'fill', 'interpolate'.
        fill_value: Value to use when strategy is 'fill'.

    Returns:
        New DataFrame with missing values handled.
    """
    if strategy == "drop":
        return df.dropna().reset_index(drop=True)
    elif strategy == "fill":
        return df.fillna(fill_value)
    elif strategy == "interpolate":
        return df.interpolate().ffill().bfill()
    else:
        raise ValueError(f"Unknown strategy: {strategy}")


def convert_types(
    df: pd.DataFrame, type_map: dict[str, str]
) -> pd.DataFrame:
    """Convert column types according to the provided mapping.

    Args:
        df: Input DataFrame (not modified).
        type_map: Dict mapping column names to target types (e.g. {"age": "int64"}).

    Returns:
        New DataFrame with converted types.
    """
    result = df.copy()
    for col, dtype in type_map.items():
        if col in result.columns:
            result[col] = result[col].astype(dtype)
    return result
