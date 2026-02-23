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
- **依赖**: `mcp[cli]>=1.0`, `httpx>=0.27`

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
# .env 中配置
DIFY_API_BASE_URL=https://api.dify.ai/v1   # Dify API 地址
DIFY_API_KEY=                                # Dify API 密钥
DIFY_DATASET_ID=                             # 数据集 ID
DIFY_MAX_RETRIES=3                           # 最大重试次数（可选）
DIFY_TIMEOUT=30                              # 请求超时秒数（可选）
```

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
- 环境变量使用 `${VAR}` 引用，从 `.env` 文件加载
- paper-search 使用绝对路径 `cwd` 指向独立项目
- dify-knowledge 使用 PEP 723 内联依赖，`uv run` 自动解析

## Claude Code 本地设置

`.claude/settings.local.json` 配置了 `additionalDirectories`，授权 Claude Code 访问 paper-search 所在的外部目录（`C:\Users\17162\Desktop\Terms\workflow`），使 MCP stdio 通信正常工作。

## 调试技巧

1. **验证 MCP 连接**: 在 Claude Code 会话中直接调用 MCP 工具，观察返回
2. **检查凭据**: `uv run scripts/validate_env.py` 会检查 Dify 凭据配置状态
3. **查看日志**: Dify 桥接服务器使用 Python logging，错误信息输出到 stderr
4. **手动测试桥接服务器**: `uv run scripts/dify-kb-mcp/server.py`（需要 MCP 客户端连接）
