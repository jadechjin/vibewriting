# Team Plan: bug-fix

## 概述

修复 vibewriting 项目端到端写作流程中暴露的 4 个 bug：文献检索优先级错误、regex_healer 双反斜杠处理 bug、PDF 缺少参考文献、引用显示 [?]。

## Codex 分析摘要

Codex 完成了全部 6 个受影响文件的代码审查，确认：
1. Bug 1（search.py）：当前 `search_literature()` 串行调用 paper-search → Dify，需改为 `asyncio.gather` 并行 + Dify 优先排序。`models.py` 的 `source` Literal 需扩展 `web-search`。
2. Bug 2（regex_healer.py）：`fix_illegal_escapes()` 逐字符扫描时未将 `\\`（双反斜杠序列）作为原子单元处理，导致 `\\d` 被拆开处理后丢失一个反斜杠。修复方案：遇到 `\\` 时整体保留并跳过 2 个字符。
3. Bug 3/4（latexmkrc + compiler.py）：`latexmkrc` 缺少 `$bibtex_use = 2`，`compile_full()` 的 `-halt-on-error` 在首次编译遇到 undefined citation 时终止后续 bibtex 运行。
4. 基线测试验证：50 条直接相关测试已通过（test_search 6t + test_contracts 22t + test_compiler 9t + 其他 13t）。

推荐方案 A（最小侵入修复），改动 6 个指定文件，不引入新架构。

## Gemini 分析摘要

Gemini CLI 因 API Key 配置问题（exit 41）连续失败。降级为本地分析 + Codex 覆盖。

SKILL.md 修改方向（本地分析）：
- 在文档顶部添加 "禁止使用内置 WebSearch 工具" 约束
- 调整 Phase 1 检索步骤为并行策略（Dify + paper-search 同时发起）
- 标注来源可信度差异：Dify 结果直接可用，paper-search/web-search 结果需用户确认

## 技术方案

### 核心决策

1. **并行检索**：`asyncio.create_task` + `asyncio.gather(return_exceptions=True)` 同时发起 Dify 和 paper-search
2. **优先级排序**：去重后按 `{"dify-kb": 0, "paper-search": 1, "web-search": 2}` 稳定排序
3. **双反斜杠原子处理**：遇到 `\\` 时整体跳过 2 字符，保留合法 JSON 转义
4. **BibTeX 强制运行**：`$bibtex_use = 2` + 移除 `-halt-on-error`

## 子任务列表

