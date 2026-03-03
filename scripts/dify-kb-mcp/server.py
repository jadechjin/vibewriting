# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "mcp[cli]>=1.0",
#   "httpx>=0.27",
#   "python-dotenv>=1.0",
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
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load .env from project root as fallback (MCP env interpolation may fail)
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env", override=False)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("dify-kb-mcp")

# ---------------------------------------------------------------------------
# Environment variable resolution with ${...} literal filtering
# ---------------------------------------------------------------------------
# Claude Code MCP env interpolation (e.g. "${VW_DIFY_API_BASE_URL}") may
# leave the literal "${...}" string when the variable is absent from the
# host process environment (known bugs: anthropics/claude-code#9427, #1254,
# #14032, #28090).  The helper below treats such literals as missing.


def _resolve_env(key: str) -> str | None:
    """Return env value for *key*, or ``None`` if missing / unresolved.

    Values that look like unresolved ``${...}`` interpolation placeholders
    (start with ``${`` and contain ``}``) are treated as missing so that the
    fallback chain can proceed.
    """
    value = os.environ.get(key)
    if not value:
        return None
    if value.startswith("${") and "}" in value:
        return None
    return value


# Fallback chain: DIFY_* (from .mcp.json env) -> VW_DIFY_* (from .env)
DIFY_API_BASE_URL = (
    _resolve_env("DIFY_API_BASE_URL")
    or _resolve_env("VW_DIFY_API_BASE_URL")
    or ""
).rstrip("/")
DIFY_API_KEY = (
    _resolve_env("DIFY_API_KEY")
    or _resolve_env("VW_DIFY_API_KEY")
    or ""
)
DIFY_DATASET_ID = (
    _resolve_env("DIFY_DATASET_ID")
    or _resolve_env("VW_DIFY_DATASET_ID")
    or ""
)
try:
    MAX_RETRIES = max(1, int(os.environ.get("DIFY_MAX_RETRIES", "3")))
except (ValueError, TypeError):
    MAX_RETRIES = 3
try:
    TIMEOUT = float(os.environ.get("DIFY_TIMEOUT", "30"))
except (ValueError, TypeError):
    TIMEOUT = 30.0

mcp = FastMCP("dify-knowledge")


def _check_credentials() -> str | None:
    """Return error message if credentials are missing or malformed, None if OK."""
    missing = []
    if not DIFY_API_BASE_URL:
        missing.append("DIFY_API_BASE_URL (or VW_DIFY_API_BASE_URL)")
    if not DIFY_API_KEY:
        missing.append("DIFY_API_KEY (or VW_DIFY_API_KEY)")
    if not DIFY_DATASET_ID:
        missing.append("DIFY_DATASET_ID (or VW_DIFY_DATASET_ID)")
    if missing:
        return (
            f"Dify credentials not configured: {', '.join(missing)}. "
            "Set these variables in .env (VW_DIFY_API_BASE_URL, "
            "VW_DIFY_API_KEY, VW_DIFY_DATASET_ID)."
        )
    if not DIFY_API_BASE_URL.startswith(("http://", "https://")):
        return (
            f"DIFY_API_BASE_URL is invalid: '{DIFY_API_BASE_URL}'. "
            "Value must start with http:// or https://. "
            "Check that VW_DIFY_API_BASE_URL is correctly set in .env "
            "(e.g. https://api.dify.ai/v1)."
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
) -> dict:
    """Search the Dify knowledge base for documents relevant to a query.

    Uses the knowledge base's default retrieval settings configured in Dify.

    Args:
        query: Search query text
    """
    cred_error = _check_credentials()
    if cred_error:
        return {"error": True, "message": cred_error}

    try:
        payload = {
            "query": query,
        }
        result = await _dify_request(
            "POST",
            f"/datasets/{DIFY_DATASET_ID}/retrieve",
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
            f"/datasets/{DIFY_DATASET_ID}/documents",
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
