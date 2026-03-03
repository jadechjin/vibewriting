"""Tests for the merge protocol module."""

from __future__ import annotations

import pytest

from vibewriting.agents.contracts import MergeConflict, MergeDecision, SectionPatchPayload
from vibewriting.agents.merge_protocol import (
    apply_merge,
    detect_conflicts,
    resolve_conflicts,
    validate_patch_payload,
)
from vibewriting.models.glossary import Glossary, SymbolTable


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_payload(
    section_id: str = "sec-intro",
    tex_content: str = r"\section{Intro} Some text.",
    claim_ids: list[str] | None = None,
    asset_ids: list[str] | None = None,
    citation_keys: list[str] | None = None,
    new_terms: dict[str, str] | None = None,
    new_symbols: dict[str, str] | None = None,
) -> SectionPatchPayload:
    return SectionPatchPayload(
        section_id=section_id,
        tex_content=tex_content,
        claim_ids=claim_ids or [],
        asset_ids=asset_ids or [],
        citation_keys=citation_keys or [],
        new_terms=new_terms or {},
        new_symbols=new_symbols or {},
    )


# ---------------------------------------------------------------------------
# TestValidatePatchPayload
# ---------------------------------------------------------------------------


class TestValidatePatchPayload:
    def test_valid_payload_no_errors(self) -> None:
        payload = make_payload(
            claim_ids=["EC-2024-001"],
            asset_ids=["ASSET-2024-001"],
        )
        errors = validate_patch_payload(
            payload,
            allowed_claim_ids={"EC-2024-001"},
            allowed_asset_ids={"ASSET-2024-001"},
        )
        assert errors == []

    def test_invalid_claim_ids(self) -> None:
        payload = make_payload(claim_ids=["EC-2024-999"])
        errors = validate_patch_payload(
            payload, allowed_claim_ids={"EC-2024-001"}
        )
        assert len(errors) == 1
        assert "EC-2024-999" in errors[0]
        assert "Invalid claim_ids" in errors[0]

    def test_invalid_asset_ids(self) -> None:
        payload = make_payload(asset_ids=["ASSET-9999"])
        errors = validate_patch_payload(
            payload, allowed_asset_ids={"ASSET-2024-001"}
        )
        assert len(errors) == 1
        assert "ASSET-9999" in errors[0]
        assert "Invalid asset_ids" in errors[0]

    def test_none_allowed_sets_skip_check(self) -> None:
        payload = make_payload(
            claim_ids=["any-claim"],
            asset_ids=["any-asset"],
        )
        errors = validate_patch_payload(
            payload,
            allowed_claim_ids=None,
            allowed_asset_ids=None,
        )
        assert errors == []

    def test_whitespace_only_tex_content(self) -> None:
        # Pydantic enforces min_length=1, so we need at least 1 char.
        # Whitespace-only content passes Pydantic but should be caught by
        # our extra check.
        payload = SectionPatchPayload(
            section_id="sec-intro",
            tex_content="   ",
        )
        errors = validate_patch_payload(payload)
        assert len(errors) == 1
        assert "whitespace-only" in errors[0]


# ---------------------------------------------------------------------------
# TestDetectConflicts
# ---------------------------------------------------------------------------


