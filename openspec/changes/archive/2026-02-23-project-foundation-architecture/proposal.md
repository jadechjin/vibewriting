# Proposal: 科研论文自动化写作系统 — 项目基础架构

## Context

### 用户需求

搭建"基于 Claude Code 与 Dify 知识库的科研论文自动化写作系统"的项目基础架构。系统设计文档（origin.md）已完成，需要将三层架构蓝图（编排与推理层、知识与检索层、集成与执行层）转化为可工作的工程化项目骨架。

### 当前状态

- **项目目录**: `f:\vibewriting`，仅包含 `origin.md` 设计文档
- **已有实现**: 第一阶段文献检索系统 `paper-search` 已在 `C:\Users\17162\Desktop\Terms\workflow` 目录独立实现（生产级，213 项测试，MCP 服务器暴露 4 个工具）
- **环境**: Windows 11, Python 3.12.2, uv 0.6.9, Git 2.52.0, Node.js v22.14.0
- **缺失工具**: TeX Live / XeLaTeX / latexmk / make 均未安装

### 发现的约束（多 Agent 交叉验证）

#### 硬约束

| ID | 约束 | 影响 | 来源 |
|----|------|------|------|
| H1 | TeX Live / XeLaTeX / latexmk 未安装 | LaTeX 编译链不可用，需用户手动安装 | 环境检测 |
| H2 | make 工具未安装 | 构建脚本必须用 bash 替代 Makefile | 环境检测 |
| H3 | Windows 11 平台 | 路径分隔符、shell 差异、bubblewrap 沙箱不可用 | 环境检测 |
| H4 | Python 3.12.2 + uv 0.6.9 | 依赖管理必须基于 uv 和 pyproject.toml | 环境检测 |
| H5 | paper-search 使用 Python 3.11+, pydantic ≥2.0, asyncio | 新代码必须兼容此技术栈 | 代码库分析 |
| H6 | paper-search 已有 MCP 服务器（4 个工具） | MCP 配置必须包含 paper-search 工具注册 | 代码库分析 |
| H7 | Dify API 信息待提供 | MCP 配置使用占位符模板 | 用户确认 |
| H8 | latexmk `$pdf_mode=5` 是 XeLaTeX 的唯一正确配置 | 不能使用 `$pdf_mode=1`（pdflatex 专用） | LaTeX Agent |
| H9 | BibTeX 对 UTF-8 非 ASCII 字符排序支持有限 | 中文作者姓名排序可能异常 | LaTeX Agent |
| H10 | ctex 宏集要求 TeX Live 2020+ | 安装时需确保版本足够新 | LaTeX Agent |
| H11 | Dify 原生 MCP 暴露的是应用级接口，非知识库 API | 需自定义 MCP 桥接服务器才能精细控制检索参数 | MCP Agent |
| H12 | numpy `<2.0` 约束（pandas 2.2.x 依赖） | scipy 版本需相应限制 | Python Agent |
| H13 | tikzplotlib 已废弃，与 matplotlib ≥3.8 不兼容 | 必须用 matplotlib pgf 后端替代 | Python Agent |
| H14 | 两个项目在不同磁盘路径（F: vs C:） | 不适合 uv workspace，必须保持独立 | Python Agent |

#### 软约束

| ID | 约束 | 来源 |
|----|------|------|
| S1 | XeLaTeX 编译器，支持中英文 | 用户决策 |
| S2 | 使用 ctexart 文档类（优于 article + xeCJK） | LaTeX Agent 推荐 |
| S3 | BibTeX 传统方案 + natbib 宏包 | 用户决策 + LaTeX Agent |
| S4 | 目录结构映射三层架构 | origin.md 设计 |
| S5 | 异步编程模式（async/await） | paper-search 惯例 |
| S6 | Pydantic 数据模型 | paper-search 惯例 |
| S7 | CLAUDE.md 渐进式披露，不超过 300 行 | origin.md 设计 |
| S8 | 使用 hatchling 构建后端（与 paper-search 一致） | Python Agent |
| S9 | src 布局（src/vibewriting/） | Python Agent |
| S10 | Ruff 代码格式化，line-length=100 | paper-search 惯例 |
| S11 | MCP 配置使用 `.mcp.json`（项目级共享）| MCP Agent |
| S12 | 自定义命令使用 Skills 格式（`.claude/skills/`） | MCP Agent |
| S13 | 每句独占一行（便于 git diff） | LaTeX Agent |

