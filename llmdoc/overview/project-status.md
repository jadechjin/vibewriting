# 项目当前状态

**最后更新**: 2026-03-03
**阶段**: Phase 7 完成（端到端集成）-- 路线图 v4 全部 7 个阶段已交付 + Bug 修复与配置统一

### Phase 7: 端到端集成（已完成）

**107 新增 tests（总计 614 tests），全部通过**

| 模块 | 内容 | 测试数 | 状态 |
|------|------|--------|------|
| config_paper | PaperConfig Pydantic 模型 + load_paper_config/merge_config/save_paper_config（YAML 序列化，不可变合并，自动创建目录） | 46 | 已完成 |
| checkpoint | PhaseStatus(Enum), PhaseRecord, Checkpoint 检查点模型；detect/save/create/update_phase/get_resume_phase/should_skip_phase/validate | 39 | 已完成 |
| metrics | LiteratureMetrics, WritingMetrics, CompilationMetrics, RunMetricsReport；collect_*/build_run_metrics/save_run_metrics 指标聚合 | 22 | 已完成 |
| Skill: vibewriting-paper | 端到端主入口 Skill（9 步工作流 + 5 个 Approval Gates） | -- | 已完成 |
| docs/ | 用户文档（quickstart.md + config-reference.md + faq.md + cross-project-guide.md） | -- | 已完成 |

### Post-Phase 7: Bug 修复与配置统一（2026-03-03）

**全量测试从 614 增加到 835 passed**

| 修复项 | 内容 | 新增测试 | 状态 |
|--------|------|----------|------|
| .env 变量前缀修正 | Dify 凭据从 `DIFY_*` 修正为 `VW_DIFY_*`，`.mcp.json` 的 `${VW_DIFY_*}` 映射匹配 | -- | 已修复 |
| 编译产物清理 | 新增 `paper/.gitignore` 防止直接 xelatex 编译残留，正确 PDF 在 `paper/build/main.pdf` | -- | 已修复 |
| natbib_style 配置链统一 | `PaperConfig.natbib_style` 默认值改为 `unsrtnat`；`incremental.py` 新增 `natbib_style` 参数 | 1 (test_custom_natbib_style) | 已修复 |
| 配置统一（双配置系统） | `PaperConfig` 新增 4 个管线字段；`config.py` 新增 `apply_paper_config()` 桥接函数；`.env` 简化 | 6 (TestApplyPaperConfig) + 4 (管线字段默认值) | 已完成 |
| Dify MCP 环境变量传递修复 | server.py 新增 python-dotenv 自动加载 .env；环境变量回退链 `DIFY_*` -> `VW_DIFY_*`；API 路径去掉重复 `/v1` 前缀 | -- | 已修复 |
| `_resolve_env()` 插值字面量过滤 | server.py 新增 `_resolve_env()` 辅助函数，过滤 `${...}` 字面量（返回 None）修复回退链失效；`_check_credentials()` 增加 URL 协议前缀检查 | -- | 已修复 |

### Bug Fix Round 2（2026-03-03）

**全量测试从 835 增加到 851 passed**

| 修复项 | 内容 | 新增测试 | 状态 |
|--------|------|----------|------|
| 文献检索并行化 + Dify 优先 | `search_literature()` 改为 asyncio 并行，Dify 结果优先；`models.py` source Literal 扩展 `web-search` | 2 (test_orchestrator_prioritizes_dify + handles_dify_failure) | 已修复 |
| regex_healer 双反斜杠 bug | `fix_illegal_escapes()` 重写，双反斜杠 `\\` 作为原子单元处理，修复 `\\d` 被破坏的 bug | 12 (test_regex_healer.py 新建) | 已修复 |
| LaTeX BibTeX 不运行 | `latexmkrc` 添加 `$bibtex_use = 2`；`compiler.py` `compile_full()` 移除 `-halt-on-error` | 2 (no_halt_on_error + bibtex_use) | 已修复 |
| SKILL.md 检索优先级文档 | `vibewriting-literature` SKILL.md 更新为并行策略 + 禁止 WebSearch + 来源可信度说明 | -- | 已修复 |

