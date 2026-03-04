# vibewriting

这是一个**兼容 Claude Code 与 Codex**的科研论文自动化写作项目。  
Skill 双入口：
- Claude: `.claude/skills/`
- Codex: `.agents/skills/`（与 Claude 技能保持同源流程）

在 Claude Code 对话里输入主题后，可端到端产出可编译的 LaTeX 论文和 PDF。

**状态**: Phase 1-7 全部完成 | 824 tests | 路线图 v4 全部阶段已交付

## 架构

```
+--------------------------------------------------+
|      编排与推理层 (Claude Code / Codex)             |
|  CLAUDE.md | AGENTS.md | Skills | Agent Teams      |
+--------------------------------------------------+
                    |  MCP 协议
+--------------------------------------------------+
|          知识与检索层 (Dify + paper-search)          |
|  Dify MCP Server | paper-search MCP Server         |
+--------------------------------------------------+
                    |  Python / LaTeX / File System
+--------------------------------------------------+
|          集成与执行层                                |
|  数据管道 | 写作引擎 | LaTeX 编译链 | 契约验证       |
+--------------------------------------------------+
```

### 七阶段工作流

```
Phase 1: 基础架构           ✅
   |
   +---> Phase 2: 数据模型 + 处理管线  ✅
   |              |
   +---> Phase 3: 文献整合工作流      ✅
   |              |
   |              v
   |     Phase 4: 单 Agent 草稿撰写   ✅
   |              |
   |              v
   |     Phase 5: 多 Agent 编排       ✅
   |              |
   |              v
   |     Phase 6: 编译 + 质量保证     ✅
   |              |
   |              v
   |     Phase 7: 端到端集成          ✅
```

## 快速开始

> 重要：推荐在 **Claude Code 会话内**使用本项目。  
> `python -m ...` 这类命令主要用于开发调试和排障，不是主要使用方式。

### 前置条件

| 依赖 | 版本 | 必需 | 说明 |
|------|------|------|------|
| Python | 3.12+ | 是 | 运行时 |
| uv | 最新 | 是 | 包管理 |
| TeX Live | 2024+ | 是 | LaTeX 编译（需 xelatex + latexmk + ctex） |
| Dify | - | 否 | 知识库增强检索 |

### 安装

```bash
git clone <repo-url>
cd vibewriting
uv sync
```

### 环境验证

```bash
uv run scripts/validate_env.py         # 彩色输出
uv run scripts/validate_env.py --json  # JSON 报告
```

退出码：0=全通过, 1=必需依赖失败, 2=仅可选失败

### 配置

```bash
cp .env.example .env  # 填写 VW_DIFY_API_KEY 等凭据（可选）
```

编辑 `paper_config.yaml` 设置论文主题和参数：

```yaml
topic: "你的论文主题"
language: zh
sections:
  - 引言
  - 相关工作
  - 方法
  - 实验
  - 结论
```

### 一键运行

```
/vibewriting-paper "你的论文主题"
```

### 预期输出

| 文件 | 说明 |
|------|------|
| `paper/build/main.pdf` | 编译后的 PDF |
| `output/checkpoint.json` | 检查点（支持断点续跑） |
| `output/run_metrics.json` | 运行指标报告 |
| `output/paper_state.json` | 论文状态快照 |

### MCP 运行时适配（Claude + Codex）

文献检索模块不再绑定某个单一运行时，可通过统一适配接口注入 MCP 调用器：

```python
from vibewriting.literature import set_mcp_tool_caller

async def my_caller(tool_name: str, **kwargs):
    ...  # 调用 Claude 或 Codex 的 MCP 工具

set_mcp_tool_caller(my_caller)
```

也可通过环境变量指定：

```bash
export VW_MCP_TOOL_CALLER=your_module:your_function
```

## 非常详细使用指南

这一节按“直接照着做”来写，不需要先看源码。  
跟着下面步骤走一遍，基本就能把流程跑通。

