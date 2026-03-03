# vibewriting - LLM 文档索引

基于 Claude Code 与 Dify 知识库的科研论文自动化写作系统。

**项目状态**: Phase 7 已完成（端到端集成，874 tests）| Phase 1-6 已完成 | 路线图 v4 全部阶段已交付 + Bug 修复与配置统一 + Bug Fix Round 2 + Bug Fix Round 3（见 `openspec/ROADMAP.md`）

## 快速导航

### overview/ - 项目概览（必读）

| 文档 | 内容 | 何时阅读 |
|------|------|---------|
| [architecture.md](overview/architecture.md) | 三层架构设计、技术栈决策、七阶段工作流、契约体系、设计原则 | 理解系统整体设计 |
| [project-status.md](overview/project-status.md) | 当前环境状态、已完成里程碑、路线图概览、下一步行动 | 了解项目进展和待办 |

### guides/ - 操作指南

| 文档 | 内容 | 何时阅读 |
|------|------|---------|
| [development.md](guides/development.md) | 开发环境搭建、构建流程、验证命令 | 开始开发前 |
| [mcp-integration.md](guides/mcp-integration.md) | MCP 服务器配置、工具调用方法、调试技巧 | 使用文献检索或知识库时 |
| [roadmap-guide.md](guides/roadmap-guide.md) | ROADMAP.md 导读、阶段速查、契约体系、设计原则索引 | 了解整体规划或开始新阶段时 |

### architecture/ - 系统架构详情

| 文档 | 内容 | 何时阅读 |
|------|------|---------|
| [directory-map.md](architecture/directory-map.md) | 完整目录结构、每个文件/目录的用途和来源 | 查找文件位置或理解项目布局 |

### reference/ - 参考资料

| 文档 | 内容 | 何时阅读 |
|------|------|---------|
| [tech-decisions.md](reference/tech-decisions.md) | 25 项技术决策（D1-D25）速查表、约束备忘、依赖列表 | 需要理解"为什么这样做"时 |

## 源文件索引

### 核心配置文件

| 文件 | 路径 | 说明 |
|------|------|------|
| CLAUDE.md | `CLAUDE.md` | Claude Code 项目配置（90 行，5 核心要素） |
| ROADMAP.md | `openspec/ROADMAP.md` | 总体路线图 v4（617 行，Phase 2-7 规划 + 9 设计原则 + 契约体系） |
| pyproject.toml | `pyproject.toml` | Python 包定义，uv + hatchling，src 布局 |
| uv.lock | `uv.lock` | 依赖锁文件，保证科研可复现性 |
| .mcp.json | `.mcp.json` | MCP 服务器配置：paper-search(stdio) + dify-knowledge(bridge) |
| .env.example | `.env.example` | 环境变量模板（仅敏感凭据 + env-only 字段，管线配置已迁移到 paper_config.yaml） |
| build.sh | `build.sh` | 构建脚本（build/watch/clean/check/doi2bib） |
| paper_config.yaml | `paper_config.yaml` | 非敏感配置统一入口（论文配置 + 管线参数，双配置系统） |

### Python 源码 -- 端到端集成（Phase 7）

| 文件 | 路径 | 说明 |
|------|------|------|
| config_paper.py | `src/vibewriting/config_paper.py` | PaperConfig（论文配置 Pydantic 模型，natbib_style=unsrtnat + 4 个管线字段）+ load/merge/save_paper_config，YAML 序列化 |
| checkpoint.py | `src/vibewriting/checkpoint.py` | PhaseStatus(Enum) + PhaseRecord + Checkpoint 检查点模型；detect/save/create/update_phase/get_resume_phase/should_skip_phase/validate |
| metrics.py | `src/vibewriting/metrics.py` | LiteratureMetrics + WritingMetrics + CompilationMetrics + RunMetricsReport；collect_*/build_run_metrics/save_run_metrics |

### Python 源码 -- 核心与配置

| 文件 | 路径 | 说明 |
|------|------|------|
| config.py | `src/vibewriting/config.py` | pydantic-settings 配置管理，`VW_` env 前缀 + `apply_paper_config()` 桥接函数 |
| __init__.py | `src/vibewriting/__init__.py` | 包入口，定义版本号 |
| validate_env.py | `scripts/validate_env.py` | 环境验证脚本：彩色输出 + JSON 报告，分级退出码 0/1/2 |
| server.py | `scripts/dify-kb-mcp/server.py` | Dify 知识库 MCP 桥接服务器：FastMCP，256 行，python-dotenv .env 自动加载 + `_resolve_env()` 字面量过滤 + 环境变量回退链 |

