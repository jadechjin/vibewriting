# 系统架构概览

**项目**: vibewriting - 基于 Claude Code 与 Dify 知识库的科研论文自动化写作系统
**目标**: 输入论文主题，端到端产出可编译的 LaTeX 论文 + PDF
**状态**: 基础架构搭建完成（project-foundation-architecture 变更已归档）

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
