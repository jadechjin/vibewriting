"""Glossary and symbol table models for cross-section terminology consistency."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class GlossaryEntry(BaseModel):
    """A single term definition in the glossary."""

    model_config = ConfigDict(extra="forbid")

    term: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    first_used_in: str = ""
    aliases: list[str] = Field(default_factory=list)


class SymbolEntry(BaseModel):
    """A single symbol definition in the symbol table."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    meaning: str = Field(min_length=1)
    first_used_in: str = ""
    latex_command: str = ""


class Glossary(BaseModel):
    """Term glossary for cross-section consistency.

    All mutating operations return a new Glossary instance (immutable pattern).
    """

    model_config = ConfigDict(extra="forbid")

    entries: dict[str, GlossaryEntry] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=_utcnow)

    def add_term(self, term: str, definition: str, section_id: str = "") -> Self:
        """Return a new Glossary with the term added (immutable)."""
        entry = GlossaryEntry(term=term, definition=definition, first_used_in=section_id)
        new_entries = {**self.entries, term: entry}
        return self.model_copy(update={"entries": new_entries, "updated_at": _utcnow()})

    def has_term(self, term: str) -> bool:
        """Check if a term exists in the glossary."""
        return term in self.entries

    def lookup(self, term: str) -> GlossaryEntry | None:
        """Look up a term by exact match or alias."""
        if term in self.entries:
            return self.entries[term]
        for entry in self.entries.values():
            if term in entry.aliases:
                return entry
        return None


class SymbolTable(BaseModel):
    """Symbol table for cross-section mathematical notation consistency.

    All mutating operations return a new SymbolTable instance (immutable pattern).
    """

    model_config = ConfigDict(extra="forbid")

    entries: dict[str, SymbolEntry] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=_utcnow)

    def add_symbol(self, symbol: str, meaning: str, section_id: str = "") -> Self:
        """Return a new SymbolTable with the symbol added (immutable)."""
        entry = SymbolEntry(symbol=symbol, meaning=meaning, first_used_in=section_id)
        new_entries = {**self.entries, symbol: entry}
        return self.model_copy(update={"entries": new_entries, "updated_at": _utcnow()})

    def has_symbol(self, symbol: str) -> bool:
        """Check if a symbol exists in the table."""
        return symbol in self.entries

    def check_consistency(self, sections_text: dict[str, str]) -> list[str]:
        """Check if symbols are used consistently across sections.

        Args:
            sections_text: {section_id: tex_content} mapping.

        Returns:
            List of inconsistency descriptions (empty means consistent).
        """
        issues: list[str] = []
        for symbol, entry in self.entries.items():
            used_in: list[str] = []
            for section_id, content in sections_text.items():
                if symbol in content:
                    used_in.append(section_id)
            if len(used_in) > 1 and not entry.meaning:
                issues.append(
                    f"Symbol '{symbol}' used in {used_in} but has no defined meaning"
                )
        return issues
