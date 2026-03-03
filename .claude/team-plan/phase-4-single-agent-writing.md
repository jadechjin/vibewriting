# Team Plan: Phase 4 — 单 Agent 草稿撰写

> **生成时间**: 2026-02-24
> **前置依赖**: Phase 2 ✅ + Phase 3 ✅（177 tests, 92% 覆盖率）
> **目标**: 建立从证据卡和数据资产到 LaTeX 草稿的完整撰写基础设施

---

## 摘要

Phase 4 引入 `src/vibewriting/writing/` 模块，提供：
1. 论文全局状态管理（paper_state.json）
2. 术语表 + 符号表（glossary.json / symbols.json）
3. 大纲生成工具
4. 5 种质量门禁检查
5. LaTeX 辅助工具（CLAIM_ID 注释、增量编译）
6. write-draft Skill（Claude Code 撰写工作流入口）

**Builder 数量**: 7 个（Sonnet）
**并行分组**: Layer 1 (3 并行) → Layer 2 (3 并行) → Layer 3 (1)

---

## 子任务列表

### Layer 1: 基础模型与框架（3 个 Builder 并行）

#### Builder 1: PaperState 数据模型

**文件范围**:
- `src/vibewriting/models/paper_state.py` (新建)
- `tests/test_paper_state.py` (新建)

**实施步骤**:

1. 创建 `src/vibewriting/models/paper_state.py`，定义以下模型：

```python
# SectionState: 扩展章节在写作阶段的状态
class SectionState(BaseModel):
    section_id: str
    title: str
    outline: list[str]  # 要点列表
    status: Literal["planned", "drafting", "drafted", "reviewed", "complete"]
    claim_ids: list[str]  # EC-YYYY-NNN 格式
    asset_ids: list[str]  # ASSET-YYYY-NNN 格式
    citation_keys: list[str]  # BibTeX key
    tex_file: str  # 相对路径，如 "sections/introduction.tex"
    word_count: int = 0
    paragraph_count: int = 0
    no_cite_exemptions: list[str]  # %% NO_CITE 豁免的段落描述

# PaperMetrics: 质量指标
class PaperMetrics(BaseModel):
    citation_coverage: float = 0.0  # 含 \citep 的段落比例
    claim_traceability: float = 0.0  # 可追溯 claim 比例
    figure_coverage: float = 0.0  # 含 \ref{fig:} 的实验段落比例
    cross_ref_integrity: bool = False  # 无悬空引用
    terminology_consistency: bool = False  # 术语一致
    total_claims: int = 0
    total_citations: int = 0
    total_figures_referenced: int = 0
    total_tables_referenced: int = 0

# PaperState: 论文全局状态机
class PaperState(BaseModel):
    paper_id: str  # 如 "PS-2026-001"
    title: str
    topic: str
    phase: Literal["outline", "drafting", "review", "complete"]
    abstract: str = ""
    sections: list[SectionState]
    metrics: PaperMetrics = PaperMetrics()
    created_at: datetime
    updated_at: datetime
    current_section_index: int = 0  # 当前正在撰写的章节
    run_id: str = ""  # 关联 run_manifest
```

2. 确保与 `contracts/integrity.py` 的 `validate_referential_integrity` 兼容：
   - `paper_state.get("sections", [])` 应返回包含 `section_id`, `claim_ids`, `asset_ids`, `citation_keys` 的 dict 列表
   - PaperState.model_dump() 的结构需匹配 integrity.py 的解析逻辑

3. 创建 `tests/test_paper_state.py`，测试：
   - PaperState 创建与序列化（model_dump / model_dump_json）
   - SectionState 状态流转（planned → drafting → drafted → reviewed → complete）
   - PaperMetrics 默认值和更新
   - 与 integrity.py 的兼容性（构造 paper_state dict → validate_referential_integrity）
   - 边界情况：空 sections、无效 phase、重复 section_id 等

