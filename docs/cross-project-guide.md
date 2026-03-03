# 跨项目知识迁移指南

本指南帮助你在多个论文项目之间复用 LaTeX 模板、`.bib` 文件、图表模板和宏定义，减少重复工作。

---

## Claude Code Additional Directories 配置

如果你在多个项目中使用 vibewriting，可以通过 Claude Code 的 Additional Directories 功能让 Claude 访问多个项目目录，从而跨项目复用资源和上下文。

### 配置方法

在 Claude Code 的设置文件中配置附加目录（`~/.claude/settings.json` 或项目级 `.claude/settings.json`）：

```json
{
  "additionalDirectories": [
    "/path/to/paper-project-a",
    "/path/to/paper-project-b",
    "/path/to/shared-latex-templates"
  ]
}
```

### 推荐的目录结构

建议创建一个共享资源仓库，集中管理可复用资源：

```
shared-latex-resources/
├── bib/
│   ├── common.bib          # 跨项目共用的基础参考文献
│   └── domain-specific.bib # 特定领域的文献库
├── macros/
│   ├── math-macros.tex     # 数学符号宏定义
│   └── abbrev.tex          # 缩写定义
├── templates/
│   ├── ctexart-zh.tex      # 中文论文模板
│   ├── ieee-en.tex         # IEEE 英文论文模板
│   └── custom-preamble.tex # 自定义导言区
└── figures/
    └── templates/           # 图表 Python 模板
```

将该目录加入 Additional Directories 后，在任意项目中都可以引用其中的资源。

---

## 从历史论文迁移 LaTeX 模式

### 提取可复用结构

如果已有写好的论文，可以提取其结构作为新项目的模板：

1. **识别可复用章节结构**

   查看历史论文的章节划分，在新项目的 `paper_config.yaml` 中沿用：

   ```yaml
   # 从历史论文继承的章节结构
   sections:
     - 引言
     - 相关工作
     - 问题定义与形式化
     - 方法
     - 实验设置
     - 实验结果与分析
     - 结论与展望
   ```

2. **提取导言区设置**

   将历史论文中经过调试的导言区保存为共享模板，新项目通过 `\input{}` 引入：

   ```latex
   % paper/main.tex
   \documentclass{ctexart}
   \input{/path/to/shared/custom-preamble.tex}  % 引入共享导言区

   \begin{document}
   \input{sections/introduction.tex}
   \end{document}
   ```

3. **复制经过验证的自定义命令**

   将常用的自定义命令整理到独立的 `.tex` 文件中：

   ```latex
   % shared/macros/math-macros.tex
   \newcommand{\R}{\mathbb{R}}           % 实数集
   \newcommand{\norm}[1]{\|#1\|}         % 范数
   \newcommand{\argmax}{\operatorname{argmax}}
   \newcommand{\argmin}{\operatorname{argmin}}
   ```

---

## 复用 .bib 文件和参考文献

### 方法一：共享 .bib 文件（推荐）

创建一个跨项目共享的 `.bib` 文件，新项目直接引用：

```latex
% paper/main.tex 中的参考文献声明
\bibliography{
  bib/references,              % 本项目特有的文献
  /path/to/shared/bib/common   % 共享文献库（使用绝对路径）
}
```

> **注意**：`.bib` 文件必须使用 UTF-8 编码，引用键（cite key）仅使用 ASCII 字符。

### 方法二：合并 .bib 文件

将历史论文的 `.bib` 文件合并到新项目：

```bash
# 合并多个 .bib 文件（去除重复项）
cat old-paper/bib/references.bib >> paper/bib/references.bib

# 使用 bibtool 去重（如果已安装）
bibtool -d -i paper/bib/references.bib -o paper/bib/references.bib
```

合并后运行检查：

```bash
bash build.sh check  # 运行 checkcites 检查引用完整性
```

### 方法三：DOI 批量导入

对于新项目需要引用的文献，使用构建脚本的 DOI 转换功能：

```bash
# 单个 DOI 转换
bash build.sh doi2bib 10.1145/1234567.1234568

# 批量处理（创建 DOI 列表文件）
while IFS= read -r doi; do
    bash build.sh doi2bib "$doi" >> paper/bib/references.bib
done < doi-list.txt
```

### .bib 格式规范

跨项目复用时，统一 `.bib` 格式可减少冲突：