### Python 源码 -- 数据模型（Phase 2 + Phase 4）

| 文件 | 路径 | 说明 |
|------|------|------|
| base.py | `src/vibewriting/models/base.py` | BaseEntity（审计字段）+ AssetBase（资产基类，ASSET-YYYY-NNN ID 模式） |
| paper.py | `src/vibewriting/models/paper.py` | Paper 模型 |
| experiment.py | `src/vibewriting/models/experiment.py` | Experiment 模型 |
| figure.py | `src/vibewriting/models/figure.py` | Figure 模型 |
| table.py | `src/vibewriting/models/table.py` | Table 模型 |
| section.py | `src/vibewriting/models/section.py` | Section 模型 |
| paper_state.py | `src/vibewriting/models/paper_state.py` | PaperState, SectionState, PaperMetrics（论文全局状态机）[Phase 4] |
| glossary.py | `src/vibewriting/models/glossary.py` | Glossary, SymbolTable, GlossaryEntry, SymbolEntry（术语表 + 符号表）[Phase 4] |

### Python 源码 -- 契约系统（Phase 2 + Phase 4）

| 文件 | 路径 | 说明 |
|------|------|------|
| schema_export.py | `src/vibewriting/contracts/schema_export.py` | Pydantic -> JSON Schema 导出（含 PaperState, Glossary, SymbolTable）[Phase 4 更新] |
| validator.py | `src/vibewriting/contracts/validator.py` | 自愈验证循环（jsonschema -> regex healer -> LLM healer，最多 3 轮） |
| integrity.py | `src/vibewriting/contracts/integrity.py` | 引用完整性验证（claim_id/asset_id/citation_key 交叉检查 + glossary/symbol integrity）[Phase 5 增强] |
| regex_healer.py | `src/vibewriting/contracts/healers/regex_healer.py` | 正则表达式修复器 |
| llm_healer.py | `src/vibewriting/contracts/healers/llm_healer.py` | LLM 回退修复器 |

### Python 源码 -- LaTeX 编译工具（Phase 6）

| 文件 | 路径 | 说明 |
|------|------|------|
| __init__.py | `src/vibewriting/latex/__init__.py` | 模块导出（compile_full, run_self_heal_loop, write_patch_reports, ErrorKind, LatexError, classify_error, parse_log, PatchProposal） |
| log_parser.py | `src/vibewriting/latex/log_parser.py` | LaTeX 日志解析器（ErrorKind 枚举, LatexError 数据类, parse_log, classify_error, extract_error_context） |
| patch_guard.py | `src/vibewriting/latex/patch_guard.py` | Patch 安全护栏（PatchProposal, validate_patch_target, validate_patch_scope, enforce_single_file, apply_patch 原子写入） |
| compiler.py | `src/vibewriting/latex/compiler.py` | 自愈编译器（compile_full, route_error, run_self_heal_loop 编译-解析-分类-路由-stash-patch-重试循环, write_patch_reports） |
| cli.py | `src/vibewriting/latex/cli.py` | Phase 6 Typer CLI（4 步管线：compile-heal -> citation-audit -> contract-audit -> peer-review，输出 phase6_report.json） |

### Python 源码 -- 审查模块（Phase 6）

| 文件 | 路径 | 说明 |
|------|------|------|
| __init__.py | `src/vibewriting/review/__init__.py` | 模块导出 |
| models.py | `src/vibewriting/review/models.py` | 审查数据模型（ReviewSeverity, ReviewCategory 枚举, ReviewFinding, PeerReviewReport, CitationAuditResult, PatchReport, Phase6Report） |
| citation_audit.py | `src/vibewriting/review/citation_audit.py` | 引文交叉审计（extract_all_cite_keys, crosscheck_with_evidence_cards, verify_crossref, run_checkcites, run_citation_audit） |
| peer_review.py | `src/vibewriting/review/peer_review.py` | 模拟同行评审（review_structure, review_evidence, review_methodology, generate_review_report, render_review_markdown, save_review_reports） |
| typography.py | `src/vibewriting/review/typography.py` | 排版检查（check_overfull_hbox, check_float_placement, check_widow_orphan, run_chktex, run_typography_check） |
| disclosure.py | `src/vibewriting/review/disclosure.py` | AI 使用声明（DisclosureConfig, EN/ZH 模板, generate_disclosure_text, inject_disclosure） |
| anonymize.py | `src/vibewriting/review/anonymize.py` | 匿名化处理（anonymize_tex 复制+替换, check_anonymization 检测自引/机构/URL） |

