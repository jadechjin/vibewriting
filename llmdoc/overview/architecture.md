# 系统架构概览

**项目**: vibewriting - 基于 Claude Code 与 Dify 知识库的科研论文自动化写作系统
**目标**: 输入论文主题，端到端产出可编译的 LaTeX 论文 + PDF
**状态**: Phase 7 完成（端到端集成，874 tests，路线图 v4 全部 7 个阶段已交付 + Bug 修复与配置统一）

## 三层架构

```
+--------------------------------------------------+
|          编排与推理层 (Claude Code)                  |
|  CLAUDE.md | Skills | Sub-agents | Agent Teams    |
+--------------------------------------------------+
                    |  MCP 协议
+--------------------------------------------------+
|          知识与检索层 (Dify + paper-search)          |
|  Dify MCP Server | paper-search MCP Server         |
+--------------------------------------------------+
                    |  MCP / Bash / Python
+--------------------------------------------------+
|          集成与执行层                                |
|  Python 数据管道 | LaTeX (TeX Live) | File System   |
+--------------------------------------------------+
```

### 编排与推理层

Claude Code 作为中枢编排引擎，负责：
- 解析用户高层级研究意图，拆解为可执行子任务
- 通过 CLAUDE.md 注入项目级指令（渐进式披露，<=300 行）
- 通过 Sub-agents / Agent Teams 实现多智能体协同撰写
- 通过自定义 Skills（`.claude/skills/`）封装可复用工作流

已交付的 7 个 Skills：
- `vibewriting-literature` -- 文献检索端到端工作流（search_papers -> decide -> export_results -> 去重 -> Evidence Card 生成 -> 缓存入库）
- `vibewriting-kb` -- Dify 知识库检索（retrieve_knowledge + list_documents）
- `vibewriting-cite-check` -- 引用完整性验证（checkcites 工作流）
- `vibewriting-draft` -- Evidence-First 草稿撰写工作流（[Phase 4] 加载证据卡 -> 生成大纲 -> 增量撰写 -> 质量门禁）
- `vibewriting-orchestrate` -- 多 Agent 编排写作工作流（[Phase 5] 加载产物 -> 构建任务图 -> 并发调度 -> 冲突裁决 -> 质量门禁）
- `vibewriting-review` -- 论文质量审查工作流（[Phase 6] 编译验证 -> 引文审计 -> 契约一致性 -> 模拟同行评审 -> Approval Gate）
- `vibewriting-paper` -- 端到端一键写作主入口（[Phase 7] 9 步工作流 + 5 个 Approval Gates，配置加载 -> 检查点检测 -> 环境验证 -> 数据管线 -> 文献检索 -> 草稿撰写 -> 多 Agent 编排 -> 编译审查 -> 指标汇总）

### 知识与检索层

两个 MCP 服务器提供知识检索能力：

| 服务器 | 传输方式 | 工具 | 状态 |
|--------|---------|------|------|
| paper-search | stdio | `search_papers`, `decide`, `export_results`, `get_session` | 已完成 |
| dify-knowledge | stdio | `retrieve_knowledge`, `list_documents` | 已完成（待 Dify 凭据验证） |

**paper-search**: 位于 `C:\Users\17162\Desktop\Terms\workflow`，独立项目，通过 MCP stdio 协议集成（D9 决策）
**Dify 桥接**: FastMCP 服务器（`scripts/dify-kb-mcp/server.py`，221 行），PEP 723 内联依赖

Dify 桥接服务器特性：
- httpx 异步客户端，调用 Dify `/datasets/{id}/retrieve` 和 `/datasets/{id}/documents` API
- python-dotenv 启动时自动加载项目根 `.env`（`override=False`），解决 MCP 环境变量插值失败问题
- 环境变量回退链：`DIFY_*`（.mcp.json 传入） -> `VW_DIFY_*`（.env 直接读取）
- URL 路径不含 `/v1` 前缀（base URL 已包含，如 `https://api.dify.ai/v1`），自动清理末尾斜杠
- `retrieve_knowledge`: 支持 hybrid/keyword/semantic 搜索 + reranking
- `list_documents`: 分页 + 关键词过滤
- 优雅降级：凭据缺失时服务器正常启动，工具调用返回结构化错误
- 重试逻辑：MAX_RETRIES（最小 1）和 TIMEOUT 可通过环境变量配置
- 4xx 短路：客户端错误不重试，仅 5xx 和网络错误重试