```bibtex
% 引用键格式：FirstAuthorLastNameYYYYKeyword
@article{LeCun2015DeepLearning,
  author    = {LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey},
  title     = {Deep learning},
  journal   = {Nature},
  year      = {2015},
  volume    = {521},
  number    = {7553},
  pages     = {436--444},
  doi       = {10.1038/nature14539},
}
```

---

## 图表模板迁移

### Python 图表模板复用

vibewriting 使用 matplotlib pgf 后端生成图表，图表代码通常高度可复用。

**1. 提取通用样式配置**

将 matplotlib 样式设置提取为共享配置文件：

```python
# shared/figures/style.py

import matplotlib
import matplotlib.pyplot as plt

def apply_paper_style():
    """应用论文图表标准样式。"""
    matplotlib.use("pgf")
    plt.rcParams.update({
        "pgf.texsystem": "xelatex",
        "font.family": "serif",
        "font.size": 10,
        "axes.labelsize": 10,
        "axes.titlesize": 10,
        "legend.fontsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "figure.figsize": (3.5, 2.5),   # 单栏图表宽度（英寸）
        "figure.dpi": 300,
    })
```

**2. 新项目中引用共享样式**

```python
import sys
sys.path.insert(0, "/path/to/shared/figures")
from style import apply_paper_style

apply_paper_style()
# 继续绘制图表...
```

**3. 迁移历史图表代码**

历史论文中的图表生成脚本通常可以直接复制到新项目的 `src/vibewriting/visualization/` 下，修改数据路径即可使用。

### LaTeX 表格模板复用

vibewriting 使用 Jinja2 模板生成 LaTeX 表格，模板文件位于 `src/vibewriting/visualization/templates/`。

**将表格模板提取为共享资源**：

```
shared-latex-resources/
└── table-templates/
    ├── comparison_table.tex.j2    # 方法对比表模板
    ├── ablation_table.tex.j2      # 消融实验表模板
    └── results_table.tex.j2       # 实验结果表模板
```

在新项目的可视化代码中引用共享模板：

```python
from jinja2 import Environment, FileSystemLoader

# 加载共享模板目录
env = Environment(
    loader=FileSystemLoader([
        "src/vibewriting/visualization/templates",          # 项目本地模板
        "/path/to/shared-latex-resources/table-templates",  # 共享模板
    ])
)

template = env.get_template("comparison_table.tex.j2")
```

---

## 配置文件版本化策略

### 为每个论文项目维护独立的 paper_config.yaml

建议在 Git 中跟踪 `paper_config.yaml`，不同论文项目使用不同的配置文件：

```bash
# 在 git 中查看历史项目的配置
git log --oneline paper_config.yaml

# 查看特定版本的配置
git show HEAD~5:paper_config.yaml
```

### 使用 Git 分支管理多篇论文

如果在同一仓库中管理多篇论文（不推荐，但可行）：

```bash
git checkout -b paper/medical-nlp        # 医学 NLP 论文分支
git checkout -b paper/image-segmentation # 图像分割论文分支
```

每个分支维护独立的 `paper_config.yaml` 和 `paper/` 目录。

---

## 迁移检查清单

从历史论文迁移到新项目时，建议按以下顺序操作：

- [ ] 复制并更新 `paper_config.yaml`（修改 `topic`、`sections`、`language`）
- [ ] 迁移或合并 `.bib` 文件到 `paper/bib/references.bib`
- [ ] 运行 `bash build.sh check` 验证引用完整性
- [ ] 复制可复用的 LaTeX 宏定义到 `paper/preamble.tex`（如有）
- [ ] 迁移图表 Python 脚本，更新数据路径
- [ ] 迁移 Jinja2 表格模板（如有自定义模板）
- [ ] 运行 `uv run scripts/validate_env.py` 确认环境配置正常
- [ ] 运行 `bash build.sh build` 验证 LaTeX 编译正常

---

## 注意事项

1. **绝对路径 vs 相对路径**：在 LaTeX 中引用外部资源时，优先使用相对路径，避免在不同机器上路径失效
2. **编码统一**：所有 `.tex` 和 `.bib` 文件强制使用 UTF-8 编码
3. **字体兼容性**：跨平台迁移时，检查字体是否在目标系统可用（见 [FAQ：字体缺失](./faq.md)）
4. **包版本差异**：不同 TeX Live 版本的包 API 可能有差异，迁移后建议完整编译验证
5. **引用键唯一性**：合并 `.bib` 文件时，检查引用键是否有冲突（重名条目会被静默覆盖）
