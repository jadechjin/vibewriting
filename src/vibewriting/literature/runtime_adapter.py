"""Runtime adapter for MCP tool calls across Claude and Codex."""

from __future__ import annotations

import importlib
import inspect
import os
from typing import Any, Callable

from vibewriting.literature.local_mcp_caller import get_auto_mcp_tool_caller

MCPToolCaller = Callable[..., Any]

_MCP_TOOL_CALLER: MCPToolCaller | None = None


def set_mcp_tool_caller(caller: MCPToolCaller | None) -> None:
    """Register a runtime MCP tool caller.

    The caller should accept ``tool_name`` plus keyword args:
    ``caller(tool_name, **kwargs)`` and may return awaitable or plain result.
    """
    global _MCP_TOOL_CALLER
    _MCP_TOOL_CALLER = caller


def get_mcp_tool_caller() -> MCPToolCaller | None:
    """Get currently configured MCP tool caller."""
    return _MCP_TOOL_CALLER


def _load_caller_from_env() -> MCPToolCaller | None:
    """Load caller from env var ``VW_MCP_TOOL_CALLER=module:function``."""
    spec = os.getenv("VW_MCP_TOOL_CALLER", "").strip()
    if not spec:
        return None
    if ":" not in spec:
        raise ValueError(
            "VW_MCP_TOOL_CALLER must use 'module:function' format"
        )
    module_name, func_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    caller = getattr(module, func_name)
    if not callable(caller):
        raise TypeError(
            f"Configured MCP caller '{spec}' is not callable"
        )
    return caller


async def call_mcp_tool(tool_name: str, **kwargs: Any) -> Any:
    """Call an MCP tool through the configured runtime adapter."""
    caller = (
        _MCP_TOOL_CALLER
        or _load_caller_from_env()
        or get_auto_mcp_tool_caller()
    )
    if caller is None:
        raise NotImplementedError(
            f"MCP tool '{tool_name}' has no runtime adapter. "
            "Configure one via set_mcp_tool_caller() or "
            "VW_MCP_TOOL_CALLER=module:function "
            "(or enable auto fallback with VW_MCP_AUTO_ADAPTER=1)."
        )

    result = caller(tool_name, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result
