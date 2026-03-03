# Team Plan: Phase 5 Multi-Agent Orchestration

## 概述

为 vibewriting 实现多 Agent 编排系统：Orchestrator 作为唯一文件写入节点，Role Agents（Storyteller/Analyst/Critic/Formatter）返回 Patch/JSON，通过合并协议串行落盘，实现章节并行生成与角色分工。

## Codex 分析摘要

- **可行性**: 8.5/10，现有 PaperState + 不可变模式 + 质量门禁 + 契约系统提供了强基础
- **推荐架构**: Sub-agents 优先（稳定可控），Agent Teams 作为可选升级路径
- **关键缺口**:
  - `agents/` 目录为空，需从零建设编排/合并层
  - `check_terminology_consistency` 几乎不会失败，需增强
  - `integrity.py` 的 glossary/symbols 参数未真正参与校验
  - 无 Git 快照/回滚封装
- **实施建议**: 7 个新文件 + 1 Skill + 5 个现有文件修改，分 6 个子阶段
- **文件设计**: contracts.py(数据契约) -> planner.py(任务图) -> executor.py(执行抽象) -> merge_protocol.py(合并协议) -> git_safety.py(Git安全) -> orchestrator.py(编排核心)

## Gemini 分析摘要

- **架构模型**: Hub-and-Spoke，Orchestrator 为特权中枢
- **Role Agents**: 无状态、沙盒隔离，只返回内容不写文件
- **合并策略**: Strict Serial Write + Git Snapshots + Schema Validation
- **冲突裁决**: 术语/符号以 glossary/symbols 为硬裁决源，叙事冲突由 Storyteller 裁决（不可突破证据约束）
- **集成建议**: Sub-agents 用于原子任务（引用验证、公式检查），Agent Teams 用于重度生成（章节撰写）
- **验证策略**: 单元测试合并逻辑 + 集成测试编排循环 + 全文引用完整性 + LaTeX 编译

## 技术方案

### 核心架构决策

1. **执行后端**: Sub-agents 优先（稳定性高），保留 Agent Teams 接口（Protocol 抽象）
2. **写权限模型**: Orchestrator 是唯一物理文件写入者，Role Agents 只返回 JSON Payload
3. **合并协议**: 串行队列 + 冲突检测 + 分级裁决（术语>引用>叙事）
4. **单一真源**: `paper_state.json` + `glossary.json` + `symbols.json`
5. **Git 安全网**: 每轮合并前 snapshot commit，失败回滚到 snapshot
6. **同步修补**: 增强术语门禁 + integrity 的 glossary/symbols 校验

### 数据流

```
Outline (paper_state.json)
    |
    v
Orchestrator: build_section_task_graph()
    |
    v  (dispatch to Sub-agents)
+---+---+---+---+
| ST | AN | CR | FM |   <- 4 Role Agents (stateless)
+---+---+---+---+
    |   return SectionPatchPayload (JSON)
    v
Orchestrator: validate_patch + detect_conflicts + resolve_conflicts
    |
    v
Orchestrator: apply_merge -> write files (serial) -> run_all_gates -> compile
    |
    v
paper_state.json + glossary.json + symbols.json + paper/sections/*.tex
    |
    v
git commit -m "auto: multi-agent merge round N"
```

### Role Agent 定义

| Agent | 角色 | 输入 | 输出 | 职责范围 |
|-------|------|------|------|----------|
| Storyteller | 叙事 | section outline + evidence cards + existing drafts | SectionPatchPayload | 长篇正文生成、叙事主线构建、跨章节衔接 |
| Analyst | 数据 | section outline + asset_manifest + evidence cards | SectionPatchPayload | 实验结果解读、数据描述、图表引用 |
| Critic | 审查 | drafted sections + quality gate results | CriticReport | 逻辑审查、论证强度评估、改进建议 |
| Formatter | 排版 | drafted sections + glossary + symbols | FormatterPatch | LaTeX 格式规范、术语/符号统一、排版优化 |

## 子任务列表

### Task 1: Agent 通信契约（Pydantic 数据模型）
- **类型**: 后端核心
- **文件范围**:
  - `src/vibewriting/agents/contracts.py` (新增)
  - `tests/test_agents/__init__.py` (新增)
  - `tests/test_agents/conftest.py` (新增)
  - `tests/test_agents/test_contracts.py` (新增)
