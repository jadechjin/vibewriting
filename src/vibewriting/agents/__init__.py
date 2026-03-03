"""Multi-agent orchestration for vibewriting.

Core components:
- contracts: Pydantic data models for agent communication
- planner: Section task planning and dependency resolution
- merge_protocol: Conflict detection and resolution
- executor: Agent execution abstraction
- orchestrator: Orchestration core
- git_safety: Git snapshot and rollback utilities
"""

from vibewriting.agents.contracts import (
    AgentRole,
    CriticIssue,
    CriticReport,
    FormatterPatch,
    MergeConflict,
    MergeDecision,
    OrchestrationReport,
    OrchestrationRound,
    SectionPatchPayload,
    SectionTask,
)
from vibewriting.agents.executor import AgentExecutor, MockExecutor, SubAgentExecutor
from vibewriting.agents.orchestrator import OrchestratorConfig, WritingOrchestrator
from vibewriting.agents.planner import (
    assign_roles,
    build_section_task_graph,
    get_ready_tasks,
)

__all__ = [
    "AgentRole",
    "CriticIssue",
    "CriticReport",
    "FormatterPatch",
    "MergeConflict",
    "MergeDecision",
    "OrchestrationReport",
    "OrchestrationRound",
    "SectionPatchPayload",
    "SectionTask",
    "AgentExecutor",
    "MockExecutor",
    "SubAgentExecutor",
    "OrchestratorConfig",
    "WritingOrchestrator",
    "assign_roles",
    "build_section_task_graph",
    "get_ready_tasks",
]