**验收标准**:
- `uv run pytest tests/test_paper_state.py -v` 全部通过
- PaperState.model_dump() 输出可直接传给 `validate_referential_integrity()`

---

#### Builder 2: Glossary + Symbols 数据模型

**文件范围**:
- `src/vibewriting/models/glossary.py` (新建)
- `tests/test_glossary_symbols.py` (新建)

**实施步骤**:

1. 创建 `src/vibewriting/models/glossary.py`，定义以下模型：

```python
class GlossaryEntry(BaseModel):
    term: str  # 术语（如 "Transformer"）
    definition: str  # 定义
    first_used_in: str = ""  # 首次使用的 section_id
    aliases: list[str] = []  # 别名

class SymbolEntry(BaseModel):
    symbol: str  # LaTeX 符号（如 r"\alpha"）
    meaning: str  # 含义（如 "学习率"）
    first_used_in: str = ""
    latex_command: str = ""  # 完整 LaTeX 命令

class Glossary(BaseModel):
    entries: dict[str, GlossaryEntry]  # term -> GlossaryEntry
    updated_at: datetime

class SymbolTable(BaseModel):
    entries: dict[str, SymbolEntry]  # symbol -> SymbolEntry
    updated_at: datetime
```

2. 提供辅助方法：
   - `Glossary.add_term(term, definition, section_id)` → 不可变，返回新 Glossary
   - `Glossary.has_term(term) -> bool`
   - `Glossary.lookup(term) -> GlossaryEntry | None`
   - `SymbolTable.add_symbol(symbol, meaning, section_id)` → 不可变，返回新 SymbolTable
   - `SymbolTable.has_symbol(symbol) -> bool`
   - `SymbolTable.check_consistency(sections_text: dict[str, str]) -> list[str]` — 检查同名符号是否在不同章节有不同含义

3. 创建 `tests/test_glossary_symbols.py`，测试：
   - GlossaryEntry / SymbolEntry 创建和序列化
   - Glossary / SymbolTable 不可变操作
   - add_term / add_symbol 返回新实例
   - has_term / has_symbol / lookup
   - check_consistency 检测冲突
   - 边界情况：空表、重复条目、aliases 查找

**验收标准**:
- `uv run pytest tests/test_glossary_symbols.py -v` 全部通过
- 不可变模式：所有修改操作返回新实例

---

#### Builder 3: Writing 模块初始化 + Quality Gates

**文件范围**:
- `src/vibewriting/writing/__init__.py` (新建)
- `src/vibewriting/writing/quality_gates.py` (新建)
- `tests/test_writing/__init__.py` (新建)
- `tests/test_writing/test_quality_gates.py` (新建)

**实施步骤**:

1. 创建 `src/vibewriting/writing/__init__.py`（空模块初始化）

2. 创建 `src/vibewriting/writing/quality_gates.py`，实现 5 种质量门禁：

