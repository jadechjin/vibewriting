from __future__ import annotations

import asyncio
import os

import pytest

from vibewriting.literature.runtime_adapter import (
    call_mcp_tool,
    get_mcp_tool_caller,
    set_mcp_tool_caller,
)


class TestRuntimeAdapter:
    def setup_method(self) -> None:
        os.environ["VW_MCP_AUTO_ADAPTER"] = "0"

    def teardown_method(self) -> None:
        set_mcp_tool_caller(None)
        os.environ.pop("VW_MCP_AUTO_ADAPTER", None)

    def test_no_caller_raises(self) -> None:
        set_mcp_tool_caller(None)
        with pytest.raises(NotImplementedError):
            asyncio.run(call_mcp_tool("search_papers", query="test"))

    def test_sync_caller(self) -> None:
        def caller(tool_name: str, **kwargs):  # type: ignore[no-untyped-def]
            return {"tool": tool_name, "kwargs": kwargs}

        set_mcp_tool_caller(caller)
        result = asyncio.run(call_mcp_tool("search_papers", query="abc"))
        assert result["tool"] == "search_papers"
        assert result["kwargs"]["query"] == "abc"

    def test_async_caller(self) -> None:
        async def caller(tool_name: str, **kwargs):  # type: ignore[no-untyped-def]
            return {"tool": tool_name, "kwargs": kwargs}

        set_mcp_tool_caller(caller)
        result = asyncio.run(call_mcp_tool("retrieve_knowledge", query="abc"))
        assert result["tool"] == "retrieve_knowledge"
        assert result["kwargs"]["query"] == "abc"

    def test_getter(self) -> None:
        def caller(tool_name: str, **kwargs):  # type: ignore[no-untyped-def]
            return None

        set_mcp_tool_caller(caller)
        assert get_mcp_tool_caller() is caller

    def test_auto_caller_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def auto_caller(tool_name: str, **kwargs):  # type: ignore[no-untyped-def]
            return {"tool": tool_name, "kwargs": kwargs, "via": "auto"}

        monkeypatch.setenv("VW_MCP_AUTO_ADAPTER", "1")
        monkeypatch.setattr(
            "vibewriting.literature.runtime_adapter.get_auto_mcp_tool_caller",
            lambda: auto_caller,
        )
        set_mcp_tool_caller(None)

        result = asyncio.run(call_mcp_tool("retrieve_knowledge", query="abc"))
        assert result["tool"] == "retrieve_knowledge"
        assert result["kwargs"]["query"] == "abc"
        assert result["via"] == "auto"
