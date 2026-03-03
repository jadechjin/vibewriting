# Tasks: Phase 2 — 数据模型 + 处理管线

> 零决策实施计划 — 每个任务都是纯机械执行，无需判断

## P0: 项目配置更新（前置）

### T01: 更新 pyproject.toml 依赖与版本
- [x] `requires-python` 从 `">=3.11"` 改为 `">=3.12"`
- [x] `[project.dependencies]` 新增: `jsonschema>=4.0`, `typer>=0.9`, `jinja2>=3.0`
- [x] 运行 `uv sync` 安装新依赖
- **验证**: `uv run python -c "import jsonschema, typer, jinja2; print('OK')"`

### T02: 更新 .env.example 环境变量前缀
- [x] 所有变量加 `VW_` 前缀: `VW_DIFY_API_KEY`, `VW_DIFY_API_BASE_URL`, `VW_DIFY_DATASET_ID`
- [x] 新增: `VW_RANDOM_SEED=42`, `VW_FLOAT_PRECISION=6`
- **验证**: 与 `config.py` 中的键名一致

### T03: 更新 config.py 适配 VW_ 前缀
- [x] 所有 `os.getenv()` 调用使用 `VW_` 前缀
- [x] 新增 `RANDOM_SEED` 和 `FLOAT_PRECISION` 配置项
- **验证**: `uv run python -c "from vibewriting.config import *; print('OK')"`

## P1: Pydantic 数据模型

### T04: 创建 models/base.py — BaseEntity + AssetBase
- [x] `BaseEntity`: `id: str`, `created_at: datetime`, `updated_at: datetime`, `tags: list[str]`
- [x] `AssetBase(BaseEntity)`: `asset_id: str`, `kind: Literal["figure", "table"]`, `path: str`, `content_hash: str`, `semantic_description: str`, `generator_version: str`
- [x] 所有模型 `model_config = ConfigDict(extra='forbid', frozen=False)`
- **验证**: `uv run pytest tests/test_models.py::test_base_models`

### T05: 创建 models/paper.py — Paper
- [x] 字段: `title: str`, `authors: list[str]`, `abstract: str`, `bib_key: str`, `quality_score: float = Field(ge=0, le=10)`, `sections: list[str]`
- [x] `bib_key` 约束: `pattern=r'^[a-zA-Z0-9_:-]+$'`
- **验证**: round-trip PBT 测试

### T06: 创建 models/experiment.py — Experiment
- [x] 字段: `experiment_id: str`, `config: dict[str, Any]`, `results: dict[str, Any]`, `data_fingerprint: str`, `asset_ids: list[str]`
- **验证**: round-trip PBT 测试

### T07: 创建 models/figure.py — Figure（继承 AssetBase）
- [x] `kind: Literal["figure"]`
- [x] 额外字段: `chart_type: Literal["line", "bar", "scatter", "heatmap"]`, `data_source: str`, `x_label: str`, `y_label: str`
- **验证**: discriminator 测试

### T08: 创建 models/table.py — Table（继承 AssetBase）
- [x] `kind: Literal["table"]`
- [x] 额外字段: `columns: list[str]`, `row_count: int = Field(ge=0)`, `template_name: str`
- **验证**: discriminator 测试

### T09: 创建 models/section.py — Section
- [x] 字段: `section_id: str`, `title: str`, `outline: list[str]`, `status: Literal["draft", "review", "complete"]`, `claim_ids: list[str]`, `asset_ids: list[str]`, `citation_keys: list[str]`
- **验证**: round-trip PBT 测试

### T10: 更新 models/__init__.py 导出所有模型
- [x] `from .base import BaseEntity, AssetBase`
- [x] `from .paper import Paper` ... 等
- **验证**: `uv run python -c "from vibewriting.models import Paper, Experiment, Figure, Table, Section"`

### T11: 编写 tests/test_models.py
- [x] 每个模型: round-trip 测试、bounds 测试、extra='forbid' 测试
- [x] 使用 hypothesis `st.from_type()` 生成测试数据
- **验证**: `uv run pytest tests/test_models.py -v`

