"""CLI entry point for the data processing pipeline.

Usage:
    uv run python -m vibewriting.pipeline.cli --help
    uv run python -m vibewriting.pipeline.cli run --data-dir data/raw --output-dir output
"""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import typer

from vibewriting.config import settings
from vibewriting.pipeline.dag import DAGNode, DAGRunner
from vibewriting.pipeline.nodes import (
    build_manifests,
    clean_data,
    compute_statistics,
    generate_figures,
    generate_tables,
    load_data,
    transform_data,
    validate_contracts,
)

app = typer.Typer(help="vibewriting data processing pipeline")


def _build_dag() -> DAGRunner:
    """Build the processing DAG with all nodes."""
    runner = DAGRunner()
    runner.add_node(DAGNode("load_data", load_data))
    runner.add_node(DAGNode("clean_data", clean_data, depends_on=["load_data"]))
    runner.add_node(DAGNode("transform_data", transform_data, depends_on=["clean_data"]))
    runner.add_node(DAGNode("compute_statistics", compute_statistics, depends_on=["transform_data"]))
    runner.add_node(DAGNode("generate_figures", generate_figures, depends_on=["transform_data"]))
    runner.add_node(DAGNode("generate_tables", generate_tables, depends_on=["compute_statistics"]))
    runner.add_node(DAGNode("build_manifests", build_manifests, depends_on=["generate_figures", "generate_tables"]))
    runner.add_node(DAGNode("validate_contracts", validate_contracts, depends_on=["build_manifests"]))
    return runner


@app.command()
def run(
    data_dir: Path = typer.Option(
        None,
        help="Path to raw data directory",
    ),
    output_dir: Path = typer.Option(
        None,
        help="Path to output directory",
    ),
    seed: int = typer.Option(
        None,
        help="Random seed for reproducibility",
    ),
) -> None:
    """Run the full data processing pipeline."""
    effective_seed = seed if seed is not None else settings.random_seed
    random.seed(effective_seed)
    np.random.seed(effective_seed)

    context = {
        "data_dir": str(data_dir or settings.data_dir / "raw"),
        "output_dir": str(output_dir or settings.output_dir),
        "seed": effective_seed,
    }

    dag = _build_dag()
    result = dag.run(context)

    if result.failed:
        typer.echo(f"Pipeline failed at node '{result.failed}': {result.error}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Pipeline completed successfully. Nodes executed: {len(result.completed)}")
    typer.echo(f"Asset manifest: {result.context.get('asset_manifest_path', 'N/A')}")
    typer.echo(f"Run manifest: {result.context.get('run_manifest_path', 'N/A')}")


if __name__ == "__main__":
    app()