### Bug Fix Round 3（2026-03-03）

**全量测试从 851 增加到 874 passed**

| 修复项 | 内容 | 新增测试 | 状态 |
|--------|------|----------|------|
| paper-search vs Dify KB 去重缺失 | 新增 `dify_inventory.py` 模块：`DifyDocEntry`/`DifyInventory` 模型 + `sync_dify_inventory()`（分页调 list_documents API 更新本地 JSON）+ `load_dify_inventory()` + `dedup_against_inventory()`（DOI 精确匹配 + 标题 Jaccard 近似匹配） | 23 (test_dify_inventory.py) | 已修复 |
| DeduplicationReport 扩展 | `dedup.py` `DeduplicationReport` 新增 `inventory_filtered_count` + `inventory_filtered_titles` 字段 | -- | 已修复 |
| search_literature() 集成清单去重 | `search.py` `search_literature()` 新增 `inventory_path` 参数，去重流程增加 Dify KB 清单对比步骤（sync -> dedup_against_inventory） | -- | 已修复 |

## 已完成的阶段

### Phase 1: 基础架构（已归档）

**52/52 任务全部完成，6 个 spec 已合并到 `openspec/specs/`**

| 子阶段 | 内容 | 任务数 | 状态 |
|--------|------|--------|------|
| P0 | 项目脚手架 + Git + Python + CLAUDE.md | 13 | 已完成 |
| P1 | MCP 配置 + paper-search 集成 + Skills | 7 | 已完成 |
| P2 | 环境验证脚本 v1 | 8 | 已完成 |
| P3 | LaTeX 模板 + 构建脚本 | 10 | 已完成 |
| P4 | Dify MCP 桥接服务器 | 7 | 已完成 |
| 最终验证 | 全量校验 | 7 | 已完成 |

### Phase 2: 数据模型 + 处理管线（已归档）

**102 tests，覆盖率 91%**

| 模块 | 内容 | 测试数 | 状态 |
|------|------|--------|------|
| models | 6 个 Pydantic 模型（BaseEntity, AssetBase, Paper, Experiment, Figure, Table, Section） | 29 | 已完成 |
| contracts | 契约系统（schema_export + validator 自愈循环 + integrity 引用完整性 + healers） | 22 | 已完成 |
| processing | 数据处理（cleaners + transformers + statistics） | 27 | 已完成 |
| visualization | 可视化（figures + tables + pgf_export + booktabs 模板） | 10 | 已完成 |
| pipeline | DAG 管线（dag + nodes + cli） | 10 | 已完成 |
| golden | 黄金文件回归测试 | 4 | 已完成 |

### Phase 3: 文献整合工作流（已完成）

**77 新增 tests（总计 177 tests），覆盖率 92%**

| 模块 | 内容 | 测试数 | 状态 |
|------|------|--------|------|
| evidence_card | EvidenceCard Pydantic 模型（16 字段，`EC-YYYY-NNN` claim_id） | -- | 已完成 |
| literature/models | RawLiteratureRecord 统一文献记录格式 | -- | 已完成 |
| literature/bib_manager | BibTeX 管理（bibtexparser 2.x，解析/规范化/合并/写回，原子写入） | 16 | 已完成 |
| literature/evidence | Evidence Card 生成 + claim_id 单调递增管理 | 12 | 已完成 |
| literature/cache | 本地知识缓存（JSONL + 内存四级索引：claim_id, bib_key, tag, evidence_type） | 20 | 已完成 |
| literature/dedup | 三层去重管道（L1 主键 DOI>arXiv>PMID，L2 近似标题 Jaccard，L3 claim 级去重） | 23 | 已完成 |
| literature/search | MCP 编排器（paper-search + Dify 降级，SearchResult 容器） | 6 | 已完成 |

### Phase 4: 单 Agent 草稿撰写（已完成）

**259 新增 tests（总计 436 tests），覆盖率 93%**