### 0. 先选一种运行方式

| 方式 | 入口 | 适合场景 | 是否需要人工交互 |
|------|------|----------|------------------|
| Claude Code 端到端（推荐） | `/vibewriting-paper` | 从主题直接产出 PDF | 是（默认有 Approval Gate） |
| Claude Code 分阶段 | `/vibewriting-literature`、`/vibewriting-draft`、`/vibewriting-orchestrate`、`/vibewriting-review` | 想精细控制每个阶段 | 是 |
| 开发调试：仅数据处理 | `python -m vibewriting.pipeline.cli run` | 只调试统计、图表、表格 | 否 |
| 开发调试：仅编译审查 | `python -m vibewriting.latex.cli run` | 只调试 Phase 6 | 否 |

### 1. 第一次使用（Claude Code 场景）

#### Step 1.1 克隆并安装依赖

```bash
git clone <repo-url>
cd vibewriting
uv sync
```

成功标志：
- 命令正常结束，无 `ERROR` 级报错
- 项目根目录出现 `.venv`（由 `uv` 管理）

#### Step 1.2 验证运行环境

```bash
uv run scripts/validate_env.py
```

如果你要将结果接入脚本或 CI，用 JSON 模式：

```bash
uv run scripts/validate_env.py --json
```

退出码含义：
- `0`：必需与可选检查全部通过
- `1`：必需依赖缺失，必须先修复
- `2`：仅可选依赖缺失（通常是 TeX Live 或 Dify），核心流程可继续

#### Step 1.3 配置环境变量

```bash
cp .env.example .env
```

最小可运行配置（仅公开文献检索）：

```env
SERPAPI_API_KEY=your_serpapi_key
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=your_openai_key
```

如果要接入 Dify 知识库，再补充：

```env
VW_DIFY_API_BASE_URL=https://api.dify.ai/v1
VW_DIFY_API_KEY=your_dify_api_key
VW_DIFY_DATASET_ID=your_dataset_id
```

#### Step 1.4 配置论文参数

编辑 `paper_config.yaml`，建议先使用下面模板：

```yaml
topic: "基于 Transformer 的中文长文本摘要方法研究"
language: zh
document_class: ctexart
sections:
  - 引言
  - 相关工作
  - 方法
  - 实验
  - 结论
literature_query_count: 3
min_evidence_cards: 5
writing_mode: multi
auto_approve: false
```

#### Step 1.5 在 Claude Code 里执行端到端流程

方式 A：主题由命令传入（推荐）

```text
/vibewriting-paper "基于 Transformer 的中文长文本摘要方法研究"
```

方式 B：使用 `paper_config.yaml` 中的 `topic`

```text
/vibewriting-paper
```

成功标志（至少应看到）：
- `paper/build/main.pdf`
- `paper/bib/references.bib`
- `data/processed/literature/literature_cards.jsonl`
- `output/paper_state.json`
- `output/checkpoint.json`

### 2. 在 Claude Code 里分阶段执行（需要精细控制时）

如果你想每一步都自己看结果，就按下面顺序来。

#### Step 2.1 数据管线（Phase 2）

```bash
uv run python -m vibewriting.pipeline.cli run \
  --data-dir data/raw \
  --output-dir output \
  --seed 42
```

关键输出：
- `output/asset_manifest.json`
- `output/figures/`
- `output/tables/`

#### Step 2.2 文献检索（Phase 3）

```text
/vibewriting-literature "你的论文主题"
```

关键输出：
- `data/processed/literature/literature_cards.jsonl`
- `paper/bib/references.bib`

#### Step 2.3 草稿撰写（Phase 4）

```text
/vibewriting-draft "你的论文主题"
```

关键输出：
- `paper/sections/*.tex`
- `output/paper_state.json`
- `output/glossary.json`
- `output/symbols.json`

#### Step 2.4 多 Agent 编排（Phase 5，可选）

开了 `writing_mode=multi` 再跑这一步就行：

