"""Shared fixtures for agent contract tests."""

from __future__ import annotations

import pytest

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


@pytest.fixture
def sample_section_task() -> SectionTask:
    return SectionTask(
        section_id="sec-intro",
        role=AgentRole.STORYTELLER,
        evidence_cards=[{"claim_id": "EC-2024-001", "content": "test evidence"}],
        assets=[{"asset_id": "ASSET-2024-001", "type": "figure"}],
        context={"outline": "Introduction outline"},
        dependencies=[],
    )


@pytest.fixture
def sample_section_patch() -> SectionPatchPayload:
    return SectionPatchPayload(
        section_id="sec-intro",
        tex_content=r"\section{Introduction}\nThis is the introduction.",
        claim_ids=["EC-2024-001", "EC-2024-002"],
        asset_ids=["ASSET-2024-001"],
        citation_keys=["smith2024", "jones2023"],
        new_terms={"term1": "definition1"},
        new_symbols={"alpha": "learning rate"},
        word_count=150,
    )


@pytest.fixture
def sample_critic_issue() -> CriticIssue:
    return CriticIssue(
        location="paragraph 3",
        issue_type="logic",
        severity="warning",
        description="The argument lacks supporting evidence.",
        suggested_fix="Add citation from related work.",
    )


@pytest.fixture
def sample_critic_report(sample_critic_issue: CriticIssue) -> CriticReport:
    return CriticReport(
        section_id="sec-intro",
        issues=[sample_critic_issue],
        suggestions=["Consider adding more context."],
        severity_scores={"logic": 0.7, "evidence": 0.5},
        overall_score=0.65,
    )


@pytest.fixture
def sample_formatter_patch() -> FormatterPatch:
    return FormatterPatch(
        section_id="sec-intro",
        tex_content=r"\section{Introduction}\nFormatted content.",
        term_replacements={"old_term": "new_term"},
        symbol_updates={"alpha": "\\alpha"},
    )


@pytest.fixture
def sample_merge_conflict() -> MergeConflict:
    return MergeConflict(
        conflict_type="terminology",
        affected_sections=["sec-intro", "sec-related"],
        description="Term 'learning rate' vs 'step size' used inconsistently.",
        conflicting_values={"sec-intro": "learning rate", "sec-related": "step size"},
    )


@pytest.fixture
def sample_merge_decision(sample_merge_conflict: MergeConflict) -> MergeDecision:
    return MergeDecision(
        conflict=sample_merge_conflict,
        resolution="Use 'learning rate' consistently throughout the paper.",
        resolved_value="learning rate",
        requires_human_review=False,
    )


@pytest.fixture
def sample_orchestration_round() -> OrchestrationRound:
    return OrchestrationRound(
        round_number=1,
        sections_processed=["sec-intro", "sec-related"],
        payloads_received=2,
        conflicts_detected=1,
        conflicts_resolved=1,
        gates_passed=True,
    )


@pytest.fixture
def sample_orchestration_report(
    sample_orchestration_round: OrchestrationRound,
) -> OrchestrationReport:
    return OrchestrationReport(
        paper_id="paper-2024-001",
        rounds=[sample_orchestration_round],
        total_sections=6,
        sections_completed=2,
        total_conflicts=1,
        unresolved_conflicts=0,
        final_gate_report_summary="All gates passed.",
        success=True,
    )
