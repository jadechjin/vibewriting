# Team Research: vibewriting Bug 修复（4 个问题）

## 增强后的需求

**目标**：修复 vibewriting 项目在端到端写作流程中暴露的 4 个 bug，具体为：

1. **Bug 1 — 文献检索优先级错误**：`/vibewriting-literature` Skill 执行时，Claude Code Agent 自动调用内置 `web_search` 工具代替了 MCP 学术检索工具。期望策略：三种检索同时执行，但优先级为 `Dify 知识库 > paper-search MCP > WebSearch`。其中 Dify 检索结果可直接使用于文章；paper-search 和 WebSearch 结果为补充来源，需用户确认后上传 Dify 才可用于内容。

2. **Bug 2 — heredoc 中的 regex 转义问题**：在 `/vibewriting-paper` 会话（约 1h 前，224 messages）中，Claude Code 提示发现 heredoc 中的 regex 转义问题。根本原因推断为：在 bash 双引号 heredoc（`<<EOF` 不带单引号）中嵌入含有 `\\d`, `\\w`, `\\s` 等双反斜杠的 JSON regex 模式时，bash 将 `\\` 解释为单个 `\`，导致 JSON 中 `\\d` 变为 `\d`（无效 JSON 转义）。此外，`regex_healer.py::fix_illegal_escapes()` 存在将有效 JSON `\\d` 序列错误二次转义为 `\\\\d` 的 bug。

3. **Bug 3 — PDF 缺少参考文献章节**：编译输出的 PDF 无参考文献章节。TeX Live 安装状态不确定，需提前修复编译配置以备安装后即可使用。根本原因推断为：latexmkrc 缺少 `$bibtex_use` 和 BIBINPUTS 路径配置，或 `compiler.py` 中 `-halt-on-error` 旗标在首次编译时阻止了 bibtex 运行。

4. **Bug 4 — 文献引用显示 [?]**：PDF 中 `\citep{}` 和 `\citet{}` 引用显示为 `[?]`。与 Bug 3 同源 —— bibtex 未成功运行导致 .bbl 文件未生成，natbib 无法解析引用键。

**技术约束**：
- Python 3.12 + uv 环境，Windows 11
- LaTeX 编译链：XeLaTeX + latexmk + BibTeX + natbib (unsrtnat)
- 编译产物：`paper/build/main.pdf`
- .bib 文件：`paper/bib/references.bib`（UTF-8，25 条 auto-generated 条目）

---

## 约束集

### 硬约束

- **[HC-1]** `search.py::search_literature()` 当前调用顺序是 `paper-search → Dify`（均通过 `_call_mcp_tool()` 占位符），需改为 `Dify → paper-search → WebSearch(仅 Skill 层面标注为最低优先级)`。来源：代码分析 + 用户确认

- **[HC-2]** `RawLiteratureRecord.source` 字段的已知合法值为 `paper-search|dify-kb`，若要支持 WebSearch 降级，需在 `models.py` 中添加 `web-search` 选项。来源：Codex 探索

- **[HC-3]** SKILL.md（`vibewriting-literature`）必须明确告知 Claude **禁止使用内置 `WebSearch` 工具**，应只通过 MCP 工具检索；所有三种检索源同时执行（并行），Dify 结果直接可用，其余需用户确认。来源：用户确认

- **[HC-4]** Dify 检索到的内容可直接用于论文撰写；paper-search 和 WebSearch 结果只能作为候选，须用户确认后上传 Dify 方可使用。来源：用户明确要求

- **[HC-5]** `paper/main.tex` 已有正确的 `\bibliographystyle{unsrtnat}` + `\bibliography{bib/references}`，位置正确（在 `conclusion` 之后、`appendix` 之前）。来源：文件读取

- **[HC-6]** `latexmkrc` 使用 `$out_dir = 'build'` + `$aux_dir = 'build'`，BibTeX 以 CWD=`paper/` 运行 `bibtex build/main`，应能找到 `paper/bib/references.bib`，但缺少 `$bibtex_use = 2` 强制运行设置。来源：文件读取 + Gemini 探索

- **[HC-7]** `compiler.py::compile_full()` 使用 `-halt-on-error` 旗标，可能在首次编译遇到 undefined reference 时阻止 bibtex 运行（bibtex 需在 xelatex 第一遍后才运行）。来源：代码分析

- **[HC-8]** bash heredoc `<<'EOF'`（单引号）不执行任何变量或转义解释，`<<EOF`（双引号）会解释 `\\` → `\`，导致 JSON 中 `\\d` 变成 `\d`（无效 JSON 转义）。含 regex 模式的 JSON 必须用 `<<'EOF'` heredoc。来源：bash 规范 + Codex 探索

- **[HC-9]** `regex_healer.py::fix_illegal_escapes()` 存在 bug：当处理 Python 字符串 `\d`（来自 JSON 的 `\\d`）时，因 `d` 不在 `valid_escapes` 中，会错误将其替换为 `\\`（即 JSON 中变成 `\\\\d`），破坏原本有效的 regex 序列。来源：代码逐行分析

- **[HC-10]** 修改 `search_literature()` 优先级顺序不能破坏现有 835 条测试（尤其 `tests/test_literature/test_search.py` 中 6 条测试）。来源：项目状态文档

### 软约束

- **[SC-1]** Dify 检索采用 `top_k=5, search_method="hybrid_search"` 默认参数，paper-search 采用 `max_results=20`，两者并行时应在合并后去重（利用现有三层去重管道）。来源：代码规范

- **[SC-2]** SKILL.md 文档与 `search.py` 代码逻辑须保持一致，两者都要更新以反映新的优先级策略。来源：代码规范

- **[SC-3]** `latexmkrc` 添加 `$bibtex_use = 2` 时应同时保留现有 `$pdf_mode = 5`、`$max_repeat = 5` 等配置，不破坏现有编译链。来源：代码规范

- **[SC-4]** 修复 `fix_illegal_escapes()` 时需保留其他修复功能（`strip_markdown_fences`、`fix_trailing_commas`、`fix_single_quotes`、`fix_unclosed_strings`），只修复双反斜杠逻辑。来源：代码规范

- **[SC-5]** `compiler.py::compile_full()` 移除 `-halt-on-error` 或替换为 `-interaction=nonstopmode`（已有），让 latexmk 能完整跑完多轮（xelatex + bibtex + xelatex）。来源：LaTeX 编译最佳实践

- **[SC-6]** Dify 检索结果在 `SearchResult.records` 中排在前面（`source == "dify-kb"` 的记录优先），保持可审计性。来源：用户要求可观测

### 依赖关系

- **[DEP-1]** `src/vibewriting/literature/search.py` → `src/vibewriting/literature/dedup.py`：search 调用顺序改变后，dedup 仍接受所有来源的 `RawLiteratureRecord` 列表，兼容。

- **[DEP-2]** `.claude/skills/vibewriting-literature/SKILL.md` → `src/vibewriting/literature/search.py`：SKILL.md 定义 Agent 行为，`search.py` 定义代码行为，两者须同步更新。

- **[DEP-3]** `paper/latexmkrc` → `paper/bib/references.bib`：latexmk 通过 bibtex 读取 .bib 文件，latexmkrc 的 `$bibtex_use` 和 BIBINPUTS 配置影响 bibtex 能否找到 .bib 文件。

- **[DEP-4]** `src/vibewriting/latex/compiler.py` → `paper/latexmkrc`：`compiler.py` 调用 `latexmk` 并使用 `latexmkrc` 配置；`compiler.py` 的 `-halt-on-error` 和 `-output-directory=build` 与 latexmkrc 的 `$out_dir='build'` 之间存在冗余但不冲突。

- **[DEP-5]** `src/vibewriting/contracts/healers/regex_healer.py` → `src/vibewriting/contracts/validator.py`：validator 调用 heal() 管道，修复 `fix_illegal_escapes` 不会影响其他修复器。

### 风险

- **[RISK-1]** Bug 1 修复：若三种检索并行运行，Dify 失败不影响 paper-search 返回结果，但现有测试中 Mock 了 paper-search 优先的顺序，需更新 Mock 期望。缓解：只修改函数内部调用顺序，接口不变。

- **[RISK-2]** Bug 2 修复：`fix_illegal_escapes` 修复会改变对合法 `\\d` 序列的处理，若有测试依赖于当前错误行为，需同步修复测试。缓解：修复前先运行测试确认 baseline。

- **[RISK-3]** Bug 3/4 修复：TeX Live 安装状态不确定，所有编译相关修复无法立即验证。缓解：同时修复 `latexmkrc` 和 `compiler.py`，确保任一 TeX Live 安装状态下的配置都是正确的。

- **[RISK-4]** `compiler.py` 移除 `-halt-on-error` 可能导致含语法错误的 .tex 文件编译"成功"但 PDF 内容不完整。缓解：保留 `$max_repeat = 5` 让 latexmk 多轮迭代，且自愈循环仍会解析日志中的错误。

- **[RISK-5]** Gemini CLI 遭遇 429 限流，前端探索结果部分不完整，但关键约束已由 Codex 和本地代码分析覆盖。

---

## 成功判据

- **[OK-1]** 运行 `/vibewriting-literature` 时，日志中首先出现 `retrieve_knowledge` MCP 调用，而非 `web_search`；paper-search MCP 调用出现在 Dify 之后。
- **[OK-2]** `SearchResult.records` 中 `source == "dify-kb"` 的记录排在所有 `source == "paper-search"` 记录之前。
- **[OK-3]** 输入 `{"pattern": "^EC-\\d{4}-\\d{3}$"}` 经过 `regex_healer.heal()` 后保持不变（不被二次转义）。
- **[OK-4]** 含 regex 模式的 bash heredoc 使用 `<<'EOF'` 格式，JSON 中 `\\d` 在 heredoc 内保持为 `\\d`。
- **[OK-5]** 安装 TeX Live 后运行 `bash build.sh build`，`paper/build/main.log` 中出现 bibtex 成功运行日志，PDF 包含参考文献章节。
- **[OK-6]** PDF 中所有 `\citep{}` 和 `\citet{}` 引用显示为 `[1]`, `[2]` 等编号，而非 `[?]`。
- **[OK-7]** 所有 835 条现有测试仍然通过（`uv run pytest`）。

---

## 开放问题（已解决）

- Q1: "自动调用 WebSearch"是代码层面还是 Agent 运行时？
  → A: Agent 运行时自动使用内置 web_search 工具（Skill 层面问题）
  → 约束：[HC-3] 需在 SKILL.md 中明确禁止

- Q2: "Dify 优先"是串行还是并行？
  → A: 三种源同时并行检索，Dify 结果排最前；Dify 内容直接可用，其余需用户确认
  → 约束：[HC-3], [HC-4], [SC-6]

- Q3: Bug 2 heredoc 具体位置？
  → A: `/vibewriting-paper` 会话（224 messages）中 bash heredoc 使用了 `<<EOF`（未带引号），包含 JSON regex 模式时 `\\d` 被 bash 解为 `\d`；同时 `regex_healer.py::fix_illegal_escapes()` 有独立的双反斜杠处理 bug
  → 约束：[HC-8], [HC-9]

- Q4: TeX Live 是否已安装？
  → A: 不确定，需提前修复配置以备安装后即用
  → 约束：[HC-6], [HC-7], [SC-5]

---

## 受影响文件（修复范围）

| 文件 | Bug | 修改类型 |
|------|-----|---------|
| `src/vibewriting/literature/search.py` | Bug 1 | 调整 Dify/paper-search 调用顺序，Dify 优先 |
| `.claude/skills/vibewriting-literature/SKILL.md` | Bug 1 | 明确禁止 WebSearch，更新优先级说明 |
| `src/vibewriting/literature/models.py` | Bug 1 | 添加 `web-search` 来源类型（可选） |
| `src/vibewriting/contracts/healers/regex_healer.py` | Bug 2 | 修复 `fix_illegal_escapes()` 双反斜杠处理逻辑 |
| `paper/latexmkrc` | Bug 3/4 | 添加 `$bibtex_use = 2`，可选添加 BIBINPUTS |
| `src/vibewriting/latex/compiler.py` | Bug 3/4 | 移除 `-halt-on-error`，让 latexmk 完整运行 |
| `paper/main.tex`（可能） | Bug 3/4 | 确认 bibliography 命令位置正确（已正确，无需改） |

---

*研究完成。运行 `/clear` 后执行 `/ccg:team-plan bug-fix` 开始规划。*

当前上下文使用量：约 85%（建议执行 `/clear` 后再进行规划阶段）