```text
/vibewriting-orchestrate "你的论文主题"
```

关键输出：
- 更新后的 `paper/sections/*.tex`
- 更新后的 `output/paper_state.json`
- `output/orchestration_report.json`（若执行了编排报告脚本）

#### Step 2.5 编译与质量审查（Phase 6）

Skill 入口：

```text
/vibewriting-review
```

CLI 入口（可脚本化）：

```bash
uv run python -m vibewriting.latex.cli run
```

跳过外部 API（例如 CrossRef）：

```bash
uv run python -m vibewriting.latex.cli run --skip-external-api
```

```bash
uv run python -m vibewriting.latex.cli run --export-docx
```

关键输出：
- `paper/build/main.pdf`
- `output/phase6_report.json`
- `output/peer_review.md`
- `output/peer_review.json`
- `output/patch_report.json`（有自愈修复时）

### 3. 断点续跑与重跑策略

#### 3.1 断点续跑

```text
/vibewriting-paper "你的论文主题" --resume
```

它会这样处理：
- 系统读取 `output/checkpoint.json`
- 已 `completed` 的阶段自动跳过
- 从第一个未完成阶段继续

#### 3.2 从头重跑（清理状态）

如果你想从头再来，先把检查点和中间产物清掉：

```bash
rm -f output/checkpoint.json output/run_metrics.json output/paper_state.json
rm -f data/processed/literature/literature_cards.jsonl
```

然后重新执行：

```text
/vibewriting-paper "你的论文主题"
```

### 4. 输出文件详解（何时看、看什么）

| 文件 | 阶段 | 用途 | 什么时候重点查看 |
|------|------|------|------------------|
| `paper/build/main.pdf` | Phase 6 | 最终论文 PDF | 验证交付质量 |
| `paper/sections/*.tex` | Phase 4/5 | 各章节源码 | 人工润色与审稿修改 |
| `paper/bib/references.bib` | Phase 3 | 参考文献库 | 排查未定义引用 |
| `data/processed/literature/literature_cards.jsonl` | Phase 3 | 证据卡缓存 | 检查 Evidence-First 依据 |
| `output/checkpoint.json` | 全程 | 阶段状态机 | 续跑与排障首看文件 |
| `output/paper_state.json` | Phase 4/5 | 论文结构与章节状态 | 判断草稿完成度 |
| `output/phase6_report.json` | Phase 6 | 编译/引文/契约/评审汇总 | 质量审查主报告 |
| `output/peer_review.md` | Phase 6 | 模拟同行评审结论 | 快速看改进建议 |
| `output/run_metrics.json` | 收尾 | 运行指标沉淀 | 对比不同 run 的效果 |

### 5. 常用命令清单

#### Claude Code 主命令（推荐）

```text
/vibewriting-paper "你的论文主题"
/vibewriting-literature "你的论文主题"
/vibewriting-draft "你的论文主题"
/vibewriting-orchestrate "你的论文主题"
/vibewriting-review
```

#### 环境与依赖

```bash
uv sync
uv run scripts/validate_env.py
uv run scripts/validate_env.py --json
```

#### 开发调试命令（可选）

```bash
uv run python -m vibewriting.pipeline.cli run --data-dir data/raw --output-dir output --seed 42
uv run python -m vibewriting.latex.cli run
bash build.sh build
bash build.sh watch
bash build.sh clean
bash build.sh check
```

#### 测试

```bash
uv run pytest
uv run pytest --tb=short -q
uv run pytest tests/test_config_paper.py
```

### 6. 常见报错怎么处理

#### 症状 A：`validate_env` 返回退出码 `1`

可以按这个顺序处理：
1. 先修复 Python/uv/git 缺失
2. 再执行 `uv sync`
3. 重新运行 `uv run scripts/validate_env.py`

#### 症状 B：`xelatex` 或 `latexmk` 找不到

处理命令：

```bash
which xelatex
which latexmk
```

