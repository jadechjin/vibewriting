---
name: search-literature
description: Search academic papers using paper-search MCP server
---

# Literature Search Workflow

Use the paper-search MCP tools to find academic papers relevant to the research topic.

## Workflow

1. **Start search**: Call `search_papers(query)` with the user's research topic.
   - Set `domain` to "general" or "materials_science" as appropriate.
   - Set `max_results` to control result volume (default: 100).

2. **Strategy checkpoint**: The server returns a `strategy_confirmation` checkpoint.
   - Present the parsed intent and search strategy to the user.
   - Ask the user to approve, edit, or reject the strategy.
   - Call `decide(session_id, action, user_response)` with the user's decision.

3. **Wait for results**: Poll `get_session(session_id)` if the pipeline is still running.

4. **Result review checkpoint**: When results are ready, present the paper summary to the user.
   - Show facets, paper counts, and top results.
   - Ask the user to approve or provide feedback for refinement.
   - Call `decide(session_id, action, user_response)` with the user's decision.

5. **Export**: Call `export_results(session_id, format)` to export.
   - Use `bibtex` format for LaTeX integration (save to `paper/bib/references.bib`).
   - Use `markdown` for human review.
   - Use `json` for programmatic processing.

## MCP Tools Reference

| Tool | Parameters | Purpose |
|------|-----------|---------|
| `search_papers` | query, domain, max_results | Start a search session |
| `decide` | session_id, action, user_response, data, note | Submit checkpoint decision |
| `get_session` | session_id | Poll session progress |
| `export_results` | session_id, format | Export final results |

## Important

- Always present checkpoints to the user; never auto-approve.
- The `user_response` parameter in `decide()` must contain the user's actual input, not trivial responses like "ok".
- BibTeX exports should be appended to `paper/bib/references.bib`, not overwrite it.
