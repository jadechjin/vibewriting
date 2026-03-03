# Design: Phase 3 — 文献整合工作流

## 技术决策

### D1: BibTeX 解析库 — bibtexparser 2.x

**决策**: 使用 bibtexparser >=2.0 进行 BibTeX 解析与写入。

**理由**: 纯 Python，活跃维护，Pydantic 友好。相比 pybtex 更轻量，API 更直观。

**新增依赖**: `bibtexparser>=2.0` 加入 `pyproject.toml`

### D2: Evidence Card 存储 — 纯文件方案

**决策**: JSONL 文件 + 内存字典索引，不使用 SQLite。

**理由**: 用户选择简单方案。当前文献规模（数百篇）内存索引足够。

**实现**:
```python
# literature/cache.py
class LiteratureCache:
    def __init__(self, jsonl_path: Path):
        self._path = jsonl_path
        self._index: dict[str, EvidenceCard] = {}  # claim_id → card
        self._bib_index: dict[str, list[str]] = {}  # bib_key → [claim_id, ...]
        self._tag_index: dict[str, list[str]] = {}  # tag → [claim_id, ...]

    def load(self) -> None:
        """全量加载 JSONL 到内存索引"""

    def upsert(self, card: EvidenceCard) -> None:
        """追加写入 JSONL + 更新内存索引"""

    def query(self, *, claim_id=None, bib_key=None, tags=None, evidence_type=None) -> list[EvidenceCard]:
        """按条件检索"""
```

### D3: 去重策略 — 三层管道

**决策**: 主键 → 近似 → claim 级，按序执行。

**层级参数**:
- L1 主键: DOI 精确匹配 > arXiv ID > PMID > 标题+年份规范化
- L2 近似: 标题归一化（lowercase + 去标点 + 去停用词）后 Token Jaccard >= 0.9
- L3 claim: `normalize(claim_text)` + content_hash，同 bib_key 下保留 quality_score 最高的卡

**可配置**: 近似阈值通过 `VW_DEDUP_THRESHOLD` 环境变量设置，默认 0.9

### D4: MCP 编排模式

**决策**: 异步编排器统一管理 paper-search 和 Dify MCP 调用。

**编排流程**:
```
1. search_papers(query) → session_id
2. [interactive] 处理 checkpoint → decide(session_id, action)
3. export_results(session_id, "json") → raw_results
4. export_results(session_id, "bibtex") → bibtex_entries
5. [parallel] retrieve_knowledge(query) → dify_results  (Dify 可选)
6. 统一映射 → RawLiteratureRecord[]
7. 三层去重
8. 证据卡生成 + Schema 校验/自愈
9. 写入 JSONL 缓存
10. BibTeX merge → references.bib 更新
```

**降级策略**: Dify 调用失败时，记录警告日志，仅使用 paper-search 结果继续。

### D5: BibTeX 管理策略

**决策**: 规范化写回 + 原子写入 + 合并报告。

**cite key 规范化规则**:
1. 取第一作者姓氏 → ASCII transliterate
2. 拼接年份 4 位
3. 拼接标题首个关键词（去停用词）
4. 冲突时追加后缀: a, b, c...
5. 示例: `vaswani2017attention`, `devlin2019bert`

**写回格式**:
- 按 bib_key 字母升序排列
- 字段名小写
- 缩进 2 空格
- 原子写入: 先写 `.bib.tmp` → rename 覆盖

**合并逻辑**:
- 人工条目优先（已存在的条目不被自动覆盖）
- 自动条目标记 `note = {auto-generated}`
- 产出合并报告: `{added: [], updated: [], conflicts: []}`

### D6: claim_id 生成规则

**决策**: `EC-{year}-{NNN}` 格式，年度内单调递增。

**实现**:
```python
def next_claim_id(existing_cards: list[EvidenceCard]) -> str:
    year = datetime.now().year
    existing_nums = [
        int(c.claim_id.split('-')[2])
        for c in existing_cards
        if c.claim_id.startswith(f"EC-{year}-")
    ]
    next_num = max(existing_nums, default=0) + 1
    return f"EC-{year}-{next_num:03d}"
```

**约束**: `^EC-\d{4}-\d{3}$` 正则严格校验。

### D7: Evidence Card 与 Phase 2 共享点

**共享 Schema**: `evidence_card.schema.json` 由 Phase 2 的 Pydantic 模型自动生成。Phase 3 消费该 Schema 做校验。

**协调方案**: EvidenceCard 模型定义在 `src/vibewriting/models/evidence_card.py`（Phase 2 创建），Phase 3 导入使用。

## 目录结构

```
src/vibewriting/
  models/
    evidence_card.py     ← EvidenceCard Pydantic 模型（Phase 2 创建，Phase 3 使用）
  literature/
    __init__.py
    search.py            ← 文献检索编排器（async）
    evidence.py          ← Evidence Card 生成 + claim_id 管理
    cache.py             ← 本地知识缓存（JSONL + 内存索引）
    bib_manager.py       ← BibTeX 管理（bibtexparser 2.x）
    dedup.py             ← 三层去重
    models.py            ← RawLiteratureRecord 等内部模型
data/
  processed/
    literature/
      literature_cards.jsonl  ← 证据卡主存储
paper/
  bib/
    references.bib            ← BibTeX 数据库
.claude/
  skills/
    search-literature/
      SKILL.md                ← 升级后的完整工作流
tests/
  test_literature/
    test_search.py
    test_evidence.py
    test_cache.py
    test_bib_manager.py
    test_dedup.py
    conftest.py              ← MCP Mock fixtures
```
