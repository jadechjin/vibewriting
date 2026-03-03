"""Paper state model for tracking writing progress."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SectionState(BaseModel):
    """Writing-stage section state (extends Section semantics)."""

    model_config = ConfigDict(extra="forbid")

    section_id: str
    title: str
    outline: list[str] = Field(default_factory=list)
    status: Literal["planned", "drafting", "drafted", "reviewed", "complete"] = "planned"
    claim_ids: list[str] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)
    citation_keys: list[str] = Field(default_factory=list)
    tex_file: str
    word_count: int = 0
    paragraph_count: int = 0
    no_cite_exemptions: list[str] = Field(default_factory=list)


class PaperMetrics(BaseModel):
    """Quality metrics for the paper writing process."""

    model_config = ConfigDict(extra="forbid")

    citation_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    claim_traceability: float = Field(default=0.0, ge=0.0, le=1.0)
    figure_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    cross_ref_integrity: bool = False
    terminology_consistency: bool = False
    total_claims: int = Field(default=0, ge=0)
    total_citations: int = Field(default=0, ge=0)
    total_figures_referenced: int = Field(default=0, ge=0)
    total_tables_referenced: int = Field(default=0, ge=0)


class PaperState(BaseModel):
    """Global paper state machine tracking writing progress.

    Designed to be compatible with contracts/integrity.py's
    validate_referential_integrity() function.
    """

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    title: str
    topic: str
    phase: Literal["outline", "drafting", "review", "complete"] = "outline"
    abstract: str = ""
    sections: list[SectionState] = Field(default_factory=list)
    metrics: PaperMetrics = Field(default_factory=PaperMetrics)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    current_section_index: int = Field(default=0, ge=0)
    run_id: str = ""
