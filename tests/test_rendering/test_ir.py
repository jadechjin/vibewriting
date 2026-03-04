from __future__ import annotations

from pathlib import Path

from vibewriting.models.paper_state import PaperState, SectionState
from vibewriting.rendering.ir import (
    build_document_ir_from_paper_state,
    load_document_ir,
    write_document_ir,
)


def _make_state() -> PaperState:
    return PaperState(
        paper_id="paper-001",
        title="Test Title",
        topic="Test Topic",
        sections=[
            SectionState(
                section_id="introduction",
                title="引言",
                tex_file="sections/introduction.tex",
                citation_keys=[],
            )
        ],
    )


def test_build_document_ir_extracts_citations(tmp_path: Path) -> None:
    paper_dir = tmp_path / "paper"
    section_dir = paper_dir / "sections"
    section_dir.mkdir(parents=True)
    (section_dir / "introduction.tex").write_text(
        (
            "This is intro with a citation \\citep{smith2024alpha,doe2025beta}. "
            "%% CLAIM_ID: EC-2026-001\n\nSecond paragraph."
        ),
        encoding="utf-8",
    )

    state = _make_state()
    ir = build_document_ir_from_paper_state(state, paper_dir, language="en")

    assert ir.paper_id == "paper-001"
    assert ir.language == "en"
    assert len(ir.sections) == 1
    assert ir.sections[0].citation_keys == ["smith2024alpha", "doe2025beta"]
    assert len(ir.sections[0].blocks) == 2
    assert ir.sections[0].blocks[0].citation_keys == ["smith2024alpha", "doe2025beta"]


def test_document_ir_roundtrip(tmp_path: Path) -> None:
    paper_dir = tmp_path / "paper"
    section_dir = paper_dir / "sections"
    section_dir.mkdir(parents=True)
    (section_dir / "introduction.tex").write_text("Simple text.", encoding="utf-8")

    ir = build_document_ir_from_paper_state(_make_state(), paper_dir)
    path = tmp_path / "output" / "document_ir.json"
    write_document_ir(ir, path)
    loaded = load_document_ir(path)

    assert loaded.paper_id == ir.paper_id
    assert loaded.sections[0].section_id == "introduction"