### 集成与执行层

| 组件 | 技术方案 | 用途 | 状态 |
|------|---------|------|------|
| 数据模型 | Pydantic 2.0 + BaseEntity/AssetBase | 6 个实体模型（Paper, Experiment, Figure, Table, Section） | **已完成** |
| 契约系统 | jsonschema + 自愈循环（regex/LLM healer） | Schema 导出 + 验证 + 引用完整性 | **已完成** |
| 数据处理 | Python 3.12 + pandas + scipy + statsmodels | CSV/JSON 清洗、统计分析 | **已完成** |
| 可视化 | matplotlib + seaborn（pgf 后端导出）+ jinja2 | 生成 PDF/PGF/PNG 图表 + LaTeX 表格 | **已完成** |
| DAG 管线 | DAGRunner（拓扑排序）+ Typer CLI | 8 节点管线：load -> clean -> transform -> stats -> figs/tables -> manifests -> validate | **已完成** |
| 文献整合 | bibtexparser 2.x + JSONL 缓存 + MCP 编排 | 文献检索/去重/Evidence Card/BibTeX 管理/知识缓存 | **已完成** |
| 草稿撰写 | PaperState + 质量门禁 + 增量编译 | Evidence-First 单章节撰写工作流 + 术语/符号表 | **已完成** |
| 多 Agent 编排 | Orchestrator + 角色 Agent + 合并协议 | 多视角协同撰写 + 冲突裁决 + Git 安全网 | **已完成** |
| 编译链 | XeLaTeX + latexmk + BibTeX + 自愈循环 | 论文编译 + 日志解析 + 错误分类 + Patch 护栏 + 自动重试 | **已完成** |
| 质量审查 | 引文审计 + 同行评审模拟 + 排版检查 + AI 披露 + 匿名化 | 编译后质量保证 + phase6_report.json | **已完成** |
| 全量契约 | SHA256 资产哈希 + TeX 引用交叉验证 | 端到端引用完整性验证 | **已完成** |
| 端到端集成 | PaperConfig + Checkpoint + RunMetrics + vibewriting-paper Skill | 一键式工作流（主题 -> PDF）+ 检查点续跑 + 指标汇总 | **已完成** |

## 双配置系统（Post-Phase 7）

配置分为两层，通过 `apply_paper_config()` 桥接：

```
paper_config.yaml  (非敏感配置，统一入口)
    |                                          优先级: .env > paper_config.yaml > defaults
    +-- apply_paper_config() --> Settings      仅当 env var 未设置时（仍为默认值），YAML 值才生效
    |
.env  (敏感凭据 + env-only 字段)
    |
    +-- pydantic-settings (env_prefix="VW_") --> Settings
```

| 配置层 | 文件 | 内容 | 修改频率 |
|--------|------|------|---------|
| 论文级配置 | `paper_config.yaml` | 题目/章节/natbib_style/管线参数（random_seed, float_precision, dedup_threshold, compile_max_retries, compile_timeout_sec） | 每篇论文 |
| 环境凭据 | `.env` | API 密钥（VW_DIFY_*）+ env-only 字段（VW_PATCH_WINDOW_LINES, VW_CROSSREF_API_EMAIL 等） | 一次性配置 |

桥接函数 `apply_paper_config()` 位于 `src/vibewriting/config.py`，使用 `model_copy(update=...)` 不可变模式创建新 Settings 实例。

## 七阶段工作流

完整路线图见 `openspec/ROADMAP.md`（v4，617 行）。

### 阶段总览

```
Phase 1: 基础架构 [已完成]
   |
   +---> Phase 2: 数据模型 + 处理管线 [已完成]    Phase 3: 文献整合工作流 [已完成]
   |        (资产契约 + 图表)                        (证据卡 + BibTeX)
   |              |                                          |
   |              +------------ Approval Gates --------------+
   |                                |
   |                                v
   |                   Phase 4: 单 Agent 草稿撰写 [已完成]
   |                       (Evidence-First + 增量编译)
   |                                |
   |                                v
   |                   Phase 5: 多 Agent 编排 [已完成]
   |                       (Orchestrator + 角色 Agent + 合并协议)
   |                                |
   |                                v
   |                   Phase 6: 编译 + 质量保证 [已完成]
   |                       (自修复 + 同行评审模拟)
   |                                |
   |                                v
   |                   Phase 7: 端到端集成 [已完成]
   |                       (一键: 主题 -> PDF)
```