#### 跨模块依赖

| ID | 依赖 | 状态 | 备注 |
|----|------|------|------|
| D1 | TeX Live 2020+ | 阻塞 | 需用户手动安装，约 8GB |
| D2 | Dify 实例信息 | 延迟 | URL + API Key + Dataset ID |
| D3 | paper-search 路径引用 | 就绪 | `C:\Users\17162\Desktop\Terms\workflow` |
| D4 | Python 虚拟环境 + 依赖 | 就绪 | uv 已安装 |
| D5 | Windows 系统字体 | 就绪 | SimSun/SimHei/KaiTi/FangSong 已预装 |
| D6 | Perl（latexmk 运行时） | 随 TeX Live | 无需单独安装 |
| D7 | curl（DOI 转 BibTeX） | 就绪 | Git for Windows 自带 |

#### 风险

| ID | 风险 | 严重度 | 缓解策略 |
|----|------|--------|---------|
| R1 | TeX Live 安装耗时（30-60 分钟）且占 8GB | 中 | 提供安装指南 + 验证脚本 |
| R2 | Windows 路径分隔符问题 | 低 | 脚本统一正斜杠，Python 用 pathlib |
| R3 | paper-search 跨目录引用 | 低 | MCP 配置使用绝对路径 |
| R4 | Dify MCP 配置延迟 | 中 | 先创建桥接模板，独立可测试 |
| R5 | BibTeX UTF-8 中文排序异常 | 中 | 使用 LaTeX 转义序列或未来迁移 biber |
| R6 | Claude 生成 LaTeX 时引入不可见 Unicode 字符 | 低 | CLAUDE.md 中添加规则禁止 |
| R7 | numpy/pandas/scipy 版本锁链 | 低 | 保守版本约束 + uv 解析器自动回退 |
| R8 | 多 MCP 服务器上下文消耗 | 中 | 工具描述占 10-25% Token，需精简 |

---

## Requirements

### REQ-01: 项目目录结构

**场景**: 开发者首次进入项目后，能从目录结构直观理解系统的三层架构和各模块职责。

**约束映射**: S4, S8, S9, H3, H14

**目录设计（多 Agent 综合优化版）**:

```
vibewriting/
├── origin.md                    # 系统设计文档（已有）
├── CLAUDE.md                    # Claude Code 项目配置
├── pyproject.toml               # Python 项目配置（uv + hatchling）
├── .mcp.json                    # MCP 服务器配置（项目级，可提交）
├── .gitignore                   # Git 忽略规则
├── .env.example                 # 环境变量模板
├── build.sh                     # 构建脚本（Git Bash 兼容）
├── openspec/                    # OPSX 变更管理（已有）
│
├── paper/                       # LaTeX 论文源码（核心输出）
│   ├── main.tex                 # 主文档（ctexart 文档类）
│   ├── latexmkrc                # latexmk 配置（$pdf_mode=5）
│   ├── sections/                # 各章节（\input 拆分）
│   │   ├── introduction.tex
│   │   ├── related-work.tex
│   │   ├── method.tex
│   │   ├── experiments.tex
│   │   ├── conclusion.tex
│   │   └── appendix.tex
│   ├── bib/                     # 参考文献
│   │   └── references.bib
│   ├── figures/                 # 图片资源（PDF/PNG/EPS）
│   └── build/                   # 编译输出（gitignored）
│
├── src/                         # Python 源码（src 布局）
│   └── vibewriting/
│       ├── __init__.py
│       ├── config.py            # 项目配置加载（dotenv）
│       ├── processing/          # 数据处理管道
│       │   ├── __init__.py
│       │   ├── cleaners.py
│       │   ├── transformers.py
│       │   └── statistics.py
│       ├── visualization/       # 可视化生成
│       │   ├── __init__.py
│       │   ├── figures.py       # matplotlib/seaborn 图表
│       │   ├── tables.py        # LaTeX 表格生成
│       │   └── pgf_export.py    # PGF 后端导出
│       ├── latex/               # LaTeX 资产管理
│       │   ├── __init__.py
│       │   └── compiler.py      # LaTeX 编译调用
│       ├── models/              # Pydantic 数据模型
│       │   ├── __init__.py
│       │   ├── paper.py         # 论文元数据（兼容 paper-search）
│       │   └── experiment.py    # 实验数据模型
│       └── agents/              # 智能体定义（预留）
│           └── __init__.py
│
├── data/                        # 数据资产
│   ├── raw/                     # 原始数据（不可修改，gitignored 大文件）
│   ├── processed/               # 清洗后数据
│   └── cache/                   # 文献分析缓存（可安全删除）
│
├── output/                      # 生成资产（Python 脚本输出）
│   ├── figures/                 # 生成的图表（.pdf, .pgf, .png）
│   ├── tables/                  # 生成的 LaTeX 表格（.tex）
│   └── assets/                  # 其他 LaTeX 资产
│
├── scripts/                     # 工具脚本
│   ├── validate_env.py          # 环境验证（uv run 脚本）
│   └── dify-kb-mcp/             # Dify 知识库 MCP 桥接服务器
│       └── server.py
│
├── tests/                       # 测试
│   ├── conftest.py
│   ├── test_processing/
│   ├── test_visualization/
│   └── test_latex/
│
├── .claude/                     # Claude Code 本地配置
│   ├── settings.local.json      # 权限规则 + 附加目录（不提交）
│   └── skills/                  # 自定义技能（Skills 格式）
│       ├── search-literature/
│       │   └── SKILL.md
│       ├── retrieve-kb/
│       │   └── SKILL.md
│       └── validate-citations/
│           └── SKILL.md
│
└── llmdoc/                      # 项目文档（LLM 可读）
    ├── index.md
    └── overview/
        └── architecture.md
```

