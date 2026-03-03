"""Tests for Glossary and SymbolTable models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from vibewriting.models.glossary import GlossaryEntry, Glossary, SymbolEntry, SymbolTable


# ---------------------------------------------------------------------------
# GlossaryEntry tests
# ---------------------------------------------------------------------------


def test_glossary_entry_normal_creation():
    entry = GlossaryEntry(term="overfitting", definition="Model memorizes training data")
    assert entry.term == "overfitting"
    assert entry.definition == "Model memorizes training data"


def test_glossary_entry_empty_term_raises():
    with pytest.raises(ValidationError):
        GlossaryEntry(term="", definition="some definition")


def test_glossary_entry_empty_definition_raises():
    with pytest.raises(ValidationError):
        GlossaryEntry(term="term", definition="")


def test_glossary_entry_defaults():
    entry = GlossaryEntry(term="t", definition="d")
    assert entry.first_used_in == ""
    assert entry.aliases == []


def test_glossary_entry_extra_field_forbidden():
    with pytest.raises(ValidationError):
        GlossaryEntry(term="t", definition="d", unknown_field="x")


# ---------------------------------------------------------------------------
# SymbolEntry tests
# ---------------------------------------------------------------------------


def test_symbol_entry_normal_creation():
    entry = SymbolEntry(symbol=r"\alpha", meaning="learning rate")
    assert entry.symbol == r"\alpha"
    assert entry.meaning == "learning rate"


def test_symbol_entry_empty_symbol_raises():
    with pytest.raises(ValidationError):
        SymbolEntry(symbol="", meaning="something")


def test_symbol_entry_empty_meaning_raises():
    with pytest.raises(ValidationError):
        SymbolEntry(symbol=r"\beta", meaning="")


def test_symbol_entry_defaults():
    entry = SymbolEntry(symbol=r"\gamma", meaning="discount factor")
    assert entry.first_used_in == ""
    assert entry.latex_command == ""


# ---------------------------------------------------------------------------
# Glossary tests
# ---------------------------------------------------------------------------


def test_glossary_empty_creation():
    g = Glossary()
    assert g.entries == {}


def test_glossary_add_term_returns_new_instance():
    g = Glossary()
    g2 = g.add_term("loss", "training objective")
    assert g2 is not g


def test_glossary_add_multiple_terms():
    g = Glossary()
    g = g.add_term("loss", "training objective")
    g = g.add_term("gradient", "partial derivative vector")
    assert "loss" in g.entries
    assert "gradient" in g.entries


def test_glossary_has_term_true():
    g = Glossary().add_term("epoch", "one full pass over training data")
    assert g.has_term("epoch") is True


def test_glossary_has_term_false():
    g = Glossary()
    assert g.has_term("epoch") is False


def test_glossary_lookup_exact_match():
    g = Glossary().add_term("batch", "subset of training data")
    entry = g.lookup("batch")
    assert entry is not None
    assert entry.term == "batch"


def test_glossary_lookup_via_alias():
    g = Glossary()
    g2 = g.add_term("batch", "subset of training data")
    # manually set alias via model_copy on entry
    entry_with_alias = g2.entries["batch"].model_copy(update={"aliases": ["mini-batch"]})
    g3 = g2.model_copy(update={"entries": {**g2.entries, "batch": entry_with_alias}})
    result = g3.lookup("mini-batch")
    assert result is not None
    assert result.term == "batch"


def test_glossary_lookup_missing_returns_none():
    g = Glossary()
    assert g.lookup("nonexistent") is None


def test_glossary_add_term_overwrites_existing():
    g = Glossary().add_term("loss", "old definition")
    g2 = g.add_term("loss", "new definition")
    assert g2.entries["loss"].definition == "new definition"


def test_glossary_serialization_roundtrip():
    g = Glossary().add_term("regularization", "technique to reduce overfitting", section_id="sec1")
    json_str = g.model_dump_json()
    restored = Glossary.model_validate_json(json_str)
    assert restored.entries["regularization"].definition == "technique to reduce overfitting"
    assert restored.entries["regularization"].first_used_in == "sec1"


# ---------------------------------------------------------------------------
# SymbolTable tests
# ---------------------------------------------------------------------------


def test_symbol_table_empty_creation():
    st = SymbolTable()
    assert st.entries == {}


def test_symbol_table_add_symbol_returns_new_instance():
    st = SymbolTable()
    st2 = st.add_symbol(r"\alpha", "learning rate")
    assert st2 is not st


def test_symbol_table_has_symbol_true():
    st = SymbolTable().add_symbol(r"\lambda", "regularization coefficient")
    assert st.has_symbol(r"\lambda") is True


def test_symbol_table_has_symbol_false():
    st = SymbolTable()
    assert st.has_symbol(r"\lambda") is False


def test_symbol_table_check_consistency_no_issues():
    st = SymbolTable().add_symbol(r"\alpha", "learning rate")
    sections = {
        "sec1": r"We set \alpha=0.01",
        "sec2": r"The value of \beta is fixed",
    }
    issues = st.check_consistency(sections)
    assert issues == []


def test_symbol_table_check_consistency_detects_issue():
    # Create a symbol with empty meaning (bypass Field min_length via model_copy hack)
    # The check_consistency logic only triggers when meaning is empty,
    # but SymbolEntry enforces min_length=1. We test via direct entry injection.
    st = SymbolTable()
    # Inject an entry with no meaning by bypassing validation (model_construct)
    bad_entry = SymbolEntry.model_construct(symbol=r"\zeta", meaning="", first_used_in="", latex_command="")
    st_with_bad = st.model_copy(update={"entries": {r"\zeta": bad_entry}})
    sections = {
        "sec1": r"We use \zeta here",
        "sec2": r"Also \zeta appears again",
    }
    issues = st_with_bad.check_consistency(sections)
    assert len(issues) == 1
    assert r"\zeta" in issues[0]


def test_symbol_table_serialization_roundtrip():
    st = SymbolTable().add_symbol(r"\theta", "model parameters", section_id="intro")
    json_str = st.model_dump_json()
    restored = SymbolTable.model_validate_json(json_str)
    assert restored.entries[r"\theta"].meaning == "model parameters"
    assert restored.entries[r"\theta"].first_used_in == "intro"


# ---------------------------------------------------------------------------
# Immutability verification
# ---------------------------------------------------------------------------


def test_glossary_add_term_original_unchanged():
    g_original = Glossary()
    _ = g_original.add_term("term", "definition")
    assert "term" not in g_original.entries
    assert len(g_original.entries) == 0


def test_symbol_table_add_symbol_original_unchanged():
    st_original = SymbolTable()
    _ = st_original.add_symbol(r"\pi", "constant pi")
    assert r"\pi" not in st_original.entries
    assert len(st_original.entries) == 0