```python
@dataclass
class GateResult:
    gate_name: str
    passed: bool
    score: float  # 0.0 - 1.0
    details: list[str]  # 具体问题描述
    section_id: str = ""

@dataclass
class GateReport:
    results: list[GateResult]
    all_passed: bool
    summary: str

# 门禁 1: Citation Coverage（按段落类型分策略）
def check_citation_coverage(
    tex_content: str,
    section_id: str,
    section_type: Literal["introduction", "related-work", "method", "experiments", "conclusion", "appendix"],
) -> GateResult:
    """解析 .tex 内容，统计含 \\citep/\\citet 的段落比例。

    策略:
    - introduction/related-work: recommend（建议引用，score = 比例）
    - method/experiments: require（必须引用或 \\ref，score < 0.5 则 fail）
    - conclusion/appendix: 不强制检查
    - %% NO_CITE: common knowledge 标记的段落豁免
    """

# 门禁 2: Figure/Table Coverage
def check_asset_coverage(
    tex_content: str,
    section_id: str,
    section_type: str,
    expected_asset_ids: list[str],
) -> GateResult:
    """检查实验章节是否引用了预期的图表。

    - 解析 \\ref{fig:*} 和 \\ref{tab:*}
    - experiments 章节必须至少 1 个 \\ref
    """

# 门禁 3: Claim Traceability
def check_claim_traceability(
    tex_content: str,
    section_id: str,
    expected_claim_ids: list[str],
) -> GateResult:
    """检查 %% CLAIM_ID: EC-XXXX-XXX 注释覆盖率。

    - 解析所有 %% CLAIM_ID 注释
    - 与 expected_claim_ids 对比
    - score = 已标注 / 预期总数
    """

# 门禁 4: Cross-ref Integrity
def check_cross_references(
    tex_content: str,
    section_id: str,
    all_labels: set[str],
) -> GateResult:
    """检查 LaTeX 交叉引用完整性。

    - 解析 \\label{} 和 \\ref{} / \\eqref{}
    - 检测未引用的 label 和引用不存在的 label
    """

# 门禁 5: Terminology Consistency
def check_terminology_consistency(
    tex_content: str,
    section_id: str,
    glossary_terms: dict[str, str],
    symbol_entries: dict[str, str],
) -> GateResult:
    """检查术语和符号使用一致性。

    - 术语: 检查是否使用了 glossary 中未定义的关键术语
    - 符号: 检查同一符号在不同位置是否含义一致
    """

# 综合门禁
def run_all_gates(
    tex_content: str,
    section_id: str,
    section_type: str,
    expected_claim_ids: list[str],
    expected_asset_ids: list[str],
    all_labels: set[str],
    glossary_terms: dict[str, str],
    symbol_entries: dict[str, str],
) -> GateReport:
    """运行所有质量门禁，返回综合报告。"""
```

3. 辅助函数（内部使用）:
   - `_parse_paragraphs(tex_content) -> list[str]` — 按空行分割段落
   - `_extract_citations(tex_content) -> list[str]` — 提取 \citep{} 和 \citet{} 中的 key
   - `_extract_refs(tex_content) -> list[str]` — 提取 \ref{} 中的 label
   - `_extract_labels(tex_content) -> list[str]` — 提取 \label{} 定义
   - `_extract_claim_annotations(tex_content) -> list[str]` — 提取 %% CLAIM_ID: 注释
   - `_is_no_cite_exempt(paragraph) -> bool` — 检查 %% NO_CITE 豁免

4. 创建 `tests/test_writing/__init__.py`（空文件）

5. 创建 `tests/test_writing/test_quality_gates.py`，测试：
   - 各辅助解析函数（_parse_paragraphs, _extract_citations 等）
   - 各门禁独立测试（正常通过、不通过、边界情况）
   - run_all_gates 综合测试
   - NO_CITE 豁免机制
   - 不同 section_type 的策略差异

**验收标准**:
- `uv run pytest tests/test_writing/test_quality_gates.py -v` 全部通过
- 所有 LaTeX 解析使用正则表达式，不依赖外部 LaTeX 解析库
- GateResult / GateReport 数据结构清晰，可序列化

---

### Layer 2: 工具模块（依赖 Layer 1，3 个 Builder 并行）

#### Builder 4: State Manager + Outline 生成

**文件范围**:
- `src/vibewriting/writing/state_manager.py` (新建)
- `src/vibewriting/writing/outline.py` (新建)
- `tests/test_writing/test_state_manager.py` (新建)
- `tests/test_writing/test_outline.py` (新建)

**依赖**: Builder 1 (PaperState 模型)

**实施步骤**:

1. 创建 `src/vibewriting/writing/state_manager.py`：

