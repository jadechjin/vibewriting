# 路线图导读指南

## 文件位置

**`openspec/ROADMAP.md`** -- v4，617 行，项目总体路线图

## 何时阅读

- 需要了解项目整体规划和阶段划分时
- 开始新阶段开发前，查看该阶段的交付物清单和验证标准
- 需要理解跨阶段设计原则和契约体系时
- 评估风险和约束时

## 文档结构速查

| 章节 | 行数范围(约) | 内容 |
|------|-------------|------|
| 愿景摘要 | 开头 | 项目目标和四个核心工作流 |
| 阶段依赖图 | ~17-45 | Phase 1-7 的依赖关系和 Approval Gates |
| 跨阶段设计原则 | ~48-226 | 9 项设计原则的详细说明 |
| Phase 1 | ~229-241 | 基础架构（已完成） |
| Phase 2 | ~245-301 | 数据模型 + 处理管线 |
| Phase 3 | ~305-351 | 文献整合工作流 |
| Phase 4 | ~355-421 | 单 Agent 草稿撰写 |
| Phase 5 | ~425-478 | 多 Agent 编排 |
| Phase 6 | ~482-547 | 编译 + 质量保证 |
| Phase 7 | ~551-583 | 端到端集成 |
| 风险与约束 | ~586-607 | 17 项风险 + 缓解措施 |
| 技术栈约束 | ~609-623 | 不可变技术决策清单 |

## 关键概念速查

### 契约体系（6 个契约文件）

| 契约 | 说明 | 产出阶段 |
|------|------|---------|
| `paper_state.json` | 论文全局状态机 | Phase 4 |
| `literature_cards.jsonl` | 文献证据卡集合 | Phase 3 |
| `asset_manifest.json` | 数据资产清单 | Phase 2 |
| `run_manifest.json` | 运行环境锁定 | Phase 2 |
| `glossary.json` | 术语表 | Phase 4 初版 |
| `symbols.json` | 符号表 | Phase 4 初版 |

### 设计原则（9 项）

1. **阶段产物契约** -- JSON Schema 强校验 + 自愈循环 + 引用完整性
2. **证据优先工作流** -- Writer 只引用已入库的 Evidence Card
3. **Git 一等公民** -- auto commit / snapshot / stash
4. **人机协同审批门** -- AskUserQuestion 实现 Approval Gates
5. **LaTeX 增量编译** -- draft_main.tex(单章节) -> main.tex(全量)
6. **可观测性与指标** -- run_id + 8 维指标
7. **合规与 AI 披露** -- 引用摘抄限制 + AI 声明可开关
8. **源码溯源注释** -- `%% CLAIM_ID` 注释
9. **Prompt 缓存架构** -- 静态头部 + 动态尾部

### Approval Gates（4 个断点）

| 断点 | 触发条件 | 用户操作 |
|------|---------|---------|
| Phase 2 -> 4 | 图表 + asset_manifest 完成 | `/approve` 或调整资产 |
| Phase 3 -> 4 | 证据卡 + BibTeX 完成 | `/approve` 或补充文献 |
| Phase 4 -> 5 | 单 Agent 草稿 + 门禁通过 | `/approve` 或手动修订 |
| Phase 5 -> 6 | 多 Agent 合并完成 | `/approve` 或重写章节 |

## 与其他文档的关系

- `llmdoc/overview/architecture.md` -- 契约体系和设计原则概要（精简版）
- `llmdoc/overview/project-status.md` -- 当前进展和下一步行动
- `openspec/changes/archive/` -- Phase 1 的详细设计和任务归档
- `origin.md` -- 原始系统蓝图（ROADMAP 基于此扩展）
