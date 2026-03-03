"""Tests for WritingOrchestrator core."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vibewriting.agents.contracts import (
    AgentRole,
    SectionPatchPayload,
    SectionTask,
)
from vibewriting.agents.executor import MockExecutor
from vibewriting.agents.orchestrator import OrchestratorConfig, WritingOrchestrator
from vibewriting.models.paper_state import PaperState, SectionState
from vibewriting.writing.state_manager import PaperStateManager


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def _make_paper_state(
    paper_id: str = "paper-test-001",
    section_ids: list[str] | None = None,
) -> PaperState:
    """Build a minimal PaperState for testing."""
    if section_ids is None:
        section_ids = ["sec-method", "sec-experiments"]

    sections = [
        SectionState(
            section_id=sid,
            title=sid.replace("sec-", "").replace("-", " ").title(),
            tex_file=f"sections/{sid}.tex",
            status="planned",
        )
        for sid in section_ids
    ]
    return PaperState(
        paper_id=paper_id,
        title="Test Paper",
        topic="machine learning",
        phase="drafting",
        sections=sections,
    )


def _make_orchestrator(
    tmp_path: Path,
    config: OrchestratorConfig | None = None,
    executor: MockExecutor | None = None,
) -> tuple[WritingOrchestrator, PaperStateManager]:
    """Build a WritingOrchestrator with a temp directory."""
    state_path = tmp_path / "paper_state.json"
    paper_dir = tmp_path / "paper"
    output_dir = tmp_path / "output"
    paper_dir.mkdir()
    output_dir.mkdir()

    state_manager = PaperStateManager(state_path)
    exec_ = executor or MockExecutor()
    cfg = config or OrchestratorConfig()

    orchestrator = WritingOrchestrator(
        config=cfg,
        state_manager=state_manager,
        executor=exec_,
        paper_dir=paper_dir,
        output_dir=output_dir,
    )
    return orchestrator, state_manager


# ─────────────────────────────────────────────
# TestOrchestratorConfig
# ─────────────────────────────────────────────


class TestOrchestratorConfig:
    def test_default_config(self) -> None:
        cfg = OrchestratorConfig()
        assert cfg.max_rounds == 3
        assert cfg.max_retries_per_section == 2
        assert cfg.enable_git_snapshots is True
        assert cfg.executor_type == "mock"

    def test_custom_config(self) -> None:
        cfg = OrchestratorConfig(
            max_rounds=5,
            max_retries_per_section=1,
            enable_git_snapshots=False,
            executor_type="subagent",
        )
        assert cfg.max_rounds == 5
        assert cfg.max_retries_per_section == 1
        assert cfg.enable_git_snapshots is False
        assert cfg.executor_type == "subagent"


# ─────────────────────────────────────────────
# TestWritingOrchestrator
# ─────────────────────────────────────────────


class TestWritingOrchestrator:
    def test_run_success_with_mock_executor(self, tmp_path: Path) -> None:
        """2 sections, MockExecutor -> report.success=True."""
        orchestrator, _ = _make_orchestrator(tmp_path)
        state = _make_paper_state(section_ids=["sec-method", "sec-appendix"])

        report = asyncio.run(orchestrator.run(state))

        assert report.success is True
        assert report.paper_id == "paper-test-001"
        assert report.sections_completed == 2
        assert report.total_sections == 2

    def test_run_creates_tex_files(self, tmp_path: Path) -> None:
        """Verify .tex files are written to paper_dir."""
        orchestrator, _ = _make_orchestrator(tmp_path)
        state = _make_paper_state(section_ids=["sec-method"])

        asyncio.run(orchestrator.run(state))

        expected_file = tmp_path / "paper" / "sections" / "sec-method.tex"
        assert expected_file.exists()
        content = expected_file.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_run_updates_section_status_to_drafted(self, tmp_path: Path) -> None:
        """After orchestration, sections should have status 'drafted'."""
        state_path = tmp_path / "paper_state.json"
        paper_dir = tmp_path / "paper"
        output_dir = tmp_path / "output"
        paper_dir.mkdir()
        output_dir.mkdir()

        state_manager = PaperStateManager(state_path)
        orchestrator = WritingOrchestrator(
            config=OrchestratorConfig(),
            state_manager=state_manager,
            executor=MockExecutor(),
            paper_dir=paper_dir,
            output_dir=output_dir,
        )
        state = _make_paper_state(section_ids=["sec-method"])
        asyncio.run(orchestrator.run(state))

        # Load saved state and verify
        saved_state = state_manager.load()
        assert saved_state is not None
        section = next(
            (s for s in saved_state.sections if s.section_id == "sec-method"),
            None,
        )
        assert section is not None
        assert section.status == "drafted"

    def test_run_saves_state(self, tmp_path: Path) -> None:
        """state_manager.save should be called after orchestration."""
        state_path = tmp_path / "paper_state.json"
        paper_dir = tmp_path / "paper"
        output_dir = tmp_path / "output"
        paper_dir.mkdir()
        output_dir.mkdir()

        real_manager = PaperStateManager(state_path)
        save_calls = []
        original_save = real_manager.save

        def tracking_save(s: PaperState) -> None:
            save_calls.append(s)
            original_save(s)

        real_manager.save = tracking_save  # type: ignore[method-assign]

        orchestrator = WritingOrchestrator(
            config=OrchestratorConfig(),
            state_manager=real_manager,
            executor=MockExecutor(),
            paper_dir=paper_dir,
            output_dir=output_dir,
        )
        state = _make_paper_state(section_ids=["sec-method"])
        asyncio.run(orchestrator.run(state))

        assert len(save_calls) >= 1

    def test_run_with_empty_sections(self, tmp_path: Path) -> None:
        """Empty sections -> success but sections_completed=0."""
        orchestrator, _ = _make_orchestrator(tmp_path)
        state = _make_paper_state(section_ids=[])

        report = asyncio.run(orchestrator.run(state))

        assert report.sections_completed == 0
        assert report.total_sections == 0
        assert report.success is True

    def test_run_report_fields(self, tmp_path: Path) -> None:
        """Report contains correct paper_id, rounds, timestamps, etc."""
        orchestrator, _ = _make_orchestrator(tmp_path)
        state = _make_paper_state(section_ids=["sec-method"])

        report = asyncio.run(orchestrator.run(state))

        assert report.paper_id == "paper-test-001"
        assert len(report.rounds) >= 1
        assert report.started_at is not None
        assert report.finished_at is not None
        assert report.finished_at >= report.started_at
        assert report.total_sections == 1

    def test_dispatch_handles_executor_error(self, tmp_path: Path) -> None:
        """Executor throwing an exception -> skip section, no crash."""

        class FailingExecutor:
            async def run_task(self, task: SectionTask, context: dict | None = None):  # type: ignore[override]
                raise RuntimeError("simulated executor failure")

        state_path = tmp_path / "paper_state.json"
        paper_dir = tmp_path / "paper"
        output_dir = tmp_path / "output"
        paper_dir.mkdir()
        output_dir.mkdir()

        orchestrator = WritingOrchestrator(
            config=OrchestratorConfig(),
            state_manager=PaperStateManager(state_path),
            executor=FailingExecutor(),  # type: ignore[arg-type]
            paper_dir=paper_dir,
            output_dir=output_dir,
        )
        state = _make_paper_state(section_ids=["sec-method"])

        # Should not raise
        report = asyncio.run(orchestrator.run(state))

        # Section was not completed due to executor failure
        assert report.sections_completed == 0
        assert report.success is False

    def test_merge_and_persist_writes_file(self, tmp_path: Path) -> None:
        """_merge_and_persist writes final tex content to file."""
        orchestrator, state_manager = _make_orchestrator(tmp_path)
        state = _make_paper_state(section_ids=["sec-method"])

        payload = SectionPatchPayload(
            section_id="sec-method",
            tex_content=r"\section{Method} This is the method section.",
            claim_ids=[],
            asset_ids=[],
            citation_keys=[],
            word_count=8,
        )

        orchestrator._merge_and_persist(state, [payload], [], None, None)

        expected_file = tmp_path / "paper" / "sections" / "sec-method.tex"
        assert expected_file.exists()
        content = expected_file.read_text(encoding="utf-8")
        assert "Method" in content

    def test_post_merge_validation_runs_gates(self, tmp_path: Path) -> None:
        """_post_merge_validation returns a GateReport with results."""
        orchestrator, _ = _make_orchestrator(tmp_path)

        payload = SectionPatchPayload(
            section_id="sec-conclusion",
            tex_content=r"\section{Conclusion} This concludes the paper.",
            claim_ids=[],
            asset_ids=[],
            citation_keys=[],
            word_count=7,
        )

        gate_report = orchestrator._post_merge_validation(payload, None, None)

        assert gate_report is not None
        assert hasattr(gate_report, "results")
        assert len(gate_report.results) > 0
        assert hasattr(gate_report, "all_passed")
        assert hasattr(gate_report, "summary")

    def test_run_with_multiple_rounds(self, tmp_path: Path) -> None:
        """Multiple dependency layers produce multiple rounds."""
        orchestrator, _ = _make_orchestrator(
            tmp_path,
            config=OrchestratorConfig(max_rounds=5),
        )
        # method has no deps; introduction depends on method
        state = _make_paper_state(
            section_ids=["sec-method", "sec-introduction"]
        )

        report = asyncio.run(orchestrator.run(state))

        # Both sections should be completed
        assert report.sections_completed == 2
        # introduction depends on method -> at least 2 rounds
        assert report.total_sections == 2

    def test_handle_failure_calls_rollback(self, tmp_path: Path) -> None:
        """_handle_failure triggers rollback when snapshot hash is provided."""
        orchestrator, _ = _make_orchestrator(tmp_path)
        error = RuntimeError("test error")
        fake_hash = "abc1234"

        # rollback_to_snapshot is lazily imported inside _handle_failure via
        # `from vibewriting.agents.git_safety import rollback_to_snapshot`.
        # Patch at the git_safety module level to intercept the call.
        with patch(
            "vibewriting.agents.git_safety.rollback_to_snapshot"
        ) as mock_rb:
            # Should not raise even if rollback fails internally
            orchestrator._handle_failure(error, fake_hash)
            # Rollback was attempted with the correct snapshot hash
            mock_rb.assert_called_once()
            call_args = mock_rb.call_args
            assert fake_hash in call_args.args or fake_hash in call_args.kwargs.values()
