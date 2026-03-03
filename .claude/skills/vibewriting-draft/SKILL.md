---
name: vibewriting-draft
description: Evidence-First 论文草稿撰写：claim 溯源、质量门禁、增量编译
---

# vibewriting-draft

基于 Evidence-First 约束的论文草稿撰写工作流。

## 输入参数

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `topic` | 必需 | — | 论文研究主题 |
| `title` | 可选 | 从主题自动生成 | 论文标题 |
| `resume` | 可选 | false | 是否从 paper_state.json 恢复未完成的撰写 |

## 前置条件

执行前必须验证以下文件存在且有效：

```bash
test -f data/processed/literature/literature_cards.jsonl && echo "OK" || echo "MISSING: 请先运行 /vibewriting-literature"
test -f output/asset_manifest.json && echo "OK" || echo "MISSING: 请先运行数据管线"
test -f paper/bib/references.bib && echo "OK" || echo "MISSING: 参考文献数据库缺失"
```

如有任何前置文件缺失，停止并告知用户需要先完成相应的前序步骤。

## 工作流程

### Step 1: 加载前置产物

```python
from vibewriting.literature.cache import LiteratureCache
from pathlib import Path
import json

# 加载证据卡
cache = LiteratureCache(Path("data/processed/literature/literature_cards.jsonl"))
cache.load()
all_cards = cache.all_cards()

# 加载资产清单
with open("output/asset_manifest.json") as f:
    asset_manifest = json.load(f)

print(f"Loaded {len(all_cards)} evidence cards")
print(f"Loaded {len(asset_manifest.get('assets', []))} assets")
```

### Step 2: 生成论文大纲

```python
from vibewriting.writing.outline import build_default_outline, outline_to_paper_state

outline = build_default_outline(
    topic=topic,
    title=title,
    evidence_cards=[c.model_dump() for c in all_cards],
    asset_manifest=asset_manifest.get("assets", []),
)
```

展示大纲给用户，使用 `AskUserQuestion` 工具获取确认：
- 选项 1: "确认大纲，开始撰写"
- 选项 2: "修改大纲"（用户提供修改指令后重新调用 `build_default_outline`）

### Step 3: 创建 paper_state.json

```python
from vibewriting.writing.state_manager import PaperStateManager

manager = PaperStateManager(Path("output/paper_state.json"))
state = outline_to_paper_state(outline, paper_id="PS-2026-001")
manager.save(state)
state = manager.advance_phase(state)  # outline -> drafting
manager.save(state)
```

### Step 4: 逐章节撰写（核心循环）

对 `state.sections` 中的每个章节依次执行以下步骤。

#### 4a. 加载章节相关证据卡

```python
section = state.sections[i]

# 从证据卡缓存中获取本章节关联的 claim
relevant_cards = []
for claim_id in section.claim_ids:
    card = cache.get(claim_id)
    if card:
        relevant_cards.append(card)

# 构建引用键->证据卡映射，便于内容生成时查阅
bib_key_map = {card.bib_key: card for card in relevant_cards}
```

#### 4b. 生成 LaTeX 源码

在生成每个章节时，严格遵循以下撰写规则：

<writing-rules>
1. **Evidence-First**: 只允许引用 `relevant_cards` 中的 claim。
   每个引用的 claim 必须在行末标注溯源注释：`%% CLAIM_ID: EC-XXXX-XXX`

2. **引用格式**:
   - 括号引用（结尾）：`\citep{key}`
   - 文本引用（句中）：`\citet{key}`
   - 引用键 `key` 必须来自证据卡的 `bib_key` 字段

3. **图表引用**:
   - 图：`\ref{fig:label}`
   - 表：`\ref{tab:label}`
   - label 基于 `asset_manifest` 中的资产 ID 派生

4. **每句一行**: LaTeX 源码每个句子独占一行（以句号、问号或感叹号结尾后换行）

