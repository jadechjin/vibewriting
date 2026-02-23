# 目录结构地图

**最后更新**: 2026-02-23
**来源**: project-foundation-architecture 变更归档后的实际文件系统

## 完整目录树

```
F:/vibewriting/
|
|-- CLAUDE.md                          # Claude Code 项目配置（90 行）
|-- pyproject.toml                     # Python 包定义（hatchling + src 布局）
|-- uv.lock                            # 依赖锁文件（提交 Git，D3 决策）
|-- .env.example                       # 环境变量模板
|-- .gitignore                         # LaTeX + Python + .venv 忽略规则
|-- .gitattributes                     # Git 属性配置
|-- build.sh                           # 构建脚本（build/watch/clean/check/doi2bib）
|-- origin.md                          # 系统设计文档（完整架构蓝图，约 24KB）
|-- .mcp.json                          # MCP 服务器配置（paper-search + dify-knowledge）
|
|-- paper/                             # LaTeX 论文源码
|   |-- main.tex                       #   ctexart 主文档（\input 章节组织）
|   |-- latexmkrc                      #   latexmk 配置（$pdf_mode=5, out_dir=build）
|   |-- sections/                      #   章节文件
|   |   |-- introduction.tex           #     引言
|   |   |-- related-work.tex           #     相关工作
|   |   |-- method.tex                 #     方法
|   |   |-- experiments.tex            #     实验
|   |   |-- conclusion.tex             #     结论
|   |   `-- appendix.tex               #     附录
|   |-- bib/                           #   参考文献
|   |   `-- references.bib             #     BibTeX 数据库
|   |-- figures/                       #   图片资源（手动放置）
|   `-- build/                         #   编译输出（gitignored）
|
|-- src/vibewriting/                   # Python 源码（src 布局）
|   |-- __init__.py                    #   包入口，版本号 "0.1.0"
|   |-- config.py                      #   集中配置（python-dotenv，D7 决策）
|   |-- processing/                    #   数据处理管道（待建）
|   |-- visualization/                 #   可视化生成（待建）
|   |-- latex/                         #   LaTeX 资产管理（待建）
|   |-- models/                        #   Pydantic 数据模型（待建）
|   `-- agents/                        #   智能体定义（预留）
|
|-- data/                              # 数据资产
|   |-- raw/                           #   原始数据（大文件 gitignored）
|   |-- processed/                     #   清洗后数据
|   `-- cache/                         #   文献分析缓存
|
|-- output/                            # 生成资产
|   |-- figures/                       #   图表输出（.pdf/.pgf/.png）
|   |-- tables/                        #   LaTeX 表格输出（.tex）
|   `-- assets/                        #   其他 LaTeX 资产
|
|-- scripts/                           # 工具脚本
|   |-- validate_env.py                #   环境验证（彩色输出 + JSON，退出码 0/1/2）
|   `-- dify-kb-mcp/                   #   Dify MCP 桥接服务器
|       `-- server.py                  #     FastMCP 服务器（204 行，PEP 723）
|
|-- tests/                             # 测试目录
|   `-- conftest.py                    #   pytest 配置
|
|-- .claude/                           # Claude Code 本地配置
|   |-- settings.local.json            #   本地设置（additionalDirectories）
|   `-- skills/                        #   自定义 Skills
|       |-- search-literature/         #     文献检索工作流
|       |   `-- SKILL.md
|       |-- retrieve-kb/               #     知识库检索
|       |   `-- SKILL.md
|       `-- validate-citations/        #     引用验证
|           `-- SKILL.md
|
|-- openspec/                          # OPSX 变更管理
|   |-- changes/
|   |   `-- archive/
|   |       `-- 2026-02-23-project-foundation-architecture/
|   |           |-- proposal.md        #   变更提案（10 需求，12 成功判据）
|   |           |-- design.md          #   技术设计（9 决策 D1-D9）
|   |           |-- tasks.md           #   任务清单（52 项，全部完成）
|   |           `-- specs/             #   6 个规格模块（已合并）
|   `-- specs/                         #   已合并的规格
|       |-- claude-config/
|       |-- env-validation/
|       |-- latex-compilation/
|       |-- mcp-integration/
|       |-- project-scaffold/
|       `-- python-environment/
|
`-- llmdoc/                            # LLM 文档系统
    |-- index.md                       #   文档索引（本系统入口）
    |-- overview/                      #   项目概览
    |-- guides/                        #   操作指南
    |-- architecture/                  #   架构详情
    `-- reference/                     #   参考资料
```

## 目录职责与来源

| 目录 | 来自阶段 | 核心用途 | gitignored |
|------|---------|---------|------------|
| `paper/` | P3 | LaTeX 论文源码和编译 | `paper/build/` |
| `src/vibewriting/` | P0 | Python 业务逻辑 | `__pycache__/` |
| `data/` | P0 | 数据资产存储 | `data/raw/*.csv` 等大文件 |
| `output/` | P0 | 生成的图表和表格 | 否 |
| `scripts/` | P2+P4 | 工具脚本 | 否 |
| `tests/` | P0 | 测试代码 | 否 |
| `.claude/` | P1 | Claude Code 配置 | 否 |
| `openspec/` | OPSX | 变更管理归档 | 否 |
| `llmdoc/` | -- | LLM 文档系统 | 否 |

## 关键文件速查

| 需要做什么 | 看哪个文件 |
|-----------|-----------|
| 了解项目配置 | `CLAUDE.md` |
| 查看/修改依赖 | `pyproject.toml` |
| 配置环境变量 | `.env.example` -> `.env` |
| 编写论文章节 | `paper/sections/*.tex` |
| 添加参考文献 | `paper/bib/references.bib` |
| 编译论文 | `build.sh` |
| 配置 MCP 服务器 | `.mcp.json` |
| 验证环境 | `scripts/validate_env.py` |
| 数据处理代码 | `src/vibewriting/processing/` |
| 图表生成代码 | `src/vibewriting/visualization/` |