### Python 源码 -- 全量契约验证（Phase 6）

| 文件 | 路径 | 说明 |
|------|------|------|
| full_integrity.py | `src/vibewriting/contracts/full_integrity.py` | 全量契约验证（validate_all_tex_citations, validate_asset_hashes SHA256, validate_sections_complete, validate_glossary_in_tex, validate_symbols_in_tex, validate_end_to_end） |

### Python 源码 -- 写作模块（Phase 4 + Phase 5 增强）

| 文件 | 路径 | 说明 |
|------|------|------|
| quality_gates.py | `src/vibewriting/writing/quality_gates.py` | 5 种质量门禁 + 增强术语一致性检测（幽灵/未定义/跨章节）[Phase 5 增强] |
| state_manager.py | `src/vibewriting/writing/state_manager.py` | PaperStateManager（不可变模式 + 原子写入 + update_section_payload/batch_update_sections）[Phase 5 增强] |
| outline.py | `src/vibewriting/writing/outline.py` | 大纲生成工具（build_default_outline, outline_to_paper_state） |
| latex_helpers.py | `src/vibewriting/writing/latex_helpers.py` | CLAIM_ID 注释管理、引用格式化、LaTeX 解析 |
| incremental.py | `src/vibewriting/writing/incremental.py` | 增量编译（draft_main.tex 单章节编译，支持 natbib_style 参数） |

### Python 源码 -- 多 Agent 编排模块（Phase 5）

| 文件 | 路径 | 说明 |
|------|------|------|
| __init__.py | `src/vibewriting/agents/__init__.py` | 模块公共 API 导出（15 个公共符号） |
| contracts.py | `src/vibewriting/agents/contracts.py` | Agent 通信契约（10 个 Pydantic 模型：AgentRole, SectionTask, SectionPatchPayload, CriticIssue, CriticReport, FormatterPatch, MergeConflict, MergeDecision, OrchestrationRound, OrchestrationReport） |
| planner.py | `src/vibewriting/agents/planner.py` | 章节任务规划器（build_section_task_graph, get_ready_tasks, assign_roles，基于 PaperState 构建依赖图） |
| merge_protocol.py | `src/vibewriting/agents/merge_protocol.py` | 合并协议（validate_patch_payload, detect_conflicts, resolve_conflicts, apply_merge，三类冲突：术语/符号/引用） |
| executor.py | `src/vibewriting/agents/executor.py` | Agent 执行抽象（AgentExecutor Protocol, MockExecutor, SubAgentExecutor placeholder） |
| orchestrator.py | `src/vibewriting/agents/orchestrator.py` | 编排核心（OrchestratorConfig, WritingOrchestrator，多轮依赖层调度 + asyncio 并发） |
| git_safety.py | `src/vibewriting/agents/git_safety.py` | Git 安全网（create_snapshot_commit, rollback_to_snapshot + stash_before_patch, rollback_stash, drop_stash, list_stashes，管辖 paper/ + output/）[Phase 6 增强] |

### Python 源码 -- 数据处理（Phase 2）

| 文件 | 路径 | 说明 |
|------|------|------|
| cleaners.py | `src/vibewriting/processing/cleaners.py` | CSV 读取 + 缺失值处理 |
| transformers.py | `src/vibewriting/processing/transformers.py` | 数据聚合与转换 |
| statistics.py | `src/vibewriting/processing/statistics.py` | 描述统计计算 |

### Python 源码 -- 可视化（Phase 2）

| 文件 | 路径 | 说明 |
|------|------|------|
| figures.py | `src/vibewriting/visualization/figures.py` | 折线图 / 柱状图生成（matplotlib） |
| tables.py | `src/vibewriting/visualization/tables.py` | LaTeX 表格生成（jinja2 booktabs 模板） |
| pgf_export.py | `src/vibewriting/visualization/pgf_export.py` | PGF 后端导出 |
| booktabs.tex.j2 | `src/vibewriting/visualization/templates/booktabs.tex.j2` | booktabs 表格 Jinja2 模板 |

