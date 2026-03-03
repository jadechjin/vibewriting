"""Tests for dedup module."""

from __future__ import annotations

import pytest

from vibewriting.literature.dedup import (
    DeduplicationReport,
    dedup_by_primary_key,
    dedup_by_similarity,
    dedup_claims,
    deduplicate,
    normalize_title,
    token_jaccard,
)
from vibewriting.literature.models import RawLiteratureRecord
from vibewriting.models.evidence_card import EvidenceCard


class TestNormalizeTitle:
    def test_lowercase(self) -> None:
        assert "attention" in normalize_title("ATTENTION")

    def test_remove_punctuation(self) -> None:
        result = normalize_title("Hello, World!")
        assert "," not in result
        assert "!" not in result

    def test_remove_stop_words(self) -> None:
        result = normalize_title("The Art of Programming")
        assert "the" not in result.split()
        assert "of" not in result.split()

    def test_idempotency(self) -> None:
        text = "Some Random Title: A Study"
        assert normalize_title(text) == normalize_title(normalize_title(text))


class TestTokenJaccard:
    def test_identical_strings(self) -> None:
        assert token_jaccard("hello world", "hello world") == 1.0

    def test_completely_different(self) -> None:
        assert token_jaccard("hello world", "foo bar") == 0.0

    def test_partial_overlap(self) -> None:
        score = token_jaccard("hello world foo", "hello world bar")
        assert 0.0 < score < 1.0

    def test_empty_strings(self) -> None:
        assert token_jaccard("", "") == 0.0

    def test_symmetric(self) -> None:
        a, b = "hello world foo", "foo bar baz"
        assert token_jaccard(a, b) == token_jaccard(b, a)


class TestDedupByPrimaryKey:
    def test_removes_doi_duplicates(self) -> None:
        records = [
            RawLiteratureRecord(title="Paper A", authors=["A"], year=2020, doi="10.1234/a"),
            RawLiteratureRecord(title="Paper A (copy)", authors=["A"], year=2020, doi="10.1234/a"),
        ]
        result = dedup_by_primary_key(records)
        assert len(result) == 1

    def test_keeps_different_records(self, sample_raw_records: list[RawLiteratureRecord]) -> None:
        result = dedup_by_primary_key(sample_raw_records)
        assert len(result) == len(sample_raw_records)

    def test_empty_input(self) -> None:
        assert dedup_by_primary_key([]) == []

    def test_preserves_first_occurrence(self) -> None:
        r1 = RawLiteratureRecord(title="First", authors=["A"], year=2020, doi="10.1234/a")
        r2 = RawLiteratureRecord(title="Second", authors=["A"], year=2020, doi="10.1234/a")
        result = dedup_by_primary_key([r1, r2])
        assert result[0].title == "First"


class TestDedupBySimilarity:
    def test_removes_similar_titles(self) -> None:
        records = [
            RawLiteratureRecord(title="Attention Is All You Need", authors=["V"], year=2017),
            RawLiteratureRecord(title="Attention is All You Need", authors=["V"], year=2017),
        ]
        result = dedup_by_similarity(records, threshold=0.9)
        assert len(result) == 1

    def test_keeps_different_titles(self) -> None:
        records = [
            RawLiteratureRecord(title="Attention Is All You Need", authors=["V"], year=2017),
            RawLiteratureRecord(title="BERT Pre-training", authors=["D"], year=2019),
        ]
        result = dedup_by_similarity(records, threshold=0.9)
        assert len(result) == 2

    def test_threshold_sensitivity(self) -> None:
        records = [
            RawLiteratureRecord(title="Machine Learning Basics", authors=["A"], year=2020),
            RawLiteratureRecord(title="Machine Learning Fundamentals", authors=["B"], year=2020),
        ]
        # Low threshold should merge them
        strict = dedup_by_similarity(records, threshold=0.3)
        # High threshold should keep them
        loose = dedup_by_similarity(records, threshold=0.99)
        assert len(strict) <= len(loose)


class TestDedupClaims:
    def test_removes_duplicate_claims_same_bib(self) -> None:
        cards = [
            EvidenceCard(
                claim_id="EC-2026-001",
                claim_text="Transformers use attention.",
                bib_key="vaswani2017",
                evidence_type="empirical",
                quality_score=8,
                retrieval_source="paper-search",
                content_hash="abc123",
            ),
            EvidenceCard(
                claim_id="EC-2026-002",
                claim_text="Transformers use attention.",
                bib_key="vaswani2017",
                evidence_type="empirical",
                quality_score=5,
                retrieval_source="paper-search",
                content_hash="abc123",
            ),
        ]
        result = dedup_claims(cards)
        assert len(result) == 1
        assert result[0].quality_score == 8  # Keeps highest

    def test_keeps_different_claims(self, sample_evidence_cards: list[EvidenceCard]) -> None:
        result = dedup_claims(sample_evidence_cards)
        assert len(result) == len(sample_evidence_cards)

    def test_empty_input(self) -> None:
        assert dedup_claims([]) == []


class TestDeduplicate:
    def test_monotonicity(self) -> None:
        """L2 <= L1 <= input."""
        records = [
            RawLiteratureRecord(title="Attention Is All You Need", authors=["V"], year=2017, doi="10.1/a"),
            RawLiteratureRecord(title="Attention is All You Need", authors=["V"], year=2017, doi="10.1/b"),
            RawLiteratureRecord(title="BERT Paper", authors=["D"], year=2019, doi="10.1/c"),
        ]
        result, report = deduplicate(records, threshold=0.9)
        assert report.l2_count <= report.l1_count <= report.input_count

    def test_idempotency(self, sample_raw_records: list[RawLiteratureRecord]) -> None:
        """dedup(dedup(x)) == dedup(x)."""
        result1, _ = deduplicate(sample_raw_records)
        result2, _ = deduplicate(result1)
        assert len(result1) == len(result2)

    def test_empty_input(self) -> None:
        result, report = deduplicate([])
        assert result == []
        assert report.input_count == 0

    def test_single_record(self) -> None:
        records = [RawLiteratureRecord(title="Solo", authors=["A"], year=2024)]
        result, report = deduplicate(records)
        assert len(result) == 1
        assert report.l1_count == 1
