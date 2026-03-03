---
name: vibewriting-review
description: 论文质量审查：编译验证、引文审计、契约一致性、模拟同行评审
triggers:
  - "review paper"
  - "审查论文"
  - "check paper quality"
  - "论文质量检查"
---

# vibewriting-review

论文质量审查工作流，运行 Phase 6 全流程并展示结果。

## 工作流

### Step 1: 确认审查范围

使用 `AskUserQuestion` 询问用户审查范围：

| 选项 | 说明 |
|------|------|
| 全量审查（推荐） | 编译 + 引文 + 契约 + 同行评审 |
| 仅编译检查 | 只运行 latexmk 编译和自修复 |
| 仅引文检查 | 只运行 checkcites + CrossRef 验证 |

### Step 2: 运行 Phase 6 CLI

根据用户选择执行：

```bash
# 全量审查
uv run python -m vibewriting.latex.cli run

# 仅编译（手动调用 compiler 模块）
# 仅引文（手动调用 citation_audit 模块）
```

如果用户选择跳过外部 API：
```bash
uv run python -m vibewriting.latex.cli run --skip-external-api
```

### Step 3: 解析报告

读取 `output/phase6_report.json`，提取关键指标：

- **编译状态**: 成功/失败，自修复轮次
- **引文审计**: 验证数、可疑引用、孤立 claim
- **契约完整性**: 违规数量和类型
- **同行评审**: 总分、verdict、关键发现

### Step 4: 展示结果

以结构化格式展示审查摘要：

```
## 论文审查报告

### 编译: ✅/❌
- 自修复轮次: N
- 补丁报告: output/patch_report.json

### 引文: ✅/⚠️
- 已验证: N 条
- 可疑: N 条
- 孤立 claim: N 条

### 契约完整性: ✅/⚠️
- 违规: N 条

### 同行评审: X.X/10 (Verdict)
- 详细报告: output/peer_review.md
```

### Step 5: Approval Gate

使用 `AskUserQuestion` 展示摘要并提供选项：

| 选项 | 说明 |
|------|------|
| 查看详细报告 | 读取并展示 peer_review.md |
| 修复关键问题 | 根据报告逐一修复 |
| 接受当前状态 | 结束审查 |

## 依赖

- TeX Live（latexmk, checkcites, chktex）
- Python 模块: `vibewriting.latex.cli`
- 契约产物: `output/paper_state.json`（可选）
