# Team Plan: Phase 7 端到端集成

## 概述

将 Phase 1-6 的所有模块串联为一键式工作流，实现 "输入论文主题 → 输出 PDF + 审查报告 + 运行指标"。

## Codex 分析摘要

技术可行性高。Phase 1-6 已建成完整的模块化基础设施（507 tests），Phase 7 的核心工作是**编排层集成**而非新建底层能力。关键发现：
- `PaperState.phase` 字段已支持 `outline|drafting|review|complete` 状态机，可直接扩展为检查点
- `config.py` 的 `Settings(BaseSettings)` 模式可复用于 `PaperConfig`
- `pipeline/cli.py` 和 `latex/cli.py` 已有 Typer CLI 模式，指标收集可从现有产物文件聚合
- `SubAgentExecutor` 是 placeholder，但 write-paper Skill 通过 Claude Code Skill 机制编排，不依赖 Python 级 executor

## Gemini 分析摘要

Skill 工作流设计是核心。write-paper SKILL.md 作为顶层编排 Prompt，需要：
- 明确的阶段状态检测逻辑（读取 checkpoint.json 判断恢复点）
- 每个阶段间的 AskUserQuestion Approval Gate 交互设计
- 配置三层合并的清晰优先级：yaml < Skill 入参 < 用户运行时修改
- 错误恢复策略：阶段失败时保存检查点，下次运行自动跳过已完成阶段

## 技术方案

### 架构决策

1. **配置系统**: 新建 `src/vibewriting/config_paper.py`，使用 Pydantic BaseModel + PyYAML 加载，与现有 `config.py`（环境变量）互补
2. **检查点**: 新建 `src/vibewriting/checkpoint.py`，基于 `output/checkpoint.json` 文件持久化，恢复时执行 schema + integrity 验证
3. **指标汇总**: 新建 `src/vibewriting/metrics.py`，从现有产物文件（literature_cards.jsonl, paper_state.json, phase6_report.json, run_manifest.json）聚合
4. **主入口 Skill**: 新建 `.claude/skills/write-paper/SKILL.md`，编排调用 6 个已有 Skills + Python CLI
5. **依赖**: 需确认 PyYAML 是否在 pyproject.toml 中（pyyaml 或通过其他包间接引入）

### 新增依赖

- `pyyaml`: 用于 paper_config.yaml 解析（需添加到 pyproject.toml dependencies）

## 子任务列表

### Task 1: 配置系统 (config_paper.py + paper_config.yaml)

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/config_paper.py` (新建)
  - `paper_config.yaml` (新建，项目根目录)
  - `pyproject.toml` (追加 pyyaml 依赖)
  - `tests/test_config_paper.py` (新建)
- **依赖**: 无
- **实施步骤**:
  1. 在 `pyproject.toml` 的 `dependencies` 中添加 `pyyaml>=6.0`，运行 `uv sync`
  2. 创建 `src/vibewriting/config_paper.py`:
     - `PaperConfig(BaseModel)` 模型，字段:
       - `topic: str` — 论文主题（必填）
       - `language: Literal["zh", "en"] = "zh"` — 语言
       - `document_class: str = "ctexart"` — LaTeX 文档类
       - `sections: list[str]` — 章节列表，默认 5 章
       - `literature_query_count: int = 3` — 文献检索轮数
       - `min_evidence_cards: int = 5` — 最少证据卡数
       - `data_dir: str | None = None` — 数据目录（可选）
       - `random_seed: int = 42` — 随机种子
       - `writing_mode: Literal["single", "multi"] = "multi"` — 写作模式
       - `enable_ai_disclosure: bool = False` — AI 披露开关
       - `enable_anonymize: bool = False` — 匿名化开关
       - `natbib_style: str = "plainnat"` — natbib 引用风格
       - `auto_approve: bool = False` — 跳过 Approval Gates（危险标记）
     - `load_paper_config(path: Path | None = None) -> PaperConfig` — 从 YAML 加载，path 为 None 时使用默认值
     - `merge_config(base: PaperConfig, overrides: dict) -> PaperConfig` — 不可变合并，返回新对象
     - `save_paper_config(config: PaperConfig, path: Path) -> None` — 序列化为 YAML
  3. 创建 `paper_config.yaml` 默认模板（含注释说明每个字段）
  4. 编写 `tests/test_config_paper.py`（≥15 tests）:
     - 默认值测试、YAML 加载、合并优先级、无效值拒绝、序列化往返
- **验收标准**:
  - `uv run pytest tests/test_config_paper.py` 全部通过
  - `PaperConfig` 通过 JSON Schema 导出
  - 三层合并逻辑正确（yaml < overrides < runtime）

### Task 2: 检查点系统 (checkpoint.py)

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/checkpoint.py` (新建)
  - `tests/test_checkpoint.py` (新建)
