"""Automatic local MCP caller for Codex sessions.

This module provides a best-effort fallback caller when:
1) no in-process caller was injected via ``set_mcp_tool_caller()``, and
2) no ``VW_MCP_TOOL_CALLER`` env override was provided.

Fallback behavior:
- Read server commands from project ``.mcp.json``.
- Spawn stdio MCP servers as subprocesses.
- Speak newline-delimited JSON-RPC (FastMCP stdio protocol).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Keep mapping explicit so unsupported tools fail fast and clearly.
_TOOL_SERVER_MAP: dict[str, str] = {
    "search_papers": "paper-search",
    "decide": "paper-search",
    "get_session": "paper-search",
    "export_results": "paper-search",
    "retrieve_knowledge": "dify-knowledge",
    "list_documents": "dify-knowledge",
}

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}
_PROTOCOL_VERSION = "2025-11-25"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_MCP_CONFIG_PATH = _REPO_ROOT / ".mcp.json"


def _env_bool(name: str) -> bool | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    value = raw.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    return None


def _should_enable_auto_caller() -> bool:
    """Enable in Codex by default; allow explicit env override."""
    override = _env_bool("VW_MCP_AUTO_ADAPTER")
    if override is not None:
        return override
    return bool(os.getenv("CODEX_THREAD_ID"))


def _resolve_config_path() -> Path:
    configured = os.getenv("VW_MCP_CONFIG_PATH", "").strip()
    if not configured:
        return _DEFAULT_MCP_CONFIG_PATH
    path = Path(configured)
    if path.is_absolute():
        return path
    return (_REPO_ROOT / path).resolve()


@dataclass(frozen=True)
class _ServerConfig:
    command: str
    args: tuple[str, ...]
    cwd: str | None
    env: dict[str, str] | None


class _JsonRpcStdioClient:
    """Minimal newline-JSON stdio client compatible with FastMCP."""

    def __init__(self, name: str, config: _ServerConfig) -> None:
        self._name = name
        self._config = config
        self._process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._stderr_task: asyncio.Task[None] | None = None
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._next_id = 1
        self._initialized = False
        self._write_lock = asyncio.Lock()
        self._lifecycle_lock = asyncio.Lock()

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        await self._ensure_started()
        result = await self._request(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
            timeout_s=120.0,
        )
        return _decode_call_tool_result(result)

    async def aclose(self) -> None:
        process = self._process
        if process is None:
            return

        self._process = None
        self._initialized = False

        try:
            if process.stdin is not None:
                process.stdin.close()
                await process.stdin.wait_closed()
        except Exception:
            pass

        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                process.kill()
                try:
                    await process.wait()
                except Exception:
                    pass

        for task in (self._reader_task, self._stderr_task):
            if task is not None and not task.done():
                task.cancel()

        self._reader_task = None
        self._stderr_task = None
        self._fail_pending(
            RuntimeError(f"MCP server '{self._name}' client closed")
        )

    async def _ensure_started(self) -> None:
        async with self._lifecycle_lock:
            if (
                self._process is not None
                and self._process.returncode is None
                and self._initialized
            ):
                return
            await self._start()

    async def _start(self) -> None:
        env = os.environ.copy()
        if self._config.env:
            env.update(self._config.env)

        self._process = await asyncio.create_subprocess_exec(
            self._config.command,
            *self._config.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._config.cwd or None,
            env=env,
        )
        self._reader_task = asyncio.create_task(self._stdout_reader())
        self._stderr_task = asyncio.create_task(self._stderr_reader())

        await self._request(
            "initialize",
            {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "vibewriting-local-mcp-adapter",
                    "version": "0.1.0",
                },
            },
            timeout_s=30.0,
        )
        await self._notify("notifications/initialized", {})
        self._initialized = True

    async def _stdout_reader(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return

        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                raw = line.decode("utf-8", errors="replace").strip()
                if not raw:
                    continue
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    logger.debug("[%s] non-json stdout: %s", self._name, raw)
                    continue
                self._dispatch_response(message)
        except Exception as exc:  # pragma: no cover - defensive transport guard
            self._fail_pending(exc)
            return

        rc = process.returncode
        self._fail_pending(
            RuntimeError(f"MCP server '{self._name}' exited unexpectedly (code={rc})")
        )

    async def _stderr_reader(self) -> None:
        process = self._process
        if process is None or process.stderr is None:
            return
        while True:
            line = await process.stderr.readline()
            if not line:
                return
            msg = line.decode("utf-8", errors="replace").rstrip()
            if msg:
                logger.debug("[%s] %s", self._name, msg)

    def _dispatch_response(self, message: dict[str, Any]) -> None:
        msg_id = message.get("id")
        if not isinstance(msg_id, int):
            return

        future = self._pending.pop(msg_id, None)
        if future is None or future.done():
            return

        if "error" in message:
            future.set_exception(RuntimeError(_format_error(message["error"])))
            return
        future.set_result(message.get("result"))

    def _fail_pending(self, exc: Exception) -> None:
        for future in self._pending.values():
            if not future.done():
                future.set_exception(exc)
        self._pending.clear()

    async def _request(
        self,
        method: str,
        params: dict[str, Any] | None,
        timeout_s: float,
    ) -> Any:
        if self._process is None:
            raise RuntimeError(f"MCP server '{self._name}' is not running")
        if self._process.returncode is not None:
            raise RuntimeError(
                f"MCP server '{self._name}' already exited (code={self._process.returncode})"
            )
        if self._process.stdin is None:
            raise RuntimeError(f"MCP server '{self._name}' has no stdin stream")

        request_id = self._next_id
        self._next_id += 1
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self._pending[request_id] = future

        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        raw = json.dumps(payload, ensure_ascii=False)
        async with self._write_lock:
            self._process.stdin.write((raw + "\n").encode("utf-8"))
            await self._process.stdin.drain()

        try:
            return await asyncio.wait_for(future, timeout=timeout_s)
        finally:
            self._pending.pop(request_id, None)

    async def _notify(self, method: str, params: dict[str, Any] | None) -> None:
        if self._process is None or self._process.stdin is None:
            return
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        raw = json.dumps(payload, ensure_ascii=False)
        async with self._write_lock:
            self._process.stdin.write((raw + "\n").encode("utf-8"))
            await self._process.stdin.drain()


class _LocalMCPCaller:
    def __init__(self) -> None:
        self._clients: dict[str, _JsonRpcStdioClient] = {}
        self._servers: dict[str, _ServerConfig] | None = None
        self._config_lock = asyncio.Lock()

    async def __call__(self, tool_name: str, **kwargs: Any) -> Any:
        server_name = _TOOL_SERVER_MAP.get(tool_name)
        if server_name is None:
            raise NotImplementedError(
                f"Tool '{tool_name}' is not mapped to a local MCP server"
            )

        servers = await self._load_servers()
        server_cfg = servers.get(server_name)
        if server_cfg is None:
            raise NotImplementedError(
                f"Local MCP server '{server_name}' is not configured in .mcp.json"
            )

        client = self._clients.get(server_name)
        if client is None:
            client = _JsonRpcStdioClient(server_name, server_cfg)
            self._clients[server_name] = client
        return await client.call_tool(tool_name, kwargs)

    async def aclose(self) -> None:
        clients = list(self._clients.values())
        self._clients.clear()
        for client in clients:
            await client.aclose()

    async def _load_servers(self) -> dict[str, _ServerConfig]:
        async with self._config_lock:
            if self._servers is not None:
                return self._servers

            cfg_path = _resolve_config_path()
            if not cfg_path.exists():
                raise NotImplementedError(
                    f"Local MCP config not found: {cfg_path}"
                )

            try:
                raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Failed to parse MCP config '{cfg_path}': {exc}"
                ) from exc

            mcp_servers = raw.get("mcpServers")
            if not isinstance(mcp_servers, dict):
                raise RuntimeError(
                    f"Invalid MCP config '{cfg_path}': missing 'mcpServers' object"
                )

            parsed: dict[str, _ServerConfig] = {}
            for name, value in mcp_servers.items():
                if not isinstance(value, dict):
                    continue
                command = str(value.get("command", "")).strip()
                if not command:
                    continue
                raw_args = value.get("args", [])
                args = tuple(str(a) for a in raw_args) if isinstance(raw_args, list) else ()
                cwd = value.get("cwd")
                cwd_str = str(cwd) if isinstance(cwd, (str, Path)) else None
                env_raw = value.get("env")
                env: dict[str, str] | None
                if isinstance(env_raw, dict):
                    env = {str(k): str(v) for k, v in env_raw.items() if v is not None}
                else:
                    env = None
                parsed[name] = _ServerConfig(
                    command=command,
                    args=args,
                    cwd=cwd_str,
                    env=env,
                )

            self._servers = parsed
            return parsed


def _format_error(error: Any) -> str:
    if isinstance(error, dict):
        code = error.get("code")
        message = error.get("message")
        if code is None and message is None:
            return json.dumps(error, ensure_ascii=False)
        return f"[{code}] {message}"
    return str(error)


def _decode_call_tool_result(result: Any) -> Any:
    if not isinstance(result, dict):
        return result

    if result.get("isError") is True:
        raise RuntimeError(_extract_tool_error_message(result))

    structured = result.get("structuredContent")
    if structured is not None:
        # FastMCP commonly wraps return payload as {"result": <tool-return>}.
        if isinstance(structured, dict) and set(structured) == {"result"}:
            return _maybe_json_or_passthrough(structured["result"])
        return structured

    content = result.get("content")
    parsed_content = _parse_content_text(content)
    if parsed_content is not None:
        return parsed_content

    return result


def _extract_tool_error_message(result: dict[str, Any]) -> str:
    content = result.get("content")
    parsed = _parse_content_text(content)
    if isinstance(parsed, str) and parsed.strip():
        return parsed
    if isinstance(parsed, dict) and parsed:
        return json.dumps(parsed, ensure_ascii=False)
    return "MCP tool returned an error"


def _parse_content_text(content: Any) -> Any | None:
    if not isinstance(content, list):
        return None

    values: list[Any] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        values.append(_maybe_json(text))

    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return values


def _maybe_json(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        return ""
    if not (stripped.startswith("{") or stripped.startswith("[")):
        return stripped
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return stripped


def _maybe_json_or_passthrough(value: Any) -> Any:
    if isinstance(value, str):
        return _maybe_json(value)
    return value


_AUTO_CALLER: _LocalMCPCaller | None = None


def get_auto_mcp_tool_caller() -> _LocalMCPCaller | None:
    """Return automatic local caller when enabled for current runtime."""
    global _AUTO_CALLER
    if not _should_enable_auto_caller():
        return None
    if _AUTO_CALLER is None:
        _AUTO_CALLER = _LocalMCPCaller()
    return _AUTO_CALLER


async def shutdown_auto_mcp_tool_caller() -> None:
    """Close auto fallback MCP subprocesses in the current event loop."""
    global _AUTO_CALLER
    if _AUTO_CALLER is None:
        return
    await _AUTO_CALLER.aclose()
