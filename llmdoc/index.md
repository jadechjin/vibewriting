# vibewriting - LLM 文档索引

基于 Claude Code 与 Dify 知识库的科研论文自动化写作系统。

**项目状态**: 基础架构搭建完成（`project-foundation-architecture` 变更已归档，52/52 任务，6 个 spec 已合并）

## 快速导航

### overview/ - 项目概览（必读）

| 文档 | 内容 | 何时阅读 |
|------|------|---------|
| [architecture.md](overview/architecture.md) | 三层架构设计、技术栈决策、四阶段工作流 | 理解系统整体设计 |
| [project-status.md](overview/project-status.md) | 当前环境状态、已完成里程碑、下一步行动 | 了解项目进展和待办 |

### guides/ - 操作指南

| 文档 | 内容 | 何时阅读 |
|------|------|---------|
| [development.md](guides/development.md) | 开发环境搭建、构建流程、验证命令 | 开始开发前 |
| [mcp-integration.md](guides/mcp-integration.md) | MCP 服务器配置、工具调用方法、调试技巧 | 使用文献检索或知识库时 |

### architecture/ - 系统架构详情

| 文档 | 内容 | 何时阅读 |
|------|------|---------|
| [directory-map.md](architecture/directory-map.md) | 完整目录结构、每个文件/目录的用途和来源 | 查找文件位置或理解项目布局 |

### reference/ - 参考资料

| 文档 | 内容 | 何时阅读 |
|------|------|---------|
| [tech-decisions.md](reference/tech-decisions.md) | 9 项技术决策（D1-D9）速查表、约束备忘 | 需要理解"为什么这样做"时 |

## 源文件索引

### 核心配置文件

| 文件 | 路径 | 说明 |
|------|------|------|
| CLAUDE.md | `CLAUDE.md` | Claude Code 项目配置（90 行，5 核心要素） |
| pyproject.toml | `pyproject.toml` | Python 包定义，uv + hatchling，src 布局 |
| uv.lock | `uv.lock` | 依赖锁文件，保证科研可复现性 |
| .mcp.json | `.mcp.json` | MCP 服务器配置：paper-search(stdio) + dify-knowledge(bridge) |
| .env.example | `.env.example` | 环境变量模板 |
| build.sh | `build.sh` | 构建脚本（build/watch/clean/check/doi2bib） |

### Python 源码

| 文件 | 路径 | 说明 |
|------|------|------|
| config.py | `src/vibewriting/config.py` | 集中配置管理，基于 python-dotenv |
| __init__.py | `src/vibewriting/__init__.py` | 包入口，定义版本号 |
| validate_env.py | `scripts/validate_env.py` | 环境验证脚本：彩色输出 + JSON 报告，分级退出码 0/1/2 |
| server.py | `scripts/dify-kb-mcp/server.py` | Dify 知识库 MCP 桥接服务器：FastMCP，204 行 |

### LaTeX 论文模板

| 文件 | 路径 | 说明 |
|------|------|------|
| main.tex | `paper/main.tex` | ctexart 主文档，\input 章节组织 |
| latexmkrc | `paper/latexmkrc` | latexmk 配置（$pdf_mode=5, out_dir=build） |
| references.bib | `paper/bib/references.bib` | 参考文献数据库 |
| sections/*.tex | `paper/sections/` | 6 个章节模板文件 |

### Claude Code 配置

| 文件 | 路径 | 说明 |
|------|------|------|
| settings.local.json | `.claude/settings.local.json` | 本地设置，授权 paper-search 外部目录访问 |
| search-literature | `.claude/skills/search-literature/SKILL.md` | 文献检索工作流 Skill |
| retrieve-kb | `.claude/skills/retrieve-kb/SKILL.md` | Dify 知识库检索 Skill |
| validate-citations | `.claude/skills/validate-citations/SKILL.md` | 引用完整性验证 Skill |

### OPSX 归档

| 文件 | 路径 | 说明 |
|------|------|------|
| proposal.md | `openspec/changes/archive/2026-02-23-project-foundation-architecture/proposal.md` | 变更提案（10 个需求，12 个成功判据） |
| design.md | `openspec/changes/archive/2026-02-23-project-foundation-architecture/design.md` | 技术设计（9 项决策 D1-D9） |
| tasks.md | `openspec/changes/archive/2026-02-23-project-foundation-architecture/tasks.md` | 任务清单（52 项，全部完成） |
| specs/ | `openspec/specs/` | 6 个已合并规格模块 |

## 关于本文档系统

- 面向 LLM 阅读优化，保持结构化和简洁
- 使用简体中文
- 遵循 llmdoc 标准目录结构（index / overview / guides / architecture / reference）
- 文档更新应与代码变更同步
