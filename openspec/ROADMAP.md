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
   |        |
   |        +---> Phase 4: 单 Agent 草稿撰写 --------+
   |                                                   |
   +---> Phase 3: 文献整合工作流 ----+                 |
                                     |                 |
                                     +---> Phase 5: 多 Agent 编排
                                                       |
                                                       v
                                              Phase 6: 编译 + 质量保证
                                                       |
                                                       v
                                              Phase 7: 端到端集成
```

依赖关系说明：
- Phase 2 和 Phase 3 可并行开发（无相互依赖）
- Phase 4 依赖 Phase 2（数据模型）+ Phase 3（文献数据）
- Phase 5 依赖 Phase 4（单 Agent 验证后才能扩展到多 Agent）
- Phase 6 依赖 Phase 5（需要完整的 LaTeX 源码输出）
- Phase 7 依赖 Phase 6（全流程串联）

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

**目标**: 建立从原始数据到 LaTeX 可用资产（图表 + 表格）的自动化管线。

**交付物**:
- [ ] Pydantic 数据模型（`src/vibewriting/models/`）
  - Paper: 论文元数据（标题、作者、摘要、引用键、质量评分）
  - Experiment: 实验配置 + 结果
  - Figure / Table: 图表/表格元数据 + 生成参数
  - Section: 章节结构（大纲、状态、引用列表）
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
- [ ] 输出确定性验证：相同输入 → 相同输出

**涉及目录**:
```
src/vibewriting/models/      ← Pydantic 模型
src/vibewriting/processing/  ← 数据清洗 + 统计
src/vibewriting/visualization/ ← 图表 + 表格生成
data/raw/                    ← 原始数据输入
data/processed/              ← 清洗后数据
output/figures/              ← 生成的图表 (.pdf/.pgf/.png)
output/tables/               ← 生成的 LaTeX 表格 (.tex)
```

**前置依赖**: Phase 1 ✅
**验证标准**: `uv run pytest` 全部通过，示例数据端到端生成图表 + 表格

---

## Phase 3: 文献整合工作流

**对应 origin.md**: 第一阶段（智能化文献检索与结构化特征提取）

**目标**: 建立从文献检索到结构化知识缓存的完整工作流，为撰写阶段提供有据可依的素材库。

**交付物**:
- [ ] 文献检索端到端工作流
  - paper-search MCP: 主题 → 搜索 → 筛选 → 导出 BibTeX
  - Dify MCP: 知识库语义检索 → 片段提取
  - 检索结果自动去重与合并
- [ ] 结构化特征提取
  - Analyst 子智能体提示词设计（独立上下文，受限工具）
  - 每篇文献提取：核心声明（≤120 词）、方法论评估、质量评分（1-10）
  - 输出格式：结构化 Markdown / JSON
- [ ] 本地知识缓存
  - 文献分析报告存储（`data/processed/literature/`）
  - 可跨会话搜索的索引
- [ ] BibTeX 自动管理
  - doi2bib 批量获取
  - 引用键去重与规范化
  - references.bib 自动更新
- [ ] 增强 Skill: `search-literature` 升级为完整工作流

**涉及目录**:
```
data/processed/literature/   ← 文献分析缓存
paper/bib/references.bib     ← BibTeX 数据库
.claude/skills/              ← Skill 升级
src/vibewriting/agents/      ← Analyst 子智能体配置
```

**前置依赖**: Phase 1 ✅
**验证标准**: 给定主题 → 自动检索 → 产出 ≥5 篇结构化文献分析 + 更新 BibTeX

---

## Phase 4: 单 Agent 草稿撰写

**对应 origin.md**: 第三阶段前半（单一上下文撰写验证）

**目标**: 验证单个 Claude Code 会话能否利用文献素材和数据资产，生成符合学术规范的 LaTeX 草稿。

**交付物**:
- [ ] 论文大纲生成
  - 基于主题 + 文献分析 → 生成章节大纲
  - 每章节：标题、要点、预期引用、预期图表
- [ ] 逐章节草稿撰写
  - 按大纲逐章生成 LaTeX 源码
  - 自动插入 `\citep{}` / `\citet{}` 引用
  - 自动插入 `\ref{}` 图表引用
  - 遵循学术风格约束（客观语气、无 LLM 废话）
- [ ] 上下文管理策略
  - Token 预算监控
  - 进度持久化（写入本地文件后继续）
  - 会话中断恢复机制
- [ ] 撰写 Skill: `write-draft`
  - 输入：主题 + 大纲（可选）
  - 输出：paper/sections/*.tex 更新

**涉及目录**:
```
paper/sections/              ← 章节 .tex 文件
src/vibewriting/agents/      ← 撰写智能体配置
.claude/skills/              ← write-draft Skill
```

**前置依赖**: Phase 2 + Phase 3
**验证标准**: 给定主题 → 生成 ≥3 章节的 LaTeX 草稿 → `bash build.sh build` 编译通过

---

## Phase 5: 多 Agent 编排

**对应 origin.md**: 第三阶段后半（多智能体协同撰写）

**目标**: 引入多智能体编排，实现章节并行生成和角色分工，提升生成质量和效率。

**交付物**:
- [ ] Orchestrator 编排智能体
  - 分析大纲，分配章节任务给角色 Agent
  - 管理 Agent 间依赖（如引言需等待方法论确定）
  - 合并产出，消解跨章节冲突
- [ ] 角色 Agent 设计
  - Storyteller: 叙事主线构建 + 长篇正文生成
  - Analyst: 数据解读 + 实验结果描述
  - Critic: 内部逻辑审查 + 论证强度评估
  - Formatter: LaTeX 格式规范 + 排版优化
- [ ] Sub-agents vs Agent Teams 选型
  - 原子任务（引用验证、公式检查）→ Sub-agents
  - 重度生成任务（章节撰写）→ Agent Teams（如可用）
- [ ] 跨章节一致性
  - 术语表统一
  - 符号表一致
  - 叙事风格校准
- [ ] 编排 Skill: `orchestrate-writing`

**涉及目录**:
```
src/vibewriting/agents/      ← Agent 角色配置
.claude/skills/              ← orchestrate-writing Skill
paper/sections/              ← 并行产出的章节
```

**前置依赖**: Phase 4（单 Agent 验证通过）
**验证标准**: 给定主题 → 多 Agent 并行 → 生成完整论文草稿 → 风格一致性检查通过

---

## Phase 6: 编译 + 质量保证

**对应 origin.md**: 第四阶段（自动化编译与同行评审模拟）

**目标**: 自动化编译流程，加入错误自修复和多维度质量检查。

**交付物**:
- [ ] 编译自修复循环
  - latexmk 编译 → 失败时解析 .log → 定位错误行 → 生成补丁 → 重试
  - 最大重试次数限制，防止无限循环
- [ ] 引文交叉验证
  - checkcites 基础检查（已有）
  - CrossRef / Semantic Scholar API 验证引文真实性
  - 标记可能的幻觉引用
- [ ] 模拟同行评审
  - 结构审查：章节完整性、逻辑链条
  - 证据审查：每个 claim 是否有引用/数据支撑
  - 方法论审查：实验设计合理性
  - 输出：结构化审查报告（Markdown）
- [ ] 排版质量检查（可选）
  - Claude 视觉模型检查 PDF 页面
  - 图表清晰度、跨页断行、公式对齐
- [ ] 双盲审查准备（可选）
  - 自动匿名化处理（去除作者信息）
- [ ] 审查 Skill: `review-paper`

**涉及目录**:
```
paper/build/                 ← 编译输出
scripts/                     ← 审查辅助脚本
.claude/skills/              ← review-paper Skill
```

**前置依赖**: Phase 5
**验证标准**: 完整论文源码 → 自动编译成功 → 审查报告无 Critical 级别问题

---

## Phase 7: 端到端集成

**目标**: 将所有阶段串联为一键式工作流，实现 "输入主题 → 输出 PDF" 的完整体验。

**交付物**:
- [ ] 一键启动工作流
  - Skill: `write-paper` — 主入口
  - 输入：论文主题 + 可选配置（模板、数据路径、文献范围）
  - 输出：paper/build/main.pdf + 审查报告
- [ ] 进度持久化与恢复
  - 每阶段产出保存检查点
  - 上下文重置后自动从检查点恢复
  - 跨会话状态文件（JSON）
- [ ] 跨项目知识迁移
  - Additional Directories 配置指南
  - 从历史论文迁移 LaTeX 模式和排版知识
- [ ] 用户文档
  - 快速开始指南
  - 配置参考
  - 常见问题排查

**前置依赖**: Phase 6
**验证标准**: 全新主题 → 一键启动 → 无人干预产出完整 PDF（允许交互式检查点）

---

## 风险与约束

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 上下文窗口耗尽 | 长论文生成中断 | 进度持久化 + 分章节生成 + MCP 按需加载 |
| 文献幻觉 | 虚假引用 | CrossRef 交叉验证 + Analyst 子智能体质量评分 |
| LaTeX 编译错误 | 产出失败 | 自修复循环 + .log 解析 |
| Agent Teams 可用性 | 多 Agent 方案受限 | 降级为 Sub-agents 串行方案 |
| Dify API 不稳定 | 知识库检索失败 | 优雅降级 + 本地缓存兜底 |
| 中文排版兼容性 | ctexart 特殊行为 | 固定 TeX Live 版本 + 测试矩阵 |

## 技术栈约束（不可变）

以下决策在 Phase 1 已确立，后续阶段必须遵循：

- LaTeX: XeLaTeX + ctexart + latexmk (`$pdf_mode=5`)
- 参考文献: BibTeX + natbib（非 biblatex）
- Python: 3.12+, uv, hatchling, src 布局
- 图表: matplotlib pgf 后端（非 tikzplotlib）
- MCP: paper-search（外部项目，stdio）+ dify-knowledge（本地桥接）
- 章节: `\input{}`（非 `\include{}`）
- CLAUDE.md: ≤300 行，渐进式披露
