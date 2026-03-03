---
name: vibewriting-paper
description: 端到端论文写作：从主题到可编译 LaTeX 论文 + PDF 的完整自动化工作流
triggers:
  - "write paper"
  - "写论文"
  - "一键生成论文"
  - "端到端生成论文"
  - "generate paper"
  - "论文自动写作"
---

# vibewriting-paper

端到端论文写作主入口 Skill。输入研究主题，自动完成数据管线 -> 文献检索 -> 草稿撰写 -> 多 Agent 编排 -> 编译审查，输出可编译 LaTeX 论文和 PDF。

## 输入参数

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `topic` | 必需 | — | 论文研究主题（如："基于 Transformer 的自然语言处理综述"） |
| `config_path` | 可选 | `paper_config.yaml` | YAML 配置文件路径，不存在时使用默认配置 |
| `data_dir` | 可选 | `null` | 原始数据目录路径，提供时运行数据管线 |
| `resume` | 可选 | `false` | 是否从 `output/checkpoint.json` 恢复上次中断的运行 |

---

## 工作流程总览

```
Step 0: 配置加载
Step 1: 检查点检测（resume 支持）
Step 2: 环境验证
Step 3: 数据管线（Phase 2）
  └── Step 3.5: Approval Gate
Step 4: 文献检索（Phase 3）
  └── Step 4.5: Approval Gate
Step 5: 草稿撰写（Phase 4）
  └── Step 5.5: Approval Gate
Step 6: 多 Agent 编排（Phase 5，writing_mode="multi" 时执行）
  └── Step 6.5: Approval Gate
Step 7: 编译 + 审查（Phase 6）
  └── Step 7.5: Approval Gate
Step 8: 指标汇总
Step 9: 最终输出
```

---

## Step 0: 配置加载

读取并合并配置，将 Skill 入参作为最高优先级的 overrides：

```python
from vibewriting.config_paper import load_paper_config, merge_config
from pathlib import Path

# 加载基础配置（config_path 不存在时返回默认配置）
config_path = Path(config_path) if config_path else Path("paper_config.yaml")
base_config = load_paper_config(config_path)

# 构建 overrides：仅包含 Skill 显式传入的非 None 参数
overrides = {}
if topic:
    overrides["topic"] = topic
if data_dir:
    overrides["data_dir"] = data_dir

# 不可变合并：返回新的 PaperConfig，base_config 不被修改
config = merge_config(base_config, overrides)

print(f"配置加载完成:")
print(f"  主题: {config.topic}")
print(f"  语言: {config.language}")
print(f"  写作模式: {config.writing_mode}")
print(f"  章节: {config.sections}")
print(f"  文献查询数: {config.literature_query_count}")
print(f"  最小证据卡数: {config.min_evidence_cards}")
print(f"  随机种子: {config.random_seed}")
print(f"  auto_approve: {config.auto_approve}")
```

检查点检测准备：

```python
import uuid

run_id = str(uuid.uuid4())[:8]  # 生成简短 run_id，用于本次运行标识
```

---

## Step 1: 检查点检测

检测是否存在可恢复的检查点：

```python
from vibewriting.checkpoint import detect_checkpoint, get_resume_phase, PHASE_ORDER
from pathlib import Path

output_dir = Path("output")
cp = detect_checkpoint(output_dir)

if resume and cp is not None:
    resume_phase = get_resume_phase(cp)
    print(f"发现检查点（run_id={cp.run_id}，主题={cp.topic}）")
    print(f"  创建时间: {cp.created_at}")
    print(f"  需从阶段 '{resume_phase}' 继续")
    print(f"  各阶段状态:")
    for phase in PHASE_ORDER:
        record = cp.phases.get(phase)
        status = record.status if record else "not_started"
        print(f"    - {phase}: {status}")
    # 沿用旧 run_id 保持连续性
    run_id = cp.run_id
else:
    # 创建新检查点
    from vibewriting.checkpoint import create_checkpoint, save_checkpoint

    cp = create_checkpoint(run_id=run_id, topic=config.topic, config=config.model_dump())
    save_checkpoint(cp, output_dir)
    print(f"已创建新检查点（run_id={run_id}）")
```

