# 项目当前状态

**最后更新**: 2026-02-23
**阶段**: 基础架构搭建完成 -- `project-foundation-architecture` 变更已归档

## 里程碑

**52/52 任务全部完成，6 个 spec 已合并到 `openspec/specs/`**

| 阶段 | 内容 | 任务数 | 状态 |
|------|------|--------|------|
| P0 | 项目脚手架 + Git + Python + CLAUDE.md | 13 | 已完成 |
| P1 | MCP 配置 + paper-search 集成 + Skills | 7 | 已完成 |
| P2 | 环境验证脚本 v1 | 8 | 已完成 |
| P3 | LaTeX 模板 + 构建脚本 | 10 | 已完成 |
| P4 | Dify MCP 桥接服务器 | 7 | 已完成 |
| 最终验证 | 全量校验 | 7 | 已完成 |

## 环境

| 项目 | 版本/状态 | 备注 |
|------|----------|------|
| OS | Windows 11 | 路径用正斜杠，shell 用 Git Bash |
| Python | 3.12.2 | 满足 >=3.11 要求 |
| uv | 0.6.9 | 依赖管理工具，`uv sync` 已完成 |
| Git | 2.52.0 | 版本控制 |
| Node.js | v22.14.0 | MCP 相关工具可能需要 |
| TeX Live | **需用户安装** | 阻塞 LaTeX 编译（约 8GB），模板和构建脚本已就绪 |
| make | **未安装** | 构建脚本用 bash 替代 |
| Dify | 已有实例 | URL + API Key + Dataset ID 待配置到 .env |
| Windows 字体 | 就绪 | SimSun/SimHei/KaiTi/FangSong 已预装 |

## 已交付产物概览

### 核心配置（P0）
- `CLAUDE.md` -- 项目级 Claude Code 配置，90 行，5 核心要素
- `pyproject.toml` -- Python 包定义（hatchling + src 布局，12 个运行时依赖）
- `uv.lock` -- 依赖锁文件，已提交 Git 保证可复现性（D3）
- `src/vibewriting/config.py` -- 集中配置管理，基于 python-dotenv（D7）
- `.env.example` -- 环境变量模板
- `.gitignore` / `.gitattributes` -- Git 配置

### MCP 集成（P1 + P4）
- `.mcp.json` -- 双 MCP 服务器配置（paper-search + dify-knowledge）
- `.claude/settings.local.json` -- 授权 paper-search 外部目录访问
- 3 个 Skills -- search-literature, retrieve-kb, validate-citations
- `scripts/dify-kb-mcp/server.py` -- FastMCP 桥接服务器（204 行，PEP 723）

### 环境验证（P2）
- `scripts/validate_env.py` -- 分级退出码 0/1/2，彩色输出 + JSON 报告

### LaTeX 模板（P3）
- `paper/main.tex` -- ctexart 主文档
- `paper/latexmkrc` -- latexmk 配置（$pdf_mode=5, out_dir=build）
- `paper/sections/` -- 6 个章节模板（introduction, related-work, method, experiments, conclusion, appendix）
- `paper/bib/references.bib` -- 参考文献数据库（含示例条目）
- `build.sh` -- 构建脚本（build/watch/clean/check/doi2bib）

### OPSX 归档
- `openspec/changes/project-foundation-architecture/` -- proposal + design + tasks
- `openspec/specs/` -- 6 个已合并规格（project-scaffold, latex-compilation, claude-config, mcp-integration, python-environment, env-validation）

## 下一步行动

基础架构已就绪，完整路线图见 **`openspec/ROADMAP.md`**（v4，617 行，7 阶段）。

### 阶段依赖图

```
Phase 1: 基础架构 [已完成]
   |
   +---> Phase 2: 数据模型 + 处理管线 ─────+
   |                                        +---> Phase 4: 单 Agent 草稿撰写
   +---> Phase 3: 文献整合工作流 ───────────+            |
                                                         v
                                                Phase 5: 多 Agent 编排
                                                         |
                                                         v
                                                Phase 6: 编译 + 质量保证
                                                         |
                                                         v
                                                Phase 7: 端到端集成
```

- Phase 2 和 Phase 3 **可并行开发**（无相互依赖）
- 阶段间设有 **Approval Gates**（通过 AskUserQuestion 实现人机协同审批）
- 详细阶段说明、交付物清单、验证标准见 `openspec/ROADMAP.md`

### 下一阶段工作（Phase 2 + Phase 3 并行）

| 阶段 | 核心交付物 | 涉及目录 |
|------|-----------|---------|
| Phase 2 | Pydantic 模型 + 契约体系 + 数据管线 + 图表生成 + Golden Test | `src/vibewriting/models/`, `contracts/`, `processing/`, `visualization/` |
| Phase 3 | 文献检索工作流 + Evidence Card 系统 + BibTeX 管理 | `src/vibewriting/agents/`, `data/processed/literature/` |

### 需要用户操作的阻塞项

1. **TeX Live 安装** -- 安装后 `bash build.sh build` 可编译论文，`validate_env.py` 中 xelatex/latexmk/bibtex/checkcites 将从 blocked 变为 pass
2. **Dify 凭据配置** -- 在 `.env` 中设置 `DIFY_API_KEY`, `DIFY_API_BASE_URL`, `DIFY_DATASET_ID`，启用知识库检索功能

### 可立即开始的工作

- Pydantic 数据模型定义（`src/vibewriting/models/`）-- Phase 2
- 阶段产物契约 + JSON Schema（`src/vibewriting/contracts/`）-- Phase 2
- 数据处理管线搭建（`src/vibewriting/processing/`, `visualization/`）-- Phase 2
- 文献检索端到端工作流测试（通过 paper-search MCP，无需 TeX Live）-- Phase 3
- Evidence Card 系统设计（`literature_cards.jsonl` + schema）-- Phase 3
