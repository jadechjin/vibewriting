"""Tests for evidence module."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from vibewriting.literature.evidence import (
    compute_content_hash,
    create_evidence_card,
    next_claim_id,
)
from vibewriting.literature.models import RawLiteratureRecord
from vibewriting.models.evidence_card import EvidenceCard


class TestNextClaimId:
    def test_first_id_of_year(self) -> None:
        result = next_claim_id([])
        year = datetime.now(UTC).year
        assert result == f"EC-{year}-001"

    def test_increments_from_existing(self, sample_evidence_cards: list[EvidenceCard]) -> None:
        result = next_claim_id(sample_evidence_cards)
        year = datetime.now(UTC).year
        assert result == f"EC-{year}-003"

    def test_monotonicity(self) -> None:
        cards: list[EvidenceCard] = []
        ids = []
        for i in range(5):
            cid = next_claim_id(cards)
            ids.append(cid)
            cards.append(
                EvidenceCard(
                    claim_id=cid,
                    claim_text=f"Claim {i}",
                    bib_key=f"key{i}",
                    evidence_type="empirical",
                    retrieval_source="manual",
                )
            )
        # Extract numbers and verify monotonicity
        nums = [int(cid.split("-")[2]) for cid in ids]
        assert nums == sorted(nums)
        assert len(set(nums)) == len(nums)  # All unique

    def test_format_pattern(self) -> None:
        import re
        result = next_claim_id([])
        assert re.match(r"^EC-\d{4}-\d{3}$", result)


class TestComputeContentHash:
    def test_deterministic(self) -> None:
        h1 = compute_content_hash("same text")
        h2 = compute_content_hash("same text")
        assert h1 == h2

    def test_different_for_different_text(self) -> None:
        h1 = compute_content_hash("text a")
        h2 = compute_content_hash("text b")
        assert h1 != h2

    def test_returns_hex_string(self) -> None:
        h = compute_content_hash("test")
        assert len(h) == 16
        int(h, 16)  # Should not raise


class TestCreateEvidenceCard:
    def test_basic_creation(self, sample_raw_record: RawLiteratureRecord) -> None:
        card = create_evidence_card(
            raw_record=sample_raw_record,
            claim_text="Transformer eliminates recurrence.",
            supporting_quote="relying entirely on attention",
            bib_key="vaswani2017attention",
            evidence_type="empirical",
        )
        assert card.claim_id.startswith("EC-")
        assert card.claim_text == "Transformer eliminates recurrence."
        assert card.bib_key == "vaswani2017attention"
        assert card.content_hash is not None
        assert card.retrieval_source == "paper-search"

    def test_auto_paraphrase_on_long_quote(self, sample_raw_record: RawLiteratureRecord) -> None:
        long_quote = " ".join(["word"] * 60)
        card = create_evidence_card(
            raw_record=sample_raw_record,
            claim_text="Some claim.",
            supporting_quote=long_quote,
            bib_key="vaswani2017attention",
            evidence_type="empirical",
        )
        assert card.paraphrase is True

    def test_short_quote_not_paraphrase(self, sample_raw_record: RawLiteratureRecord) -> None:
        card = create_evidence_card(
            raw_record=sample_raw_record,
            claim_text="Some claim.",
            supporting_quote="short quote",
            bib_key="vaswani2017attention",
            evidence_type="empirical",
        )
        assert card.paraphrase is False

    def test_source_id_from_record(self, sample_raw_record: RawLiteratureRecord) -> None:
        card = create_evidence_card(
            raw_record=sample_raw_record,
            claim_text="Claim.",
            supporting_quote="quote",
            bib_key="vaswani2017attention",
            evidence_type="empirical",
        )
        assert card.source_id == sample_raw_record.primary_key

    def test_increments_claim_id(self, sample_raw_record: RawLiteratureRecord, sample_evidence_cards: list[EvidenceCard]) -> None:
        card = create_evidence_card(
            raw_record=sample_raw_record,
            claim_text="New claim.",
            supporting_quote="quote",
            bib_key="vaswani2017attention",
            evidence_type="empirical",
            existing_cards=sample_evidence_cards,
        )
        year = datetime.now(UTC).year
        expected_num = max(int(c.claim_id.split("-")[2]) for c in sample_evidence_cards if c.claim_id.startswith(f"EC-{year}-")) + 1
        assert card.claim_id == f"EC-{year}-{expected_num:03d}"
