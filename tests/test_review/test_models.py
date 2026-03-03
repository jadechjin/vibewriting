"""Tests for review data models."""

from __future__ import annotations

import json

from vibewriting.review.models import (
    CitationAuditResult,
    PatchReport,
    PeerReviewReport,
    Phase6Report,
    ReviewCategory,
    ReviewFinding,
    ReviewSeverity,
)


class TestReviewFinding:
    def test_serialize(self):
        f = ReviewFinding(
            severity=ReviewSeverity.MAJOR,
            category=ReviewCategory.EVIDENCE,
            location="section:intro",
            issue="Missing citation",
            rationale="Claims need evidence",
        )
        data = json.loads(f.model_dump_json())
        assert data["severity"] == "MAJOR"
        assert data["category"] == "EVIDENCE"

    def test_with_suggestion(self):
        f = ReviewFinding(
            severity=ReviewSeverity.MINOR,
            category=ReviewCategory.LANGUAGE,
            location="line 5",
            issue="Typo",
            rationale="Spelling error",
            suggestion="Fix spelling",
        )
        assert f.suggestion == "Fix spelling"


class TestPeerReviewReport:
    def test_score_bounds(self):
        r = PeerReviewReport(
            overall_score=7.5,
            verdict="Minor Revision",
            summary="Good paper",
            strengths=["Clear writing"],
            weaknesses=["Missing data"],
            detailed_findings=[],
        )
        assert 0 <= r.overall_score <= 10

    def test_serialize_roundtrip(self):
        r = PeerReviewReport(
            overall_score=5.0,
            verdict="Major Revision",
            summary="Needs work",
            strengths=["Novel idea"],
            weaknesses=["Weak evidence"],
            detailed_findings=[],
        )
        data = json.loads(r.model_dump_json())
        r2 = PeerReviewReport.model_validate(data)
        assert r2.overall_score == 5.0
        assert r2.verdict == "Major Revision"

    def test_invalid_score_too_high(self):
        import pytest
        with pytest.raises(Exception):
            PeerReviewReport(
                overall_score=11.0,
                verdict="Accept",
                summary="",
                strengths=[],
                weaknesses=[],
                detailed_findings=[],
            )


class TestCitationAuditResult:
    def test_serialize(self):
        r = CitationAuditResult(
            verified_count=5,
            suspicious_keys=["fake2023"],
            orphan_claims=["EC-0001-002"],
            missing_evidence_cards=[],
        )
        data = json.loads(r.model_dump_json())
        assert data["verified_count"] == 5
        assert "fake2023" in data["suspicious_keys"]


class TestPatchReport:
    def test_serialize(self):
        r = PatchReport(
            round_number=1,
            error_kind="syntax_error",
            target_file="sections/intro.tex",
            lines_changed=3,
            success=True,
            stash_ref="stash@{0}",
        )
        data = json.loads(r.model_dump_json())
        assert data["success"] is True


class TestPhase6Report:
    def test_empty_report(self):
        r = Phase6Report(compilation=[])
        data = json.loads(r.model_dump_json())
        assert data["compilation"] == []
        assert data["citation_audit"] is None
        assert data["peer_review"] is None