- **依赖**: 无
- **实施步骤**:
  1. 定义 `AgentRole` 枚举 (`storyteller|analyst|critic|formatter`)
  2. 定义 `SectionTask` 模型（section_id, role, evidence_cards, assets, context）
  3. 定义 `SectionPatchPayload` 模型（section_id, tex_content, claim_ids, asset_ids, citation_keys, new_terms, new_symbols, word_count）
  4. 定义 `CriticReport` 模型（section_id, issues, suggestions, severity_scores）
  5. 定义 `FormatterPatch` 模型（section_id, tex_content, term_replacements, symbol_updates）
  6. 定义 `MergeConflict` 和 `MergeDecision` 模型（conflict_type, affected_sections, resolution）
  7. 定义 `OrchestrationReport` 模型（汇总所有轮次结果）
  8. 为所有模型编写单测（字段验证、边界值、序列化/反序列化）
- **验收标准**: `uv run pytest tests/test_agents/test_contracts.py` 全绿，所有 Pydantic 模型可 JSON 序列化

### Task 2: 章节任务规划器
- **类型**: 后端核心
- **文件范围**:
  - `src/vibewriting/agents/planner.py` (新增)
  - `tests/test_agents/test_planner.py` (新增)
- **依赖**: Task 1
- **实施步骤**:
  1. 实现 `build_section_task_graph(state: PaperState, evidence_cards, asset_manifest) -> list[SectionTask]`
     - 根据章节类型分配 Agent 角色（introduction/related-work -> Storyteller; experiments -> Analyst; all -> Critic/Formatter）
     - 章节间依赖建模（引言需等待方法论确定 -> method 优先于 introduction 最终版）
  2. 实现 `get_ready_tasks(tasks, completed_ids) -> list[SectionTask]`
     - 返回所有前置依赖已满足的待执行任务
  3. 实现 `assign_roles(section_type) -> list[AgentRole]`
     - 每种章节类型的默认角色分配策略
  4. 编写单测覆盖：6 章节分配、依赖顺序、ready task 选择
- **验收标准**: `uv run pytest tests/test_agents/test_planner.py` 全绿

### Task 3: 合并协议
- **类型**: 后端核心
- **文件范围**:
  - `src/vibewriting/agents/merge_protocol.py` (新增)
  - `tests/test_agents/test_merge_protocol.py` (新增)
- **依赖**: Task 1
- **实施步骤**:
  1. 实现 `validate_patch_payload(payload: SectionPatchPayload, allowed_claim_ids, allowed_asset_ids) -> list[str]`
     - 校验 claim_ids 子集约束、asset_ids 子集约束、tex_content 非空
  2. 实现 `detect_conflicts(payloads: list[SectionPatchPayload], glossary: Glossary, symbols: SymbolTable) -> list[MergeConflict]`
     - 术语冲突：不同 payload 对同一术语定义不一致
     - 符号冲突：不同 payload 对同一符号含义不一致
     - 引用冲突：不同 payload 引用键不在 references.bib 中
  3. 实现 `resolve_conflicts(conflicts: list[MergeConflict], glossary, symbols) -> list[MergeDecision]`
     - 术语/符号 -> 以 glossary/symbols 为准，生成回写指令
     - 引用 -> 以 references.bib + evidence_cards 为准
     - 叙事 -> 标记为人工审查或 Storyteller 最终裁决
  4. 实现 `apply_merge(payload, decisions, current_tex) -> str`
     - 应用裁决后的最终 tex 内容
  5. 编写单测覆盖三类冲突场景 + 正常合并
- **验收标准**: `uv run pytest tests/test_agents/test_merge_protocol.py` 全绿，含冲突检测与解决测试

### Task 4: Git 安全网
- **类型**: 后端工具
- **文件范围**:
  - `src/vibewriting/agents/git_safety.py` (新增)
  - `tests/test_agents/test_git_safety.py` (新增)
- **依赖**: 无
- **实施步骤**:
  1. 实现 `create_snapshot_commit(repo_root: Path, message: str) -> str`
     - `git add paper/ output/` + `git commit -m "auto: snapshot before {message}"`
     - 返回 commit hash
  2. 实现 `rollback_to_snapshot(repo_root: Path, commit_hash: str) -> None`
     - `git reset --hard {commit_hash}` 限定于 paper/ 和 output/ 路径
  3. 实现 `get_managed_paths() -> list[str]`
     - 返回 Orchestrator 管辖路径列表（不回滚非管辖文件）
  4. 实现 `has_uncommitted_changes(repo_root: Path) -> bool`
  5. 编写单测（mock subprocess，验证命令参数正确性）
