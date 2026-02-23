# 开发指南

## 环境搭建

### 前置条件

- Python >= 3.11（推荐 3.12）
- uv（Python 依赖管理）
- Git
- Git Bash（Windows 下执行 build.sh）

### 可选前置条件

- TeX Live（LaTeX 编译，约 8GB）
- Dify 实例（知识库检索）

### 初始化步骤

```bash
# 1. 克隆并进入项目
cd F:/vibewriting

# 2. 安装 Python 依赖
uv sync

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填写必要的 API 密钥

# 4. 验证环境
uv run scripts/validate_env.py
```

## 构建流程

### LaTeX 编译（需 TeX Live）

```bash
bash build.sh build      # 编译论文 -> paper/build/main.pdf
bash build.sh watch       # 监视模式，文件变更自动重编译
bash build.sh clean       # 清理 paper/build/ 中的编译产物
bash build.sh check       # 运行 checkcites 检查引用完整性
bash build.sh doi2bib DOI # 通过 DOI 获取 BibTeX 条目
```

编译产物输出到 `paper/build/`（已 gitignored）。

### Python 测试

```bash
uv run pytest              # 运行所有测试
uv run pytest -v           # 详细输出
uv run pytest tests/       # 指定测试目录
```

### 代码质量

```bash
uv run ruff check src/     # 代码检查
uv run mypy src/            # 类型检查
```

## 环境验证

```bash
uv run scripts/validate_env.py         # 彩色控制台输出
uv run scripts/validate_env.py --json  # JSON 机器可读报告
```

退出码语义（D5 决策）：
- `0` -- 所有检查通过
- `1` -- 必需依赖缺失（Python 包、git、uv、.env 文件）
- `2` -- 仅可选依赖缺失（TeX Live、Dify 凭据、polars/pyarrow）

### 检查项目

**必需项**：Python 版本、pandas/matplotlib/scipy/pydantic 可导入、git、uv、.env 文件
**可选项**：xelatex/latexmk/bibtex/checkcites（TeX Live）、Dify 凭据、polars/pyarrow（性能优化包）

## 工作流纪律

### LaTeX 编辑规则

- 修改 `.tex` 文件后运行 `bash build.sh build` 验证编译
- 修改 `.bib` 文件后运行 `bash build.sh check` 验证引用
- 每句话独占一行（便于 git diff 和审查）
- 章节使用 `\input{}`（非 `\include{}`），不强制换页
- `.bib` 文件强制 UTF-8 编码，引用键仅 ASCII 字符

### Python 编辑规则

- 修改后运行 `uv run pytest`
- 数据处理管道修改后验证输出确定性
- 依赖变更后运行 `uv sync` 并提交 `uv.lock`

### 引用规则

- `\citep{key}` -- 括号引用（如 [1]）
- `\citet{key}` -- 文本引用（如 Author [1]）
- 每个 claim 必须有引用或数据支撑
- 数学公式使用 amsmath 环境（equation, align），禁止 `$$...$$`

## 目录职责

| 目录 | 放什么 | 不放什么 |
|------|--------|---------|
| `paper/sections/` | .tex 章节文件 | 图片、数据 |
| `paper/bib/` | .bib 参考文献 | 非 UTF-8 文件 |
| `paper/figures/` | 论文中引用的图片 | 生成的图表（用 output/figures/） |
| `src/vibewriting/` | Python 源码 | 脚本、配置文件 |
| `data/raw/` | 原始数据文件 | 处理后的数据 |
| `data/processed/` | 清洗后数据 | 原始数据 |
| `output/figures/` | 生成的图表（.pdf/.pgf/.png） | 手绘图 |
| `output/tables/` | 生成的 LaTeX 表格（.tex） | 手写表格 |
| `scripts/` | 工具脚本 | 业务逻辑代码 |

## 安全边界

- 不修改全局配置或系统字体
- 不泄露 `.env` 中的 API 密钥（日志和输出中屏蔽）
- 不执行未经确认的 `git push`
- 不直接 import paper-search 代码（通过 MCP 协议集成）
- 不安装全局 Python 包（所有依赖通过 uv 管理）
