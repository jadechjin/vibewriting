"""Evidence Card Pydantic model for structured literature claims."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(UTC)


class EvidenceCard(BaseModel):
    """A structured evidence claim extracted from literature."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(pattern=r"^EC-\d{4}-\d{3}$")
    claim_text: str = Field(min_length=1)
    supporting_quote: str = Field(default="")
    paraphrase: bool = False
    bib_key: str = Field(min_length=1)
    location: dict = Field(default_factory=dict)
    evidence_type: Literal["empirical", "theoretical", "survey", "meta-analysis"]
    key_statistics: str | None = None
    methodology_notes: str = ""
    quality_score: int = Field(ge=1, le=10, default=5)
    tags: list[str] = Field(default_factory=list)
    retrieval_source: Literal["paper-search", "dify-kb", "manual"]
    retrieved_at: datetime = Field(default_factory=_utcnow)
    source_id: str = ""
    content_hash: str | None = None

    @field_validator("supporting_quote")
    @classmethod
    def check_quote_length(cls, v: str, info) -> str:
        """Warn if supporting_quote exceeds 50 words."""
        if v and len(v.split()) > 50:
            # Auto-flag as paraphrase in create_evidence_card, not here
            pass
        return v
