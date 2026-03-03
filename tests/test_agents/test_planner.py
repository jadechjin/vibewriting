"""Tests for agents.planner module."""

from __future__ import annotations

import pytest

from vibewriting.agents.contracts import AgentRole, SectionTask
from vibewriting.agents.planner import (
    _infer_section_type,
    assign_roles,
    build_section_task_graph,
    get_ready_tasks,
)
from vibewriting.models.paper_state import PaperState, SectionState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_section(
    section_id: str,
    title: str = "Title",
    claim_ids: list[str] | None = None,
    asset_ids: list[str] | None = None,
    outline: list[str] | None = None,
) -> SectionState:
    return SectionState(
        section_id=section_id,
        title=title,
        outline=outline or [],
        claim_ids=claim_ids or [],
        asset_ids=asset_ids or [],
        tex_file=f"paper/sections/{section_id}.tex",
    )


def _make_state(sections: list[SectionState]) -> PaperState:
    return PaperState(
        paper_id="test-paper",
        title="Test Paper",
        topic="Testing",
        sections=sections,
    )


def _make_6_section_state() -> PaperState:
    return _make_state(
        [
            _make_section("introduction"),
            _make_section("related-work"),
            _make_section("method"),
            _make_section("experiments"),
            _make_section("conclusion"),
            _make_section("appendix"),
        ]
    )


# ---------------------------------------------------------------------------
# TestInferSectionType
# ---------------------------------------------------------------------------


class TestInferSectionType:
    def test_introduction(self) -> None:
        assert _infer_section_type("introduction") == "introduction"

    def test_intro_alias(self) -> None:
        assert _infer_section_type("intro") == "introduction"

    def test_related_work(self) -> None:
        assert _infer_section_type("related-work") == "related-work"

    def test_related_alias(self) -> None:
        assert _infer_section_type("related") == "related-work"

    def test_method(self) -> None:
        assert _infer_section_type("method") == "method"

    def test_experiments(self) -> None:
        assert _infer_section_type("experiments") == "experiments"

    def test_results_alias(self) -> None:
        assert _infer_section_type("results") == "experiments"

    def test_conclusion(self) -> None:
        assert _infer_section_type("conclusion") == "conclusion"

    def test_unknown_defaults_to_appendix(self) -> None:
        assert _infer_section_type("abstract") == "appendix"


# ---------------------------------------------------------------------------
# TestAssignRoles
# ---------------------------------------------------------------------------


class TestAssignRoles:
    def test_introduction_gets_storyteller(self) -> None:
        roles = assign_roles("introduction")
        assert AgentRole.STORYTELLER in roles

    def test_experiments_gets_analyst(self) -> None:
        roles = assign_roles("experiments")
        assert AgentRole.ANALYST in roles

    def test_unknown_type_gets_storyteller(self) -> None:
        roles = assign_roles("unknown_section_type")
        assert AgentRole.STORYTELLER in roles


# ---------------------------------------------------------------------------
# TestBuildSectionTaskGraph
# ---------------------------------------------------------------------------