class TestDetectConflicts:
    def test_no_conflicts_with_single_payload(self) -> None:
        payload = make_payload(
            new_terms={"alpha": "first letter"},
            new_symbols={"alpha": "learning rate"},
            citation_keys=["smith2024"],
        )
        conflicts = detect_conflicts(
            [payload], bib_keys={"smith2024"}
        )
        assert conflicts == []

    def test_terminology_conflict_detected(self) -> None:
        p1 = make_payload("sec-intro", new_terms={"model": "a statistical model"})
        p2 = make_payload("sec-related", new_terms={"model": "a neural network"})
        conflicts = detect_conflicts([p1, p2])
        terminology_conflicts = [c for c in conflicts if c.conflict_type == "terminology"]
        assert len(terminology_conflicts) == 1
        c = terminology_conflicts[0]
        assert "model" in c.description
        assert "sec-intro" in c.affected_sections
        assert "sec-related" in c.affected_sections

    def test_symbol_conflict_detected(self) -> None:
        p1 = make_payload("sec-intro", new_symbols={"alpha": "learning rate"})
        p2 = make_payload("sec-method", new_symbols={"alpha": "significance level"})
        conflicts = detect_conflicts([p1, p2])
        symbol_conflicts = [c for c in conflicts if c.conflict_type == "symbol"]
        assert len(symbol_conflicts) == 1
        c = symbol_conflicts[0]
        assert "alpha" in c.description
        assert "sec-intro" in c.affected_sections
        assert "sec-method" in c.affected_sections

    def test_citation_conflict_missing_bib_key(self) -> None:
        payload = make_payload(citation_keys=["missing_key"])
        conflicts = detect_conflicts([payload], bib_keys={"smith2024"})
        citation_conflicts = [c for c in conflicts if c.conflict_type == "citation"]
        assert len(citation_conflicts) == 1
        assert "missing_key" in citation_conflicts[0].description

    def test_no_citation_conflict_when_bib_keys_none(self) -> None:
        payload = make_payload(citation_keys=["any_key"])
        conflicts = detect_conflicts([payload], bib_keys=None)
        citation_conflicts = [c for c in conflicts if c.conflict_type == "citation"]
        assert citation_conflicts == []

    def test_glossary_conflict_detected(self) -> None:
        glossary = Glossary().add_term("model", "a statistical model", "existing")
        payload = make_payload("sec-intro", new_terms={"model": "a neural network"})
        conflicts = detect_conflicts([payload], glossary=glossary)
        terminology_conflicts = [c for c in conflicts if c.conflict_type == "terminology"]
        assert len(terminology_conflicts) == 1
        c = terminology_conflicts[0]
        assert "glossary" in c.conflicting_values
        assert c.conflicting_values["glossary"] == "a statistical model"
        assert c.conflicting_values["sec-intro"] == "a neural network"

    def test_symbol_table_conflict_detected(self) -> None:
        symbols = SymbolTable().add_symbol("beta", "discount factor", "existing")
        payload = make_payload("sec-method", new_symbols={"beta": "regularization"})
        conflicts = detect_conflicts([payload], symbols=symbols)
        symbol_conflicts = [c for c in conflicts if c.conflict_type == "symbol"]
        assert len(symbol_conflicts) == 1
        c = symbol_conflicts[0]
        assert "symbol_table" in c.conflicting_values
        assert c.conflicting_values["symbol_table"] == "discount factor"

    def test_no_conflict_when_definitions_match(self) -> None:
        glossary = Glossary().add_term("model", "a statistical model", "existing")
        p1 = make_payload("sec-intro", new_terms={"model": "a statistical model"})
        p2 = make_payload("sec-method", new_terms={"model": "a statistical model"})
        conflicts = detect_conflicts([p1, p2], glossary=glossary)
        assert conflicts == []


# ---------------------------------------------------------------------------
# TestResolveConflicts
# ---------------------------------------------------------------------------


