# Proposal: Fix Dify MCP Environment Variable Resolution

## Context

`scripts/dify-kb-mcp/server.py` 是 Dify 知识库的 FastMCP 桥接服务器。
它通过 `.mcp.json` 的 `env` 字段接收 `DIFY_API_BASE_URL`、`DIFY_API_KEY`、`DIFY_DATASET_ID`，
并以 `python-dotenv` + `VW_DIFY_*` 作为回退。

## Problem

Claude  Code 的 MCP 环境变量插值 `${VW_DIFY_API_BASE_URL}` 在进程环境中不存在该变量时，
行为不可靠（已知 Bug：anthropics/claude-code#9427, #1254, #14032, #28090）：
- 可能将字面量 `${VW_DIFY_API_BASE_URL}` 传入子进程（truthy 字符串）
- 导致 Python `or` 短路，不触发 `VW_DIFY_*` 回退
- URL 组装为 `${VW_DIFY_API_BASE_URL}/datasets/.../retrieve`
- httpx 抛出 "Request URL is missing an 'http://' or 'https://' protocol"

## Root Cause

```python
# 当前代码（有 Bug）：
DIFY_API_BASE_URL = (
    os.environ.get("DIFY_API_BASE_URL")   # 返回字面量 "${VW_DIFY_API_BASE_URL}"（truthy！）
    or os.environ.get("VW_DIFY_API_BASE_URL", "")  # 被短路，永远不执行
).rstrip("/")
```

`_check_credentials()` 也无法检测到问题，因为字面量字符串是 truthy。

## Solution: Method A

在 `server.py` 中添加 `_resolve_env()` 辅助函数，过滤所有未解析的 `${...}` 插值字面量。
同时在 `_check_credentials()` 中增加 URL 协议前缀检查，提供更好的错误信息。

## Constraints

- C1: 不能修改 Claude  Code 的 MCP env 插值行为（上游 Bug）
- C2: `server.py` 保持 PEP 723 格式（内联依赖，无 pyproject.toml 依赖）
- C3: `override=False` 在 `load_dotenv` 中保留（防止覆盖已正确传入的值）
- C4: 向后兼容：已正确配置系统环境变量的用户不受影响
- C5: 过滤规则：以 `${` 开头且包含 `}` 的字符串视为未解析插值

## Requirements

### R1: `_resolve_env()` 辅助函数

**场景**：给定一个可能是未解析插值字面量的环境变量值，返回 `None`（如果是字面量或空）。

```
Given DIFY_API_BASE_URL = "${VW_DIFY_API_BASE_URL}"
When _resolve_env("DIFY_API_BASE_URL") is called
Then returns None (triggers fallback)

Given DIFY_API_BASE_URL = "https://api.dify.ai/v1"
When _resolve_env("DIFY_API_BASE_URL") is called
Then returns "https://api.dify.ai/v1"

Given DIFY_API_BASE_URL = "" (or not set)
When _resolve_env("DIFY_API_BASE_URL") is called
Then returns None (triggers fallback)
```

### R2: 回退链使用 `_resolve_env()`

**场景**：三个 Dify 凭据均通过 `_resolve_env()` 过滤后再回退到 `VW_DIFY_*`。

### R3: URL 协议前缀检查（`_check_credentials()`）

**场景**：`DIFY_API_BASE_URL` 有值但不是 `http://` 或 `https://` 开头时，返回明确错误信息。

```
Given DIFY_API_BASE_URL = "api.dify.ai/v1" (missing protocol)
When _check_credentials() is called
Then returns error message containing "must start with http:// or https://"
```

## Success Criteria

- SC1: `uv run python -c "import scripts/dify-kb-mcp/server.py"` 无语法错误
- SC2: 当 `.mcp.json` 插值失败时，`retrieve_knowledge` 返回 "Dify credentials not configured" 错误（而非 httpx 协议错误）
- SC3: 当 `VW_DIFY_*` 正确设置时，`retrieve_knowledge` 正常工作（不受影响）
- SC4: `uv run pytest tests/` 全部通过（835 tests）