```python
class PaperStateManager:
    """paper_state.json 状态管理器（不可变模式）。

    所有修改操作返回新的 PaperState 实例。
    持久化使用原子写入（先写 .tmp 再 rename）。
    """

    def __init__(self, state_path: Path):
        self._path = state_path

    def load(self) -> PaperState | None:
        """从 JSON 文件加载 PaperState。"""

    def save(self, state: PaperState) -> None:
        """原子写入 PaperState 到 JSON 文件。"""

    def create(self, paper_id: str, title: str, topic: str, sections: list[dict]) -> PaperState:
        """创建新的 PaperState（outline 阶段）。"""

    def update_section_status(self, state: PaperState, section_id: str, new_status: str) -> PaperState:
        """更新章节状态（不可变）。"""

    def update_metrics(self, state: PaperState, metrics: PaperMetrics) -> PaperState:
        """更新质量指标（不可变）。"""

    def advance_phase(self, state: PaperState) -> PaperState:
        """推进论文阶段（outline → drafting → review → complete）。"""

    def add_claim_to_section(self, state: PaperState, section_id: str, claim_id: str) -> PaperState:
        """向章节添加 claim_id（不可变）。"""

    def add_asset_to_section(self, state: PaperState, section_id: str, asset_id: str) -> PaperState:
        """向章节添加 asset_id（不可变）。"""
```

2. 创建 `src/vibewriting/writing/outline.py`：

```python
@dataclass
class OutlineSection:
    """大纲中的一个章节定义。"""
    section_id: str
    title: str
    key_points: list[str]
    suggested_claim_ids: list[str]  # 建议使用的证据卡
    suggested_asset_ids: list[str]  # 建议引用的图表
    section_type: Literal["introduction", "related-work", "method", "experiments", "conclusion", "appendix"]
    tex_file: str  # 如 "sections/introduction.tex"

@dataclass
class PaperOutline:
    """完整论文大纲。"""
    title: str
    topic: str
    abstract_draft: str
    sections: list[OutlineSection]

def build_default_outline(
    topic: str,
    title: str,
    evidence_cards: list[dict],
    asset_manifest: list[dict],
) -> PaperOutline:
    """基于主题、证据卡和数据资产构建默认大纲骨架。

    - 使用固定的 6 章节结构（与 paper/sections/ 对应）
    - 按 evidence_type 分配证据卡到不同章节
    - 按 asset kind 分配图表到实验章节
    """

def outline_to_paper_state(outline: PaperOutline, paper_id: str) -> PaperState:
    """将大纲转换为 PaperState（outline 阶段）。"""

def outline_to_sections(outline: PaperOutline) -> list[SectionState]:
    """将大纲转换为 SectionState 列表。"""
```

3. 创建 `tests/test_writing/test_state_manager.py`，测试：
   - load/save 往返一致性（save → load → 比较）
   - 原子写入（中断不丢失旧文件）
   - 不可变操作（update_section_status 返回新实例）
   - 状态推进逻辑
   - 文件不存在时 load 返回 None

4. 创建 `tests/test_writing/test_outline.py`，测试：
   - build_default_outline 基本流程
   - 证据卡按 evidence_type 分配
   - 资产按 kind 分配到实验章节
   - outline_to_paper_state 转换
   - 空证据卡/空资产时的降级行为

**验收标准**:
- `uv run pytest tests/test_writing/test_state_manager.py tests/test_writing/test_outline.py -v` 全部通过
- 原子写入测试覆盖
- 不可变模式：所有修改返回新实例

---

#### Builder 5: LaTeX 辅助工具 + 增量编译

**文件范围**:
- `src/vibewriting/writing/latex_helpers.py` (新建)
- `src/vibewriting/writing/incremental.py` (新建)
- `tests/test_writing/test_latex_helpers.py` (新建)
- `tests/test_writing/test_incremental.py` (新建)

**依赖**: Builder 1 (PaperState 中 SectionState 的 tex_file 路径)

**实施步骤**:

1. 创建 `src/vibewriting/writing/latex_helpers.py`：

