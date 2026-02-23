# 系统架构概览

**项目**: vibewriting - 基于 Claude Code 与 Dify 知识库的科研论文自动化写作系统
**目标**: 输入论文主题，端到端产出可编译的 LaTeX 论文 + PDF
**设计文档**: `origin.md`（详尽版）, `openspec/changes/project-foundation-architecture/proposal.md`（工程化版）

## 三层架构

```
+--------------------------------------------------+
|          编排与推理层 (Claude Code)                  |
|  CLAUDE.md | Skills | Sub-agents | Agent Teams    |
+--------------------------------------------------+
                    |  MCP 协议
+--------------------------------------------------+
|          知识与检索层 (Dify + paper-search)          |
|  Dify MCP Server | paper-search MCP Server         |
+--------------------------------------------------+
                    |  MCP / Bash / Python
+--------------------------------------------------+
|          集成与执行层                                |
|  Python 数据管道 | LaTeX (TeX Live) | File System   |
+--------------------------------------------------+
```

### 编排与推理层

Claude Code 作为中枢编排引擎，负责：
- 解析用户高层级研究意图，拆解为可执行子任务
- 通过 CLAUDE.md 注入项目级指令（渐进式披露，<=300 行）
- 通过 Sub-agents / Agent Teams 实现多智能体协同撰写
- 通过自定义 Skills（`.claude/skills/`）封装可复用工作流

### 知识与检索层

两个 MCP 服务器提供知识检索能力：

| 服务器 | 传输方式 | 工具 | 状态 |
|--------|---------|------|------|
| paper-search | stdio | `search_papers`, `decide`, `export_results`, `get_session` | 已完成（外部路径） |
| dify-knowledge | stdio | `retrieve_knowledge`, `list_documents` | **已完成**（待 Dify 凭据验证） |

- paper-search: 位于 `C:\Users\17162\Desktop\Terms\workflow`，生产级，213 项测试
- Dify 桥接: FastMCP 服务器（`scripts/dify-kb-mcp/server.py`，204 行），PEP 723 内联依赖（mcp[cli]>=1.0, httpx>=0.27）
  - **工具**: `retrieve_knowledge`（hybrid/keyword/semantic 搜索 + reranking）、`list_documents`（分页 + 关键词过滤）
  - **HTTP 客户端**: httpx 异步客户端，调用 Dify `/v1/datasets/{id}/retrieve` 和 `/v1/datasets/{id}/documents` API
  - **优雅降级**: 凭据缺失时服务器正常启动，工具调用返回结构化错误响应；连接失败时不崩溃
  - **重试逻辑**: 可配置 MAX_RETRIES（最小 1）和 TIMEOUT 环境变量，安全解析（无效值回退默认）
  - **4xx 短路**: 客户端错误（如 401/403）不重试，仅服务端错误（5xx）和网络错误重试
  - **MCP 配置**: `.mcp.json` 中 args 为 `["run", "scripts/dify-kb-mcp/server.py"]`（PEP 723 兼容），显式 `cwd: "F:/vibewriting"`

### 集成与执行层

| 组件 | 技术方案 | 用途 |
|------|---------|------|
| 数据处理 | Python 3.12 + pandas + scipy + statsmodels | CSV/JSON 清洗、统计分析 |
| 可视化 | matplotlib + seaborn（pgf 后端导出） | 生成 PDF/PGF/PNG 图表 |
| LaTeX 表格 | Python + jinja2 + tabulate | 生成 .tex 表格文件 |
| 编译链 | XeLaTeX + latexmk + BibTeX | 论文编译，输出 PDF |

## 四阶段工作流

```
阶段1: 文献检索             阶段2: 数据处理
[paper-search MCP]     ->  [Python/Pandas/Matplotlib]
  输出: BibTeX/JSON/MD       输出: .tex/.pdf/.png
         |                          |
         v                          v
阶段3: 协同撰写             阶段4: 编译评审
[Multi-Agent Writing]  ->  [latexmk + BibTeX + Review]
  输出: .tex 源码              输出: PDF + 评审报告
```

- **阶段1**: 复用 paper-search MCP，检查点驱动，导出 BibTeX 引用库
- **阶段2**: 原始数据 -> pandas 清洗 -> matplotlib 图表 + LaTeX 表格
- **阶段3**: Orchestrator 分析大纲，委派 Storyteller/Analyst 等角色并行撰写章节
- **阶段4**: latexmk 编译、checkcites 引文验证、模拟同行评审

