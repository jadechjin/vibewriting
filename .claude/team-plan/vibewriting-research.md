# Team Research: vibewriting

## 增强后的需求

**项目名称**：vibewriting - 基于 Claude Code 与 Dify 知识库的科研论文自动化写作系统

**目标**：实现一个以 Claude Code 为中枢编排引擎、通过 MCP 协议桥接 Dify 文献知识库的端到端学术论文写作系统。系统覆盖从文献检索、数据处理、多智能体协同撰写到自动化编译与评审的完整四阶段生命周期。

**技术约束**：
- 运行环境：Windows 11, Python 3.12.2, uv 0.6.9
- 编排引擎：Claude Code (通过代理 127.0.0.1:15721)
- 知识库：Dify 实例（已有文献知识库，全 MCP 化集成）
- LaTeX：TeX Live（需安装）
- 已有资产：paper-search 项目（C:\Users\17162\Desktop\Terms\workflow）

**范围边界**：
- 阶段1：智能化文献检索 - 复用 paper-search MCP Server
- 阶段2：实验数据清洗与 LaTeX 资产生成 - 新建
- 阶段3：多智能体协同撰写 - 新建
- 阶段4：自动化编译与同行评审模拟 - 新建

**验收标准**：输入论文主题后，端到端产出可编译的 LaTeX 论文 + PDF

---

## 约束集

### 硬约束

- [HC-1] **项目从零起步**：vibewriting 仓库当前仅有 origin.md 设计文档，所有代码模块需从 0 到 1 构建 — 来源：Codex
- [HC-2] **全 MCP 化 Dify 集成**：所有与 Dify 知识库的交互（检索、文档管理、元数据查询）必须通过 MCP 工具协议封装，不使用直接 HTTP 调用 — 来源：用户决策
- [HC-3] **TeX Live 作为 LaTeX 发行版**：需在 Windows 上安装完整 TeX Live 发行版（约 5GB），提供 latexmk + biber 工具链 — 来源：用户决策
- [HC-4] **纯 BibTeX 引用流程**：参考文献管理不依赖外部工具（Zotero 等），直接由 paper-search 导出 BibTeX + 系统自动生成/管理 .bib 文件 — 来源：用户决策
- [HC-5] **半自动检查点审批**：关键节点（大纲确认、论点审批、终稿审核）设置强制审批点，其余环节自动运行 — 来源：用户决策
- [HC-6] **paper-search 为文献检索基座**：阶段1 完全复用现有 paper-search MCP Server（search_papers/decide/export_results/get_session 四个工具） — 来源：Codex
- [HC-7] **Python 3.12.2 + uv 工具链**：与 paper-search (>=3.11) 兼容，使用 uv 管理依赖 — 来源：Codex
- [HC-8] **CLAUDE.md 不超过 300 行**：采用渐进式披露原则，指向而非内联 — 来源：Gemini
- [HC-9] **代理网络约束**：所有 Claude Code API 调用经过 127.0.0.1:15721 代理 — 来源：Codex

### 软约束

- [SC-1] **目录语义约定**：遵循 origin.md 约定的产物目录结构 — `assets/` (图像)、`tables/` (LaTeX 表格)、`output/` (PDF) — 来源：Codex
- [SC-2] **MCP 检查点驱动交互**：延续 paper-search 的检查点模式，用户反馈必须实质性（非敷衍） — 来源：Codex
- [SC-3] **导出格式对齐**：paper-search 已固定 JSON/BibTeX/Markdown 三种导出格式，后续模块应直接消费 — 来源：Codex
- [SC-4] **测试基线**：遵循 paper-search 的工程质量基线（pytest + pytest-asyncio + ruff），测试覆盖率 >= 80% — 来源：Codex
- [SC-5] **XML 标签结构化提示词**：智能体提示词使用 XML 标签界定系统角色、操作规则与输入边界 — 来源：Gemini
- [SC-6] **学术幻觉抑制**：写作智能体必须内置 CoT 推理链，强制在隐藏标签中建立假设树再输出结论 — 来源：Gemini
- [SC-7] **状态持久化**：长周期任务必须支持跨会话恢复，进度文件保存在 `.vibewriting/state/` — 来源：Gemini
- [SC-8] **密钥统一治理**：SerpAPI、LLM Provider、Dify API Key 通过 .env + pydantic 统一管理，不硬编码 — 来源：Codex

### 依赖关系

- [DEP-1] **阶段1 → 阶段3/4**：`export_results(bibtex/markdown/json)` 输出是写作与编译的输入基座
- [DEP-2] **阶段1 → Dify**：paper-search 输出需映射为 Dify 数据集文档/片段结构，再由 retrieve 提供给写作智能体
- [DEP-3] **阶段2 → 阶段4**：Pandas/Matplotlib 产出的图表资产必须与 LaTeX 模板路径约定一致
- [DEP-4] **阶段3 → Claude Code 能力面**：依赖 MCP 工具调用、Sub-agents 任务隔离与代理网络可达性
- [DEP-5] **阶段4 → TeX Live 环境**：latexmk + biber + 必要宏包集合
- [DEP-6] **全链路 → 密钥治理**：SerpAPI、LLM Provider、Dify API Key、代理配置统一注入

### 风险