### Python 源码 -- DAG 管线（Phase 2）

| 文件 | 路径 | 说明 |
|------|------|------|
| dag.py | `src/vibewriting/pipeline/dag.py` | DAGRunner（拓扑排序 + 环检测 + 顺序执行） |
| nodes.py | `src/vibewriting/pipeline/nodes.py` | 8 个管线节点（load -> clean -> transform -> stats -> figures/tables -> manifests -> validate） |
| cli.py | `src/vibewriting/pipeline/cli.py` | Typer CLI 入口（`uv run python -m vibewriting.pipeline.cli run`） |

### Python 源码 -- 文献整合（Phase 3）

| 文件 | 路径 | 说明 |
|------|------|------|
| evidence_card.py | `src/vibewriting/models/evidence_card.py` | EvidenceCard Pydantic 模型（16 字段，`^EC-\d{4}-\d{3}$` claim_id 格式） |
| models.py | `src/vibewriting/literature/models.py` | RawLiteratureRecord 内部数据模型（统一文献记录格式） |
| bib_manager.py | `src/vibewriting/literature/bib_manager.py` | BibTeX 管理（bibtexparser 2.x，解析/规范化/合并/写回，原子写入） |
| evidence.py | `src/vibewriting/literature/evidence.py` | Evidence Card 生成 + claim_id 单调递增管理（`EC-YYYY-NNN` 格式） |
| cache.py | `src/vibewriting/literature/cache.py` | 本地知识缓存（JSONL + 内存四级索引：claim_id, bib_key, tag, evidence_type） |
| dedup.py | `src/vibewriting/literature/dedup.py` | 三层去重管道（L1 主键 DOI>arXiv>PMID，L2 近似标题 Jaccard，L3 claim 级去重）+ `inventory_filtered_count`/`inventory_filtered_titles` 字段 |
| search.py | `src/vibewriting/literature/search.py` | MCP 编排器（paper-search + Dify 降级，SearchResult 容器）+ `inventory_path` 参数支持清单去重 |
| dify_inventory.py | `src/vibewriting/literature/dify_inventory.py` | Dify KB 文献清单管理（DifyDocEntry/DifyInventory 模型，sync_dify_inventory 异步分页同步，load_dify_inventory 加载，dedup_against_inventory DOI 精确+标题 Jaccard 近似去重）[Bug Fix Round 3] |

### Python 源码 -- 测试（Phase 2 + Phase 3 + Phase 4 + Phase 5 + Phase 6 + Phase 7 + Bug 修复 + Bug Fix Round 2）

| 文件 | 路径 | 说明 |
|------|------|------|
| test_models.py | `tests/test_models.py` | 模型测试（29 tests） |
| test_contracts.py | `tests/test_contracts.py` | 契约测试（22 tests）[Phase 5 增强] |
| test_processing.py | `tests/test_processing.py` | 数据处理测试（27 tests） |
| test_visualization.py | `tests/test_visualization.py` | 可视化测试（10 tests） |
| test_pipeline.py | `tests/test_pipeline.py` | 管线测试（10 tests） |
| test_golden.py | `tests/golden/test_golden.py` | 黄金文件测试（4 tests） |
| conftest.py | `tests/test_literature/conftest.py` | 文献模块 MCP Mock fixtures + 样本数据 |
| test_bib_manager.py | `tests/test_literature/test_bib_manager.py` | BibTeX 管理测试（16 tests） |
| test_evidence.py | `tests/test_literature/test_evidence.py` | Evidence Card 测试（12 tests） |
| test_cache.py | `tests/test_literature/test_cache.py` | 知识缓存测试（20 tests） |
| test_dedup.py | `tests/test_literature/test_dedup.py` | 去重管道测试（23 tests） |
| test_search.py | `tests/test_literature/test_search.py` | MCP 编排器测试（8 tests）[+2 Bug Fix Round 2] |
| test_paper_state.py | `tests/test_paper_state.py` | PaperState 状态机测试（25 tests）[Phase 4] |
| test_glossary_symbols.py | `tests/test_glossary_symbols.py` | 术语表 + 符号表测试（28 tests）[Phase 4] |
| test_writing/ | `tests/test_writing/` | 写作模块测试（206 tests，6 文件 + conftest.py）[Phase 4, Phase 5 增强] |
| test_agents/ | `tests/test_agents/` | 多 Agent 编排测试（8 文件：conftest + contracts + planner + merge_protocol + executor + orchestrator + git_safety）[Phase 5] |
| test_latex/ | `tests/test_latex/` | LaTeX 编译工具测试（conftest + test_log_parser 16t + test_patch_guard 12t + test_compiler 11t）[Phase 6 + +2 Bug Fix Round 2] |
| test_review/ | `tests/test_review/` | 审查模块测试（conftest + test_models 9t + test_citation_audit 9t + test_peer_review 9t）[Phase 6] |
| test_full_integrity.py | `tests/test_contracts/test_full_integrity.py` | 全量契约验证测试（11 tests）[Phase 6] |
| test_regex_healer.py | `tests/test_contracts/test_regex_healer.py` | regex_healer 模块测试（12 tests）[Bug Fix Round 2] |
| test_config_paper.py | `tests/test_config_paper.py` | 论文配置测试（46 + 4 管线字段默认值 + 6 apply_paper_config 测试）[Phase 7 + Post] |
| test_checkpoint.py | `tests/test_checkpoint.py` | 检查点测试（39 tests）[Phase 7] |
| test_metrics.py | `tests/test_metrics.py` | 指标汇总测试（22 tests）[Phase 7] |

