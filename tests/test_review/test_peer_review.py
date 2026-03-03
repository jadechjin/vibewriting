"""Tests for peer review module."""

from __future__ import annotations

from pathlib import Path

from vibewriting.review.models import ReviewSeverity
from vibewriting.review.peer_review import (
    generate_review_report,
    render_review_markdown,
    review_evidence,
    review_methodology,
    review_structure,
    save_review_reports,
)


class TestReviewStructure:
    def test_missing_sections(self):
        paper_state = {"sections": []}
        findings = review_structure(paper_state)
        assert len(findings) >= 1
        assert any("Missing required section" in f.issue for f in findings)

    def test_complete_sections(self):
        sections = [
            {"section_id": "abstract", "status": "complete"},
            {"section_id": "introduction", "status": "complete"},
            {"section_id": "methodology", "status": "complete"},
            {"section_id": "results", "status": "complete"},
            {"section_id": "conclusion", "status": "complete"},
        ]
        findings = review_structure({"sections": sections})
        major = [f for f in findings if f.severity == ReviewSeverity.MAJOR]
        assert len(major) == 0

    def test_incomplete_section(self):
        sections = [
            {"section_id": "introduction", "status": "draft"},
        ]
        findings = review_structure({"sections": sections})
        assert any("draft" in f.issue for f in findings)


class TestReviewEvidence:
    def test_no_claims(self, tmp_path: Path):
        d = tmp_path / "paper"
        d.mkdir()
        (d / "test.tex").write_text("No claims\n", encoding="utf-8")
        cards = tmp_path / "cards.jsonl"
        cards.write_text("", encoding="utf-8")
        findings = review_evidence(d, cards)
        assert any("No CLAIM_ID" in f.issue for f in findings)


class TestReviewMethodology:
    def test_no_math(self, tmp_path: Path):
        d = tmp_path / "paper"
        d.mkdir()
        (d / "test.tex").write_text("Just text, no math.\n", encoding="utf-8")
        findings = review_methodology(d, [])
        assert any("mathematical" in f.issue.lower() or "equation" in f.issue.lower() for f in findings)


class TestGenerateReport:
    def test_generates_report(self, tmp_paper_dir: Path, cards_path: Path):
        paper_state = {"sections": [
            {"section_id": "introduction", "status": "complete"},
        ]}
        report = generate_review_report(paper_state, tmp_paper_dir, cards_path)
        assert 0 <= report.overall_score <= 10
        assert report.verdict in ("Accept", "Minor Revision", "Major Revision", "Reject")

    def test_verdict_consistency(self, tmp_paper_dir: Path, cards_path: Path):
        report = generate_review_report({}, tmp_paper_dir, cards_path)
        if report.overall_score < 4:
            assert report.verdict == "Reject"


class TestRenderMarkdown:
    def test_render(self, tmp_paper_dir: Path, cards_path: Path):
        report = generate_review_report({}, tmp_paper_dir, cards_path)
        md = render_review_markdown(report)
        assert "# Peer Review Report" in md
        assert "Score" in md


class TestSaveReports:
    def test_save(self, tmp_paper_dir: Path, cards_path: Path, tmp_path: Path):
        report = generate_review_report({}, tmp_paper_dir, cards_path)
        json_path, md_path = save_review_reports(report, tmp_path / "out")
        assert json_path.exists()
        assert md_path.exists()