| 模块 | 内容 | 测试数 | 状态 |
|------|------|--------|------|
| models/paper_state | PaperState, SectionState, PaperMetrics（论文全局状态机） | 25 | 已完成 |
| models/glossary | Glossary, SymbolTable, GlossaryEntry, SymbolEntry（术语表 + 符号表） | 28 | 已完成 |
| writing/quality_gates | 5 种质量门禁（Citation/Asset/Claim Traceability/Cross-ref/Terminology Coverage） | -- | 已完成 |
| writing/state_manager | PaperStateManager（不可变模式 + 原子写入） | -- | 已完成 |
| writing/outline | 大纲生成（build_default_outline, outline_to_paper_state） | -- | 已完成 |
| writing/latex_helpers | CLAIM_ID 注释管理、引用格式化、LaTeX 解析 | -- | 已完成 |
| writing/incremental | 增量编译（draft_main.tex 单章节编译，mock subprocess） | -- | 已完成 |
| contracts/schema_export | 新增 PaperState, Glossary, SymbolTable Schema 导出 | -- | 已完成 |
| test_writing/ | 写作模块测试（6 个测试文件 + conftest.py） | 206 | 已完成 |
| Skill: vibewriting-draft | Evidence-First 撰写工作流 Skill | -- | 已完成 |

### Phase 5: 多 Agent 编排（已完成）

**总计 432 tests，全部通过**

| 模块 | 内容 | 测试数 | 状态 |
|------|------|--------|------|
| agents/contracts | Agent 通信契约（AgentRole, SectionTask, SectionPatchPayload, CriticReport, FormatterPatch, MergeConflict, MergeDecision, OrchestrationRound, OrchestrationReport） | -- | 已完成 |
| agents/planner | 章节任务规划器（build_section_task_graph, get_ready_tasks, assign_roles，基于 PaperState 构建依赖图） | -- | 已完成 |
| agents/merge_protocol | 合并协议（validate_patch_payload, detect_conflicts, resolve_conflicts, apply_merge，三类冲突检测：术语/符号/引用） | -- | 已完成 |
| agents/executor | Agent 执行抽象（AgentExecutor Protocol, MockExecutor 测试用, SubAgentExecutor placeholder） | -- | 已完成 |
| agents/orchestrator | 编排核心（OrchestratorConfig, WritingOrchestrator，多轮依赖层调度 + asyncio 并发） | -- | 已完成 |
| agents/git_safety | Git 安全网（create_snapshot_commit, rollback_to_snapshot，仅管辖 paper/ + output/） | -- | 已完成 |
| writing/state_manager | 新增 update_section_payload, set_current_section_index, batch_update_sections 方法 | -- | 已完成 |
| writing/quality_gates | 增强 check_terminology_consistency（幽灵术语检测、未定义术语检测、跨章节一致性） | -- | 已完成 |
| contracts/integrity | 新增 validate_glossary_integrity, validate_symbol_integrity，集成到 validate_referential_integrity | -- | 已完成 |
| test_agents/ | Agent 模块测试（8 个测试文件：contracts, planner, merge_protocol, executor, orchestrator, git_safety + conftest.py） | -- | 已完成 |
| Skill: vibewriting-orchestrate | 多 Agent 编排写作工作流 Skill | -- | 已完成 |

### Phase 6: 编译 + 质量保证（已完成）

**75 新增 tests（总计 507 tests），全部通过**

