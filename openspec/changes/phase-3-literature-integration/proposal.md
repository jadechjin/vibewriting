# Proposal: Phase 3 — 文献整合工作流

## Context

### 用户需求

为 vibewriting 科研论文自动化写作系统建立从文献检索到结构化证据卡的完整工作流，为撰写阶段提供强约束的有据可依素材库。

### 当前状态

- **Phase 1 已完成**: MCP 集成（paper-search + dify-knowledge）、3 个 Skills（search-literature, retrieve-kb, validate-citations）
- **已有**: `.mcp.json` 配置、`scripts/dify-kb-mcp/server.py`（204 行 FastMCP 桥接）
- **缺失**: Evidence Card 系统、本地知识缓存、BibTeX 自动管理、端到端工作流

### 发现的约束（多模型交叉验证）

#### 硬约束

| ID | 约束 | 影响 |
|----|------|------|
| H1 | bibtexparser >=2.0 用于 BibTeX 解析 | 新增依赖 |
| H2 | Evidence Card JSON Schema 与 Phase 2 共享（Pydantic 自动生成） | 模型定义在 Phase 2 |
| H3 | claim_id 格式: `EC-YYYY-NNN`（年度内单调递增） | 全局唯一标识 |
| H4 | supporting_quote ≤50 词，超出标记 `paraphrase: true` | 合规约束 |
| H5 | bib_key 格式: 仅 ASCII (`authorYYYYkeyword`) | UTF-8 兼容 |
| H6 | 证据卡索引: 纯文件 JSONL + 内存索引（无 SQLite） | 用户决策 |
| H7 | 自愈策略与 Phase 2 共享（规则优先 + LLM 兜底，max 3 轮） | 一致性 |
| H8 | 异步混合模式: MCP 调用用 async，本地处理用同步 | 用户决策 |
| H9 | 三层去重: 主键（DOI）→ 近似（标题）→ claim 级 | Codex 设计 |

#### 软约束

| ID | 约束 | 来源 |
|----|------|------|
| S1 | paper-search 有 checkpoint 机制，需支持 interactive + headless 模式 | Codex 分析 |
| S2 | Dify 不可用时优雅降级，仅保留 paper-search 结果 | 已有设计 |
| S3 | BibTeX 写回保持稳定排序和原子写入 | Codex 推荐 |
| S4 | 去重阈值需可配置 | 避免误删 |

## Requirements

### R1: 文献检索端到端工作流

**交付物**: `src/vibewriting/literature/search.py`

- paper-search MCP: 主题 → `search_papers` → 处理 checkpoints → `export_results(json+bibtex)`
- Dify MCP: `retrieve_knowledge` → 片段提取
- 统一映射为 `RawLiteratureRecord`
- 两种模式: interactive（人审 checkpoint）/ headless（自动 decide）
- Dify 不可用时优雅降级

**PBT 不变量**:
- [CRITICAL] bounds: 0 <= 返回结果数 <= max_results，重试次数 <= 配置上限
- [CRITICAL] idempotency: 固定后端快照下相同 query → 相同主键集合
- [HIGH] monotonicity: 查询放宽 → 命中集合单调不减

### R2: Evidence Card 系统

**交付物**: `src/vibewriting/literature/evidence.py`

- `EvidenceCard` Pydantic 模型（字段见路线图 §2）
- claim_id 生成器: `EC-{year}-{NNN}` 年度单调递增
- supporting_quote 校验: ≤50 词限制 + paraphrase 标记
- 产出 `literature_cards.jsonl`（符合 evidence_card.schema.json + 自愈校验）

**PBT 不变量**:
- [CRITICAL] invariant: 每张卡的 claim_id + bib_key 可追溯到有效 claim 与 BibTeX 条目
- [HIGH] round_trip: JSONL 读写往返后语义等价
- [HIGH] commutativity: 多来源合并满足交换律

### R3: 本地知识缓存

**交付物**: `src/vibewriting/literature/cache.py`

- JSONL 存储: `data/processed/literature/literature_cards.jsonl`
- 内存索引: 按 `claim_id`、`bib_key`、`tags`、`evidence_type` 检索
- 追加写入 + 原子 rename
- claim_id 唯一约束
- content_hash 漂移检测

**PBT 不变量**:
- [CRITICAL] invariant: 内存索引 == JSONL 全量重放
- [HIGH] idempotency: 相同记录重复 upsert 不产生重复条目
- [MEDIUM] bounds: 损坏行不阻断有效行加载

### R4: BibTeX 自动管理

**交付物**: `src/vibewriting/literature/bib_manager.py`

- bibtexparser 2.x 解析 + 规范化
- doi2bib 批量获取（HTTP Accept: `application/x-bibtex`）
- cite key 规范化: ASCII + `authorYYYYkeyword` + 冲突后缀 a/b/c
- 合并策略: 人工条目优先，自动条目标记来源
- 写回: 稳定排序（按 bib_key 字母序）+ 原子写入（tmp → replace）
- 合并报告: 新增/更新/冲突

**PBT 不变量**:
- [CRITICAL] round_trip: parse → dump → parse 语义一致
- [CRITICAL] invariant: bib_key 全局唯一 + 必需字段（title/author/year）非空
- [HIGH] idempotency: 规范化重复执行结果不变

### R5: 检索去重

**交付物**: `src/vibewriting/literature/dedup.py`

三层去重:
1. **主键去重**: DOI > arXiv > PMID > 规范化标题+年份
2. **近似匹配**: 标题归一化后编辑距离 / Token Jaccard（阈值可配，默认 0.9）
3. **claim 级去重**: `normalize(claim_text)` + `content_hash`，同 bib_key 下保留高质量卡

合并时保留来源集合 `retrieval_source[]`。

**PBT 不变量**:
- [CRITICAL] monotonicity: `|L3| <= |L2| <= |L1| <= |Input|`
- [CRITICAL] idempotency: `dedup(dedup(x)) == dedup(x)`
- [HIGH] commutativity: 固定阈值下去重不依赖输入顺序

### R6: 增强 Skill

**交付物**: `.claude/skills/search-literature/SKILL.md` 升级

- 集成完整检索 → 去重 → 证据卡 → BibTeX 管理工作流
- 支持参数: 主题、max_results、evidence_type 过滤

## Success Criteria

| ID | 判据 | 验证方式 |
|----|------|---------|
| SC1 | 给定主题 → 自动检索 → 产出 ≥5 篇结构化证据卡 | 端到端测试 |
| SC2 | 每张证据卡通过 JSON Schema 校验 | `validate_contract()` |
| SC3 | `literature_cards.jsonl` 中无重复 claim_id | 唯一性测试 |
| SC4 | 每张卡有 retrieval_source + retrieved_at + source_id + evidence_type | Schema 校验 |
| SC5 | BibTeX parse → dump → parse 语义一致 | round-trip 测试 |
| SC6 | 去重三层单调递减 | PBT 测试 |
| SC7 | 测试覆盖率 ≥80% | pytest-cov |
| SC8 | Dify 不可用时优雅降级（不崩溃） | Mock 测试 |