## P2: 阶段产物契约

### T12: 创建 contracts/schema_export.py
- [x] 遍历所有 Pydantic 模型，调用 `model_json_schema()`
- [x] 导出到 `contracts/schemas/` 目录
- [x] 增加 CLI 命令: `uv run python -m vibewriting.contracts.schema_export`
- **验证**: `ls contracts/schemas/*.schema.json` 非空

### T13: 创建 contracts/healers/regex_healer.py
- [x] 修复常见 JSON 错误: 未闭合引号、非法转义、Markdown 代码块剥离、尾部逗号
- [x] 每个修复规则一个函数，可组合
- **验证**: 单元测试覆盖 5+ 种常见错误模式

### T14: 创建 contracts/healers/llm_healer.py
- [x] 接口定义: `heal(payload: str, errors: list[ValidationError]) -> str`
- [x] 构造 Prompt: 包含 Schema 片段 + error.path/message
- [x] 返回修复后的 JSON 字符串
- **验证**: Mock LLM 的单元测试

### T15: 创建 contracts/validator.py
- [x] `validate_contract(payload, schema_name, max_retries=3) -> ValidatedPayload`
- [x] 循环: jsonschema.validate → 失败 → regex_healer → 失败 → llm_healer → 最终失败抛异常
- [x] 每轮记录 violation_count
- **验证**: PBT 测试（bounds: ≤3 轮, monotonicity: 违规不增, idempotency: 合法输入幂等）

### T16: 创建 contracts/integrity.py
- [x] `validate_referential_integrity(paper_state, evidence_cards, asset_manifest, glossary, symbols, bib_path)`
- [x] 外键检查: claim_id → evidence_cards, asset_id → asset_manifest, bib_key → references.bib
- [x] 输出: `list[IntegrityViolation]` 机器可读
- **验证**: PBT 测试（invariant: 断链必检出, commutativity: 加载顺序无关）

### T17: 编写 tests/test_contracts.py
- [x] 自愈循环 bounds/monotonicity/idempotency 测试
- [x] 引用完整性 invariant/commutativity 测试
- [x] Schema 导出一致性测试
- **验证**: `uv run pytest tests/test_contracts.py -v`

## P3: 数据清洗管线

### T18: 实现 processing/cleaners.py
- [x] `read_csv(path) -> DataFrame`: 编码检测（chardet）+ UTF-8 转换
- [x] `read_json(path) -> DataFrame`
- [x] `handle_missing(df, strategy) -> DataFrame`: drop/fill/interpolate
- [x] `convert_types(df, type_map) -> DataFrame`: 类型转换
- [x] 所有函数纯函数，不修改输入
- **验证**: idempotency PBT 测试

### T19: 实现 processing/transformers.py
- [x] `aggregate(df, group_by, agg_funcs) -> DataFrame`
- [x] `pivot(df, index, columns, values) -> DataFrame`
- [x] `feature_engineer(df, features) -> DataFrame`
- [x] groupby 后强制 `.sort_values().reset_index(drop=True)`
- **验证**: 确定性测试

### T20: 实现 processing/statistics.py
- [x] `descriptive_stats(df) -> dict`: mean/std/min/max/quartiles
- [x] `hypothesis_test(group_a, group_b, test_type) -> TestResult`
- [x] `effect_size(group_a, group_b) -> float`
- [x] 所有浮点输出 round 到 VW_FLOAT_PRECISION 位
- **验证**: invariant PBT 测试（统计与数据一致）

### T21: 编写 tests/test_processing.py
- [x] cleaners idempotency + commutativity 测试
- [x] statistics invariant 测试
- [x] 边界: 空 DataFrame、单行、NaN/Inf
- **验证**: `uv run pytest tests/test_processing.py -v`

## P4: 图表生成