| 模块 | 内容 | 测试数 | 状态 |
|------|------|--------|------|
| latex/log_parser | LaTeX 日志解析器（ErrorKind 枚举, LatexError 数据类, parse_log, classify_error, extract_error_context） | 16 | 已完成 |
| latex/patch_guard | Patch 安全护栏（PatchProposal, validate_patch_target, validate_patch_scope, enforce_single_file, apply_patch 原子写入） | 12 | 已完成 |
| latex/compiler | 自愈编译器（compile_full, route_error, run_self_heal_loop 编译-解析-分类-路由-stash-patch-重试循环, write_patch_reports） | 9 | 已完成 |
| latex/cli | Phase 6 Typer CLI（4 步管线：compile-heal -> citation-audit -> contract-audit -> peer-review，输出 phase6_report.json） | -- | 已完成 |
| review/models | 审查数据模型（ReviewSeverity, ReviewCategory 枚举, ReviewFinding, PeerReviewReport score 0-10 + verdict, CitationAuditResult, PatchReport, Phase6Report） | 9 | 已完成 |
| review/citation_audit | 引文交叉审计（extract_all_cite_keys, crosscheck_with_evidence_cards, verify_crossref CrossRef API, run_checkcites, run_citation_audit） | 9 | 已完成 |
| review/peer_review | 模拟同行评审（review_structure, review_evidence, review_methodology, generate_review_report 评分+判定, render_review_markdown, save_review_reports） | 9 | 已完成 |
| review/typography | 排版检查（check_overfull_hbox, check_float_placement, check_widow_orphan, run_chktex, run_typography_check） | -- | 已完成 |
| review/disclosure | AI 使用声明（DisclosureConfig, EN/ZH 模板, generate_disclosure_text, inject_disclosure） | -- | 已完成 |
| review/anonymize | 匿名化处理（anonymize_tex 复制+替换, check_anonymization 检测自引/机构/URL） | -- | 已完成 |
| contracts/full_integrity | 全量契约验证（validate_all_tex_citations, validate_asset_hashes SHA256, validate_sections_complete, validate_glossary_in_tex, validate_symbols_in_tex, validate_end_to_end） | 11 | 已完成 |
| agents/git_safety | 新增 stash_before_patch, rollback_stash, drop_stash, list_stashes 4 个 stash 函数 | -- | 已完成 |
| config.py | 新增 Phase 6 配置字段（compile_max_retries, compile_timeout_sec, patch_window_lines, enable_layout_check, enable_ai_disclosure, crossref_api_email） | -- | 已完成 |
| Skill: vibewriting-review | 论文质量审查工作流 Skill（编译验证 -> 引文审计 -> 契约一致性 -> 模拟同行评审 -> Approval Gate） | -- | 已完成 |

## 环境

| 项目 | 版本/状态 | 备注 |
|------|----------|------|
| OS | Windows 11 | 路径用正斜杠，shell 用 Git Bash |
| Python | 3.12.2 | requires-python >=3.12 |
| uv | 0.6.9 | 依赖管理工具，`uv sync` 已完成 |
| Git | 2.52.0 | 版本控制 |
| Node.js | v22.14.0 | MCP 相关工具可能需要 |
| TeX Live | **需用户安装** | 阻塞 LaTeX 编译（约 8GB），模板和构建脚本已就绪 |
| make | **未安装** | 构建脚本用 bash 替代 |
| Dify | 已有实例 | `.env` 中设置 `VW_DIFY_API_KEY` + `VW_DIFY_API_BASE_URL` + `VW_DIFY_DATASET_ID`（`VW_` 前缀已统一） |
| Windows 字体 | 就绪 | SimSun/SimHei/KaiTi/FangSong 已预装 |

## 已交付产物概览

### 核心配置（Phase 1 P0）
- `CLAUDE.md` -- 项目级 Claude Code 配置（含 Phase 3 新增 literature/ 和 data/processed/literature/ 目录映射）
- `pyproject.toml` -- Python 包定义（hatchling + src 布局，14 个运行时依赖 + jsonschema/typer + bibtexparser）
- `uv.lock` -- 依赖锁文件，已提交 Git 保证可复现性（D3）
- `src/vibewriting/config.py` -- pydantic-settings 配置管理，`VW_` env 前缀（含 `VW_DEDUP_THRESHOLD`）+ `apply_paper_config()` 桥接函数（双配置系统）
- `.env.example` -- 环境变量模板（仅敏感凭据 + env-only 字段，管线配置已迁移到 `paper_config.yaml`）
- `.gitignore` / `.gitattributes` -- Git 配置

