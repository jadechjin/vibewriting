"""Internal models for literature processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class RawLiteratureRecord:
    """Unified literature record from any retrieval source."""

    title: str
    authors: list[str]
    year: int
    doi: str | None = None
    arxiv_id: str | None = None
    pmid: str | None = None
    abstract: str = ""
    source: Literal["paper-search", "dify-kb", "web-search"] = "paper-search"
    raw_data: dict = field(default_factory=dict)

    @property
    def primary_key(self) -> str:
        """Return the best available unique identifier."""
        if self.doi:
            return f"doi:{self.doi}"
        if self.arxiv_id:
            return f"arxiv:{self.arxiv_id}"
        if self.pmid:
            return f"pmid:{self.pmid}"
        normalized = self.title.lower().strip()
        return f"title:{normalized}:{self.year}"