各阶段对应四个核心工作流：

| 工作流 | 阶段 | 输入 | 输出 |
|--------|------|------|------|
| 智能化文献检索 | Phase 3 | 研究主题 | `literature_cards.jsonl` + BibTeX |
| 数据分析与资产生成 | Phase 2 | 原始数据 | 图表(.pgf/.pdf) + 表格(.tex) + `asset_manifest.json` |
| 协同撰写 | Phase 4 + 5 | 证据卡 + 数据资产 | `paper/sections/*.tex` + `paper_state.json` |
| 编译与评审 | Phase 6 + 7 | LaTeX 源码 | PDF + 审查报告 + `run_metrics.json` |

## 阶段产物契约体系

JSON 是唯一事实源，LaTeX 是渲染层。所有阶段产物通过机器可验证的 JSON Schema 定义。

**实现状态**: Phase 2 已建成核心契约基础设施，Phase 3 已交付 `literature_cards.jsonl` 产物，Phase 4 已交付 `paper_state.json`、`glossary.json`、`symbols.json` 产物及对应 JSON Schema，Phase 5 已交付 Agent 通信契约 + 引用完整性增强（glossary/symbol integrity），Phase 6 已交付全量契约验证（TeX 引用交叉验证 + 资产哈希 SHA256 + 端到端完整性），Phase 7 已交付端到端集成层（PaperConfig + Checkpoint + RunMetrics + vibewriting-paper Skill）。