若无输出，安装 TeX Live 后重试，并重新执行：

```bash
uv run scripts/validate_env.py
```

#### 症状 C：引用未定义或多余引用

先确保已编译过一次，再运行：

```bash
bash build.sh check
```

若仍失败，检查：
- `paper/bib/references.bib` 是否包含对应 key
- `\citep{}` / `\citet{}` 键名是否大小写一致

#### 症状 D：流程中断后无法继续

先看这两个地方：
- `output/checkpoint.json` 是否存在
- `run_id` 与 `topic` 是否匹配当前任务

恢复命令：

```text
/vibewriting-paper "原主题" --resume
```

### 7. 推荐的日常使用节奏

1. 每次开工先跑 `uv run scripts/validate_env.py`。  
2. 先用 `/vibewriting-paper` 跑出可编译版本，再做人工精修。  
3. 每次改动 `paper/sections/*.tex` 后执行 `bash build.sh build`。  
4. 提交前至少执行一次 `uv run python -m vibewriting.latex.cli run`。  
5. 若是连续多日写作，保留 `output/checkpoint.json`，优先用 `--resume`。  

### 8. 什么时候看 docs 子文档

- 你要查完整配置字段：看 `docs/config-reference.md`
- 你只想快速跑通一次：看 `docs/quickstart.md`
- 你遇到平台安装与故障问题：看 `docs/faq.md`
- 你要跨项目复用流程：看 `docs/cross-project-guide.md`

## 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| LaTeX | XeLaTeX + ctexart + latexmk (`$pdf_mode=5`) | 原生 Unicode，中文自动排版 |
| 参考文献 | BibTeX + natbib (`\citep{}`/`\citet{}`) | 学术引用标准 |
| Python | 3.12, uv, hatchling, src 布局 | 现代 Python 工程 |
| 图表 | matplotlib pgf 后端 | LaTeX 原生兼容 |
| 数据模型 | Pydantic 2.0 | 类型安全 + JSON Schema |
| 契约系统 | jsonschema + 自愈循环 | 阶段产物强校验 |
| MCP | paper-search + dify-knowledge | 文献检索 + 知识库 |

## 项目结构

```
vibewriting/
├── paper/                  # LaTeX 论文源码
│   ├── main.tex           # ctexart 主文档
│   ├── sections/          # 章节文件（\input 组织）
│   ├── bib/               # 参考文献 (.bib)
│   └── build/             # 编译输出（gitignored）
├── src/vibewriting/
│   ├── config.py          # 环境配置（VW_ 前缀）
│   ├── config_paper.py    # 论文配置（PaperConfig + YAML）
│   ├── checkpoint.py      # 检查点系统（阶段状态 + 断点续跑）
│   ├── metrics.py         # 指标汇总（运行报告）
│   ├── models/            # Pydantic 数据模型
│   ├── contracts/         # 契约系统（Schema + 自愈验证 + 引用完整性）
│   ├── processing/        # 数据清洗、转换、统计
│   ├── visualization/     # 图表生成 + LaTeX 表格
│   ├── pipeline/          # DAG 管线编排 + CLI
│   ├── literature/        # 文献检索 + 去重 + 证据卡 + BibTeX
│   ├── writing/           # 草稿撰写 + 质量门禁 + 增量编译
│   ├── agents/            # 多 Agent 编排 + 合并协议 + Git 安全网
│   ├── latex/             # LaTeX 编译 + 日志解析 + 自愈循环
│   └── review/            # 引文审计 + 同行评审 + 排版检查
├── tests/                 # 824 tests
├── data/                  # 原始数据 + 处理后数据
├── output/                # 管线输出 + 契约产物
├── docs/                  # 用户文档（快速开始、配置参考、FAQ）
├── .claude/skills/        # 7 个 Claude Code Skills
├── llmdoc/                # LLM 优化文档系统
├── openspec/              # 路线图 + 变更归档
├── paper_config.yaml      # 论文配置文件
├── build.sh               # LaTeX 构建脚本
└── pyproject.toml         # Python 包定义
```

