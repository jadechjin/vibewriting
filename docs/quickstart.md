# 快速开始

本指南帮助你在 15 分钟内完成 vibewriting 的安装、配置和首次论文生成。

---

## 前置条件

在开始之前，请确认以下工具已安装：

| 工具 | 最低版本 | 说明 |
|------|----------|------|
| Python | 3.12+ | 运行时环境 |
| uv | 最新版 | Python 包管理器，替代 pip/venv |
| TeX Live | 2022+ | 包含 `xelatex`、`latexmk`、`ctex` |
| Git | 任意版本 | 克隆仓库 |

> **Dify 知识库**（可选）：如需使用私有知识库检索，还需要配置 Dify 服务凭据，详见[配置参考](./config-reference.md)。

---

## 安装

### 1. 克隆仓库

```bash
git clone <repo-url>
cd vibewriting
```

### 2. 安装 Python 依赖

```bash
uv sync
```

`uv sync` 会自动读取 `pyproject.toml`，在隔离的虚拟环境中安装所有依赖，无需手动激活 venv。

### 3. 验证环境

```bash
uv run scripts/validate_env.py
```

脚本会检查所有必需和可选依赖的状态，并以彩色输出显示结果：

- **绿色** — 检查通过
- **黄色** — 可选组件缺失（不影响基础功能）
- **红色** — 必需依赖缺失（必须修复）

如需机器可读的报告，使用 `--json` 参数：

```bash
uv run scripts/validate_env.py --json
```

**退出码说明**：

| 退出码 | 含义 |
|--------|------|
| `0` | 全部检查通过 |
| `1` | 必需依赖失败，无法运行 |
| `2` | 仅可选依赖失败，核心功能可用 |

---

## 配置

### 1. 配置环境变量

```bash
cp .env.example .env
```

用文本编辑器打开 `.env`，填写必要的凭据。最低配置（仅使用公开文献搜索）：

```env
SERPAPI_API_KEY=your_serpapi_key_here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=your_openai_key_here
```

如需启用 Dify 知识库，还需额外填写：

```env
VW_DIFY_API_BASE_URL=https://api.dify.ai/v1
VW_DIFY_API_KEY=your_dify_api_key
VW_DIFY_DATASET_ID=your_dataset_id
```

完整的环境变量说明见[配置参考](./config-reference.md)。

### 2. 配置论文参数

编辑项目根目录的 `paper_config.yaml`，至少填写 `topic` 字段：

```yaml
# 论文主题（必填）
topic: "基于深度学习的医学图像分割方法综述"

# 输出语言：zh（中文）或 en（英文）
language: zh

# 写作模式：single（单 Agent）或 multi（多 Agent 并行）
writing_mode: multi
```

其余字段均有合理默认值，首次使用无需修改。全字段说明见[配置参考](./config-reference.md)。

---

## 一键运行

vibewriting 通过 Claude Code Skill 提供主要交互接口。在 Claude Code 中运行：

```
/write-paper "你的论文主题"
```

或者，如果已在 `paper_config.yaml` 中设置好主题，直接运行：

```
/write-paper
```

系统会按以下顺序自动执行：

1. **文献检索** — 通过 paper-search MCP 搜索相关论文
2. **证据卡生成** — 提取关键信息形成结构化证据卡
3. **数据处理** — 运行统计分析和图表生成
4. **论文写作** — 调用写作 Agent 生成各章节内容
5. **LaTeX 编译** — 使用 XeLaTeX + latexmk 编译为 PDF
6. **质量检查** — 校验引用完整性、图表可用性

---

## 恢复中断的任务

如果写作过程因网络问题或手动中断，可以从检查点恢复：

```
/write-paper "主题" --resume
```

系统会自动读取 `output/checkpoint.json`，从上次中断的阶段继续执行，已完成的阶段不会重复运行。

---

## 预期输出

任务完成后，以下文件会被生成：

| 文件 | 说明 |
|------|------|
| `paper/build/main.pdf` | 编译完成的 PDF 论文 |
| `paper/build/main.tex` | 最终的 LaTeX 源码 |
| `paper/bib/references.bib` | 引用的 BibTeX 文件 |
| `output/figures/` | 生成的图表（.pdf / .pgf / .png） |
| `output/tables/` | 生成的 LaTeX 表格（.tex） |
| `output/run_metrics.json` | 运行指标（耗时、Token 用量等） |
| `output/checkpoint.json` | 阶段检查点（用于断点续传） |
| `data/processed/literature/literature_cards.jsonl` | 证据卡缓存 |

---

## 手动运行数据管线（可选）

如果只需要运行数据处理部分，不需要写作流程：

```bash
uv run python -m vibewriting.pipeline.cli run \
  --data-dir data/raw \
  --output-dir output \
  --seed 42
```

---

## 下一步

- [配置参考](./config-reference.md) — 所有配置项的详细说明
- [常见问题](./faq.md) — 安装和运行中的常见问题解答
- [跨项目迁移指南](./cross-project-guide.md) — 在多个论文项目间复用资源
