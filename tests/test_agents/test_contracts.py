"""Tests for agent communication contracts."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

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


class TestAgentRole:
    """Tests for AgentRole enum."""

    def test_all_roles_defined(self) -> None:
        assert AgentRole.STORYTELLER == "storyteller"
        assert AgentRole.ANALYST == "analyst"
        assert AgentRole.CRITIC == "critic"
        assert AgentRole.FORMATTER == "formatter"

    def test_role_is_str_enum(self) -> None:
        assert isinstance(AgentRole.STORYTELLER, str)

    def test_role_values(self) -> None:
        values = {r.value for r in AgentRole}
        assert values == {"storyteller", "analyst", "critic", "formatter"}

    def test_role_from_string(self) -> None:
        assert AgentRole("storyteller") == AgentRole.STORYTELLER
        assert AgentRole("analyst") == AgentRole.ANALYST

    def test_invalid_role_raises(self) -> None:
        with pytest.raises(ValueError):
            AgentRole("invalid_role")


class TestSectionTask:
    """Tests for SectionTask model."""

    def test_create_minimal(self) -> None:
        task = SectionTask(section_id="sec-1", role=AgentRole.STORYTELLER)
        assert task.section_id == "sec-1"
        assert task.role == AgentRole.STORYTELLER
        assert task.evidence_cards == []
        assert task.assets == []
        assert task.context == {}
        assert task.dependencies == []

    def test_create_full(self, sample_section_task: SectionTask) -> None:
        assert sample_section_task.section_id == "sec-intro"
        assert len(sample_section_task.evidence_cards) == 1
        assert len(sample_section_task.assets) == 1

    def test_section_id_min_length(self) -> None:
        with pytest.raises(ValidationError):
            SectionTask(section_id="", role=AgentRole.ANALYST)

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            SectionTask(section_id="sec-1", role=AgentRole.ANALYST, unknown_field="x")

    def test_serialization_roundtrip(self, sample_section_task: SectionTask) -> None:
        json_str = sample_section_task.model_dump_json()
        restored = SectionTask.model_validate_json(json_str)
        assert restored == sample_section_task

    def test_model_dump(self) -> None:
        task = SectionTask(section_id="sec-2", role=AgentRole.CRITIC)
        data = task.model_dump()
        assert data["section_id"] == "sec-2"
        assert data["role"] == "critic"

    def test_role_as_string_accepted(self) -> None:
        task = SectionTask(section_id="sec-1", role="formatter")
        assert task.role == AgentRole.FORMATTER


class TestSectionPatchPayload:
    """Tests for SectionPatchPayload model."""

    def test_create_minimal(self) -> None:
        payload = SectionPatchPayload(
            section_id="sec-1",
            tex_content=r"\section{Intro}",
        )
        assert payload.section_id == "sec-1"
        assert payload.word_count == 0
        assert payload.claim_ids == []
        assert payload.citation_keys == []

    def test_create_full(self, sample_section_patch: SectionPatchPayload) -> None:
        assert sample_section_patch.word_count == 150
        assert len(sample_section_patch.claim_ids) == 2
        assert len(sample_section_patch.citation_keys) == 2

    def test_section_id_required(self) -> None:
        with pytest.raises(ValidationError):
            SectionPatchPayload(tex_content=r"\section{Intro}")

    def test_tex_content_required(self) -> None:
        with pytest.raises(ValidationError):
            SectionPatchPayload(section_id="sec-1")

    def test_section_id_empty_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SectionPatchPayload(section_id="", tex_content=r"\section{Intro}")

    def test_tex_content_empty_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SectionPatchPayload(section_id="sec-1", tex_content="")

    def test_word_count_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            SectionPatchPayload(
                section_id="sec-1",
                tex_content=r"\section{Intro}",
                word_count=-1,
            )

    def test_word_count_zero_accepted(self) -> None:
        payload = SectionPatchPayload(
            section_id="sec-1",
            tex_content=r"\section{Intro}",
            word_count=0,
        )
        assert payload.word_count == 0

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            SectionPatchPayload(
                section_id="sec-1",
                tex_content=r"\section{Intro}",
                extra_field="forbidden",
            )

    def test_serialization_roundtrip(
        self, sample_section_patch: SectionPatchPayload
    ) -> None:
        json_str = sample_section_patch.model_dump_json()
        restored = SectionPatchPayload.model_validate_json(json_str)
        assert restored == sample_section_patch


class TestCriticIssue:
    """Tests for CriticIssue model."""

    def test_create_minimal(self) -> None:
        issue = CriticIssue(
            location="paragraph 1",
            issue_type="logic",
            severity="critical",
            description="Missing evidence.",
        )
        assert issue.suggested_fix == ""

    def test_all_issue_types(self) -> None:
        valid_types = ["logic", "evidence", "clarity", "structure", "citation"]
        for issue_type in valid_types:
            issue = CriticIssue(
                location="loc",
                issue_type=issue_type,
                severity="warning",
                description="desc",
            )
            assert issue.issue_type == issue_type

    def test_invalid_issue_type(self) -> None:
        with pytest.raises(ValidationError):
            CriticIssue(
                location="loc",
                issue_type="invalid_type",
                severity="warning",
                description="desc",
            )

    def test_all_severities(self) -> None:
        valid_severities = ["critical", "warning", "suggestion"]
        for severity in valid_severities:
            issue = CriticIssue(
                location="loc",
                issue_type="logic",
                severity=severity,
                description="desc",
            )
            assert issue.severity == severity

    def test_invalid_severity(self) -> None:
        with pytest.raises(ValidationError):
            CriticIssue(
                location="loc",
                issue_type="logic",
                severity="fatal",
                description="desc",
            )

    def test_description_min_length(self) -> None:
        with pytest.raises(ValidationError):
            CriticIssue(
                location="loc",
                issue_type="logic",
                severity="warning",
                description="",
            )

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            CriticIssue(
                location="loc",
                issue_type="logic",
                severity="warning",
                description="desc",
                unknown="x",
            )

    def test_serialization_roundtrip(self, sample_critic_issue: CriticIssue) -> None:
        json_str = sample_critic_issue.model_dump_json()
        restored = CriticIssue.model_validate_json(json_str)
        assert restored == sample_critic_issue


class TestCriticReport:
    """Tests for CriticReport model."""

    def test_create_minimal(self) -> None:
        report = CriticReport(section_id="sec-1")
        assert report.overall_score == 0.0
        assert report.issues == []
        assert report.suggestions == []

    def test_overall_score_range_valid(self) -> None:
        report = CriticReport(section_id="sec-1", overall_score=0.75)
        assert report.overall_score == 0.75

    def test_overall_score_zero(self) -> None:
        report = CriticReport(section_id="sec-1", overall_score=0.0)
        assert report.overall_score == 0.0

    def test_overall_score_one(self) -> None:
        report = CriticReport(section_id="sec-1", overall_score=1.0)
        assert report.overall_score == 1.0

    def test_overall_score_below_zero(self) -> None:
        with pytest.raises(ValidationError):
            CriticReport(section_id="sec-1", overall_score=-0.1)

    def test_overall_score_above_one(self) -> None:
        with pytest.raises(ValidationError):
            CriticReport(section_id="sec-1", overall_score=1.1)

    def test_section_id_min_length(self) -> None:
        with pytest.raises(ValidationError):
            CriticReport(section_id="")

    def test_with_issues(self, sample_critic_report: CriticReport) -> None:
        assert len(sample_critic_report.issues) == 1
        assert sample_critic_report.issues[0].issue_type == "logic"

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            CriticReport(section_id="sec-1", extra="forbidden")

    def test_serialization_roundtrip(
        self, sample_critic_report: CriticReport
    ) -> None:
        json_str = sample_critic_report.model_dump_json()
        restored = CriticReport.model_validate_json(json_str)
        assert restored == sample_critic_report


class TestFormatterPatch:
    """Tests for FormatterPatch model."""

    def test_create_minimal(self) -> None:
        patch = FormatterPatch(
            section_id="sec-1",
            tex_content=r"\section{Intro}",
        )
        assert patch.term_replacements == {}
        assert patch.symbol_updates == {}

    def test_section_id_min_length(self) -> None:
        with pytest.raises(ValidationError):
            FormatterPatch(section_id="", tex_content=r"\section{Intro}")

    def test_tex_content_min_length(self) -> None:
        with pytest.raises(ValidationError):
            FormatterPatch(section_id="sec-1", tex_content="")

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            FormatterPatch(
                section_id="sec-1",
                tex_content=r"\section{Intro}",
                forbidden="x",
            )

    def test_serialization_roundtrip(
        self, sample_formatter_patch: FormatterPatch
    ) -> None:
        json_str = sample_formatter_patch.model_dump_json()
        restored = FormatterPatch.model_validate_json(json_str)
        assert restored == sample_formatter_patch


class TestMergeConflict:
    """Tests for MergeConflict model."""

    def test_create_minimal(self) -> None:
        conflict = MergeConflict(
            conflict_type="terminology",
            description="Conflicting term usage.",
        )
        assert conflict.affected_sections == []
        assert conflict.conflicting_values == {}

    def test_all_conflict_types(self) -> None:
        valid_types = ["terminology", "symbol", "citation", "narrative"]
        for conflict_type in valid_types:
            conflict = MergeConflict(
                conflict_type=conflict_type,
                description="desc",
            )
            assert conflict.conflict_type == conflict_type

    def test_invalid_conflict_type(self) -> None:
        with pytest.raises(ValidationError):
            MergeConflict(conflict_type="invalid", description="desc")

    def test_description_min_length(self) -> None:
        with pytest.raises(ValidationError):
            MergeConflict(conflict_type="terminology", description="")

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            MergeConflict(
                conflict_type="terminology",
                description="desc",
                unknown="x",
            )

    def test_serialization_roundtrip(
        self, sample_merge_conflict: MergeConflict
    ) -> None:
        json_str = sample_merge_conflict.model_dump_json()
        restored = MergeConflict.model_validate_json(json_str)
        assert restored == sample_merge_conflict


class TestMergeDecision:
    """Tests for MergeDecision model."""

    def test_create_minimal(self, sample_merge_conflict: MergeConflict) -> None:
        decision = MergeDecision(
            conflict=sample_merge_conflict,
            resolution="Use consistent terminology.",
        )
        assert decision.resolved_value == ""
        assert decision.requires_human_review is False

    def test_resolution_min_length(self, sample_merge_conflict: MergeConflict) -> None:
        with pytest.raises(ValidationError):
            MergeDecision(conflict=sample_merge_conflict, resolution="")

    def test_requires_human_review(
        self, sample_merge_conflict: MergeConflict
    ) -> None:
        decision = MergeDecision(
            conflict=sample_merge_conflict,
            resolution="Needs expert review.",
            requires_human_review=True,
        )
        assert decision.requires_human_review is True

    def test_extra_fields_forbidden(
        self, sample_merge_conflict: MergeConflict
    ) -> None:
        with pytest.raises(ValidationError):
            MergeDecision(
                conflict=sample_merge_conflict,
                resolution="resolve",
                extra="forbidden",
            )

    def test_serialization_roundtrip(
        self, sample_merge_decision: MergeDecision
    ) -> None:
        json_str = sample_merge_decision.model_dump_json()
        restored = MergeDecision.model_validate_json(json_str)
        assert restored == sample_merge_decision

    def test_nested_conflict_preserved(
        self, sample_merge_decision: MergeDecision
    ) -> None:
        assert sample_merge_decision.conflict.conflict_type == "terminology"
        assert len(sample_merge_decision.conflict.affected_sections) == 2


class TestOrchestrationRound:
    """Tests for OrchestrationRound model."""

    def test_create_minimal(self) -> None:
        rnd = OrchestrationRound(round_number=1)
        assert rnd.sections_processed == []
        assert rnd.payloads_received == 0
        assert rnd.conflicts_detected == 0
        assert rnd.conflicts_resolved == 0
        assert rnd.gates_passed is False

    def test_round_number_ge_one(self) -> None:
        with pytest.raises(ValidationError):
            OrchestrationRound(round_number=0)

    def test_round_number_negative(self) -> None:
        with pytest.raises(ValidationError):
            OrchestrationRound(round_number=-1)

    def test_payloads_received_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            OrchestrationRound(round_number=1, payloads_received=-1)

    def test_conflicts_detected_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            OrchestrationRound(round_number=1, conflicts_detected=-1)

    def test_conflicts_resolved_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            OrchestrationRound(round_number=1, conflicts_resolved=-1)

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            OrchestrationRound(round_number=1, unknown="x")

    def test_serialization_roundtrip(
        self, sample_orchestration_round: OrchestrationRound
    ) -> None:
        json_str = sample_orchestration_round.model_dump_json()
        restored = OrchestrationRound.model_validate_json(json_str)
        assert restored == sample_orchestration_round


class TestOrchestrationReport:
    """Tests for OrchestrationReport model."""

    def test_create_minimal(self) -> None:
        report = OrchestrationReport(paper_id="paper-001")
        assert report.rounds == []
        assert report.total_sections == 0
        assert report.sections_completed == 0
        assert report.success is False
        assert report.finished_at is None

    def test_paper_id_min_length(self) -> None:
        with pytest.raises(ValidationError):
            OrchestrationReport(paper_id="")

    def test_total_sections_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            OrchestrationReport(paper_id="paper-001", total_sections=-1)

    def test_sections_completed_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            OrchestrationReport(paper_id="paper-001", sections_completed=-1)

    def test_total_conflicts_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            OrchestrationReport(paper_id="paper-001", total_conflicts=-1)

    def test_unresolved_conflicts_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            OrchestrationReport(paper_id="paper-001", unresolved_conflicts=-1)

    def test_started_at_default_utc(self) -> None:
        report = OrchestrationReport(paper_id="paper-001")
        assert report.started_at.tzinfo is not None

    def test_finished_at_optional(self) -> None:
        report = OrchestrationReport(paper_id="paper-001")
        assert report.finished_at is None

    def test_finished_at_can_be_set(self) -> None:
        now = datetime.now(UTC)
        report = OrchestrationReport(paper_id="paper-001", finished_at=now)
        assert report.finished_at == now

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            OrchestrationReport(paper_id="paper-001", unknown="x")

    def test_full_construction(
        self, sample_orchestration_report: OrchestrationReport
    ) -> None:
        assert sample_orchestration_report.paper_id == "paper-2024-001"
        assert len(sample_orchestration_report.rounds) == 1
        assert sample_orchestration_report.total_sections == 6
        assert sample_orchestration_report.sections_completed == 2
        assert sample_orchestration_report.success is True

    def test_serialization_roundtrip(
        self, sample_orchestration_report: OrchestrationReport
    ) -> None:
        json_str = sample_orchestration_report.model_dump_json()
        restored = OrchestrationReport.model_validate_json(json_str)
        assert restored == sample_orchestration_report

    def test_json_is_valid_json(
        self, sample_orchestration_report: OrchestrationReport
    ) -> None:
        json_str = sample_orchestration_report.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["paper_id"] == "paper-2024-001"
        assert parsed["success"] is True

    def test_nested_rounds_preserved(
        self, sample_orchestration_report: OrchestrationReport
    ) -> None:
        rnd = sample_orchestration_report.rounds[0]
        assert rnd.round_number == 1
        assert rnd.gates_passed is True
        assert "sec-intro" in rnd.sections_processed
