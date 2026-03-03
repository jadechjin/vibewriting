"""Golden test: snapshot comparison for pipeline determinism.

Runs the full pipeline with fixed seed and compares output to baselines.
If baselines don't exist, generates them (first run).
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

import numpy as np
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
BASELINES_DIR = Path(__file__).parent / "baselines"


def _normalize(text: str) -> str:
    """Normalize text for snapshot comparison.

    Removes timestamps, normalizes path separators, strips trailing whitespace.
    """
    # Remove ISO timestamps
    text = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[.\d]*[Z+\-\d:]*", "<TIMESTAMP>", text)
    # Normalize run_id (hex hashes)
    text = re.sub(r'"run_id":\s*"[a-f0-9]+"', '"run_id": "<RUN_ID>"', text)
    # Normalize path separators
    text = text.replace("\\\\", "/").replace("\\", "/")
    # Remove absolute path prefixes (keep relative from output dir)
    text = re.sub(r"[A-Z]:/[^\"]+/(output/)", r"\1", text)
    text = re.sub(r"/tmp/[^\"]+/(output/)", r"\1", text)
    # Strip trailing whitespace per line
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text


def _run_pipeline(output_dir: Path) -> dict:
    """Run the pipeline with fixed seed and return the context."""
    random.seed(42)
    np.random.seed(42)

    from vibewriting.pipeline.cli import _build_dag

    ctx = {
        "data_dir": str(FIXTURES_DIR),
        "output_dir": str(output_dir),
        "missing_strategy": "drop",
    }
    dag = _build_dag()
    result = dag.run(ctx)
    assert result.failed is None, f"Pipeline failed: {result.error}"
    return result.context


class TestGolden:
    @pytest.fixture(autouse=True)
    def setup_output(self, tmp_path):
        self.output_dir = tmp_path / "output"
        self.ctx = _run_pipeline(self.output_dir)

    def _check_or_generate_baseline(self, name: str, content: str):
        """Compare against baseline or generate it."""
        baseline_path = BASELINES_DIR / name
        normalized = _normalize(content)

        if baseline_path.exists():
            expected = _normalize(baseline_path.read_text(encoding="utf-8"))
            assert normalized == expected, (
                f"Snapshot mismatch for {name}. "
                f"Delete {baseline_path} to regenerate."
            )
        else:
            BASELINES_DIR.mkdir(parents=True, exist_ok=True)
            baseline_path.write_text(content, encoding="utf-8")
            pytest.skip(f"Baseline generated: {baseline_path}")

    def test_asset_manifest_snapshot(self):
        path = Path(self.ctx["asset_manifest_path"])
        self._check_or_generate_baseline("asset_manifest.json", path.read_text())

    def test_statistics_snapshot(self):
        stats = self.ctx.get("statistics", {})
        content = json.dumps(stats, indent=2, sort_keys=True, ensure_ascii=False)
        self._check_or_generate_baseline("statistics.json", content)

    def test_pipeline_completeness(self):
        """All 8 nodes should have executed."""
        # This is verified implicitly by the pipeline not failing,
        # but we check the context keys
        assert "validation_passed" in self.ctx
        assert self.ctx["validation_passed"] is True

    def test_deterministic_statistics(self, tmp_path):
        """Running again produces identical statistics."""
        ctx2 = _run_pipeline(tmp_path / "output2")
        assert self.ctx["statistics"] == ctx2["statistics"]
