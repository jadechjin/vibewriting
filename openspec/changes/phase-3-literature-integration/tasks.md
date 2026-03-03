# Tasks: Phase 3 — 文献整合工作流

> 零决策实施计划 — 每个任务都是纯机械执行，无需判断

## P0: 项目配置更新（前置）

### T01: 更新 pyproject.toml 新增 bibtexparser
- [ ] `[project.dependencies]` 新增: `bibtexparser>=2.0`
- [ ] 运行 `uv sync`
- **验证**: `uv run python -c "import bibtexparser; print(bibtexparser.__version__)"`

### T02: 创建 literature 模块目录结构
- [ ] `src/vibewriting/literature/__init__.py`
- [ ] `src/vibewriting/literature/search.py`（空骨架）
- [ ] `src/vibewriting/literature/evidence.py`（空骨架）
- [ ] `src/vibewriting/literature/cache.py`（空骨架）
- [ ] `src/vibewriting/literature/bib_manager.py`（空骨架）
- [ ] `src/vibewriting/literature/dedup.py`（空骨架）
- [ ] `src/vibewriting/literature/models.py`（空骨架）
- **验证**: `uv run python -c "from vibewriting.literature import search, evidence, cache"`

### T03: 创建 EvidenceCard 模型（依赖 Phase 2 T04）
- [ ] `src/vibewriting/models/evidence_card.py`
- [ ] 字段: `claim_id: str`, `claim_text: str`, `supporting_quote: str`, `paraphrase: bool`, `bib_key: str`, `location: dict`, `evidence_type: Literal["empirical", "theoretical", "survey", "meta-analysis"]`, `key_statistics: str | None`, `methodology_notes: str`, `quality_score: int = Field(ge=1, le=10)`, `tags: list[str]`, `retrieval_source: Literal["paper-search", "dify-kb", "manual"]`, `retrieved_at: datetime`, `source_id: str`, `content_hash: str | None`
- [ ] `claim_id` 校验: `pattern=r'^EC-\d{4}-\d{3}$'`
- [ ] `supporting_quote` 校验: 自定义 validator 检查词数 ≤50
- [ ] 更新 `models/__init__.py` 导出
- **验证**: round-trip PBT 测试 + Schema 导出

### T04: 创建测试目录结构
- [ ] `tests/test_literature/__init__.py`
- [ ] `tests/test_literature/conftest.py`（MCP Mock fixtures）
- [ ] `tests/test_literature/test_search.py`（空骨架）
- [ ] `tests/test_literature/test_evidence.py`
- [ ] `tests/test_literature/test_cache.py`
- [ ] `tests/test_literature/test_bib_manager.py`
- [ ] `tests/test_literature/test_dedup.py`
- **验证**: `uv run pytest tests/test_literature/ --collect-only`

## P1: BibTeX 管理（优先，无外部依赖）

### T05: 实现 literature/bib_manager.py — 解析与规范化
- [ ] `parse_bib(path: Path) -> list[BibEntry]`: 使用 bibtexparser 2.x 解析
- [ ] `normalize_entry(entry: BibEntry) -> BibEntry`: 字段名小写、空白清理
- [ ] `normalize_cite_key(entry) -> str`: `authorYYYYkeyword` 规则 + 冲突后缀 a/b/c
- [ ] `BibEntry` dataclass: key, entry_type, fields dict
- **验证**: round-trip 测试 + idempotency 测试

### T06: 实现 bib_manager.py — doi2bib 批量获取
- [ ] `doi_to_bibtex(doi: str) -> str | None`: HTTP GET `https://doi.org/{doi}` with Accept: `application/x-bibtex`
- [ ] `batch_doi_to_bibtex(dois: list[str]) -> list[tuple[str, str | None]]`: 并发获取（限速 1 req/sec）
- [ ] 超时/404 处理: 返回 None + 警告日志
- **验证**: Mock HTTP 测试

### T07: 实现 bib_manager.py — 合并与写回
- [ ] `merge_bib(existing: list[BibEntry], new: list[BibEntry]) -> MergeReport`
- [ ] `MergeReport`: added, updated, conflicts 列表
- [ ] 人工条目优先（已存在不覆盖）
- [ ] 自动条目标记 `note = {auto-generated}`
- [ ] `write_bib(entries: list[BibEntry], path: Path)`: 按 key 排序 + 原子写入（.tmp → rename）
- **验证**: 合并逻辑单元测试 + 原子写入测试

