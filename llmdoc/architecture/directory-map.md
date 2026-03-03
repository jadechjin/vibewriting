# 目录结构地图

**最后更新**: 2026-03-03
**来源**: Post-Phase 7 (bug fixes & config unification) 变更后的实际文件系统

## 完整目录树

```
F:/vibewriting/
|
|-- CLAUDE.md                          # Claude Code 项目配置
|-- pyproject.toml                     # Python 包定义（hatchling + src 布局，>=3.12）
|-- uv.lock                            # 依赖锁文件（提交 Git，D3 决策）
|-- .env.example                       # 环境变量模板（仅敏感凭据 + env-only 字段，管线配置已迁移到 paper_config.yaml）
|-- .gitignore                         # LaTeX + Python + .venv 忽略规则
|-- .gitattributes                     # Git 属性配置
|-- build.sh                           # 构建脚本（build/watch/clean/check/doi2bib）
|-- origin.md                          # 系统设计文档（完整架构蓝图，约 24KB）
|-- paper_config.yaml                  # 非敏感配置统一入口（论文配置 + 管线参数，双配置系统）[Phase 7 + Post]
|-- .mcp.json                          # MCP 服务器配置（paper-search + dify-knowledge）
|
|-- paper/                             # LaTeX 论文源码
|   |-- main.tex                       #   ctexart 主文档（\input 章节组织）
|   |-- latexmkrc                      #   latexmk 配置（$pdf_mode=5, out_dir=build）
|   |-- .gitignore                     #   防止直接 xelatex 编译残留（正确产物在 build/）
|   |-- sections/                      #   章节文件
|   |   |-- introduction.tex           #     引言
|   |   |-- related-work.tex           #     相关工作
|   |   |-- method.tex                 #     方法
|   |   |-- experiments.tex            #     实验
|   |   |-- conclusion.tex             #     结论
|   |   `-- appendix.tex               #     附录
|   |-- bib/                           #   参考文献
|   |   `-- references.bib             #     BibTeX 数据库
|   |-- figures/                       #   图片资源（手动放置）
|   `-- build/                         #   编译输出（gitignored）
|
|-- src/vibewriting/                   # Python 源码（src 布局）
|   |-- __init__.py                    #   包入口，版本号 "0.1.0"
|   |-- config.py                      #   pydantic-settings 配置（VW_ env 前缀）+ apply_paper_config() 桥接函数
|   |-- config_paper.py                #   PaperConfig 论文配置模型（natbib_style=unsrtnat + 4 个管线字段，YAML 序列化）[Phase 7 + Post]
|   |-- checkpoint.py                  #   Checkpoint 检查点模型（PhaseStatus/PhaseRecord）[Phase 7]
|   |-- metrics.py                     #   RunMetricsReport 指标聚合（Literature/Writing/Compilation metrics）[Phase 7]
|   |
|   |-- models/                        #   Pydantic 数据模型 [Phase 2 + Phase 3 + Phase 4]
|   |   |-- __init__.py                #     公共 API: BaseEntity, AssetBase, Paper, Experiment, Figure, Table, Section, EvidenceCard, PaperState, Glossary, SymbolTable
|   |   |-- base.py                    #     BaseEntity（审计字段）+ AssetBase（资产基类）
|   |   |-- paper.py                   #     Paper 模型
|   |   |-- experiment.py              #     Experiment 模型
|   |   |-- figure.py                  #     Figure 模型
|   |   |-- table.py                   #     Table 模型
|   |   |-- section.py                 #     Section 模型
|   |   |-- evidence_card.py           #     EvidenceCard 模型（16 字段，EC-YYYY-NNN claim_id）[Phase 3]
|   |   |-- paper_state.py             #     PaperState, SectionState, PaperMetrics（论文全局状态机）[Phase 4]
|   |   `-- glossary.py                #     Glossary, SymbolTable, GlossaryEntry, SymbolEntry（术语 + 符号表）[Phase 4]
|   |
|   |-- contracts/                     #   契约系统 [Phase 2 + Phase 4]
|   |   |-- __init__.py
|   |   |-- schema_export.py           #     Pydantic -> JSON Schema 导出（含 PaperState/Glossary/SymbolTable）[Phase 4 更新]
|   |   |-- validator.py               #     自愈验证循环（jsonschema + healers，最多 3 轮）
|   |   |-- integrity.py               #     引用完整性验证（claim_id/asset_id/citation_key）
|   |   |-- healers/                   #     修复器
|   |   |   |-- __init__.py
|   |   |   |-- regex_healer.py        #       正则表达式修复
|   |   |   `-- llm_healer.py          #       LLM 回退修复
|   |   `-- schemas/                   #     JSON Schema 文件（由 schema_export 生成）
|   |       |-- paperstate.schema.json #       PaperState Schema [Phase 4]
|   |       |-- glossary.schema.json   #       Glossary Schema [Phase 4]
|   |       `-- symboltable.schema.json #      SymbolTable Schema [Phase 4]
|   |
|   |-- processing/                    #   数据处理管道 [Phase 2]
|   |   |-- __init__.py
|   |   |-- cleaners.py                #     CSV 读取 + 缺失值处理
|   |   |-- transformers.py            #     数据聚合与转换
|   |   `-- statistics.py              #     描述统计计算
|   |
|   |-- visualization/                 #   可视化生成 [Phase 2]
|   |   |-- __init__.py
|   |   |-- figures.py                 #     折线图 / 柱状图（matplotlib）
|   |   |-- tables.py                  #     LaTeX 表格（jinja2 + booktabs）
|   |   |-- pgf_export.py              #     PGF 后端导出
|   |   `-- templates/
|   |       `-- booktabs.tex.j2        #     booktabs 表格 Jinja2 模板
|   |
|   |-- pipeline/                      #   DAG 管线 [Phase 2]
|   |   |-- __init__.py
|   |   |-- dag.py                     #     DAGRunner（拓扑排序 + 环检测）
|   |   |-- nodes.py                   #     8 个管线节点定义
|   |   `-- cli.py                     #     Typer CLI 入口
|   |
|   |-- literature/                    #   文献整合 [Phase 3]
|   |   |-- __init__.py
|   |   |-- models.py                  #     RawLiteratureRecord 统一文献记录格式
|   |   |-- bib_manager.py            #     BibTeX 管理（bibtexparser 2.x，原子写入）
|   |   |-- evidence.py               #     Evidence Card 生成 + claim_id 管理
|   |   |-- cache.py                   #     JSONL 知识缓存 + 内存四级索引
|   |   |-- dedup.py                   #     三层去重管道（L1 主键/L2 标题 Jaccard/L3 claim）+ inventory 统计字段
|   |   |-- dify_inventory.py          #     Dify KB 文献清单管理（sync/load/dedup_against_inventory）[Bug Fix Round 3]
|   |   `-- search.py                  #     MCP 编排器（paper-search + Dify 降级 + 清单去重集成）
|   |
|   |-- writing/                       #   草稿撰写模块 [Phase 4, Phase 5 增强]
|   |   |-- __init__.py
|   |   |-- quality_gates.py           #     5 种质量门禁 + 增强术语一致性检测（幽灵/未定义/跨章节）[Phase 5 增强]
|   |   |-- state_manager.py           #     PaperStateManager（不可变模式 + 原子写入 + update_section_payload/batch_update_sections）[Phase 5 增强]
|   |   |-- outline.py                 #     大纲生成（build_default_outline, outline_to_paper_state）
|   |   |-- latex_helpers.py           #     CLAIM_ID 注释管理、引用格式化、LaTeX 解析
|   |   `-- incremental.py             #     增量编译（draft_main.tex 单章节编译，支持 natbib_style 参数）
|   |
|   |-- agents/                        #   多 Agent 编排模块 [Phase 5]
|   |   |-- __init__.py                #     模块公共 API 导出（15 个公共符号）
|   |   |-- contracts.py               #     Agent 通信契约（10 个 Pydantic 模型：AgentRole, SectionTask, SectionPatchPayload, CriticIssue, CriticReport, FormatterPatch, MergeConflict, MergeDecision, OrchestrationRound, OrchestrationReport）
|   |   |-- planner.py                 #     章节任务规划器（build_section_task_graph, get_ready_tasks, assign_roles）
|   |   |-- merge_protocol.py          #     合并协议（validate_patch_payload, detect_conflicts, resolve_conflicts, apply_merge）
|   |   |-- executor.py                #     Agent 执行抽象（AgentExecutor Protocol, MockExecutor, SubAgentExecutor placeholder）
|   |   |-- orchestrator.py            #     编排核心（OrchestratorConfig, WritingOrchestrator，多轮依赖层 + asyncio 并发）
|   |   `-- git_safety.py              #     Git 安全网（snapshot + rollback + stash_before_patch/rollback_stash/drop_stash/list_stashes）[Phase 6 增强]
|   |
|   |-- latex/                         #   LaTeX 编译工具 [Phase 6]
|   |   |-- __init__.py                #     模块导出（compile_full, run_self_heal_loop, write_patch_reports, ErrorKind, LatexError, classify_error, parse_log, PatchProposal）
|   |   |-- log_parser.py              #     LaTeX 日志解析器（ErrorKind 枚举, LatexError 数据类, parse_log, classify_error, extract_error_context）
|   |   |-- patch_guard.py             #     Patch 安全护栏（PatchProposal, validate_patch_target, validate_patch_scope, enforce_single_file, apply_patch 原子写入）
|   |   |-- compiler.py                #     自愈编译器（compile_full, route_error, run_self_heal_loop 编译-解析-分类-路由-stash-patch-重试循环, write_patch_reports）
|   |   `-- cli.py                     #     Phase 6 Typer CLI（4 步管线：compile-heal -> citation-audit -> contract-audit -> peer-review，输出 phase6_report.json）
|   |
|   `-- review/                        #   审查模块 [Phase 6]
|       |-- __init__.py                #     模块导出
|       |-- models.py                  #     审查数据模型（ReviewSeverity, ReviewCategory 枚举, ReviewFinding, PeerReviewReport, CitationAuditResult, PatchReport, Phase6Report）
|       |-- citation_audit.py          #     引文交叉审计（extract_all_cite_keys, crosscheck_with_evidence_cards, verify_crossref, run_checkcites, run_citation_audit）
|       |-- peer_review.py             #     模拟同行评审（review_structure, review_evidence, review_methodology, generate_review_report, render_review_markdown, save_review_reports）
|       |-- typography.py              #     排版检查（check_overfull_hbox, check_float_placement, check_widow_orphan, run_chktex, run_typography_check）
|       |-- disclosure.py              #     AI 使用声明（DisclosureConfig, EN/ZH 模板, generate_disclosure_text, inject_disclosure）
|       `-- anonymize.py               #     匿名化处理（anonymize_tex 复制+替换, check_anonymization 检测自引/机构/URL）
|
|-- data/                              # 数据资产
|   |-- raw/                           #   原始数据（大文件 gitignored）
|   |-- processed/                     #   清洗后数据
|   |   `-- literature/                #   文献证据卡存储 [Phase 3]
|   |       |-- literature_cards.jsonl #     JSONL 格式证据卡集合
|   |       `-- dify_kb_inventory.json #     Dify KB 文献清单 JSON（运行时生成）[Bug Fix Round 3]
|   `-- cache/                         #   文献分析缓存
|
|-- output/                            # 生成资产（管线输出目标）
|   |-- figures/                       #   图表输出（.pdf/.pgf/.png）
|   |-- tables/                        #   LaTeX 表格输出（.tex）
|   |-- assets/                        #   其他 LaTeX 资产
|   |-- asset_manifest.json            #   资产清单（管线生成）
|   `-- run_manifest.json              #   运行清单（管线生成）
|
|-- scripts/                           # 工具脚本
|   |-- validate_env.py                #   环境验证（彩色输出 + JSON，退出码 0/1/2）
|   `-- dify-kb-mcp/                   #   Dify MCP 桥接服务器
|       `-- server.py                  #     FastMCP 服务器（204 行，PEP 723）
|
|-- tests/                             # 测试目录（874 tests）
|   |-- conftest.py                    #   pytest 配置
|   |-- test_models.py                 #   模型测试（29 tests）
|   |-- test_contracts.py              #   契约测试（22 tests）[Phase 5 增强]
|   |-- test_processing.py             #   数据处理测试（27 tests）
|   |-- test_visualization.py          #   可视化测试（10 tests）
|   |-- test_pipeline.py               #   管线测试（10 tests）
|   |-- test_paper_state.py            #   PaperState 状态机测试（25 tests）[Phase 4]
|   |-- test_glossary_symbols.py       #   术语表 + 符号表测试（28 tests）[Phase 4]
|   |-- test_config_paper.py           #   论文配置测试（46 + 4 + 6 tests）[Phase 7 + Post]
|   |-- test_checkpoint.py             #   检查点测试（39 tests）[Phase 7]
|   |-- test_metrics.py                #   指标汇总测试（22 tests）[Phase 7]
|   |-- golden/                        #   黄金文件回归测试
|   |   |-- __init__.py
|   |   `-- test_golden.py             #     确定性输出验证（4 tests）
|   |-- test_literature/               #   文献模块测试 [Phase 3]（100 tests）
|   |   |-- __init__.py
|   |   |-- conftest.py                #     MCP Mock fixtures + 样本数据
|   |   |-- test_bib_manager.py        #     BibTeX 管理测试（16 tests）
|   |   |-- test_evidence.py           #     Evidence Card 测试（12 tests）
|   |   |-- test_cache.py              #     知识缓存测试（20 tests）
|   |   |-- test_dedup.py              #     去重管道测试（23 tests）
|   |   |-- test_dify_inventory.py     #     Dify KB 清单去重测试（23 tests）[Bug Fix Round 3]
|   |   `-- test_search.py             #     MCP 编排器测试（6 tests）
|   |-- test_writing/                  #   写作模块测试 [Phase 4]（206 tests）
|   |   |-- __init__.py
|   |   |-- conftest.py                #     写作模块 fixtures
|   |   |-- test_quality_gates.py      #     质量门禁测试 [Phase 5 增强]
|   |   |-- test_state_manager.py      #     状态管理器测试
|   |   |-- test_outline.py            #     大纲生成测试
|   |   |-- test_latex_helpers.py      #     LaTeX 辅助工具测试
|   |   `-- test_incremental.py        #     增量编译测试
|   |-- test_agents/                   #   多 Agent 编排测试 [Phase 5]
|   |   |-- __init__.py
|   |   |-- conftest.py                #     Agent 模块共享 fixtures
|   |   |-- test_contracts.py          #     Agent 通信契约测试
|   |   |-- test_planner.py            #     任务规划器测试
|   |   |-- test_merge_protocol.py     #     合并协议测试
|   |   |-- test_executor.py           #     执行器测试
|   |   |-- test_orchestrator.py       #     编排器测试
|   |   `-- test_git_safety.py         #     Git 安全网测试
|   |-- test_latex/                    #   LaTeX 编译工具测试 [Phase 6]（37 tests）
|   |   |-- conftest.py                #     tmp_paper_dir fixture
|   |   |-- test_log_parser.py         #     日志解析器测试（16 tests）
|   |   |-- test_patch_guard.py        #     Patch 护栏测试（12 tests）
|   |   `-- test_compiler.py           #     自愈编译器测试（9 tests）
|   |-- test_review/                   #   审查模块测试 [Phase 6]（27 tests）
|   |   |-- conftest.py                #     tmp_paper_dir + cards_path fixtures
|   |   |-- test_models.py             #     审查数据模型测试（9 tests）
|   |   |-- test_citation_audit.py     #     引文审计测试（9 tests）
|   |   `-- test_peer_review.py        #     同行评审测试（9 tests）
|   `-- test_contracts/                #   契约模块测试 [Phase 6]
|       `-- test_full_integrity.py     #     全量契约验证测试（11 tests）
|
|-- .claude/                           # Claude Code 本地配置
|   |-- settings.local.json            #   本地设置（additionalDirectories）
|   `-- skills/                        #   自定义 Skills
|       |-- vibewriting-literature/    #     文献检索工作流
|       |   `-- SKILL.md
|       |-- vibewriting-kb/              #     知识库检索
|       |   `-- SKILL.md
|       |-- vibewriting-cite-check/      #     引用验证
|       |   `-- SKILL.md
|       |-- vibewriting-draft/           #     Evidence-First 草稿撰写 [Phase 4]
|       |   `-- SKILL.md
|       |-- vibewriting-orchestrate/     #     多 Agent 编排写作 [Phase 5]
|       |   `-- SKILL.md
|       |-- vibewriting-review/          #     论文质量审查 [Phase 6]
|       |   `-- SKILL.md
|       `-- vibewriting-paper/           #     端到端一键写作主入口 [Phase 7]
|           `-- SKILL.md
|
|-- openspec/                          # OPSX 变更管理
|   |-- ROADMAP.md                     #   总体路线图 v4（617 行，Phase 2-7 规划）
|   |-- changes/
|   |   |-- phase-3-literature-integration/
|   |   |   |-- .openspec.yaml        #   Phase 3 OPSX 元数据
|   |   |   |-- proposal.md           #   Phase 3 变更提案
|   |   |   |-- design.md             #   技术设计
|   |   |   `-- tasks.md              #   任务清单
|   |   `-- archive/
|   |       |-- 2026-02-23-project-foundation-architecture/
|   |       |   |-- proposal.md        #   Phase 1 变更提案
|   |       |   |-- design.md          #   技术设计（9 决策 D1-D9）
|   |       |   |-- tasks.md           #   任务清单（52 项，全部完成）
|   |       |   `-- specs/             #   6 个规格模块（已合并）
|   |       `-- 2026-02-23-phase-2-data-models-pipeline/
|   |           `-- ...                #   Phase 2 归档（102 tests，91% 覆盖率）
|   `-- specs/                         #   已合并的规格
|       |-- claude-config/
|       |-- env-validation/
|       |-- latex-compilation/
|       |-- mcp-integration/
|       |-- project-scaffold/
|       `-- python-environment/
|
`-- llmdoc/                            # LLM 文档系统
    |-- index.md                       #   文档索引（本系统入口）
    |-- overview/                      #   项目概览
    |-- guides/                        #   操作指南
    |-- architecture/                  #   架构详情
    `-- reference/                     #   参考资料

