# 项目当前状态

**最后更新**: 2026-02-23
**阶段**: P0+P1+P2+P4 完成（34/52），P3 待 TeX Live，P4 仅 5.7 待 Dify 凭据

## 环境

| 项目 | 版本/状态 | 备注 |
|------|----------|------|
| OS | Windows 11 | 路径用正斜杠，shell 用 Git Bash |
| Python | 3.12.2 | 满足 >=3.11 要求 |
| uv | 0.6.9 | 依赖管理工具，`uv sync` 已完成 |
| Git | 2.52.0 | 版本控制 |
| Node.js | v22.14.0 | MCP 相关工具可能需要 |
| TeX Live | **未安装** | 阻塞 LaTeX 编译，需用户手动安装（约 8GB） |
| make | **未安装** | 构建脚本用 bash 替代 |
| Dify | 已有实例 | URL + API Key + Dataset ID 待配置 |
| Windows 字体 | 就绪 | SimSun/SimHei/KaiTi/FangSong 已预装 |

## 已有资产

| 资产 | 路径 | 说明 |
|------|------|------|
| 系统设计文档 | `origin.md` | 完整架构蓝图（24KB） |
| OPSX Proposal | `openspec/changes/project-foundation-architecture/proposal.md` | 10 个需求定义 + 12 个成功判据 |
| 团队研究报告 | `.claude/team-plan/vibewriting-research.md` | 约束集 + MVP 路径 |
| paper-search | `C:\Users\17162\Desktop\Terms\workflow` | 外部项目，生产级，213 测试，4 个 MCP 工具 |
| **CLAUDE.md** | `CLAUDE.md` | 89 行，5 核心要素（P0 产出） |
| **pyproject.toml** | `pyproject.toml` | Python 包配置，uv 管理依赖（P0 产出） |
| **uv.lock** | `uv.lock` | 依赖锁文件，已提交保证可复现性（P0 产出） |
| **config.py** | `src/vibewriting/config.py` | 集中配置管理，基于 python-dotenv（P0 产出） |
| **.env.example** | `.env.example` | 环境变量模板（P0 产出） |
| **.gitignore** | `.gitignore` | 覆盖 LaTeX + Python + 虚拟环境（P0 产出） |
| **项目脚手架** | `src/vibewriting/` | 三层架构目录：agents/ models/ processing/ latex/ visualization/（P0 产出） |
| **.mcp.json** | `.mcp.json` | MCP 服务器配置：paper-search(stdio) + dify-knowledge(bridge)（P1 产出） |
| **settings.local.json** | `.claude/settings.local.json` | Claude Code 本地设置：additionalDirectories 授权 paper-search 路径（P1 产出） |
| **SKILL: search-literature** | `.claude/skills/search-literature/SKILL.md` | 文献检索工作流 Skill：4 个 MCP 工具调用步骤 + checkpoint 交互（P1 产出） |
| **SKILL: retrieve-kb** | `.claude/skills/retrieve-kb/SKILL.md` | 知识库检索 Skill：retrieve_knowledge + list_documents（P1 产出） |
| **SKILL: validate-citations** | `.claude/skills/validate-citations/SKILL.md` | 引用验证 Skill：checkcites 工作流（P1 产出） |
| **validate_env.py** | `scripts/validate_env.py` | 环境验证脚本：彩色控制台输出 + JSON 报告，分级退出码 0/1/2（P2 产出） |
| **dify-kb-mcp/server.py** | `scripts/dify-kb-mcp/server.py` | Dify 知识库 MCP 桥接服务器：FastMCP，2 个工具，httpx 异步客户端，优雅降级，PEP 723 内联依赖（P4 产出） |

## OPSX 变更管理

### project-foundation-architecture

| 阶段 | 状态 | 说明 |
|------|------|------|
| Proposal | 已完成 | 约束分析、需求定义（REQ-01 ~ REQ-10）、成功判据（SC-01 ~ SC-12） |
| Design | 已完成 | 9 项技术决策（D1-D9），见 `openspec/changes/project-foundation-architecture/design.md` |
| Specs | 已完成 | 6 个模块规格，见 `openspec/changes/project-foundation-architecture/specs/` |
| Tasks | 已完成 | 37 项任务，6 个阶段（P0-P4 + 最终验证），见 `openspec/changes/project-foundation-architecture/tasks.md` |

### 需求清单（Proposal 中定义）

| ID | 需求 | 关键内容 |
|----|------|---------|
| REQ-01 | 项目目录结构 | 三层架构映射 + src 布局 |
| REQ-02 | LaTeX 编译环境 | XeLaTeX + ctexart + latexmkrc |
| REQ-03 | CLAUDE.md 配置 | <=300 行，5 个核心要素 |
| REQ-04 | MCP 服务器配置 | paper-search + dify-knowledge |
| REQ-05 | Python 数据处理环境 | pyproject.toml + uv |
| REQ-06 | Git 仓库初始化 | .gitignore 覆盖 LaTeX + Python |
| REQ-07 | 构建脚本 | build.sh（Git Bash 兼容） |
| REQ-08 | paper-search 集成 | MCP stdio 引用，非代码拷贝 |
| REQ-09 | Dify MCP 桥接服务器 | scripts/dify-kb-mcp/server.py |
| REQ-10 | 环境验证脚本 | scripts/validate_env.py |