> 说明：`PHASE_ORDER` = `["infrastructure", "data_pipeline", "literature", "single_draft", "multi_agent", "compilation", "integration"]`

---

## Step 2: 环境验证

运行环境检查脚本，确认所有必需依赖可用：

```bash
uv run scripts/validate_env.py --json
```

解析 JSON 输出，检查退出码：
- 退出码 0：全部通过，继续执行
- 退出码 1：必需依赖失败 -> 停止并告知用户缺少哪些依赖
- 退出码 2：可选依赖失败（如 TeX Live）-> 继续执行，但后续编译步骤可能跳过

若必需依赖验证失败，在检查点中记录失败并终止：

```python
from vibewriting.checkpoint import update_phase, PhaseStatus, save_checkpoint

cp = update_phase(cp, "infrastructure", PhaseStatus.failed, error="必需环境依赖缺失，请查看验证报告")
save_checkpoint(cp, output_dir)
# 告知用户：请修复环境后使用 resume=true 重新运行
```

环境验证通过后更新检查点：

```python
cp = update_phase(cp, "infrastructure", PhaseStatus.completed)
save_checkpoint(cp, output_dir)
```

---

## Step 3: 数据管线（Phase 2）

仅当 `config.data_dir` 不为空时执行：

```python
from vibewriting.checkpoint import update_phase, PhaseStatus, save_checkpoint, should_skip_phase

# 检查是否可跳过（resume 模式下已完成的阶段）
if should_skip_phase(cp, "data_pipeline"):
    print("data_pipeline 阶段已完成，跳过（resume 模式）")
elif config.data_dir:
    # 标记阶段开始
    cp = update_phase(cp, "data_pipeline", PhaseStatus.in_progress)
    save_checkpoint(cp, output_dir)

    # 运行数据管线
    # uv run python -m vibewriting.pipeline.cli run \
    #   --data-dir {config.data_dir} \
    #   --output-dir output \
    #   --seed {config.random_seed}

    # 成功后更新检查点
    cp = update_phase(cp, "data_pipeline", PhaseStatus.completed)
    save_checkpoint(cp, output_dir)
else:
    print("未提供 data_dir，跳过数据管线")
    cp = update_phase(cp, "data_pipeline", PhaseStatus.completed)
    save_checkpoint(cp, output_dir)
```

实际执行命令：

```bash
uv run python -m vibewriting.pipeline.cli run \
  --data-dir {config.data_dir} \
  --output-dir output \
  --seed {config.random_seed}
```

### Step 3.5: Approval Gate — 数据管线确认

如 `config.auto_approve=false` 且执行了数据管线，使用 `AskUserQuestion` 展示数据资产摘要：

```
数据管线已完成。

产物摘要：
- output/asset_manifest.json: 已生成
- output/figures/: 图表文件（如有）
- output/tables/: 表格文件（如有）
- data/processed/: 清洗后数据

请选择：
1. 继续文献检索
2. 查看 asset_manifest.json 详情
3. 中止并保留检查点（可用 resume=true 继续）
```

选项：
- 选项 1: "继续文献检索" — 继续下一步
- 选项 2: "查看详情" — 展示 `output/asset_manifest.json` 内容后再次询问
- 选项 3: "中止" — 停止工作流，提示用户可用 `resume=true` 继续

---

## Step 4: 文献检索（Phase 3）

调用 `/vibewriting-literature` Skill 完成文献检索、去重、证据卡生成和 BibTeX 更新。

首先标记阶段开始：

```python
if should_skip_phase(cp, "literature"):
    print("literature 阶段已完成，跳过（resume 模式）")
else:
    cp = update_phase(cp, "literature", PhaseStatus.in_progress)
    save_checkpoint(cp, output_dir)
```

调用参数：

| 参数 | 值 |
|------|-----|
| `query` | `config.topic` |
| `max_results` | `config.literature_query_count * 5`（每轮查询结果数） |
| `mode` | `headless`（若 `config.auto_approve=true`）或 `interactive` |

期望产物：
- `data/processed/literature/literature_cards.jsonl` — 证据卡 JSONL 缓存
- `paper/bib/references.bib` — 更新后的 BibTeX 数据库

