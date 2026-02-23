# 系统架构概览

**项目**: vibewriting - 基于 Claude Code 与 Dify 知识库的科研论文自动化写作系统
**目标**: 输入论文主题，端到端产出可编译的 LaTeX 论文 + PDF
**状态**: 基础架构搭建完成（Phase 1 归档）| 路线图 v4 已就绪（Phase 2-7 规划完成）

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

已交付的 3 个 Skills：
- `search-literature` -- 文献检索工作流（search_papers -> decide -> export_results）
- `retrieve-kb` -- Dify 知识库检索（retrieve_knowledge + list_documents）
- `validate-citations` -- 引用完整性验证（checkcites 工作流）

### 知识与检索层

两个 MCP 服务器提供知识检索能力：

| 服务器 | 传输方式 | 工具 | 状态 |
|--------|---------|------|------|
| paper-search | stdio | `search_papers`, `decide`, `export_results`, `get_session` | 已完成 |
| dify-knowledge | stdio | `retrieve_knowledge`, `list_documents` | 已完成（待 Dify 凭据验证） |

**paper-search**: 位于 `C:\Users\17162\Desktop\Terms\workflow`，独立项目，通过 MCP stdio 协议集成（D9 决策）
**Dify 桥接**: FastMCP 服务器（`scripts/dify-kb-mcp/server.py`，204 行），PEP 723 内联依赖

Dify 桥接服务器特性：
- httpx 异步客户端，调用 Dify `/v1/datasets/{id}/retrieve` 和 `/v1/datasets/{id}/documents` API
- `retrieve_knowledge`: 支持 hybrid/keyword/semantic 搜索 + reranking
- `list_documents`: 分页 + 关键词过滤
- 优雅降级：凭据缺失时服务器正常启动，工具调用返回结构化错误
- 重试逻辑：MAX_RETRIES（最小 1）和 TIMEOUT 可通过环境变量配置
- 4xx 短路：客户端错误不重试，仅 5xx 和网络错误重试

### 集成与执行层

| 组件 | 技术方案 | 用途 | 状态 |
|------|---------|------|------|
| 数据处理 | Python 3.12 + pandas + scipy + statsmodels | CSV/JSON 清洗、统计分析 | 依赖就绪，管线待建 |
| 可视化 | matplotlib + seaborn（pgf 后端导出） | 生成 PDF/PGF/PNG 图表 | 依赖就绪，管线待建 |
| LaTeX 表格 | Python + jinja2 + tabulate | 生成 .tex 表格文件 | 依赖就绪，管线待建 |
| 编译链 | XeLaTeX + latexmk + BibTeX | 论文编译，输出 PDF | 模板就绪，需 TeX Live |

## 七阶段工作流

完整路线图见 `openspec/ROADMAP.md`（v4，617 行）。

### 阶段总览

```
Phase 1: 基础架构 [已完成]
   |
   +---> Phase 2: 数据模型 + 处理管线        Phase 3: 文献整合工作流
   |        (资产契约 + 图表)                   (证据卡 + BibTeX)
   |              |                                    |
   |              +------------ Approval Gates --------+
   |                                |
   |                                v
   |                   Phase 4: 单 Agent 草稿撰写
   |                       (Evidence-First + 增量编译)
   |                                |
   |                                v
   |                   Phase 5: 多 Agent 编排
   |                       (Orchestrator + 角色 Agent)
   |                                |
   |                                v
   |                   Phase 6: 编译 + 质量保证
   |                       (自修复 + 同行评审模拟)
   |                                |
   |                                v
   |                   Phase 7: 端到端集成
   |                       (一键: 主题 -> PDF)
```

各阶段对应四个核心工作流：

| 工作流 | 阶段 | 输入 | 输出 |
|--------|------|------|------|
| 智能化文献检索 | Phase 3 | 研究主题 | `literature_cards.jsonl` + BibTeX |
| 数据分析与资产生成 | Phase 2 | 原始数据 | 图表(.pgf/.pdf) + 表格(.tex) + `asset_manifest.json` |
| 协同撰写 | Phase 4 + 5 | 证据卡 + 数据资产 | `paper/sections/*.tex` + `paper_state.json` |
| 编译与评审 | Phase 6 + 7 | LaTeX 源码 | PDF + 审查报告 + `run_metrics.json` |

## 阶段产物契约体系

