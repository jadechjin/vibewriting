"""Tests for pipeline: DAG runner, nodes, and end-to-end."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from vibewriting.pipeline.dag import CycleDetectedError, DAGNode, DAGResult, DAGRunner


# ---------------------------------------------------------------------------
# DAG Runner
# ---------------------------------------------------------------------------

class TestDAGRunner:
    def test_empty_dag(self):
        runner = DAGRunner()
        result = runner.run()
        assert result.completed == []
        assert result.failed is None

    def test_single_node(self):
        runner = DAGRunner()
        runner.add_node(DAGNode("a", lambda ctx: {**ctx, "a": True}))
        result = runner.run()
        assert result.completed == ["a"]
        assert result.context["a"] is True

    def test_linear_chain(self):
        runner = DAGRunner()
        runner.add_node(DAGNode("a", lambda ctx: {**ctx, "order": ctx.get("order", []) + ["a"]}))
        runner.add_node(DAGNode("b", lambda ctx: {**ctx, "order": ctx["order"] + ["b"]}, depends_on=["a"]))
        runner.add_node(DAGNode("c", lambda ctx: {**ctx, "order": ctx["order"] + ["c"]}, depends_on=["b"]))
        result = runner.run()
        assert result.context["order"] == ["a", "b", "c"]

    def test_diamond_dependency(self):
        """A -> B, A -> C, B+C -> D."""
        runner = DAGRunner()
        runner.add_node(DAGNode("a", lambda ctx: {**ctx, "a": 1}))
        runner.add_node(DAGNode("b", lambda ctx: {**ctx, "b": ctx["a"] + 1}, depends_on=["a"]))
        runner.add_node(DAGNode("c", lambda ctx: {**ctx, "c": ctx["a"] + 2}, depends_on=["a"]))
        runner.add_node(DAGNode("d", lambda ctx: {**ctx, "d": ctx["b"] + ctx["c"]}, depends_on=["b", "c"]))
        result = runner.run()
        assert result.context["d"] == 5  # (1+1) + (1+2) = 5

    def test_cycle_detection(self):
        runner = DAGRunner()
        runner.add_node(DAGNode("a", lambda ctx: ctx, depends_on=["b"]))
        runner.add_node(DAGNode("b", lambda ctx: ctx, depends_on=["a"]))
        with pytest.raises(CycleDetectedError):
            runner.run()

    def test_unknown_dependency(self):
        runner = DAGRunner()
        runner.add_node(DAGNode("a", lambda ctx: ctx, depends_on=["missing"]))
        with pytest.raises(ValueError, match="unknown node"):
            runner.run()

    def test_failure_stops_execution(self):
        def fail_node(ctx):
            raise RuntimeError("intentional failure")

        runner = DAGRunner()
        runner.add_node(DAGNode("a", lambda ctx: {**ctx, "a": True}))
        runner.add_node(DAGNode("b", fail_node, depends_on=["a"]))
        runner.add_node(DAGNode("c", lambda ctx: {**ctx, "c": True}, depends_on=["b"]))
        result = runner.run()
        assert result.completed == ["a"]
        assert result.failed == "b"
        assert "intentional failure" in result.error
        assert "c" not in result.context

    def test_topological_sort_determinism(self):
        """Same DAG always produces the same execution order."""
        def make_runner():
            r = DAGRunner()
            r.add_node(DAGNode("x", lambda ctx: {**ctx, "x": 1}))
            r.add_node(DAGNode("y", lambda ctx: {**ctx, "y": 1}))
            r.add_node(DAGNode("z", lambda ctx: {**ctx, "z": 1}, depends_on=["x", "y"]))
            return r

        r1 = make_runner().run()
        r2 = make_runner().run()
        assert r1.completed == r2.completed


# ---------------------------------------------------------------------------
# End-to-end pipeline with sample data
# ---------------------------------------------------------------------------

class TestPipelineE2E:
    @pytest.fixture
    def sample_data_dir(self, tmp_path):
        data_dir = tmp_path / "raw"
        data_dir.mkdir()
        df = pd.DataFrame({
            "x": range(1, 11),
            "y": [2.0, 4.0, 1.0, 3.0, 5.0, 7.0, 6.0, 8.0, 9.0, 10.0],
            "z": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
        })
        df.to_csv(data_dir / "sample_data.csv", index=False)
        return data_dir

    def test_full_pipeline(self, tmp_path, sample_data_dir):
        from vibewriting.pipeline.cli import _build_dag

        output_dir = tmp_path / "output"
        ctx = {
            "data_dir": str(sample_data_dir),
            "output_dir": str(output_dir),
        }
        dag = _build_dag()
        result = dag.run(ctx)

        assert result.failed is None
        assert len(result.completed) == 8
        assert result.context.get("validation_passed") is True

        # Check manifests exist
        asset_path = Path(result.context["asset_manifest_path"])
        run_path = Path(result.context["run_manifest_path"])
        assert asset_path.exists()
        assert run_path.exists()

        # Validate manifest content
        asset_manifest = json.loads(asset_path.read_text())
        assert asset_manifest["count"] >= 0
        run_manifest = json.loads(run_path.read_text())
        assert "run_id" in run_manifest

    def test_pipeline_determinism(self, tmp_path, sample_data_dir):
        """Running pipeline twice with same seed produces same statistics."""
        import random
        import numpy as np
        from vibewriting.pipeline.cli import _build_dag

        results = []
        for i in range(2):
            random.seed(42)
            np.random.seed(42)
            output_dir = tmp_path / f"run{i}"
            ctx = {
                "data_dir": str(sample_data_dir),
                "output_dir": str(output_dir),
            }
            dag = _build_dag()
            result = dag.run(ctx)
            results.append(result)

        assert results[0].context["statistics"] == results[1].context["statistics"]