**验证场景**:
- [ ] 所有目录已创建
- [ ] 目录结构符合三层架构映射
- [ ] Python 采用 src 布局，与 paper-search 一致

---

### REQ-02: LaTeX 编译环境

**场景**: 使用 XeLaTeX + ctexart 编译中英文学术论文，生成出版级 PDF。

**约束映射**: H1, H8, H9, H10, S1, S2, S3, S13, D1, D5

**技术决策（LaTeX Agent 研究结论）**:

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 文档类 | **ctexart**（非 article + xeCJK） | ctex 官方推荐；自动处理标点压缩、行距 1.3x、字号五号、标题汉化 |
| 编译器 | XeLaTeX via latexmk | `$pdf_mode=5` 专为 XeLaTeX 设计（xelatex→xdv→pdf） |
| 参考文献 | BibTeX + natbib | `\citep{}`/`\citet{}` 支持，`unsrtnat` 样式 |
| 章节拆分 | `\input`（非 `\include`） | 不强制换页，灵活嵌套，论文规模无需选择性编译 |
| 字体 | Windows 默认（windowsnew 字体集） | ctex 自动检测：SimSun/SimHei/KaiTi/FangSong |
| 输出目录 | `paper/build/`（隔离编译产物） | 保持项目整洁 |

**latexmkrc 配置**:
```perl
$pdf_mode = 5;
$xelatex = 'xelatex -file-line-error -interaction=nonstopmode -synctex=1 %O %S';
$bibtex = 'bibtex %O %B';
$out_dir = 'build';
$aux_dir = 'build';
$clean_ext = 'synctex.gz synctex.gz(busy) run.xml';
@default_files = ('main.tex');
$force_mode = 0;
$max_repeat = 5;
```

**main.tex 前言核心宏包**:
- ctexart[UTF8, a4paper, 12pt, zihao=-4]
- geometry（页边距 2.54/3.17cm）
- amsmath, amssymb, amsthm, mathtools（数学）
- graphicx, float, booktabs, subcaption（图表）
- natbib[numbers, sort&compress], hyperref, cleveref（引用）
- listings, xcolor, algorithm2e（代码/算法）
- siunitx, enumitem（辅助）

**验证场景**:
- [ ] TeX Live 安装后，`cd paper && latexmk` 成功生成 PDF
- [ ] 中英文混排正确渲染，标点压缩正常
- [ ] `\bibliographystyle{unsrtnat}` + `\bibliography{bib/references}` 正确编译
- [ ] `checkcites build/main.aux` 报告零未定义引用

---

### REQ-03: CLAUDE.md 项目配置

**场景**: Claude Code 启动会话时加载项目级指令，规范智能体行为和学术输出标准。

**约束映射**: S7（渐进式披露，<300 行）

**必须包含的核心要素**:

1. **架构与技术栈约定**
   - XeLaTeX + ctexart, BibTeX + natbib
   - Python 3.12, uv, hatchling, src 布局
   - 三层架构（编排/知识/集成）

