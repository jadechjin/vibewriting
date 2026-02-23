# vibewriting 总体路线图

> 基于 Claude Code 与 Dify 知识库的科研论文自动化写作系统
> 目标：输入论文主题，端到端产出可编译的 LaTeX 论文 + PDF

## 愿景摘要

系统将 Claude Code 作为中枢编排引擎，通过 MCP 协议桥接 paper-search（文献检索）和 Dify（知识库），驱动 Python 数据管线和 LaTeX 编译链，实现从文献定标、数据分析、草稿撰写到同行评审模拟的端到端学术写作流水线。

四个核心工作流阶段（对应 origin.md）：
1. 智能化文献检索与结构化特征提取
2. 实验数据清洗、分析与 LaTeX 资产生成
3. 多智能体协同撰写
4. 自动化编译与同行评审模拟

## 阶段依赖图

```
Phase 1: 基础架构 ✅ (2026-02-23 归档, 52/52)
   |
   +---> Phase 2: 数据模型 + 处理管线
   |        |                              ┌─ Approval Gate ─┐
   |        +---> Phase 4: 单 Agent 撰写 --┤ /approve 继续   ├--+
   |                                       └─────────────────┘  |
   +---> Phase 3: 文献整合工作流 ----+                           |
                  |                  |                           |
                  └─ Approval Gate ──+---> Phase 5: 多 Agent 编排
                                                       |
                                                       v
                                              Phase 6: 编译 + 质量保证
                                                       |
                                                       v
                                              Phase 7: 端到端集成
```

依赖关系说明：
- Phase 2 和 Phase 3 可并行开发（无相互依赖）
- Phase 4 依赖 Phase 2（数据模型 + 资产契约）+ Phase 3（证据卡 + BibTeX）
- Phase 5 依赖 Phase 4（单 Agent 验证 + 质量门禁通过后才扩展）
- Phase 6 依赖 Phase 5（需要完整的 LaTeX 源码输出）
- Phase 7 依赖 Phase 6（全流程串联）
- **Approval Gates**: Phase 2→4、Phase 3→4 之间有人工审批断点

---

## 跨阶段设计原则

### 1. 阶段产物契约（Phase Contracts）

每个阶段的输出必须通过**机器可验证的 JSON Schema** 定义，LaTeX 只是渲染层，JSON 是唯一事实源。

```
src/vibewriting/contracts/
  ├── paper_state.json      ← 论文全局状态机（章节/图表/引用/claim 状态）
  ├── literature_cards.jsonl ← 文献证据卡集合
  ├── asset_manifest.json   ← 数据资产清单（图表/表格路径 + 哈希）
  └── schemas/              ← JSON Schema 定义
      ├── paper_state.schema.json
      ├── evidence_card.schema.json
      └── asset_manifest.schema.json
```

- Phase 2 产出 `asset_manifest.json`（图表/表格清单）
- Phase 3 产出 `literature_cards.jsonl`（证据卡集合）
- Phase 4/5 消费上述契约，产出 `paper_state.json`（论文状态）
- Phase 6 验证所有契约的一致性

### 2. 证据优先工作流（Evidence-First）

写作阶段（Phase 4/5）的 Writer **只允许引用已入库的证据卡**。正文中每个 claim 必须可追溯到 `claim_id → bib_key`。

**Evidence Card 结构**:
```json
{
  "claim_id": "EC-2026-001",
  "claim_text": "Transformer 模型在长序列任务上的注意力复杂度为 O(n²)",
  "supporting_quote": "The self-attention mechanism has quadratic complexity...",
  "paraphrase": true,
  "bib_key": "vaswani2017attention",
  "location": { "doi": "10.48550/arXiv.1706.03762", "section": "3.1" },
  "methodology_notes": "理论分析，无实验验证",
  "quality_score": 9,
  "tags": ["method", "complexity", "transformer"]
}
```

### 3. Git 作为一等公民

Git 不仅是版本控制，更是**工作流安全网**：
- Phase 4: 每章节编译通过后自动 `git commit -m "auto: finish section X [cite: N papers]"`
- Phase 5: 多 Agent 修改前自动创建 snapshot commit，合并失败可 `git reset`
- Phase 6: 每次自修复补丁前 `git stash`，修坏可回退
- 所有自动提交使用 `auto:` 前缀与人工提交区分