```python
# CLAIM_ID 注释管理
def inject_claim_annotation(line: str, claim_id: str) -> str:
    """在 LaTeX 行末添加 %% CLAIM_ID: EC-XXXX-XXX 注释。

    如果行已有 CLAIM_ID 注释则替换，否则追加。
    """

def extract_claim_annotations(tex_content: str) -> dict[int, str]:
    """从 .tex 内容中提取所有 CLAIM_ID 注释。

    Returns: {行号: claim_id} 映射
    """

def strip_claim_annotations(tex_content: str) -> str:
    """移除所有 %% CLAIM_ID 注释（生成干净版本用于某些场景）。"""

# 引用插入
def format_citation(bib_key: str, style: Literal["citep", "citet"] = "citep") -> str:
    r"""生成 \citep{key} 或 \citet{key}。"""

def format_figure_ref(label: str) -> str:
    r"""生成 \ref{fig:label}。"""

def format_table_ref(label: str) -> str:
    r"""生成 \ref{tab:label}。"""

# LaTeX 段落工具
def split_into_paragraphs(tex_content: str) -> list[str]:
    """按双换行分割 LaTeX 段落（保留注释行）。"""

def count_words_in_tex(tex_content: str) -> int:
    """统计 .tex 文件中的正文字数（排除命令和注释）。"""

def extract_all_labels(tex_content: str) -> set[str]:
    r"""提取 \label{} 中定义的所有 label。"""

def extract_all_refs(tex_content: str) -> set[str]:
    r"""提取 \ref{} 和 \eqref{} 中引用的所有 label。"""
```

2. 创建 `src/vibewriting/writing/incremental.py`：

```python
DRAFT_PREAMBLE = r"""\documentclass[UTF8, a4paper, 12pt, zihao=-4]{ctexart}
\usepackage[top=2.54cm, bottom=2.54cm, left=3.17cm, right=3.17cm]{geometry}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsthm}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage[numbers,sort&compress]{natbib}
\usepackage[colorlinks=true, linkcolor=blue, citecolor=blue, urlcolor=blue]{hyperref}
\graphicspath{{figures/}}
"""

def generate_draft_main(
    section_tex_file: str,
    title: str = "Draft",
    output_path: Path | None = None,
) -> str:
    """生成只含单个章节的 draft_main.tex。

    - 保留完整 preamble（与 main.tex 一致）
    - 只 \input 指定章节
    - 包含 bibliography（引用需要）
    - 返回生成的 .tex 内容
    """

def write_draft_main(
    paper_dir: Path,
    section_tex_file: str,
    title: str = "Draft",
) -> Path:
    """写入 draft_main.tex 到 paper/ 目录，返回文件路径。"""

def compile_single_section(
    paper_dir: Path,
    section_tex_file: str,
) -> tuple[bool, str]:
    """增量编译单章节。

    1. 生成 draft_main.tex
    2. 调用 latexmk（如可用）
    3. 返回 (success, log_output)

    注意: 如果 latexmk 不可用，返回 (False, "latexmk not found")
    """

def cleanup_draft(paper_dir: Path) -> None:
    """清理 draft_main.tex 及其编译产物。"""
```

3. 创建 `tests/test_writing/test_latex_helpers.py`，测试：
   - inject_claim_annotation（新增、替换、多行）
   - extract_claim_annotations（正常、无注释、混合内容）
   - strip_claim_annotations
   - format_citation / format_figure_ref / format_table_ref
   - split_into_paragraphs（空行分割、保留注释）
   - count_words_in_tex（排除命令和注释）
   - extract_all_labels / extract_all_refs

4. 创建 `tests/test_writing/test_incremental.py`，测试：
   - generate_draft_main 输出内容检查（preamble + 单章节 input + bibliography）
   - write_draft_main 文件写入验证
   - cleanup_draft 清理验证
   - compile_single_section（mock subprocess，不依赖 TeX Live）

**验收标准**:
- `uv run pytest tests/test_writing/test_latex_helpers.py tests/test_writing/test_incremental.py -v` 全部通过
- LaTeX 解析全部使用正则表达式
- 增量编译 mock subprocess，不依赖 TeX Live 安装

---

