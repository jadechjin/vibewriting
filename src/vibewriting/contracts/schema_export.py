"""Export Pydantic models to JSON Schema files.

Usage:
    uv run python -m vibewriting.contracts.schema_export
"""

from __future__ import annotations

import json
from pathlib import Path

from vibewriting.models import (
    Experiment,
    Figure,
    Glossary,
    Paper,
    PaperState,
    Section,
    SymbolTable,
    Table,
)

MODELS = [Paper, Experiment, Figure, Table, Section, PaperState, Glossary, SymbolTable]

SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"


def export_schemas(output_dir: Path | None = None) -> list[Path]:
    """Export all model JSON Schemas to the given directory.

    Returns the list of written schema file paths.
    """
    target = output_dir or SCHEMAS_DIR
    target.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for model in MODELS:
        schema = model.model_json_schema()
        path = target / f"{model.__name__.lower()}.schema.json"
        path.write_text(
            json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(path)

    return written


if __name__ == "__main__":
    paths = export_schemas()
    for p in paths:
        print(f"Exported: {p}")