### MCP 集成（Phase 1 P1 + P4）
- `.mcp.json` -- 双 MCP 服务器配置（paper-search + dify-knowledge，VW_ 前缀环境变量）
- `.claude/settings.local.json` -- 授权 paper-search 外部目录访问
- 3 个 Skills -- vibewriting-literature, vibewriting-kb, vibewriting-cite-check
- `scripts/dify-kb-mcp/server.py` -- FastMCP 桥接服务器（221 行，PEP 723，python-dotenv 自动加载 .env + 环境变量回退链）

### 环境验证（Phase 1 P2）
- `scripts/validate_env.py` -- 分级退出码 0/1/2，彩色输出 + JSON 报告

### LaTeX 模板（Phase 1 P3）
- `paper/main.tex` -- ctexart 主文档
- `paper/latexmkrc` -- latexmk 配置（$pdf_mode=5, out_dir=build）
- `paper/.gitignore` -- 防止直接 xelatex 编译残留（*.aux, *.log, *.pdf 等，正确产物在 `build/`）
- `paper/sections/` -- 6 个章节模板（introduction, related-work, method, experiments, conclusion, appendix）
- `paper/bib/references.bib` -- 参考文献数据库（含示例条目）
- `build.sh` -- 构建脚本（build/watch/clean/check/doi2bib）

### 数据模型（Phase 2）
- `src/vibewriting/models/` -- 7 个文件：base.py（BaseEntity + AssetBase）、paper.py、experiment.py、figure.py、table.py、section.py、__init__.py
- 所有模型继承 BaseEntity（id + created_at + updated_at + tags），AssetBase 扩展 asset_id（`ASSET-YYYY-NNN` 格式）+ kind + path + content_hash + semantic_description

### 契约系统（Phase 2）
- `src/vibewriting/contracts/schema_export.py` -- Pydantic 模型 -> JSON Schema 文件
- `src/vibewriting/contracts/validator.py` -- 自愈验证循环：jsonschema.validate -> regex_healer -> llm_healer（最多 3 轮），ContractValidationError 异常
- `src/vibewriting/contracts/integrity.py` -- 引用完整性验证：claim_id -> evidence_cards, asset_id -> asset_manifest, citation_key -> references.bib
- `src/vibewriting/contracts/healers/` -- regex_healer（正则修复）+ llm_healer（LLM 回退修复，需 LLMBackend 回调）

### 数据处理管线（Phase 2）
- `src/vibewriting/processing/cleaners.py` -- CSV 读取 + 缺失值处理（drop/fill 策略）
- `src/vibewriting/processing/transformers.py` -- 数据聚合与转换
- `src/vibewriting/processing/statistics.py` -- 描述统计（均值/中位数/标准差/四分位）

### 可视化生成（Phase 2）
- `src/vibewriting/visualization/figures.py` -- 折线图 / 柱状图（matplotlib）
- `src/vibewriting/visualization/tables.py` -- LaTeX 表格（jinja2 + booktabs 模板）
- `src/vibewriting/visualization/pgf_export.py` -- PGF 后端导出
- `src/vibewriting/visualization/templates/booktabs.tex.j2` -- booktabs 表格 Jinja2 模板

### DAG 管线（Phase 2）
- `src/vibewriting/pipeline/dag.py` -- DAGRunner（Kahn 拓扑排序 + 环检测 + 失败短路）
- `src/vibewriting/pipeline/nodes.py` -- 8 个节点：load_data -> clean_data -> transform_data -> compute_statistics -> generate_figures -> generate_tables -> build_manifests -> validate_contracts
- `src/vibewriting/pipeline/cli.py` -- Typer CLI（`uv run python -m vibewriting.pipeline.cli run`），支持 --data-dir / --output-dir / --seed 参数
- 管线输出：`output/asset_manifest.json` + `output/run_manifest.json`

