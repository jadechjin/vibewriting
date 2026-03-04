"""Tests for citation audit module."""

from __future__ import annotations

import json
from pathlib import Path

from vibewriting.review.citation_audit import (
    crosscheck_with_evidence_cards,
    extract_all_cite_keys,
    extract_all_claim_ids,
    run_citation_audit,
)


class TestExtractCiteKeys:
    def test_extract_citep(self, tmp_paper_dir: Path):
        keys = extract_all_cite_keys(tmp_paper_dir)
        assert "smith2023" in keys

    def test_extract_multiple_keys(self, tmp_path: Path):
        d = tmp_path / "paper"
        d.mkdir()
        (d / "test.tex").write_text(
            "\\citep{a2023,b2024} and \\citet{c2025}\n", encoding="utf-8",
        )
        keys = extract_all_cite_keys(d)
        assert keys == {"a2023", "b2024", "c2025"}

    def test_empty_dir(self, tmp_path: Path):
        d = tmp_path / "empty"
        d.mkdir()
        assert extract_all_cite_keys(d) == set()


class TestExtractClaimIds:
    def test_extract_claim_id(self, tmp_paper_dir: Path):
        ids = extract_all_claim_ids(tmp_paper_dir)
        all_ids = [cid for cids in ids.values() for cid in cids]
        assert "EC-0001-001" in all_ids

    def test_no_claims(self, tmp_path: Path):
        d = tmp_path / "paper"
        d.mkdir()
        (d / "test.tex").write_text("No claims here\n", encoding="utf-8")
        assert extract_all_claim_ids(d) == {}


class TestCrosscheckEvidenceCards:
    def test_all_matched(self, cards_path: Path):
        claim_ids = {"intro.tex": ["EC-0001-001"]}
        result = crosscheck_with_evidence_cards(claim_ids, cards_path)
        assert result.verified_count == 1
        assert result.orphan_claims == []

    def test_orphan_claim(self, cards_path: Path):
        claim_ids = {"intro.tex": ["EC-0001-001", "EC-9999-999"]}
        result = crosscheck_with_evidence_cards(claim_ids, cards_path)
        assert "EC-9999-999" in result.orphan_claims

    def test_missing_cards_file(self, tmp_path: Path):
        missing = tmp_path / "nonexistent.jsonl"
        result = crosscheck_with_evidence_cards({"f": ["EC-0001-001"]}, missing)
        assert result.verified_count == 0

    def test_deduplicates_claim_ids(self, cards_path: Path):
        claim_ids = {"intro.tex": ["EC-0001-001", "EC-0001-001"]}
        result = crosscheck_with_evidence_cards(claim_ids, cards_path)
        assert result.verified_count == 1

    def test_returns_sorted_missing_and_orphan(self, tmp_path: Path):
        cards = tmp_path / "cards.jsonl"
        cards.write_text(
            "\n".join([
                json.dumps({"claim_id": "EC-0003-001"}),
                json.dumps({"claim_id": "EC-0002-001"}),
            ]),
            encoding="utf-8",
        )
        claim_ids = {"intro.tex": ["EC-0004-001", "EC-0001-001"]}

        result = crosscheck_with_evidence_cards(claim_ids, cards)

        assert result.orphan_claims == ["EC-0001-001", "EC-0004-001"]
        assert result.missing_evidence_cards == ["EC-0002-001", "EC-0003-001"]


class TestRunCitationAudit:
    def test_full_audit(self, tmp_paper_dir: Path, cards_path: Path):
        bib_path = tmp_paper_dir / "bib" / "references.bib"
        result = run_citation_audit(
            tmp_paper_dir, cards_path, bib_path, skip_external_api=True,
        )
        assert result.verified_count >= 0
        assert isinstance(result.suspicious_keys, list)
