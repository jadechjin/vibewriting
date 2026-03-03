"""Tests for PaperState, SectionState, and PaperMetrics models."""

from __future__ import annotations

from datetime import UTC, datetime, timezone

import pytest
from pydantic import ValidationError

from vibewriting.models.paper_state import PaperMetrics, PaperState, SectionState


def _make_section(**kwargs) -> SectionState:
    defaults = {
        "section_id": "sec-intro",
        "title": "Introduction",
        "tex_file": "sections/introduction.tex",
    }
    defaults.update(kwargs)
    return SectionState(**defaults)


def _make_paper(**kwargs) -> PaperState:
    defaults = {
        "paper_id": "paper-001",
        "title": "Test Paper",
        "topic": "machine learning",
    }
    defaults.update(kwargs)
    return PaperState(**defaults)


def test_paper_state_creation_basic_fields():
    paper = _make_paper()
    assert paper.paper_id == "paper-001"
    assert paper.title == "Test Paper"
    assert paper.topic == "machine learning"
    assert paper.phase == "outline"
    assert paper.abstract == ""
    assert paper.sections == []
    assert paper.run_id == ""
    assert paper.current_section_index == 0
    assert isinstance(paper.created_at, datetime)
    assert isinstance(paper.updated_at, datetime)
    assert isinstance(paper.metrics, PaperMetrics)


def test_section_state_creation_defaults():
    section = _make_section()
    assert section.section_id == "sec-intro"
    assert section.title == "Introduction"
    assert section.tex_file == "sections/introduction.tex"
    assert section.status == "planned"
    assert section.outline == []
    assert section.claim_ids == []
    assert section.asset_ids == []
    assert section.citation_keys == []
    assert section.word_count == 0
    assert section.paragraph_count == 0
    assert section.no_cite_exemptions == []


def test_section_state_creation_custom_values():
    section = SectionState(
        section_id="sec-related",
        title="Related Work",
        tex_file="sections/related.tex",
        status="drafting",
        outline=["Point A", "Point B"],
        claim_ids=["EC-2026-001", "EC-2026-002"],
        asset_ids=["ASSET-2026-001"],
        citation_keys=["smith2023", "jones2024"],
        word_count=500,
        paragraph_count=4,
        no_cite_exemptions=["common knowledge"],
    )
    assert section.status == "drafting"
    assert section.outline == ["Point A", "Point B"]
    assert section.claim_ids == ["EC-2026-001", "EC-2026-002"]
    assert section.asset_ids == ["ASSET-2026-001"]
    assert section.citation_keys == ["smith2023", "jones2024"]
    assert section.word_count == 500
    assert section.paragraph_count == 4
    assert section.no_cite_exemptions == ["common knowledge"]


def test_section_state_all_valid_statuses():
    for status in ("planned", "drafting", "drafted", "reviewed", "complete"):
        section = _make_section(status=status)
        assert section.status == status


def test_paper_metrics_default_values():
    metrics = PaperMetrics()
    assert metrics.citation_coverage == 0.0
    assert metrics.claim_traceability == 0.0
    assert metrics.figure_coverage == 0.0
    assert metrics.cross_ref_integrity is False
    assert metrics.terminology_consistency is False
    assert metrics.total_claims == 0
    assert metrics.total_citations == 0
    assert metrics.total_figures_referenced == 0
    assert metrics.total_tables_referenced == 0


def test_paper_metrics_coverage_range_valid():
    metrics = PaperMetrics(
        citation_coverage=0.0,
        claim_traceability=0.5,
        figure_coverage=1.0,
    )
    assert metrics.citation_coverage == 0.0
    assert metrics.claim_traceability == 0.5
    assert metrics.figure_coverage == 1.0


def test_paper_metrics_coverage_below_min_raises():
    with pytest.raises(ValidationError):
        PaperMetrics(citation_coverage=-0.1)


def test_paper_metrics_coverage_above_max_raises():
    with pytest.raises(ValidationError):
        PaperMetrics(claim_traceability=1.1)


def test_paper_metrics_count_negative_raises():
    with pytest.raises(ValidationError):
        PaperMetrics(total_claims=-1)