2. **工具与资源指针**
   - paper-search MCP 工具清单（4 个工具及用途）
   - Dify MCP 知识库检索工具
   - 数据目录路径映射（data/raw, data/processed, output/）
   - 构建脚本使用说明

3. **验证标准与工作流纪律**
   - 修改 .tex 文件后必须运行 `latexmk` 验证编译
   - 修改 .bib 文件后运行 `checkcites` 检查引文一致性
   - 每句独占一行（便于 git diff）

4. **学术风格约束**
   - 客观第三人称论述语气
   - 避免大模型套话（"值得注意的是"、"总之"等）
   - 引用格式：`\citep{}` 叙述外引用，`\citet{}` 叙述内引用
   - 数学公式使用 amsmath 环境（禁止 `$$...$$`）

5. **安全边界**
   - 不修改全局配置和系统字体
   - 不泄露 .env 中的 API Key
   - 不执行未经批准的 `git push`

**验证场景**:
- [ ] CLAUDE.md 行数 ≤ 300
- [ ] 包含所有 5 个核心要素
- [ ] 路径指针全部有效
- [ ] 不包含具体业务逻辑或 API 文档

---

### REQ-04: MCP 服务器配置

**场景**: Claude Code 通过 MCP 连接 paper-search 工具和 Dify 知识库。

**约束映射**: H6, H7, H11, S11, S12, D2, D3, R4, R8

**技术决策（MCP Agent 研究结论）**:

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 配置格式 | `.mcp.json`（项目根目录） | 团队共享，可提交 Git |
| paper-search 传输 | stdio（command + args） | 本地进程，低延迟 |
| Dify 集成方案 | **方案 A：自定义 MCP 桥接** | 可精细控制 hybrid_search、reranking 等参数 |
| 自定义命令 | Skills 格式（`.claude/skills/`） | Claude Code 推荐的新格式 |
| 权限管理 | `.claude/settings.local.json` | 不提交，包含权限白名单 |

**`.mcp.json` 配置**:
```json
{
  "mcpServers": {
    "paper-search": {
      "command": "uv",
      "args": ["run", "paper-search-mcp"],
      "cwd": "C:/Users/17162/Desktop/Terms/workflow",
      "env": {
        "SERPAPI_API_KEY": "${SERPAPI_API_KEY}",
        "LLM_PROVIDER": "${LLM_PROVIDER}",
        "LLM_MODEL": "${LLM_MODEL}",
        "LLM_BASE_URL": "${LLM_BASE_URL}",
        "OPENAI_API_KEY": "${OPENAI_API_KEY}"
      }
    },
    "dify-knowledge": {
      "command": "uv",
      "args": ["run", "python", "scripts/dify-kb-mcp/server.py"],
      "env": {
        "DIFY_API_BASE_URL": "${DIFY_API_BASE_URL}",
        "DIFY_API_KEY": "${DIFY_API_KEY}",
        "DIFY_DATASET_ID": "${DIFY_DATASET_ID}"
      }
    }
  }
}
```

**自定义 Skills（3 个）**:
1. `/search-literature` — 调用 paper-search 工作流搜索学术文献
2. `/retrieve-kb` — 从 Dify 知识库检索文献片段
3. `/validate-citations` — 验证 LaTeX 引用完整性（cite 键 vs bib 条目）

**Dify MCP 桥接服务器**（`scripts/dify-kb-mcp/server.py`）:
- 暴露 2 个工具：`retrieve_knowledge`（混合检索）、`list_documents`（文档列表）
- 使用 httpx 异步调用 Dify `/v1/datasets/{id}/retrieve` API
- 支持 hybrid_search、reranking、score_threshold 等参数

**验证场景**:
- [ ] `.mcp.json` JSON 格式有效
- [ ] paper-search MCP 可正常启动（`uv run paper-search-mcp`）
- [ ] Dify MCP 桥接模板代码无语法错误
- [ ] 3 个 Skills 的 SKILL.md 格式正确

---

### REQ-05: Python 数据处理环境

**场景**: 运行数据清洗、分析和 LaTeX 资产生成脚本。

**约束映射**: H4, H5, H12, H13, H14, S5, S6, S8, S9, S10