## Skills

| Skill | 阶段 | 用途 |
|-------|------|------|
| `/vibewriting-paper` | Phase 7 | Claude Code 端到端主入口（9步工作流 + 5个 Approval Gates） |
| `/vibewriting-literature` | Phase 3 | 文献检索 + 证据卡生成 |
| `/vibewriting-draft` | Phase 4 | Evidence-First 草稿撰写 |
| `/vibewriting-orchestrate` | Phase 5 | 多 Agent 协同编排 |
| `/vibewriting-review` | Phase 6 | 编译验证 + 引文审计 + 同行评审 |
| `/vibewriting-kb` | Phase 1 | Dify 知识库检索 |
| `/vibewriting-cite-check` | Phase 1 | 引用完整性验证 |

## 构建论文

```bash
bash build.sh build      # 编译论文 (latexmk)
bash build.sh watch       # 监视模式
bash build.sh clean       # 清理构建产物
bash build.sh check       # 运行 checkcites
bash build.sh doi2bib DOI # DOI 转 BibTeX
```

## 数据管线

```bash
uv run python -m vibewriting.pipeline.cli run \
  --data-dir data/raw --output-dir output --seed 42
```

## 测试

```bash
uv run pytest                           # 全部 824 tests
uv run pytest tests/test_config_paper.py  # 单模块测试
uv run pytest --tb=short -q              # 简洁输出
```

## 配置参考

### paper_config.yaml

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `topic` | str | (必填) | 论文主题 |
| `language` | zh/en | zh | 语言 |
| `document_class` | str | ctexart | LaTeX 文档类 |
| `sections` | list | 5章 | 章节列表 |
| `literature_query_count` | int | 3 | 文献检索轮数 |
| `min_evidence_cards` | int | 5 | 最少证据卡数 |
| `data_dir` | str/null | null | 数据目录 |
| `random_seed` | int | 42 | 随机种子 |
| `writing_mode` | single/multi | multi | 写作模式 |
| `auto_approve` | bool | false | 跳过审批门禁 |

### 环境变量 (.env)

| 变量 | 必需 | 说明 |
|------|------|------|
| `VW_DIFY_API_KEY` | 否 | Dify API Key |
| `VW_DIFY_API_BASE_URL` | 否 | Dify 服务地址 |
| `VW_DIFY_DATASET_ID` | 否 | Dify 数据集 ID |
| `VW_RANDOM_SEED` | 否 | 全局随机种子 |

详见 [docs/config-reference.md](docs/config-reference.md)。

## 文档

| 文档 | 说明 |
|------|------|
| [docs/quickstart.md](docs/quickstart.md) | 快速开始指南 |
| [docs/config-reference.md](docs/config-reference.md) | 完整配置参考 |
| [docs/faq.md](docs/faq.md) | 常见问题解答 |
| [docs/cross-project-guide.md](docs/cross-project-guide.md) | 跨项目迁移指南 |
| [llmdoc/index.md](llmdoc/index.md) | LLM 文档系统索引 |
| [openspec/ROADMAP.md](openspec/ROADMAP.md) | 完整路线图（v4, 7阶段） |

## 设计原则

1. **阶段产物契约** — JSON Schema + 自愈循环 + 引用完整性
2. **证据优先工作流** — Evidence Card + claim 追溯
3. **Git 一等公民** — auto commit + snapshot + stash 安全网
4. **人机协同审批门** — AskUserQuestion Approval Gates
5. **LaTeX 增量编译** — 单章节草稿 → 全量编译
6. **可观测性与指标** — run_id + 运行指标报告
7. **合规与 AI 披露** — 引用限制 + AI 声明可开关
8. **源码溯源注释** — `%% CLAIM_ID: EC-2026-XXX`
9. **Prompt 缓存架构** — 静态头部 + 动态尾部

## 许可证

待定