- **依赖**: 无
- **实施步骤**:
  1. 创建 `src/vibewriting/checkpoint.py`:
     - `PhaseStatus(str, Enum)`: `not_started`, `in_progress`, `completed`, `failed`
     - `PhaseRecord(BaseModel)`: `status: PhaseStatus`, `started_at: datetime | None`, `completed_at: datetime | None`, `error: str | None`
     - `Checkpoint(BaseModel)`:
       - `run_id: str` — UUID
       - `topic: str`
       - `phases: dict[str, PhaseRecord]` — 7 个阶段状态
       - `config_snapshot: dict` — PaperConfig 快照
       - `created_at: datetime`
       - `updated_at: datetime`
     - `PHASE_ORDER: list[str] = ["infrastructure", "data_pipeline", "literature", "single_draft", "multi_agent", "compilation", "integration"]`
     - `detect_checkpoint(output_dir: Path) -> Checkpoint | None` — 读取 checkpoint.json
     - `validate_checkpoint(cp: Checkpoint, output_dir: Path, data_dir: Path) -> list[str]` — 验证完整性（文件存在 + schema check）
     - `save_checkpoint(cp: Checkpoint, output_dir: Path) -> None` — 原子写入
     - `create_checkpoint(run_id: str, topic: str, config: dict) -> Checkpoint` — 初始化新检查点
     - `update_phase(cp: Checkpoint, phase: str, status: PhaseStatus, error: str | None = None) -> Checkpoint` — 不可变更新
     - `get_resume_phase(cp: Checkpoint) -> str | None` — 找到第一个未完成阶段
     - `should_skip_phase(cp: Checkpoint, phase: str) -> bool` — 判断是否跳过
  2. 编写 `tests/test_checkpoint.py`（≥20 tests）:
     - 创建/保存/加载往返、阶段状态转换、恢复点检测、验证逻辑、不可变性
- **验收标准**:
  - `uv run pytest tests/test_checkpoint.py` 全部通过
  - 检查点文件为 JSON 格式，可通过 jsonschema 验证
  - 不可变模式：update_phase 返回新对象

### Task 3: 指标汇总 (metrics.py)

- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/metrics.py` (新建)
  - `tests/test_metrics.py` (新建)
- **依赖**: 无
- **实施步骤**:
  1. 创建 `src/vibewriting/metrics.py`:
     - `LiteratureMetrics(BaseModel)`:
       - `total_searched: int`, `after_dedup: int`, `evidence_cards: int`
       - `dedup_rate: float`, `tag_distribution: dict[str, int]`
     - `WritingMetrics(BaseModel)`:
       - `citation_coverage: float`, `claim_traceability: float`
       - `total_sections: int`, `total_words: int`, `total_claims: int`
     - `CompilationMetrics(BaseModel)`:
       - `first_pass_success: bool`, `heal_rounds: int`, `heal_success: bool`
       - `peer_review_score: float`, `peer_review_verdict: str`
       - `contract_violations: int`
     - `RunMetricsReport(BaseModel)`:
       - `run_id: str`, `topic: str`, `created_at: datetime`
       - `phase_durations: dict[str, float | None]` — 每阶段耗时(秒)
       - `literature: LiteratureMetrics`
       - `writing: WritingMetrics`
       - `compilation: CompilationMetrics`
       - `total_duration_sec: float | None`
     - `collect_literature_metrics(cards_path: Path) -> LiteratureMetrics` — 从 JSONL 聚合
     - `collect_writing_metrics(paper_state_path: Path) -> WritingMetrics` — 从 paper_state.json 聚合
     - `collect_compilation_metrics(phase6_report_path: Path) -> CompilationMetrics` — 从 phase6_report.json 聚合
     - `build_run_metrics(run_id: str, topic: str, checkpoint: dict, output_dir: Path, data_dir: Path) -> RunMetricsReport` — 汇总所有指标
     - `save_run_metrics(report: RunMetricsReport, output_dir: Path) -> Path` — 保存 run_metrics.json
  2. 编写 `tests/test_metrics.py`（≥18 tests）:
     - 各收集器独立测试、空文件/缺失文件降级、汇总逻辑、序列化
- **验收标准**:
  - `uv run pytest tests/test_metrics.py` 全部通过
  - 缺失产物文件时优雅降级（返回零值而非崩溃）
  - run_metrics.json 可通过 JSON Schema 验证

### Task 4: write-paper Skill (主入口)

- **类型**: 编排层 (Skill Prompt)
- **文件范围**:
  - `.claude/skills/write-paper/SKILL.md` (新建)
- **依赖**: Task 1, Task 2, Task 3
- **实施步骤**:
  1. 创建 `.claude/skills/write-paper/SKILL.md`，包含:
     - **触发条件**: 用户请求写论文、一键生成论文
     - **输入参数**: topic (必填), config_path (可选), data_dir (可选), resume (bool, 可选)
     - **工作流步骤**:
       - Step 0: 配置加载 — 读取 paper_config.yaml，合并 Skill 入参
       - Step 1: 检查点检测 — 读取 output/checkpoint.json，决定恢复点
       - Step 2: 环境验证 — 运行 `uv run scripts/validate_env.py --json`
       - Step 3: 数据管线 (Phase 2) — 如有 data_dir，运行 `uv run python -m vibewriting.pipeline.cli run`
       - Step 3.5: Approval Gate — AskUserQuestion 展示数据资产摘要
       - Step 4: 文献检索 (Phase 3) — 调用 search-literature Skill
       - Step 4.5: Approval Gate — AskUserQuestion 展示证据卡摘要
       - Step 5: 草稿撰写 (Phase 4) — 调用 write-draft Skill
       - Step 5.5: Approval Gate — AskUserQuestion 展示草稿质量门禁结果
       - Step 6: 多Agent编排 (Phase 5) — 调用 orchestrate-writing Skill（如 writing_mode=multi）
       - Step 6.5: Approval Gate — AskUserQuestion 展示合并结果
       - Step 7: 编译+审查 (Phase 6) — 调用 review-paper Skill
       - Step 7.5: Approval Gate — AskUserQuestion 展示审查报告
       - Step 8: 指标汇总 — 运行 Python 收集指标，保存 run_metrics.json
       - Step 9: 最终输出 — 展示 PDF 路径 + 审查报告 + 运行指标摘要
     - **检查点更新**: 每个 Step 完成后更新 checkpoint.json
     - **错误处理**: 阶段失败时保存检查点，提示用户可恢复
     - **auto_approve 模式**: 跳过 AskUserQuestion（需用户在配置中显式启用）
  2. Skill 中引用的 Python 命令:
     - `uv run python -c "from vibewriting.config_paper import load_paper_config; ..."` — 配置加载
     - `uv run python -c "from vibewriting.checkpoint import detect_checkpoint; ..."` — 检查点检测
     - `uv run python -c "from vibewriting.metrics import build_run_metrics, save_run_metrics; ..."` — 指标汇总
- **验收标准**:
  - SKILL.md 结构完整，步骤清晰
  - 每个阶段有明确的输入/输出/检查点更新
  - Approval Gate 交互设计合理（展示摘要 + 选项）

### Task 5: 用户文档

- **类型**: 文档
- **文件范围**:
  - `docs/quickstart.md` (新建)
  - `docs/config-reference.md` (新建)
  - `docs/faq.md` (新建)
  - `docs/cross-project-guide.md` (新建)
- **依赖**: 无（可与 Layer 1 并行）
- **实施步骤**:
  1. `docs/quickstart.md`: 快速开始指南
     - 前置条件（Python 3.12, uv, TeX Live, Dify 可选）
     - 安装步骤（uv sync, validate_env.py）
     - 一键运行示例（/write-paper "论文主题"）
     - 预期输出说明
  2. `docs/config-reference.md`: 配置参考
     - paper_config.yaml 字段说明表
     - .env 环境变量说明表
     - 三层配置优先级说明
  3. `docs/faq.md`: 常见问题
     - TeX Live 安装问题
     - Dify 凭据配置
     - 编译失败排查
     - 检查点恢复方法
  4. `docs/cross-project-guide.md`: 跨项目知识迁移
     - Additional Directories 配置
     - 从历史论文迁移 LaTeX 模式
- **验收标准**:
  - 文档简体中文，结构清晰
  - 快速开始指南可独立执行

## 文件冲突检查

✅ 无冲突 — 所有 Task 的文件范围完全隔离：

| Task | 文件范围 | 冲突 |
|------|---------|------|
| Task 1 | config_paper.py, paper_config.yaml, pyproject.toml, test_config_paper.py | 无 |
| Task 2 | checkpoint.py, test_checkpoint.py | 无 |
| Task 3 | metrics.py, test_metrics.py | 无 |
| Task 4 | .claude/skills/write-paper/SKILL.md | 无 |
| Task 5 | docs/*.md | 无 |

注: Task 1 修改 pyproject.toml（追加依赖），其他 Task 不触碰此文件。

## 并行分组

- **Layer 1 (并行, 3 个 Builder)**: Task 1 + Task 2 + Task 3
  - 三个独立 Python 模块，文件无重叠，可完全并行
- **Layer 2 (依赖 Layer 1, 1 个 Builder)**: Task 4
  - write-paper Skill 需要引用 Task 1-3 的模块接口
- **Layer 3 (独立, 可与 Layer 1 并行, 1 个 Builder)**: Task 5
  - 纯文档，不依赖代码实现

## 验证标准（Phase 7 整体）

- [ ] `uv run pytest` 全部通过（含新增 ~53 tests，总计 ~560 tests）
- [ ] paper_config.yaml 可正确加载和合并
- [ ] checkpoint.json 支持创建/保存/加载/恢复
- [ ] run_metrics.json 可从现有产物聚合生成
- [ ] write-paper SKILL.md 步骤完整，覆盖全部 7 个阶段
- [ ] 用户文档覆盖快速开始、配置参考、FAQ、跨项目迁移
