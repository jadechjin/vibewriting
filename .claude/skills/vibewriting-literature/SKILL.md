---
name: vibewriting-literature
description: 端到端文献检索：检索、去重、证据卡生成、BibTeX 管理
---

# Literature Search Workflow

End-to-end literature search: retrieve papers -> deduplicate -> generate evidence cards -> update BibTeX.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| query | (required) | Research topic or search terms |
| max_results | 20 | Maximum papers to retrieve |
| evidence_type | all | Filter: `empirical`, `theoretical`, `survey`, `meta-analysis` |
| mode | interactive | `interactive` (human checkpoints) or `headless` (auto-accept) |

## Workflow

### Phase 1: Literature Retrieval

1. **Parallel retrieval**: Launch **both** sources simultaneously:
   - Call `retrieve_knowledge(query)` via Dify MCP (trusted source) — uses KB default settings
   - Call `search_papers(query, max_results=N)` via paper-search MCP (supplementary source)
   - Dify results are marked **trusted** — can be used directly in drafts.
   - paper-search results are marked **supplementary** — require user confirmation before use in content.

2. **Merge results**: Combine results with source priority: Dify (dify-kb) > paper-search > web-search.

3. **Strategy checkpoint** (interactive mode only):
   - Present the parsed intent, search strategy, and source breakdown to the user.
   - Call `decide(session_id, action, user_response)` with the user's decision.

4. **Export results**: Call `export_results(session_id, format)` for both `json` and `bibtex`.

### Phase 2: Dedup + Evidence Cards

5. **Three-layer deduplication**:
   - L1: Primary key dedup (DOI > arXiv > PMID > title+year)
   - L2: Near-duplicate title removal (token Jaccard >= 0.9)
   - Report dedup results to the user.

6. **Generate evidence cards**: For each retained paper:
   - Extract key claims from the abstract.
   - Create `EvidenceCard` with `claim_id` (EC-YYYY-NNN), `bib_key`, `evidence_type`.
   - Auto-flag `paraphrase=True` when quote > 50 words.
   - Validate each card against JSON Schema.

7. **L3 claim-level dedup**: Remove duplicate claims within same bib_key.

### Phase 3: Persistence

8. **Cache evidence cards**: Write to `data/processed/literature/literature_cards.jsonl`.
   - Use `LiteratureCache.upsert()` for each card.

9. **Update BibTeX**: Merge new entries into `paper/bib/references.bib`.
   - Human-edited entries are preserved (never overwritten).
   - Auto-generated entries marked with `note = {auto-generated}`.
   - Entries sorted alphabetically by cite key.
   - Atomic write (tmp -> rename).

10. **Report**: Present summary to the user:
    - Papers found / after dedup / evidence cards generated
    - New BibTeX entries added
    - Any conflicts or errors

## MCP Tools Reference

| Tool | Parameters | Purpose |
|------|-----------|---------|
| `search_papers` | query, domain, max_results | Start a search session |
| `decide` | session_id, action, user_response | Submit checkpoint decision |
| `get_session` | session_id | Poll session progress |
| `export_results` | session_id, format | Export results (json/bibtex/markdown) |
| `retrieve_knowledge` | query | Dify knowledge base search (uses KB defaults) |

## Python Module Reference

```python
from vibewriting.literature.search import search_literature, SearchResult
from vibewriting.literature.evidence import create_evidence_card
from vibewriting.literature.cache import LiteratureCache
from vibewriting.literature.bib_manager import parse_bib, merge_bib, write_bib
from vibewriting.literature.dedup import dedup_claims
```

## Important

- **Do NOT use the built-in `WebSearch` / `web_search` tool.** All retrieval must go through MCP tools (`retrieve_knowledge` for Dify, `search_papers` for paper-search). Using the built-in web search bypasses the knowledge management system.
- **Source trust levels**: Dify knowledge base (`dify-kb`) results can be used directly in drafts. Paper-search and web-search results are supplementary and require user confirmation before being used in content.
- In interactive mode, always present checkpoints to the user; never auto-approve.
- BibTeX merge preserves human-edited entries (conflicts logged, not overwritten).
- Evidence cards must pass `EC-\d{4}-\d{3}` claim_id pattern validation.
- Quote length limit: <= 50 words for direct quotes; longer quotes auto-flagged as paraphrases.
- All evidence cards are stored in JSONL format (one JSON object per line).
