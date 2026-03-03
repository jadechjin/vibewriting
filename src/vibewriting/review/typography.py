"""Typography quality checks: overfull hbox, float placement, chktex."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from vibewriting.review.models import (
    ReviewCategory,
    ReviewFinding,
    ReviewSeverity,
)

logger = logging.getLogger(__name__)

_OVERFULL_RE = re.compile(r"(Overfull \\hbox .+?) in paragraph at lines (\d+)--(\d+)")
_UNDERFULL_RE = re.compile(r"(Underfull \\hbox .+?) in paragraph at lines (\d+)--(\d+)")
_WIDOW_RE = re.compile(r"(Widow penalty|Club penalty)")
_FORCE_FLOAT_RE = re.compile(r"\\begin\{(?:figure|table)\}\s*\[([HhH!]+)\]")


def check_overfull_hbox(log_content: str) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for match in _OVERFULL_RE.finditer(log_content):
        findings.append(ReviewFinding(
            severity=ReviewSeverity.MINOR,
            category=ReviewCategory.LANGUAGE,
            location=f"lines {match.group(2)}-{match.group(3)}",
            issue=match.group(1),
            rationale="Overfull hbox causes text to extend beyond margins",
            suggestion="Rephrase or add hyphenation hints",
        ))
    return findings


def check_float_placement(paper_dir: Path) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for tex_file in paper_dir.rglob("*.tex"):
        content = tex_file.read_text(encoding="utf-8")
        rel = str(tex_file.relative_to(paper_dir))
        for line_num, line in enumerate(content.splitlines(), 1):
            for match in _FORCE_FLOAT_RE.finditer(line):
                findings.append(ReviewFinding(
                    severity=ReviewSeverity.SUGGESTION,
                    category=ReviewCategory.LANGUAGE,
                    location=f"{rel}:{line_num}",
                    issue=f"Forced float placement [{match.group(1)}]",
                    rationale="Forced placement can cause large whitespace gaps",
                    suggestion="Use [tbp] and let LaTeX optimize placement",
                ))
    return findings


def check_widow_orphan(log_content: str) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for match in _WIDOW_RE.finditer(log_content):
        findings.append(ReviewFinding(
            severity=ReviewSeverity.SUGGESTION,
            category=ReviewCategory.LANGUAGE,
            location="compilation log",
            issue=f"{match.group(1)} detected",
            rationale="Widow/orphan lines reduce readability",
            suggestion="Adjust paragraph breaks or use \\widowpenalties",
        ))
    return findings


def run_chktex(paper_dir: Path) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    main_tex = paper_dir / "main.tex"
    if not main_tex.exists():
        return findings

    try:
        result = subprocess.run(
            ["chktex", "-q", str(main_tex)],
            capture_output=True, text=True, check=False, timeout=30,
        )
    except FileNotFoundError:
        logger.warning("chktex not found, skipping")
        return findings
    except subprocess.TimeoutExpired:
        return findings

    for line in result.stdout.splitlines():
        if "Warning" in line:
            findings.append(ReviewFinding(
                severity=ReviewSeverity.SUGGESTION,
                category=ReviewCategory.LANGUAGE,
                location="chktex",
                issue=line.strip(),
                rationale="chktex style warning",
            ))
    return findings


def run_typography_check(
    paper_dir: Path,
    log_content: str = "",
    enable_ai_vision: bool = False,
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    if log_content:
        findings.extend(check_overfull_hbox(log_content))
        findings.extend(check_widow_orphan(log_content))
    findings.extend(check_float_placement(paper_dir))
    findings.extend(run_chktex(paper_dir))
    return findings
