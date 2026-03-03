"""Agent communication contracts for multi-agent orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AgentRole(str, Enum):
    """Roles for multi-agent writing orchestration."""

    STORYTELLER = "storyteller"
    ANALYST = "analyst"
    CRITIC = "critic"
    FORMATTER = "formatter"


class SectionTask(BaseModel):
    """A task assigned to a role agent for a specific section."""

    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    role: AgentRole
    evidence_cards: list[dict] = Field(default_factory=list)
    assets: list[dict] = Field(default_factory=list)
    context: dict = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)


class SectionPatchPayload(BaseModel):
    """Return payload from Storyteller/Analyst agents."""

    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    tex_content: str = Field(min_length=1)
    claim_ids: list[str] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)
    citation_keys: list[str] = Field(default_factory=list)
    new_terms: dict[str, str] = Field(default_factory=dict)
    new_symbols: dict[str, str] = Field(default_factory=dict)
    word_count: int = Field(default=0, ge=0)


class CriticIssue(BaseModel):
    """A single issue found by the Critic agent."""

    model_config = ConfigDict(extra="forbid")

    location: str
    issue_type: Literal["logic", "evidence", "clarity", "structure", "citation"]
    severity: Literal["critical", "warning", "suggestion"]
    description: str = Field(min_length=1)
    suggested_fix: str = ""


class CriticReport(BaseModel):
    """Return payload from Critic agent."""

    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    issues: list[CriticIssue] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    severity_scores: dict[str, float] = Field(default_factory=dict)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)


class FormatterPatch(BaseModel):
    """Return payload from Formatter agent."""

    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    tex_content: str = Field(min_length=1)
    term_replacements: dict[str, str] = Field(default_factory=dict)
    symbol_updates: dict[str, str] = Field(default_factory=dict)


class MergeConflict(BaseModel):
    """A detected conflict during merge."""

    model_config = ConfigDict(extra="forbid")

    conflict_type: Literal["terminology", "symbol", "citation", "narrative"]
    affected_sections: list[str] = Field(default_factory=list)
    description: str = Field(min_length=1)
    conflicting_values: dict[str, str] = Field(default_factory=dict)


class MergeDecision(BaseModel):
    """Resolution decision for a merge conflict."""

    model_config = ConfigDict(extra="forbid")

    conflict: MergeConflict
    resolution: str = Field(min_length=1)
    resolved_value: str = ""
    requires_human_review: bool = False


class OrchestrationRound(BaseModel):
    """Record of a single orchestration round."""

    model_config = ConfigDict(extra="forbid")

    round_number: int = Field(ge=1)
    sections_processed: list[str] = Field(default_factory=list)
    payloads_received: int = Field(default=0, ge=0)
    conflicts_detected: int = Field(default=0, ge=0)
    conflicts_resolved: int = Field(default=0, ge=0)
    gates_passed: bool = False


class OrchestrationReport(BaseModel):
    """Aggregate report from the entire orchestration process."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str = Field(min_length=1)
    rounds: list[OrchestrationRound] = Field(default_factory=list)
    total_sections: int = Field(default=0, ge=0)
    sections_completed: int = Field(default=0, ge=0)
    total_conflicts: int = Field(default=0, ge=0)
    unresolved_conflicts: int = Field(default=0, ge=0)
    final_gate_report_summary: str = ""
    started_at: datetime = Field(default_factory=_utcnow)
    finished_at: datetime | None = None
    success: bool = False
