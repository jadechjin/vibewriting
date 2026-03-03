"""Tests for contract validation, healing, schema export, and referential integrity."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from vibewriting.contracts.healers import regex_healer
from vibewriting.contracts.healers.llm_healer import HealResult, ValidationErrorInfo, heal
from vibewriting.contracts.integrity import (
    IntegrityViolation,
    validate_glossary_integrity,
    validate_referential_integrity,
    validate_symbol_integrity,
)
from vibewriting.contracts.schema_export import MODELS, export_schemas
from vibewriting.contracts.validator import (
    ContractValidationError,
    ValidatedPayload,
    validate_contract,
)


# ---------------------------------------------------------------------------
# Regex Healer
# ---------------------------------------------------------------------------

class TestRegexHealer:
    def test_strip_markdown_fences(self):
        raw = '```json\n{"a": 1}\n```'
        assert regex_healer.strip_markdown_fences(raw) == '{"a": 1}'

    def test_strip_markdown_fences_no_lang(self):
        raw = '```\n{"a": 1}\n```'
        assert regex_healer.strip_markdown_fences(raw) == '{"a": 1}'

    def test_fix_trailing_commas(self):
        assert regex_healer.fix_trailing_commas('{"a": 1,}') == '{"a": 1}'
        assert regex_healer.fix_trailing_commas('[1, 2,]') == '[1, 2]'

    def test_fix_single_quotes(self):
        result = regex_healer.fix_single_quotes("{'key': 'value'}")
        assert result == '{"key": "value"}'

    def test_fix_unclosed_strings(self):
        # Line with odd number of quotes gets one added
        result = regex_healer.fix_unclosed_strings('"hello')
        assert result.count('"') % 2 == 0

    def test_heal_combined(self):
        raw = "```json\n{'a': 1, 'b': 2,}\n```"
        result = regex_healer.heal(raw)
        parsed = json.loads(result)
        assert parsed == {"a": 1, "b": 2}


# ---------------------------------------------------------------------------
# LLM Healer
# ---------------------------------------------------------------------------

class TestLLMHealer:
    def test_heal_success(self):
        def mock_llm(prompt: str) -> str:
            return '{"fixed": true}'

        errors = [ValidationErrorInfo(path="root", message="bad value")]
        result = heal('{"broken": true}', errors, mock_llm)
        assert result.success
        assert json.loads(result.healed_payload) == {"fixed": True}

    def test_heal_strips_markdown(self):
        def mock_llm(prompt: str) -> str:
            return '```json\n{"fixed": true}\n```'

        errors = [ValidationErrorInfo(path="root", message="bad")]
        result = heal("{}", errors, mock_llm)
        assert json.loads(result.healed_payload) == {"fixed": True}

    def test_heal_failure(self):
        def mock_llm(prompt: str) -> str:
            raise RuntimeError("API error")

        errors = [ValidationErrorInfo(path="root", message="bad")]
        result = heal('{"original": 1}', errors, mock_llm)
        assert not result.success
        assert result.healed_payload == '{"original": 1}'


# ---------------------------------------------------------------------------
# Schema Export
# ---------------------------------------------------------------------------

class TestSchemaExport:
    def test_export_creates_files(self, tmp_path):
        paths = export_schemas(tmp_path)
        assert len(paths) == len(MODELS)
        for p in paths:
            assert p.exists()
            schema = json.loads(p.read_text())
            assert "properties" in schema or "$defs" in schema

    def test_export_consistency(self, tmp_path):
        """Exporting twice produces identical schemas."""
        paths1 = export_schemas(tmp_path / "run1")
        paths2 = export_schemas(tmp_path / "run2")
        for p1, p2 in zip(paths1, paths2):
            assert p1.read_text() == p2.read_text()


# ---------------------------------------------------------------------------
# Contract Validator
# ---------------------------------------------------------------------------

class TestValidator:
    def test_valid_payload_passes(self, tmp_path):
        # Export schemas to temp dir
        export_schemas(tmp_path)
        # Create a valid Paper payload
        payload = {
            "id": "test",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "tags": [],
            "title": "Test",
            "authors": ["A"],
            "abstract": "Abs",
            "bib_key": "key2026",
            "quality_score": 5.0,
            "sections": [],
        }
        # Monkey-patch schemas dir
        import vibewriting.contracts.validator as v
        orig = v.SCHEMAS_DIR
        v.SCHEMAS_DIR = tmp_path
        try:
            result = validate_contract(payload, "paper")
            assert isinstance(result, ValidatedPayload)
            assert result.heal_rounds == 0
        finally:
            v.SCHEMAS_DIR = orig

    def test_idempotency_valid_input(self, tmp_path):
        """Valid input returns immediately (heal_rounds=0)."""
        export_schemas(tmp_path)
        payload = {
            "id": "t",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "tags": [],
            "experiment_id": "exp-1",
            "config": {},
            "results": {},
            "data_fingerprint": "",
            "asset_ids": [],
        }
        import vibewriting.contracts.validator as v
        orig = v.SCHEMAS_DIR
        v.SCHEMAS_DIR = tmp_path
        try:
            result = validate_contract(payload, "experiment")
            assert result.heal_rounds == 0
            assert result.violation_counts == [0]
        finally:
            v.SCHEMAS_DIR = orig

    def test_invalid_payload_raises(self, tmp_path):
        """Payload missing required fields raises after retries."""
        export_schemas(tmp_path)
        import vibewriting.contracts.validator as v
        orig = v.SCHEMAS_DIR
        v.SCHEMAS_DIR = tmp_path
        try:
            with pytest.raises(ContractValidationError):
                validate_contract({"id": "x"}, "paper", max_retries=1)
        finally:
            v.SCHEMAS_DIR = orig

    def test_bounds_max_3_retries(self, tmp_path):
        """Max retries is capped at 3."""
        export_schemas(tmp_path)
        import vibewriting.contracts.validator as v
        orig = v.SCHEMAS_DIR
        v.SCHEMAS_DIR = tmp_path
        try:
            with pytest.raises(ContractValidationError):
                validate_contract({"bad": True}, "paper", max_retries=10)
        finally:
            v.SCHEMAS_DIR = orig

    def test_string_payload_with_markdown(self, tmp_path):
        """String payloads with markdown fences get healed."""
        export_schemas(tmp_path)
        payload_str = '```json\n' + json.dumps({
            "id": "t",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "tags": [],
            "experiment_id": "exp-1",
            "config": {},
            "results": {},
            "data_fingerprint": "",
            "asset_ids": [],
        }) + '\n```'
        import vibewriting.contracts.validator as v
        orig = v.SCHEMAS_DIR
        v.SCHEMAS_DIR = tmp_path
        try:
            result = validate_contract(payload_str, "experiment")
            assert isinstance(result, ValidatedPayload)
        finally:
            v.SCHEMAS_DIR = orig


# ---------------------------------------------------------------------------
# Referential Integrity
# ---------------------------------------------------------------------------

class TestIntegrity:
    def test_valid_references(self):
        paper_state = {
            "sections": [
                {
                    "section_id": "intro",
                    "claim_ids": ["EC-001"],
                    "asset_ids": ["ASSET-2026-001"],
                    "citation_keys": [],
                }
            ]
        }
        evidence = [{"claim_id": "EC-001"}]
        assets = [{"asset_id": "ASSET-2026-001"}]
        violations = validate_referential_integrity(paper_state, evidence, assets)
        assert violations == []

    def test_missing_claim(self):
        paper_state = {
            "sections": [
                {
                    "section_id": "intro",
                    "claim_ids": ["EC-MISSING"],
                    "asset_ids": [],
                    "citation_keys": [],
                }
            ]
        }
        violations = validate_referential_integrity(paper_state, [], [])
        assert len(violations) == 1
        assert violations[0].missing_key == "EC-MISSING"
        assert violations[0].target == "evidence_cards"

    def test_missing_asset(self):
        paper_state = {
            "sections": [
                {
                    "section_id": "method",
                    "claim_ids": [],
                    "asset_ids": ["ASSET-GONE"],
                    "citation_keys": [],
                }
            ]
        }
        violations = validate_referential_integrity(paper_state, [], [])
        assert len(violations) == 1
        assert violations[0].target == "asset_manifest"

    def test_missing_bib_key(self, tmp_path):
        bib_file = tmp_path / "references.bib"
        bib_file.write_text('@article{smith2026,\n  title={Test}\n}\n')
        paper_state = {
            "sections": [
                {
                    "section_id": "related",
                    "claim_ids": [],
                    "asset_ids": [],
                    "citation_keys": ["smith2026", "missing2026"],
                }
            ]
        }
        violations = validate_referential_integrity(
            paper_state, [], [], bib_path=bib_file
        )
        assert len(violations) == 1
        assert violations[0].missing_key == "missing2026"

    def test_invariant_broken_link_detected(self):
        """Any broken reference must be detected regardless of combination."""
        paper_state = {
            "sections": [
                {
                    "section_id": "s1",
                    "claim_ids": ["EC-1", "EC-2"],
                    "asset_ids": ["A-1"],
                    "citation_keys": [],
                }
            ]
        }
        evidence = [{"claim_id": "EC-1"}]  # EC-2 missing
        assets = []  # A-1 missing
        violations = validate_referential_integrity(paper_state, evidence, assets)
        missing_keys = {v.missing_key for v in violations}
        assert "EC-2" in missing_keys
        assert "A-1" in missing_keys

    def test_commutativity_load_order(self):
        """Results are the same regardless of argument order construction."""
        paper_state = {
            "sections": [
                {
                    "section_id": "s1",
                    "claim_ids": ["EC-1"],
                    "asset_ids": ["A-1"],
                    "citation_keys": [],
                }
            ]
        }
        ev1 = [{"claim_id": "EC-1"}]
        as1 = [{"asset_id": "A-1"}]

        v1 = validate_referential_integrity(paper_state, ev1, as1)
        v2 = validate_referential_integrity(paper_state, ev1, as1)
        assert v1 == v2
        assert len(v1) == 0


# ---------------------------------------------------------------------------
# Glossary Integrity
# ---------------------------------------------------------------------------

class TestGlossaryIntegrity:
    def test_valid_glossary_no_violations(self):
        paper_state = {
            "sections": [
                {"section_id": "intro", "claim_ids": [], "asset_ids": [], "citation_keys": []}
            ]
        }
        glossary = {"entries": {"transformer": {"term": "transformer", "definition": "A model"}}}
        violations = validate_glossary_integrity(paper_state, glossary)
        assert violations == []

    def test_empty_entries_no_violations(self):
        paper_state = {"sections": []}
        glossary = {"entries": {}}
        violations = validate_glossary_integrity(paper_state, glossary)
        assert violations == []

    def test_term_id_referenced_but_not_in_glossary_is_violation(self):
        """section 有 term_ids 但 glossary 中不存在该 term -> violation。"""
        paper_state = {
            "sections": [
                {
                    "section_id": "method",
                    "claim_ids": [],
                    "asset_ids": [],
                    "citation_keys": [],
                    "term_ids": ["unknown_term"],
                }
            ]
        }
        glossary = {"entries": {}}
        violations = validate_glossary_integrity(paper_state, glossary)
        assert len(violations) == 1
        assert violations[0].missing_key == "unknown_term"
        assert violations[0].target == "glossary"

    def test_term_id_in_glossary_no_violation(self):
        paper_state = {
            "sections": [
                {
                    "section_id": "method",
                    "claim_ids": [],
                    "asset_ids": [],
                    "citation_keys": [],
                    "term_ids": ["transformer"],
                }
            ]
        }
        glossary = {"entries": {"transformer": {"term": "transformer", "definition": "A model"}}}
        violations = validate_glossary_integrity(paper_state, glossary)
        assert violations == []


# ---------------------------------------------------------------------------
# Symbol Integrity
# ---------------------------------------------------------------------------

class TestSymbolIntegrity:
    def test_valid_symbols_no_violations(self):
        paper_state = {
            "sections": [
                {"section_id": "method", "claim_ids": [], "asset_ids": [], "citation_keys": []}
            ]
        }
        symbols = {"entries": {"\\alpha": {"symbol": "\\alpha", "meaning": "learning rate"}}}
        violations = validate_symbol_integrity(paper_state, symbols)
        assert violations == []

    def test_empty_entries_no_violations(self):
        paper_state = {"sections": []}
        symbols = {"entries": {}}
        violations = validate_symbol_integrity(paper_state, symbols)
        assert violations == []

    def test_symbol_id_referenced_but_not_in_symbols_is_violation(self):
        """section 有 symbol_ids 但 symbols 中不存在 -> violation。"""
        paper_state = {
            "sections": [
                {
                    "section_id": "method",
                    "claim_ids": [],
                    "asset_ids": [],
                    "citation_keys": [],
                    "symbol_ids": ["\\beta"],
                }
            ]
        }
        symbols = {"entries": {}}
        violations = validate_symbol_integrity(paper_state, symbols)
        assert len(violations) == 1
        assert violations[0].missing_key == "\\beta"
        assert violations[0].target == "symbols"

    def test_symbol_id_in_symbols_no_violation(self):
        paper_state = {
            "sections": [
                {
                    "section_id": "method",
                    "claim_ids": [],
                    "asset_ids": [],
                    "citation_keys": [],
                    "symbol_ids": ["\\alpha"],
                }
            ]
        }
        symbols = {"entries": {"\\alpha": {"symbol": "\\alpha", "meaning": "learning rate"}}}
        violations = validate_symbol_integrity(paper_state, symbols)
        assert violations == []


# ---------------------------------------------------------------------------
# Integrity integration: glossary/symbols in validate_referential_integrity
# ---------------------------------------------------------------------------

class TestIntegrityWithGlossarySymbols:
    def test_glossary_integrated_into_validate_referential_integrity(self):
        paper_state = {
            "sections": [
                {"section_id": "s1", "claim_ids": [], "asset_ids": [], "citation_keys": []}
            ]
        }
        glossary = {"entries": {}}
        violations = validate_referential_integrity(paper_state, [], [], glossary=glossary)
        assert violations == []

    def test_symbols_integrated_into_validate_referential_integrity(self):
        paper_state = {
            "sections": [
                {"section_id": "s1", "claim_ids": [], "asset_ids": [], "citation_keys": []}
            ]
        }
        symbols = {"entries": {}}
        violations = validate_referential_integrity(paper_state, [], [], symbols=symbols)
        assert violations == []

    def test_glossary_violation_propagated_through_validate_referential_integrity(self):
        """通过 validate_referential_integrity 调用时，glossary 违规也应被检出。"""
        paper_state = {
            "sections": [
                {
                    "section_id": "s1",
                    "claim_ids": [],
                    "asset_ids": [],
                    "citation_keys": [],
                    "term_ids": ["missing_term"],
                }
            ]
        }
        glossary = {"entries": {}}
        violations = validate_referential_integrity(paper_state, [], [], glossary=glossary)
        assert len(violations) == 1
        assert violations[0].missing_key == "missing_term"

    def test_symbols_violation_propagated_through_validate_referential_integrity(self):
        """通过 validate_referential_integrity 调用时，symbols 违规也应被检出。"""
        paper_state = {
            "sections": [
                {
                    "section_id": "s1",
                    "claim_ids": [],
                    "asset_ids": [],
                    "citation_keys": [],
                    "symbol_ids": ["\\missing"],
                }
            ]
        }
        symbols = {"entries": {}}
        violations = validate_referential_integrity(paper_state, [], [], symbols=symbols)
        assert len(violations) == 1
        assert violations[0].missing_key == "\\missing"

    def test_none_glossary_and_symbols_skipped(self):
        """glossary=None 和 symbols=None 时不触发额外校验。"""
        paper_state = {
            "sections": [
                {"section_id": "s1", "claim_ids": [], "asset_ids": [], "citation_keys": []}
            ]
        }
        violations = validate_referential_integrity(paper_state, [], [], glossary=None, symbols=None)
        assert violations == []