JSON 是唯一事实源，LaTeX 是渲染层。所有阶段产物通过机器可验证的 JSON Schema 定义。

```
src/vibewriting/contracts/
  +-- paper_state.json        <- 论文全局状态机（章节/图表/引用/claim 状态 + metrics）
  +-- literature_cards.jsonl  <- 文献证据卡集合
  +-- asset_manifest.json     <- 数据资产清单（图表/表格路径 + 哈希 + 语义描述）
  +-- run_manifest.json       <- 运行环境锁定（run_id + 数据版本/种子/依赖/TeX Live 版本）
  +-- glossary.json           <- 术语表（术语 -> 定义，跨章节统一）
  +-- symbols.json            <- 符号表（符号 -> 含义，跨章节统一）
  +-- schemas/                <- JSON Schema 定义文件
```

产出阶段分配：

| 契约文件 | 产出阶段 | 消费阶段 |
|---------|---------|---------|
| `asset_manifest.json` | Phase 2 | Phase 4/5/6 |
| `run_manifest.json` | Phase 2 | Phase 6/7 |
| `literature_cards.jsonl` | Phase 3 | Phase 4/5/6 |
| `paper_state.json` | Phase 4 | Phase 5/6/7 |
| `glossary.json` + `symbols.json` | Phase 4 初版 | Phase 5 合并裁决, Phase 6 一致性验证 |

契约强校验与自愈：写入任何契约文件前，必须经过 `jsonschema.validate()` 拦截，校验失败触发 Prompt 反弹修复（最多重试 3 次）。

引用完整性约束（Phase 6 验证）：
- `paper_state` 中的 `claim_id` -> `literature_cards`
- `paper_state` 中的 `asset_id` -> `asset_manifest`
- 术语/符号 -> `glossary` / `symbols`
- `bib_key` -> `references.bib`

## 跨阶段设计原则（9 项）

详细说明见 `openspec/ROADMAP.md` "跨阶段设计原则" 章节。

| 编号 | 原则 | 核心思想 |
|------|------|---------|
| 1 | 阶段产物契约 | JSON Schema + 自愈循环 + 引用完整性外键 |
| 2 | 证据优先工作流 | Evidence Card + claim 追溯，Writer 只引用已入库证据 |
| 3 | Git 一等公民 | auto commit + snapshot + stash，`auto:` 前缀区分 |
| 4 | 人机协同审批门 | AskUserQuestion 实现 Approval Gates |
| 5 | LaTeX 增量编译 | `draft_main.tex`(单章节) -> `main.tex`(全量) |
| 6 | 可观测性与指标 | run_id + 8 项指标（文献/写作/编译/体验） |
| 7 | 合规与 AI 披露 | 引用摘抄限制 + AI 声明可开关 |
| 8 | 源码溯源注释 | `%% CLAIM_ID: EC-2026-XXX` 注释可追溯 |
| 9 | Prompt 缓存架构 | 静态头部(schemas+证据卡) + 动态尾部(任务指令) |

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

## LaTeX 编译链

```
paper/main.tex
  |-- \input{sections/introduction.tex}
  |-- \input{sections/related-work.tex}
  |-- \input{sections/method.tex}
  |-- \input{sections/experiments.tex}
  |-- \input{sections/conclusion.tex}
  |-- \bibliography{bib/references}
  `-- \input{sections/appendix.tex}
       |
       v
  latexmk (latexmkrc: $pdf_mode=5, out_dir=build)
       |
       v
  paper/build/main.pdf
```

latexmkrc 配置：
- `$pdf_mode = 5` -- 使用 XeLaTeX
- `$out_dir = 'build'` / `$aux_dir = 'build'` -- 隔离编译产物
- `$max_repeat = 5` -- 最大编译迭代次数
- `-file-line-error -interaction=nonstopmode -synctex=1` -- 编译选项

## 关键约束备忘

- TeX Live 未安装时，LaTeX 编译链不可用（validate_env.py 将其标记为 optional/blocked）
- make 未安装，构建脚本使用 bash 替代（`build.sh`）
- Dify 原生 MCP 暴露应用级接口，需自定义桥接服务器精细控制检索参数
- tikzplotlib 已废弃，必须用 matplotlib pgf 后端替代
- vibewriting(F:) 与 paper-search(C:) 在不同磁盘，保持独立项目
- CLAUDE.md 渐进式披露，不超过 300 行
- LaTeX 每句独占一行，便于 git diff
