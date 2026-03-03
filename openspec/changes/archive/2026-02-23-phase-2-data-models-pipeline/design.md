# Design: Phase 2 — 数据模型 + 处理管线

## 技术决策

### D1: Schema 管理策略 — Pydantic 自动生成

**决策**: 使用 `model_json_schema()` 从 Pydantic 模型自动生成 JSON Schema，导出到 `contracts/schemas/`。

**理由**: 消除 Pydantic 模型与 JSON Schema 之间的漂移风险。单一事实源在 Python 代码中。

**实现**:
```python
# contracts/schema_export.py
from vibewriting.models import Paper, Experiment, Figure, Table, Section
MODELS = [Paper, Experiment, Figure, Table, Section]

def export_schemas(output_dir: Path):
    for model in MODELS:
        schema = model.model_json_schema()
        (output_dir / f"{model.__name__.lower()}.schema.json").write_text(
            json.dumps(schema, indent=2, ensure_ascii=False)
        )
```

### D2: Pydantic 模型设计 — 组合优先

**决策**: `AssetBase(asset_id, kind, path, content_hash, semantic_description)` 作为 `Figure`/`Table` 父类，使用 `Literal` discriminator。其余模型使用组合而非继承。

**字段约束**:
- `extra='forbid'` 全局启用
- 不可变字段（如 `asset_id`）使用 `frozen=True`
- 所有 ID 格式严格：`asset_id` → `ASSET-YYYY-NNN`，`claim_id` → `EC-YYYY-NNN`

### D3: 契约自愈循环

**决策**: 规则优先（Regex 修复常见 JSON 错误）+ LLM 兜底，max 3 轮。

**实现流程**:
```
输入 payload
  → jsonschema.validate()
  → 失败 → 规则修复器（Regex: 未闭合引号/非法转义/Markdown 代码块剥离）
  → 再次校验
  → 仍失败 → LLM 修复器（传入 error.path/message/schema_path）
  → 再次校验
  → 仍失败 → 第 3 轮最终尝试
  → 仍失败 → 抛出 ContractValidationError + 诊断日志
```

**有界保证**: 循环计数器 + `max_retries=3` 硬编码上限。

### D4: 管线架构 — 轻量 DAG

**决策**: 自建轻量 DAG Runner，不引入 Prefect/Celery 等外部工具。

**设计**:
```python
# pipeline/dag.py
@dataclass
class DAGNode:
    name: str
    fn: Callable
    depends_on: list[str]

class DAGRunner:
    def add_node(self, node: DAGNode): ...
    def run(self, context: dict) -> dict:
        # 拓扑排序 → 串行执行（Phase 2 无并发需求）
        # 每步产出写入 context
        # 失败时记录错误并中断
```

**节点列表**:
1. `load_data` → 读取原始数据
2. `clean_data` → 清洗
3. `transform_data` → 转换
4. `compute_statistics` → 统计
5. `generate_figures` → 图表
6. `generate_tables` → 表格
7. `build_manifests` → 构建 asset_manifest + run_manifest
8. `validate_contracts` → 校验所有产物

### D5: Golden Test 确定性保证

**决策**: 文本快照匹配 + 规范化（去除时间戳/路径噪声）。

**确定性措施**:
- `random.seed(42)` + `np.random.seed(42)`
- `matplotlib.use('pgf')` + 固定 rcParams
- `locale` 固定为 `C`/`POSIX`
- DataFrame 操作后 `.sort_values().reset_index(drop=True)`
- 浮点输出统一 6 位小数
- JSON `sort_keys=True`
- 换行统一 LF

### D6: 新增依赖

| 包 | 版本约束 | 用途 |
|----|---------|------|
| jsonschema | >=4.0 | 契约强校验 |
| typer | >=0.9 | CLI 入口 |
| jinja2 | >=3.0 | LaTeX 表格模板 |

### D7: 异步策略 — 混合模式

**决策**: `processing/` 和 `visualization/` 使用同步函数。MCP 调用使用 `async`。DAG Runner 同步执行。

**理由**: pandas/scipy/matplotlib 是 CPU 密集型，async 无收益且增加复杂度。Phase 3 的 MCP 调用才需要 async。

### D8: 环境变量前缀

**决策**: 统一 `VW_` 前缀。

**映射**:
- `VW_DIFY_API_KEY` → Dify API 密钥
- `VW_DIFY_API_BASE_URL` → Dify 基础 URL
- `VW_DIFY_DATASET_ID` → Dify 数据集 ID
- `VW_RANDOM_SEED` → 全局随机种子（默认 42）
- `VW_FLOAT_PRECISION` → 浮点精度（默认 6）

### D9: Python 版本升级

**决策**: `pyproject.toml` 中 `requires-python` 从 `>=3.11` 改为 `>=3.12`。

## 目录结构

```
src/vibewriting/
  models/
    __init__.py          ← 导出所有模型
    base.py              ← BaseEntity, AssetBase
    paper.py             ← Paper
    experiment.py        ← Experiment
    figure.py            ← Figure
    table.py             ← Table
    section.py           ← Section
  contracts/
    __init__.py
    validator.py         ← validate_contract() + 自愈循环
    integrity.py         ← validate_referential_integrity()
    schema_export.py     ← 自动导出 JSON Schema
    healers/
      __init__.py
      regex_healer.py    ← 规则修复器
      llm_healer.py      ← LLM 修复器接口
    schemas/             ← 自动生成的 JSON Schema（gitignored or committed）
  processing/
    __init__.py
    cleaners.py          ← 数据清洗
    transformers.py      ← 数据转换
    statistics.py        ← 统计计算
  visualization/
    __init__.py
    figures.py           ← matplotlib 图表
    tables.py            ← LaTeX 表格（jinja2）
    pgf_export.py        ← PGF 导出
  pipeline/
    __init__.py
    dag.py               ← DAG Runner
    cli.py               ← typer CLI
    nodes.py             ← DAG 节点定义
tests/
  golden/
    fixtures/            ← 小样例输入数据
    baselines/           ← 期望输出 baseline
    test_golden.py       ← 快照匹配测试
  test_models.py
  test_contracts.py
  test_processing.py
  test_visualization.py
  test_pipeline.py
```