- **验收标准**: `uv run pytest tests/test_agents/test_git_safety.py` 全绿

### Task 5: Agent 执行抽象
- **类型**: 后端核心
- **文件范围**:
  - `src/vibewriting/agents/executor.py` (新增)
  - `tests/test_agents/test_executor.py` (新增)
- **依赖**: Task 1
- **实施步骤**:
  1. 定义 `AgentExecutor` Protocol
     - `async run_task(task: SectionTask, context: dict) -> SectionPatchPayload | CriticReport | FormatterPatch`
  2. 实现 `SubAgentExecutor(AgentExecutor)` — Claude Code Sub-agent 后端
     - 构建 prompt（注入 section outline + evidence cards + writing rules）
     - 调用 Claude Code sub-agent（通过 Task tool）
     - 解析返回的 JSON 为 Payload
  3. 实现 `MockExecutor(AgentExecutor)` — 测试用 mock 后端
  4. 预留 `TeamExecutor(AgentExecutor)` 接口（Agent Teams 后备，暂不实现）
  5. 编写单测（使用 MockExecutor 验证接口契约）
- **验收标准**: `uv run pytest tests/test_agents/test_executor.py` 全绿

### Task 6: Orchestrator 编排核心
- **类型**: 后端核心
- **文件范围**:
  - `src/vibewriting/agents/orchestrator.py` (新增)
  - `tests/test_agents/test_orchestrator.py` (新增)
  - `src/vibewriting/agents/__init__.py` (修改，添加导出)
- **依赖**: Task 1, 2, 3, 4, 5
- **实施步骤**:
  1. 定义 `OrchestratorConfig`（max_rounds, max_retries_per_section, enable_git_snapshots, executor_type）
  2. 实现 `WritingOrchestrator` 类
     - `__init__(config, state_manager, executor, paper_dir, output_dir)`
     - `run(state: PaperState, evidence_cards, asset_manifest, glossary, symbols) -> OrchestrationReport`
       1. 创建 Git snapshot
       2. `build_section_task_graph()` -> 获取任务列表
       3. 按依赖层级调度（Layer 内并发收集 Payload，跨 Layer 串行）
       4. 对每个 Payload: `validate_patch_payload()` -> `detect_conflicts()` -> `resolve_conflicts()` -> `apply_merge()`
       5. 串行写入 .tex 文件 + 更新 glossary/symbols
       6. 运行 `run_all_gates()` 验证
       7. 运行 `compile_single_section()` 验证
       8. 更新 `paper_state.json` 状态
       9. Git commit
  3. 实现 `_dispatch_role_tasks(tasks, executor) -> list[Payload]`
  4. 实现 `_merge_and_persist(payloads, state, glossary, symbols) -> PaperState`
  5. 实现 `_post_merge_validation(state) -> GateReport`
  6. 实现 `_handle_failure(error, snapshot_hash) -> None`（回滚逻辑）
  7. 更新 `agents/__init__.py` 导出核心类
  8. 编写集成测试（mock executor，验证完整 plan->dispatch->merge->validate 流程）
- **验收标准**: `uv run pytest tests/test_agents/test_orchestrator.py` 全绿，含成功流程 + 失败回滚

### Task 7: State Manager 增强
- **类型**: 后端增强
- **文件范围**:
  - `src/vibewriting/writing/state_manager.py` (修改)
  - `tests/test_writing/test_state_manager.py` (修改)
- **依赖**: 无
- **实施步骤**:
  1. 新增 `update_section_payload(state, section_id, claim_ids, asset_ids, citation_keys, word_count, paragraph_count) -> PaperState`
     - 一次性批量更新 section 的多个字段（减少中间状态）
  2. 新增 `set_current_section_index(state, index) -> PaperState`
  3. 新增 `batch_update_sections(state, updates: dict[str, dict]) -> PaperState`
     - 多章节批量状态更新（用于合并后一次性落盘）
  4. 扩展现有测试文件，补充新接口测试
- **验收标准**: `uv run pytest tests/test_writing/test_state_manager.py` 全绿，新增方法 100% 覆盖

### Task 8: 质量门禁增强 + 引用完整性修补
- **类型**: 后端增强
- **文件范围**:
  - `src/vibewriting/writing/quality_gates.py` (修改)
  - `src/vibewriting/contracts/integrity.py` (修改)
  - `tests/test_writing/test_quality_gates.py` (修改)
  - `tests/test_contracts.py` (修改)