### 4. 人机协同审批门（Approval Gates）

阶段间设置明确的 HITL（Human-In-The-Loop）断点：

| 断点 | 触发条件 | 用户操作 |
|------|---------|---------|
| Phase 2 → 4 | 图表/表格生成完毕 | `/approve` 继续 或 修改指令调整资产 |
| Phase 3 → 4 | 文献检索+证据卡完成 | `/approve` 继续 或 补充文献/调整检索 |
| Phase 4 → 5 | 单 Agent 草稿 + 门禁通过 | `/approve` 进入多 Agent 或 手动修订草稿 |
| Phase 5 → 6 | 多 Agent 合并完成 | `/approve` 进入编译评审 或 指定章节重写 |

### 5. LaTeX 增量编译策略

全量编译耗时长（尤其含 .pgf 矢量图时），采用增量策略：
- **单章节验证**: 生成 `draft_main.tex`，仅 `\input` 当前章节 → 极速编译验证语法
- **全量编译**: 所有章节通过单独验证后，合并进 `main.tex` 执行最终编译
- Phase 4/5 写作时默认用增量模式，Phase 6 最终用全量模式

---

## Phase 1: 基础架构 ✅

**状态**: 已完成并归档 (`2026-02-23-project-foundation-architecture`)

**交付物**:
- 项目脚手架（src 布局 + uv + hatchling）
- MCP 集成（paper-search + dify-knowledge 桥接服务器）
- LaTeX 模板 + build.sh 构建脚本
- 环境验证脚本（validate_env.py）
- 3 个 Skills（search-literature, retrieve-kb, validate-citations）
- 6 个 OpenSpec specs

---

## Phase 2: 数据模型 + 处理管线

**对应 origin.md**: 第二阶段（实验数据清洗、分析与 LaTeX 资产生成）

**目标**: 建立从原始数据到 LaTeX 可用资产（图表 + 表格）的自动化管线，产出机器可验证的资产契约。

**交付物**:
- [ ] Pydantic 数据模型（`src/vibewriting/models/`）
  - Paper: 论文元数据（标题、作者、摘要、引用键、质量评分）
  - Experiment: 实验配置 + 结果
  - Figure / Table: 图表/表格元数据 + 生成参数
  - Section: 章节结构（大纲、状态、引用列表）
- [ ] 阶段产物契约（`src/vibewriting/contracts/`）
  - JSON Schema 定义（paper_state, evidence_card, asset_manifest）
  - 契约验证工具函数
- [ ] 数据清洗管线（`src/vibewriting/processing/`）
  - cleaners.py: CSV/JSON 数据读取、缺失值处理、类型转换
  - transformers.py: 聚合、透视、特征工程
  - statistics.py: 描述性统计、假设检验、效应量计算
- [ ] 图表生成（`src/vibewriting/visualization/`）
  - figures.py: matplotlib 图表生成（折线图、柱状图、散点图、热力图）
  - tables.py: LaTeX 表格生成（booktabs 风格，jinja2 模板）
  - pgf_export.py: matplotlib pgf 后端导出（.pgf + .pdf 双格式）
- [ ] 管线编排入口
  - CLI 或函数接口：指定数据源 → 自动执行清洗 → 生成图表 → 输出到 output/
  - 产出 `asset_manifest.json`（资产清单 + 内容哈希）
- [ ] Golden Test 回归测试（`tests/golden/`）
  - 小样例数据 + 期望输出 baseline 文件
  - `uv run pytest -k golden`: 比较 .pgf 文本一致性 + .tex 表格一致性
  - 强制设定随机种子、matplotlib 后端参数、排序规则（防 groupby 漂移）

**涉及目录**:
```
src/vibewriting/models/       ← Pydantic 模型
src/vibewriting/contracts/    ← 阶段产物契约 + JSON Schema
src/vibewriting/processing/   ← 数据清洗 + 统计
src/vibewriting/visualization/ ← 图表 + 表格生成
data/raw/                     ← 原始数据输入
data/processed/               ← 清洗后数据
output/figures/               ← 生成的图表 (.pdf/.pgf/.png)
output/tables/                ← 生成的 LaTeX 表格 (.tex)
tests/golden/                 ← Golden Test baseline
```

