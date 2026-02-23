# vibewriting - LLM 文档索引

基于 Claude Code 与 Dify 知识库的科研论文自动化写作系统。

## 快速导航

### overview/ - 项目概览（必读）

| 文档 | 内容 | 何时阅读 |
|------|------|---------|
| [architecture.md](overview/architecture.md) | 三层架构设计、技术栈决策、四阶段工作流 | 理解系统整体设计 |
| [project-status.md](overview/project-status.md) | 当前环境状态、OPSX 进度、下一步行动 | 了解项目进展和待办 |

### guides/ - 操作指南

| 文档 | 内容 | 何时阅读 |
|------|------|---------|
| （待创建） | 开发指南、环境配置等 | P3 实施后补充 |

**快速验证环境**: `uv run scripts/validate_env.py`（P2 已交付）

### architecture/ - 系统架构详情

（待初始化 — 各模块实现后补充模块级架构文档）

### reference/ - 参考资料

（待初始化 — API 规格、数据模型、约定规范等）

## 源文件索引

### OPSX 规划文档

| 文件 | 路径 | 说明 |
|------|------|------|
| 系统设计文档 | `origin.md` | 完整的架构蓝图与工作流设计报告（约 24KB，详尽版） |
| OPSX Proposal | `openspec/changes/project-foundation-architecture/proposal.md` | 基础架构搭建的变更提案（含约束分析、需求定义、成功判据） |
| OPSX Design | `openspec/changes/project-foundation-architecture/design.md` | 技术设计文档（9 项决策 D1-D9，风险分析，阶段划分） |
| OPSX Tasks | `openspec/changes/project-foundation-architecture/tasks.md` | 实施任务清单（37 项任务，6 个阶段 P0-P4 + 最终验证） |
| Spec: project-scaffold | `openspec/changes/project-foundation-architecture/specs/project-scaffold/spec.md` | 项目脚手架规格（REQ-01, REQ-06） |
| Spec: latex-compilation | `openspec/changes/project-foundation-architecture/specs/latex-compilation/spec.md` | LaTeX 编译链规格（REQ-02, REQ-07） |
| Spec: claude-config | `openspec/changes/project-foundation-architecture/specs/claude-config/spec.md` | CLAUDE.md 配置规格（REQ-03） |
| Spec: mcp-integration | `openspec/changes/project-foundation-architecture/specs/mcp-integration/spec.md` | MCP 服务器集成规格（REQ-04, REQ-08, REQ-09） |
| Spec: python-environment | `openspec/changes/project-foundation-architecture/specs/python-environment/spec.md` | Python 环境规格（REQ-05） |
| Spec: env-validation | `openspec/changes/project-foundation-architecture/specs/env-validation/spec.md` | 环境验证脚本规格（REQ-10） |
| 团队研究报告 | `.claude/team-plan/vibewriting-research.md` | 多 Agent 交叉验证的约束集与 MVP 路径 |

### P0 产出文件（项目脚手架 + Git + Python + CLAUDE.md）

| 文件 | 路径 | 说明 |
|------|------|------|
| CLAUDE.md | `CLAUDE.md` | Claude Code 项目配置（89 行，5 核心要素） |
| pyproject.toml | `pyproject.toml` | Python 包定义，uv 管理依赖 |
| uv.lock | `uv.lock` | 依赖锁文件，保证科研可复现性（D3 决策） |
| config.py | `src/vibewriting/config.py` | 集中配置管理，基于 python-dotenv（D7 决策） |
| __init__.py | `src/vibewriting/__init__.py` | 包入口，定义版本号 |
| .env.example | `.env.example` | 环境变量模板（D7 决策） |
| .gitignore | `.gitignore` | 覆盖 LaTeX + Python + .venv |
| .gitattributes | `.gitattributes` | Git 属性配置 |
| conftest.py | `tests/conftest.py` | pytest 测试配置 |

### P1 产出文件（MCP 配置 + paper-search 集成 + Skills）

| 文件 | 路径 | 说明 |
|------|------|------|
| .mcp.json | `.mcp.json` | MCP 服务器配置：paper-search(stdio) + dify-knowledge(bridge) |
| settings.local.json | `.claude/settings.local.json` | Claude Code 本地设置，授权 paper-search 外部目录访问 |
| SKILL: search-literature | `.claude/skills/search-literature/SKILL.md` | 文献检索工作流：search_papers, decide, get_session, export_results |
| SKILL: retrieve-kb | `.claude/skills/retrieve-kb/SKILL.md` | Dify 知识库检索：retrieve_knowledge, list_documents |
| SKILL: validate-citations | `.claude/skills/validate-citations/SKILL.md` | 引用完整性验证：checkcites 工作流 |

### P2 产出文件（环境验证脚本）

| 文件 | 路径 | 说明 |
|------|------|------|
| validate_env.py | `scripts/validate_env.py` | 环境验证脚本：彩色控制台输出 + JSON 报告，分级退出码 0/1/2（D5 决策落地） |

### P4 产出文件（Dify MCP 桥接服务器）

| 文件 | 路径 | 说明 |
|------|------|------|
| server.py | `scripts/dify-kb-mcp/server.py` | Dify 知识库 MCP 桥接服务器：FastMCP，2 个工具（retrieve_knowledge, list_documents），httpx 异步客户端，优雅降级，重试逻辑，PEP 723 内联依赖（204 行） |
| .mcp.json（更新） | `.mcp.json` | 更新 dify-knowledge 配置：args 改为 PEP 723 兼容格式，添加显式 cwd |

## 关于本文档系统

- 面向 LLM 阅读优化，保持结构化和简洁
- 使用简体中文
- 遵循 llmdoc 标准目录结构（index / overview / guides / architecture / reference）
- 文档更新应与代码变更同步
