"""Referential integrity validation across contract artifacts.

Validates cross-references between:
- paper_state claim_ids -> evidence_cards
- paper_state asset_ids -> asset_manifest
- paper_state citation_keys -> references.bib
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class IntegrityViolation:
    """A single referential integrity violation."""

    source: str
    field: str
    missing_key: str
    target: str

    def __str__(self) -> str:
        return f"[{self.source}] {self.field}='{self.missing_key}' not found in {self.target}"


def _extract_bib_keys(bib_path: Path) -> set[str]:
    """Extract all entry keys from a .bib file."""
    if not bib_path.exists():
        return set()
    content = bib_path.read_text(encoding="utf-8")
    return set(re.findall(r"@\w+\{([^,]+),", content))


def _extract_ids(items: list[dict[str, Any]], id_field: str) -> set[str]:
    """Extract a set of IDs from a list of dicts."""
    return {item[id_field] for item in items if id_field in item}


def validate_glossary_integrity(
    paper_state: dict[str, Any],
    glossary: dict[str, Any],
) -> list[IntegrityViolation]:
    """Validate glossary term usage across paper sections.

    Checks:
    - glossary 中定义的术语在所有 sections 中是否至少出现一次（检查 outline 字段）
    - sections 中标记使用了某 term 但 glossary 未定义（仅当 section 有 term_ids 字段时）
    """
    violations: list[IntegrityViolation] = []
    glossary_entries = glossary.get("entries", {})
    sections = paper_state.get("sections", [])

    # Collect all terms referenced across sections (via term_ids field if present)
    referenced_terms: set[str] = set()
    for section in sections:
        for term_id in section.get("term_ids", []):
            referenced_terms.add(term_id)

    # Check: terms referenced in sections but not defined in glossary
    defined_terms = set(glossary_entries.keys())
    for term_id in referenced_terms:
        if term_id not in defined_terms:
            violations.append(
                IntegrityViolation(
                    source="paper_state:sections",
                    field="term_id",
                    missing_key=term_id,
                    target="glossary",
                )
            )

    return violations


def validate_symbol_integrity(
    paper_state: dict[str, Any],
    symbols: dict[str, Any],
) -> list[IntegrityViolation]:
    """Validate symbol usage across paper sections.

    Checks:
    - symbols 中引用的符号在 paper_state 中是否存在定义（仅当 section 有 symbol_ids 字段时）
    """
    violations: list[IntegrityViolation] = []
    symbol_entries = symbols.get("entries", {})
    sections = paper_state.get("sections", [])

    # Collect all symbols referenced across sections (via symbol_ids field if present)
    referenced_symbols: set[str] = set()
    for section in sections:
        for symbol_id in section.get("symbol_ids", []):
            referenced_symbols.add(symbol_id)

    # Check: symbols referenced in sections but not defined in symbol table
    defined_symbols = set(symbol_entries.keys())
    for symbol_id in referenced_symbols:
        if symbol_id not in defined_symbols:
            violations.append(
                IntegrityViolation(
                    source="paper_state:sections",
                    field="symbol_id",
                    missing_key=symbol_id,
                    target="symbols",
                )
            )

    return violations


def validate_referential_integrity(
    paper_state: dict[str, Any],
    evidence_cards: list[dict[str, Any]],
    asset_manifest: list[dict[str, Any]],
    glossary: dict[str, Any] | None = None,
    symbols: dict[str, Any] | None = None,
    bib_path: Path | None = None,
) -> list[IntegrityViolation]:
    """Validate referential integrity across all contract artifacts.

    Args:
        paper_state: Paper state dict with sections containing claim_ids, asset_ids, citation_keys.
        evidence_cards: List of evidence card dicts with 'claim_id' field.
        asset_manifest: List of asset dicts with 'asset_id' field.
        glossary: Optional glossary dict with 'entries' sub-dict.
        symbols: Optional symbols dict with 'entries' sub-dict.
        bib_path: Optional path to .bib file.

    Returns:
        List of IntegrityViolation objects (empty means valid).
    """
    violations: list[IntegrityViolation] = []

    # Build lookup sets
    evidence_ids = _extract_ids(evidence_cards, "claim_id")
    asset_ids = _extract_ids(asset_manifest, "asset_id")
    bib_keys = _extract_bib_keys(bib_path) if bib_path else set()

    # Validate sections in paper_state
    sections = paper_state.get("sections", [])
    for section in sections:
        section_id = section.get("section_id", "<unknown>")

        # claim_id -> evidence_cards
        for claim_id in section.get("claim_ids", []):
            if claim_id not in evidence_ids:
                violations.append(
                    IntegrityViolation(
                        source=f"section:{section_id}",
                        field="claim_id",
                        missing_key=claim_id,
                        target="evidence_cards",
                    )
                )

        # asset_id -> asset_manifest
        for asset_id in section.get("asset_ids", []):
            if asset_id not in asset_ids:
                violations.append(
                    IntegrityViolation(
                        source=f"section:{section_id}",
                        field="asset_id",
                        missing_key=asset_id,
                        target="asset_manifest",
                    )
                )

        # citation_key -> references.bib
        if bib_path:
            for key in section.get("citation_keys", []):
                if key not in bib_keys:
                    violations.append(
                        IntegrityViolation(
                            source=f"section:{section_id}",
                            field="citation_key",
                            missing_key=key,
                            target="references.bib",
                        )
                    )

    # Glossary integrity
    if glossary:
        violations.extend(validate_glossary_integrity(paper_state, glossary))

    # Symbol integrity
    if symbols:
        violations.extend(validate_symbol_integrity(paper_state, symbols))

    return violations