**前置依赖**: Phase 1 ✅
**验证标准**:
- `uv run pytest` 全部通过（含 golden tests）
- 示例数据端到端生成图表 + 表格 + `asset_manifest.json`
- 重复运行产出相同哈希

---

## Phase 3: 文献整合工作流

**对应 origin.md**: 第一阶段（智能化文献检索与结构化特征提取）

**目标**: 建立从文献检索到结构化证据卡的完整工作流，为撰写阶段提供强约束的有据可依素材库。

**交付物**:
- [ ] 文献检索端到端工作流
  - paper-search MCP: 主题 → 搜索 → 筛选 → 导出 BibTeX
  - Dify MCP: 知识库语义检索 → 片段提取
  - 检索结果自动去重与合并
- [ ] Evidence Card（证据卡）系统
  - 每篇文献拆分为可追溯证据单元（强约束）：
    - `claim_id`: 唯一标识
    - `claim_text`: 一句话可被引用的声明
    - `supporting_quote`: 原文短摘 + paraphrase 标记
    - `bib_key`: 引用键
    - `location`: DOI/页码/章节/URL
    - `methodology_notes`: 方法论评估
    - `quality_score`: 1-10 质量评分
    - `tags`: 方法/数据集/结论类型
  - Analyst 子智能体提示词设计（独立上下文，受限工具）
  - 产出 `literature_cards.jsonl`（符合 evidence_card.schema.json）
- [ ] 本地知识缓存
  - 证据卡存储（`data/processed/literature/`）
  - 可跨会话搜索的索引（按 tags/bib_key/claim_id 检索）
- [ ] BibTeX 自动管理
  - doi2bib 批量获取
  - 引用键去重与规范化（仅 ASCII 键名）
  - references.bib 自动更新
- [ ] 增强 Skill: `search-literature` 升级为完整工作流

**涉及目录**:
```
src/vibewriting/contracts/      ← evidence_card schema
data/processed/literature/      ← 证据卡缓存 (.jsonl)
paper/bib/references.bib        ← BibTeX 数据库
.claude/skills/                 ← Skill 升级
src/vibewriting/agents/         ← Analyst 子智能体配置
```

**前置依赖**: Phase 1 ✅
**验证标准**:
- 给定主题 → 自动检索 → 产出 ≥5 篇结构化证据卡 + 更新 BibTeX
- 每张证据卡通过 JSON Schema 校验
- `literature_cards.jsonl` 中无重复 claim_id

---

## Phase 4: 单 Agent 草稿撰写

**对应 origin.md**: 第三阶段前半（单一上下文撰写验证）

**目标**: 验证单个 Claude Code 会话能否基于证据卡和数据资产，生成符合学术规范的 LaTeX 草稿。

**交付物**:
- [ ] 论文大纲生成
  - 基于主题 + 证据卡聚类 → 生成章节大纲
  - 每章节：标题、要点、预期引用（claim_id 列表）、预期图表（asset_id 列表）
  - 大纲写入 `paper_state.json`
- [ ] 逐章节草稿撰写（Evidence-First 约束）
  - 按大纲逐章生成 LaTeX 源码
  - **只允许引用已入库证据卡的 claim**（claim_id → bib_key 可追溯）
  - 自动插入 `\citep{}` / `\citet{}` 引用
  - 自动插入 `\ref{}` 图表引用
  - 遵循学术风格约束（客观语气、无 LLM 废话）
- [ ] 章节写作质量门禁（自动化检查）
  - **Citation Coverage**: 每个段落至少 1 个 `\citep{}`（或显式标注"常识无需引用"）
  - **Figure/Table Coverage**: 实验章节必须至少引用 1 个 `\ref{}`
  - **Claim Traceability**: 随机抽样 N 条句子可追溯到 claim_id
- [ ] Git 自动提交
  - 每章节编译通过后: `git commit -m "auto: finish section X [cite: N papers]"`
  - 异常时可 `git reset` 到上一个稳定版本
- [ ] 增量编译验证
  - 生成 `draft_main.tex` 仅含当前章节 → 极速验证语法
  - 全部章节通过后再全量编译
- [ ] 上下文管理策略
  - Token 预算监控
  - 进度持久化至 `paper_state.json`
  - 会话中断恢复机制