完成后验证最小证据卡数量是否达标：

```python
from pathlib import Path

cards_path = Path("data/processed/literature/literature_cards.jsonl")
if cards_path.exists():
    card_count = sum(1 for line in cards_path.read_text(encoding="utf-8").splitlines() if line.strip())
    if card_count < config.min_evidence_cards:
        print(f"警告: 证据卡数量 ({card_count}) 低于最小要求 ({config.min_evidence_cards})")
        # 不终止，仅警告；用户可在 Approval Gate 决策
```

阶段完成后更新检查点：

```python
cp = update_phase(cp, "literature", PhaseStatus.completed)
save_checkpoint(cp, output_dir)
```

### Step 4.5: Approval Gate — 文献检索确认

如 `config.auto_approve=false`，使用 `AskUserQuestion` 展示证据卡摘要：

```
文献检索已完成。

证据卡摘要：
- 总计: N 张证据卡（来自 M 篇文献）
- 去重后: K 张（去重率: X%）
- 达标状态: [满足最小要求 N >= min_evidence_cards] 或 [警告: N < min_evidence_cards]
- 标签分布:
    - empirical: N 张
    - theoretical: N 张
    - survey: N 张
    - meta-analysis: N 张
- BibTeX 条目: N 条已添加至 paper/bib/references.bib

请选择：
1. 继续草稿撰写
2. 增补文献检索（重新运行 /vibewriting-literature 追加更多论文）
3. 中止并保留检查点
```

选项：
- 选项 1: "继续草稿撰写" — 继续下一步
- 选项 2: "增补文献检索" — 重新调用 `/vibewriting-literature`，完成后再次展示此门禁
- 选项 3: "中止" — 停止工作流

---

## Step 5: 草稿撰写（Phase 4）

调用 `/vibewriting-draft` Skill 完成 Evidence-First 草稿撰写。

首先标记阶段开始：

```python
if should_skip_phase(cp, "single_draft"):
    print("single_draft 阶段已完成，跳过（resume 模式）")
else:
    cp = update_phase(cp, "single_draft", PhaseStatus.in_progress)
    save_checkpoint(cp, output_dir)
```

调用参数：

| 参数 | 值 |
|------|-----|
| `topic` | `config.topic` |
| `resume` | `false`（新运行）或 `true`（resume 模式下已有 paper_state.json） |

期望产物：
- `paper/sections/*.tex` — 各章节 LaTeX 文件（带 CLAIM_ID 溯源注释）
- `output/paper_state.json` — 论文状态机（阶段、章节状态、质量指标）
- `output/glossary.json` — 术语表
- `output/symbols.json` — 数学符号表

阶段完成后更新检查点：

```python
cp = update_phase(cp, "single_draft", PhaseStatus.completed)
save_checkpoint(cp, output_dir)
```

### Step 5.5: Approval Gate — 草稿质量确认

如 `config.auto_approve=false`，读取 `output/paper_state.json` 并使用 `AskUserQuestion` 展示质量门禁结果：

```python
import json
from pathlib import Path

paper_state = json.loads(Path("output/paper_state.json").read_text(encoding="utf-8"))
metrics = paper_state.get("metrics", {})
sections = paper_state.get("sections", [])
drafted = [s for s in sections if s.get("status") == "drafted"]
```

展示格式：

```
草稿撰写已完成。

质量门禁结果：
- 完成章节: N/total（N 章已通过质量门禁）
- 引用覆盖率: X.X%（目标 >= 50%）
- Claim 追溯率: X.X%（目标 >= 30%）
- 总词数: 约 NNNN 词
- 总引用数: N 条

各章节状态：
- 引言: [drafted / gate_failed]
- 相关工作: [drafted / gate_failed]
- 方法: [drafted / gate_failed]
- 实验: [drafted / gate_failed]
- 结论: [drafted / gate_failed]

请选择：
1. 继续（若 writing_mode=multi 则进入多 Agent 编排，否则跳至编译审查）
2. 查看 paper_state.json 详情
3. 中止并保留检查点
```

选项：
- 选项 1: "继续" — 根据 `config.writing_mode` 决定下一步
- 选项 2: "查看详情" — 展示 `output/paper_state.json` 内容后再次询问
- 选项 3: "中止" — 停止工作流

