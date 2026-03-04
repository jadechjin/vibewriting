# vibewriting Agent Notes

This repository supports both Claude Code and Codex.

## Skill Entry Points

- Claude runtime skills: `.claude/skills/`
- Codex runtime skills: `.agents/skills/`

Codex skill wrappers delegate to the canonical Claude skill playbooks to keep
a single workflow definition.

## MCP Runtime

For Python-level literature workflows, configure MCP tool calls through:

```python
from vibewriting.literature import set_mcp_tool_caller
```

or environment variable:

```bash
VW_MCP_TOOL_CALLER=module:function
```

The callable signature must be:

```python
caller(tool_name: str, **kwargs) -> Any | Awaitable[Any]
```