5. **学术写作风格**:
   - 使用客观第三人称叙述语气
   - 禁止使用以下 LLM 常见废话：
     - "delve into" / "it's important to note" / "in conclusion"
     - "it is worth noting" / "fascinating" / "crucial"
     - "groundbreaking" / "novel" / "significant advancements"
   - 使用精确、专业的学术用语

6. **常识豁免**: 不需要引用的通用背景知识，在行末标注：`%% NO_CITE: common knowledge`

7. **数学公式**: 使用 amsmath 环境（`equation`、`align`），禁止使用 `$$...$$`

8. **图表标题**: 先陈述核心结论，再描述细节（例："模型在 X 数据集上达到 Y 性能。图中纵轴为 ... "）

9. **每个 claim 必须有支撑**: 每个实验结论或理论 claim 必须有对应的 `\citep{}` 或实验数据支撑
</writing-rules>

生成内容示例结构：

```latex
\section{Introduction}

Deep learning has transformed natural language processing in recent years. %% NO_CITE: common knowledge

The Transformer architecture introduced self-attention mechanisms that process sequences in parallel \citep{vaswani2017attention}. %% CLAIM_ID: EC-2026-001
This design achieves $O(n^2)$ complexity with respect to sequence length, enabling efficient training on modern hardware \citep{vaswani2017attention}. %% CLAIM_ID: EC-2026-001

BERT demonstrated that bidirectional pre-training substantially improves performance across eleven downstream NLP tasks \citep{devlin2019bert}. %% CLAIM_ID: EC-2026-002
As shown in Table~\ref{tab:results}, fine-tuned BERT outperforms task-specific architectures by an average of 7.7\% on the GLUE benchmark \citep{devlin2019bert}. %% CLAIM_ID: EC-2026-002
```

#### 4c. 写入 .tex 文件

```python
from vibewriting.writing.latex_helpers import inject_claim_annotation

tex_path = Path("paper") / section.tex_file
tex_path.parent.mkdir(parents=True, exist_ok=True)
tex_path.write_text(generated_content, encoding="utf-8")
```

#### 4d. 运行质量门禁

```python
from vibewriting.writing.quality_gates import run_all_gates

report = run_all_gates(
    tex_content=generated_content,
    section_id=section.section_id,
    section_type=section.section_id,  # section_id 与 section_type 对应
    expected_claim_ids=section.claim_ids,
    expected_asset_ids=section.asset_ids,
)

if not report.all_passed:
    # 显示失败的门禁详情，告知用户并尝试修复
    for r in report.results:
        if not r.passed:
            print(f"Gate FAILED: {r.gate_name} (score={r.score:.2f})")
            for d in r.details:
                print(f"  - {d}")
    # 尝试修复后重新运行门禁，最多尝试 2 次
```

五个质量门禁说明：

| 门禁 | 检查内容 | 通过标准 |
|------|----------|----------|
| `citation_coverage` | 段落引用覆盖率 | introduction/related-work: >0; method/experiments: >=50% |
| `asset_coverage` | 图表引用覆盖 | experiments 章节必须有 >=1 个 fig/tab ref |
| `claim_traceability` | CLAIM_ID 注释覆盖 | >=30% expected claims 已标注 |
| `cross_ref_integrity` | \\ref{} 标签一致性 | 无悬空引用 |
| `terminology_consistency` | 术语/符号一致性 | 无关键术语冲突 |

#### 4e. 增量编译（如 TeX Live 可用）

```python
from vibewriting.writing.incremental import compile_single_section

success, log = compile_single_section(Path("paper"), section.tex_file)
if not success:
    # 分析编译日志，定位 LaTeX 错误并尝试修复
    print(f"Compilation failed. Log excerpt:\n{log[-500:]}")
```

#### 4f. 更新状态并提交

```python
state = manager.update_section_status(state, section.section_id, "drafted")
manager.save(state)
```

Git auto-commit（每节完成后）：

