"""Tests for agents.executor module."""

from __future__ import annotations

import pytest

from vibewriting.agents.contracts import (
    AgentRole,
    CriticReport,
    FormatterPatch,
    SectionPatchPayload,
    SectionTask,
)
from vibewriting.agents.executor import (
    AgentExecutor,
    MockExecutor,
    SubAgentExecutor,
    TaskResult,
)


# ---------------------------------------------------------------------------
# TestAgentExecutorProtocol
# ---------------------------------------------------------------------------


class TestAgentExecutorProtocol:
    def test_mock_executor_satisfies_protocol(self) -> None:
        executor = MockExecutor()
        assert isinstance(executor, AgentExecutor)

    def test_sub_agent_executor_satisfies_protocol(self) -> None:
        executor = SubAgentExecutor()
        assert isinstance(executor, AgentExecutor)


# ---------------------------------------------------------------------------
# TestMockExecutor
# ---------------------------------------------------------------------------


class TestMockExecutor:
    @pytest.mark.asyncio
    async def test_storyteller_returns_patch_payload(self) -> None:
        executor = MockExecutor()
        task = SectionTask(section_id="sec-intro", role=AgentRole.STORYTELLER)
        result = await executor.run_task(task)
        assert isinstance(result, SectionPatchPayload)
        assert result.section_id == "sec-intro"

    @pytest.mark.asyncio
    async def test_analyst_returns_patch_payload(self) -> None:
        executor = MockExecutor()
        task = SectionTask(section_id="sec-method", role=AgentRole.ANALYST)
        result = await executor.run_task(task)
        assert isinstance(result, SectionPatchPayload)
        assert result.section_id == "sec-method"

    @pytest.mark.asyncio
    async def test_critic_returns_critic_report(self) -> None:
        executor = MockExecutor()
        task = SectionTask(section_id="sec-results", role=AgentRole.CRITIC)
        result = await executor.run_task(task)
        assert isinstance(result, CriticReport)
        assert result.section_id == "sec-results"

    @pytest.mark.asyncio
    async def test_formatter_returns_formatter_patch(self) -> None:
        executor = MockExecutor()
        task = SectionTask(section_id="sec-conclusion", role=AgentRole.FORMATTER)
        result = await executor.run_task(task)
        assert isinstance(result, FormatterPatch)
        assert result.section_id == "sec-conclusion"

    @pytest.mark.asyncio
    async def test_call_history_tracks_tasks(self) -> None:
        executor = MockExecutor()
        task1 = SectionTask(section_id="sec-intro", role=AgentRole.STORYTELLER)
        task2 = SectionTask(section_id="sec-method", role=AgentRole.CRITIC)
        await executor.run_task(task1)
        await executor.run_task(task2)
        history = executor.call_history
        assert len(history) == 2
        assert history[0].section_id == "sec-intro"
        assert history[1].section_id == "sec-method"

    @pytest.mark.asyncio
    async def test_call_count(self) -> None:
        executor = MockExecutor()
        assert executor.call_count == 0
        task = SectionTask(section_id="sec-intro", role=AgentRole.STORYTELLER)
        await executor.run_task(task)
        assert executor.call_count == 1
        await executor.run_task(task)
        assert executor.call_count == 2

    @pytest.mark.asyncio
    async def test_custom_response_override(self) -> None:
        custom_patch = SectionPatchPayload(
            section_id="sec-intro",
            tex_content="Custom override content.",
        )
        executor = MockExecutor(custom_responses={"sec-intro": custom_patch})
        task = SectionTask(section_id="sec-intro", role=AgentRole.CRITIC)
        result = await executor.run_task(task)
        # custom response overrides role-based dispatch
        assert result is custom_patch
        assert isinstance(result, SectionPatchPayload)

    @pytest.mark.asyncio
    async def test_default_tex_configurable(self) -> None:
        custom_tex = "Custom default LaTeX content."
        executor = MockExecutor(default_tex=custom_tex)
        task = SectionTask(section_id="sec-intro", role=AgentRole.STORYTELLER)
        result = await executor.run_task(task)
        assert isinstance(result, SectionPatchPayload)
        assert result.tex_content == custom_tex

    @pytest.mark.asyncio
    async def test_default_score_configurable(self) -> None:
        executor = MockExecutor(default_score=0.42)
        task = SectionTask(section_id="sec-intro", role=AgentRole.CRITIC)
        result = await executor.run_task(task)
        assert isinstance(result, CriticReport)
        assert result.overall_score == pytest.approx(0.42)

    @pytest.mark.asyncio
    async def test_call_history_returns_copy(self) -> None:
        executor = MockExecutor()
        task = SectionTask(section_id="sec-intro", role=AgentRole.STORYTELLER)
        await executor.run_task(task)
        history = executor.call_history
        history.clear()
        # internal state should not be mutated
        assert executor.call_count == 1

    @pytest.mark.asyncio
    async def test_context_expected_claims_propagated(self) -> None:
        executor = MockExecutor()
        task = SectionTask(
            section_id="sec-intro",
            role=AgentRole.STORYTELLER,
            context={"expected_claims": ["EC-2024-001", "EC-2024-002"]},
        )
        result = await executor.run_task(task)
        assert isinstance(result, SectionPatchPayload)
        assert result.claim_ids == ["EC-2024-001", "EC-2024-002"]


# ---------------------------------------------------------------------------
# TestSubAgentExecutor
# ---------------------------------------------------------------------------


class TestSubAgentExecutor:
    @pytest.mark.asyncio
    async def test_raises_not_implemented(self) -> None:
        executor = SubAgentExecutor()
        task = SectionTask(section_id="sec-intro", role=AgentRole.STORYTELLER)
        with pytest.raises(NotImplementedError):
            await executor.run_task(task)

    def test_model_stored(self) -> None:
        executor = SubAgentExecutor(model="opus")
        assert executor._model == "opus"

    def test_default_model_is_sonnet(self) -> None:
        executor = SubAgentExecutor()
        assert executor._model == "sonnet"
