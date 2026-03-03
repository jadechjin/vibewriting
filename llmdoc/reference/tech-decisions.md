# 技术决策速查表

**来源**: Phase 1 `design.md` + Phase 2 实现经验 + Phase 3 文献整合 + Phase 4 草稿撰写 + Phase 5 多 Agent 编排 + Post-Phase 7 Bug 修复

## Phase 1 决策（D1-D9）

### D1: 分阶段降级交付

**选择**: P0-P4 五阶段，按外部阻塞状态渐进交付
**否决**: 容器化封装、远程编译服务
**理由**: 允许在 TeX Live / Dify 凭据未就绪时先交付不依赖它们的部分

### D2: LaTeX 编译驱动

**选择**: latexmk 统一驱动（`$pdf_mode=5`），不保留手工回退
**否决**: latexmk + 手工回退链、固定命令链
**配置**: `paper/latexmkrc` -- xelatex + bibtex + synctex + out_dir=build
**理由**: latexmk 自动管理编译迭代次数和依赖追踪

### D3: 依赖锁定

**选择**: 提交 `uv.lock` 到 Git
**否决**: 不提交 lockfile
**理由**: 科研可复现性要求，确保任何时间点重建环境一致

### D4: Dify 失败策略

**选择**: 可降级运行（无知识库模式）
**否决**: 失败即中断
**实现**: `scripts/dify-kb-mcp/server.py` 凭据缺失时返回结构化错误，不崩溃；python-dotenv 自动加载 `.env` 解决 MCP 环境变量插值失败问题
**环境变量回退链**: `DIFY_*`（.mcp.json env 传入） -> `VW_DIFY_*`（.env 直接读取），两层回退确保凭据可达
**URL 路径**: base URL 已含 `/v1`，请求路径直接使用 `/datasets/{id}/...`，避免路径重复
**理由**: Dify 是增强功能，不应阻塞核心论文撰写流程

### D5: 环境验证退出码

**选择**: 分级语义 0/1/2 + JSON 报告
**否决**: 简单二元退出码
**实现**: `scripts/validate_env.py`
**语义**: 0=全通过, 1=必需项失败, 2=仅可选项失败
**理由**: 区分"完全不能工作"和"部分功能受限"

### D6: Git 初始化

**选择**: 幂等校验模式
**理由**: 已有 .git 时仅补全配置，避免破坏已有历史

### D7: 配置管理

**选择**: pydantic-settings + `VW_` 环境变量前缀 + `paper_config.yaml` 双配置系统
**实现**: `src/vibewriting/config.py`，`BaseSettings` + `SettingsConfigDict(env_prefix="VW_")` + `apply_paper_config()` 桥接函数
**升级**: Phase 2 从 python-dotenv 迁移到 pydantic-settings，新增 `random_seed`/`float_precision` 字段；Post-Phase 7 新增双配置系统（`.env` 仅敏感凭据，`paper_config.yaml` 管理非敏感配置）
**理由**: 类型安全的配置管理，自动从 `.env` 加载，前缀隔离命名空间；非敏感管线参数迁移到 YAML 便于版本控制和每篇论文独立配置

### D8: 日志策略

**选择**: Python logging 模块，文件(详细) + 控制台(摘要)
**理由**: 调试时查文件日志，日常使用看控制台摘要

### D9: paper-search 集成

**选择**: MCP stdio 协议，`.mcp.json` 配置绝对路径
**否决**: 子进程 CLI 调用、直接 import
**理由**: MCP 是 Claude Code 原生支持的集成方式，解耦项目间依赖

## 关键约束备忘

| 编号 | 约束 | 影响 |
|------|------|------|
| H1 | TeX Live 需用户手动安装 | LaTeX 编译链阻塞，模板和脚本已就绪 |
| H2 | make 未安装 | 构建脚本使用 bash 替代 |
| H11 | Dify 原生 MCP 暴露应用级接口 | 需自定义桥接服务器精细控制检索参数 |
| H13 | tikzplotlib 已废弃 | 必须用 matplotlib pgf 后端替代 |
| H14 | vibewriting(F:) 与 paper-search(C:) 不同磁盘 | 保持独立项目，MCP stdio 集成 |
| S7 | CLAUDE.md 渐进式披露 | 不超过 300 行 |
| S13 | LaTeX 每句独占一行 | 便于 git diff |

## Phase 2 新增决策（D10-D14）

### D10: 契约自愈循环

