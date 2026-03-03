"""Tests for regex_healer module — focused on fix_illegal_escapes double-backslash bug."""
from __future__ import annotations

import json

import pytest

from vibewriting.contracts.healers.regex_healer import fix_illegal_escapes, heal


class TestFixIllegalEscapes:
    def test_preserves_valid_double_backslash_regex(self) -> None:
        """Valid regex patterns with \\\\d should not be modified."""
        # In Python source: '{"pattern":"^EC-\\\\d{4}-\\\\d{3}$"}'
        # As JSON string:   {"pattern":"^EC-\\d{4}-\\d{3}$"}
        # After fix:        unchanged
        raw = '{"pattern":"^EC-\\\\d{4}-\\\\d{3}$"}'
        result = fix_illegal_escapes(raw)
        # Should be parseable as valid JSON
        parsed = json.loads(result)
        assert "\\d" in parsed["pattern"]  # still contains regex \d

    def test_repairs_invalid_single_backslash(self) -> None:
        """Invalid \\d (single backslash) should be repaired to \\\\d."""
        # JSON with invalid escape: {"x": "\d"}
        raw = '{"x": "\\d"}'
        result = fix_illegal_escapes(raw)
        # Should now be parseable
        parsed = json.loads(result)
        assert parsed["x"] == "\\d"  # fixed to literal backslash + d

    def test_preserves_valid_newline_escape(self) -> None:
        """Valid \\n escape should be preserved."""
        raw = '{"msg": "hello\\nworld"}'
        result = fix_illegal_escapes(raw)
        parsed = json.loads(result)
        assert parsed["msg"] == "hello\nworld"

    def test_preserves_valid_double_backslash(self) -> None:
        """Valid \\\\ (escaped backslash) should be preserved."""
        raw = '{"path": "C:\\\\Users\\\\test"}'
        result = fix_illegal_escapes(raw)
        parsed = json.loads(result)
        assert parsed["path"] == "C:\\Users\\test"

    def test_no_change_outside_strings(self) -> None:
        """Backslashes outside JSON strings should not be modified."""
        raw = '{"count": 5}'
        result = fix_illegal_escapes(raw)
        assert result == raw

    def test_heal_preserves_double_backslash_regex(self) -> None:
        """End-to-end: heal() should preserve valid regex with \\\\d."""
        raw = '{"pattern": "^EC-\\\\d{4}-\\\\d{3}$"}'
        result = heal(raw)
        parsed = json.loads(result)
        assert parsed["pattern"] == "^EC-\\d{4}-\\d{3}$"

    def test_preserves_valid_tab_escape(self) -> None:
        """Valid \\t escape should be preserved."""
        raw = '{"data": "col1\\tcol2"}'
        result = fix_illegal_escapes(raw)
        parsed = json.loads(result)
        assert parsed["data"] == "col1\tcol2"

    def test_preserves_valid_unicode_escape(self) -> None:
        """Valid \\uXXXX escape should be preserved."""
        raw = '{"char": "\\u0041"}'
        result = fix_illegal_escapes(raw)
        parsed = json.loads(result)
        assert parsed["char"] == "A"

    def test_repairs_multiple_invalid_escapes(self) -> None:
        """Multiple invalid escapes in one string should all be repaired."""
        raw = '{"re": "\\d+\\.\\w+"}'
        result = fix_illegal_escapes(raw)
        parsed = json.loads(result)
        # \d -> \\d, \. stays valid (dot after backslash is invalid -> doubled),
        # \w -> \\w
        assert "\\d" in parsed["re"]
        assert "\\w" in parsed["re"]

    def test_mixed_valid_and_invalid_escapes(self) -> None:
        """Mix of valid (\\n) and invalid (\\d) escapes."""
        raw = '{"x": "line1\\nregex\\d+"}'
        result = fix_illegal_escapes(raw)
        parsed = json.loads(result)
        assert "line1\nregex\\d+" == parsed["x"]

    def test_empty_string_value(self) -> None:
        """Empty string values should pass through unchanged."""
        raw = '{"x": ""}'
        result = fix_illegal_escapes(raw)
        assert result == raw
        parsed = json.loads(result)
        assert parsed["x"] == ""

    def test_idempotent_on_already_valid_json(self) -> None:
        """Already valid JSON should not be modified."""
        raw = '{"a": 1, "b": "hello", "c": true}'
        result = fix_illegal_escapes(raw)
        assert result == raw
