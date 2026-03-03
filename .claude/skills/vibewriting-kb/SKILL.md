---
name: vibewriting-kb
description: 从 Dify 知识库检索相关文档
---

# Knowledge Base Retrieval

Use the dify-knowledge MCP tools to retrieve relevant documents from the Dify knowledge base.

## Prerequisites

- Dify credentials must be configured in `.env` (DIFY_API_BASE_URL, DIFY_API_KEY, DIFY_DATASET_ID).
- If credentials are not configured, the bridge will return a clear error message.

## Tools

### retrieve_knowledge

Search the knowledge base for documents relevant to a query.

Uses the knowledge base's default retrieval settings configured in Dify (search method, top_k, score threshold, reranking, etc.).

**Parameters:**
- `query` (required): Search query text

**Usage:**
```
retrieve_knowledge(query="perovskite solar cell efficiency")
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
