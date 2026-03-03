"""PGF export backend for matplotlib figures.

Exports figures as .pgf (LaTeX-native vector) and .pdf files.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt


def _compute_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# PGF rcParams for consistent LaTeX output
PGF_RCPARAMS: dict[str, Any] = {
    "pgf.texsystem": "xelatex",
    "font.family": "serif",
    "text.usetex": False,
    "pgf.rcfonts": True,
}


def export_pgf(
    fig: plt.Figure,
    output_path: Path,
) -> tuple[Path, Path, str]:
    """Export a matplotlib figure as .pgf and .pdf.

    Args:
        fig: The matplotlib Figure to export.
        output_path: Base path (without extension).

    Returns:
        Tuple of (pgf_path, pdf_path, content_hash_of_pgf).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pgf_path = output_path.with_suffix(".pgf")
    pdf_path = output_path.with_suffix(".pdf")

    # Apply PGF settings temporarily
    with matplotlib.rc_context(PGF_RCPARAMS):
        fig.savefig(str(pgf_path), bbox_inches="tight")
        fig.savefig(str(pdf_path), bbox_inches="tight")

    content_hash = _compute_hash(pgf_path)
    return pgf_path, pdf_path, content_hash