- **依赖**: 无
- **实施步骤**:
  1. 增强 `check_terminology_consistency()`：
     - 检测同一术语在不同章节的定义是否一致（cross-section check）
     - 检测 glossary 中存在但全文从未使用的"幽灵术语"
     - 检测全文出现但 glossary 中未定义的新术语（warning）
  2. 在 `integrity.py` 中增加术语/符号完整性校验：
     - `validate_glossary_integrity(paper_state, glossary) -> list[IntegrityViolation]`
     - `validate_symbol_integrity(paper_state, symbols) -> list[IntegrityViolation]`
  3. 在 `validate_referential_integrity()` 中实际调用 glossary/symbols 校验
  4. 补充测试：术语冲突场景、符号不一致场景、幽灵术语检测
- **验收标准**: `uv run pytest tests/test_writing/test_quality_gates.py tests/test_contracts.py` 全绿

### Task 9: orchestrate-writing Skill
- **类型**: Claude Code Skill
- **文件范围**:
  - `.claude/skills/orchestrate-writing/SKILL.md` (新增)
- **依赖**: Task 6
- **实施步骤**:
  1. 定义 Skill 元数据（name, description）
  2. 定义输入参数（topic, title, resume, executor_type）
  3. 定义前置条件检查（Phase 4 产物存在性验证）
  4. 定义工作流步骤：
     - Step 1: 加载前置产物（evidence_cards, asset_manifest, glossary, symbols）
     - Step 2: 加载或创建 paper_state.json
     - Step 3: Approval Gate — 确认进入多 Agent 编排
     - Step 4: 创建 Git snapshot
     - Step 5: 调用 WritingOrchestrator.run()
     - Step 6: 展示 OrchestrationReport
     - Step 7: Approval Gate — 确认多 Agent 合并结果
     - Step 8: 全量编译验证
     - Step 9: 最终报告
  5. 定义恢复机制（从 paper_state.json 的 phase 字段恢复）
  6. 定义 Python 模块参考和输出产物清单
- **验收标准**: Skill 文档完整，工作流步骤可执行

## 文件冲突检查

| Task | 文件范围 | 冲突 |
|------|----------|------|
| Task 1 | agents/contracts.py, tests/test_agents/test_contracts.py | - |
| Task 2 | agents/planner.py, tests/test_agents/test_planner.py | - |
| Task 3 | agents/merge_protocol.py, tests/test_agents/test_merge_protocol.py | - |
| Task 4 | agents/git_safety.py, tests/test_agents/test_git_safety.py | - |
| Task 5 | agents/executor.py, tests/test_agents/test_executor.py | - |
| Task 6 | agents/orchestrator.py, agents/__init__.py, tests/test_agents/test_orchestrator.py | - |
| Task 7 | writing/state_manager.py, tests/test_writing/test_state_manager.py | - |
| Task 8 | writing/quality_gates.py, contracts/integrity.py, tests | - |
| Task 9 | .claude/skills/orchestrate-writing/SKILL.md | - |

✅ 无文件冲突 — 所有任务文件范围完全隔离

## 并行分组

```
Layer 1 (并行, 4 Builders): Task 1, Task 4, Task 7, Task 8
    |
    v
Layer 2 (并行, 3 Builders): Task 2, Task 3, Task 5
    |
    v
Layer 3 (串行, 1 Builder): Task 6
    |
    v
Layer 4 (串行, 1 Builder): Task 9
```

## 测试覆盖目标

- 新增测试文件: 8 个（tests/test_agents/ 下 7 个 + conftest.py）
- 修改测试文件: 3 个
- 覆盖率目标: >=90%（与现有 93% 持平）
- 预估新增测试数: ~120-150 tests

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| 多 Agent 输出格式漂移 | SectionPatchPayload Pydantic 强校验 + validate_contract |
| 并发写冲突 | Orchestrator 单写者串行落盘 |
| 术语/符号冲突自动裁决失败 | glossary/symbols 硬裁决源 + 人工 Approval Gate 兜底 |
| Git 回滚误伤 | 限定管辖路径（paper/ + output/），非管辖不回滚 |
| Agent Teams 不稳定 | Sub-agents 为默认，Team 仅保留接口 |
| 上下文窗口超限 | 证据卡按需注入 + Prompt 缓存排布 |
