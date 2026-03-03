"""Shared fixtures for latex module tests."""

from __future__ import annotations

import pytest
from pathlib import Path


@pytest.fixture
def tmp_paper_dir(tmp_path: Path) -> Path:
    paper = tmp_path / "paper"
    paper.mkdir()
    sections = paper / "sections"
    sections.mkdir()
    (paper / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}\n",
        encoding="utf-8",
    )
    (sections / "intro.tex").write_text(
        "\\section{Introduction}\nLine 1\nLine 2\nLine 3\nLine 4\nLine 5\n",
        encoding="utf-8",
    )
    return paper