- [RISK-1] **架构空转**：四阶段并发开发可能失控，需先定义最小可运行闭环 (MVP) — 缓解：按阶段递进实现，每阶段独立验证
- [RISK-2] **接口漂移**：paper-search PaperCollection 与 Dify 数据集 schema 若无稳定映射，引用追踪将断裂 — 缓解：定义明确的中间数据模型
- [RISK-3] **编译链失败 (Windows)**：TeX Live 首次安装耗时长，宏包不全导致 latexmk 连续失败 — 缓解：预装完整 scheme-full，提供编译错误自动修复逻辑
- [RISK-4] **学术幻觉**：LLM 可能生成不准确引用或捏造事实 — 缓解：强制 CoT 推理 + Dify 检索交叉验证 + 评审智能体后置检查
- [RISK-5] **状态持久化失败**：跨会话恢复逻辑缺陷可能导致工作丢失 — 缓解：每个检查点自动快照，JSON 格式可人工恢复
- [RISK-6] **单一检索源**：SerpAPI 限流/失效会导致阶段1退化 — 缓解：Dify 知识库作为二级缓存，已有文献可直接检索
- [RISK-7] **提示词脆弱性**：底层模型变动可能导致多智能体协作失效 — 缓解：提示词版本化管理，定义回归测试用例

---

## 成功判据

- [OK-1] 输入论文主题后，MCP `search_papers -> decide -> export_results(bibtex)` 在单会话成功完成，生成可编译引用库
- [OK-2] Dify MCP 检索返回命中片段包含可追溯元数据（文档 ID/来源），写作智能体能正确消费
- [OK-3] CSV/JSON 实验数据经 Pandas 清洗后稳定产出 `assets/*.pdf|png` 与 `tables/*.tex`，重复运行结果一致
- [OK-4] `latexmk -xelatex` + `biber` 在 Windows 连续构建成功，编译错误可自动定位并回归验证
- [OK-5] 多智能体协同撰写产出的 LaTeX 源码通过编译，章节间逻辑连贯、术语一致
- [OK-6] 模拟同行评审能自动发现至少三类问题（引用失配、图表缺注释、结构逻辑冲突）并产出修改建议
- [OK-7] 用户可在关键检查点（大纲/论点/终稿）通过 CLI 审批或修改，系统根据反馈调整
- [OK-8] 跨会话恢复功能正常：关闭 CLI 后重新启动可从上次检查点继续
- [OK-9] 端到端流程具备审计日志（检索来源、模型决策、编译日志、评审意见）

---

## 开放问题（已解决）

- Q1: Dify 集成方式？ → A: 全 MCP 化 → 约束：[HC-2]
- Q2: LaTeX 发行版选型？ → A: TeX Live → 约束：[HC-3]
- Q3: 参考文献管理工具？ → A: 纯 BibTeX 流程 → 约束：[HC-4]
- Q4: 工作流自动化程度？ → A: 半自动（检查点审批） → 约束：[HC-5]
- Q5: 实现范围？ → A: 完整四阶段系统 → 约束：[HC-1]
- Q6: 研究场景？ → A: 有具体论文主题 → 需后续确认具体主题

---

## 系统架构概要（研究发现）

### 三层架构

```
+--------------------------------------------------+
|          编排与推理层 (Claude Code)                  |
|  CLAUDE.md | Skills | Commands | Sub-agents       |
+--------------------------------------------------+
                    |  MCP
+--------------------------------------------------+
|          知识与检索层 (Dify + paper-search)          |
|  Dify MCP Server | paper-search MCP Server         |
+--------------------------------------------------+
                    |  MCP / Bash
+--------------------------------------------------+
|          集成与执行层                                |
|  Python Scripts | LaTeX (TeX Live) | File System   |
+--------------------------------------------------+
```

### 四阶段工作流

```
阶段1: 文献检索          阶段2: 数据处理
[paper-search MCP]  →   [Python/Pandas/Matplotlib]
  ↓ BibTeX/JSON            ↓ .tex/.pdf/.png
  ↓                        ↓
阶段3: 协同撰写          阶段4: 编译评审
[Multi-Agent Writing] →  [latexmk + biber + Review]
  ↓ .tex 源码              ↓ PDF + 评审报告
```

### 关键技术组件

| 组件 | 技术方案 | 来源 |
|------|---------|------|
| 文献检索 | paper-search MCP (4 tools) | 已有 |
| 知识库 | Dify MCP Server (全 MCP 化) | 需构建 MCP wrapper |
| 数据处理 | Python + Pandas + Matplotlib | 需构建 |
| LaTeX 资产 | Python -> .tex 表格/图表代码 | 需构建 |
| 智能体编排 | Claude Code Sub-agents + 自定义 Skills | 需构建 |
| 论文撰写 | Orchestrator/Storyteller/Analyst 角色 | 需构建 |
| 编译链 | TeX Live + latexmk + biber | 需安装+构建 |
| 同行评审 | Reviewer 子智能体 + 引用验证 | 需构建 |
| 状态管理 | JSON 快照 + 检查点恢复 | 需构建 |
| 项目配置 | CLAUDE.md + .env + pydantic | 需构建 |

### 建议 MVP 路径

1. **MVP-1**：TeX Live 安装 + CLAUDE.md 配置 + 项目脚手架
2. **MVP-2**：Dify MCP Server 封装 + paper-search 集成验证
3. **MVP-3**：数据处理管线 (CSV -> Pandas -> LaTeX assets)
4. **MVP-4**：单智能体草稿撰写（先不并行）
5. **MVP-5**：多智能体编排 + 章节并行生成
6. **MVP-6**：LaTeX 编译链 + 自动错误修复
7. **MVP-7**：同行评审模拟 + 端到端集成测试

---

## 环境快照

| 项目 | 状态 |
|------|------|
| Python | 3.12.2 |
| uv | 0.6.9 |
| LaTeX | 未安装（需 TeX Live） |
| Dify | 已有实例 + 知识库 |
| paper-search | 已完成 (v0.1.3, 213 tests) |
| Claude Code | 通过代理运行 |
| 操作系统 | Windows 11 |
