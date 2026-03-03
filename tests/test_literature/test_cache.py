"""Tests for cache module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibewriting.literature.cache import LiteratureCache
from vibewriting.models.evidence_card import EvidenceCard


@pytest.fixture
def cache_path(tmp_path: Path) -> Path:
    return tmp_path / "literature" / "cards.jsonl"


@pytest.fixture
def cache(cache_path: Path) -> LiteratureCache:
    return LiteratureCache(cache_path)


class TestLoad:
    def test_load_empty(self, cache: LiteratureCache) -> None:
        count = cache.load()
        assert count == 0
        assert cache.count() == 0

    def test_load_existing_file(self, cache_path: Path, cache: LiteratureCache, sample_evidence_card: EvidenceCard) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(sample_evidence_card.model_dump_json() + "\n")

        count = cache.load()
        assert count == 1
        assert cache.has(sample_evidence_card.claim_id)

    def test_load_skips_corrupted_lines(self, cache_path: Path, cache: LiteratureCache, sample_evidence_card: EvidenceCard) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(sample_evidence_card.model_dump_json() + "\n")
            f.write("THIS IS NOT JSON\n")
            f.write("{bad json\n")

        count = cache.load()
        assert count == 1  # Only the valid line loaded


class TestUpsert:
    def test_upsert_new_card(self, cache: LiteratureCache, sample_evidence_card: EvidenceCard) -> None:
        cache.upsert(sample_evidence_card)
        assert cache.has(sample_evidence_card.claim_id)
        assert cache.count() == 1

    def test_upsert_creates_parent_dir(self, cache: LiteratureCache, sample_evidence_card: EvidenceCard) -> None:
        cache.upsert(sample_evidence_card)
        assert cache._path.parent.exists()

    def test_upsert_writes_to_file(self, cache: LiteratureCache, cache_path: Path, sample_evidence_card: EvidenceCard) -> None:
        cache.upsert(sample_evidence_card)
        assert cache_path.exists()
        lines = cache_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["claim_id"] == sample_evidence_card.claim_id

    def test_upsert_idempotency(self, cache: LiteratureCache, sample_evidence_card: EvidenceCard) -> None:
        """Upserting the same card twice should not duplicate in index."""
        cache.upsert(sample_evidence_card)
        cache.upsert(sample_evidence_card)
        assert cache.count() == 1

    def test_upsert_multiple_cards(self, cache: LiteratureCache, sample_evidence_cards: list[EvidenceCard]) -> None:
        for card in sample_evidence_cards:
            cache.upsert(card)
        assert cache.count() == len(sample_evidence_cards)


class TestQuery:
    def test_query_by_claim_id(self, cache: LiteratureCache, sample_evidence_cards: list[EvidenceCard]) -> None:
        for c in sample_evidence_cards:
            cache.upsert(c)
        result = cache.query(claim_id="EC-2026-001")
        assert len(result) == 1
        assert result[0].claim_id == "EC-2026-001"

    def test_query_by_bib_key(self, cache: LiteratureCache, sample_evidence_cards: list[EvidenceCard]) -> None:
        for c in sample_evidence_cards:
            cache.upsert(c)
        result = cache.query(bib_key="devlin2019bert")
        assert len(result) == 1
        assert result[0].bib_key == "devlin2019bert"

    def test_query_by_tags(self, cache: LiteratureCache, sample_evidence_cards: list[EvidenceCard]) -> None:
        for c in sample_evidence_cards:
            cache.upsert(c)
        result = cache.query(tags=["transformer"])
        assert len(result) == 1

    def test_query_by_evidence_type(self, cache: LiteratureCache, sample_evidence_cards: list[EvidenceCard]) -> None:
        for c in sample_evidence_cards:
            cache.upsert(c)
        result = cache.query(evidence_type="empirical")
        assert len(result) == 2

    def test_query_no_filters_returns_all(self, cache: LiteratureCache, sample_evidence_cards: list[EvidenceCard]) -> None:
        for c in sample_evidence_cards:
            cache.upsert(c)
        result = cache.query()
        assert len(result) == len(sample_evidence_cards)

    def test_query_nonexistent(self, cache: LiteratureCache) -> None:
        result = cache.query(claim_id="EC-9999-999")
        assert result == []


class TestGet:
    def test_get_existing(self, cache: LiteratureCache, sample_evidence_card: EvidenceCard) -> None:
        cache.upsert(sample_evidence_card)
        result = cache.get(sample_evidence_card.claim_id)
        assert result is not None
        assert result.claim_id == sample_evidence_card.claim_id

    def test_get_nonexistent(self, cache: LiteratureCache) -> None:
        result = cache.get("EC-9999-999")
        assert result is None


class TestDetectDrift:
    def test_no_drift_same_hash(self, cache: LiteratureCache, sample_evidence_card: EvidenceCard) -> None:
        cache.upsert(sample_evidence_card)
        assert cache.detect_drift(sample_evidence_card) is False

    def test_drift_different_hash(self, cache: LiteratureCache, sample_evidence_card: EvidenceCard) -> None:
        cache.upsert(sample_evidence_card)
        modified = sample_evidence_card.model_copy(update={"content_hash": "different_hash_value"})
        assert cache.detect_drift(modified) is True

    def test_no_drift_when_not_in_cache(self, cache: LiteratureCache, sample_evidence_card: EvidenceCard) -> None:
        assert cache.detect_drift(sample_evidence_card) is False


class TestConsistency:
    def test_memory_equals_reload(self, cache: LiteratureCache, cache_path: Path, sample_evidence_cards: list[EvidenceCard]) -> None:
        """Memory index should equal a fresh full reload."""
        for c in sample_evidence_cards:
            cache.upsert(c)

        # Create a new cache from the same file
        fresh = LiteratureCache(cache_path)
        fresh.load()

        assert cache.count() == fresh.count()
        for cid in [c.claim_id for c in sample_evidence_cards]:
            assert cache.get(cid) is not None
            assert fresh.get(cid) is not None
            assert cache.get(cid).claim_id == fresh.get(cid).claim_id
