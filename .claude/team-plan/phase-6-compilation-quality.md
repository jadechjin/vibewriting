# Team Plan: Phase 6 编译 + 质量保证

## 概述

为 vibewriting 实现自修复 LaTeX 编译循环、引文交叉验证、全契约一致性验证、模拟同行评审及 review-paper Skill，完成从 LaTeX 源码到高质量 PDF 的自动化闭环。

## Codex 分析摘要

- **可行性**: 8.5/10，现有基础覆盖 60%+ 核心能力
- **推荐方案**: 模块化（方案 B）—— `latex/ + contracts/ + review/ + skill` 分层
- **关键架构**: compiler.py + log_parser.py + patch_guard.py + citation_audit.py + full_integrity.py + peer_review.py
- **发现问题**: paper_state.json 路径在 Skill 中不一致；validate_env.py 中 Dify 变量前缀不一致
- **风险**: 自修复误改语义、日志误分类、git stash 冲突、外部 API 限流

## Gemini 分析摘要

- **审查报告模型**: ReviewFinding（severity: Critical/Major/Minor/Suggestion）+ PeerReviewReport（verdict: Accept/Reject/Revision）
- **交互模式**: Draft-Review-Apply 补丁审批模式
- **排版检查**: 混合方案（规则检查 chktex + AI 视觉可选）
- **Approval Gate**: 自修复补丁生成后不自动覆盖，需确认
- **严重性分级**: Critical（编译失败/引文造假）> Major（逻辑断层）> Minor（格式拼写）

## 技术方案

### 综合决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 架构风格 | 模块化（Codex 方案 B） | 可测试、可扩展、清晰边界 |
| 新模块位置 | `src/vibewriting/review/` | 评审功能独立于编译和写作 |
| 审查报告格式 | JSON + Markdown 双格式（Gemini 方案） | 机器可读 + 人类可读 |
| 严重性分级 | Critical/Major/Minor/Suggestion（4 级） | 与学术同行评审对齐 |
| 排版检查 | 规则优先（chktex/lacheck），AI 视觉可选 | 降低成本，按需启用 |
| 编译回滚 | git stash（非 snapshot commit） | ROADMAP 明确要求 stash |
| 外部 API | CrossRef 优先，Semantic Scholar 降级 | CrossRef 覆盖率高 |
| 错误未知分类 | 不自动补丁，转人工介入 | 安全第一 |

### 新增目录结构

```
src/vibewriting/
  latex/
    __init__.py          ← 修改（导出新公共 API）
    compiler.py          ← 修改（核心：自修复循环 + 全量编译）
    log_parser.py        ← 新增（.log 解析 + 错误分类）
    patch_guard.py       ← 新增（补丁范围限制 + 安全验证）
  review/
    __init__.py          ← 新增（模块入口）
    models.py            ← 新增（ReviewFinding + PeerReviewReport Pydantic 模型）
    citation_audit.py    ← 新增（引文交叉验证：checkcites + API + CLAIM_ID）
    peer_review.py       ← 新增（模拟同行评审：结构/证据/方法论）
  contracts/
    full_integrity.py    ← 新增（全契约一致性：扩展 integrity.py）
  config.py              ← 修改（新增 Phase 6 配置项）
  agents/
    git_safety.py        ← 修改（新增 stash_before_patch / rollback_stash）
.claude/skills/
  review-paper/
    SKILL.md             ← 新增（review-paper 工作流 Skill）
tests/
  test_latex/            ← 新增（编译模块测试）
  test_review/           ← 新增（评审模块测试）
```

## 子任务列表