### T08: 编写 tests/test_literature/test_bib_manager.py
- [ ] round-trip: parse → dump → parse 语义一致
- [ ] invariant: bib_key 唯一 + 必需字段非空
- [ ] idempotency: normalize 重复执行不变
- [ ] commutativity: 条目输入顺序不影响最终排序
- [ ] 边界: 空文件、特殊字符、非 ASCII 作者名
- **验证**: `uv run pytest tests/test_literature/test_bib_manager.py -v`

## P2: Evidence Card 生成

### T09: 实现 literature/evidence.py — claim_id 生成器
- [ ] `next_claim_id(existing_cards: list[EvidenceCard]) -> str`
- [ ] 格式: `EC-{year}-{NNN:03d}` 年度内单调递增
- [ ] 读取已有 JSONL 确定最大 NNN
- **验证**: monotonicity 测试

### T10: 实现 evidence.py — 证据卡工厂
- [ ] `create_evidence_card(raw_record: RawLiteratureRecord, claim_text: str, supporting_quote: str, **kwargs) -> EvidenceCard`
- [ ] 自动填充: claim_id（调用生成器）、retrieved_at（当前时间）、content_hash（sha256 of claim_text）
- [ ] supporting_quote 词数校验: >50 词自动设 `paraphrase=True`
- **验证**: Schema 校验 + 自愈测试

### T11: 实现 literature/models.py — RawLiteratureRecord
- [ ] `RawLiteratureRecord`: 统一的文献记录格式
- [ ] 字段: `title`, `authors`, `year`, `doi`, `arxiv_id`, `abstract`, `source: Literal["paper-search", "dify-kb"]`, `raw_data: dict`
- **验证**: 类型测试

### T12: 编写 tests/test_literature/test_evidence.py
- [ ] claim_id monotonicity 测试
- [ ] round-trip: JSONL 读写测试
- [ ] invariant: claim_id + bib_key 可追溯
- [ ] bounds: claim_id 格式校验
- [ ] supporting_quote ≤50 词校验
- **验证**: `uv run pytest tests/test_literature/test_evidence.py -v`

## P3: 本地知识缓存

### T13: 实现 literature/cache.py — LiteratureCache 类
- [ ] `__init__(jsonl_path: Path)`: 路径初始化
- [ ] `load() -> None`: 全量加载 JSONL → 内存索引（`_index`, `_bib_index`, `_tag_index`）
- [ ] 损坏行处理: 记录警告日志 + 跳过，不中断加载
- **验证**: invariant 测试（内存 == 重放）

### T14: 实现 cache.py — 写入与查询
- [ ] `upsert(card: EvidenceCard) -> None`: 追加 JSONL + 更新索引（claim_id 唯一约束）
- [ ] `query(*, claim_id=None, bib_key=None, tags=None, evidence_type=None) -> list[EvidenceCard]`
- [ ] `has(claim_id: str) -> bool`
- [ ] `get(claim_id: str) -> EvidenceCard | None`
- [ ] 原子写入: 追加模式 `'a'` + flush
- **验证**: idempotency 测试（重复 upsert 不重复）

### T15: 实现 cache.py — 漂移检测
- [ ] `detect_drift(card: EvidenceCard) -> bool`: 比较内存中同 claim_id 卡的 content_hash
- [ ] 如果 hash 不同，记录警告
- **验证**: 单元测试

### T16: 编写 tests/test_literature/test_cache.py
- [ ] invariant: 内存索引 == JSONL 全量重放
- [ ] idempotency: 重复 upsert 不产生重复
- [ ] bounds: 损坏行不阻断有效行
- [ ] 并发: 多次 upsert 后索引一致
- **验证**: `uv run pytest tests/test_literature/test_cache.py -v`

## P4: 检索去重

### T17: 实现 literature/dedup.py — L1 主键去重
- [ ] `dedup_by_primary_key(records: list[RawLiteratureRecord]) -> list[RawLiteratureRecord]`
- [ ] 优先级: DOI > arXiv > PMID > 规范化标题+年份
- [ ] 合并来源: 保留 retrieval_source 集合
- **验证**: 单元测试

### T18: 实现 dedup.py — L2 近似匹配
- [ ] `dedup_by_similarity(records, threshold=0.9) -> list[RawLiteratureRecord]`
- [ ] 标题归一化: lowercase + 去标点 + 去停用词
- [ ] Token Jaccard 计算
- [ ] 阈值通过 `VW_DEDUP_THRESHOLD` 可配置
- **验证**: 单元测试 + 阈值边界测试