**技术决策（Python Agent 研究结论）**:

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 构建后端 | hatchling | 与 paper-search 一致 |
| 布局 | src 布局（src/vibewriting/） | 避免隐式导入问题 |
| pandas 版本 | `>=2.2,<3.0` | pandas 3.0 Arrow 后端有破坏性变更 |
| numpy 版本 | `>=1.26,<2.0` | pandas 2.2.x 依赖 numpy <2.0 |
| 图表导出 | matplotlib pgf 后端 | tikzplotlib 已废弃 |
| workspace | 不使用 | 两项目在不同磁盘，生命周期不同 |

**pyproject.toml 核心依赖**:
```toml
dependencies = [
    "pandas>=2.2,<3.0",
    "numpy>=1.26,<2.0",
    "matplotlib>=3.10",
    "seaborn>=0.13",
    "scipy>=1.14",
    "statsmodels>=0.14",
    "pydantic>=2.0",
    "httpx",
    "python-dotenv",
    "tabulate>=0.9",
    "jinja2>=3.1",
]

[project.optional-dependencies]
perf = ["polars>=1.30", "pyarrow>=15.0"]
latex = ["pylatex>=1.4"]

[dependency-groups]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "ruff>=0.14", "mypy>=1.10"]
```

**与 paper-search 兼容性验证**:
- 共享依赖：pydantic ≥2.0, httpx, python-dotenv — 无版本冲突
- 独立依赖：科研库（pandas/scipy）与 LLM SDK（openai/anthropic）无交集
- 结论：保持独立项目，松耦合集成

**验证场景**:
- [ ] `uv sync` 成功，无版本冲突
- [ ] `uv run python -c "import pandas, matplotlib, seaborn, scipy; print('OK')"` 成功
- [ ] `uv lock` 生成一致的锁文件
- [ ] pyproject.toml 版本约束与 paper-search 无冲突

---

### REQ-06: Git 仓库初始化

**场景**: 版本控制科研项目的所有文件。

**约束映射**: 无特殊约束