#### Builder 6: Schema 导出 + 模型注册 + 契约集成

**文件范围**:
- `src/vibewriting/models/__init__.py` (修改: 添加导出)
- `src/vibewriting/contracts/schema_export.py` (修改: 添加新模型)
- `src/vibewriting/contracts/schemas/paper_state.schema.json` (新建, 自动生成)
- `src/vibewriting/contracts/schemas/glossary.schema.json` (新建, 自动生成)
- `src/vibewriting/contracts/schemas/symboltable.schema.json` (新建, 自动生成)
- `tests/test_writing/test_schema_integration.py` (新建)

**依赖**: Builder 1 (PaperState) + Builder 2 (Glossary, SymbolTable)

**实施步骤**:

1. 修改 `src/vibewriting/models/__init__.py`：
   - 添加导入: `from .paper_state import PaperState, SectionState, PaperMetrics`
   - 添加导入: `from .glossary import Glossary, SymbolTable, GlossaryEntry, SymbolEntry`
   - 更新 `__all__` 列表

2. 修改 `src/vibewriting/contracts/schema_export.py`：
   - 导入 `PaperState, Glossary, SymbolTable`
   - 将它们添加到 `MODELS` 列表
   - 确保 model_json_schema() 正确生成

3. 运行 schema 导出：`uv run python -m vibewriting.contracts.schema_export`
   - 验证 3 个新 schema 文件生成到 `src/vibewriting/contracts/schemas/`

4. 创建 `tests/test_writing/test_schema_integration.py`，测试：
   - Schema 导出可执行（export_schemas() 不报错）
   - 新 schema 文件存在且非空
   - PaperState 实例通过 schema 验证（validate_contract）
   - Glossary / SymbolTable 实例通过 schema 验证
   - 引用完整性：PaperState → evidence_cards + asset_manifest 交叉验证

**验收标准**:
- `uv run pytest tests/test_writing/test_schema_integration.py -v` 全部通过
- `uv run python -m vibewriting.contracts.schema_export` 生成所有 schema
- 新模型通过 `validate_contract()` 自愈验证循环

---

### Layer 3: Skill 定义（依赖 Layer 2，1 个 Builder）

#### Builder 7: write-draft Skill

**文件范围**:
- `.claude/skills/write-draft/SKILL.md` (新建)
- `tests/test_writing/conftest.py` (新建)

**依赖**: Builder 3 (Quality Gates) + Builder 4 (State Manager + Outline) + Builder 5 (LaTeX Helpers)

**实施步骤**:

1. 创建 `.claude/skills/write-draft/SKILL.md`，定义完整的 Evidence-First 撰写工作流：

```markdown
核心流程:
1. 加载前置产物（literature_cards.jsonl + asset_manifest.json）
2. 生成论文大纲（或接受用户提供的大纲）
3. 创建 paper_state.json（outline 阶段）
4. Approval Gate: 展示大纲，等待用户确认
5. 逐章节撰写（Evidence-First 约束）:
   a. 加载当前章节相关的证据卡子集（按 tags 过滤）
   b. 生成 LaTeX 源码（含 %% CLAIM_ID 注释）
   c. 运行质量门禁
   d. 增量编译验证（如 TeX Live 可用）
   e. 更新 paper_state.json
   f. Git auto-commit: "auto: finish section X [cite: N papers]"
6. 生成术语表和符号表初版
7. 全量编译验证（如 TeX Live 可用）
8. 输出最终报告

关键约束:
- 只允许引用已入库证据卡的 claim
- 图表描述基于 asset_manifest 的 semantic_description
- 源码溯源注释: %% CLAIM_ID: EC-XXXX-XXX
- 学术风格: 客观第三人称，无 LLM 废话
- 每句独占一行（便于 git diff）
```

2. Skill 输入参数：
   - `topic`: 论文主题（必需）
   - `title`: 论文标题（可选，默认从主题生成）
   - `outline`: 自定义大纲 JSON（可选）
   - `data_dir`: 数据目录（默认 data/raw）
   - `resume`: 是否从 paper_state.json 恢复（默认 false）

