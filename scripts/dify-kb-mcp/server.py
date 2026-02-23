# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "mcp[cli]>=1.0",
#   "httpx>=0.27",
# ]
# ///
"""Dify Knowledge Base MCP Bridge Server.

Bridges Dify knowledge base API to MCP protocol with graceful degradation.
When credentials are missing or Dify is unavailable, returns informative
error responses without crashing.
"""

from __future__ import annotations

import logging
import os

import httpx
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("dify-kb-mcp")

DIFY_API_BASE_URL = os.environ.get("DIFY_API_BASE_URL", "").rstrip("/")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "")
DIFY_DATASET_ID = os.environ.get("DIFY_DATASET_ID", "")
try:
    MAX_RETRIES = max(1, int(os.environ.get("DIFY_MAX_RETRIES", "3")))
except (ValueError, TypeError):
    MAX_RETRIES = 3
try:
    TIMEOUT = float(os.environ.get("DIFY_TIMEOUT", "30"))
except (ValueError, TypeError):
    TIMEOUT = 30.0

VALID_SEARCH_METHODS = ("hybrid_search", "keyword_search", "semantic_search")

mcp = FastMCP("dify-knowledge")


def _check_credentials() -> str | None:
    """Return error message if credentials are missing, None if OK."""
    missing = []
    if not DIFY_API_BASE_URL:
        missing.append("DIFY_API_BASE_URL")
    if not DIFY_API_KEY:
        missing.append("DIFY_API_KEY")
    if not DIFY_DATASET_ID:
        missing.append("DIFY_DATASET_ID")
    if missing:
        return (
            f"Dify credentials not configured: {', '.join(missing)}. "
            "Set these environment variables in .env file."
        )
    return None


async def _dify_request(method: str, path: str, **kwargs: object) -> dict:
    """Make HTTP request to Dify API with retry logic."""
    url = f"{DIFY_API_BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json",
    }

    last_error = f"Request to {url} failed after {MAX_RETRIES} attempts"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.request(
                    method, url, headers=headers, **kwargs,
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            last_error = f"Request timeout (attempt {attempt}/{MAX_RETRIES}): {e}"
            logger.warning(last_error)
        except httpx.ConnectError as e:
            last_error = f"Connection failed (attempt {attempt}/{MAX_RETRIES}): {e}"
            logger.warning(last_error)
        except httpx.HTTPStatusError as e:
            last_error = (
                f"HTTP {e.response.status_code} "
                f"(attempt {attempt}/{MAX_RETRIES}): {e}"
            )
            logger.warning(last_error)
            if e.response.status_code < 500:
                break  # Don't retry client errors (4xx)
        except httpx.HTTPError as e:
            last_error = f"HTTP error (attempt {attempt}/{MAX_RETRIES}): {e}"
            logger.warning(last_error)

    raise RuntimeError(last_error)


@mcp.tool()
async def retrieve_knowledge(
    query: str,
    top_k: int = 5,
    search_method: str = "hybrid_search",
    score_threshold: float = 0.5,
) -> dict:
    """Search the Dify knowledge base for documents relevant to a query.

    Args:
        query: Search query text
        top_k: Number of results to return (default: 5)
        search_method: One of hybrid_search, keyword_search, semantic_search
        score_threshold: Minimum relevance score (default: 0.5)
    """
    cred_error = _check_credentials()
    if cred_error:
        return {"error": True, "message": cred_error}

    if search_method not in VALID_SEARCH_METHODS:
        return {
            "error": True,
            "message": (
                f"Invalid search_method: {search_method}. "
                f"Use one of: {', '.join(VALID_SEARCH_METHODS)}."
            ),
        }

    try:
        payload = {
            "query": query,
            "retrieval_model": {
                "search_method": search_method,
                "reranking_enable": True,
                "reranking_mode": "reranking_model",
                "top_k": top_k,
                "score_threshold_enabled": True,
                "score_threshold": score_threshold,
            },
        }
        result = await _dify_request(
            "POST",
            f"/v1/datasets/{DIFY_DATASET_ID}/retrieve",
            json=payload,
        )
        return {"error": False, "records": result.get("records", [])}
    except RuntimeError as e:
        return {
            "error": True,
            "message": (
                f"Dify API request failed: {e}. "
                "Check credentials (DIFY_API_KEY, DIFY_DATASET_ID) "
                "and network connectivity (DIFY_API_BASE_URL)."
            ),
        }


@mcp.tool()
async def list_documents(
    page: int = 1,
    limit: int = 20,
    keyword: str = "",
) -> dict:
    """List documents in the Dify knowledge base dataset.

    Args:
        page: Page number (default: 1)
        limit: Results per page (default: 20)
        keyword: Optional filter keyword
    """
    cred_error = _check_credentials()
    if cred_error:
        return {"error": True, "message": cred_error}

    try:
        params: dict[str, int | str] = {"page": page, "limit": limit}
        if keyword:
            params["keyword"] = keyword
        result = await _dify_request(
            "GET",
            f"/v1/datasets/{DIFY_DATASET_ID}/documents",
            params=params,
        )
        return {
            "error": False,
            "data": result.get("data", []),
            "total": result.get("total", 0),
            "page": page,
            "limit": limit,
        }
    except RuntimeError as e:
        return {
            "error": True,
            "message": (
                f"Dify API request failed: {e}. "
                "Check credentials (DIFY_API_KEY, DIFY_DATASET_ID) "
                "and network connectivity (DIFY_API_BASE_URL)."
            ),
        }


if __name__ == "__main__":
    mcp.run()
