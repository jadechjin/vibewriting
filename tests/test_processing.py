"""Tests for data processing: cleaners, transformers, statistics."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from vibewriting.processing.cleaners import (
    convert_types,
    handle_missing,
    read_csv,
    read_json,
)
from vibewriting.processing.statistics import (
    descriptive_stats,
    effect_size,
    hypothesis_test,
)
from vibewriting.processing.transformers import aggregate, feature_engineer, pivot


# ---------------------------------------------------------------------------
# Cleaners
# ---------------------------------------------------------------------------

class TestReadCSV:
    def test_read_utf8(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
        df = read_csv(csv_file)
        assert list(df.columns) == ["a", "b"]
        assert len(df) == 2

    def test_read_latin1_fallback(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_bytes(b"name,value\ncaf\xe9,1\n")
        df = read_csv(csv_file)
        assert len(df) == 1


class TestReadJSON:
    def test_read_records(self, tmp_path):
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps([{"a": 1}, {"a": 2}]))
        df = read_json(json_file)
        assert len(df) == 2


class TestHandleMissing:
    def test_drop(self):
        df = pd.DataFrame({"a": [1, None, 3], "b": [4, 5, None]})
        result = handle_missing(df, "drop")
        assert len(result) == 1
        assert result.iloc[0]["a"] == 1

    def test_fill(self):
        df = pd.DataFrame({"a": [1, None, 3]})
        result = handle_missing(df, "fill", fill_value=0)
        assert result.iloc[1]["a"] == 0

    def test_interpolate(self):
        df = pd.DataFrame({"a": [1.0, None, 3.0]})
        result = handle_missing(df, "interpolate")
        assert result.iloc[1]["a"] == pytest.approx(2.0)

    def test_idempotency(self):
        """Applying handle_missing twice on clean data gives same result."""
        df = pd.DataFrame({"a": [1, 2, 3]})
        r1 = handle_missing(df, "drop")
        r2 = handle_missing(r1, "drop")
        pd.testing.assert_frame_equal(r1, r2)

    def test_does_not_mutate_input(self):
        df = pd.DataFrame({"a": [1, None, 3]})
        original_len = len(df)
        handle_missing(df, "drop")
        assert len(df) == original_len


class TestConvertTypes:
    def test_basic_conversion(self):
        df = pd.DataFrame({"a": ["1", "2", "3"]})
        result = convert_types(df, {"a": "int64"})
        assert result["a"].dtype == np.int64

    def test_unknown_column_ignored(self):
        df = pd.DataFrame({"a": [1]})
        result = convert_types(df, {"b": "float64"})
        assert list(result.columns) == ["a"]


# ---------------------------------------------------------------------------
# Transformers
# ---------------------------------------------------------------------------

class TestAggregate:
    def test_basic_aggregation(self):
        df = pd.DataFrame({
            "group": ["A", "B", "A", "B"],
            "value": [1, 2, 3, 4],
        })
        result = aggregate(df, "group", {"value": "sum"})
        assert len(result) == 2

    def test_deterministic_ordering(self):
        """Repeated calls produce identical output."""
        df = pd.DataFrame({
            "group": ["B", "A", "B", "A"],
            "value": [4, 1, 3, 2],
        })
        r1 = aggregate(df, "group", {"value": "mean"})
        r2 = aggregate(df, "group", {"value": "mean"})
        pd.testing.assert_frame_equal(r1, r2)


class TestPivot:
    def test_basic_pivot(self):
        df = pd.DataFrame({
            "idx": ["a", "a", "b", "b"],
            "col": ["x", "y", "x", "y"],
            "val": [1, 2, 3, 4],
        })
        result = pivot(df, index="idx", columns="col", values="val")
        assert "x" in result.columns
        assert "y" in result.columns


class TestFeatureEngineer:
    def test_add_feature(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = feature_engineer(df, {
            "a_plus_b": lambda d: d["a"] + d["b"],
        })
        assert "a_plus_b" in result.columns
        assert result["a_plus_b"].tolist() == [5, 7, 9]

    def test_does_not_mutate_input(self):
        df = pd.DataFrame({"a": [1]})
        feature_engineer(df, {"b": lambda d: d["a"] * 2})
        assert "b" not in df.columns


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class TestDescriptiveStats:
    def test_basic_stats(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0]})
        result = descriptive_stats(df)
        assert "x" in result
        assert result["x"]["mean"] == pytest.approx(3.0)
        assert result["x"]["min"] == pytest.approx(1.0)
        assert result["x"]["max"] == pytest.approx(5.0)

    def test_empty_numeric(self):
        df = pd.DataFrame({"name": ["a", "b"]})
        result = descriptive_stats(df)
        assert result == {}

    def test_invariant_stats_consistent(self):
        """Stats values are consistent with the data."""
        df = pd.DataFrame({"x": [10.0, 20.0, 30.0]})
        result = descriptive_stats(df)
        assert result["x"]["min"] <= result["x"]["mean"] <= result["x"]["max"]
        assert result["x"]["q25"] <= result["x"]["q50"] <= result["x"]["q75"]


class TestHypothesisTest:
    def test_ttest_same_dist(self):
        np.random.seed(42)
        a = np.random.normal(0, 1, 100)
        b = np.random.normal(0, 1, 100)
        result = hypothesis_test(a, b, "t-test")
        assert result.test_name == "Independent t-test"
        assert not result.significant  # Same distribution

    def test_ttest_different_dist(self):
        np.random.seed(42)
        a = np.random.normal(0, 1, 100)
        b = np.random.normal(5, 1, 100)
        result = hypothesis_test(a, b, "t-test")
        assert result.significant  # Very different means

    def test_mann_whitney(self):
        np.random.seed(42)
        a = np.random.normal(0, 1, 50)
        b = np.random.normal(3, 1, 50)
        result = hypothesis_test(a, b, "mann-whitney")
        assert result.test_name == "Mann-Whitney U"
        assert result.significant

    def test_unknown_test_raises(self):
        with pytest.raises(ValueError, match="Unknown"):
            hypothesis_test(np.array([1]), np.array([2]), "chi-square")


class TestEffectSize:
    def test_zero_effect(self):
        a = np.array([1.0, 2.0, 3.0])
        d = effect_size(a, a)
        assert d == pytest.approx(0.0)

    def test_positive_effect(self):
        a = np.array([10.0, 11.0, 12.0])
        b = np.array([1.0, 2.0, 3.0])
        d = effect_size(a, b)
        assert d > 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_dataframe_cleaners(self):
        df = pd.DataFrame(columns=["a", "b"])
        result = handle_missing(df, "drop")
        assert len(result) == 0

    def test_single_row(self):
        df = pd.DataFrame({"x": [42.0]})
        result = descriptive_stats(df)
        assert result["x"]["mean"] == pytest.approx(42.0)

    def test_nan_in_stats(self):
        df = pd.DataFrame({"x": [1.0, float("nan"), 3.0]})
        result = descriptive_stats(df)
        assert result["x"]["mean"] == pytest.approx(2.0)
