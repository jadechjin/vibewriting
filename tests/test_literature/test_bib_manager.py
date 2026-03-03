"""Tests for bib_manager module."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from vibewriting.literature.bib_manager import (
    BibEntry,
    MergeReport,
    merge_bib,
    normalize_cite_key,
    normalize_entry,
    parse_bib,
    write_bib,
)


@pytest.fixture
def sample_bib_content() -> str:
    return textwrap.dedent("""\
        @article{vaswani2017attention,
          title = {Attention Is All You Need},
          author = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki},
          year = {2017},
          journal = {Advances in Neural Information Processing Systems},
        }

        @inproceedings{devlin2019bert,
          title = {BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding},
          author = {Devlin, Jacob and Chang, Ming-Wei and Lee, Kenton},
          year = {2019},
          booktitle = {NAACL-HLT},
        }
    """)


@pytest.fixture
def sample_bib_file(tmp_path: Path, sample_bib_content: str) -> Path:
    p = tmp_path / "test.bib"
    p.write_text(sample_bib_content, encoding="utf-8")
    return p


class TestParseBib:
    def test_parse_valid_file(self, sample_bib_file: Path) -> None:
        entries = parse_bib(sample_bib_file)
        assert len(entries) == 2
        keys = {e.key for e in entries}
        assert "vaswani2017attention" in keys
        assert "devlin2019bert" in keys

    def test_parse_returns_bib_entries(self, sample_bib_file: Path) -> None:
        entries = parse_bib(sample_bib_file)
        for e in entries:
            assert isinstance(e, BibEntry)
            assert e.key
            assert e.entry_type
            assert isinstance(e.fields, dict)

    def test_parse_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.bib"
        p.write_text("", encoding="utf-8")
        entries = parse_bib(p)
        assert entries == []

    def test_parse_nonexistent_file(self, tmp_path: Path) -> None:
        p = tmp_path / "nonexistent.bib"
        with pytest.raises((FileNotFoundError, OSError)):
            parse_bib(p)


class TestNormalizeEntry:
    def test_lowercase_fields(self) -> None:
        entry = BibEntry(
            key="test2024",
            entry_type="article",
            fields={"Title": " Some Title ", "YEAR": "2024"},
        )
        result = normalize_entry(entry)
        assert "title" in result.fields
        assert "year" in result.fields
        assert result.fields["title"] == "Some Title"
        assert result.fields["year"] == "2024"

    def test_idempotency(self) -> None:
        entry = BibEntry(
            key="test2024",
            entry_type="article",
            fields={"title": "Clean Title", "year": "2024"},
        )
        once = normalize_entry(entry)
        twice = normalize_entry(once)
        assert once.fields == twice.fields


class TestNormalizeCiteKey:
    def test_basic_generation(self) -> None:
        entry = BibEntry(
            key="old_key",
            entry_type="article",
            fields={
                "author": "Vaswani, Ashish and Shazeer, Noam",
                "year": "2017",
                "title": "Attention Is All You Need",
            },
        )
        key = normalize_cite_key(entry)
        assert key == "vaswani2017attention"

    def test_conflict_suffix(self) -> None:
        entry = BibEntry(
            key="old",
            entry_type="article",
            fields={
                "author": "Vaswani, Ashish",
                "year": "2017",
                "title": "Attention Is All You Need",
            },
        )
        key = normalize_cite_key(entry, existing_keys={"vaswani2017attention"})
        assert key == "vaswani2017attentiona"

    def test_missing_author_fallback(self) -> None:
        entry = BibEntry(
            key="old",
            entry_type="article",
            fields={"year": "2024", "title": "Some Paper"},
        )
        key = normalize_cite_key(entry)
        assert "2024" in key


class TestMergeBib:
    def test_add_new_entries(self) -> None:
        existing = [
            BibEntry(key="a2020", entry_type="article", fields={"title": "A", "year": "2020"}),
        ]
        new = [
            BibEntry(key="b2021", entry_type="article", fields={"title": "B", "year": "2021"}),
        ]
        merged, report = merge_bib(existing, new)
        assert "b2021" in report.added
        assert len(merged) == 2

    def test_conflict_preserves_existing(self) -> None:
        existing = [
            BibEntry(key="a2020", entry_type="article", fields={"title": "Original A", "year": "2020"}),
        ]
        new = [
            BibEntry(key="a2020", entry_type="article", fields={"title": "New A", "year": "2020"}),
        ]
        merged, report = merge_bib(existing, new)
        assert "a2020" in report.conflicts
        # Existing entry preserved
        a_entry = next(e for e in merged if e.key == "a2020")
        assert a_entry.fields["title"] == "Original A"

    def test_update_auto_generated(self) -> None:
        existing = [
            BibEntry(key="a2020", entry_type="article",
                     fields={"title": "Old A", "year": "2020", "note": "auto-generated"}),
        ]
        new = [
            BibEntry(key="a2020", entry_type="article", fields={"title": "Updated A", "year": "2020"}),
        ]
        merged, report = merge_bib(existing, new)
        assert "a2020" in report.updated
        a_entry = next(e for e in merged if e.key == "a2020")
        assert a_entry.fields["title"] == "Updated A"


class TestWriteBib:
    def test_write_and_read_round_trip(self, tmp_path: Path) -> None:
        entries = [
            BibEntry(key="b2021", entry_type="article", fields={"title": "B Paper", "year": "2021"}),
            BibEntry(key="a2020", entry_type="inproceedings", fields={"title": "A Paper", "year": "2020"}),
        ]
        out = tmp_path / "output.bib"
        write_bib(entries, out)
        assert out.exists()

        # Read back
        parsed = parse_bib(out)
        assert len(parsed) == 2
        # Should be sorted by key
        keys = [e.key for e in parsed]
        assert keys == sorted(keys)

    def test_atomic_write(self, tmp_path: Path) -> None:
        out = tmp_path / "atomic.bib"
        entries = [BibEntry(key="x2024", entry_type="article", fields={"title": "X", "year": "2024"})]
        write_bib(entries, out)
        # No .tmp file should remain
        assert not (tmp_path / "atomic.bib.tmp").exists()
        assert out.exists()

    def test_sorted_output(self, tmp_path: Path) -> None:
        entries = [
            BibEntry(key="z2024", entry_type="article", fields={"title": "Z", "year": "2024"}),
            BibEntry(key="a2024", entry_type="article", fields={"title": "A", "year": "2024"}),
            BibEntry(key="m2024", entry_type="article", fields={"title": "M", "year": "2024"}),
        ]
        out = tmp_path / "sorted.bib"
        write_bib(entries, out)
        parsed = parse_bib(out)
        keys = [e.key for e in parsed]
        assert keys == ["a2024", "m2024", "z2024"]


class TestRoundTrip:
    def test_parse_write_parse_semantic_consistency(self, sample_bib_file: Path, tmp_path: Path) -> None:
        """Parse → write → parse should preserve semantic content."""
        entries1 = parse_bib(sample_bib_file)
        out = tmp_path / "roundtrip.bib"
        write_bib(entries1, out)
        entries2 = parse_bib(out)

        assert len(entries1) == len(entries2)
        for e1, e2 in zip(sorted(entries1, key=lambda e: e.key), sorted(entries2, key=lambda e: e.key)):
            assert e1.key == e2.key
            assert e1.entry_type == e2.entry_type
            # Fields should be semantically equivalent
            for k in e1.fields:
                assert e1.fields[k].strip() == e2.fields.get(k, "").strip(), f"Field {k} differs"