### 文献整合（Phase 3）
- `src/vibewriting/models/evidence_card.py` -- EvidenceCard Pydantic 模型（16 字段，`^EC-\d{4}-\d{3}$` claim_id 格式）
- `src/vibewriting/literature/models.py` -- RawLiteratureRecord 统一文献记录格式
- `src/vibewriting/literature/bib_manager.py` -- BibTeX 管理（bibtexparser 2.x，解析/规范化/合并/写回，原子写入）
- `src/vibewriting/literature/evidence.py` -- Evidence Card 生成 + claim_id 单调递增管理（`EC-YYYY-NNN`）
- `src/vibewriting/literature/cache.py` -- 本地知识缓存（JSONL 持久化 + 内存四级索引：claim_id, bib_key, tag, evidence_type）
- `src/vibewriting/literature/dedup.py` -- 三层去重管道（L1 主键去重 DOI>arXiv>PMID，L2 近似标题 token Jaccard，L3 claim 级去重）
- `src/vibewriting/literature/search.py` -- MCP 编排器（paper-search 主 + Dify 降级，SearchResult 容器）
- `.claude/skills/vibewriting-literature/SKILL.md` -- 升级为完整端到端工作流

### 草稿撰写（Phase 4）
- `src/vibewriting/models/paper_state.py` -- PaperState, SectionState, PaperMetrics（论文全局状态机）
- `src/vibewriting/models/glossary.py` -- Glossary, SymbolTable, GlossaryEntry, SymbolEntry（术语 + 符号管理）
- `src/vibewriting/writing/quality_gates.py` -- 5 种质量门禁 + 增强术语一致性检测（Citation/Asset/Claim Traceability/Cross-ref/Terminology）
- `src/vibewriting/writing/state_manager.py` -- PaperStateManager（不可变模式 + 原子写入 + update_section_payload/batch_update_sections）
- `src/vibewriting/writing/outline.py` -- 大纲生成（build_default_outline, outline_to_paper_state）
- `src/vibewriting/writing/latex_helpers.py` -- CLAIM_ID 注释管理、引用格式化、LaTeX 解析
- `src/vibewriting/writing/incremental.py` -- 增量编译（draft_main.tex 单章节编译）
- `src/vibewriting/contracts/schemas/paperstate.schema.json` -- PaperState JSON Schema
- `src/vibewriting/contracts/schemas/glossary.schema.json` -- Glossary JSON Schema
- `src/vibewriting/contracts/schemas/symboltable.schema.json` -- SymbolTable JSON Schema
- `.claude/skills/vibewriting-draft/SKILL.md` -- Evidence-First 草稿撰写工作流 Skill

### 多 Agent 编排（Phase 5）
- `src/vibewriting/agents/contracts.py` -- Agent 通信契约（10 个 Pydantic 数据模型：AgentRole, SectionTask, SectionPatchPayload, CriticIssue, CriticReport, FormatterPatch, MergeConflict, MergeDecision, OrchestrationRound, OrchestrationReport）
- `src/vibewriting/agents/planner.py` -- 章节任务规划器（依赖图构建 + 就绪任务选取 + 角色分配）
- `src/vibewriting/agents/merge_protocol.py` -- 合并协议（Payload 验证 + 三类冲突检测 + 优先级裁决 + 合并应用）
- `src/vibewriting/agents/executor.py` -- Agent 执行抽象（AgentExecutor Protocol + MockExecutor + SubAgentExecutor placeholder）
- `src/vibewriting/agents/orchestrator.py` -- 编排核心（OrchestratorConfig + WritingOrchestrator，多轮依赖层调度 + asyncio 并发执行）
- `src/vibewriting/agents/git_safety.py` -- Git 安全网（快照提交 + 路径级回滚，仅管辖 paper/ + output/）
- `src/vibewriting/agents/__init__.py` -- 模块公共 API 导出
- `src/vibewriting/contracts/integrity.py` -- 新增 validate_glossary_integrity + validate_symbol_integrity
- `.claude/skills/vibewriting-orchestrate/SKILL.md` -- 多 Agent 编排写作工作流 Skill

