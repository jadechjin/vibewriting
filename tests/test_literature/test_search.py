"""Tests for search module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vibewriting.literature.models import RawLiteratureRecord


class TestSearchViaPaperSearch:
    """Tests for paper-search MCP integration.

    Note: These tests mock MCP tool calls since paper-search
    is an external MCP server.
    """

    @pytest.mark.asyncio
    async def test_basic_search_returns_records(self, mock_paper_search_results: dict) -> None:
        from vibewriting.literature.search import search_via_paper_search

        with patch("vibewriting.literature.search._call_mcp_tool", new_callable=AsyncMock) as mock_mcp:
            # search_papers returns session_id
            mock_mcp.side_effect = [
                {"session_id": "test-session-001", "status": "completed"},
                mock_paper_search_results,
            ]
            records, bibtex = await search_via_paper_search("transformer attention", max_results=10)
            assert len(records) > 0
            assert all(isinstance(r, RawLiteratureRecord) for r in records)
            assert bibtex  # Non-empty bibtex string

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        from vibewriting.literature.search import search_via_paper_search

        with patch("vibewriting.literature.search._call_mcp_tool", new_callable=AsyncMock) as mock_mcp:
            mock_mcp.side_effect = [
                {"session_id": "test-session-002", "status": "completed"},
                {"results": [], "bibtex": ""},
            ]
            records, bibtex = await search_via_paper_search("nonexistent topic", max_results=10)
            assert records == []


class TestSearchViaDify:
    @pytest.mark.asyncio
    async def test_basic_search(self, mock_dify_results: list[dict]) -> None:
        from vibewriting.literature.search import search_via_dify

        with patch("vibewriting.literature.search._call_mcp_tool", new_callable=AsyncMock) as mock_mcp:
            mock_mcp.return_value = mock_dify_results
            records = await search_via_dify("transformer mechanism")
            assert isinstance(records, list)

    @pytest.mark.asyncio
    async def test_dify_graceful_degradation(self) -> None:
        from vibewriting.literature.search import search_via_dify

        with patch("vibewriting.literature.search._call_mcp_tool", new_callable=AsyncMock) as mock_mcp:
            mock_mcp.side_effect = Exception("Dify unavailable")
            records = await search_via_dify("test query")
            assert records == []  # Should not raise, returns empty


class TestSearchLiterature:
    @pytest.mark.asyncio
    async def test_orchestrator_combines_sources(self, mock_paper_search_results: dict) -> None:
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
                "@article{a2020, title={Paper A}, year={2020}}\n",
            )
            mock_dify.return_value = []

            result = await search_literature("test query", max_results=10)
            assert hasattr(result, "records")
            assert hasattr(result, "dedup_report")

    @pytest.mark.asyncio
    async def test_bounds_max_results(self, mock_paper_search_results: dict) -> None:
        from vibewriting.literature.search import search_literature

        with patch("vibewriting.literature.search.search_via_paper_search", new_callable=AsyncMock) as mock_ps, \
             patch("vibewriting.literature.search.search_via_dify", new_callable=AsyncMock) as mock_dify:
            mock_ps.return_value = ([], "")
            mock_dify.return_value = []

            result = await search_literature("test", max_results=5)
            assert len(result.records) <= 5

    @pytest.mark.asyncio
    async def test_orchestrator_prioritizes_dify(self) -> None:
        from vibewriting.literature.search import search_literature

        with patch("vibewriting.literature.search.search_via_paper_search", new_callable=AsyncMock) as mock_ps, \
             patch("vibewriting.literature.search.search_via_dify", new_callable=AsyncMock) as mock_dify:
            mock_ps.return_value = (
                [
                    RawLiteratureRecord(
                        title="Paper B", authors=["B"], year=2021,
                        doi="10.1/b", source="paper-search",
                    ),
                ],
                "@article{b2021}\n",
            )
            mock_dify.return_value = [
                RawLiteratureRecord(
                    title="Paper A", authors=["A"], year=2020,
                    doi="10.1/a", source="dify-kb",
                ),
            ]

            result = await search_literature("test query", max_results=10)
            # dify-kb records should come before paper-search records
            assert len(result.records) >= 1
            dify_indices = [i for i, r in enumerate(result.records) if r.source == "dify-kb"]
            ps_indices = [i for i, r in enumerate(result.records) if r.source == "paper-search"]
            if dify_indices and ps_indices:
                assert max(dify_indices) < min(ps_indices)

    @pytest.mark.asyncio
    async def test_orchestrator_handles_dify_failure_gracefully(self) -> None:
        from vibewriting.literature.search import search_literature

        with patch("vibewriting.literature.search.search_via_paper_search", new_callable=AsyncMock) as mock_ps, \
             patch("vibewriting.literature.search.search_via_dify", new_callable=AsyncMock) as mock_dify:
            mock_ps.return_value = (
                [
                    RawLiteratureRecord(
                        title="Paper C", authors=["C"], year=2022,
                        doi="10.1/c", source="paper-search",
                    ),
                ],
                "@article{c2022}\n",
            )
            mock_dify.side_effect = Exception("Dify unavailable")

            result = await search_literature("test query", max_results=10)
            # Should still return paper-search results despite Dify failure
            assert len(result.records) >= 1
            assert any("Dify error" in e for e in result.errors)