- [ ] 撰写 Skill: `write-draft`
  - 输入：主题 + 大纲（可选）
  - 输出：paper/sections/*.tex 更新 + paper_state.json 更新

**涉及目录**:
```
paper/sections/                ← 章节 .tex 文件
src/vibewriting/agents/        ← 撰写智能体配置
src/vibewriting/contracts/     ← paper_state.json
.claude/skills/                ← write-draft Skill
```

**前置依赖**: Phase 2（asset_manifest.json）+ Phase 3（literature_cards.jsonl）
**Approval Gate**: Phase 2/3 完成后，用户 `/approve` 才进入撰写
**验证标准**:
- 给定主题 → 生成 ≥3 章节的 LaTeX 草稿
- `bash build.sh build` 编译通过
- 质量门禁全部通过（Citation/Figure/Claim Coverage）
- paper_state.json 通过 schema 校验

---

## Phase 5: 多 Agent 编排

**对应 origin.md**: 第三阶段后半（多智能体协同撰写）

**目标**: 引入多智能体编排，实现章节并行生成和角色分工，通过明确的合并协议确保一致性。

**交付物**:
- [ ] Orchestrator 编排智能体
  - 分析大纲，分配章节任务给角色 Agent
  - 管理 Agent 间依赖（如引言需等待方法论确定）
  - 执行合并协议（见下）
- [ ] 角色 Agent 设计
  - Storyteller: 叙事主线构建 + 长篇正文生成
  - Analyst: 数据解读 + 实验结果描述
  - Critic: 内部逻辑审查 + 论证强度评估
  - Formatter: LaTeX 格式规范 + 排版优化
- [ ] Sub-agents vs Agent Teams 选型
  - 原子任务（引用验证、公式检查）→ Sub-agents
  - 重度生成任务（章节撰写）→ Agent Teams（如可用）
- [ ] 合并协议（Merge Protocol）
  - **单一真源**: `paper_state.json` + `glossary.json` + `symbols.json`
  - **冲突分级**:
    - 术语/符号冲突 → 强制以 glossary/symbols 为准，回写各章
    - 引用键冲突 → 统一 references.bib，回写 cite key
    - 叙事冲突 → Storyteller 做最终裁决，但必须引用同一组证据卡
  - **章节隔离**: 每个 Agent 只允许编辑自己的 `paper/sections/X.tex`
  - **共享资源**: 只通过 state 文件修改（glossary, symbols, references）
- [ ] Git 安全网
  - 多 Agent 修改前自动创建 snapshot commit
  - 合并失败可 `git reset --hard` 到 snapshot
- [ ] 编排 Skill: `orchestrate-writing`

**涉及目录**:
```
src/vibewriting/agents/        ← Agent 角色配置
src/vibewriting/contracts/     ← paper_state/glossary/symbols JSON
.claude/skills/                ← orchestrate-writing Skill
paper/sections/                ← 并行产出的章节
```

**前置依赖**: Phase 4（单 Agent 验证 + 质量门禁通过）
**Approval Gate**: 用户确认单 Agent 草稿质量后 `/approve` 进入多 Agent
**验证标准**:
- 给定主题 → 多 Agent 并行 → 生成完整论文草稿
- 合并后无术语/符号/引用冲突
- 质量门禁全部通过
- paper_state.json 状态一致

---

## Phase 6: 编译 + 质量保证

**对应 origin.md**: 第四阶段（自动化编译与同行评审模拟）

**目标**: 自动化编译流程，加入有安全护栏的错误自修复和多维度质量检查。

**交付物**:
- [ ] 编译自修复循环（带安全护栏）
  - latexmk 编译 → 失败时解析 .log → 定位错误行 → 生成补丁 → 重试
  - **Patch Scope 限制**: 一次补丁只改动错误行附近 ±N 行，且只允许改 `paper/sections/*.tex`（不改 main.tex 模板）
  - **回滚机制**: 每次补丁前 `git stash`，修坏可回退
  - **错误分类路由**:
    - 缺包 → 提示安装（不自动修复）
    - 引用缺失 → 检查 references.bib + 证据卡
    - 语法错误 → 自动补丁
    - 图表找不到 → 检查 asset_manifest.json
    - 编码问题 → 提示手动检查
  - 最大重试次数限制（默认 5 次）
- [ ] 引文交叉验证
  - checkcites 基础检查（已有）
  - CrossRef / Semantic Scholar API 验证引文真实性
  - 与 literature_cards.jsonl 交叉比对，标记无证据卡支撑的引用为"可疑"
- [ ] 模拟同行评审
  - 结构审查：章节完整性、逻辑链条
  - 证据审查：每个 claim 是否有 claim_id 支撑
  - 方法论审查：实验设计合理性
  - 输出：结构化审查报告（Markdown + JSON）
- [ ] 排版质量检查（可选）
  - Claude 视觉模型检查 PDF 页面
  - 图表清晰度、跨页断行、公式对齐
- [ ] 双盲审查准备（可选）
  - 自动匿名化处理（去除作者信息）
- [ ] 审查 Skill: `review-paper`

**涉及目录**:
```
paper/build/                   ← 编译输出
scripts/                       ← 审查辅助脚本
.claude/skills/                ← review-paper Skill
src/vibewriting/contracts/     ← 契约一致性验证
```

**前置依赖**: Phase 5
**验证标准**:
- 完整论文源码 → 自动编译成功
- 自修复循环能处理常见错误（语法/引用缺失）且不越修越坏
- 审查报告无 Critical 级别问题
- 所有引用可追溯到证据卡

---

## Phase 7: 端到端集成

**目标**: 将所有阶段串联为一键式工作流，实现 "输入主题 → 输出 PDF" 的完整体验。

**交付物**:
- [ ] 一键启动工作流
  - Skill: `write-paper` — 主入口
  - 输入：论文主题 + 可选配置（模板、数据路径、文献范围）
  - 输出：paper/build/main.pdf + 审查报告
  - 内置 Approval Gates（每个阶段完成后等待用户确认）
- [ ] 进度持久化与恢复
  - 每阶段产出保存检查点（paper_state.json phase 字段）
  - 上下文重置后自动从检查点恢复
  - 跨会话状态文件验证（schema check on resume）
- [ ] 跨项目知识迁移
  - Additional Directories 配置指南
  - 从历史论文迁移 LaTeX 模式和排版知识
- [ ] 用户文档
  - 快速开始指南
  - 配置参考
  - 常见问题排查

**前置依赖**: Phase 6
**验证标准**: 全新主题 → 一键启动 → 经 Approval Gates 产出完整 PDF + 审查报告

---

## 风险与约束

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 上下文窗口耗尽 | 长论文生成中断 | 进度持久化 + 分章节生成 + MCP 按需加载 |
| 文献幻觉 | 虚假引用 | **Evidence-First 约束**: 只允许引用已入库证据卡; CrossRef 交叉验证 |
| LaTeX 编译错误 | 产出失败 | 自修复循环 + 错误分类路由 + git stash 回滚 |
| 自修复越修越坏 | 源码损坏 | Patch Scope 限制 + 回滚机制 + 最大重试次数 |
| Agent Teams 可用性 | 多 Agent 方案受限 | 降级为 Sub-agents 串行方案 |
| 多 Agent 合并冲突 | 章节不一致 | 合并协议 + 单一真源 JSON + 章节隔离 |
| Dify API 不稳定 | 知识库检索失败 | 优雅降级 + 本地证据卡缓存兜底 |
| 中文排版兼容性 | ctexart 特殊行为 | 固定 TeX Live 版本 + 测试矩阵 |
| 全量编译耗时 | 迭代慢/超时 | 增量编译策略（单章节 → 全量两阶段） |
| 数据资产漂移 | 图表不一致 | Golden Test + 随机种子 + 内容哈希验证 |

## 技术栈约束（不可变）

以下决策在 Phase 1 已确立，后续阶段必须遵循：

- LaTeX: XeLaTeX + ctexart + latexmk (`$pdf_mode=5`)
- 参考文献: BibTeX + natbib（非 biblatex）
- Python: 3.12+, uv, hatchling, src 布局
- 图表: matplotlib pgf 后端（非 tikzplotlib）
- MCP: paper-search（外部项目，stdio）+ dify-knowledge（本地桥接）
- 章节: `\input{}`（非 `\include{}`）
- CLAUDE.md: ≤300 行，渐进式披露
- Git: 自动提交使用 `auto:` 前缀，人工操作需 `/approve` 确认
