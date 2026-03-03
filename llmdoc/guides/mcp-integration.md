# MCP 集成指南

## 概览

vibewriting 通过两个 MCP 服务器获取外部知识：

```
Claude Code
  |
  |-- MCP stdio --> paper-search (文献检索)
  |-- MCP stdio --> dify-knowledge (知识库检索)
```

配置文件：`.mcp.json`（项目级，已提交 Git）

## paper-search MCP

### 基本信息

- **位置**: `C:\Users\17162\Desktop\Terms\workflow`（独立项目）
- **传输**: stdio
- **启动**: `uv run paper-search-mcp`（在 paper-search 项目目录下）

### 工具清单

| 工具 | 参数 | 用途 |
|------|------|------|
| `search_papers(query)` | query: 搜索词 | 启动文献检索会话 |
| `decide(session_id, action)` | session_id, action | 检查点决策（继续/停止/导出） |
| `get_session(session_id)` | session_id | 查询会话状态和进度 |
| `export_results(session_id, format)` | session_id, format: json/bibtex/markdown | 导出检索结果 |

### 典型工作流

```
1. search_papers("deep learning optimization")
   -> 返回 session_id + 初始结果

2. decide(session_id, "continue")  或  decide(session_id, "stop")
   -> 控制检索深度

3. get_session(session_id)
   -> 查看当前进度

4. export_results(session_id, "bibtex")
   -> 导出为 BibTeX 格式，追加到 paper/bib/references.bib
```

### 环境变量

```bash
# .env 中配置
SERPAPI_API_KEY=        # SerpAPI 密钥（文献搜索引擎）
LLM_PROVIDER=           # LLM 提供商（用于论文评分）
LLM_MODEL=              # LLM 模型名
LLM_BASE_URL=           # LLM API 地址
OPENAI_API_KEY=         # OpenAI API 密钥
```

## dify-knowledge MCP

### 基本信息

- **位置**: `scripts/dify-kb-mcp/server.py`（项目内）
- **传输**: stdio
- **启动**: `uv run scripts/dify-kb-mcp/server.py`（PEP 723 内联依赖）
- **依赖**: `mcp[cli]>=1.0`, `httpx>=0.27`, `python-dotenv>=1.0`

### 工具清单

| 工具 | 参数 | 用途 |
|------|------|------|
| `retrieve_knowledge(query, top_k, search_method, score_threshold)` | query: 搜索词, top_k: 数量(默认5), search_method: 搜索方式, score_threshold: 阈值(默认0.5) | 语义检索知识库 |
| `list_documents(page, limit, keyword)` | page: 页码, limit: 每页数(默认20), keyword: 过滤词 | 列出数据集文档 |

### search_method 可选值

- `hybrid_search` -- 混合搜索（默认，推荐）
- `keyword_search` -- 关键词搜索
- `semantic_search` -- 语义搜索

### 环境变量

```bash
# .env 中配置（VW_ 前缀命名空间）
VW_DIFY_API_BASE_URL=https://api.dify.ai/v1   # Dify API 地址（含 /v1 路径）
VW_DIFY_API_KEY=                                # Dify API 密钥
VW_DIFY_DATASET_ID=                             # 数据集 ID
DIFY_MAX_RETRIES=3                              # 最大重试次数（可选，无 VW_ 前缀）
DIFY_TIMEOUT=30                                 # 请求超时秒数（可选，无 VW_ 前缀）
```

### 环境变量加载机制

server.py 启动时自动执行三步加载：

1. **python-dotenv 加载**: 通过 `load_dotenv(project_root/.env, override=False)` 从项目根 `.env` 文件加载环境变量。`override=False` 表示不覆盖已通过 `.mcp.json` env 传入的变量。
2. **`_resolve_env()` 过滤**: 所有环境变量读取均通过 `_resolve_env(key)` 辅助函数，该函数会过滤未被解析的 `${...}` 字面量字符串（返回 `None`），使 `or` 回退链能正确工作。
3. **回退链读取**: 每个配置项按优先级读取：
   - `DIFY_*`（`.mcp.json` env 字段传入，如 `DIFY_API_BASE_URL`）
   - `VW_DIFY_*`（`.env` 直接读取，如 `VW_DIFY_API_BASE_URL`）

这解决了 Claude Code 启动 MCP 服务器时 `.mcp.json` 中 `${VW_DIFY_*}` 插值可能未被解析的问题。当插值失败时 Claude Code 会将 `${VW_DIFY_API_BASE_URL}` 这样的字面量字符串传入子进程（已知 Bug：#9427, #1254, #14032, #28090），字面量是 truthy 值会导致 `or` 短路使回退链失效；`_resolve_env()` 通过正则过滤 `${...}` 格式字符串截断该问题。

### URL 路径拼接规则

`DIFY_API_BASE_URL`（如 `https://api.dify.ai/v1`）末尾斜杠会被自动清理（`.rstrip("/")`）。API 请求路径不再包含 `/v1` 前缀，直接使用 `/datasets/{id}/retrieve` 和 `/datasets/{id}/documents`，避免 URL 变成 `https://api.dify.ai/v1/v1/datasets/...` 的重复路径问题。