### T22: 实现 visualization/figures.py
- [x] `generate_line_chart(data, config) -> FigureResult`
- [x] `generate_bar_chart(data, config) -> FigureResult`
- [x] `generate_scatter_plot(data, config) -> FigureResult`
- [x] `generate_heatmap(data, config) -> FigureResult`
- [x] 每个函数返回 `FigureResult(path, content_hash, semantic_description)`
- **验证**: 输出文件存在且哈希稳定

### T23: 实现 visualization/tables.py
- [x] `generate_latex_table(data, template_name, config) -> TableResult`
- [x] 使用 jinja2 模板，booktabs 风格
- [x] 模板存放在 `visualization/templates/`
- **验证**: 输出 .tex 文件可嵌入 LaTeX

### T24: 实现 visualization/pgf_export.py
- [x] `export_pgf(fig, output_path) -> tuple[Path, Path]`: 导出 .pgf + .pdf
- [x] 固定 `matplotlib.use('pgf')` + rcParams
- [x] 计算 content_hash (sha256)
- **验证**: idempotency 测试

### T25: 编写 tests/test_visualization.py
- [x] figures idempotency + bounds 测试
- [x] tables 模板渲染测试
- [x] pgf_export 哈希稳定性测试
- **验证**: `uv run pytest tests/test_visualization.py -v`

## P5: 管线编排

### T26: 实现 pipeline/dag.py
- [x] `DAGNode` dataclass: name, fn, depends_on
- [x] `DAGRunner`: add_node, run (拓扑排序 + 串行执行)
- [x] 失败时记录错误并中断，返回已完成步骤
- **验证**: 单元测试（拓扑排序正确性、循环依赖检测）

### T27: 实现 pipeline/nodes.py
- [x] 定义 8 个 DAG 节点: load_data → clean_data → transform_data → compute_statistics → generate_figures → generate_tables → build_manifests → validate_contracts
- [x] 每个节点是纯函数: `(context: dict) -> dict`
- **验证**: 每个节点独立测试

### T28: 实现 pipeline/cli.py
- [x] typer CLI: `vibewriting pipeline run --data-dir <path> --output-dir <path> --seed 42`
- [x] 连接 DAG Runner
- [x] 输出 asset_manifest.json + run_manifest.json
- **验证**: `uv run python -m vibewriting.pipeline.cli --help`

### T29: 编写 tests/test_pipeline.py
- [x] 端到端管线测试（小样例数据 → 完整输出）
- [x] DAG 拓扑排序测试
- [x] 管线中断恢复测试
- **验证**: `uv run pytest tests/test_pipeline.py -v`

## P6: Golden Test

### T30: 创建 tests/golden/fixtures/
- [x] `sample_data.csv`: 10 行 5 列样例数据
- [x] `sample_config.json`: 管线配置
- **验证**: 文件存在且格式正确

### T31: 运行管线生成 baseline
- [x] 使用固定 seed=42 运行完整管线
- [x] 将输出复制到 `tests/golden/baselines/`
- [x] 包含: .pgf 文件、.tex 表格、asset_manifest.json、run_manifest.json
- **验证**: baseline 文件非空

### T32: 实现 tests/golden/test_golden.py
- [x] 快照比较: 规范化后文本一致性
- [x] 规范化器: 去除时间戳占位符、统一路径分隔符
- [x] 如果 baseline 不存在则自动生成（首次运行）
- **验证**: `uv run pytest tests/golden/ -v`

## P7: 最终验证

### T33: 运行完整测试套件
- [x] `uv run pytest --cov=vibewriting --cov-report=term-missing`
- [x] 确认覆盖率 ≥80%
- **验证**: CI 通过

### T34: 端到端验证
- [x] 示例数据 → 完整管线 → 图表 + 表格 + manifests
- [x] 所有契约校验通过
- [x] 重复运行哈希一致
- **验证**: Golden Test 通过

### T35: 更新 CLAUDE.md（如有必要）
- [x] 新增管线相关命令到"构建脚本"部分
- [x] 更新目录映射
- **验证**: 文档与实际一致
