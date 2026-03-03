"""Review data models for Phase 6 compilation and quality assurance."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReviewSeverity(Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    SUGGESTION = "SUGGESTION"


class ReviewCategory(Enum):
    METHODOLOGY = "METHODOLOGY"
    EVIDENCE = "EVIDENCE"
    STRUCTURE = "STRUCTURE"
    LANGUAGE = "LANGUAGE"
    CITATION = "CITATION"


class ReviewFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: ReviewSeverity
    category: ReviewCategory
    location: str
    issue: str
    rationale: str
    suggestion: str = ""


class PeerReviewReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_score: float = Field(ge=0, le=10)
    verdict: Literal["Accept", "Minor Revision", "Major Revision", "Reject"]
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    detailed_findings: list[ReviewFinding]
    consistency_check: dict = Field(default_factory=dict)


class CitationAuditResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified_count: int
    suspicious_keys: list[str]
    orphan_claims: list[str]
    missing_evidence_cards: list[str]


class PatchReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_number: int
    error_kind: str
    target_file: str
    lines_changed: int
    success: bool
    stash_ref: str = ""


class Phase6Report(BaseModel):
    model_config = ConfigDict(extra="forbid")

    compilation: list[PatchReport]
    citation_audit: CitationAuditResult | None = None
    contract_integrity: list[dict] | None = None
    peer_review: PeerReviewReport | None = None