def test_paper_state_all_valid_phases():
    for phase in ("outline", "drafting", "review", "complete"):
        paper = _make_paper(phase=phase)
        assert paper.phase == phase


def test_paper_state_serialization_roundtrip():
    section = _make_section(
        claim_ids=["EC-2026-001"],
        citation_keys=["smith2023"],
    )
    original = _make_paper(sections=[section], run_id="run-42")
    json_str = original.model_dump_json()
    restored = PaperState.model_validate_json(json_str)
    assert restored.paper_id == original.paper_id
    assert restored.title == original.title
    assert restored.run_id == original.run_id
    assert len(restored.sections) == 1
    assert restored.sections[0].section_id == section.section_id
    assert restored.sections[0].claim_ids == ["EC-2026-001"]
    assert restored.sections[0].citation_keys == ["smith2023"]


def test_paper_state_model_dump_integrity_compatible():
    section = SectionState(
        section_id="sec-method",
        title="Methodology",
        tex_file="sections/methodology.tex",
        claim_ids=["EC-2026-001", "EC-2026-002"],
        asset_ids=["ASSET-2026-001"],
        citation_keys=["doe2025"],
    )
    paper = _make_paper(sections=[section])
    dumped = paper.model_dump()

    sections_list = dumped["sections"]
    assert len(sections_list) == 1

    sec_dict = sections_list[0]
    assert "section_id" in sec_dict
    assert "claim_ids" in sec_dict
    assert "asset_ids" in sec_dict
    assert "citation_keys" in sec_dict
    assert sec_dict["section_id"] == "sec-method"
    assert sec_dict["claim_ids"] == ["EC-2026-001", "EC-2026-002"]
    assert sec_dict["asset_ids"] == ["ASSET-2026-001"]
    assert sec_dict["citation_keys"] == ["doe2025"]


def test_paper_state_extra_field_raises():
    with pytest.raises(ValidationError):
        PaperState(
            paper_id="p-001",
            title="T",
            topic="t",
            unknown_field="value",
        )


def test_section_state_extra_field_raises():
    with pytest.raises(ValidationError):
        SectionState(
            section_id="s-001",
            title="T",
            tex_file="sections/s.tex",
            unknown_field="value",
        )


def test_paper_metrics_extra_field_raises():
    with pytest.raises(ValidationError):
        PaperMetrics(unknown_field="value")


def test_paper_state_empty_sections_valid():
    paper = _make_paper(sections=[])
    assert paper.sections == []
    dumped = paper.model_dump()
    assert dumped["sections"] == []


def test_paper_state_multiple_sections():
    sections = [
        _make_section(section_id=f"sec-{i}", title=f"Section {i}", tex_file=f"sections/sec{i}.tex")
        for i in range(3)
    ]
    paper = _make_paper(sections=sections)
    assert len(paper.sections) == 3
    assert paper.sections[0].section_id == "sec-0"
    assert paper.sections[2].section_id == "sec-2"


def test_paper_state_updated_at_is_utc():
    before = datetime.now(UTC)
    paper = _make_paper()
    after = datetime.now(UTC)
    assert paper.updated_at.tzinfo is not None
    assert before <= paper.updated_at <= after


def test_paper_state_created_at_is_utc():
    before = datetime.now(UTC)
    paper = _make_paper()
    after = datetime.now(UTC)
    assert paper.created_at.tzinfo is not None
    assert before <= paper.created_at <= after


def test_paper_state_invalid_phase_raises():
    with pytest.raises(ValidationError):
        _make_paper(phase="writing")


def test_section_state_invalid_status_raises():
    with pytest.raises(ValidationError):
        _make_section(status="pending")


def test_paper_metrics_coverage_boundary_zero():
    metrics = PaperMetrics(citation_coverage=0.0)
    assert metrics.citation_coverage == 0.0


def test_paper_metrics_coverage_boundary_one():
    metrics = PaperMetrics(citation_coverage=1.0)
    assert metrics.citation_coverage == 1.0


def test_paper_metrics_coverage_below_zero_raises():
    with pytest.raises(ValidationError):
        PaperMetrics(figure_coverage=-0.01)


def test_paper_metrics_coverage_above_one_raises():
    with pytest.raises(ValidationError):
        PaperMetrics(figure_coverage=1.01)