class TestBuildSectionTaskGraph:
    def test_basic_6_sections(self) -> None:
        state = _make_6_section_state()
        tasks = build_section_task_graph(state)
        # Each section produces exactly 1 task (one primary role each)
        assert len(tasks) == 6

    def test_dependencies_resolved(self) -> None:
        """introduction tasks should depend on method's section_id."""
        state = _make_6_section_state()
        tasks = build_section_task_graph(state)
        intro_tasks = [t for t in tasks if t.section_id == "introduction"]
        assert intro_tasks, "Expected at least one task for introduction"
        for task in intro_tasks:
            assert "method" in task.dependencies

    def test_experiments_depends_on_method(self) -> None:
        state = _make_6_section_state()
        tasks = build_section_task_graph(state)
        exp_tasks = [t for t in tasks if t.section_id == "experiments"]
        assert exp_tasks, "Expected at least one task for experiments"
        for task in exp_tasks:
            assert "method" in task.dependencies

    def test_evidence_cards_filtered(self) -> None:
        """Evidence cards are filtered by section's claim_ids."""
        sections = [
            _make_section("introduction", claim_ids=["EC-2026-001"]),
            _make_section("method", claim_ids=["EC-2026-002"]),
        ]
        state = _make_state(sections)
        evidence_cards = [
            {"claim_id": "EC-2026-001", "text": "Card 1"},
            {"claim_id": "EC-2026-002", "text": "Card 2"},
            {"claim_id": "EC-2026-003", "text": "Card 3"},
        ]
        tasks = build_section_task_graph(state, evidence_cards=evidence_cards)
        intro_tasks = [t for t in tasks if t.section_id == "introduction"]
        assert len(intro_tasks) == 1
        assert len(intro_tasks[0].evidence_cards) == 1
        assert intro_tasks[0].evidence_cards[0]["claim_id"] == "EC-2026-001"

    def test_assets_filtered(self) -> None:
        """Assets are filtered by section's asset_ids."""
        sections = [
            _make_section("experiments", asset_ids=["ASSET-2026-001"]),
            _make_section("method"),
        ]
        state = _make_state(sections)
        asset_manifest = [
            {"asset_id": "ASSET-2026-001", "type": "figure"},
            {"asset_id": "ASSET-2026-002", "type": "table"},
        ]
        tasks = build_section_task_graph(state, asset_manifest=asset_manifest)
        exp_tasks = [t for t in tasks if t.section_id == "experiments"]
        assert len(exp_tasks) == 1
        assert len(exp_tasks[0].assets) == 1
        assert exp_tasks[0].assets[0]["asset_id"] == "ASSET-2026-001"

    def test_context_includes_outline(self) -> None:
        """Context dict includes section title and outline."""
        sections = [
            _make_section(
                "method",
                title="Methodology",
                outline=["Step 1", "Step 2"],
            )
        ]
        state = _make_state(sections)
        tasks = build_section_task_graph(state)
        assert len(tasks) == 1
        ctx = tasks[0].context
        assert ctx["title"] == "Methodology"
        assert ctx["outline"] == ["Step 1", "Step 2"]

    def test_empty_state_returns_empty_list(self) -> None:
        state = _make_state([])
        tasks = build_section_task_graph(state)
        assert tasks == []


# ---------------------------------------------------------------------------
# TestGetReadyTasks
# ---------------------------------------------------------------------------


class TestGetReadyTasks:
    def _make_task(
        self,
        section_id: str,
        dependencies: list[str] | None = None,
    ) -> SectionTask:
        return SectionTask(
            section_id=section_id,
            role=AgentRole.STORYTELLER,
            dependencies=dependencies or [],
        )

    def test_no_dependencies_always_ready(self) -> None:
        tasks = [
            self._make_task("method"),
            self._make_task("related-work"),
        ]
        ready = get_ready_tasks(tasks, completed_ids=set())
        assert len(ready) == 2

    def test_dependencies_not_met(self) -> None:
        tasks = [self._make_task("introduction", dependencies=["method"])]
        ready = get_ready_tasks(tasks, completed_ids=set())
        assert ready == []

    def test_dependencies_met(self) -> None:
        tasks = [self._make_task("introduction", dependencies=["method"])]
        ready = get_ready_tasks(tasks, completed_ids={"method"})
        assert len(ready) == 1
        assert ready[0].section_id == "introduction"

    def test_partial_completion(self) -> None:
        tasks = [
            self._make_task("method"),
            self._make_task("introduction", dependencies=["method"]),
            self._make_task("conclusion", dependencies=["experiments", "method"]),
        ]
        # Only method is completed — introduction becomes ready, conclusion still blocked
        ready = get_ready_tasks(tasks, completed_ids={"method"})
        ready_ids = {t.section_id for t in ready}
        assert "introduction" in ready_ids
        assert "conclusion" not in ready_ids

    def test_empty_tasks_returns_empty(self) -> None:
        ready = get_ready_tasks([], completed_ids=set())
        assert ready == []
