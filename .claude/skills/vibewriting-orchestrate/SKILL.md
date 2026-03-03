---
name: vibewriting-orchestrate
description: 多 Agent 编排写作：并行生成、审阅和格式化 LaTeX 章节
---

# vibewriting-orchestrate

多 Agent 编排的论文撰写工作流。协调多个 AI Agent 角色（Storyteller、Analyst、Critic、Formatter）并行生成、审阅和格式化 LaTeX 章节，含冲突解决和质量门禁。

## 触发条件

"orchestrate writing"、"multi-agent draft"、"agent orchestration"、"parallel writing"

## 前置条件

执行前必须验证以下文件存在且有效：

```bash
test -f data/processed/literature/literature_cards.jsonl && echo "OK" || echo "MISSING: 请先运行 /vibewriting-literature"
test -f output/asset_manifest.json && echo "OK" || echo "MISSING: 请先运行数据管线"
test -f paper/bib/references.bib && echo "OK" || echo "MISSING: 参考文献数据库缺失"
test -f output/paper_state.json && echo "OK" || echo "MISSING: 请先运行 /vibewriting-draft 生成 paper_state.json"
```

如有任何前置文件缺失，停止并告知用户需要先完成相应的前序步骤。

## 输入参数

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `topic` | 必需 | — | 论文研究主题 |
| `title` | 可选 | 自动生成 | 论文标题 |
| `resume` | 可选 | `false` | 是否从 paper_state.json 恢复 |
| `executor_type` | 可选 | `mock` | 执行器类型：mock / subagent |
| `max_rounds` | 可选 | `3` | 最大编排轮数 |

## 工作流程

### Step 1: 加载前置产物

```python
from vibewriting.literature.cache import LiteratureCache
from vibewriting.models.glossary import Glossary, SymbolTable
from vibewriting.contracts.integrity import _extract_bib_keys
from pathlib import Path
import json

# 加载证据卡
cache = LiteratureCache(Path("data/processed/literature/literature_cards.jsonl"))
cache.load()
all_cards = cache.all_cards()

# 加载资产清单
with open("output/asset_manifest.json") as f:
    asset_manifest = json.load(f)

# 加载词汇表和符号表（可选，不存在则跳过）
glossary = None
symbols = None
if Path("output/glossary.json").exists():
    glossary = Glossary.model_validate_json(
        Path("output/glossary.json").read_text(encoding="utf-8")
    )
if Path("output/symbols.json").exists():
    symbols = SymbolTable.model_validate_json(
        Path("output/symbols.json").read_text(encoding="utf-8")
    )

# 提取 BibTeX 键集合
bib_keys = _extract_bib_keys(Path("paper/bib/references.bib"))

print(f"已加载 {len(all_cards)} 张证据卡")
print(f"已加载 {len(asset_manifest.get('assets', []))} 个资产")
print(f"已加载 {len(bib_keys)} 个 BibTeX 键")
```

### Step 2: 加载 PaperState

```python
from vibewriting.writing.state_manager import PaperStateManager

manager = PaperStateManager(Path("output/paper_state.json"))
state = manager.load()

if state is None:
    raise FileNotFoundError(
        "output/paper_state.json 不存在。请先运行 /vibewriting-draft 生成论文状态文件。"
    )

print(f"已加载论文状态: {state.title}")
print(f"章节数: {len(state.sections)}")
```

### Step 3: 编排计划确认门禁

使用 `AskUserQuestion` 工具展示编排计划并等待用户确认：

```
📋 Multi-Agent 编排计划:
- 论文: {state.title}
- 章节数: {len(state.sections)}
- Agent 角色: Storyteller, Analyst, Critic, Formatter
- 执行器: {executor_type}
- 最大轮数: {max_rounds}

确认进入多 Agent 编排？
```

选项：
- 选项 1: "确认，开始编排"
- 选项 2: "取消"

### Step 4: 创建 Git 快照

```python
from vibewriting.agents.git_safety import create_snapshot_commit, has_uncommitted_changes

if has_uncommitted_changes(Path(".")):
    snapshot_hash = create_snapshot_commit(
        Path("."), f"snapshot: before multi-agent orchestration [{state.title}]"
    )
    print(f"Git 快照已创建: {snapshot_hash}")
```

### Step 5: 运行编排器

