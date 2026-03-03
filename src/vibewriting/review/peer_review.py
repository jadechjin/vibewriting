"""Simulated peer review: structure, evidence, and methodology checks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from vibewriting.review.models import (
    PeerReviewReport,
    ReviewCategory,
    ReviewFinding,
    ReviewSeverity,
)

_REQUIRED_SECTIONS = {"abstract", "introduction", "methodology", "results", "conclusion"}
_MATH_RE = re.compile(r"\\begin\{(?:equation|align|gather|multline)\}")
_FIGURE_REF_RE = re.compile(r"\\(?:ref|autoref|cref)\{fig:")
_TABLE_REF_RE = re.compile(r"\\(?:ref|autoref|cref)\{tab:")
_CLAIM_ID_RE = re.compile(r"%%\s*CLAIM_ID\s*:\s*(\S+)")


def review_structure(paper_state: dict[str, Any]) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    sections = paper_state.get("sections", [])
    section_ids = {s.get("section_id", "").lower() for s in sections}

    for req in _REQUIRED_SECTIONS:
        if not any(req in sid for sid in section_ids):
            findings.append(ReviewFinding(
                severity=ReviewSeverity.MAJOR,
                category=ReviewCategory.STRUCTURE,
                location="paper_state",
                issue=f"Missing required section: {req}",
                rationale=f"A complete paper must include a {req} section",
            ))

    for section in sections:
        status = section.get("status", "")
        if status and status != "complete":
            findings.append(ReviewFinding(
                severity=ReviewSeverity.MINOR,
                category=ReviewCategory.STRUCTURE,
                location=f"section:{section.get('section_id', '?')}",
                issue=f"Section status is '{status}', not 'complete'",
                rationale="All sections should be finalized before submission",
            ))

    return findings


def review_evidence(
    paper_dir: Path, cards_path: Path,
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []

    all_claim_ids: list[str] = []
    for tex_file in paper_dir.rglob("*.tex"):
        content = tex_file.read_text(encoding="utf-8")
        all_claim_ids.extend(_CLAIM_ID_RE.findall(content))

    if not all_claim_ids:
        findings.append(ReviewFinding(
            severity=ReviewSeverity.MAJOR,
            category=ReviewCategory.EVIDENCE,
            location="paper_dir",
            issue="No CLAIM_ID annotations found in any .tex file",
            rationale="Every claim should be traceable to an evidence card",
        ))
        return findings

    card_types: dict[str, str] = {}
    if cards_path.exists():
        for line in cards_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                card = json.loads(line)
                card_types[card.get("claim_id", "")] = card.get("evidence_type", "")
            except json.JSONDecodeError:
                continue

    type_counts: dict[str, int] = {}
    for cid in all_claim_ids:
        etype = card_types.get(cid, "unknown")
        type_counts[etype] = type_counts.get(etype, 0) + 1

    if "empirical" not in type_counts and "survey" not in type_counts:
        findings.append(ReviewFinding(
            severity=ReviewSeverity.MAJOR,
            category=ReviewCategory.EVIDENCE,
            location="evidence_cards",
            issue="No empirical or survey evidence found",
            rationale="A balanced paper should include empirical evidence",
            suggestion="Add empirical studies or survey data to support claims",
        ))

    return findings


def review_methodology(
    paper_dir: Path, asset_manifest: list[dict[str, Any]],
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []

    all_tex = ""
    for tex_file in paper_dir.rglob("*.tex"):
        all_tex += tex_file.read_text(encoding="utf-8") + "\n"

    has_math = bool(_MATH_RE.search(all_tex))
    has_fig_ref = bool(_FIGURE_REF_RE.search(all_tex))
    has_tab_ref = bool(_TABLE_REF_RE.search(all_tex))

    if not has_math:
        findings.append(ReviewFinding(
            severity=ReviewSeverity.MINOR,
            category=ReviewCategory.METHODOLOGY,
            location="paper_dir",
            issue="No mathematical equations found",
            rationale="Methodology sections typically include formal definitions",
            suggestion="Consider adding equations for key algorithms or models",
        ))

    if not has_fig_ref and not has_tab_ref:
        findings.append(ReviewFinding(
            severity=ReviewSeverity.MINOR,
            category=ReviewCategory.METHODOLOGY,
            location="paper_dir",
            issue="No figure or table references found in text",
            rationale="Results should reference visual evidence",
            suggestion="Add \\ref{fig:...} or \\ref{tab:...} references",
        ))

    if asset_manifest and not has_fig_ref:
        findings.append(ReviewFinding(
            severity=ReviewSeverity.MINOR,
            category=ReviewCategory.METHODOLOGY,
            location="asset_manifest",
            issue=f"{len(asset_manifest)} assets in manifest but no figure references in text",
            rationale="Generated assets should be referenced in the paper",
        ))

    return findings


def _compute_verdict(score: float) -> str:
    if score >= 8:
        return "Accept"
    if score >= 6:
        return "Minor Revision"
    if score >= 4:
        return "Major Revision"
    return "Reject"


def generate_review_report(
    paper_state: dict[str, Any],
    paper_dir: Path,
    cards_path: Path,
    asset_manifest: list[dict[str, Any]] | None = None,
) -> PeerReviewReport:
    all_findings: list[ReviewFinding] = []

    all_findings.extend(review_structure(paper_state))
    all_findings.extend(review_evidence(paper_dir, cards_path))
    all_findings.extend(review_methodology(paper_dir, asset_manifest or []))

    critical = sum(1 for f in all_findings if f.severity == ReviewSeverity.CRITICAL)
    major = sum(1 for f in all_findings if f.severity == ReviewSeverity.MAJOR)
    minor = sum(1 for f in all_findings if f.severity == ReviewSeverity.MINOR)

    score = max(0.0, 10.0 - critical * 3.0 - major * 1.5 - minor * 0.5)
    verdict = _compute_verdict(score)

    strengths: list[str] = []
    weaknesses: list[str] = []
    if not critical:
        strengths.append("No critical issues found")
    if major == 0:
        strengths.append("No major structural or evidence gaps")
    for f in all_findings:
        if f.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.MAJOR):
            weaknesses.append(f.issue)

    return PeerReviewReport(
        overall_score=round(score, 1),
        verdict=verdict,
        summary=f"Review found {len(all_findings)} issues: {critical} critical, {major} major, {minor} minor",
        strengths=strengths,
        weaknesses=weaknesses,
        detailed_findings=all_findings,
    )


def render_review_markdown(report: PeerReviewReport) -> str:
    lines = [
        f"# Peer Review Report",
        f"",
        f"**Score**: {report.overall_score}/10",
        f"**Verdict**: {report.verdict}",
        f"",
        f"## Summary",
        report.summary,
        f"",
        f"## Strengths",
    ]
    for s in report.strengths:
        lines.append(f"- {s}")
    lines.append("")
    lines.append("## Weaknesses")
    for w in report.weaknesses:
        lines.append(f"- {w}")
    lines.append("")
    lines.append("## Detailed Findings")
    for f in report.detailed_findings:
        lines.append(f"- [{f.severity.value}] [{f.category.value}] {f.location}: {f.issue}")
        if f.suggestion:
            lines.append(f"  - Suggestion: {f.suggestion}")
    return "\n".join(lines)


def save_review_reports(
    report: PeerReviewReport, output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "peer_review.json"
    md_path = output_dir / "peer_review.md"

    json_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    md_path.write_text(
        render_review_markdown(report),
        encoding="utf-8",
    )
    return json_path, md_path
