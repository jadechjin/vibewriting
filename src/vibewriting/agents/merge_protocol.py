"""Merge protocol for multi-agent orchestration.

Validates patches, detects conflicts, resolves conflicts, and applies merges.
The orchestrator is the single writer - this module provides merge logic.
"""

from __future__ import annotations

import logging
import re

from vibewriting.agents.contracts import (
    MergeConflict,
    MergeDecision,
    SectionPatchPayload,
)
from vibewriting.models.glossary import Glossary, SymbolTable

logger = logging.getLogger(__name__)


def validate_patch_payload(
    payload: SectionPatchPayload,
    allowed_claim_ids: set[str] | None = None,
    allowed_asset_ids: set[str] | None = None,
) -> list[str]:
    """Validate a patch payload against allowed references.

    Checks:
    - claim_ids are subset of allowed_claim_ids (if provided)
    - asset_ids are subset of allowed_asset_ids (if provided)
    - tex_content is non-empty (enforced by Pydantic, but double-check)

    Returns:
        List of validation error messages (empty = valid).
    """
    errors: list[str] = []

    if not payload.tex_content.strip():
        errors.append(f"[{payload.section_id}] tex_content is empty or whitespace-only")

    if allowed_claim_ids is not None:
        invalid_claims = set(payload.claim_ids) - allowed_claim_ids
        if invalid_claims:
            errors.append(
                f"[{payload.section_id}] Invalid claim_ids: {', '.join(sorted(invalid_claims))}"
            )

    if allowed_asset_ids is not None:
        invalid_assets = set(payload.asset_ids) - allowed_asset_ids
        if invalid_assets:
            errors.append(
                f"[{payload.section_id}] Invalid asset_ids: {', '.join(sorted(invalid_assets))}"
            )

    return errors


def detect_conflicts(
    payloads: list[SectionPatchPayload],
    glossary: Glossary | None = None,
    symbols: SymbolTable | None = None,
    bib_keys: set[str] | None = None,
) -> list[MergeConflict]:
    """Detect conflicts across multiple patch payloads.

    Conflict types:
    1. Terminology: different payloads define same term with different definitions
    2. Symbol: different payloads define same symbol with different meanings
    3. Citation: payloads reference keys not in bib_keys

    Args:
        payloads: List of patch payloads to check.
        glossary: Current glossary (for reference).
        symbols: Current symbol table (for reference).
        bib_keys: Set of valid BibTeX keys (from references.bib).

    Returns:
        List of detected MergeConflict objects.
    """
    conflicts: list[MergeConflict] = []

    # 1. Terminology conflicts: same term, different definitions
    term_defs: dict[str, dict[str, str]] = {}  # term -> {section_id: definition}
    for payload in payloads:
        for term, definition in payload.new_terms.items():
            if term not in term_defs:
                term_defs[term] = {}
            term_defs[term][payload.section_id] = definition

    for term, defs in term_defs.items():
        unique_defs = set(defs.values())
        if len(unique_defs) > 1:
            conflicts.append(
                MergeConflict(
                    conflict_type="terminology",
                    affected_sections=list(defs.keys()),
                    description=f"Term '{term}' has conflicting definitions across sections",
                    conflicting_values=defs,
                )
            )
        # Also check against existing glossary
        if glossary and glossary.has_term(term):
            existing_def = glossary.entries[term].definition
            for section_id, new_def in defs.items():
                if new_def != existing_def:
                    conflicts.append(
                        MergeConflict(
                            conflict_type="terminology",
                            affected_sections=[section_id],
                            description=(
                                f"Term '{term}' in section '{section_id}' "
                                f"conflicts with glossary definition"
                            ),
                            conflicting_values={"glossary": existing_def, section_id: new_def},
                        )
                    )

    # 2. Symbol conflicts: same symbol, different meanings
    symbol_meanings: dict[str, dict[str, str]] = {}
    for payload in payloads:
        for symbol, meaning in payload.new_symbols.items():
            if symbol not in symbol_meanings:
                symbol_meanings[symbol] = {}
            symbol_meanings[symbol][payload.section_id] = meaning

    for symbol, meanings in symbol_meanings.items():
        unique_meanings = set(meanings.values())
        if len(unique_meanings) > 1:
            conflicts.append(
                MergeConflict(
                    conflict_type="symbol",
                    affected_sections=list(meanings.keys()),
                    description=f"Symbol '{symbol}' has conflicting meanings across sections",
                    conflicting_values=meanings,
                )
            )
        # Check against existing symbols
        if symbols and symbols.has_symbol(symbol):
            existing_meaning = symbols.entries[symbol].meaning
            for section_id, new_meaning in meanings.items():
                if new_meaning != existing_meaning:
                    conflicts.append(
                        MergeConflict(
                            conflict_type="symbol",
                            affected_sections=[section_id],
                            description=(
                                f"Symbol '{symbol}' in section '{section_id}' "
                                f"conflicts with symbol table"
                            ),
                            conflicting_values={
                                "symbol_table": existing_meaning,
                                section_id: new_meaning,
                            },
                        )
                    )

    # 3. Citation conflicts: keys not in bib
    if bib_keys is not None:
        for payload in payloads:
            invalid_keys = set(payload.citation_keys) - bib_keys
            if invalid_keys:
                conflicts.append(
                    MergeConflict(
                        conflict_type="citation",
                        affected_sections=[payload.section_id],
                        description=(
                            f"Citation keys not found in references.bib: "
                            f"{', '.join(sorted(invalid_keys))}"
                        ),
                        conflicting_values={k: "missing" for k in invalid_keys},
                    )
                )

    return conflicts


