from __future__ import annotations

import subprocess
from pathlib import Path

from vibewriting.rendering.docx_renderer import (
    build_markdown_from_ir,
    render_docx_from_ir,
)
from vibewriting.rendering.ir import DocumentIR, ParagraphBlockIR, SectionIR


def _make_document_ir() -> DocumentIR:
    return DocumentIR(
        paper_id="p001",
        title="Docx Export Test",
        topic="Testing",
        sections=[
            SectionIR(
                section_id="intro",
                title="引言",
                source_tex_file="sections/introduction.tex",
                citation_keys=["smith2024alpha"],
                blocks=[
                    ParagraphBlockIR(
                        text="Reference \\citep{smith2024alpha}.",
                        citation_keys=["smith2024alpha"],
                    )
                ],
            )
        ],
    )


def test_build_markdown_from_ir_converts_citations() -> None:
    md = build_markdown_from_ir(_make_document_ir())
    assert "# Docx Export Test" in md
    assert "## 引言" in md
    assert "[@smith2024alpha]" in md


def test_render_docx_success(monkeypatch, tmp_path: Path) -> None:
    recorded: dict[str, list[str]] = {}

    def _fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        recorded["cmd"] = args[0]
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    ir = _make_document_ir()
    output_path = tmp_path / "paper" / "build" / "main.docx"
    bib_path = tmp_path / "paper" / "bib" / "references.bib"
    bib_path.parent.mkdir(parents=True, exist_ok=True)
    bib_path.write_text("", encoding="utf-8")

    result = render_docx_from_ir(
        ir,
        output_path,
        working_dir=tmp_path,
        bibliography_path=bib_path,
    )

    assert result.success is True
    assert result.markdown_path.exists()
    assert "pandoc" in recorded["cmd"][0]
    assert "--bibliography" in recorded["cmd"]


def test_render_docx_when_pandoc_missing(monkeypatch, tmp_path: Path) -> None:
    def _missing(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError("pandoc")

    monkeypatch.setattr(subprocess, "run", _missing)

    result = render_docx_from_ir(
        _make_document_ir(),
        tmp_path / "paper" / "build" / "main.docx",
        working_dir=tmp_path,
    )

    assert result.success is False
    assert "pandoc not found" in result.message

