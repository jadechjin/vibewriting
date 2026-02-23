# 技术决策速查表

**来源**: `openspec/changes/archive/2026-02-23-project-foundation-architecture/design.md`

## 9 项核心决策（D1-D9）

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
**实现**: `scripts/dify-kb-mcp/server.py` 凭据缺失时返回结构化错误，不崩溃
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

**选择**: `.env` + python-dotenv
**实现**: `src/vibewriting/config.py` 加载 `.env`，`.env.example` 提交 Git
**理由**: 标准做法，密钥不进版本控制

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
| pydantic-settings | >=2.0 | 配置管理 |
| httpx | latest | HTTP 客户端 |
| python-dotenv | latest | 环境变量加载 |
| tabulate | >=0.9 | 表格格式化 |
| jinja2 | >=3.1 | 模板引擎 |

### 可选依赖

| 组 | 包 | 用途 |
|----|----|----|
| perf | polars >=1.30, pyarrow >=15.0 | 大数据集性能优化 |
| latex | pylatex >=1.4 | LaTeX 文档生成辅助 |

### 开发依赖（[dependency-groups] dev）

| 包 | 用途 |
|----|------|
| pytest >=8.0 | 测试框架 |
| pytest-asyncio >=0.23 | 异步测试支持 |
| ruff >=0.14 | 代码检查 |
| mypy >=1.10 | 类型检查 |

### Dify 桥接服务器依赖（PEP 723 内联）

| 包 | 用途 |
|----|------|
| mcp[cli] >=1.0 | FastMCP 框架 |
| httpx >=0.27 | 异步 HTTP 客户端 |