3. 创建 `tests/test_writing/conftest.py`，提供共享 fixtures：
   - `sample_paper_state()`: 示例 PaperState
   - `sample_glossary()`: 示例 Glossary
   - `sample_symbol_table()`: 示例 SymbolTable
   - `sample_tex_content()`: 示例 LaTeX 章节内容
   - `sample_evidence_cards()`: 示例证据卡列表
   - `sample_asset_manifest()`: 示例资产清单
   - `tmp_paper_dir(tmp_path)`: 临时 paper/ 目录结构

**验收标准**:
- SKILL.md 内容完整，覆盖 Evidence-First 全流程
- conftest.py 提供可复用的测试数据
- `uv run pytest tests/test_writing/ -v` 全部通过

---

## 依赖关系图

```
Layer 1 (并行):
  Builder 1: PaperState 模型 ──┐
  Builder 2: Glossary/Symbols ─┼── Layer 2 (并行):
  Builder 3: Quality Gates ────┘     Builder 4: State Manager + Outline (← B1)
                                      Builder 5: LaTeX Helpers + Incremental (← B1)
                                      Builder 6: Schema + Registration (← B1, B2)
                                           │
                                           └── Layer 3:
                                                Builder 7: write-draft Skill (← B3, B4, B5)
```

## 文件范围汇总

| Builder | 新建文件 | 修改文件 |
|---------|---------|---------|
| B1 | `models/paper_state.py`, `tests/test_paper_state.py` | — |
| B2 | `models/glossary.py`, `tests/test_glossary_symbols.py` | — |
| B3 | `writing/__init__.py`, `writing/quality_gates.py`, `tests/test_writing/__init__.py`, `tests/test_writing/test_quality_gates.py` | — |
| B4 | `writing/state_manager.py`, `writing/outline.py`, `tests/test_writing/test_state_manager.py`, `tests/test_writing/test_outline.py` | — |
| B5 | `writing/latex_helpers.py`, `writing/incremental.py`, `tests/test_writing/test_latex_helpers.py`, `tests/test_writing/test_incremental.py` | — |
| B6 | `contracts/schemas/*.schema.json`, `tests/test_writing/test_schema_integration.py` | `models/__init__.py`, `contracts/schema_export.py` |
| B7 | `.claude/skills/write-draft/SKILL.md`, `tests/test_writing/conftest.py` | — |

**总计**: 新建 19 个文件, 修改 2 个文件

## 验证计划

全部 Builder 完成后，运行：

```bash
# 1. 全量测试
uv run pytest -v

# 2. 覆盖率检查（目标 >= 85%）
uv run pytest --cov=vibewriting --cov-report=term-missing

# 3. Schema 导出验证
uv run python -m vibewriting.contracts.schema_export

# 4. 类型检查（如配置了 mypy）
uv run mypy src/vibewriting/writing/ src/vibewriting/models/paper_state.py src/vibewriting/models/glossary.py
```

## 设计决策记录

| 编号 | 决策 | 理由 |
|------|------|------|
| D16 | PaperState 使用 Pydantic BaseModel（非 BaseEntity） | 不需要 BaseEntity 的 id/tags 审计字段，PaperState 自身已有 paper_id 和时间戳 |
| D17 | SectionState 独立于 Section 模型 | Section 是通用数据模型，SectionState 是写作阶段的扩展状态（含 tex_file, word_count 等写作特有字段） |
| D18 | Quality Gates 纯正则解析 | 不依赖外部 LaTeX 解析库（如 TexSoup），减少依赖，正则足够处理 \citep/\ref/\label |
| D19 | 增量编译 mock subprocess | 测试不依赖 TeX Live 安装，通过 mock 验证逻辑正确性 |
| D20 | Glossary/SymbolTable 不可变操作 | 遵循项目编码规范（不可变模式），修改操作返回新实例 |