---

## Step 6: 多 Agent 编排（Phase 5）

仅当 `config.writing_mode="multi"` 时执行；`writing_mode="single"` 时跳过此步骤并直接进入 Step 7。

首先标记阶段开始：

```python
if config.writing_mode != "multi":
    print("writing_mode=single，跳过多 Agent 编排阶段")
    cp = update_phase(cp, "multi_agent", PhaseStatus.completed)
    save_checkpoint(cp, output_dir)
elif should_skip_phase(cp, "multi_agent"):
    print("multi_agent 阶段已完成，跳过（resume 模式）")
else:
    cp = update_phase(cp, "multi_agent", PhaseStatus.in_progress)
    save_checkpoint(cp, output_dir)
```

调用 `/vibewriting-orchestrate` Skill 参数：

| 参数 | 值 |
|------|-----|
| `topic` | `config.topic` |
| `resume` | 同上层 `resume` 参数 |
| `executor_type` | `mock`（默认测试模式）|
| `max_rounds` | `3`（默认）|

期望产物：
- 更新后的 `paper/sections/*.tex`
- 更新后的 `output/paper_state.json`（含 Agent 贡献指标）
- Git 快照记录

阶段完成后更新检查点：

```python
cp = update_phase(cp, "multi_agent", PhaseStatus.completed)
save_checkpoint(cp, output_dir)
```

### Step 6.5: Approval Gate — 多 Agent 编排结果确认

仅当 `config.writing_mode="multi"` 且 `config.auto_approve=false` 时展示。

使用 `AskUserQuestion` 展示合并结果：

```
多 Agent 编排已完成。

编排摘要：
- 编排轮数: N 轮
- 章节完成: N/total
- 检测到的冲突: N 个（已解决: M 个 / 未解决: K 个）
- 质量门禁: 全通过 / M 章节有警告

未解决冲突（如有）：
- 术语冲突: ...
- 符号冲突: ...
- 引用冲突: ...

请选择：
1. 批准，继续编译和审查
2. 重新运行编排（清除当前输出后重试）
3. 手动修改后继续
4. 中止并保留检查点
```

选项：
- 选项 1: "批准，继续" — 进入 Step 7
- 选项 2: "重新运行" — 重新调用 `/vibewriting-orchestrate`
- 选项 3: "手动修改" — 告知用户可直接编辑 `paper/sections/*.tex`，编辑完成后回复继续
- 选项 4: "中止" — 停止工作流

---

## Step 7: 编译 + 审查（Phase 6）

调用 `/vibewriting-review` Skill 完成 LaTeX 自愈编译、引文审计、契约一致性验证和模拟同行评审。

首先标记阶段开始：

```python
if should_skip_phase(cp, "compilation"):
    print("compilation 阶段已完成，跳过（resume 模式）")
else:
    cp = update_phase(cp, "compilation", PhaseStatus.in_progress)
    save_checkpoint(cp, output_dir)
```

调用 `/vibewriting-review` Skill（选择"全量审查"选项）。实际执行：

```bash
uv run python -m vibewriting.latex.cli run
```

如用户希望跳过外部 API 验证：

```bash
uv run python -m vibewriting.latex.cli run --skip-external-api
```

期望产物：
- `paper/build/main.pdf` — 编译后的论文 PDF
- `output/phase6_report.json` — Phase 6 完整报告
- `output/peer_review.md` — 同行评审 Markdown 报告
- `output/patch_report.json` — 自愈补丁记录（如有）

阶段完成后更新检查点：

```python
cp = update_phase(cp, "compilation", PhaseStatus.completed)
save_checkpoint(cp, output_dir)
```

### Step 7.5: Approval Gate — 审查报告确认

如 `config.auto_approve=false`，读取 `output/phase6_report.json` 并使用 `AskUserQuestion` 展示审查报告：

```python
import json
from pathlib import Path

phase6_report = json.loads(Path("output/phase6_report.json").read_text(encoding="utf-8"))
```

展示格式：

