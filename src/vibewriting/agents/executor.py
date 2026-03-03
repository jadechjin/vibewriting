"""Agent executor abstraction for multi-agent orchestration.

Provides a Protocol-based abstraction for executing section tasks.
Implementations:
- MockExecutor: For testing
- SubAgentExecutor: For Claude Code sub-agent execution (placeholder)
- TeamExecutor: Reserved for Agent Teams (not implemented)
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from vibewriting.agents.contracts import (
    AgentRole,
    CriticReport,
    FormatterPatch,
    SectionPatchPayload,
    SectionTask,
)

logger = logging.getLogger(__name__)


# Type alias for executor return types
TaskResult = SectionPatchPayload | CriticReport | FormatterPatch


@runtime_checkable
class AgentExecutor(Protocol):
    """Protocol for agent task executors.

    All implementations must provide a run_task method that:
    1. Accepts a SectionTask and optional context
    2. Returns the appropriate payload type based on task role:
       - STORYTELLER/ANALYST -> SectionPatchPayload
       - CRITIC -> CriticReport
       - FORMATTER -> FormatterPatch
    """

    async def run_task(
        self,
        task: SectionTask,
        context: dict | None = None,
    ) -> TaskResult:
        """Execute a section task and return the result.

        Args:
            task: The section task to execute.
            context: Additional context (e.g., existing drafts, paper state).

        Returns:
            Appropriate payload type based on task.role.
        """
        ...


class MockExecutor:
    """Mock executor for testing.

    Returns deterministic payloads based on task role.
    Useful for unit testing orchestration logic without LLM calls.
    """

    def __init__(
        self,
        *,
        default_tex: str = "Mock generated content.",
        default_score: float = 0.8,
        custom_responses: dict[str, TaskResult] | None = None,
    ) -> None:
        """Initialize mock executor.

        Args:
            default_tex: Default tex content for patch payloads.
            default_score: Default score for critic reports.
            custom_responses: Optional {section_id: response} overrides.
        """
        self._default_tex = default_tex
        self._default_score = default_score
        self._custom_responses = custom_responses or {}
        self._call_history: list[SectionTask] = []

    @property
    def call_history(self) -> list[SectionTask]:
        """Return the list of tasks this executor was called with."""
        return list(self._call_history)

    @property
    def call_count(self) -> int:
        """Return the number of times run_task was called."""
        return len(self._call_history)

    async def run_task(
        self,
        task: SectionTask,
        context: dict | None = None,
    ) -> TaskResult:
        """Return a mock response based on task role."""
        self._call_history.append(task)

        # Check for custom response
        if task.section_id in self._custom_responses:
            return self._custom_responses[task.section_id]

        if task.role in (AgentRole.STORYTELLER, AgentRole.ANALYST):
            return SectionPatchPayload(
                section_id=task.section_id,
                tex_content=self._default_tex,
                claim_ids=list(task.context.get("expected_claims", [])) if task.context else [],
                word_count=len(self._default_tex.split()),
            )

        elif task.role == AgentRole.CRITIC:
            return CriticReport(
                section_id=task.section_id,
                overall_score=self._default_score,
            )

        elif task.role == AgentRole.FORMATTER:
            return FormatterPatch(
                section_id=task.section_id,
                tex_content=self._default_tex,
            )

        # Fallback (should not reach here)
        return SectionPatchPayload(
            section_id=task.section_id,
            tex_content=self._default_tex,
        )


class SubAgentExecutor:
    """Placeholder for Claude Code sub-agent executor.

    In production, this would:
    1. Build a prompt from the SectionTask
    2. Call Claude Code sub-agent via Task tool
    3. Parse the returned JSON into the appropriate payload

    Currently raises NotImplementedError.
    """

    def __init__(self, *, model: str = "sonnet") -> None:
        self._model = model

    async def run_task(
        self,
        task: SectionTask,
        context: dict | None = None,
    ) -> TaskResult:
        """Execute via Claude Code sub-agent (not yet implemented)."""
        raise NotImplementedError(
            "SubAgentExecutor is a placeholder. "
            "Use MockExecutor for testing or implement LLM integration."
        )
