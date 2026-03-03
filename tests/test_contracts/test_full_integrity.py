"""Tests for full contract integrity validation."""

from __future__ import annotations

import hashlib
from pathlib import Path

from vibewriting.contracts.full_integrity import (
    validate_all_tex_citations,
    validate_asset_hashes,
    validate_end_to_end,
    validate_glossary_in_tex,
    validate_sections_complete,
    validate_symbols_in_tex,
)


class TestValidateAllTexCitations:
    def test_valid_citation(self, tmp_path: Path):
        paper = tmp_path / "paper"
        paper.mkdir()
        (paper / "test.tex").write_text("\\citep{smith2023}\n", encoding="utf-8")
        bib = tmp_path / "refs.bib"
        bib.write_text("@article{smith2023, author={S}, year={2023}}\n", encoding="utf-8")
        violations = validate_all_tex_citations(paper, bib)
        assert len(violations) == 0

    def test_missing_citation(self, tmp_path: Path):
        paper = tmp_path / "paper"
        paper.mkdir()
        (paper / "test.tex").write_text("\\citep{missing2023}\n", encoding="utf-8")
        bib = tmp_path / "refs.bib"
        bib.write_text("@article{smith2023, author={S}, year={2023}}\n", encoding="utf-8")
        violations = validate_all_tex_citations(paper, bib)
        assert len(violations) == 1
        assert violations[0].missing_key == "missing2023"

    def test_multiple_keys_in_cite(self, tmp_path: Path):
        paper = tmp_path / "paper"
        paper.mkdir()
        (paper / "test.tex").write_text("\\citep{a2023, b2024}\n", encoding="utf-8")
        bib = tmp_path / "refs.bib"
        bib.write_text("@article{a2023, author={A}, year={2023}}\n", encoding="utf-8")
        violations = validate_all_tex_citations(paper, bib)
        assert len(violations) == 1
        assert violations[0].missing_key == "b2024"


class TestValidateAssetHashes:
    def test_valid_asset(self, tmp_path: Path):
        out = tmp_path / "output"
        out.mkdir()
        f = out / "fig1.pdf"
        f.write_bytes(b"fake pdf content")
        h = hashlib.sha256(b"fake pdf content").hexdigest()
        manifest = [{"asset_id": "fig1", "file_path": "fig1.pdf", "content_hash": h}]
        violations = validate_asset_hashes(manifest, out)
        assert len(violations) == 0

    def test_missing_asset(self, tmp_path: Path):
        out = tmp_path / "output"
        out.mkdir()
        manifest = [{"asset_id": "fig1", "file_path": "missing.pdf", "content_hash": "abc"}]
        violations = validate_asset_hashes(manifest, out)
        assert len(violations) == 1

    def test_hash_mismatch(self, tmp_path: Path):
        out = tmp_path / "output"
        out.mkdir()
        (out / "fig1.pdf").write_bytes(b"content")
        manifest = [{"asset_id": "fig1", "file_path": "fig1.pdf", "content_hash": "wrong"}]
        violations = validate_asset_hashes(manifest, out)
        assert len(violations) == 1
        assert "content_hash" in violations[0].field


class TestValidateSectionsComplete:
    def test_all_complete(self):
        state = {"sections": [
            {"section_id": "intro", "status": "complete"},
            {"section_id": "method", "status": "complete"},
        ]}
        assert validate_sections_complete(state) == []

    def test_incomplete_section(self):
        state = {"sections": [
            {"section_id": "intro", "status": "draft"},
        ]}
        violations = validate_sections_complete(state)
        assert len(violations) == 1


class TestValidateGlossaryInTex:
    def test_term_found(self, tmp_path: Path):
        paper = tmp_path / "paper"
        paper.mkdir()
        (paper / "test.tex").write_text("We use machine learning.\n", encoding="utf-8")
        glossary = {"entries": {"ml": {"term": "machine learning"}}}
        violations = validate_glossary_in_tex(glossary, paper)
        assert len(violations) == 0

    def test_term_missing(self, tmp_path: Path):
        paper = tmp_path / "paper"
        paper.mkdir()
        (paper / "test.tex").write_text("Nothing here.\n", encoding="utf-8")
        glossary = {"entries": {"ml": {"term": "machine learning"}}}
        violations = validate_glossary_in_tex(glossary, paper)
        assert len(violations) == 1


class TestValidateEndToEnd:
    def test_empty_run(self, tmp_path: Path):
        paper = tmp_path / "paper"
        paper.mkdir()
        out = tmp_path / "output"
        out.mkdir()
        data = tmp_path / "data"
        data.mkdir()
        violations = validate_end_to_end(paper, out, data)
        assert violations == []