### Task 1: LaTeX Log 解析器 + 错误分类

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/latex/log_parser.py`（新增）
- **依赖**: 无
- **实施步骤**:
  1. 定义 `LatexError` 数据类（line_number, file_path, error_type, message, context_lines）
  2. 定义 `ErrorKind` 枚举（MISSING_PACKAGE, UNDEFINED_REFERENCE, SYNTAX_ERROR, MISSING_FILE, ENCODING_ERROR, UNKNOWN）
  3. 实现 `parse_log(log_content: str) -> list[LatexError]`：正则匹配 `! LaTeX Error`, `Undefined control sequence`, `! Missing`, `File ... not found` 等模式
  4. 实现 `classify_error(error: LatexError) -> ErrorKind`：按错误消息文本分类
  5. 实现 `extract_error_context(log_content: str, error: LatexError, window: int = 5) -> str`：提取错误行上下文
- **验收标准**:
  - 能正确解析 5 种常见 LaTeX 错误类型的 .log 内容
  - 每种 ErrorKind 至少有 1 个测试用例
  - 对未知错误归类为 UNKNOWN

### Task 2: LaTeX 补丁护栏

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/latex/patch_guard.py`（新增）
- **依赖**: 无
- **实施步骤**:
  1. 定义 `PatchProposal` 数据类（target_file, start_line, end_line, original_content, patched_content, error_kind）
  2. 实现 `validate_patch_target(proposal: PatchProposal, paper_dir: Path) -> bool`：确保 target_file 在 `paper/sections/*.tex` 范围内
  3. 实现 `validate_patch_scope(proposal: PatchProposal, max_window: int = 10) -> bool`：确保修改范围不超过 ±N 行
  4. 实现 `enforce_single_file(proposals: list[PatchProposal]) -> bool`：确保单轮只修改 1 个文件
  5. 实现 `apply_patch(proposal: PatchProposal, paper_dir: Path) -> bool`：原子写入补丁内容
- **验收标准**:
  - 拒绝修改 `main.tex` 的补丁
  - 拒绝超出 ±N 行窗口的补丁
  - 拒绝单轮多文件修改
  - 成功应用合规补丁

### Task 3: Review 数据模型

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/review/__init__.py`（新增）
  - `src/vibewriting/review/models.py`（新增）
- **依赖**: 无
- **实施步骤**:
  1. 创建 `src/vibewriting/review/` 目录
  2. 定义 `ReviewSeverity` 枚举（CRITICAL, MAJOR, MINOR, SUGGESTION）
  3. 定义 `ReviewCategory` 枚举（METHODOLOGY, EVIDENCE, STRUCTURE, LANGUAGE, CITATION）
  4. 定义 `ReviewFinding` Pydantic 模型（severity, category, location, issue, rationale, suggestion）
  5. 定义 `PeerReviewReport` Pydantic 模型（overall_score: float 0-10, verdict: Accept/Minor Revision/Major Revision/Reject, summary, strengths, weaknesses, detailed_findings: list[ReviewFinding], consistency_check: dict）
  6. 定义 `CitationAuditResult` Pydantic 模型（verified_count, suspicious_keys, orphan_claims, missing_evidence_cards）
  7. 定义 `PatchReport` Pydantic 模型（round_number, error_kind, target_file, lines_changed, success, stash_ref）
  8. 定义 `Phase6Report` 聚合模型（compilation, citation_audit, contract_integrity, peer_review）
  9. `__init__.py` 导出所有公共模型
- **验收标准**:
  - 所有模型可序列化为 JSON
  - 字段约束正确（score 0-10, severity 枚举值）
  - 模型间引用一致

### Task 4: Config 扩展

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/config.py`（修改）
- **依赖**: 无
- **实施步骤**:
  1. 在 `Settings` 类中新增 Phase 6 配置字段：
     - `compile_max_retries: int = 5`
     - `compile_timeout_sec: int = 120`
     - `patch_window_lines: int = 10`
     - `enable_layout_check: bool = False`
     - `enable_ai_disclosure: bool = False`
     - `crossref_api_email: str = ""`（CrossRef 礼貌池）
  2. 更新 `.env.example` 添加对应 `VW_COMPILE_MAX_RETRIES` 等条目
- **验收标准**:
  - 所有新配置有合理默认值
  - 可通过环境变量覆盖
  - `.env.example` 同步更新