```
编译和审查已完成。

审查报告摘要：
- 编译状态: [成功 / 失败]
- 自愈轮次: N 轮
- 引文验证: N 条已验证（可疑: M 条，孤立 claim: K 条）
- 契约违规: N 条
- 同行评审分数: X.X/10 (Verdict: Accept / Minor Revision / Major Revision / Reject)

关键问题（如有）：
- [CRITICAL] ...
- [HIGH] ...
- [MEDIUM] ...

输出文件：
- paper/build/main.pdf
- output/phase6_report.json
- output/peer_review.md

请选择：
1. 接受当前状态，继续汇总指标
2. 查看详细同行评审报告（output/peer_review.md）
3. 修复关键问题后重新审查（重新运行 /vibewriting-review）
4. 中止并保留检查点
```

选项：
- 选项 1: "接受" — 继续 Step 8
- 选项 2: "查看详情" — 读取并展示 `output/peer_review.md`，之后再次询问
- 选项 3: "修复并重新审查" — 重新调用 `/vibewriting-review`
- 选项 4: "中止" — 停止工作流

---

## Step 8: 指标汇总

收集并保存本次运行的完整指标：

```python
from vibewriting.metrics import build_run_metrics, save_run_metrics
from vibewriting.checkpoint import detect_checkpoint
from pathlib import Path
import json

output_dir = Path("output")
data_dir = Path(config.data_dir) if config.data_dir else Path("data")

# 重新加载最新检查点
cp = detect_checkpoint(output_dir)
checkpoint_dict = json.loads(cp.model_dump_json()) if cp else {}

# 构建运行指标报告
report = build_run_metrics(
    run_id=run_id,
    topic=config.topic,
    checkpoint=checkpoint_dict,
    output_dir=output_dir,
    data_dir=data_dir,
)

# 原子写入 output/run_metrics.json
metrics_path = save_run_metrics(report, output_dir)
print(f"指标报告已保存: {metrics_path}")
```

更新最终检查点状态：

```python
cp = update_phase(cp, "integration", PhaseStatus.completed)
save_checkpoint(cp, output_dir)
print(f"检查点已更新，run_id={run_id}，所有阶段完成")
```

---

## Step 9: 最终输出

展示完整运行总结：

```
论文写作完成！

输出文件：
- PDF: paper/build/main.pdf
- 章节源码: paper/sections/*.tex
- 参考文献: paper/bib/references.bib
- 论文状态: output/paper_state.json

运行指标摘要（output/run_metrics.json）：
- run_id: {run_id}
- 主题: {config.topic}
- 文献: {report.literature.evidence_cards} 张证据卡（去重率 {report.literature.dedup_rate:.1%}）
- 写作: {report.writing.total_sections} 章节，{report.writing.total_words} 词
  - 引用覆盖率: {report.writing.citation_coverage:.1%}
  - Claim 追溯率: {report.writing.claim_traceability:.1%}
- 编译: {'首次成功' if report.compilation.first_pass_success else f'自愈 {report.compilation.heal_rounds} 轮后成功'}
  - 同行评审: {report.compilation.peer_review_score:.1f}/10 ({report.compilation.peer_review_verdict})
  - 契约违规: {report.compilation.contract_violations} 条
- 各阶段耗时: {report.phase_durations}

检查点: output/checkpoint.json（run_id={run_id}）
```

---

## 错误处理与恢复

### 阶段失败时的标准处理

任意阶段抛出异常时：

```python
try:
    # 执行阶段逻辑
    pass
except Exception as e:
    # 1. 将检查点标记为失败，保留错误信息
    cp = update_phase(cp, phase_name, PhaseStatus.failed, error=str(e))
    save_checkpoint(cp, output_dir)

    # 2. 告知用户可恢复
    print(f"阶段 '{phase_name}' 失败：{e}")
    print(f"检查点已保存（output/checkpoint.json）。")
    print(f"修复问题后，使用 resume=true 重新运行 /vibewriting-paper 即可从当前阶段继续。")

    # 3. 抛出异常终止当前 Skill
    raise
```

### resume=true 恢复逻辑

当 `resume=true` 且 `output/checkpoint.json` 存在时：

1. 读取检查点，调用 `get_resume_phase(cp)` 获取第一个未完成阶段
2. 跳过所有已 `completed` 的阶段（`should_skip_phase` 返回 `True`）
3. 从未完成阶段继续执行