```bash
git add paper/sections/{section_id}.tex output/paper_state.json
git commit -m "auto: finish section {section_id} [cite: {N} papers]"
```

### Step 5: 生成术语表和符号表

从已撰写的所有章节中提取术语和数学符号：

```python
from vibewriting.models.glossary import Glossary, SymbolTable
import json

glossary = Glossary()
symbol_table = SymbolTable()

# 遍历每个章节，提取已定义的术语和符号
for section in state.sections:
    if section.status == "drafted":
        tex_path = Path("paper") / section.tex_file
        # 解析 \newglossaryentry、\newcommand 等宏定义
        # 提取首次出现的专业术语及其上下文

# 持久化输出
Path("output/glossary.json").write_text(
    glossary.model_dump_json(indent=2), encoding="utf-8"
)
Path("output/symbols.json").write_text(
    symbol_table.model_dump_json(indent=2), encoding="utf-8"
)
```

### Step 6: 全量编译验证

```bash
bash build.sh build
```

如果编译失败：
1. 分析 `paper/build/main.log` 中的错误信息
2. 定位出错的 `.tex` 文件和行号
3. 修复 LaTeX 语法错误
4. 重新运行 `bash build.sh build`

### Step 7: 最终报告

输出完整撰写摘要：

```
撰写完成报告:
- 完成章节: N/N
- 总引用数: X 条（来自 Y 篇文献）
- 质量门禁: A/5 通过（B 章节有警告）
- 编译状态: [成功/失败]
- paper_state.json: output/paper_state.json
- 已生成文件:
  - paper/sections/introduction.tex
  - paper/sections/related-work.tex
  - paper/sections/method.tex
  - paper/sections/experiments.tex
  - paper/sections/conclusion.tex
  - output/glossary.json
  - output/symbols.json
```

## 恢复机制

如果 `resume=true`：

```python
manager = PaperStateManager(Path("output/paper_state.json"))
state = manager.load()

if state is None:
    raise FileNotFoundError("paper_state.json 不存在，请先完整运行一次")

# 找到最后一个未完成的章节
resume_index = 0
for i, section in enumerate(state.sections):
    if section.status not in ("drafted", "reviewed", "complete"):
        resume_index = i
        break

print(f"从章节 '{state.sections[resume_index].section_id}' 恢复撰写...")
# 从 resume_index 继续 Step 4 的循环
```

## Python 模块参考

```python
from vibewriting.writing.state_manager import PaperStateManager
from vibewriting.writing.outline import build_default_outline, outline_to_paper_state
from vibewriting.writing.quality_gates import run_all_gates, GateReport, GateResult
from vibewriting.writing.latex_helpers import inject_claim_annotation, format_citation
from vibewriting.writing.incremental import compile_single_section, write_draft_main
from vibewriting.literature.cache import LiteratureCache
from vibewriting.models.paper_state import PaperState, SectionState, PaperMetrics
from vibewriting.models.glossary import Glossary, SymbolTable
```

## 输出产物

| 产物 | 路径 | 说明 |
|------|------|------|
| 章节 LaTeX | `paper/sections/*.tex` | 带 CLAIM_ID 溯源注释的章节源文件 |
| 论文状态 | `output/paper_state.json` | 阶段、章节状态、质量指标 |
| 术语表 | `output/glossary.json` | 跨章节术语一致性记录 |
| 符号表 | `output/symbols.json` | 数学符号及其含义 |
| 编译输出 | `paper/build/main.pdf` | 最终 PDF（需 TeX Live） |

## 重要约束

- **Evidence-First 强制执行**: 不允许在没有证据卡支撑的情况下引用文献
- BibTeX key 必须与 `paper/bib/references.bib` 中的条目完全一致
- `%% CLAIM_ID:` 注释与 `\citep{}` 命令必须在同一行末尾
- 生成内容中禁止直接引用超过 50 词的原文（自动标记 `paraphrase=True`）
- 每节撰写完成后必须通过质量门禁检查，门禁全部通过后才提交 Git
