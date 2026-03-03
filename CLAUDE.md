# vibewriting

基于 Claude Code 与 Dify 知识库的科研论文自动化写作系统。
输入论文主题，端到端产出可编译的 LaTeX 论文 + PDF。

## 架构与技术栈

三层架构：
- **编排与推理层**: Claude Code（CLAUDE.md / Skills / Sub-agents / Agent Teams）
- **知识与检索层**: paper-search MCP + Dify MCP 桥接服务器
- **集成与执行层**: Python 数据管道 + LaTeX (TeX Live) + 文件系统

技术选型：
- LaTeX: XeLaTeX + ctexart + latexmk (`$pdf_mode=5`)
- 参考文献: BibTeX + natbib (`\citep{}` / `\citet{}`)
- Python: 3.12, uv, hatchling, src 布局
- 图表: matplotlib pgf 后端（非 tikzplotlib）
- 环境变量: `VW_` 前缀命名空间（如 `VW_DIFY_API_KEY`, `VW_RANDOM_SEED`）

## 工具与资源

### MCP 工具

**paper-search**（文献检索）:
- `search_papers(query)` — 搜索学术论文
- `decide(session_id, action)` — 检查点决策
- `export_results(session_id, format)` — 导出结果（json/bibtex/markdown）
- `get_session(session_id)` — 查询会话状态

**dify-knowledge**（知识库检索，需配置凭据）:
- `retrieve_knowledge(query)` — 检索知识库文档
- `list_documents()` — 列出数据集文档

### 目录映射

| 目录 | 用途 |
|------|------|
| `paper/` | LaTeX 论文源码（main.tex + sections/ + bib/） |
| `paper/build/` | 编译输出（gitignored） |
| `src/vibewriting/models/` | Pydantic 数据模型（Paper, Experiment, Figure, Table, Section, EvidenceCard） |
| `src/vibewriting/contracts/` | 阶段产物契约（Schema 导出 + 自愈验证 + 引用完整性） |
| `src/vibewriting/processing/` | 数据清洗、转换、统计分析 |
| `src/vibewriting/visualization/` | 图表生成（matplotlib）+ LaTeX 表格（jinja2）+ PGF 导出 |
| `src/vibewriting/pipeline/` | DAG 管线编排 + CLI 入口 |
| `src/vibewriting/literature/` | 文献整合工作流（检索 + 去重 + 证据卡 + BibTeX 管理） |
| `src/vibewriting/latex/` | LaTeX 编译工具（待实现） |
| `data/raw/` | 原始数据（大文件 gitignored） |
| `data/processed/` | 清洗后数据 |
| `data/processed/literature/` | 证据卡缓存（literature_cards.jsonl） |
| `output/figures/` | 生成的图表（.pdf/.pgf/.png） |
| `output/tables/` | 生成的 LaTeX 表格（.tex） |
| `scripts/` | 工具脚本（validate_env.py, dify-kb-mcp/） |

### 构建脚本（需 TeX Live）

```bash
bash build.sh build      # 编译论文 (latexmk)
bash build.sh watch       # 监视模式
bash build.sh clean       # 清理构建产物
bash build.sh check       # 运行 checkcites
bash build.sh doi2bib DOI # DOI 转 BibTeX
```

### 数据管线

```bash
uv run python -m vibewriting.pipeline.cli run --data-dir data/raw --output-dir output --seed 42
uv run python -m vibewriting.contracts.schema_export   # 导出 JSON Schema
```

## 验证标准与工作流纪律

- 修改 `.tex` 文件后运行 `latexmk`（需 TeX Live）
- 修改 `.bib` 文件后运行 `checkcites`（需 TeX Live）
- LaTeX 每句独占一行（便于 git diff）
- 章节使用 `\input{}`（非 `\include{}`），不强制换页
- Python 修改后运行 `uv run pytest`
- 数据处理管道修改后验证输出确定性
- `.bib` 文件强制 UTF-8 编码，引用键仅 ASCII

环境验证：
```bash
uv run scripts/validate_env.py         # 控制台彩色输出
uv run scripts/validate_env.py --json  # JSON 机器可读报告
```

退出码：0=全通过, 1=必需依赖失败, 2=仅可选失败

## 学术写作风格约束

- 客观第三人称叙述语气
- 禁止 LLM 常见废话（"delve into", "it's important to note", "in conclusion"）
- 引用格式：`\citep{key}` 括号引用，`\citet{key}` 文本引用
- 数学公式使用 amsmath 环境（`equation`, `align`），禁止 `$$...$$`
- 图表标题简洁，先陈述结果再描述细节
- 每个 claim 必须有引用或数据支撑

## 安全边界

- 不修改全局配置或系统字体
- 不泄露 `.env` 中的 API 密钥（日志和输出中屏蔽）
- 不执行未经确认的 `git push`
- 不直接 import paper-search 代码（通过 MCP 协议集成）
- 不安装全局 Python 包（所有依赖通过 uv 管理）
