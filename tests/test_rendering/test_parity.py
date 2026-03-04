from __future__ import annotations

from vibewriting.models.paper_state import PaperState, SectionState
from vibewriting.rendering.ir import DocumentIR, ParagraphBlockIR, SectionIR
from vibewriting.rendering.parity import build_parity_report


def _make_state() -> PaperState:
    return PaperState(
        paper_id="p001",
        title="Test",
        topic="Topic",
        sections=[
            SectionState(
                section_id="intro",
                title="引言",
                tex_file="sections/introduction.tex",
                claim_ids=["EC-2026-001"],
                asset_ids=["ASSET-2026-001"],
                citation_keys=["smith2024alpha"],
            )
        ],
    )


def _make_ir(citation_key: str = "smith2024alpha") -> DocumentIR:
    return DocumentIR(
        paper_id="p001",
        title="Test",
        topic="Topic",
        sections=[
            SectionIR(
                section_id="intro",
                title="引言",
                source_tex_file="sections/introduction.tex",
                claim_ids=["EC-2026-001"],
                asset_ids=["ASSET-2026-001"],
                citation_keys=[citation_key],
                blocks=[ParagraphBlockIR(text="para")],
            )
        ],
    )


def test_parity_report_all_match() -> None:
    report = build_parity_report(_make_ir(), _make_state())
    assert report["all_match"] is True
    assert report["sections"][0]["citations_match"] is True


def test_parity_report_detects_mismatch() -> None:
    report = build_parity_report(_make_ir(citation_key="other2026"), _make_state())
    assert report["all_match"] is False
    assert report["sections"][0]["citations_match"] is False