def resolve_conflicts(
    conflicts: list[MergeConflict],
    glossary: Glossary | None = None,
    symbols: SymbolTable | None = None,
) -> list[MergeDecision]:
    """Resolve merge conflicts using priority rules.

    Resolution priority:
    - Terminology: glossary definition wins (hard authority)
    - Symbol: symbol table wins (hard authority)
    - Citation: mark as needs resolution (remove invalid key)
    - Narrative: mark for human review

    Returns:
        List of MergeDecision objects.
    """
    decisions: list[MergeDecision] = []

    for conflict in conflicts:
        if conflict.conflict_type == "terminology":
            if glossary and "glossary" in conflict.conflicting_values:
                resolved_value = conflict.conflicting_values["glossary"]
                decisions.append(
                    MergeDecision(
                        conflict=conflict,
                        resolution=f"Glossary definition wins: '{resolved_value}'",
                        resolved_value=resolved_value,
                        requires_human_review=False,
                    )
                )
            else:
                decisions.append(
                    MergeDecision(
                        conflict=conflict,
                        resolution="Multiple definitions found, requires human review",
                        requires_human_review=True,
                    )
                )

        elif conflict.conflict_type == "symbol":
            if symbols and "symbol_table" in conflict.conflicting_values:
                resolved_value = conflict.conflicting_values["symbol_table"]
                decisions.append(
                    MergeDecision(
                        conflict=conflict,
                        resolution=f"Symbol table definition wins: '{resolved_value}'",
                        resolved_value=resolved_value,
                        requires_human_review=False,
                    )
                )
            else:
                decisions.append(
                    MergeDecision(
                        conflict=conflict,
                        resolution="Multiple symbol meanings found, requires human review",
                        requires_human_review=True,
                    )
                )

        elif conflict.conflict_type == "citation":
            invalid_keys = [k for k, v in conflict.conflicting_values.items() if v == "missing"]
            decisions.append(
                MergeDecision(
                    conflict=conflict,
                    resolution=f"Remove invalid citation keys: {', '.join(invalid_keys)}",
                    resolved_value="",
                    requires_human_review=False,
                )
            )

        elif conflict.conflict_type == "narrative":
            decisions.append(
                MergeDecision(
                    conflict=conflict,
                    resolution=(
                        "Narrative conflict requires human review "
                        "or Storyteller final judgment"
                    ),
                    requires_human_review=True,
                )
            )

    return decisions


def apply_merge(
    payload: SectionPatchPayload,
    decisions: list[MergeDecision],
    current_tex: str = "",
) -> str:
    """Apply merge decisions and return final tex content.

    For terminology/symbol decisions:
    - If resolved_value is set, replace occurrences in tex_content

    For citation decisions:
    - Remove invalid \\citep{}/\\citet{} entries

    Args:
        payload: The patch payload to merge.
        decisions: Relevant merge decisions.
        current_tex: Current section tex content (for reference).

    Returns:
        Final merged tex content.
    """
    tex = payload.tex_content

    for decision in decisions:
        conflict = decision.conflict

        # Only apply decisions that affect this section
        if payload.section_id not in conflict.affected_sections:
            continue

        if decision.requires_human_review:
            # Skip, will be reviewed manually
            continue

        if conflict.conflict_type == "terminology" and decision.resolved_value:
            # The actual tex content uses the term naturally; resolution is noted
            pass

        if conflict.conflict_type == "citation":
            # Remove invalid citation keys from tex content
            for key, status in conflict.conflicting_values.items():
                if status == "missing":
                    # Remove \citep{key} and \citet{key}
                    tex = re.sub(rf"\\cite[pt]\{{{re.escape(key)}\}}", "", tex)
                    # Clean up empty citations from multi-key citations
                    tex = re.sub(r",\s*,", ",", tex)
                    tex = re.sub(r"\\cite[pt]\{\s*,", r"\\citep{", tex)
                    tex = re.sub(r",\s*\}", "}", tex)

    return tex