### Task 5: Git Safety 扩展（stash 支持）

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/agents/git_safety.py`（修改）
- **依赖**: 无
- **实施步骤**:
  1. 新增 `stash_before_patch(repo_root: Path, message: str) -> str`：执行 `git stash push -m "auto: before patch {message}" -- paper/`，返回 stash ref
  2. 新增 `rollback_stash(repo_root: Path) -> None`：执行 `git stash pop`
  3. 新增 `drop_stash(repo_root: Path) -> None`：执行 `git stash drop`（补丁成功后清理）
  4. 新增 `list_stashes(repo_root: Path) -> list[str]`：列出当前 stash 栈
- **验收标准**:
  - stash 操作仅影响 paper/ 目录
  - stash message 包含 `auto:` 前缀
  - 空工作区时 stash 不报错（优雅处理）

### Task 6: LaTeX 编译器（自修复循环）

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/latex/compiler.py`（修改）
  - `src/vibewriting/latex/__init__.py`（修改）
- **依赖**: Task 1, Task 2, Task 3, Task 4, Task 5
- **实施步骤**:
  1. 实现 `compile_full(paper_dir: Path, timeout: int = 120) -> tuple[bool, str]`：调用 latexmk 全量编译
  2. 实现 `route_error(error: LatexError) -> str`：
     - MISSING_PACKAGE → 返回安装提示，不自动修复
     - UNDEFINED_REFERENCE → 检查 references.bib + literature_cards
     - SYNTAX_ERROR → 生成自动补丁
     - MISSING_FILE → 检查 asset_manifest.json
     - ENCODING_ERROR → 提示手动检查
     - UNKNOWN → 不自动补丁，记录日志
  3. 实现 `run_self_heal_loop(paper_dir: Path, max_retries: int = 5) -> list[PatchReport]`：
     - 循环：编译 → 解析日志 → 分类 → 路由 → stash → 补丁 → 重试
     - 每轮生成 PatchReport
     - 不可修复错误提前退出
  4. 实现 `write_patch_reports(reports: list[PatchReport], output_dir: Path) -> Path`：写入 `patch_report.json`
  5. 更新 `__init__.py` 导出 `compile_full`, `run_self_heal_loop`
- **验收标准**:
  - 语法错误能自动修复（测试用故障注入）
  - 缺包错误不尝试自动修复
  - 5 轮后仍失败则退出并输出报告
  - 每轮有 stash checkpoint

### Task 7: 引文交叉验证

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/review/citation_audit.py`（新增）
- **依赖**: Task 3
- **实施步骤**:
  1. 实现 `extract_all_cite_keys(paper_dir: Path) -> set[str]`：扫描所有 `.tex` 文件中的 `\citep{}` / `\citet{}` 键
  2. 实现 `extract_all_claim_ids(paper_dir: Path) -> dict[str, list[str]]`：解析 `%% CLAIM_ID` 注释，按文件分组
  3. 实现 `crosscheck_with_evidence_cards(claim_ids: dict, cards_path: Path) -> CitationAuditResult`：验证每个 CLAIM_ID 在 literature_cards.jsonl 中存在
  4. 实现 `verify_crossref(bib_keys: set[str], bib_path: Path, email: str = "") -> dict[str, bool]`：通过 CrossRef API 验证 DOI 真实性（可选，降级为跳过）
  5. 实现 `run_checkcites(aux_path: Path) -> tuple[list[str], list[str]]`：返回 (unused_keys, undefined_keys)
  6. 实现 `run_citation_audit(paper_dir: Path, cards_path: Path, bib_path: Path) -> CitationAuditResult`：聚合所有检查
- **验收标准**:
  - 检测出所有无证据卡支撑的引用
  - 检测出 .tex 中引用但 .bib 中不存在的键
  - CrossRef 不可用时优雅降级
  - 输出 CitationAuditResult 可序列化

### Task 8: 全契约一致性验证

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/contracts/full_integrity.py`（新增）
- **依赖**: Task 3
- **实施步骤**:
  1. 实现 `validate_all_tex_citations(paper_dir: Path, bib_path: Path) -> list[IntegrityViolation]`：扫描全文 `\cite{}` 键 vs references.bib
  2. 实现 `validate_asset_hashes(asset_manifest: list[dict], output_dir: Path) -> list[IntegrityViolation]`：验证资产文件存在且 content_hash 匹配
  3. 实现 `validate_sections_complete(paper_state: dict) -> list[IntegrityViolation]`：验证所有章节状态为 "complete"
  4. 实现 `validate_glossary_in_tex(glossary: dict, paper_dir: Path) -> list[IntegrityViolation]`：术语表中定义的术语在全文至少出现一次
  5. 实现 `validate_symbols_in_tex(symbols: dict, paper_dir: Path) -> list[IntegrityViolation]`：符号表中符号在全文至少出现一次
  6. 实现 `validate_end_to_end(paper_dir: Path, output_dir: Path, data_dir: Path) -> list[IntegrityViolation]`：聚合所有检查（复用 integrity.py 的 validate_referential_integrity + 新增检查）