### LaTeX 论文模板

| 文件 | 路径 | 说明 |
|------|------|------|
| main.tex | `paper/main.tex` | ctexart 主文档，\input 章节组织 |
| latexmkrc | `paper/latexmkrc` | latexmk 配置（$pdf_mode=5, out_dir=build） |
| .gitignore | `paper/.gitignore` | 防止直接 xelatex 编译残留（正确产物在 build/） |
| references.bib | `paper/bib/references.bib` | 参考文献数据库 |
| sections/*.tex | `paper/sections/` | 6 个章节模板文件 |

### Claude Code 配置

| 文件 | 路径 | 说明 |
|------|------|------|
| settings.local.json | `.claude/settings.local.json` | 本地设置，授权 paper-search 外部目录访问 |
| vibewriting-literature | `.claude/skills/vibewriting-literature/SKILL.md` | 文献检索工作流 Skill |
| vibewriting-kb | `.claude/skills/vibewriting-kb/SKILL.md` | Dify 知识库检索 Skill |
| vibewriting-cite-check | `.claude/skills/vibewriting-cite-check/SKILL.md` | 引用完整性验证 Skill |
| vibewriting-draft | `.claude/skills/vibewriting-draft/SKILL.md` | Evidence-First 草稿撰写工作流 Skill [Phase 4] |
| vibewriting-orchestrate | `.claude/skills/vibewriting-orchestrate/SKILL.md` | 多 Agent 编排写作工作流 Skill [Phase 5] |
| vibewriting-review | `.claude/skills/vibewriting-review/SKILL.md` | 论文质量审查工作流 Skill（编译验证 -> 引文审计 -> 契约一致性 -> 模拟同行评审 -> Approval Gate）[Phase 6] |
| vibewriting-paper | `.claude/skills/vibewriting-paper/SKILL.md` | 端到端一键写作工作流 Skill（9 步工作流 + 5 个 Approval Gates，配置加载 -> 检查点 -> 环境验证 -> 数据管线 -> 文献检索 -> 草稿撰写 -> 多 Agent 编排 -> 编译审查 -> 指标汇总）[Phase 7] |

### OPSX 归档

| 文件 | 路径 | 说明 |
|------|------|------|
| Phase 1 归档 | `openspec/changes/archive/2026-02-23-project-foundation-architecture/` | proposal + design + tasks（52 项全部完成） |
| Phase 2 归档 | `openspec/changes/archive/2026-02-23-phase-2-data-models-pipeline/` | 数据模型 + 契约 + 管线（102 tests，91% 覆盖率） |
| Phase 3 变更 | `openspec/changes/phase-3-literature-integration/` | 文献整合工作流（proposal + design + tasks） |
| specs/ | `openspec/specs/` | 6 个已合并规格模块 |

## 关于本文档系统

- 面向 LLM 阅读优化，保持结构化和简洁
- 使用简体中文
- 遵循 llmdoc 标准目录结构（index / overview / guides / architecture / reference）
- 文档更新应与代码变更同步
