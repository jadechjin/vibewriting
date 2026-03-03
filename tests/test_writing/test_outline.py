"""Tests for outline generation tools."""

from __future__ import annotations

from vibewriting.models.paper_state import SectionState
from vibewriting.writing.outline import (
    SECTION_TYPES,
    PaperOutline,
    OutlineSection,
    _distribute_assets,
    _distribute_claims,
    build_default_outline,
    outline_to_paper_state,
    outline_to_sections,
)


class TestBuildDefaultOutline:
    def test_returns_six_sections(self) -> None:
        outline = build_default_outline(topic="机器学习", title="测试论文")
        assert len(outline.sections) == 6

    def test_section_ids_match_expected(self) -> None:
        outline = build_default_outline(topic="机器学习", title="测试论文")
        expected_ids = [st[0] for st in SECTION_TYPES]
        actual_ids = [s.section_id for s in outline.sections]
        assert actual_ids == expected_ids

    def test_tex_files_match_expected(self) -> None:
        outline = build_default_outline(topic="机器学习", title="测试论文")
        expected_tex = [st[2] for st in SECTION_TYPES]
        actual_tex = [s.tex_file for s in outline.sections]
        assert actual_tex == expected_tex

    def test_title_and_topic_set(self) -> None:
        outline = build_default_outline(topic="深度学习", title="深度神经网络研究")
        assert outline.title == "深度神经网络研究"
        assert outline.topic == "深度学习"

    def test_survey_evidence_goes_to_related_work(self) -> None:
        cards = [{"claim_id": "c001", "evidence_type": "survey", "tags": []}]
        outline = build_default_outline(topic="t", title="T", evidence_cards=cards)
        related = next(s for s in outline.sections if s.section_id == "related-work")
        assert "c001" in related.suggested_claim_ids

    def test_empirical_evidence_goes_to_experiments(self) -> None:
        cards = [{"claim_id": "c002", "evidence_type": "empirical", "tags": []}]
        outline = build_default_outline(topic="t", title="T", evidence_cards=cards)
        experiments = next(s for s in outline.sections if s.section_id == "experiments")
        assert "c002" in experiments.suggested_claim_ids

    def test_figure_asset_goes_to_experiments(self) -> None:
        assets = [{"asset_id": "fig-001", "kind": "figure"}]
        outline = build_default_outline(topic="t", title="T", asset_manifest=assets)
        experiments = next(s for s in outline.sections if s.section_id == "experiments")
        assert "fig-001" in experiments.suggested_asset_ids

    def test_table_asset_goes_to_experiments(self) -> None:
        assets = [{"asset_id": "tbl-001", "kind": "table"}]
        outline = build_default_outline(topic="t", title="T", asset_manifest=assets)
        experiments = next(s for s in outline.sections if s.section_id == "experiments")
        assert "tbl-001" in experiments.suggested_asset_ids

    def test_no_evidence_cards_no_claim_ids(self) -> None:
        outline = build_default_outline(topic="t", title="T", evidence_cards=None)
        for section in outline.sections:
            assert section.suggested_claim_ids == []

    def test_no_assets_no_asset_ids(self) -> None:
        outline = build_default_outline(topic="t", title="T", asset_manifest=None)
        for section in outline.sections:
            assert section.suggested_asset_ids == []


class TestOutlineToPaperState:
    def test_phase_is_outline(self) -> None:
        outline = build_default_outline(topic="t", title="T")
        state = outline_to_paper_state(outline, paper_id="p001")
        assert state.phase == "outline"

    def test_paper_id_set(self) -> None:
        outline = build_default_outline(topic="t", title="T")
        state = outline_to_paper_state(outline, paper_id="p001")
        assert state.paper_id == "p001"

    def test_title_and_topic_preserved(self) -> None:
        outline = build_default_outline(topic="强化学习", title="RL 研究")
        state = outline_to_paper_state(outline, paper_id="p002")
        assert state.title == "RL 研究"
        assert state.topic == "强化学习"

    def test_abstract_draft_mapped(self) -> None:
        outline = build_default_outline(topic="t", title="T")
        outline.abstract_draft = "这是摘要草稿"
        state = outline_to_paper_state(outline, paper_id="p003")
        assert state.abstract == "这是摘要草稿"

    def test_sections_converted(self) -> None:
        outline = build_default_outline(topic="t", title="T")
        state = outline_to_paper_state(outline, paper_id="p004")
        assert len(state.sections) == 6