docs/                                  # 用户文档 [Phase 7]
    |-- quickstart.md                  #   快速开始指南
    |-- config-reference.md            #   配置参考手册
    |-- faq.md                         #   常见问题解答
    `-- cross-project-guide.md         #   跨项目迁移指南
```

## 目录职责与来源

| 目录 | 来自阶段 | 核心用途 | gitignored |
|------|---------|---------|------------|
| `paper/` | Phase 1 P3 | LaTeX 论文源码和编译 | `paper/build/` |
| `src/vibewriting/` | Phase 1 P0 + Phase 2 + Phase 3 + Phase 4 + Phase 5 + Phase 6 + Phase 7 | Python 业务逻辑（模型/契约/处理/可视化/管线/文献/写作/编排/编译/审查/集成） | `__pycache__/` |
| `src/vibewriting/models/` | Phase 2 + Phase 3 + Phase 4 | 9 个 Pydantic 实体模型（含 PaperState, Glossary, SymbolTable） | -- |
| `src/vibewriting/contracts/` | Phase 2 + Phase 4 + Phase 5 + Phase 6 | 契约验证 + 自愈 + 引用完整性（含 glossary/symbol integrity）+ Schema 导出 + 全量契约验证 | -- |
| `src/vibewriting/processing/` | Phase 2 | 数据清洗/转换/统计 | -- |
| `src/vibewriting/visualization/` | Phase 2 | 图表/表格生成 + PGF 导出 | -- |
| `src/vibewriting/pipeline/` | Phase 2 | DAG 管线编排 + CLI | -- |
| `src/vibewriting/literature/` | Phase 3 | 文献检索/去重/Evidence Card/BibTeX/缓存 | -- |
| `src/vibewriting/writing/` | Phase 4 + Phase 5 | 草稿撰写工作流（质量门禁/状态管理/大纲/LaTeX 工具/增量编译）[Phase 5 增强] | -- |
| `src/vibewriting/agents/` | Phase 5 + Phase 6 | 多 Agent 编排（通信契约/任务规划/合并协议/执行器/编排器/Git 安全网 + stash）[Phase 6 增强] | -- |
| `src/vibewriting/latex/` | Phase 6 | LaTeX 编译工具（日志解析/Patch 护栏/自愈编译器/CLI） | -- |
| `src/vibewriting/review/` | Phase 6 | 质量审查（引文审计/同行评审/排版检查/AI 披露/匿名化） | -- |
| `src/vibewriting/config_paper.py` | Phase 7 + Post | PaperConfig 论文配置模型（natbib_style=unsrtnat + 4 个管线字段，不可变合并） | -- |
| `src/vibewriting/checkpoint.py` | Phase 7 | Checkpoint 检查点（PhaseStatus/PhaseRecord，断点续跑） | -- |
| `src/vibewriting/metrics.py` | Phase 7 | RunMetricsReport 指标聚合（文献/写作/编译维度） | -- |
| `data/` | Phase 1 P0 | 数据资产存储 | `data/raw/*.csv` 等大文件 |
| `data/processed/literature/` | Phase 3 | 文献证据卡 JSONL 存储 | -- |
| `output/` | Phase 1 P0 + Phase 2 | 生成的图表、表格和清单文件 | 否 |
| `scripts/` | Phase 1 P2+P4 | 工具脚本 | 否 |
| `tests/` | Phase 1 P0 + Phase 2 + Phase 3 + Phase 4 + Phase 5 + Phase 6 + Phase 7 + Post | 测试代码（874 tests） | 否 |
| `.claude/` | Phase 1 P1 + Phase 4 + Phase 5 + Phase 6 + Phase 7 | Claude Code 配置（含 vibewriting-draft + vibewriting-orchestrate + vibewriting-review + vibewriting-paper Skill） | 否 |
| `openspec/` | OPSX | 变更管理归档 | 否 |
| `llmdoc/` | -- | LLM 文档系统 | 否 |

