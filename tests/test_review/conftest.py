"""Shared fixtures for review module tests."""

from __future__ import annotations

import json
import pytest
from pathlib import Path


@pytest.fixture
def tmp_paper_dir(tmp_path: Path) -> Path:
    paper = tmp_path / "paper"
    paper.mkdir()
    sections = paper / "sections"
    sections.mkdir()
    bib = paper / "bib"
    bib.mkdir()
    (paper / "main.tex").write_text(
        "\\documentclass{article}\n\\author{John Doe}\n"
        "\\begin{document}\n\\input{sections/intro}\n\\end{document}\n",
        encoding="utf-8",
    )
    (sections / "intro.tex").write_text(
        "\\section{Introduction}\nSome claim \\citep{smith2023}.\n"
        "%% CLAIM_ID: EC-0001-001\n",
        encoding="utf-8",
    )
    (bib / "references.bib").write_text(
        "@article{smith2023,\n  author={Smith},\n  title={Test},\n  year={2023},\n}\n",
        encoding="utf-8",
    )
    return paper


@pytest.fixture
def cards_path(tmp_path: Path) -> Path:
    p = tmp_path / "literature_cards.jsonl"
    card = {
        "claim_id": "EC-0001-001",
        "claim_text": "Test claim",
        "bib_key": "smith2023",
        "evidence_type": "empirical",
        "retrieval_source": "manual",
    }
    p.write_text(json.dumps(card) + "\n", encoding="utf-8")
    return p
