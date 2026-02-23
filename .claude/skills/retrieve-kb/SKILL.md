---
name: retrieve-kb
description: Retrieve knowledge from Dify knowledge base via MCP bridge
---

# Knowledge Base Retrieval

Use the dify-knowledge MCP tools to retrieve relevant documents from the Dify knowledge base.

## Prerequisites

- Dify credentials must be configured in `.env` (DIFY_API_BASE_URL, DIFY_API_KEY, DIFY_DATASET_ID).
- If credentials are not configured, the bridge will return a clear error message.

## Tools

### retrieve_knowledge

Search the knowledge base for documents relevant to a query.

**Parameters:**
- `query` (required): Search query text
- `top_k` (optional, default: 5): Number of results to return
- `search_method` (optional, default: "hybrid_search"): One of "hybrid_search", "keyword_search", "semantic_search"
- `score_threshold` (optional, default: 0.5): Minimum relevance score

**Usage:**
```
retrieve_knowledge(query="perovskite solar cell efficiency", top_k=10, search_method="hybrid_search")
```

### list_documents

List documents in the knowledge base dataset.

**Parameters:**
- `page` (optional, default: 1): Page number
- `limit` (optional, default: 20): Results per page
- `keyword` (optional): Filter by keyword

## Degradation Behavior

When Dify is unavailable, the bridge returns an error response instead of crashing.
Continue the workflow without knowledge base augmentation in this case.