- **验收标准**:
  - 检测全文引用 vs .bib 不一致
  - 检测资产文件缺失或哈希不匹配
  - 检测未完成的章节状态
  - 输出复用 IntegrityViolation 类型

### Task 9: 模拟同行评审

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/review/peer_review.py`（新增）
- **依赖**: Task 3, Task 7, Task 8
- **实施步骤**:
  1. 实现 `review_structure(paper_state: dict) -> list[ReviewFinding]`：检查章节完整性（所有必需章节存在）、章节顺序合理性、摘要/结论存在性
  2. 实现 `review_evidence(paper_dir: Path, cards_path: Path) -> list[ReviewFinding]`：检查每个 claim 是否有 CLAIM_ID 支撑、evidence_type 分布是否合理（纯 theoretical 无 empirical 则 Major warning）
  3. 实现 `review_methodology(paper_dir: Path, asset_manifest: list[dict]) -> list[ReviewFinding]`：实验章节是否引用了足够的图表资产、方法章节是否有数学公式/算法描述
  4. 实现 `generate_review_report(...) -> PeerReviewReport`：聚合三维审查、计算总分、给出 verdict
  5. 实现 `render_review_markdown(report: PeerReviewReport) -> str`：渲染 Markdown 格式审查报告
  6. 实现 `save_review_reports(report: PeerReviewReport, output_dir: Path) -> tuple[Path, Path]`：同时保存 JSON + Markdown
- **验收标准**:
  - 三维审查均有输出
  - verdict 与 overall_score 一致（<4 Reject, 4-6 Major, 6-8 Minor, >8 Accept）
  - Markdown 报告人类可读

### Task 10: Phase 6 CLI 入口

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/latex/cli.py`（新增）
- **依赖**: Task 6, Task 7, Task 8, Task 9
- **实施步骤**:
  1. 使用 Typer 创建 CLI 应用
  2. 实现 `run` 命令：串联 compile-heal → citation-audit → contract-audit → peer-review
  3. 参数：`--paper-dir`, `--output-dir`, `--data-dir`, `--max-retries`, `--skip-external-api`
  4. 每步输出进度信息
  5. 最终汇总 Phase6Report 并保存到 `output/phase6_report.json`
- **验收标准**:
  - `uv run python -m vibewriting.latex.cli run` 可执行
  - 输出 phase6_report.json
  - 任一步骤 Critical 错误时，提前退出并提示

### Task 11: review-paper Skill

- **类型**: 配置
- **文件范围**:
  - `.claude/skills/review-paper/SKILL.md`（新增）
- **依赖**: Task 10
- **实施步骤**:
  1. 创建 `.claude/skills/review-paper/` 目录
  2. 编写 SKILL.md：
     - 触发条件：用户请求审查论文
     - 工作流：加载契约产物 → 运行 Phase 6 CLI → 解析报告 → 展示结果 → AskUserQuestion 确认
     - 支持选项：全量审查 / 仅编译 / 仅引文检查
  3. 集成 Approval Gate：审查完成后通过 AskUserQuestion 展示摘要
