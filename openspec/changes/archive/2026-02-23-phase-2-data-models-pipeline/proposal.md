# Proposal: Phase 2 — 数据模型 + 处理管线

## Context

### 用户需求

为 vibewriting 科研论文自动化写作系统搭建从原始数据到 LaTeX 可用资产（图表 + 表格）的自动化管线，产出机器可验证的资产契约与运行清单。

### 当前状态

- **Phase 1 已完成**: 项目脚手架、MCP 集成、LaTeX 模板、环境验证（52/52 任务）
- **已有占位**: `src/vibewriting/models/`、`processing/`、`visualization/` 含空 `__init__.py`
- **缺失**: `src/vibewriting/contracts/` 目录、所有 JSON Schema、管线编排逻辑

### 发现的约束（多模型交叉验证）

#### 硬约束

| ID | 约束 | 影响 |
|----|------|------|
| H1 | Python >=3.12（路线图要求，pyproject.toml 需更新） | 可用 type alias 等新特性 |
| H2 | Pydantic >=2.0 + `model_json_schema()` 自动生成 Schema | Schema 与模型同源 |
| H3 | matplotlib pgf 后端（非 tikzplotlib，已废弃） | 图表生成格式 |
| H4 | jsonschema 库用于契约强校验 | 新增依赖 |
| H5 | jinja2 用于 LaTeX 表格模板 | 新增依赖 |
| H6 | typer 用于 CLI 入口 | 新增依赖 |
| H7 | 自愈循环：规则优先（Regex）+ LLM 兜底，max 3 轮 | 有界终止 |
| H8 | Golden Test 文本快照匹配（规范化后字符串比较） | 确定性保证 |
| H9 | 环境变量统一 VW_ 前缀 | 配置管理 |
| H10 | 异步混合模式：同步处理 + async MCP | 避免事件循环阻塞 |

#### 软约束

| ID | 约束 | 来源 |
|----|------|------|
| S1 | 轻量 DAG + 函数式节点（非重型工作流引擎） | 用户决策 |
| S2 | 组合优先于继承（Pydantic 模型设计） | Codex 推荐 |
| S3 | `extra='forbid'` 严格类型 | 防止 Schema 漂移 |
| S4 | 浮点量化统一 6 位小数 | Golden Test 确定性 |
| S5 | DataFrame groupby/merge 后强制排序 | 确定性保证 |

## Requirements

### R1: Pydantic 数据模型

**交付物**: `src/vibewriting/models/` 下的模型定义

模型清单：
- `Paper`: 论文元数据（标题、作者、摘要、引用键、质量评分）
- `Experiment`: 实验配置 + 结果
- `Figure`: 图表元数据 + 生成参数（继承 `AssetBase`）
- `Table`: 表格元数据 + 生成参数（继承 `AssetBase`）
- `Section`: 章节结构（大纲、状态、引用列表、claim_ids、asset_ids）

**PBT 不变量**:
- [CRITICAL] round_trip: `model_validate_json(model_dump_json(m))` 语义等价
- [CRITICAL] invariant: `model_json_schema()` 接受的数据 ↔ `model_validate` 不拒绝
- [HIGH] bounds: 所有 ge/le/min_length/max_length 字段严格满足边界

### R2: 阶段产物契约

**交付物**: `src/vibewriting/contracts/`

- JSON Schema 自动从 Pydantic 模型导出到 `schemas/` 目录
- `validator.py`: `validate_contract(payload, schema_name, healer, max_retries=3)`
- `integrity.py`: 跨契约外键校验（claim_id → evidence_card, asset_id → asset_manifest, bib_key → references.bib）
- `schema_export.py`: 自动导出脚本（CI/开发时调用）

**PBT 不变量**:
- [CRITICAL] bounds: 自愈循环最多 3 轮，第 3 轮后必须终止
- [CRITICAL] monotonicity: 每轮后违规计数单调不增
- [HIGH] idempotency: 对合法输入运行自愈应幂等

### R3: 数据清洗管线

**交付物**: `src/vibewriting/processing/`

- `cleaners.py`: CSV/JSON 读取、缺失值处理、类型转换、编码检测
- `transformers.py`: 聚合、透视、特征工程
- `statistics.py`: 描述性统计、假设检验、效应量计算

**PBT 不变量**:
- [CRITICAL] idempotency: `clean(clean(x)) == clean(x)`
- [HIGH] commutativity: 无状态 cleaner 可交换
- [CRITICAL] invariant: statistics 与清洗后数据一致

### R4: 图表生成

**交付物**: `src/vibewriting/visualization/`

- `figures.py`: matplotlib 图表（折线图、柱状图、散点图、热力图）
- `tables.py`: LaTeX 表格（booktabs 风格，jinja2 模板）
- `pgf_export.py`: matplotlib pgf 后端导出（.pgf + .pdf 双格式）
- 每个资产附带 `semantic_description`

**PBT 不变量**:
- [HIGH] idempotency: 固定输入 + rcParams → PGF 哈希稳定
- [CRITICAL] bounds: 所有数据点落在坐标轴边界内
- [HIGH] invariant: Manifest 原子性（失败不产生半成品记录）

### R5: 管线编排入口

**交付物**: `src/vibewriting/pipeline/`

- `dag.py`: 轻量 DAG Runner（拓扑排序 + 缓存 + 失败重试）
- `cli.py`: typer CLI（指定数据源 → 清洗 → 图表 → 输出到 output/）
- 产出 `asset_manifest.json` + `run_manifest.json`

**PBT 不变量**:
- [CRITICAL] invariant: manifest 中每条路径存在且 sha256 匹配
- [HIGH] round_trip: manifest JSON 序列化/反序列化语义不变
- [HIGH] monotonicity: 增量运行不改写旧资产记录

### R6: Golden Test

**交付物**: `tests/golden/`

- 小样例数据 + 期望输出 baseline
- `uv run pytest -k golden`: 比较 .pgf 文本 + .tex 表格一致性
- 固定种子、rcParams、排序规则、LF 换行

**PBT 不变量**:
- [CRITICAL] idempotency: 同输入同配置同 seed → 字节级一致
- [HIGH] commutativity: 测试执行顺序不影响快照
- [HIGH] bounds: 仅白名单易变字段被归一化

## Success Criteria

| ID | 判据 | 验证方式 |
|----|------|---------|
| SC1 | `uv run pytest` 全部通过（含 golden tests） | CI |
| SC2 | 示例数据端到端生成图表 + 表格 + manifests | 手动 + CI |
| SC3 | 每个资产有非空 `semantic_description` | Schema 校验 |
| SC4 | 重复运行产出相同哈希 | Golden Test |
| SC5 | 契约文件通过 Schema 校验 | `validate_contract()` |
| SC6 | 引用完整性校验无断链 | `validate_referential_integrity()` |
| SC7 | 自愈循环不超过 3 轮 | 单元测试 |
| SC8 | 测试覆盖率 ≥80% | pytest-cov |