### T19: 实现 dedup.py — L3 claim 级去重
- [ ] `dedup_claims(cards: list[EvidenceCard]) -> list[EvidenceCard]`
- [ ] 归一化 claim_text + content_hash 比对
- [ ] 同 bib_key 下保留 quality_score 最高的卡
- **验证**: 单元测试

### T20: 实现 dedup.py — 统一管道
- [ ] `deduplicate(records, threshold=0.9) -> DeduplicationReport`
- [ ] `DeduplicationReport`: input_count, l1_count, l2_count, l3_count, removed_records
- [ ] 断言: l3 <= l2 <= l1 <= input
- **验证**: monotonicity PBT 测试 + idempotency + commutativity

### T21: 编写 tests/test_literature/test_dedup.py
- [ ] monotonicity: 三层计数递减
- [ ] idempotency: 两次去重结果一致
- [ ] commutativity: 输入顺序不影响结果
- [ ] 边界: 空输入、单条、全重复
- **验证**: `uv run pytest tests/test_literature/test_dedup.py -v`

## P5: 文献检索编排

### T22: 实现 literature/search.py — paper-search MCP 集成
- [ ] `async search_via_paper_search(query: str, max_results: int, mode: str) -> list[RawLiteratureRecord]`
- [ ] interactive 模式: 调用 `search_papers` → 处理 checkpoint → `decide` → `export_results`
- [ ] headless 模式: 自动 decide(accept) 所有 checkpoint
- [ ] 返回 `RawLiteratureRecord` 列表 + BibTeX 字符串
- **验证**: Mock MCP 测试

### T23: 实现 search.py — Dify MCP 集成
- [ ] `async search_via_dify(query: str, top_k: int = 5) -> list[RawLiteratureRecord]`
- [ ] 调用 `retrieve_knowledge`
- [ ] 降级逻辑: 失败时返回空列表 + 警告日志
- **验证**: Mock MCP 测试（含降级场景）

### T24: 实现 search.py — 编排器
- [ ] `async search_literature(query: str, max_results: int = 20, mode: str = "headless") -> SearchResult`
- [ ] 流程: paper-search + Dify 并发 → 合并 → 去重 → 证据卡生成 → Schema 校验 → 缓存写入 → BibTeX 更新
- [ ] `SearchResult`: cards, bib_entries, dedup_report, errors
- **验证**: 端到端 Mock 测试

### T25: 创建 tests/test_literature/conftest.py — MCP Mock
- [ ] `mock_paper_search`: 模拟 search_papers/decide/export_results 响应
- [ ] `mock_dify_kb`: 模拟 retrieve_knowledge 响应
- [ ] `mock_dify_unavailable`: 模拟 Dify 超时/错误
- **验证**: fixtures 可被其他测试导入

### T26: 编写 tests/test_literature/test_search.py
- [ ] paper-search 正常流程测试
- [ ] Dify 正常流程测试
- [ ] Dify 降级测试
- [ ] 端到端编排测试
- [ ] bounds: 结果数量不超过 max_results
- **验证**: `uv run pytest tests/test_literature/test_search.py -v`

## P6: Skill 升级

### T27: 升级 search-literature Skill
- [ ] 更新 `.claude/skills/search-literature/SKILL.md`
- [ ] 集成完整工作流: 检索 → 去重 → 证据卡 → BibTeX
- [ ] 新增参数: max_results, evidence_type 过滤, mode
- **验证**: Skill 格式正确

## P7: 最终验证

### T28: 运行完整测试套件
- [ ] `uv run pytest tests/test_literature/ --cov=vibewriting.literature --cov-report=term-missing`
- [ ] 确认覆盖率 ≥80%
- **验证**: CI 通过

### T29: 端到端验证
- [ ] 使用 Mock 数据模拟完整工作流
- [ ] 检索 → 去重 → 证据卡(≥5) → BibTeX 更新 → JSONL 缓存
- [ ] 所有 Schema 校验通过
- [ ] 无重复 claim_id
- **验证**: 端到端测试通过

### T30: 更新 CLAUDE.md（如有必要）
- [ ] 新增文献工作流相关命令
- [ ] 更新目录映射
- **验证**: 文档与实际一致
