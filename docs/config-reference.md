# 配置参考

本文档描述 vibewriting 的所有配置项，包括论文参数（`paper_config.yaml`）和环境变量（`.env`）。

---

## 配置优先级

vibewriting 使用三层配置，优先级从高到低：

```
命令行参数  >  环境变量（.env）  >  paper_config.yaml（带默认值）
```

- **命令行参数**：运行 Skill 或 CLI 时传入的 `--key=value` 参数，覆盖所有其他来源
- **环境变量**：`.env` 文件中的变量，覆盖 YAML 中的同名字段（如 `VW_RANDOM_SEED`）
- **paper_config.yaml**：项目级配置文件，所有字段均有默认值，未填写时使用代码内置默认值

---

## paper_config.yaml — 论文配置字段

配置文件位于项目根目录，使用 YAML 格式。通过 `PaperConfig` Pydantic 模型加载，所有字段类型安全验证。

### 字段总览

| 字段名 | 类型 | 默认值 | 必填 | 说明 |
|--------|------|--------|------|------|
| `topic` | `str` | `"untitled"` | 是 | 论文主题，将作为写作任务的核心输入 |
| `language` | `"zh"` \| `"en"` | `"zh"` | 否 | 输出语言：`zh` 为简体中文，`en` 为英文 |
| `document_class` | `str` | `"ctexart"` | 否 | LaTeX 文档类，中文论文用 `ctexart`，英文用 `article` |
| `sections` | `list[str]` | 见下方 | 否 | 章节列表，按顺序排列，不可为空 |
| `literature_query_count` | `int` | `3` | 否 | 文献检索轮数，每轮调用一次 paper-search MCP，最小值为 1 |
| `min_evidence_cards` | `int` | `5` | 否 | 最少证据卡数量，低于此数量时写作流程发出警告，最小值为 1 |
| `data_dir` | `str \| null` | `null` | 否 | 原始数据目录路径；`null` 时使用默认的 `data/raw` |
| `random_seed` | `int` | `42` | 否 | 随机种子，保证数据处理和图表生成的可复现性 |
| `writing_mode` | `"single"` \| `"multi"` | `"multi"` | 否 | 写作模式：`single` 为单 Agent，`multi` 为多 Agent 并行 |
| `enable_ai_disclosure` | `bool` | `false` | 否 | 是否在论文末尾自动插入 AI 使用声明段落 |
| `enable_anonymize` | `bool` | `false` | 否 | 是否启用匿名化处理（用于双盲投稿，隐藏作者信息） |
| `natbib_style` | `str` | `"plainnat"` | 否 | natbib 引用风格，可选 `plainnat`、`abbrvnat`、`unsrtnat` |
| `auto_approve` | `bool` | `false` | 否 | 跳过所有 Approval Gates（危险！仅用于自动化测试场景） |

### 默认章节列表

当 `sections` 未设置时，默认使用以下五个章节：

```yaml
sections:
  - 引言
  - 相关工作
  - 方法
  - 实验
  - 结论
```

### 字段详细说明

#### `topic`（必填）

论文主题字符串，会传递给所有写作 Agent 和文献检索工具。建议使用具体描述：

```yaml
# 好的写法
topic: "基于 Transformer 的中文医学命名实体识别方法"

# 过于宽泛
topic: "深度学习"
```

#### `language`

控制论文正文的输出语言。`zh` 时使用 `ctexart` 文档类（需 TeX Live 中文支持），`en` 时使用标准 `article`。

#### `document_class`

直接写入 LaTeX 文件的 `\documentclass{...}`。如需自定义文档类（如期刊模板），在此修改：

```yaml
document_class: IEEEtran  # IEEE 期刊模板
```

#### `literature_query_count`

控制文献检索的深度。值越大，检索到的论文越多，耗时越长。建议范围：`2`（快速草稿）到 `5`（高质量综述）。

#### `writing_mode`

- `single`：所有章节由单个 Agent 顺序写作，速度较慢但上下文连贯性更好
- `multi`：各章节由独立 Agent 并行写作，速度快，适合大多数场景

#### `natbib_style`

控制参考文献的排版格式：

