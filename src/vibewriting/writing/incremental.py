"""Incremental compilation tools for single-section validation."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

DRAFT_PREAMBLE = r"""\documentclass[UTF8, a4paper, 12pt, zihao=-4]{ctexart}

\usepackage[top=2.54cm, bottom=2.54cm, left=3.17cm, right=3.17cm]{geometry}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsthm}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage[numbers,sort&compress]{natbib}
\usepackage[colorlinks=true, linkcolor=blue, citecolor=blue, urlcolor=blue]{hyperref}
\graphicspath{{figures/}}
"""


def generate_draft_main(
    section_tex_file: str,
    title: str = "Draft",
    natbib_style: str = "unsrtnat",
) -> str:
    """Generate draft_main.tex content for single-section compilation.

    Args:
        section_tex_file: Relative path like "sections/introduction.tex"
            (without the .tex extension is also accepted).
        title: Document title for the draft.
        natbib_style: natbib bibliography style (default: unsrtnat).

    Returns:
        Complete .tex content string.
    """
    # Normalize: remove .tex if present for the \input command
    input_path = section_tex_file
    if input_path.endswith(".tex"):
        input_path = input_path[:-4]

    return (
        f"{DRAFT_PREAMBLE}\n"
        f"\\title{{{title}}}\n"
        f"\\date{{\\today}}\n\n"
        f"\\begin{{document}}\n\n"
        f"\\maketitle\n\n"
        f"\\input{{{input_path}}}\n\n"
        f"\\bibliographystyle{{{natbib_style}}}\n"
        f"\\bibliography{{bib/references}}\n\n"
        f"\\end{{document}}\n"
    )


def write_draft_main(
    paper_dir: Path,
    section_tex_file: str,
    title: str = "Draft",
    natbib_style: str = "unsrtnat",
) -> Path:
    """Write draft_main.tex to the paper directory.

    Returns the path to the written file.
    """
    content = generate_draft_main(section_tex_file, title, natbib_style)
    draft_path = paper_dir / "draft_main.tex"
    draft_path.write_text(content, encoding="utf-8")
    return draft_path


def compile_single_section(
    paper_dir: Path,
    section_tex_file: str,
    title: str = "Draft",
    natbib_style: str = "unsrtnat",
) -> tuple[bool, str]:
    """Incrementally compile a single section.

    1. Generate draft_main.tex
    2. Run latexmk (if available)
    3. Return (success, log_output)

    If latexmk is not available, returns (False, "latexmk not found").
    """
    if not shutil.which("latexmk"):
        return False, "latexmk not found"

    draft_path = write_draft_main(paper_dir, section_tex_file, title, natbib_style)

    try:
        result = subprocess.run(
            [
                "latexmk",
                "-xelatex",
                "-interaction=nonstopmode",
                "-file-line-error",
                f"-outdir={paper_dir / 'build'}",
                str(draft_path),
            ],
            capture_output=True,
            text=True,
            cwd=str(paper_dir),
            timeout=120,
        )
        log_output = result.stdout + "\n" + result.stderr
        return result.returncode == 0, log_output
    except subprocess.TimeoutExpired:
        return False, "Compilation timed out after 120 seconds"
    except Exception as exc:
        return False, f"Compilation error: {exc}"


def cleanup_draft(paper_dir: Path) -> None:
    """Remove draft_main.tex and its compilation artifacts."""
    draft_main = paper_dir / "draft_main.tex"
    if draft_main.exists():
        draft_main.unlink()

    # Clean build artifacts for draft_main
    build_dir = paper_dir / "build"
    if build_dir.exists():
        for pattern in ["draft_main.*"]:
            for f in build_dir.glob(pattern):
                f.unlink(missing_ok=True)
