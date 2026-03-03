"""Tests for dify_inventory module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from vibewriting.literature.dify_inventory import (
    DifyDocEntry,
    DifyInventory,
    _parse_dify_doc,
    _strip_extension,
    dedup_against_inventory,
    load_dify_inventory,
    sync_dify_inventory,
)
from vibewriting.literature.models import RawLiteratureRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestStripExtension:
    def test_pdf(self) -> None:
        assert _strip_extension("Paper Title.pdf") == "Paper Title"

    def test_docx(self) -> None:
        assert _strip_extension("Report.docx") == "Report"

    def test_no_extension(self) -> None:
        assert _strip_extension("Plain Name") == "Plain Name"

    def test_unknown_extension(self) -> None:
        assert _strip_extension("data.csv") == "data.csv"

    def test_tex(self) -> None:
        assert _strip_extension("main.tex") == "main"


class TestParseDifyDoc:
    def test_basic(self) -> None:
        doc = {"id": "abc123", "name": "Attention Is All You Need.pdf", "created_at": 1234567890}
        entry = _parse_dify_doc(doc)
        assert entry.dify_doc_id == "abc123"
        assert entry.name == "Attention Is All You Need.pdf"
        assert "attention" in entry.normalized_title
        assert "is" not in entry.normalized_title.split()  # "is" is a stop word
        assert "need" in entry.normalized_title

    def test_empty_name(self) -> None:
        doc = {"id": "x", "name": ""}
        entry = _parse_dify_doc(doc)
        assert entry.normalized_title == ""

    def test_missing_fields(self) -> None:
        doc = {}
        entry = _parse_dify_doc(doc)
        assert entry.dify_doc_id == ""
        assert entry.name == ""


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


class TestSyncDifyInventory:
    @pytest.mark.asyncio
    async def test_basic_sync(self, tmp_path: Path) -> None:
        inv_path = tmp_path / "inventory.json"

        mock_response = {
            "error": False,
            "data": [
                {"id": "doc1", "name": "Attention Is All You Need.pdf", "created_at": "2026-01-01"},
                {"id": "doc2", "name": "BERT Pre-training.pdf", "created_at": "2026-01-02"},
            ],
            "total": 2,
            "page": 1,
            "limit": 100,
        }

        with patch(
            "vibewriting.literature.dify_inventory._call_mcp_tool",
            new_callable=AsyncMock,
        ) as mock_mcp:
            mock_mcp.return_value = mock_response
            inventory = await sync_dify_inventory(inv_path)

        assert inventory.total == 2
        assert len(inventory.documents) == 2
        assert inventory.documents[0].dify_doc_id == "doc1"
        assert inv_path.exists()

    @pytest.mark.asyncio
    async def test_pagination(self, tmp_path: Path) -> None:
        inv_path = tmp_path / "inventory.json"

        page1 = {
            "error": False,
            "data": [{"id": f"doc{i}", "name": f"Paper {i}.pdf", "created_at": ""} for i in range(3)],
            "total": 5,
            "page": 1,
            "limit": 3,
        }
        page2 = {
            "error": False,
            "data": [{"id": f"doc{i}", "name": f"Paper {i}.pdf", "created_at": ""} for i in range(3, 5)],
            "total": 5,
            "page": 2,
            "limit": 3,
        }

        with patch(
            "vibewriting.literature.dify_inventory._call_mcp_tool",
            new_callable=AsyncMock,
        ) as mock_mcp:
            mock_mcp.side_effect = [page1, page2]
            inventory = await sync_dify_inventory(inv_path, page_limit=3)

        assert inventory.total == 5
        assert len(inventory.documents) == 5

    @pytest.mark.asyncio
    async def test_api_error_returns_empty(self, tmp_path: Path) -> None:
        inv_path = tmp_path / "inventory.json"

        with patch(
            "vibewriting.literature.dify_inventory._call_mcp_tool",
            new_callable=AsyncMock,
        ) as mock_mcp:
            mock_mcp.return_value = {"error": True, "message": "Credentials missing"}
            inventory = await sync_dify_inventory(inv_path)

        assert inventory.total == 0
        assert len(inventory.documents) == 0

    @pytest.mark.asyncio
    async def test_mcp_not_available(self, tmp_path: Path) -> None:
        inv_path = tmp_path / "inventory.json"

        with patch(
            "vibewriting.literature.dify_inventory._call_mcp_tool",
            new_callable=AsyncMock,
        ) as mock_mcp:
            mock_mcp.side_effect = NotImplementedError("MCP not available")
            inventory = await sync_dify_inventory(inv_path)

        assert inventory.total == 0


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------


class TestLoadDifyInventory:
    def test_load_valid(self, tmp_path: Path) -> None:
        inv_path = tmp_path / "inventory.json"
        inventory = DifyInventory(
            total=1,
            documents=[
                DifyDocEntry(
                    dify_doc_id="doc1",
                    name="Test.pdf",
                    normalized_title="test",
                ),
            ],
        )
        inv_path.write_text(inventory.model_dump_json(indent=2), encoding="utf-8")

        loaded = load_dify_inventory(inv_path)
        assert loaded is not None
        assert loaded.total == 1
        assert loaded.documents[0].dify_doc_id == "doc1"

    def test_file_not_exists(self, tmp_path: Path) -> None:
        inv_path = tmp_path / "nonexistent.json"
        assert load_dify_inventory(inv_path) is None

    def test_corrupt_file(self, tmp_path: Path) -> None:
        inv_path = tmp_path / "corrupt.json"
        inv_path.write_text("not valid json{{{", encoding="utf-8")
        assert load_dify_inventory(inv_path) is None


# ---------------------------------------------------------------------------
# Dedup against inventory
# ---------------------------------------------------------------------------


class TestDedupAgainstInventory:
    def _make_inventory(self, docs: list[tuple[str, str]]) -> DifyInventory:
        """Helper: create inventory from (doc_id, name) pairs."""
        from vibewriting.literature.dedup import normalize_title

        entries = [
            DifyDocEntry(
                dify_doc_id=did,
                name=name,
                normalized_title=normalize_title(_strip_extension(name)),
            )
            for did, name in docs
        ]
        return DifyInventory(total=len(entries), documents=entries)

    def test_title_match_filters(self) -> None:
        inventory = self._make_inventory([
            ("d1", "Attention Is All You Need.pdf"),
        ])
        records = [
            RawLiteratureRecord(
                title="Attention Is All You Need",
                authors=["Vaswani"], year=2017, doi="10.1/a",
            ),
            RawLiteratureRecord(
                title="BERT Pre-training",
                authors=["Devlin"], year=2019, doi="10.1/b",
            ),
        ]
        kept, filtered = dedup_against_inventory(records, inventory, threshold=0.9)
        assert len(kept) == 1
        assert kept[0].title == "BERT Pre-training"
        assert "Attention Is All You Need" in filtered

    def test_doi_match_filters(self) -> None:
        inventory = self._make_inventory([
            ("d1", "10.1234/paper-a - Some Title.pdf"),
        ])
        records = [
            RawLiteratureRecord(
                title="Paper A", authors=["A"], year=2020,
                doi="10.1234/paper-a",
            ),
        ]
        kept, filtered = dedup_against_inventory(records, inventory, threshold=0.9)
        assert len(kept) == 0
        assert len(filtered) == 1

    def test_no_match_keeps_all(self) -> None:
        inventory = self._make_inventory([
            ("d1", "Unrelated Document.pdf"),
        ])
        records = [
            RawLiteratureRecord(
                title="Transformer Architecture",
                authors=["X"], year=2024,
            ),
        ]
        kept, filtered = dedup_against_inventory(records, inventory, threshold=0.9)
        assert len(kept) == 1
        assert len(filtered) == 0

    def test_empty_inventory(self) -> None:
        inventory = DifyInventory(total=0, documents=[])
        records = [
            RawLiteratureRecord(title="Paper", authors=["A"], year=2020),
        ]
        kept, filtered = dedup_against_inventory(records, inventory)
        assert len(kept) == 1
        assert len(filtered) == 0

    def test_empty_records(self) -> None:
        inventory = self._make_inventory([("d1", "Paper.pdf")])
        kept, filtered = dedup_against_inventory([], inventory)
        assert len(kept) == 0
        assert len(filtered) == 0

    def test_threshold_sensitivity(self) -> None:
        inventory = self._make_inventory([
            ("d1", "Machine Learning Basics.pdf"),
        ])
        records = [
            RawLiteratureRecord(
                title="Machine Learning Fundamentals",
                authors=["A"], year=2020,
            ),
        ]
        # High threshold: should keep (titles differ enough)
        kept_strict, _ = dedup_against_inventory(records, inventory, threshold=0.99)
        # Low threshold: should filter
        kept_loose, _ = dedup_against_inventory(records, inventory, threshold=0.3)
        assert len(kept_strict) >= len(kept_loose)


# ---------------------------------------------------------------------------
# Integration: search_literature with inventory
# ---------------------------------------------------------------------------


class TestSearchLiteratureWithInventory:
    @pytest.mark.asyncio
    async def test_inventory_filters_duplicates(self, tmp_path: Path) -> None:
        from vibewriting.literature.search import search_literature

        inv_path = tmp_path / "inventory.json"

        # Pre-create inventory file
        inventory = DifyInventory(
            total=1,
            documents=[
                DifyDocEntry(
                    dify_doc_id="d1",
                    name="Attention Is All You Need.pdf",
                    normalized_title="attention all you need",
                ),
            ],
        )
        inv_path.write_text(inventory.model_dump_json(indent=2), encoding="utf-8")

        with patch("vibewriting.literature.search.search_via_paper_search", new_callable=AsyncMock) as mock_ps, \
             patch("vibewriting.literature.search.search_via_dify", new_callable=AsyncMock) as mock_dify, \
             patch("vibewriting.literature.search.sync_dify_inventory", new_callable=AsyncMock) as mock_sync:
            mock_ps.return_value = (
                [
                    RawLiteratureRecord(
                        title="Attention Is All You Need",
                        authors=["Vaswani"], year=2017, doi="10.1/a",
                        source="paper-search",
                    ),
                    RawLiteratureRecord(
                        title="BERT Pre-training",
                        authors=["Devlin"], year=2019, doi="10.1/b",
                        source="paper-search",
                    ),
                ],
                "@article{a2017}\n",
            )
            mock_dify.return_value = []
            mock_sync.return_value = inventory

            result = await search_literature(
                "test query", max_results=10, inventory_path=inv_path,
            )

            assert len(result.records) == 1
            assert result.records[0].title == "BERT Pre-training"
            assert result.dedup_report is not None
            assert result.dedup_report.inventory_filtered_count == 1

    @pytest.mark.asyncio
    async def test_no_inventory_path_skips_inventory_dedup(self) -> None:
        from vibewriting.literature.search import search_literature

        with patch("vibewriting.literature.search.search_via_paper_search", new_callable=AsyncMock) as mock_ps, \
             patch("vibewriting.literature.search.search_via_dify", new_callable=AsyncMock) as mock_dify:
            mock_ps.return_value = (
                [
                    RawLiteratureRecord(
                        title="Paper A", authors=["A"], year=2020,
                        doi="10.1/a", source="paper-search",
                    ),
                ],
                "",
            )
            mock_dify.return_value = []

            result = await search_literature("test", max_results=10)
            assert len(result.records) == 1
            assert result.dedup_report is not None
            assert result.dedup_report.inventory_filtered_count == 0