```
src/vibewriting/contracts/
  +-- schema_export.py       <- Pydantic 模型 -> JSON Schema 导出（已实现，Phase 4 更新）
  +-- validator.py           <- 自愈验证循环：jsonschema -> regex -> LLM（已实现）
  +-- integrity.py           <- 引用完整性验证（已实现）
  +-- full_integrity.py      <- 全量契约验证：TeX 引用交叉 + 资产哈希 SHA256 + 章节完整性 + 术语/符号 TeX 验证 + 端到端（已实现）[Phase 6 新增]
  +-- healers/
  |   +-- regex_healer.py    <- 正则表达式修复器（已实现）
  |   +-- llm_healer.py      <- LLM 回退修复器（已实现）
  +-- schemas/               <- JSON Schema 定义文件（由 schema_export 生成）
      +-- paperstate.schema.json   <- [Phase 4 新增]
      +-- glossary.schema.json     <- [Phase 4 新增]
      +-- symboltable.schema.json  <- [Phase 4 新增]

src/vibewriting/literature/
  +-- models.py              <- RawLiteratureRecord 统一文献格式（已实现）
  +-- bib_manager.py         <- BibTeX 解析/规范化/合并/写回（已实现）
  +-- evidence.py            <- Evidence Card 生成 + claim_id 管理（已实现）
  +-- cache.py               <- JSONL 知识缓存 + 四级索引（已实现）
  +-- dedup.py               <- 三层去重管道 L1/L2/L3 + inventory_filtered 统计（已实现）
  +-- dify_inventory.py      <- Dify KB 文献清单管理（sync/load/dedup_against_inventory）[Bug Fix Round 3 新增]
  +-- search.py              <- MCP 编排器 + 降级策略 + 清单去重集成（已实现）

src/vibewriting/writing/     <- [Phase 4 新增]
  +-- quality_gates.py       <- 5 种质量门禁 + 增强术语一致性检测 [Phase 5 更新]
  +-- state_manager.py       <- PaperStateManager（不可变模式 + 原子写入 + batch 更新）[Phase 5 更新]
  +-- outline.py             <- 大纲生成（build_default_outline, outline_to_paper_state）
  +-- latex_helpers.py       <- CLAIM_ID 注释管理、引用格式化、LaTeX 解析
  +-- incremental.py         <- 增量编译（draft_main.tex 单章节编译）

src/vibewriting/agents/      <- [Phase 5 新增]
  +-- contracts.py           <- Agent 通信契约（10 个 Pydantic 模型，strict extra="forbid"）
  +-- planner.py             <- 章节任务规划器（依赖图 + 就绪任务 + 角色分配）
  +-- merge_protocol.py      <- 合并协议（验证 + 冲突检测 + 裁决 + 合并应用）
  +-- executor.py            <- AgentExecutor Protocol + MockExecutor + SubAgentExecutor
  +-- orchestrator.py        <- WritingOrchestrator 编排核心（多轮依赖层调度）
  +-- git_safety.py          <- Git 安全网（snapshot_commit + rollback + stash，管辖 paper/ + output/）[Phase 6 增强]

src/vibewriting/latex/        <- [Phase 6 新增]
  +-- __init__.py             <- 模块导出（compile_full, run_self_heal_loop, ErrorKind, LatexError 等）
  +-- log_parser.py           <- LaTeX 日志解析器（ErrorKind 枚举 + parse_log + classify_error）
  +-- patch_guard.py          <- Patch 安全护栏（PatchProposal + validate + apply_patch 原子写入）
  +-- compiler.py             <- 自愈编译器（compile_full + route_error + run_self_heal_loop 循环）
  +-- cli.py                  <- Phase 6 Typer CLI（4 步管线，输出 phase6_report.json）

src/vibewriting/review/       <- [Phase 6 新增]
  +-- __init__.py             <- 模块导出
  +-- models.py               <- 审查数据模型（ReviewSeverity/Category, PeerReviewReport, Phase6Report 等）
  +-- citation_audit.py       <- 引文交叉审计（cite_keys 提取 + evidence_cards 交叉 + CrossRef 验证）
  +-- peer_review.py          <- 模拟同行评审（结构/证据/方法论评审 + 评分判定 + MD/JSON 报告）
  +-- typography.py           <- 排版检查（overfull hbox + float + widow/orphan + chktex）
  +-- disclosure.py           <- AI 使用声明（EN/ZH 模板 + inject_disclosure）
  +-- anonymize.py            <- 匿名化处理（anonymize_tex + check_anonymization）

src/vibewriting/config_paper.py    <- [Phase 7 新增] PaperConfig Pydantic 模型（论文配置：题目/领域/章节列表/研究问题/natbib_style=unsrtnat + 4 个管线字段）
src/vibewriting/checkpoint.py      <- [Phase 7 新增] PhaseStatus(Enum) + PhaseRecord + Checkpoint；检查点管理（detect/save/create/update_phase/get_resume_phase/should_skip_phase/validate）
src/vibewriting/metrics.py         <- [Phase 7 新增] LiteratureMetrics + WritingMetrics + CompilationMetrics + RunMetricsReport；指标聚合（collect_*/build_run_metrics/save_run_metrics）

output/
  +-- asset_manifest.json    <- 数据资产清单（管线自动生成）
  +-- run_manifest.json      <- 运行环境锁定（管线自动生成）

data/processed/literature/
  +-- literature_cards.jsonl  <- 文献证据卡集合（Phase 3 产物）
  +-- dify_kb_inventory.json  <- Dify KB 文献清单 JSON（运行时生成）[Bug Fix Round 3 新增]

Phase 4 产物:
  +-- paper_state.json       <- 论文全局状态机（已实现）
  +-- glossary.json          <- 术语表（已实现）
  +-- symbols.json           <- 符号表（已实现）
```

产出阶段分配：

| 契约文件 | 产出阶段 | 消费阶段 | 状态 |
|---------|---------|---------|------|
| `asset_manifest.json` | Phase 2 | Phase 4/5/6 | **已交付** |
| `run_manifest.json` | Phase 2 | Phase 6/7 | **已交付** |
| `literature_cards.jsonl` | Phase 3 | Phase 4/5/6 | **已交付** |
| `paper_state.json` | Phase 4 | Phase 5/6/7 | **已交付** |
| `glossary.json` + `symbols.json` | Phase 4 初版 | Phase 5 合并裁决, Phase 6 一致性验证 | **已交付** |
| `phase6_report.json` | Phase 6 | Phase 7 | **已交付** |
| `patch_reports/` | Phase 6 | Phase 7 审计 | **已交付** |
| `review_report.json` + `review_report.md` | Phase 6 | Phase 7 审计 | **已交付** |
| `run_metrics.json` | Phase 7 | 用户查阅 | **已交付** |

