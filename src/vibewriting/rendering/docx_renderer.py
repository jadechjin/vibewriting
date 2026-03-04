"""DOCX renderer based on Pandoc."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from vibewriting.rendering.ir import DocumentIR

_CLAIM_RE = re.compile(r"%%\s*CLAIM_ID:\s*EC-\d{4}-\d{3}")
_CITE_RE = re.compile(r"\\cite[tp]?\{([^}]+)\}")


def _latex_cites_to_pandoc(text: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        keys = [k.strip() for k in match.group(1).split(",") if k.strip()]
        if not keys:
            return ""
        joined = "; ".join(f"@{k}" for k in keys)
        return f"[{joined}]"

    return _CITE_RE.sub(_replace, text)


def _latex_refs_to_plain(text: str) -> str:
    text = re.sub(r"\\(?:eq)?ref\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\\label\{[^}]+\}", "", text)
    return text


def _latex_markup_to_markdown(text: str) -> str:
    text = _CLAIM_RE.sub("", text)
    text = _latex_cites_to_pandoc(text)
    text = _latex_refs_to_plain(text)
    text = text.replace(r"\%", "%")
    text = text.replace(r"\_", "_")
    return text.strip()


def build_markdown_from_ir(document_ir: DocumentIR) -> str:
    """Render DocumentIR into pandoc-friendly markdown."""
    lines: list[str] = [f"# {document_ir.title}", ""]

    for section in document_ir.sections:
        lines.extend([f"## {section.title}", ""])
        if not section.blocks:
            lines.extend(["", ""])
            continue

        for block in section.blocks:
            paragraph = _latex_markup_to_markdown(block.text)
            if paragraph:
                lines.append(paragraph)
                lines.append("")

    return "\n".join(lines).rstrip() + "\n"


@dataclass
class DocxRenderResult:
    """DOCX rendering result."""

    success: bool
    output_path: Path
    markdown_path: Path
    message: str = ""


def render_docx_from_ir(
    document_ir: DocumentIR,
    output_path: Path,
    working_dir: Path,
    *,
    reference_docx: Path | None = None,
    csl_path: Path | None = None,
    bibliography_path: Path | None = None,
) -> DocxRenderResult:
    """Render DOCX via pandoc from a markdown intermediate file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path = output_path.with_suffix(".md")
    markdown_path.write_text(
        build_markdown_from_ir(document_ir),
        encoding="utf-8",
    )

    command = [
        "pandoc",
        str(markdown_path),
        "-o",
        str(output_path),
    ]
    if reference_docx:
        command.extend(["--reference-doc", str(reference_docx)])
    if csl_path:
        command.extend(["--csl", str(csl_path)])
    if bibliography_path:
        command.extend(["--bibliography", str(bibliography_path), "--citeproc"])

    try:
        result = subprocess.run(
            command,
            cwd=str(working_dir),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return DocxRenderResult(
            success=False,
            output_path=output_path,
            markdown_path=markdown_path,
            message="pandoc not found. Install pandoc to enable DOCX export.",
        )

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Unknown pandoc error").strip()
        return DocxRenderResult(
            success=False,
            output_path=output_path,
            markdown_path=markdown_path,
            message=detail,
        )

    return DocxRenderResult(
        success=True,
        output_path=output_path,
        markdown_path=markdown_path,
    )

