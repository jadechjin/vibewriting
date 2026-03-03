"""Tests for visualization: figures, tables, pgf_export."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import shutil

from vibewriting.visualization.figures import (
    FigureResult,
    generate_bar_chart,
    generate_heatmap,
    generate_line_chart,
    generate_scatter_plot,
)
from vibewriting.visualization.pgf_export import export_pgf
from vibewriting.visualization.tables import TableResult, generate_latex_table


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "x": [1, 2, 3, 4, 5],
        "y": [2.0, 4.0, 1.0, 3.0, 5.0],
        "z": [10.0, 20.0, 30.0, 40.0, 50.0],
        "group": ["A", "B", "A", "B", "A"],
    })


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

class TestLineChart:
    def test_generates_file(self, tmp_path, sample_df):
        result = generate_line_chart(
            sample_df,
            {"x_col": "x", "y_col": "y", "title": "Test Line"},
            output_path=tmp_path / "line.png",
        )
        assert isinstance(result, FigureResult)
        assert result.path.exists()
        assert len(result.content_hash) == 64  # SHA-256

    def test_multi_y(self, tmp_path, sample_df):
        result = generate_line_chart(
            sample_df,
            {"x_col": "x", "y_cols": ["y", "z"], "title": "Multi"},
            output_path=tmp_path / "multi.png",
        )
        assert result.path.exists()


class TestBarChart:
    def test_generates_file(self, tmp_path, sample_df):
        result = generate_bar_chart(
            sample_df,
            {"x_col": "group", "y_col": "y", "title": "Test Bar"},
            output_path=tmp_path / "bar.png",
        )
        assert result.path.exists()


class TestScatterPlot:
    def test_generates_file(self, tmp_path, sample_df):
        result = generate_scatter_plot(
            sample_df,
            {"x_col": "x", "y_col": "y", "title": "Test Scatter"},
            output_path=tmp_path / "scatter.png",
        )
        assert result.path.exists()


class TestHeatmap:
    def test_generates_file(self, tmp_path, sample_df):
        result = generate_heatmap(
            sample_df,
            {"title": "Test Heatmap"},
            output_path=tmp_path / "heat.png",
        )
        assert result.path.exists()


class TestFigureIdempotency:
    def test_same_data_same_hash(self, tmp_path, sample_df):
        """Same input data and seed should produce identical output."""
        r1 = generate_line_chart(
            sample_df,
            {"x_col": "x", "y_col": "y"},
            output_path=tmp_path / "a.png",
        )
        r2 = generate_line_chart(
            sample_df,
            {"x_col": "x", "y_col": "y"},
            output_path=tmp_path / "b.png",
        )
        assert r1.content_hash == r2.content_hash


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

class TestTables:
    def test_generates_tex_file(self, tmp_path, sample_df):
        result = generate_latex_table(
            sample_df,
            config={"caption": "Test Table", "label": "tab:test"},
            output_path=tmp_path / "table.tex",
        )
        assert isinstance(result, TableResult)
        assert result.path.exists()
        content = result.path.read_text()
        assert "\\toprule" in content
        assert "\\bottomrule" in content

    def test_float_precision(self, tmp_path):
        df = pd.DataFrame({"val": [1.123456789]})
        result = generate_latex_table(
            df,
            output_path=tmp_path / "prec.tex",
        )
        content = result.path.read_text()
        # Should be rounded to 6 decimal places
        assert "1.123457" in content


# ---------------------------------------------------------------------------
# PGF Export
# ---------------------------------------------------------------------------

_HAS_TEXLIVE = shutil.which("xelatex") is not None


@pytest.mark.skipif(not _HAS_TEXLIVE, reason="TeX Live not installed")
class TestPGFExport:
    def test_exports_pgf_and_pdf(self, tmp_path):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        pgf_path, pdf_path, content_hash = export_pgf(fig, tmp_path / "test")
        plt.close(fig)
        assert pgf_path.exists()
        assert pdf_path.exists()
        assert len(content_hash) == 64

    def test_idempotency(self, tmp_path):
        """Same figure exported twice produces same PGF hash."""
        fig1, ax1 = plt.subplots()
        ax1.plot([1, 2, 3], [1, 4, 9])
        _, _, hash1 = export_pgf(fig1, tmp_path / "a")
        plt.close(fig1)

        fig2, ax2 = plt.subplots()
        ax2.plot([1, 2, 3], [1, 4, 9])
        _, _, hash2 = export_pgf(fig2, tmp_path / "b")
        plt.close(fig2)

        assert hash1 == hash2