class TestOutlineToSections:
    def test_returns_section_state_list(self) -> None:
        outline = build_default_outline(topic="t", title="T")
        sections = outline_to_sections(outline)
        assert all(isinstance(s, SectionState) for s in sections)

    def test_status_is_planned(self) -> None:
        outline = build_default_outline(topic="t", title="T")
        sections = outline_to_sections(outline)
        for section in sections:
            assert section.status == "planned"

    def test_section_ids_preserved(self) -> None:
        outline = build_default_outline(topic="t", title="T")
        sections = outline_to_sections(outline)
        expected_ids = [st[0] for st in SECTION_TYPES]
        actual_ids = [s.section_id for s in sections]
        assert actual_ids == expected_ids

    def test_claim_ids_mapped(self) -> None:
        cards = [{"claim_id": "c010", "evidence_type": "survey", "tags": []}]
        outline = build_default_outline(topic="t", title="T", evidence_cards=cards)
        sections = outline_to_sections(outline)
        related = next(s for s in sections if s.section_id == "related-work")
        assert "c010" in related.claim_ids

    def test_asset_ids_mapped(self) -> None:
        assets = [{"asset_id": "fig-010", "kind": "figure"}]
        outline = build_default_outline(topic="t", title="T", asset_manifest=assets)
        sections = outline_to_sections(outline)
        experiments = next(s for s in sections if s.section_id == "experiments")
        assert "fig-010" in experiments.asset_ids


class TestDistributeClaims:
    def test_survey_maps_to_related_work(self) -> None:
        cards = [{"claim_id": "c1", "evidence_type": "survey"}]
        result = _distribute_claims(cards, "related-work")
        assert "c1" in result

    def test_survey_not_in_introduction(self) -> None:
        cards = [{"claim_id": "c1", "evidence_type": "survey"}]
        result = _distribute_claims(cards, "introduction")
        assert "c1" not in result

    def test_theoretical_maps_to_method(self) -> None:
        cards = [{"claim_id": "c2", "evidence_type": "theoretical"}]
        result = _distribute_claims(cards, "method")
        assert "c2" in result

    def test_unknown_evidence_type_ignored(self) -> None:
        cards = [{"claim_id": "c3", "evidence_type": "unknown_type"}]
        result = _distribute_claims(cards, "introduction")
        assert result == []

    def test_empty_claim_id_ignored(self) -> None:
        cards = [{"claim_id": "", "evidence_type": "survey"}]
        result = _distribute_claims(cards, "related-work")
        assert result == []


class TestDistributeAssets:
    def test_figure_maps_to_experiments(self) -> None:
        assets = [{"asset_id": "fig-1", "kind": "figure"}]
        result = _distribute_assets(assets, "experiments")
        assert "fig-1" in result

    def test_figure_maps_to_method(self) -> None:
        assets = [{"asset_id": "fig-1", "kind": "figure"}]
        result = _distribute_assets(assets, "method")
        assert "fig-1" in result

    def test_figure_not_in_introduction(self) -> None:
        assets = [{"asset_id": "fig-1", "kind": "figure"}]
        result = _distribute_assets(assets, "introduction")
        assert "fig-1" not in result

    def test_unknown_kind_ignored(self) -> None:
        assets = [{"asset_id": "audio-1", "kind": "audio"}]
        result = _distribute_assets(assets, "experiments")
        assert result == []

    def test_empty_asset_id_ignored(self) -> None:
        assets = [{"asset_id": "", "kind": "figure"}]
        result = _distribute_assets(assets, "experiments")
        assert result == []