**选择**: 三层修复策略（jsonschema 校验 -> regex_healer -> llm_healer），最多 3 轮
**实现**: `src/vibewriting/contracts/validator.py`
**理由**: LLM 生成的 JSON 常有格式问题，自动修复减少人工干预；regex 快速修复常见问题，LLM 作为兜底

### D11: DAG 管线架构

**选择**: 自建轻量 DAGRunner（Kahn 拓扑排序），不依赖 Airflow/Prefect
**实现**: `src/vibewriting/pipeline/dag.py`
**特性**: 环检测、失败短路、共享上下文字典
**理由**: 项目规模不需要重量级编排工具，8 个节点的线性管线足够简单

### D12: 资产 ID 格式

**选择**: `ASSET-YYYY-NNN` 格式（如 `ASSET-2026-001`），正则约束 `^ASSET-\d{4}-\d{3,}$`
**实现**: `src/vibewriting/models/base.py` AssetBase.asset_id
**理由**: 年份前缀便于归档，序号支持三位及以上，避免冲突

### D13: 环境变量命名空间

**选择**: `VW_` 前缀统一所有项目配置（如 `VW_DIFY_API_KEY`, `VW_RANDOM_SEED`）
**实现**: `src/vibewriting/config.py` SettingsConfigDict(env_prefix="VW_")；`.env`、`.env.example`、`.mcp.json` 全部使用 `VW_DIFY_*` 前缀
**升级自**: Phase 1 的 `DIFY_*` 前缀（Post-Phase 7 修正 `.env` 中残留的无前缀 `DIFY_*` 变量）
**理由**: 避免与其他项目/工具的环境变量冲突

### D14: 确定性管线输出

**选择**: random_seed + float_precision 全局配置，numpy/random 双重种子设置
**实现**: `src/vibewriting/pipeline/cli.py`（`random.seed()` + `np.random.seed()`）
**配置**: `VW_RANDOM_SEED=42`, `VW_FLOAT_PRECISION=6`
**理由**: 科研可复现性要求，相同输入 + 相同种子 = 相同输出

## Phase 3 新增决策（D15）

### D15: BibTeX 解析器选型

**选择**: bibtexparser 2.x（>=2.0.0b7）
**否决**: pybtex、手写正则解析器、bibtexparser 1.x
**实现**: `src/vibewriting/literature/bib_manager.py`
**特性**:
- 基于 Lark 的现代解析器，支持完整 BibTeX 语法
- 结构化中间件管道（规范化字段名、清理空白、合并重复条目）
- 原子写入（先写临时文件再 rename，防止写入中断导致数据丢失）
- 幂等合并：相同 citation_key 的条目自动合并字段，不产生重复
**理由**: bibtexparser 1.x API 已过时且不维护；pybtex 偏重渲染而非解析；手写正则无法处理 BibTeX 边界情况（嵌套大括号、@string 宏等）；2.x 的中间件架构天然适合规范化管道

## Phase 4 新增决策（D16-D20）

### D16: PaperState 使用 BaseModel（非 BaseEntity）

**选择**: PaperState / SectionState / PaperMetrics 继承 Pydantic `BaseModel`，不继承 `BaseEntity`
**否决**: 继承 BaseEntity（携带 id/created_at/updated_at/tags 审计字段）
**实现**: `src/vibewriting/models/paper_state.py`
**理由**: PaperState 是全局单例状态机，不需要数据库式审计字段；BaseEntity 的 `id` 字段语义上冲突（论文只有一个状态快照）；轻量 BaseModel 序列化性能更好

### D17: SectionState 独立于 Section 模型

**选择**: 新建独立的 `SectionState` 类，不复用 `Section` 模型
**否决**: 在 Section 模型上扩展写作状态字段
**实现**: `src/vibewriting/models/paper_state.py`
**理由**: Section 模型是数据资产（继承 AssetBase），SectionState 是写作工作流状态（草稿/审阅/完成）；两者职责不同，混合会破坏 AssetBase 的 asset_id 约束语义

### D18: Quality Gates 纯正则解析

**选择**: 质量门禁使用纯正则表达式解析 LaTeX 源码，不依赖 LaTeX 解析库
**否决**: pylatexenc / TexSoup 等 LaTeX 解析库
**实现**: `src/vibewriting/writing/quality_gates.py`
**特性**: 5 种门禁（Citation Coverage, Asset Coverage, Claim Traceability, Cross-reference, Terminology Coverage）
**理由**: LaTeX 解析库对不完整草稿容错性差；正则足以匹配 `\citep{}`、`\ref{}`、`%% CLAIM_ID:` 等模式；零外部依赖，测试更简单