- **验收标准**:
  - Skill 可通过 `/review-paper` 触发
  - 输出结构化审查摘要
  - 包含 Approval Gate 断点

### Task 12: 单元测试

- **类型**: 测试
- **文件范围**:
  - `tests/test_latex/`（新增目录）
    - `conftest.py`
    - `test_log_parser.py`
    - `test_patch_guard.py`
    - `test_compiler.py`
  - `tests/test_review/`（新增目录）
    - `conftest.py`
    - `test_models.py`
    - `test_citation_audit.py`
    - `test_peer_review.py`
  - `tests/test_contracts/`
    - `test_full_integrity.py`（新增）
- **依赖**: Task 1-9
- **实施步骤**:
  1. 编写 log_parser 测试：5 种错误类型各 2+ 测试用例
  2. 编写 patch_guard 测试：合规/违规补丁各 3+ 测试用例
  3. 编写 compiler 测试：mock subprocess，测试自修复循环逻辑
  4. 编写 review models 测试：序列化/反序列化/约束验证
  5. 编写 citation_audit 测试：mock MCP + mock CrossRef API
  6. 编写 peer_review 测试：各维度审查逻辑
  7. 编写 full_integrity 测试：全文扫描 + 哈希验证
- **验收标准**:
  - `uv run pytest tests/test_latex/ tests/test_review/` 全部通过
  - 覆盖率 >= 80%
  - 测试总数预期 80+ 新增

## 文件冲突检查

✅ 无冲突 — 所有任务文件范围完全隔离：

| Task | 文件 | 类型 |
|------|------|------|
| 1 | `latex/log_parser.py` | 新增 |
| 2 | `latex/patch_guard.py` | 新增 |
| 3 | `review/__init__.py`, `review/models.py` | 新增 |
| 4 | `config.py` | 修改 |
| 5 | `agents/git_safety.py` | 修改 |
| 6 | `latex/compiler.py`, `latex/__init__.py` | 修改 |
| 7 | `review/citation_audit.py` | 新增 |
| 8 | `contracts/full_integrity.py` | 新增 |
| 9 | `review/peer_review.py` | 新增 |
| 10 | `latex/cli.py` | 新增 |
| 11 | `.claude/skills/review-paper/SKILL.md` | 新增 |
| 12 | `tests/test_latex/`, `tests/test_review/`, `tests/test_contracts/test_full_integrity.py` | 新增 |

## 并行分组

- **Layer 1 (并行)**: Task 1, Task 2, Task 3, Task 4, Task 5
  - 5 个无依赖的基础模块，可同时由 5 个 Builder 执行
- **Layer 2 (依赖 Layer 1)**: Task 6, Task 7, Task 8
  - Task 6 依赖 T1+T2+T3+T4+T5
  - Task 7 依赖 T3
  - Task 8 依赖 T3
  - T7 和 T8 可与 T6 并行（T7/T8 仅依赖 T3）
- **Layer 3 (依赖 Layer 2)**: Task 9
  - 依赖 T3+T7+T8
- **Layer 4 (依赖 Layer 3)**: Task 10, Task 11
  - T10 依赖 T6+T7+T8+T9
  - T11 依赖 T10
- **Layer 5 (依赖 Layer 4)**: Task 12
  - 所有实现完成后统一编写测试

## Builder 建议

- **最大并行 Builder 数**: 5（Layer 1 阶段）
- **最小 Builder 数**: 3（核心路径：编译 + 审查 + 契约）
- **预估总任务数**: 15（含可选任务）

## 可选任务（全量实施）