恢复示例：

```python
from vibewriting.checkpoint import detect_checkpoint, get_resume_phase, should_skip_phase

cp = detect_checkpoint(Path("output"))
if cp and resume:
    resume_phase = get_resume_phase(cp)
    print(f"恢复运行：从阶段 '{resume_phase}' 继续（run_id={cp.run_id}）")
```

### auto_approve=true 模式

当 `config.auto_approve=true` 时，跳过所有 Approval Gate（Step 3.5、4.5、5.5、6.5、7.5），全自动无需人工确认。适用于 CI/CD 或批量测试场景。

---

## 检查点阶段映射

| 工作流步骤 | 检查点阶段名称 | 说明 |
|------------|----------------|------|
| Step 2 | `infrastructure` | 环境验证 |
| Step 3 | `data_pipeline` | 数据管线 |
| Step 4 | `literature` | 文献检索 + 证据卡 |
| Step 5 | `single_draft` | 草稿撰写 |
| Step 6 | `multi_agent` | 多 Agent 编排 |
| Step 7 | `compilation` | 编译 + 审查 |
| Step 8 | `integration` | 指标汇总 + 收尾 |

---

## Python 模块参考

```python
# 配置
from vibewriting.config_paper import load_paper_config, merge_config, PaperConfig

# 检查点
from vibewriting.checkpoint import (
    create_checkpoint,
    detect_checkpoint,
    update_phase,
    save_checkpoint,
    get_resume_phase,
    should_skip_phase,
    PhaseStatus,
    PHASE_ORDER,
)

# 指标
from vibewriting.metrics import (
    build_run_metrics,
    save_run_metrics,
    collect_literature_metrics,
    collect_writing_metrics,
    collect_compilation_metrics,
)
```

## 子 Skill 调用参考

| Skill | 触发条件 | 核心参数 |
|-------|----------|----------|
| `/vibewriting-literature` | Step 4 | `query=config.topic`, `max_results`, `mode` |
| `/vibewriting-draft` | Step 5 | `topic=config.topic`, `resume` |
| `/vibewriting-orchestrate` | Step 6（multi 模式） | `topic=config.topic`, `resume`, `executor_type`, `max_rounds` |
| `/vibewriting-review` | Step 7 | 全量审查模式 |

---

## 输出产物总览

| 产物 | 路径 | 来源阶段 |
|------|------|---------|
| 论文 PDF | `paper/build/main.pdf` | Phase 6（编译） |
| 章节 LaTeX | `paper/sections/*.tex` | Phase 4 / Phase 5 |
| 参考文献 | `paper/bib/references.bib` | Phase 3（文献检索） |
| 证据卡缓存 | `data/processed/literature/literature_cards.jsonl` | Phase 3 |
| 论文状态 | `output/paper_state.json` | Phase 4 / Phase 5 |
| 术语表 | `output/glossary.json` | Phase 4 |
| 符号表 | `output/symbols.json` | Phase 4 |
| 资产清单 | `output/asset_manifest.json` | Phase 2（数据管线） |
| Phase 6 报告 | `output/phase6_report.json` | Phase 6 |
| 同行评审报告 | `output/peer_review.md` | Phase 6 |
| 补丁记录 | `output/patch_report.json` | Phase 6（自愈编译） |
| 运行指标 | `output/run_metrics.json` | Step 8 |
| 检查点 | `output/checkpoint.json` | 全程持续更新 |

---

## 重要约束

- **Evidence-First 强制执行**: 每个 claim 必须有证据卡支撑，不允许无来源的文献引用
- **不可变配置**: `merge_config` 返回新对象，`base_config` 永不修改
- **原子写入**: 检查点和指标报告均通过 tmp -> rename 保证原子性
- **Git 安全**: 多 Agent 编排前自动创建 Git 快照，失败时可回滚
- **BibTeX UTF-8**: `.bib` 文件强制 UTF-8 编码，引用键仅 ASCII
- **VW_ 前缀**: 所有环境变量使用 `VW_` 命名空间（如 `VW_DIFY_API_KEY`）
- **不执行未确认的 git push**: 工作流内所有 git 操作均在本地进行