## 技术栈决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| LaTeX 文档类 | ctexart | 自动处理中文标点压缩、行距、字号、标题汉化 |
| 编译器 | XeLaTeX via latexmk (`$pdf_mode=5`) | 原生 Unicode 支持，Windows 字体自动检测 |
| 参考文献 | BibTeX + natbib | `\citep{}`/`\citet{}` 引用风格 |
| Python 构建 | hatchling + src 布局 | 与 paper-search 一致 |
| 依赖管理 | uv + pyproject.toml | 快速解析，锁文件确定性 |
| 图表导出 | matplotlib pgf 后端 | tikzplotlib 已废弃，pgf 原生 LaTeX 兼容 |
| MCP 配置 | `.mcp.json`（项目级） | 可提交 Git，团队共享 |
| 章节组织 | `\input`（非 `\include`） | 不强制换页，灵活嵌套 |

## OPSX 技术决策（Design 阶段，共 9 项）

以下决策在 `openspec/changes/project-foundation-architecture/design.md` 中详细论证：

| 编号 | 决策项 | 选择 | 否决的替代方案 |
|------|--------|------|---------------|
| D1 | 交付策略 | 分阶段降级交付（P0-P4） | 容器化封装、远程编译服务 |
| D2 | LaTeX 编译驱动 | latexmk 统一驱动，不保留手工回退 | latexmk + 手工回退、固定命令链 |
| D3 | 依赖锁定 | 提交 uv.lock 到 Git | 不提交 lockfile |
| D4 | Dify 失败策略 | 可降级运行（无知识库模式） | 失败即中断 |
| D5 | 环境验证退出码 | 分级语义 0/1/2 + JSON 报告 | 简单二元退出码 |
| D6 | Git 初始化 | 幂等校验模式 | — |
| D7 | 配置管理 | .env + python-dotenv | — |
| D8 | 日志策略 | Python logging + 文件(详细) + 控制台(摘要) | — |
| D9 | paper-search 集成 | MCP stdio 协议 | 子进程 CLI 调用、直接 import |

## 实施阶段规划（P0-P4）

基于 D1（分阶段降级交付），按外部阻塞状态分 5 个阶段：

```
P0: 项目脚手架 + Git + Python + CLAUDE.md          [无阻塞]
 |  REQ-01, REQ-06, REQ-05, REQ-03
 v
P1: MCP 配置 + paper-search 集成                    [无阻塞]
 |  REQ-04, REQ-08
 v
P2: 环境验证脚本 v1（TeX/Dify 标记 blocked）         [无阻塞]
 |  REQ-10 v1
 v
P3: LaTeX 模板 + 构建脚本                           [阻塞: TeX Live]
 |  REQ-02, REQ-07
 v
P4: Dify 桥接 + 全量校验                            [阻塞: Dify 凭据]
    REQ-09, REQ-10 v2
```

## 目录结构映射

```
vibewriting/
├── origin.md              # 系统设计文档
├── CLAUDE.md              # Claude Code 项目配置
├── pyproject.toml         # Python 配置 (uv + hatchling)
├── .mcp.json              # MCP 服务器配置
├── build.sh               # 构建脚本 (Git Bash)
├── paper/                 # LaTeX 论文源码 (编译链)
│   ├── main.tex           #   ctexart 主文档
│   ├── latexmkrc          #   latexmk 配置
│   ├── sections/          #   章节 (\input 拆分)
│   ├── bib/               #   参考文献 (.bib)
│   ├── figures/           #   图片资源
│   └── build/             #   编译输出 (gitignored)
├── src/vibewriting/       # Python 源码 (src 布局)
│   ├── processing/        #   数据处理管道
│   ├── visualization/     #   可视化生成
│   ├── latex/             #   LaTeX 资产管理
│   ├── models/            #   Pydantic 数据模型
│   └── agents/            #   智能体定义 (预留)
├── data/                  # 数据资产
│   ├── raw/               #   原始数据 (gitignored 大文件)
│   ├── processed/         #   清洗后数据
│   └── cache/             #   文献分析缓存
├── output/                # 生成资产
│   ├── figures/           #   图表 (.pdf/.pgf/.png)
│   ├── tables/            #   LaTeX 表格 (.tex)
│   └── assets/            #   其他 LaTeX 资产
├── scripts/               # 工具脚本
│   ├── validate_env.py    #   环境验证
│   └── dify-kb-mcp/       #   Dify MCP 桥接服务器
├── tests/                 # 测试
└── .claude/               # Claude Code 本地配置
    ├── settings.local.json
    └── skills/            #   3 个自定义 Skill
```

## 关键约束备忘

- **H1**: TeX Live / XeLaTeX 未安装，LaTeX 编译链暂不可用
- **H2**: make 未安装，构建脚本使用 bash 替代
- **H11**: Dify 原生 MCP 暴露应用级接口，需自定义桥接服务器精细控制检索参数
- **H13**: tikzplotlib 已废弃，必须用 matplotlib pgf 后端替代
- **H14**: vibewriting(F:) 与 paper-search(C:) 在不同磁盘，保持独立项目
- **S7**: CLAUDE.md 渐进式披露，不超过 300 行
- **S13**: LaTeX 每句独占一行，便于 git diff