### D19: 增量编译 Mock Subprocess

**选择**: 增量编译模块（`incremental.py`）通过 mock subprocess 在测试中模拟 latexmk 调用
**否决**: 跳过编译测试、或要求测试环境安装 TeX Live
**实现**: `src/vibewriting/writing/incremental.py` + `tests/test_writing/test_incremental.py`
**理由**: TeX Live 是可选外部依赖（约 8GB），不强制测试环境安装；mock subprocess 保证测试确定性和速度；与 H1 约束（TeX Live 需用户手动安装）一致

### D20: Glossary/SymbolTable 不可变操作

**选择**: Glossary 和 SymbolTable 所有修改操作返回新对象，遵循不可变模式
**否决**: 直接修改内部字典
**实现**: `src/vibewriting/models/glossary.py`
**理由**: 与 PaperStateManager 的不可变模式保持一致（D16）；多 Agent 并发写作时（Phase 5）避免竞争条件；状态快照便于回滚和调试

## Phase 5 新增决策（D21-D25）

### D21: Orchestrator 单一写入者模式

**选择**: WritingOrchestrator 是唯一的文件写入者，角色 Agent 只返回 Payload
**否决**: 各 Agent 直接写入 .tex 文件
**实现**: `src/vibewriting/agents/orchestrator.py` -- WritingOrchestrator._merge_and_persist()
**理由**: 避免并发写入冲突；所有写入经过验证和合并协议；便于原子回滚（Git 安全网）；与 Phase 4 PaperStateManager 不可变模式一致

### D22: Agent 通信契约 strict 模式

**选择**: 所有 Agent 通信 Pydantic 模型使用 `ConfigDict(extra="forbid")`，禁止额外字段
**否决**: 宽松模式（`extra="allow"` 或默认 `extra="ignore"`）
**实现**: `src/vibewriting/agents/contracts.py` -- 10 个数据模型全部 strict
**理由**: 严格约束 Agent 输出格式，防止幻觉字段污染下游；Pydantic 验证错误提前暴露问题；与契约体系"JSON 是唯一事实源"原则一致

### D23: 合并冲突三类检测 + 优先级裁决

**选择**: 三类冲突检测（术语 terminology / 符号 symbol / 引用 citation）+ 硬权威优先级（glossary > agent, symbol_table > agent）
**否决**: 仅检测不裁决（全部留给人工）；基于投票的多数决
**实现**: `src/vibewriting/agents/merge_protocol.py` -- detect_conflicts() + resolve_conflicts()
**裁决规则**:
- 术语冲突: 已有 Glossary 定义优先（硬权威）
- 符号冲突: 已有 SymbolTable 定义优先（硬权威）
- 引用冲突: 自动移除无效 citation key
- 叙事冲突: 标记为需人工审阅
**理由**: 术语和符号的一致性是学术论文的硬约束，不能多数决；引用缺失有确定性解法；叙事风格确实需要人工判断

### D24: AgentExecutor Protocol 抽象

**选择**: 使用 Python `typing.Protocol`（结构化子类型）而非 ABC 基类
**否决**: 抽象基类（ABC + abstractmethod）、简单回调函数
**实现**: `src/vibewriting/agents/executor.py` -- `@runtime_checkable class AgentExecutor(Protocol)`
**变体**:
- MockExecutor: 确定性返回，用于测试
- SubAgentExecutor: Claude Code Sub-agent 占位符（NotImplementedError）
**理由**: Protocol 支持结构化子类型（duck typing），无需显式继承；`@runtime_checkable` 允许 isinstance 检查；MockExecutor 可在不引入 LLM 的情况下完整测试编排逻辑

### D25: Git 安全网路径级管辖

**选择**: Git 快照和回滚仅管辖 `paper/` + `output/` 路径，不影响源码和配置
**否决**: 全仓库级 snapshot（`git stash` 或全量 commit）
**实现**: `src/vibewriting/agents/git_safety.py` -- MANAGED_PATHS = ["paper/", "output/"]
**操作**:
- `create_snapshot_commit()`: `git add paper/ output/ && git commit -m "auto: snapshot before ..."`
- `rollback_to_snapshot()`: `git checkout <hash> -- paper/ output/`
**理由**: 编排失败只需要回滚生成的论文内容和输出资产，不应影响 Python 源码和项目配置；路径级操作更安全，不会意外覆盖开发中的代码变更

## Post-Phase 7 新增决策（D26-D28）