```python
from vibewriting.agents.orchestrator import OrchestratorConfig, WritingOrchestrator
from vibewriting.agents.executor import MockExecutor  # 生产环境替换为 SubAgentExecutor
import asyncio

config = OrchestratorConfig(
    max_rounds=max_rounds,
    enable_git_snapshots=True,
    executor_type=executor_type,
)

executor = MockExecutor()  # executor_type == "mock" 时使用

orchestrator = WritingOrchestrator(
    config=config,
    state_manager=manager,
    executor=executor,
    paper_dir=Path("paper"),
    output_dir=Path("output"),
)

report = asyncio.run(
    orchestrator.run(
        state=state,
        evidence_cards=all_cards,
        asset_manifest=asset_manifest,
        glossary=glossary,
        symbols=symbols,
        bib_keys=bib_keys,
    )
)
```

### Step 6: 展示编排结果

```
📊 编排结果:
- 总轮数: {len(report.rounds)}
- 章节完成: {report.sections_completed}/{report.total_sections}
- 冲突: {report.total_conflicts} (未解决: {report.unresolved_conflicts})
- 质量门禁: {report.final_gate_report_summary}
- 状态: 成功 / 部分完成
```

### Step 7: 结果审查门禁

使用 `AskUserQuestion` 工具展示合并结果，供用户审查：

展示内容：
- 已生成章节列表及状态
- 未解决的冲突详情（如有）
- 质量门禁检查结果
- 每章节的 Agent 贡献摘要

选项：
- 选项 1: "批准，继续全量编译"
- 选项 2: "拒绝，重新运行编排"
- 选项 3: "手动修改后继续"

### Step 8: 全量编译

如果 TeX Live 可用（用户选择继续）：

```bash
bash build.sh build
```

如果编译失败：
1. 分析 `paper/build/main.log` 中的错误信息
2. 定位出错的 `.tex` 文件和行号
3. 修复 LaTeX 语法错误
4. 重新运行 `bash build.sh build`

### Step 9: 最终报告

```
📝 最终报告:
- 论文: {state.title}
- 编排轮数: {len(report.rounds)}
- 生成章节: {report.sections_completed}
- LaTeX 编译: 成功 / 失败
- paper_state.json 已更新
- 生成文件:
  - paper/sections/introduction.tex
  - paper/sections/related-work.tex
  - paper/sections/method.tex
  - paper/sections/experiments.tex
  - paper/sections/conclusion.tex
```

## 恢复机制

如果编排中途失败，执行以下恢复步骤：

```python
# 1. 论文状态保存在 output/paper_state.json，可直接恢复
manager = PaperStateManager(Path("output/paper_state.json"))
state = manager.load()

# 2. 通过 Git 快照回滚（如需完全重置）
# git checkout <snapshot_hash> -- paper/ output/

# 3. 以 resume=true 重新运行，从上次保存状态继续
```

如果 `resume=true`：

```python
# 找到最后一个未完成的章节
resume_index = 0
for i, section in enumerate(state.sections):
    if section.status not in ("drafted", "reviewed", "complete"):
        resume_index = i
        break

print(f"从章节 '{state.sections[resume_index].section_id}' 恢复编排...")
```

## Python 模块参考

| 模块 | 用途 |
|------|------|
| `vibewriting.agents.contracts` | Agent 通信数据模型 |
| `vibewriting.agents.planner` | 章节任务图与依赖解析 |
| `vibewriting.agents.merge_protocol` | 冲突检测与解决 |
| `vibewriting.agents.executor` | Agent 执行抽象（MockExecutor / SubAgentExecutor） |
| `vibewriting.agents.orchestrator` | 核心编排逻辑 |
| `vibewriting.agents.git_safety` | Git 快照与回滚 |
| `vibewriting.writing.state_manager` | 论文状态持久化 |
| `vibewriting.writing.quality_gates` | 质量门禁检查 |
| `vibewriting.literature.cache` | 证据卡缓存读取 |
| `vibewriting.contracts.integrity` | BibTeX 键提取与引用完整性 |

## 输出产物

| 产物 | 路径 | 说明 |
|------|------|------|
| 章节 LaTeX | `paper/sections/*.tex` | 生成的章节源文件 |
| 论文状态 | `output/paper_state.json` | 含 Agent 贡献指标的更新状态 |
| 术语表 | `output/glossary.json` | 跨章节术语一致性记录 |
| 符号表 | `output/symbols.json` | 数学符号及其含义 |
| Git 快照 | Git 历史 | 编排前的回滚点 |
| 编译输出 | `paper/build/main.pdf` | 最终 PDF（需 TeX Live） |

## 重要约束

- **Evidence-First 强制执行**: 不允许在没有证据卡支撑的情况下引用文献
- BibTeX key 必须与 `paper/bib/references.bib` 中的条目完全一致
- 每节完成后必须通过质量门禁，全部通过后才提交 Git
- 冲突解决优先级：Critic > Analyst > Storyteller > Formatter
- `executor_type=mock` 仅用于测试，生产环境需切换为 `subagent`