## OPSX 技术决策摘要（Design 阶段产出）

| 决策 | 内容 | 关键选择 |
|------|------|---------|
| D1 | 分阶段降级交付 | P0-P4 五阶段，按外部阻塞状态渐进交付 |
| D2 | LaTeX 编译驱动 | latexmk 统一驱动（`$pdf_mode=5`），不保留手工回退 |
| D3 | 依赖锁定 | 提交 uv.lock 到 Git，保证科研可复现性 |
| D4 | Dify 失败策略 | 降级为无知识库模式，记录告警，不阻塞主流程 |
| D5 | 环境验证退出码 | 分级语义：0=全通过, 1=必需失败, 2=仅可选失败 + JSON 报告 |
| D6 | Git 初始化 | 幂等校验模式，已有 .git 时仅补全配置 |
| D7 | 配置管理 | .env + python-dotenv，.env.example 提交 Git |
| D8 | 日志策略 | Python logging 模块，文件(详细) + 控制台(摘要) |
| D9 | paper-search 集成 | MCP stdio 协议，.mcp.json 配置绝对路径 |

## OPSX 规格模块（Specs 阶段产出）

| 模块 | 覆盖需求 | 路径 |
|------|---------|------|
| project-scaffold | REQ-01, REQ-06 | `specs/project-scaffold/spec.md` |
| latex-compilation | REQ-02, REQ-07 | `specs/latex-compilation/spec.md` |
| claude-config | REQ-03 | `specs/claude-config/spec.md` |
| mcp-integration | REQ-04, REQ-08, REQ-09 | `specs/mcp-integration/spec.md` |
| python-environment | REQ-05 | `specs/python-environment/spec.md` |
| env-validation | REQ-10 | `specs/env-validation/spec.md` |

## 实施阶段（Tasks 阶段产出，共 37 项任务）

| 阶段 | 内容 | 任务数 | 阻塞条件 | 状态 |
|------|------|--------|---------|------|
| P0 | 项目脚手架 + Git + Python + CLAUDE.md | 13 | 无 | **已完成** |
| P1 | MCP 配置 + paper-search 集成 | 7 | 无 | **已完成** |
| P2 | 环境验证脚本 v1 | 8 | 无 | **已完成** |
| P3 | LaTeX 模板 + 构建脚本 | 10 | TeX Live 安装 | 阻塞中 |
| P4 | Dify MCP 桥接服务器 | 7 | Dify 凭据（仅 5.7） | **6/7 完成**（5.7 待凭据） |
| 最终验证 | 全量校验 | 7 | P0-P4 完成 | 待实施 |

## 下一步行动

1. **P0+P1+P2+P4 已完成**: 所有无外部阻塞的阶段已交付（34/52 任务），P4 桥接服务器代码完成（6/7，仅集成测试 5.7 待 Dify 凭据）
2. **环境验证**: 运行 `uv run scripts/validate_env.py` 可检查当前环境状态（彩色控制台输出 + JSON 报告）
3. **分级退出码**: 0=全部通过, 1=必需项失败, 2=仅可选项失败（D5 决策已落地）
4. **阻塞项**: TeX Live 安装（阻塞 P3，用户手动操作，约 30-60 分钟）、Dify 凭据（仅阻塞 P4 任务 5.7 的集成验证）
5. **建议执行顺序**: ~~P0~~ -> ~~P1~~ -> ~~P2~~ -> ~~P4(代码)~~ -> [等待 TeX Live] **P3** -> [等待 Dify 凭据] P4.5.7 -> 最终验证
6. **P0 产出清单**: pyproject.toml, uv.lock, CLAUDE.md, config.py, .env.example, .gitignore, .gitattributes, 完整目录结构, .venv（Python 3.12.2）
7. **P1 产出清单**: .mcp.json, .claude/settings.local.json, 3 个 Skills（search-literature, retrieve-kb, validate-citations）
8. **P2 产出清单**: scripts/validate_env.py（环境验证脚本，彩色输出 + JSON 报告 + 分级退出码）
9. **P4 产出清单**: scripts/dify-kb-mcp/server.py（FastMCP 桥接服务器，204 行，2 个 MCP 工具，httpx 异步客户端，重试逻辑，优雅降级，PEP 723 内联依赖），.mcp.json 已更新（PEP 723 兼容 args + 显式 cwd）

## MVP 路径（建议优先级）

```
MVP-1: 项目脚手架 + CLAUDE.md + Git 初始化  [已完成]
  |
MVP-2: MCP 配置 + paper-search 集成 + Skills  [已完成]
  |
MVP-3: 环境验证脚本 v1  [已完成]
  |
MVP-4: [等待 TeX Live] LaTeX 模板 + 编译链验证
  |
MVP-5: 数据处理管线 (CSV -> Pandas -> LaTeX assets)
  |
MVP-6: 单智能体草稿撰写
  |
MVP-7: 多智能体编排 + 章节并行生成
  |
MVP-8: 编译链 + 自动修复 + 同行评审模拟
```