| 值 | 效果 |
|----|------|
| `plainnat` | 按作者/年份排序，完整作者名 |
| `abbrvnat` | 按作者/年份排序，缩写作者名 |
| `unsrtnat` | 按引用顺序排列，不排序 |

### 完整配置示例

```yaml
topic: "基于深度学习的医学图像分割方法综述"
language: zh
document_class: ctexart
sections:
  - 引言
  - 相关工作
  - 方法
  - 实验
  - 讨论
  - 结论
literature_query_count: 4
min_evidence_cards: 8
data_dir: null
random_seed: 42
writing_mode: multi
enable_ai_disclosure: false
enable_anonymize: false
natbib_style: plainnat
auto_approve: false
```

---

## .env — 环境变量

环境变量文件位于项目根目录，从 `.env.example` 复制后填写。`VW_` 前缀为 vibewriting 专属命名空间。

### paper-search MCP（文献检索服务）

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `SERPAPI_API_KEY` | 是 | 无 | SerpAPI 密钥，用于搜索学术数据库。[获取地址](https://serpapi.com/) |
| `LLM_PROVIDER` | 是 | 无 | LLM 提供商，可选 `openai`、`anthropic` 等 |
| `LLM_MODEL` | 是 | 无 | 使用的模型名称，如 `gpt-4o`、`claude-opus-4-6` |
| `LLM_BASE_URL` | 否 | 无 | 自定义 LLM API 端点（使用代理或私有部署时填写） |
| `OPENAI_API_KEY` | 条件 | 无 | OpenAI API 密钥（`LLM_PROVIDER=openai` 时必填） |

### Dify 知识库（可选）

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `VW_DIFY_API_BASE_URL` | 否 | `https://api.dify.ai/v1` | Dify API 端点，私有部署时修改 |
| `VW_DIFY_API_KEY` | 否 | 无 | Dify API 密钥，用于访问知识库 |
| `VW_DIFY_DATASET_ID` | 否 | 无 | Dify 数据集 ID，指定检索的知识库 |

### 数据管线配置

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `VW_RANDOM_SEED` | 否 | `42` | 全局随机种子，覆盖 `paper_config.yaml` 中的 `random_seed` |
| `VW_FLOAT_PRECISION` | 否 | `6` | 浮点数精度，控制统计结果的小数位数 |

### 文献去重配置

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `VW_DEDUP_THRESHOLD` | 否 | `0.9` | 文献去重相似度阈值（0~1），值越高去重越严格 |

### LaTeX 编译与质量控制（Phase 6）

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `VW_COMPILE_MAX_RETRIES` | 否 | `5` | LaTeX 编译失败时的最大重试次数 |
| `VW_COMPILE_TIMEOUT_SEC` | 否 | `120` | 单次编译超时时间（秒） |
| `VW_PATCH_WINDOW_LINES` | 否 | `10` | 自动修复 LaTeX 错误时的上下文窗口行数 |
| `VW_ENABLE_LAYOUT_CHECK` | 否 | `false` | 是否启用版面检查（需额外依赖） |
| `VW_ENABLE_AI_DISCLOSURE` | 否 | `false` | 全局 AI 声明开关，覆盖 `paper_config.yaml` 中的同名字段 |
| `VW_CROSSREF_API_EMAIL` | 否 | 无 | Crossref API 邮箱（提高请求速率限制） |

### 最小可用配置（.env 示例）

以下为使用 OpenAI 作为 LLM 提供商的最小配置：

```env
SERPAPI_API_KEY=sk-serp-xxxxxxxxxxxx
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
```

---

## 配置加载机制

vibewriting 的配置加载流程：

1. 程序启动时调用 `load_paper_config(path)` 读取 `paper_config.yaml`
2. 如果文件不存在，返回带有 `topic="untitled"` 的默认配置
3. 环境变量在运行时由各模块直接通过 `os.environ` 或 `python-dotenv` 读取
4. 命令行传入的参数通过 `merge_config(base, overrides)` 不可变地合并到配置对象

`merge_config` 使用不可变合并模式，不修改原始配置对象：

```python
# 内部实现示意
def merge_config(base: PaperConfig, overrides: dict) -> PaperConfig:
    merged = base.model_dump()
    merged.update(overrides)
    return PaperConfig(**merged)  # 返回新对象
```
