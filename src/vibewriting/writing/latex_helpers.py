"""LaTeX helper utilities for CLAIM_ID annotations, citations, and parsing."""

from __future__ import annotations

import re


# Compiled regexes
_CLAIM_ANNOTATION_RE = re.compile(r"%%\s*CLAIM_ID:\s*(EC-\d{4}-\d{3})")
_CITE_RE = re.compile(r"\\cite[pt]\{([^}]+)\}")
_LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
_REF_RE = re.compile(r"\\(?:eq)?ref\{([^}]+)\}")
_COMMAND_RE = re.compile(r"\\[a-zA-Z]+(?:\[[^\]]*\])?\{[^}]*\}")
_COMMENT_RE = re.compile(r"(?<!%)%(?!%).*$", re.MULTILINE)


# ── CLAIM_ID annotation management ──

def inject_claim_annotation(line: str, claim_id: str) -> str:
    """Add or replace %% CLAIM_ID annotation at end of a LaTeX line.

    If line already has a CLAIM_ID annotation, replace it.
    Otherwise append it.
    """
    stripped = _CLAIM_ANNOTATION_RE.sub("", line).rstrip()
    return f"{stripped} %% CLAIM_ID: {claim_id}"


def extract_claim_annotations(tex_content: str) -> dict[int, str]:
    """Extract all CLAIM_ID annotations from .tex content.

    Returns: {line_number (1-based): claim_id} mapping.
    """
    result = {}
    for i, line in enumerate(tex_content.splitlines(), start=1):
        m = _CLAIM_ANNOTATION_RE.search(line)
        if m:
            result[i] = m.group(1)
    return result


def strip_claim_annotations(tex_content: str) -> str:
    """Remove all %% CLAIM_ID annotations from .tex content."""
    lines = []
    for line in tex_content.splitlines():
        cleaned = _CLAIM_ANNOTATION_RE.sub("", line).rstrip()
        lines.append(cleaned)
    return "\n".join(lines)


# ── Citation formatting ──

def format_citation(bib_key: str, style: str = "citep") -> str:
    r"""Generate \citep{key} or \citet{key}."""
    if style not in ("citep", "citet"):
        raise ValueError(f"Invalid citation style: {style}")
    return f"\\{style}{{{bib_key}}}"


def format_figure_ref(label: str) -> str:
    r"""Generate \ref{fig:label}."""
    if label.startswith("fig:"):
        return f"\\ref{{{label}}}"
    return f"\\ref{{fig:{label}}}"


def format_table_ref(label: str) -> str:
    r"""Generate \ref{tab:label}."""
    if label.startswith("tab:"):
        return f"\\ref{{{label}}}"
    return f"\\ref{{tab:{label}}}"


# ── LaTeX paragraph tools ──

def split_into_paragraphs(tex_content: str) -> list[str]:
    """Split LaTeX content into paragraphs by blank lines.

    Preserves comment lines within paragraphs.
    Returns non-empty paragraphs only.
    """
    paragraphs = re.split(r"\n\s*\n", tex_content)
    return [p.strip() for p in paragraphs if p.strip()]


def count_words_in_tex(tex_content: str) -> int:
    """Count words in .tex content, excluding commands and comments.

    Removes LaTeX commands, comments (single %), and whitespace,
    then counts remaining words.
    """
    # Remove comments (but not %% annotations)
    text = _COMMENT_RE.sub("", tex_content)
    # Remove commands
    text = _COMMAND_RE.sub(" ", text)
    # Remove remaining braces and backslashes
    text = re.sub(r"[{}\\]", " ", text)
    # Count words
    words = text.split()
    return len(words)


def extract_all_labels(tex_content: str) -> set[str]:
    r"""Extract all labels from \label{} commands."""
    return set(_LABEL_RE.findall(tex_content))


def extract_all_refs(tex_content: str) -> set[str]:
    r"""Extract all referenced labels from \ref{} and \eqref{} commands."""
    return set(_REF_RE.findall(tex_content))