### Task 1: 修复文献检索优先级（search.py + models.py）
- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/literature/search.py`（重写 `search_literature()` 函数体）
  - `src/vibewriting/literature/models.py`（扩展 `source` Literal 类型）
- **依赖**: 无
- **实施步骤**:
  1. 在 `search.py` 顶部添加 `import asyncio`
  2. 重写 `search_literature()` 函数（约 184-231 行）：
     - 使用 `asyncio.create_task()` 并行发起 `search_via_paper_search` 和 `search_via_dify`
     - 使用 `asyncio.gather(return_exceptions=True)` 等待两者完成
     - 合并结果时 `dify_records` 排在 `ps_records` 之前
     - 去重后按 source 优先级稳定排序：`{"dify-kb": 0, "paper-search": 1, "web-search": 2}`
     - 错误处理保持与现有语义一致（分别记录 Dify/paper-search 错误）
  3. 在 `models.py` 的 `RawLiteratureRecord.source` 字段扩展：
     - `source: Literal["paper-search", "dify-kb", "web-search"] = "paper-search"`
  4. 更新现有测试 `tests/test_literature/test_search.py`：
     - `test_orchestrator_combines_sources`：确认 mock 仍然工作（search_via_paper_search 和 search_via_dify 已经是分别 mock 的，无需改动）
     - 新增 `test_orchestrator_prioritizes_dify`：断言 dify-kb 记录在 paper-search 之前
     - 新增 `test_orchestrator_parallel_execution`：验证两个来源并行执行
  5. 运行 `uv run pytest tests/test_literature/test_search.py -v` 验证
- **验收标准**:
  - `SearchResult.records` 中 `source=="dify-kb"` 记录排在 `source=="paper-search"` 之前
  - 所有现有 test_search.py 测试通过
  - 新增 2+ 测试覆盖优先级和并行行为

### Task 2: 修复 regex_healer 双反斜杠 bug
- **类型**: 后端
- **文件范围**:
  - `src/vibewriting/contracts/healers/regex_healer.py`（重写 `fix_illegal_escapes()` 函数体）
- **依赖**: 无
- **实施步骤**:
  1. 替换 `fix_illegal_escapes()` 函数（约 37-60 行），核心逻辑：
     - 字符串内遇到 `\\`（双反斜杠）：整体保留 `\\` 并 `i += 2` 跳过两个字符
     - 字符串内遇到单 `\` + 合法转义字符（`"\\bfnrtu/`）：保留 `\`
     - 字符串内遇到单 `\` + 非法字符（如 `d`）：替换为 `\\`（即修复为合法 JSON 转义）
     - 字符串尾部孤立 `\`：补成 `\\`
  2. 新增测试到相关测试文件：
     - `test_fix_illegal_escapes_preserves_double_backslash`：输入 `{"pattern":"^EC-\\\\d{4}-\\\\d{3}$"}` 经处理后保持不变且可 `json.loads`
     - `test_fix_illegal_escapes_repairs_invalid_single_backslash`：输入含非法 `\d` 的 JSON 被修复为 `\\d`
  3. 运行 `uv run pytest tests/test_contracts/ -v` 验证
- **验收标准**:
  - `{"pattern": "^EC-\\\\d{4}-\\\\d{3}$"}` 经 `heal()` 后保持不变
  - 非法 `\d` 被修复为 `\\d`
  - 现有 regex_healer 相关测试全部通过

### Task 3: 修复 LaTeX BibTeX 编译问题
- **类型**: 后端（编译配置）
- **文件范围**:
  - `paper/latexmkrc`（添加 `$bibtex_use = 2`）
  - `src/vibewriting/latex/compiler.py`（`compile_full()` 移除 `-halt-on-error`）
- **依赖**: 无
- **实施步骤**:
  1. 编辑 `paper/latexmkrc`，在 `$bibtex = 'bibtex %O %B';` 之后添加：
     ```perl
     $bibtex_use = 2;
     ```
  2. 编辑 `src/vibewriting/latex/compiler.py` 的 `compile_full()` 函数（约 42-46 行）：
     - 从 `cmd` 列表中移除 `"-halt-on-error"`
     - 最终 cmd：`["latexmk", "-xelatex", "-interaction=nonstopmode", "-output-directory=build", str(main_tex)]`
  3. 新增测试：
     - `test_compile_full_no_halt_on_error`：patch `subprocess.run`，断言 cmd 中不含 `-halt-on-error`
     - `test_latexmkrc_has_bibtex_use`：读取 `paper/latexmkrc` 文件，断言包含 `$bibtex_use = 2`
  4. 运行 `uv run pytest tests/test_latex/test_compiler.py -v` 验证
- **验收标准**:
  - `latexmkrc` 包含 `$bibtex_use = 2;`
  - `compile_full()` 的 cmd 不含 `-halt-on-error`
  - 安装 TeX Live 后运行 `bash build.sh build` 应生成含参考文献的 PDF（当前无法验证，配置预先就绪）

### Task 4: 更新 SKILL.md 文档
- **类型**: 文档
- **文件范围**:
  - `.claude/skills/vibewriting-literature/SKILL.md`
- **依赖**: 无
- **实施步骤**:
  1. 在 `## Important` 部分顶部添加：
     ```
     - **Do NOT use the built-in `WebSearch` / `web_search` tool.** All retrieval must go through MCP tools (retrieve_knowledge, search_papers).
     ```
  2. 在 `## Important` 部分添加来源可信度说明：
     ```
     - **Source trust levels**: Dify knowledge base results can be used directly in drafts. Paper-search results are supplementary and require user confirmation before use in content.
     ```
  3. 重写 Phase 1 步骤 1-4 为并行策略：
     - 步骤 1: 同时调用 `retrieve_knowledge(query)` (Dify) 和 `search_papers(query)` (paper-search)
     - 步骤 2: Dify 结果标记为 "直接可用"（trusted），paper-search 结果标记为 "待确认"（supplementary）
     - 步骤 3: Strategy checkpoint (interactive mode)
     - 步骤 4: Export results
  4. 确保 MCP Tools Reference 表格无需更改（已包含所有工具）
- **验收标准**:
  - SKILL.md 包含 WebSearch 禁用说明
  - Phase 1 描述为并行检索策略
  - 来源可信度差异有明确标注

### Task 5: 全量回归测试
- **类型**: 测试
- **文件范围**: 无新文件
- **依赖**: Task 1, Task 2, Task 3, Task 4
- **实施步骤**:
  1. 运行 `uv run pytest --tb=short -q` 全量测试
  2. 验证 835+ 测试全部通过
  3. 如有失败，定位并修复（预期不会有，因各 Task 文件范围不重叠）
- **验收标准**:
  - 全量测试通过（835+ passed）
  - 无新增 warning

## 文件冲突检查

✅ 无冲突 — 所有子任务的文件范围完全隔离：

| Task | 文件 |
|------|------|
| Task 1 | `search.py`, `models.py`, `test_search.py` |
| Task 2 | `regex_healer.py`, `test_contracts/` 相关 |
| Task 3 | `latexmkrc`, `compiler.py`, `test_compiler.py` |
| Task 4 | `SKILL.md` |
| Task 5 | 无文件修改，只运行测试 |

## 并行分组

- **Layer 1 (并行)**: Task 1, Task 2, Task 3, Task 4
- **Layer 2 (依赖 Layer 1)**: Task 5（全量回归测试）

## Builder 资源

- Layer 1: 4 个 Builder 并行执行
- Layer 2: 1 个 Builder 运行全量测试
- 预计总耗时：Layer 1 约 3-5 分钟（最长任务为 Task 1），Layer 2 约 1-2 分钟