class TestResolveConflicts:
    def _make_terminology_conflict(
        self, section_id: str = "sec-intro", has_glossary_key: bool = True
    ) -> MergeConflict:
        vals: dict[str, str] = {section_id: "a neural network"}
        if has_glossary_key:
            vals["glossary"] = "a statistical model"
        return MergeConflict(
            conflict_type="terminology",
            affected_sections=[section_id],
            description="Term 'model' conflicts",
            conflicting_values=vals,
        )

    def _make_symbol_conflict(
        self, section_id: str = "sec-method", has_table_key: bool = True
    ) -> MergeConflict:
        vals: dict[str, str] = {section_id: "regularization"}
        if has_table_key:
            vals["symbol_table"] = "discount factor"
        return MergeConflict(
            conflict_type="symbol",
            affected_sections=[section_id],
            description="Symbol 'beta' conflicts",
            conflicting_values=vals,
        )

    def test_terminology_resolved_by_glossary(self) -> None:
        glossary = Glossary().add_term("model", "a statistical model")
        conflict = self._make_terminology_conflict()
        decisions = resolve_conflicts([conflict], glossary=glossary)
        assert len(decisions) == 1
        d = decisions[0]
        assert not d.requires_human_review
        assert d.resolved_value == "a statistical model"
        assert "Glossary" in d.resolution

    def test_terminology_no_glossary_needs_review(self) -> None:
        conflict = self._make_terminology_conflict(has_glossary_key=False)
        decisions = resolve_conflicts([conflict], glossary=None)
        assert len(decisions) == 1
        assert decisions[0].requires_human_review

    def test_symbol_resolved_by_symbol_table(self) -> None:
        symbols = SymbolTable().add_symbol("beta", "discount factor")
        conflict = self._make_symbol_conflict()
        decisions = resolve_conflicts([conflict], symbols=symbols)
        assert len(decisions) == 1
        d = decisions[0]
        assert not d.requires_human_review
        assert d.resolved_value == "discount factor"
        assert "Symbol table" in d.resolution

    def test_citation_resolved_remove_invalid(self) -> None:
        conflict = MergeConflict(
            conflict_type="citation",
            affected_sections=["sec-intro"],
            description="Citation key missing",
            conflicting_values={"bad_key": "missing"},
        )
        decisions = resolve_conflicts([conflict])
        assert len(decisions) == 1
        d = decisions[0]
        assert not d.requires_human_review
        assert "bad_key" in d.resolution

    def test_narrative_always_needs_review(self) -> None:
        conflict = MergeConflict(
            conflict_type="narrative",
            affected_sections=["sec-intro", "sec-conc"],
            description="Narrative tone inconsistency",
            conflicting_values={"sec-intro": "tone A", "sec-conc": "tone B"},
        )
        decisions = resolve_conflicts([conflict])
        assert len(decisions) == 1
        assert decisions[0].requires_human_review


# ---------------------------------------------------------------------------
# TestApplyMerge
# ---------------------------------------------------------------------------


class TestApplyMerge:
    def test_apply_with_no_decisions(self) -> None:
        payload = make_payload(tex_content=r"\section{Intro} Hello world.")
        result = apply_merge(payload, decisions=[])
        assert result == r"\section{Intro} Hello world."

    def test_apply_removes_invalid_citation(self) -> None:
        tex = r"\section{Intro} See \citep{bad_key} for details."
        payload = make_payload(section_id="sec-intro", tex_content=tex)
        conflict = MergeConflict(
            conflict_type="citation",
            affected_sections=["sec-intro"],
            description="bad_key missing",
            conflicting_values={"bad_key": "missing"},
        )
        decision = MergeDecision(
            conflict=conflict,
            resolution="Remove invalid citation keys: bad_key",
            resolved_value="",
            requires_human_review=False,
        )
        result = apply_merge(payload, decisions=[decision])
        assert r"\citep{bad_key}" not in result
        assert "See" in result
        assert "for details" in result

    def test_apply_skips_human_review_decisions(self) -> None:
        tex = r"\section{Intro} Content with \citep{bad_key}."
        payload = make_payload(section_id="sec-intro", tex_content=tex)
        conflict = MergeConflict(
            conflict_type="narrative",
            affected_sections=["sec-intro"],
            description="Narrative conflict",
            conflicting_values={"sec-intro": "value"},
        )
        decision = MergeDecision(
            conflict=conflict,
            resolution="Requires human review",
            requires_human_review=True,
        )
        result = apply_merge(payload, decisions=[decision])
        # Human review decisions should not modify content
        assert result == tex

    def test_apply_only_affects_relevant_section(self) -> None:
        tex = r"\section{Intro} See \citep{bad_key} for more."
        payload = make_payload(section_id="sec-intro", tex_content=tex)
        # conflict affects a different section
        conflict = MergeConflict(
            conflict_type="citation",
            affected_sections=["sec-method"],  # NOT sec-intro
            description="bad_key missing in sec-method",
            conflicting_values={"bad_key": "missing"},
        )
        decision = MergeDecision(
            conflict=conflict,
            resolution="Remove invalid citation keys: bad_key",
            resolved_value="",
            requires_human_review=False,
        )
        result = apply_merge(payload, decisions=[decision])
        # sec-intro should be unchanged because the conflict targets sec-method
        assert result == tex