### Task 13: 排版质量检查

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/review/typography.py`（新增）
- **依赖**: Task 3, Task 6
- **实施步骤**:
  1. 实现 `check_overfull_hbox(log_content: str) -> list[ReviewFinding]`：从编译 .log 中提取 Overfull/Underfull hbox 警告
  2. 实现 `check_float_placement(paper_dir: Path) -> list[ReviewFinding]`：扫描 .tex 中强制浮动位置 `[h!]` / `[H]` 的使用
  3. 实现 `check_widow_orphan(log_content: str) -> list[ReviewFinding]`：检测孤行/寡行警告
  4. 实现 `run_chktex(paper_dir: Path) -> list[ReviewFinding]`：调用 chktex 工具（如可用），解析输出
  5. 实现 `run_typography_check(paper_dir: Path, log_content: str, enable_ai_vision: bool = False) -> list[ReviewFinding]`：聚合所有排版检查
  6. 可选：`check_pdf_visual(pdf_path: Path) -> list[ReviewFinding]`：将 PDF 页面转图片，通过 Claude 视觉模型检查（仅当 `enable_layout_check=True` 时启用）
- **验收标准**:
  - 检测 Overfull hbox 并标记为 Minor
  - 检测强制浮动定位并标记为 Suggestion
  - chktex 不可用时优雅降级
  - AI 视觉检查默认关闭

### Task 14: AI 使用披露

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/review/disclosure.py`（新增）
- **依赖**: 无
- **实施步骤**:
  1. 定义 `DisclosureConfig` Pydantic 模型（enable: bool, template: str, placement: Literal["appendix", "acknowledgments"]）
  2. 实现 `generate_disclosure_text(config: DisclosureConfig, paper_state: dict) -> str`：根据模板生成 AI 辅助声明文本
  3. 实现 `inject_disclosure(paper_dir: Path, config: DisclosureConfig, text: str) -> Path`：将声明注入到指定位置（appendix 或 acknowledgments）
  4. 提供默认英文和中文模板
- **验收标准**:
  - `enable_ai_disclosure=False` 时不生成任何内容
  - 生成的 LaTeX 文本语法正确
  - 支持中英文双语模板

### Task 15: 双盲审查准备

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/review/anonymize.py`（新增）
- **依赖**: 无
- **实施步骤**:
  1. 实现 `anonymize_tex(paper_dir: Path, output_dir: Path) -> Path`：
     - 复制 paper/ 到临时目录
     - 替换 `\author{}` 为 "Anonymous"
     - 替换 `\affiliation{}` / `\institute{}` 为空
     - 移除致谢中的个人信息标记
  2. 实现 `check_anonymization(paper_dir: Path) -> list[ReviewFinding]`：扫描全文检测可能泄露身份的内容（"our previous work"、自引用、机构名称等）
- **验收标准**:
  - 匿名化后的 .tex 可正常编译
  - 检测到的身份泄露标记为 Major

## 更新后的文件冲突检查

✅ 无冲突 — 新增任务文件范围与现有任务完全隔离：

| Task | 文件 | 类型 |
|------|------|------|
| 13 | `review/typography.py` | 新增 |
| 14 | `review/disclosure.py` | 新增 |
| 15 | `review/anonymize.py` | 新增 |

## 更新后的并行分组

- **Layer 1 (并行)**: Task 1, Task 2, Task 3, Task 4, Task 5, Task 14, Task 15
  - 7 个无依赖的基础模块
- **Layer 2 (依赖 Layer 1)**: Task 6, Task 7, Task 8
  - Task 6 依赖 T1+T2+T3+T4+T5
  - Task 7 依赖 T3
  - Task 8 依赖 T3
- **Layer 3 (依赖 Layer 2)**: Task 9, Task 13
  - Task 9 依赖 T3+T7+T8
  - Task 13 依赖 T3+T6
- **Layer 4 (依赖 Layer 3)**: Task 10, Task 11
  - T10 依赖 T6+T7+T8+T9（+T13/T14/T15 集成）
  - T11 依赖 T10
- **Layer 5 (依赖 Layer 4)**: Task 12
  - 所有实现完成后统一编写测试（含 T13/T14/T15 的测试）
