## Context

科研论文自动化写作系统（vibewriting）从零搭建项目基础架构。系统设计文档 `origin.md`（24KB）已完成，定义了三层架构（编排与推理层、知识与检索层、集成与执行层）和四阶段工作流（文献检索 -> 数据处理 -> 协同撰写 -> 编译评审）。

当前状态：
- 项目目录仅含 `origin.md` 和 `openspec/` 目录
- paper-search MCP 服务器已在外部路径 `C:\Users\17162\Desktop\Terms\workflow` 独立实现（生产级，213 项测试）
- 环境：Windows 11, Python 3.12.2, uv 0.6.9, Git 2.52.0
- 阻塞项：TeX Live 未安装（阻塞 LaTeX 编译链），Dify 凭据未提供（阻塞知识库集成）

## Goals / Non-Goals

**Goals:**
- 创建完整的项目脚手架，反映三层架构设计
- 配置 Python 数据处理环境（uv + hatchling + src 布局）
- 配置 MCP 服务器集成（paper-search stdio + Dify 桥接模板）
- 创建 LaTeX 论文模板和编译配置（XeLaTeX + ctexart）
- 创建 CLAUDE.md 项目级智能体指令
- 创建环境验证和构建脚本
- 初始化 Git 仓库，配置完整的 .gitignore

**Non-Goals:**
- 不实现具体的数据处理管道逻辑（仅搭建模块骨架）
- 不实现多智能体协同撰写功能（仅预留 agents 目录）
- 不安装 TeX Live（用户手动操作）
- 不配置 Dify 生产凭据（仅创建模板和占位符）
- 不创建 Docker 容器化方案
- 不设计远程编译服务

## Decisions

### D1: 分阶段降级交付（Codex + Gemini 共识）

**选择**: 按外部阻塞状态分 5 个阶段交付，允许 TeX 和 Dify 依赖延迟解锁。

**替代方案**:
- 容器化封装 → 否决（Windows 门槛高，偏离本地工具链目标）
- 远程编译服务 → 否决（增加网络/安全复杂度）

**阶段划分**:
| 阶段 | 内容 | 阻塞条件 |
|------|------|---------|
| P0 | REQ-01(目录) + REQ-06(Git) + REQ-05(Python) + REQ-03(CLAUDE.md) | 无 |
| P1 | REQ-04(MCP配置) + REQ-08(paper-search集成) | 无 |
| P2 | REQ-10 v1(环境校验，TeX/Dify 标记 blocked) | 无 |
| P3 | REQ-02(LaTeX模板) + REQ-07(构建脚本) | TeX Live 安装 |
| P4 | REQ-09(Dify桥接) + REQ-10 v2(全量校验) | Dify 凭据 |

**理由**: 先交付可运行最小闭环，再按外部依赖解锁顺序扩展能力。

### D2: LaTeX 编译驱动 — latexmk 统一驱动

**选择**: 仅使用 latexmk（`$pdf_mode=5`），不保留手工命令链回退。

**替代方案**:
- latexmk + 手工回退 → 否决（增加维护面，latexmk 本身已处理依赖循环）
- 固定命令链 → 否决（无法自动检测编译轮数）

**理由**: latexmk 自动管理 xelatex→bibtex→xelatex→xelatex 循环，`$pdf_mode=5` 专为 XeLaTeX 设计。

### D3: 依赖锁定 — 提交 uv.lock

**选择**: 提交 uv.lock 到 Git，保证科研流水线可复现。

**替代方案**:
- 不提交 lockfile → 否决（科研可复现性要求严格）

**理由**: 科研论文数据处理管线的输出必须确定性可复现，lockfile 固定依赖版本树。

### D4: Dify MCP 桥接失败策略 — 可降级运行

**选择**: Dify 不可用时降级为无知识库模式，记录告警，不阻塞主流程。

**替代方案**:
- 失败即中断 → 否决（凭据延迟不应阻塞其他能力交付）

**理由**: Dify 是可选增强能力，核心论文撰写流程不依赖它。

### D5: 环境验证退出码 — 分级语义

**选择**: 0=全部通过, 1=必需依赖失败, 2=仅可选依赖失败。同时输出机器可读 JSON 报告。

**替代方案**:
- 简单二元退出码 → 否决（无法区分阻塞性与非阻塞性问题）

**理由**: 分级退出码允许 CI/脚本根据严重程度做不同处理。

### D6: Git 初始化 — 幂等校验模式

**选择**: 检测 .git 存在时仅做配置校验和补全，不重复 init。

**理由**: 避免覆盖已有协作设置（hooks、config 等）。

### D7: 配置管理 — .env + python-dotenv

**选择**: 使用 .env 文件管理敏感配置和环境变量，.env.example 提交到 Git。

**理由**: 标准做法，配合 .gitignore 防止凭据泄露。

### D8: 日志策略 — Python logging + 文件

**选择**: 统一使用 Python logging 模块，输出到文件（详细）+ 控制台（简洁摘要）。

**理由**: 标准化日志便于调试，控制台简洁摘要提升用户体验。

### D9: paper-search 集成 — MCP stdio 协议

**选择**: 通过 .mcp.json stdio 配置集成，Claude Code 直接使用 MCP 工具调用。

**替代方案**:
- 子进程 CLI 调用 → 否决（MCP 已提供更高级抽象）
- 直接 import → 否决（跨盘路径，违反独立项目原则）

**理由**: MCP stdio 是 Claude Code 原生集成方式，已在 paper-search 中实现。

## Risks / Trade-offs

| 风险 | 严重度 | 缓解策略 |
|------|--------|---------|
| TeX Live 未安装导致 P3 阶段不可交付 | 高 | REQ-10 预检 + 安装指引；P0-P2 独立于 TeX 可先行交付 |
| BibTeX 中文文献编码/排序异常 | 高 | .bib 强制 UTF-8 编码，引用键仅 ASCII；提供中英文混合编译 smoke test |
| paper-search 外部路径变更/权限问题 | 高 | 启动时路径探测 + 权限校验；MCP 配置使用绝对路径 |
| 凭据泄露（.env 误提交） | 高 | .gitignore 排除 .env；REQ-10 检查敏感变量存在性但不打印值 |
| Windows 路径/CRLF/Shell 差异 | 中 | Python 用 pathlib；build.sh 统一正斜杠 + 引号；.gitattributes 控制换行 |
| matplotlib pgf 后端依赖 TeX | 中 | 图表模块初始化时探测 TeX 可用性；不可用时输出诊断错误 |
| Dify 凭据长期缺失 | 中 | 降级模式 + feature flag 设计；REQ-09 标记为 OPTIONAL |

## Open Questions

所有技术决策已在 Step 3 歧义消除中解决，无遗留开放问题。

唯一外部依赖：
1. 用户何时安装 TeX Live → 不阻塞 P0-P2 交付
2. 用户何时提供 Dify 凭据 → 不阻塞 P0-P3 交付