### 优雅降级行为

| 场景 | 行为 |
|------|------|
| 凭据缺失 | 服务器正常启动，工具调用返回 `{"error": true, "message": "..."}` |
| 网络连接失败 | 按 MAX_RETRIES 重试，最终返回错误响应，不崩溃 |
| 4xx 客户端错误 | 不重试，立即返回错误（如 401/403 认证失败） |
| 5xx 服务端错误 | 按 MAX_RETRIES 重试 |
| 无效 search_method | 返回错误，列出有效选项 |

## .mcp.json 配置结构

```json
{
  "mcpServers": {
    "paper-search": {
      "command": "uv",
      "args": ["run", "paper-search-mcp"],
      "cwd": "C:/Users/17162/Desktop/Terms/workflow",
      "env": { "SERPAPI_API_KEY": "${SERPAPI_API_KEY}", ... }
    },
    "dify-knowledge": {
      "command": "uv",
      "args": ["run", "scripts/dify-kb-mcp/server.py"],
      "cwd": "F:/vibewriting",
      "env": { "DIFY_API_BASE_URL": "${DIFY_API_BASE_URL}", ... }
    }
  }
}
```

关键设计点：
- 环境变量使用 `${VAR}` 引用，Claude Code 尝试从进程环境解析插值
- 当 `${VW_DIFY_*}` 插值失败时（进程环境中不存在），server.py 内部通过 python-dotenv 从 `.env` 加载 `VW_DIFY_*` 作为回退
- paper-search 使用绝对路径 `cwd` 指向独立项目
- dify-knowledge 使用 PEP 723 内联依赖（`mcp[cli]`, `httpx`, `python-dotenv`），`uv run` 自动解析

## Claude Code 本地设置

`.claude/settings.local.json` 配置了 `additionalDirectories`，授权 Claude Code 访问 paper-search 所在的外部目录（`C:\Users\17162\Desktop\Terms\workflow`），使 MCP stdio 通信正常工作。

## 调试技巧

1. **验证 MCP 连接**: 在 Claude Code 会话中直接调用 MCP 工具，观察返回
2. **检查凭据**: `uv run scripts/validate_env.py` 会检查 Dify 凭据配置状态
3. **查看日志**: Dify 桥接服务器使用 Python logging，错误信息输出到 stderr
4. **手动测试桥接服务器**: `uv run scripts/dify-kb-mcp/server.py`（需要 MCP 客户端连接）
5. **环境变量诊断**: 如果 MCP 工具返回凭据缺失错误，检查以下两个来源是否配置正确：
   - `.env` 文件中的 `VW_DIFY_API_BASE_URL`、`VW_DIFY_API_KEY`、`VW_DIFY_DATASET_ID`
   - `.mcp.json` 中的 `${VW_DIFY_*}` 插值是否能在当前 shell 环境中解析
6. **URL 重复路径问题**: 如果 API 返回 404，检查 `VW_DIFY_API_BASE_URL` 是否已包含 `/v1`（server.py 请求路径不再添加 `/v1` 前缀）

## 已知问题与修复记录

### 环境变量传递失败（已修复 2026-03-03）

**问题**: Claude Code 启动 MCP 服务器时，`.mcp.json` 中 `${VW_DIFY_API_BASE_URL}` 等插值未被解析（进程环境中不存在这些变量），导致 `DIFY_API_BASE_URL` 为空字符串。

**修复**: server.py 新增 `python-dotenv` 依赖，启动时自动从项目根 `.env` 加载环境变量（`override=False` 不覆盖已有值）。环境变量回退链：`DIFY_*` -> `VW_DIFY_*`。

### URL 路径重复（已修复 2026-03-03）

**问题**: `.env` 中 `VW_DIFY_API_BASE_URL=https://api.dify.ai/v1`，但 server.py 请求路径以 `/v1/datasets/...` 开头，最终 URL 变成 `https://api.dify.ai/v1/v1/datasets/...`。

**修复**: 请求路径去掉 `/v1` 前缀，直接使用 `/datasets/{id}/retrieve` 和 `/datasets/{id}/documents`。

### `${VAR}` 插值字面量泄漏（已修复 2026-03-03）

**问题**: Claude Code MCP 环境变量插值存在已知 Bug（#9427, #1254, #14032, #28090）：当 `${VW_DIFY_API_BASE_URL}` 等变量不在进程环境中时，插值不会解析为空字符串，而是将字面量 `${VW_DIFY_API_BASE_URL}` 原样传入子进程。由于字面量是 truthy 字符串，Python `or` 运算符短路，`VW_DIFY_*` 回退链失效。

**修复**: 新增 `_resolve_env(key)` 辅助函数，通过 `re.fullmatch(r"\$\{.+\}", val)` 检测 `${...}` 字面量格式并返回 `None`，使回退链正常工作。同时 `_check_credentials()` 增加 URL 协议前缀检查（`http://` 或 `https://`），可捕获字面量漏网后的 URL 格式错误，错误信息明确提示用 `.env` 文件中的 `VW_DIFY_*` 变量。
