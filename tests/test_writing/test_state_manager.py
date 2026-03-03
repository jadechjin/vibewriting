"""Tests for PaperStateManager."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from vibewriting.models.paper_state import PaperMetrics, PaperState, SectionState
from vibewriting.writing.state_manager import PaperStateManager


def _make_section(section_id: str = "introduction", title: str = "引言") -> dict:
    return {
        "section_id": section_id,
        "title": title,
        "tex_file": f"sections/{section_id}.tex",
    }


def _make_manager(tmp_path: Path) -> tuple[PaperStateManager, Path]:
    state_path = tmp_path / "paper_state.json"
    manager = PaperStateManager(state_path)
    return manager, state_path


def _make_state(manager: PaperStateManager) -> PaperState:
    return manager.create(
        paper_id="test-paper",
        title="测试论文",
        topic="机器学习",
        sections=[
            _make_section("introduction", "引言"),
            _make_section("experiments", "实验"),
        ],
    )


class TestLoad:
    def test_load_nonexistent_file_returns_none(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        result = manager.load()
        assert result is None


class TestSave:
    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        manager.save(state)
        loaded = manager.load()
        assert loaded is not None
        assert loaded.paper_id == state.paper_id
        assert loaded.title == state.title
        assert loaded.topic == state.topic
        assert loaded.phase == state.phase
        assert len(loaded.sections) == len(state.sections)

    def test_save_atomic_write_no_tmp_after_save(self, tmp_path: Path) -> None:
        manager, state_path = _make_manager(tmp_path)
        state = _make_state(manager)
        manager.save(state)
        tmp_path_file = state_path.with_suffix(".tmp")
        assert not tmp_path_file.exists()
        assert state_path.exists()

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        nested_path = tmp_path / "deep" / "nested" / "paper_state.json"
        manager = PaperStateManager(nested_path)
        state = manager.create(
            paper_id="p1",
            title="标题",
            topic="主题",
            sections=[_make_section()],
        )
        manager.save(state)
        assert nested_path.exists()


class TestCreate:
    def test_create_returns_outline_phase(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        assert state.phase == "outline"

    def test_create_sets_fields(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        assert state.paper_id == "test-paper"
        assert state.title == "测试论文"
        assert state.topic == "机器学习"
        assert len(state.sections) == 2

    def test_create_section_defaults(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        sec = state.sections[0]
        assert sec.status == "planned"
        assert sec.claim_ids == []
        assert sec.asset_ids == []


class TestUpdateSectionStatus:
    def test_update_section_status_returns_new_instance(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.update_section_status(state, "introduction", "drafting")
        assert new_state is not state

    def test_update_section_status_changes_target(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.update_section_status(state, "introduction", "drafting")
        intro = next(s for s in new_state.sections if s.section_id == "introduction")
        assert intro.status == "drafting"

    def test_update_section_status_immutable_original(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        original_status = next(
            s.status for s in state.sections if s.section_id == "introduction"
        )
        manager.update_section_status(state, "introduction", "drafting")
        current_status = next(
            s.status for s in state.sections if s.section_id == "introduction"
        )
        assert current_status == original_status

    def test_update_section_status_other_sections_unchanged(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.update_section_status(state, "introduction", "drafting")
        experiments = next(s for s in new_state.sections if s.section_id == "experiments")
        assert experiments.status == "planned"


class TestUpdateMetrics:
    def test_update_metrics_returns_new_instance(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        metrics = PaperMetrics(citation_coverage=0.8, claim_traceability=0.9)
        new_state = manager.update_metrics(state, metrics)
        assert new_state is not state

    def test_update_metrics_sets_metrics(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        metrics = PaperMetrics(citation_coverage=0.8, claim_traceability=0.9)
        new_state = manager.update_metrics(state, metrics)
        assert new_state.metrics.citation_coverage == 0.8
        assert new_state.metrics.claim_traceability == 0.9


class TestAdvancePhase:
    def test_advance_outline_to_drafting(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        assert state.phase == "outline"
        new_state = manager.advance_phase(state)
        assert new_state.phase == "drafting"

    def test_advance_drafting_to_review(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        state = manager.advance_phase(state)
        new_state = manager.advance_phase(state)
        assert new_state.phase == "review"

    def test_advance_review_to_complete(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        state = manager.advance_phase(state)
        state = manager.advance_phase(state)
        new_state = manager.advance_phase(state)
        assert new_state.phase == "complete"

    def test_advance_from_complete_raises(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        state = manager.advance_phase(state)
        state = manager.advance_phase(state)
        state = manager.advance_phase(state)
        with pytest.raises(ValueError, match="Cannot advance from phase 'complete'"):
            manager.advance_phase(state)

    def test_advance_returns_new_instance(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.advance_phase(state)
        assert new_state is not state


class TestAddClaimToSection:
    def test_add_claim_to_section(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.add_claim_to_section(state, "introduction", "claim-001")
        intro = next(s for s in new_state.sections if s.section_id == "introduction")
        assert "claim-001" in intro.claim_ids

    def test_add_claim_no_duplicate(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        state = manager.add_claim_to_section(state, "introduction", "claim-001")
        new_state = manager.add_claim_to_section(state, "introduction", "claim-001")
        intro = next(s for s in new_state.sections if s.section_id == "introduction")
        assert intro.claim_ids.count("claim-001") == 1

    def test_add_claim_returns_new_instance(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.add_claim_to_section(state, "introduction", "claim-001")
        assert new_state is not state

    def test_add_claim_immutable_original(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        manager.add_claim_to_section(state, "introduction", "claim-001")
        intro = next(s for s in state.sections if s.section_id == "introduction")
        assert "claim-001" not in intro.claim_ids


class TestAddAssetToSection:
    def test_add_asset_to_section(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.add_asset_to_section(state, "experiments", "fig-001")
        experiments = next(s for s in new_state.sections if s.section_id == "experiments")
        assert "fig-001" in experiments.asset_ids

    def test_add_asset_no_duplicate(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        state = manager.add_asset_to_section(state, "experiments", "fig-001")
        new_state = manager.add_asset_to_section(state, "experiments", "fig-001")
        experiments = next(s for s in new_state.sections if s.section_id == "experiments")
        assert experiments.asset_ids.count("fig-001") == 1

    def test_add_asset_returns_new_instance(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.add_asset_to_section(state, "experiments", "fig-001")
        assert new_state is not state

    def test_add_asset_immutable_original(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        manager.add_asset_to_section(state, "experiments", "fig-001")
        experiments = next(s for s in state.sections if s.section_id == "experiments")
        assert "fig-001" not in experiments.asset_ids


class TestUpdatedAt:
    def test_updated_at_changes_after_update_section_status(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        time.sleep(0.01)
        new_state = manager.update_section_status(state, "introduction", "drafting")
        assert new_state.updated_at >= state.updated_at

    def test_updated_at_changes_after_advance_phase(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        time.sleep(0.01)
        new_state = manager.advance_phase(state)
        assert new_state.updated_at >= state.updated_at

    def test_updated_at_changes_after_add_claim(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        time.sleep(0.01)
        new_state = manager.add_claim_to_section(state, "introduction", "claim-001")
        assert new_state.updated_at >= state.updated_at


class TestUpdateSectionPayload:
    def test_update_claim_ids_only(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.update_section_payload(
            state, "introduction", claim_ids=["c1", "c2"]
        )
        intro = next(s for s in new_state.sections if s.section_id == "introduction")
        assert intro.claim_ids == ["c1", "c2"]
        # asset_ids not changed
        assert intro.asset_ids == []

    def test_update_multiple_fields(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.update_section_payload(
            state, "introduction",
            claim_ids=["c1"],
            word_count=500,
            paragraph_count=3,
        )
        intro = next(s for s in new_state.sections if s.section_id == "introduction")
        assert intro.claim_ids == ["c1"]
        assert intro.word_count == 500
        assert intro.paragraph_count == 3

    def test_none_fields_not_updated(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.update_section_payload(
            state, "introduction", word_count=100
        )
        intro = next(s for s in new_state.sections if s.section_id == "introduction")
        # claim_ids and asset_ids remain defaults
        assert intro.claim_ids == []
        assert intro.asset_ids == []
        assert intro.word_count == 100

    def test_returns_new_instance(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.update_section_payload(
            state, "introduction", claim_ids=["c1"]
        )
        assert new_state is not state

    def test_original_unchanged(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        manager.update_section_payload(
            state, "introduction", claim_ids=["c1"], word_count=999
        )
        intro = next(s for s in state.sections if s.section_id == "introduction")
        assert intro.claim_ids == []
        assert intro.word_count == 0


class TestSetCurrentSectionIndex:
    def test_set_valid_index(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.set_current_section_index(state, 1)
        assert new_state.current_section_index == 1

    def test_set_out_of_range_raises(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        with pytest.raises(ValueError):
            manager.set_current_section_index(state, 10)

    def test_set_negative_raises(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        with pytest.raises(ValueError):
            manager.set_current_section_index(state, -1)

    def test_returns_new_instance(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.set_current_section_index(state, 0)
        assert new_state is not state


class TestBatchUpdateSections:
    def test_batch_update_single_section(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.batch_update_sections(
            state, {"introduction": {"status": "drafting"}}
        )
        intro = next(s for s in new_state.sections if s.section_id == "introduction")
        assert intro.status == "drafting"

    def test_batch_update_multiple_sections(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.batch_update_sections(
            state,
            {
                "introduction": {"status": "drafting"},
                "experiments": {"word_count": 200},
            },
        )
        intro = next(s for s in new_state.sections if s.section_id == "introduction")
        experiments = next(s for s in new_state.sections if s.section_id == "experiments")
        assert intro.status == "drafting"
        assert experiments.word_count == 200

    def test_unknown_section_id_ignored(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        # Should not raise, unknown id silently ignored
        new_state = manager.batch_update_sections(
            state, {"nonexistent": {"status": "drafting"}}
        )
        assert len(new_state.sections) == len(state.sections)

    def test_returns_new_instance(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.batch_update_sections(
            state, {"introduction": {"status": "drafting"}}
        )
        assert new_state is not state

    def test_empty_updates_returns_new_instance(self, tmp_path: Path) -> None:
        manager, _ = _make_manager(tmp_path)
        state = _make_state(manager)
        new_state = manager.batch_update_sections(state, {})
        assert new_state is not state
