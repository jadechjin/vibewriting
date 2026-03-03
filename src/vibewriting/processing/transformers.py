"""Data transformation utilities.

All functions are pure and enforce deterministic output ordering.
"""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd


def aggregate(
    df: pd.DataFrame,
    group_by: str | list[str],
    agg_funcs: dict[str, str | list[str]],
) -> pd.DataFrame:
    """Group and aggregate a DataFrame.

    Always sorts results and resets index for deterministic output.
    """
    result = df.groupby(group_by, sort=True).agg(agg_funcs)
    # Flatten MultiIndex columns if needed
    if isinstance(result.columns, pd.MultiIndex):
        result.columns = ["_".join(col).strip("_") for col in result.columns]
    return result.sort_values(by=result.columns[0]).reset_index(drop=False)


def pivot(
    df: pd.DataFrame,
    index: str,
    columns: str,
    values: str,
) -> pd.DataFrame:
    """Pivot a DataFrame with deterministic column ordering."""
    result = df.pivot_table(index=index, columns=columns, values=values, aggfunc="first")
    result = result.sort_index()
    result.columns = [str(c) for c in result.columns]
    return result.reset_index()


def feature_engineer(
    df: pd.DataFrame,
    features: dict[str, Callable[[pd.DataFrame], pd.Series]],
) -> pd.DataFrame:
    """Add computed feature columns to a DataFrame.

    Args:
        df: Input DataFrame (not modified).
        features: Dict mapping new column names to functions that
                  take a DataFrame and return a Series.

    Returns:
        New DataFrame with added feature columns.
    """
    result = df.copy()
    for name, fn in features.items():
        result[name] = fn(result)
    return result