契约强校验与自愈：写入任何契约文件前，必须经过 `jsonschema.validate()` 拦截，校验失败触发 Prompt 反弹修复（最多重试 3 次）。

引用完整性约束（Phase 6 验证）：
- `paper_state` 中的 `claim_id` -> `literature_cards`
- `paper_state` 中的 `asset_id` -> `asset_manifest`
- 术语/符号 -> `glossary` / `symbols`
- `bib_key` -> `references.bib`

## 跨阶段设计原则（9 项）

详细说明见 `openspec/ROADMAP.md` "跨阶段设计原则" 章节。

| 编号 | 原则 | 核心思想 |
|------|------|---------|
| 1 | 阶段产物契约 | JSON Schema + 自愈循环 + 引用完整性外键 |
| 2 | 证据优先工作流 | Evidence Card + claim 追溯，Writer 只引用已入库证据 |
| 3 | Git 一等公民 | auto commit + snapshot + stash，`auto:` 前缀区分 |
| 4 | 人机协同审批门 | AskUserQuestion 实现 Approval Gates |
| 5 | LaTeX 增量编译 | `draft_main.tex`(单章节) -> `main.tex`(全量) |
| 6 | 可观测性与指标 | run_id + 8 项指标（文献/写作/编译/体验） |
| 7 | 合规与 AI 披露 | 引用摘抄限制 + AI 声明可开关 |
| 8 | 源码溯源注释 | `%% CLAIM_ID: EC-2026-XXX` 注释可追溯 |
| 9 | Prompt 缓存架构 | 静态头部(schemas+证据卡) + 动态尾部(任务指令) |

## 技术栈决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| LaTeX 文档类 | ctexart | 自动处理中文标点压缩、行距、字号、标题汉化 |
| 编译器 | XeLaTeX via latexmk (`$pdf_mode=5`) | 原生 Unicode 支持，Windows 字体自动检测 |
| 参考文献 | BibTeX + natbib (unsrtnat) | `\citep{}`/`\citet{}` 引用风格，`unsrtnat` 按引用顺序排列 |
| Python 构建 | hatchling + src 布局 | 与 paper-search 一致 |
| 依赖管理 | uv + pyproject.toml | 快速解析，锁文件确定性 |
| 图表导出 | matplotlib pgf 后端 | tikzplotlib 已废弃，pgf 原生 LaTeX 兼容 |
| MCP 配置 | `.mcp.json`（项目级） | 可提交 Git，团队共享 |
| 章节组织 | `\input`（非 `\include`） | 不强制换页，灵活嵌套 |

## LaTeX 编译链

```
paper/main.tex
  |-- \input{sections/introduction.tex}
  |-- \input{sections/related-work.tex}
  |-- \input{sections/method.tex}
  |-- \input{sections/experiments.tex}
  |-- \input{sections/conclusion.tex}
  |-- \bibliography{bib/references}
  `-- \input{sections/appendix.tex}
       |
       v
  latexmk (latexmkrc: $pdf_mode=5, out_dir=build)
       |
       v
  paper/build/main.pdf
```

latexmkrc 配置：
- `$pdf_mode = 5` -- 使用 XeLaTeX
- `$out_dir = 'build'` / `$aux_dir = 'build'` -- 隔离编译产物
- `$max_repeat = 5` -- 最大编译迭代次数
- `-file-line-error -interaction=nonstopmode -synctex=1` -- 编译选项

## 关键约束备忘

- TeX Live 未安装时，LaTeX 编译链不可用（validate_env.py 将其标记为 optional/blocked）
- make 未安装，构建脚本使用 bash 替代（`build.sh`）
- Dify 原生 MCP 暴露应用级接口，需自定义桥接服务器精细控制检索参数
- tikzplotlib 已废弃，必须用 matplotlib pgf 后端替代
- vibewriting(F:) 与 paper-search(C:) 在不同磁盘，保持独立项目
- CLAUDE.md 渐进式披露，不超过 300 行
- LaTeX 每句独占一行，便于 git diff
- 编译产物隔离：正确的 PDF 始终在 `paper/build/main.pdf`（`paper/.gitignore` 防止直接 xelatex 残留）
- `.env` 仅保留敏感凭据和 env-only 字段，管线配置统一由 `paper_config.yaml` 管理