### 编译 + 质量保证（Phase 6）
- `src/vibewriting/latex/log_parser.py` -- LaTeX 日志解析器（ErrorKind 枚举, LatexError 数据类, parse_log, classify_error）
- `src/vibewriting/latex/patch_guard.py` -- Patch 安全护栏（PatchProposal, validate_patch_target/scope, enforce_single_file, apply_patch 原子写入）
- `src/vibewriting/latex/compiler.py` -- 自愈编译器（compile_full, route_error, run_self_heal_loop, write_patch_reports）
- `src/vibewriting/latex/cli.py` -- Phase 6 Typer CLI（4 步管线，输出 phase6_report.json）
- `src/vibewriting/latex/__init__.py` -- 模块导出
- `src/vibewriting/review/models.py` -- 审查数据模型（ReviewSeverity, ReviewCategory, ReviewFinding, PeerReviewReport, CitationAuditResult, PatchReport, Phase6Report）
- `src/vibewriting/review/citation_audit.py` -- 引文交叉审计（extract_all_cite_keys, crosscheck_with_evidence_cards, verify_crossref, run_citation_audit）
- `src/vibewriting/review/peer_review.py` -- 模拟同行评审（review_structure/evidence/methodology, generate_review_report, save_review_reports）
- `src/vibewriting/review/typography.py` -- 排版检查（overfull hbox, float placement, widow/orphan, chktex）
- `src/vibewriting/review/disclosure.py` -- AI 使用声明（DisclosureConfig, EN/ZH 模板, inject_disclosure）
- `src/vibewriting/review/anonymize.py` -- 匿名化处理（anonymize_tex, check_anonymization）
- `src/vibewriting/review/__init__.py` -- 模块导出
- `src/vibewriting/contracts/full_integrity.py` -- 全量契约验证（validate_all_tex_citations, validate_asset_hashes, validate_end_to_end）
- `src/vibewriting/agents/git_safety.py` -- 新增 stash_before_patch, rollback_stash, drop_stash, list_stashes
- `src/vibewriting/config.py` -- 新增 Phase 6 配置字段（compile_max_retries, compile_timeout_sec, patch_window_lines 等）+ `apply_paper_config()` 桥接函数（Post-Phase 7 新增）
- `.env.example` -- 简化为仅敏感凭据 + env-only 字段（管线配置迁移到 `paper_config.yaml`，保留注释说明）
- `.claude/skills/vibewriting-review/SKILL.md` -- 论文质量审查工作流 Skill

### 端到端集成（Phase 7）
- `src/vibewriting/config_paper.py` -- PaperConfig Pydantic 模型（论文配置：题目/领域/章节列表/研究问题/natbib_style=unsrtnat + 4 个管线字段 float_precision/dedup_threshold/compile_max_retries/compile_timeout_sec）+ load_paper_config（YAML 加载）+ merge_config（不可变合并）+ save_paper_config（YAML 序列化，自动创建目录）
- `src/vibewriting/checkpoint.py` -- PhaseStatus(Enum) + PhaseRecord + Checkpoint 检查点模型；detect_checkpoint/save_checkpoint/create_checkpoint/update_phase/get_resume_phase/should_skip_phase/validate_checkpoint
- `src/vibewriting/metrics.py` -- LiteratureMetrics + WritingMetrics + CompilationMetrics + RunMetricsReport；collect_literature/writing/compilation_metrics + build_run_metrics + save_run_metrics
- `.claude/skills/vibewriting-paper/SKILL.md` -- 端到端主入口 Skill（745 行，9 步工作流 + 5 个 Approval Gates）
- `docs/quickstart.md` -- 快速开始指南
- `docs/config-reference.md` -- 配置参考手册
- `docs/faq.md` -- 常见问题解答
- `docs/cross-project-guide.md` -- 跨项目迁移指南
- `paper_config.yaml` -- 论文配置示例文件（项目根目录）