## 关键文件速查

| 需要做什么 | 看哪个文件 |
|-----------|-----------|
| 了解项目配置 | `CLAUDE.md` |
| 查看/修改依赖 | `pyproject.toml` |
| 配置环境变量 | `.env.example` -> `.env`（仅敏感凭据 VW_ 前缀）+ `paper_config.yaml`（管线参数） |
| 编写论文章节 | `paper/sections/*.tex` |
| 添加参考文献 | `paper/bib/references.bib` |
| 编译论文 | `build.sh` |
| 配置 MCP 服务器 | `.mcp.json` |
| 验证环境 | `scripts/validate_env.py` |
| 定义数据模型 | `src/vibewriting/models/` |
| 契约验证/自愈 | `src/vibewriting/contracts/validator.py` |
| 引用完整性检查 | `src/vibewriting/contracts/integrity.py` |
| 导出 JSON Schema | `uv run python -m vibewriting.contracts.schema_export` |
| 数据处理代码 | `src/vibewriting/processing/` |
| 图表生成代码 | `src/vibewriting/visualization/` |
| 运行数据管线 | `uv run python -m vibewriting.pipeline.cli run` |
| 文献检索与去重 | `src/vibewriting/literature/search.py` + `dedup.py` + `dify_inventory.py` |
| BibTeX 管理 | `src/vibewriting/literature/bib_manager.py` |
| Evidence Card 生成 | `src/vibewriting/literature/evidence.py` |
| 文献知识缓存 | `src/vibewriting/literature/cache.py` |
| 草稿撰写状态管理 | `src/vibewriting/writing/state_manager.py` |
| 质量门禁检查 | `src/vibewriting/writing/quality_gates.py` |
| 大纲生成 | `src/vibewriting/writing/outline.py` |
| LaTeX 增量编译 | `src/vibewriting/writing/incremental.py` |
| 多 Agent 编排 | `src/vibewriting/agents/orchestrator.py` |
| Agent 通信契约 | `src/vibewriting/agents/contracts.py` |
| 章节任务规划 | `src/vibewriting/agents/planner.py` |
| 合并冲突解决 | `src/vibewriting/agents/merge_protocol.py` |
| Agent 执行抽象 | `src/vibewriting/agents/executor.py` |
| Git 快照与回滚 | `src/vibewriting/agents/git_safety.py` |
| LaTeX 自愈编译 | `src/vibewriting/latex/compiler.py` |
| LaTeX 日志解析 | `src/vibewriting/latex/log_parser.py` |
| Patch 安全护栏 | `src/vibewriting/latex/patch_guard.py` |
| Phase 6 CLI 管线 | `src/vibewriting/latex/cli.py` |
| 引文交叉审计 | `src/vibewriting/review/citation_audit.py` |
| 模拟同行评审 | `src/vibewriting/review/peer_review.py` |
| 排版检查 | `src/vibewriting/review/typography.py` |
| AI 使用声明 | `src/vibewriting/review/disclosure.py` |
| 匿名化处理 | `src/vibewriting/review/anonymize.py` |
| 全量契约验证 | `src/vibewriting/contracts/full_integrity.py` |
| 论文配置加载/保存 | `src/vibewriting/config_paper.py` |
| 检查点管理 | `src/vibewriting/checkpoint.py` |
| 运行指标汇总 | `src/vibewriting/metrics.py` |
| 端到端写作一键启动 | `.claude/skills/vibewriting-paper/SKILL.md` |
| 运行测试 | `uv run pytest`（874 tests） |

## DAG 管线节点拓扑

```
load_data
   |
   v
clean_data
   |
   v
transform_data
   |
   +--------+--------+
   v                 v
compute_statistics   generate_figures
   |                      |
   v                      |
generate_tables           |
   |                      |
   +--------+-------------+
            v
      build_manifests
            |
            v
    validate_contracts
```

输入: `data/raw/*.csv`
输出: `output/figures/` + `output/tables/` + `output/asset_manifest.json` + `output/run_manifest.json`
