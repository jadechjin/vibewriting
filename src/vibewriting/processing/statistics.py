"""Statistical analysis utilities.

All floating-point outputs are rounded to VW_FLOAT_PRECISION digits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from vibewriting.config import settings

_PRECISION = settings.float_precision


def _round(value: float) -> float:
    return round(float(value), _PRECISION)


def descriptive_stats(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Compute descriptive statistics for all numeric columns.

    Returns dict mapping column name -> {mean, std, min, max, q25, q50, q75}.
    """
    result: dict[str, dict[str, float]] = {}
    numeric = df.select_dtypes(include=[np.number])
    for col in sorted(numeric.columns):
        series = numeric[col].dropna()
        if series.empty:
            continue
        result[col] = {
            "mean": _round(series.mean()),
            "std": _round(series.std()),
            "min": _round(series.min()),
            "max": _round(series.max()),
            "q25": _round(series.quantile(0.25)),
            "q50": _round(series.quantile(0.50)),
            "q75": _round(series.quantile(0.75)),
        }
    return result


@dataclass
class TestResult:
    """Result of a statistical hypothesis test."""

    test_name: str
    statistic: float
    p_value: float
    significant: bool


def hypothesis_test(
    group_a: pd.Series | np.ndarray,
    group_b: pd.Series | np.ndarray,
    test_type: str = "t-test",
    alpha: float = 0.05,
) -> TestResult:
    """Run a hypothesis test between two groups.

    Args:
        group_a: First sample.
        group_b: Second sample.
        test_type: One of 't-test', 'mann-whitney'.
        alpha: Significance level.

    Returns:
        TestResult with statistic, p-value, and significance.
    """
    a = np.asarray(group_a, dtype=float)
    b = np.asarray(group_b, dtype=float)

    if test_type == "t-test":
        stat, p = stats.ttest_ind(a, b)
        name = "Independent t-test"
    elif test_type == "mann-whitney":
        stat, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        name = "Mann-Whitney U"
    else:
        raise ValueError(f"Unknown test type: {test_type}")

    return TestResult(
        test_name=name,
        statistic=_round(stat),
        p_value=_round(p),
        significant=p < alpha,
    )


def effect_size(
    group_a: pd.Series | np.ndarray,
    group_b: pd.Series | np.ndarray,
) -> float:
    """Compute Cohen's d effect size between two groups."""
    a = np.asarray(group_a, dtype=float)
    b = np.asarray(group_b, dtype=float)
    pooled_std = np.sqrt((a.std() ** 2 + b.std() ** 2) / 2)
    if pooled_std == 0:
        return 0.0
    return _round((a.mean() - b.mean()) / pooled_std)