**`.gitignore` 覆盖范围（LaTeX Agent 提供的完整规则）**:
- LaTeX 编译产物（.aux, .log, .bbl, .synctex.gz, .xdv 等 50+ 类型）
- 编译输出目录（paper/build/）
- Python 缓存（__pycache__, .mypy_cache, .ruff_cache）
- 环境文件（.env, .venv/）
- 数据大文件（data/raw/ 中的特定类型）
- IDE 配置（.vscode/settings.json 中的敏感部分）
- 不忽略：.env.example, .mcp.json, paper/figures/*, paper/bib/*

**验证场景**:
- [ ] `git init` 成功
- [ ] .gitignore 正确过滤 LaTeX 辅助文件
- [ ] .env 不被追踪，.env.example 被追踪
- [ ] .mcp.json 被追踪（项目级共享配置）

---

### REQ-07: 构建脚本

**场景**: 一键编译论文和运行常用任务。

**约束映射**: H2, H3

**`build.sh` 功能（LaTeX Agent 提供的完整实现）**:

| 命令 | 功能 |
|------|------|
| `bash build.sh build` | latexmk 编译论文，输出到 paper/build/ |
| `bash build.sh watch` | 持续编译模式（latexmk -pvc） |
| `bash build.sh clean` | 清理所有编译产物 |
| `bash build.sh check` | checkcites 引文完整性检查 |
| `bash build.sh doi2bib <DOI>` | curl DOI 内容协商获取 BibTeX 条目 |

**特性**:
- Git Bash 兼容（set -euo pipefail）
- 彩色输出（错误红色、成功绿色、警告黄色）
- 编译失败时自动提取关键错误行
- DOI 到 BibTeX 转换（无第三方依赖，用 curl 的 Accept 头）

**验证场景**:
- [ ] `bash build.sh build` 编译成功（需 TeX Live）
- [ ] `bash build.sh clean` 正确清理 paper/build/
- [ ] `bash build.sh doi2bib 10.1038/s41586-021-03819-2` 返回 BibTeX 条目
- [ ] 错误时返回非零退出码

---

### REQ-08: 已有工作流集成准备

**场景**: paper-search 系统作为外部工具通过 MCP 集成到写作系统。

**约束映射**: H6, H14, D3

**集成方式**:
- 通过 `.mcp.json` 的 stdio 传输引用 paper-search
- 不复制代码，不使用 uv workspace
- CLAUDE.md 记录 paper-search 的 4 个 MCP 工具：
  - `search_papers(query, domain, max_results)` — 启动搜索
  - `decide(session_id, action, user_response)` — 提交检查点决策
  - `export_results(session_id, format)` — 导出结果
  - `get_session(session_id)` — 查询会话状态
- `.claude/settings.local.json` 配置 `additionalDirectories` 包含 workflow 路径

**验证场景**:
- [ ] MCP 配置中 paper-search `cwd` 路径正确
- [ ] CLAUDE.md 记录了完整的工具清单和用法
- [ ] 无 paper-search 代码的硬拷贝

---

### REQ-09: Dify MCP 桥接服务器（新增）

**场景**: 自定义 MCP 服务器桥接 Dify 知识库 API，支持精细化检索参数。

**约束映射**: H7, H11, D2, R4

**规格（MCP Agent 提供的完整实现）**:
- Python 脚本：`scripts/dify-kb-mcp/server.py`
- 依赖：mcp ≥1.22, httpx, python-dotenv
- 暴露工具：
  - `retrieve_knowledge(query, top_k, search_method, score_threshold)` — 混合检索
  - `list_documents(page, limit, keyword)` — 文档列表
- 环境变量：DIFY_API_BASE_URL, DIFY_API_KEY, DIFY_DATASET_ID
- 支持 hybrid_search、keyword_search、semantic_search 三种检索方法
- 自动启用重排序（reranking）

**验证场景**:
- [ ] `python scripts/dify-kb-mcp/server.py` 无语法错误
- [ ] 环境变量占位符配置完整
- [ ] Dify API 可达时，检索返回结构化 Markdown 结果

---

### REQ-10: 环境验证脚本（新增）

**场景**: 一键验证开发环境完整性（Python 依赖 + LaTeX 工具链）。

**约束映射**: H1, H4, R1

**规格（Python Agent 提供的完整实现）**:
- Python 脚本：`scripts/validate_env.py`（PEP 723 inline metadata，可直接 `uv run`）
- 检查项：Python 版本、核心依赖版本、LaTeX 发行版、可选依赖
- 输出：彩色 [PASS]/[FAIL] 报告
- 退出码：0 = 全部通过，1 = 必需依赖缺失

**验证场景**:
- [ ] `uv run scripts/validate_env.py` 正确报告已安装/缺失的依赖
- [ ] LaTeX 未安装时显示 [FAIL] 但不阻塞其他检查
- [ ] 退出码正确反映验证结果

---

## Success Criteria

| ID | 判据 | 验证方式 |
|----|------|---------|
| SC-01 | 项目目录结构完整，符合三层架构 + src 布局 | `tree` 命令检查 |
| SC-02 | LaTeX 模板文件就绪（main.tex + latexmkrc + sections/） | 文件存在性检查 |
| SC-03 | CLAUDE.md ≤ 300 行，包含 5 个核心要素 | `wc -l` + 内容审查 |
| SC-04 | `.mcp.json` 包含 paper-search 和 dify-knowledge 配置 | `jq .` 格式验证 |
| SC-05 | `uv sync` 成功，Python 依赖可用 | 命令执行测试 |
| SC-06 | Git 仓库已初始化，.gitignore 正确 | `git status` 检查 |
| SC-07 | `build.sh` 在 Git Bash 中可运行 | `bash build.sh check` 测试 |
| SC-08 | paper-search 通过 MCP 集成（非代码拷贝） | 配置审查 |
| SC-09 | Dify MCP 桥接模板代码无语法错误 | `python -c "import ast; ast.parse(open(...).read())"` |
| SC-10 | 3 个 Skills 的 SKILL.md 格式正确 | YAML frontmatter 解析 |
| SC-11 | `uv run scripts/validate_env.py` 正确运行 | 执行测试 |
| SC-12 | 安装 TeX Live 后 `latexmk` 可编译 main.tex | 编译测试（延迟验证） |

---

## Appendix: 多 Agent 研究来源

| Agent | 上下文边界 | 关键发现数 | 代码片段数 |
|-------|-----------|-----------|-----------|
| LaTeX Agent | 学术排版生态系统 | 8 项约束 + 8 项推荐 | latexmkrc, main.tex, .gitignore, build.sh |
| MCP Agent | MCP + Dify 集成架构 | 6 项约束 + 7 项推荐 | .mcp.json, settings.local.json, 3x SKILL.md, dify-kb-mcp/server.py |
| Python Agent | 科研数据处理工具链 | 5 项约束 + 8 项推荐 | pyproject.toml, validate_env.py |