### D26: 双配置系统（paper_config.yaml + .env）

**选择**: 非敏感管线配置迁移到 `paper_config.yaml`，`.env` 仅保留敏感凭据和 env-only 字段
**实现**: `src/vibewriting/config.py` -- `apply_paper_config(paper_config: PaperConfig) -> Settings`
**优先级**: 环境变量 > paper_config.yaml > 默认值（仅当 Settings 字段仍为默认值时 YAML 才生效）
**迁移字段**: `random_seed`, `float_precision`, `dedup_threshold`, `compile_max_retries`, `compile_timeout_sec`, `enable_ai_disclosure`
**不可变**: 使用 `model_copy(update=...)` 返回新 Settings 实例，不修改全局 settings 单例
**理由**: 管线参数是每篇论文独立的非敏感配置，放在 YAML 中便于版本控制和复现；API 密钥等敏感凭据仍通过 `.env` 管理不入库；优先级设计确保环境变量始终可覆盖 YAML

### D27: natbib_style 配置链统一

**选择**: `PaperConfig.natbib_style` 默认值 `unsrtnat`（按引用顺序排列），贯穿 PaperConfig -> incremental.py -> main.tex
**否决**: `plainnat`（按作者字母排序，不符合多数中文论文惯例）
**实现**: `config_paper.py` 默认值 + `incremental.py` 的 `generate_draft_main()`/`write_draft_main()`/`compile_single_section()` 新增 `natbib_style` 参数
**理由**: `unsrtnat` 按引用出现顺序编号，与 `\citep{}`/`\citet{}` 编号引用风格一致，符合中文科技论文习惯

### D28: paper/.gitignore 编译产物隔离

**选择**: 在 `paper/` 目录新增 `.gitignore`，忽略直接 xelatex 编译产生的残留文件
**实现**: `paper/.gitignore` -- 忽略 `*.aux`, `*.log`, `*.synctex.gz`, `*.pdf`, `*.bbl`, `*.blg` 等
**理由**: 用户可能直接运行 `xelatex main.tex`（不通过 latexmk），产物散落在 `paper/` 根目录；正确的构建产物始终通过 latexmk 输出到 `paper/build/`；gitignore 防止这些残留被误提交

## 依赖列表

### 运行时依赖（pyproject.toml [project].dependencies）

| 包 | 版本约束 | 用途 |
|----|---------|------|
| pandas | >=2.2,<3.0 | 数据处理 |
| numpy | >=1.26,<2.0 | 数值计算 |
| matplotlib | >=3.10 | 图表生成（pgf 后端） |
| seaborn | >=0.13 | 统计可视化 |
| scipy | >=1.14 | 科学计算 |
| statsmodels | >=0.14 | 统计建模 |
| pydantic | >=2.0 | 数据模型 |
| pydantic-settings | >=2.0 | 配置管理（VW_ env 前缀） |
| httpx | latest | HTTP 客户端 |
| python-dotenv | latest | 环境变量加载 |
| tabulate | >=0.9 | 表格格式化 |
| jinja2 | >=3.1 | 模板引擎（booktabs 表格） |
| jsonschema | >=4.0 | 契约验证（Draft 2020-12）[Phase 2 新增] |
| typer | >=0.9 | CLI 框架（管线入口）[Phase 2 新增] |
| bibtexparser | >=2.0.0b7 | BibTeX 解析/规范化/合并 [Phase 3 新增] |

### 可选依赖

| 组 | 包 | 用途 |
|----|----|----|
| perf | polars >=1.30, pyarrow >=15.0 | 大数据集性能优化 |
| latex | pylatex >=1.4 | LaTeX 文档生成辅助 |

### 开发依赖（[dependency-groups] dev）

| 包 | 用途 |
|----|------|
| pytest >=8.0 | 测试框架 |
| pytest-cov >=5.0 | 覆盖率报告 [Phase 2 新增] |
| pytest-asyncio >=0.23 | 异步测试支持 |
| hypothesis >=6.0 | 基于属性的测试 [Phase 2 新增] |
| ruff >=0.14 | 代码检查 |
| mypy >=1.10 | 类型检查 |

### Dify 桥接服务器依赖（PEP 723 内联）

| 包 | 用途 |
|----|------|
| mcp[cli] >=1.0 | FastMCP 框架 |
| httpx >=0.27 | 异步 HTTP 客户端 |
| python-dotenv >=1.0 | .env 文件加载（解决 MCP 环境变量插值失败） |