### 测试（Phase 2 + Phase 3 + Phase 4 + Phase 5 + Phase 6 + Phase 7 + Bug 修复）
- 总计 851 tests，含 test_agents/ + test_latex/ + test_review/ + test_contracts/ + test_config_paper + test_checkpoint + test_metrics 模块 + Post-Phase 7 新增测试 + Bug Fix Round 2 新增测试
- `tests/golden/` -- 黄金文件回归测试（4 tests），确保管线输出确定性
- `tests/test_literature/` -- 文献模块测试（77 tests），含 MCP Mock fixtures
- `tests/test_paper_state.py` -- PaperState 状态机测试（25 tests）[Phase 4]
- `tests/test_glossary_symbols.py` -- 术语表 + 符号表测试（28 tests）[Phase 4]
- `tests/test_writing/` -- 写作模块测试（206 tests，6 文件）[Phase 4] + test_custom_natbib_style [Post-Phase 7]
- `tests/test_agents/` -- 多 Agent 编排测试（8 文件：contracts, planner, merge_protocol, executor, orchestrator, git_safety + conftest.py）[Phase 5]
- `tests/test_latex/` -- LaTeX 编译工具测试（conftest + test_log_parser 16t + test_patch_guard 12t + test_compiler 9t）[Phase 6]
- `tests/test_review/` -- 审查模块测试（conftest + test_models 9t + test_citation_audit 9t + test_peer_review 9t）[Phase 6]
- `tests/test_contracts/test_full_integrity.py` -- 全量契约验证测试（11 tests）[Phase 6]
- `tests/test_config_paper.py` -- 论文配置测试（46 tests + 4 管线字段默认值 + 6 apply_paper_config 测试）[Phase 7 + Post]
- `tests/test_checkpoint.py` -- 检查点测试（39 tests）[Phase 7]
- `tests/test_metrics.py` -- 指标汇总测试（22 tests）[Phase 7]

### OPSX 归档
- `openspec/changes/archive/2026-02-23-project-foundation-architecture/` -- Phase 1 归档
- `openspec/changes/archive/2026-02-23-phase-2-data-models-pipeline/` -- Phase 2 归档
- `openspec/changes/phase-3-literature-integration/` -- Phase 3 变更（proposal + design + tasks）
- `openspec/specs/` -- 6 个已合并规格（project-scaffold, latex-compilation, claude-config, mcp-integration, python-environment, env-validation）

## 下一步行动

Phase 1-7 全部已完成，路线图 v4 全部阶段已交付。完整路线图见 **`openspec/ROADMAP.md`**（v4，617 行，7 阶段）。

### 阶段依赖图

```
Phase 1: 基础架构 [已完成]
   |
   +---> Phase 2: 数据模型 + 处理管线 [已完成] ─+
   |                                              +---> Phase 4: 单 Agent 草稿撰写 [已完成]
   +---> Phase 3: 文献整合工作流 [已完成] ────────+            |
                                                               v
                                                   Phase 5: 多 Agent 编排 [已完成]
                                                               |
                                                               v
                                                   Phase 6: 编译 + 质量保证 [已完成]
                                                               |
                                                               v
                                                   Phase 7: 端到端集成 [已完成]
```

- Phase 1-7 **全部已完成**
- 阶段间设有 **Approval Gates**（通过 AskUserQuestion 实现人机协同审批）
- 详细阶段说明、交付物清单、验证标准见 `openspec/ROADMAP.md`

### 需要用户操作的阻塞项

1. **TeX Live 安装** -- 安装后 `bash build.sh build` 可编译论文，`validate_env.py` 中 xelatex/latexmk/bibtex/checkcites 将从 blocked 变为 pass
2. **Dify 凭据配置** -- 在 `.env` 中设置 `VW_DIFY_API_KEY`, `VW_DIFY_API_BASE_URL`, `VW_DIFY_DATASET_ID`（`VW_` 前缀已统一修正），启用知识库检索功能

### 可立即开始的工作

- 使用 `/vibewriting-paper` Skill 启动端到端写作流程（`paper_config.yaml` 已就绪）
- LaTeX 全量编译验证（需 TeX Live，`bash build.sh build`）
- SubAgentExecutor 实现（对接 Claude Code Sub-agent，替代 MockExecutor）
