"""Literature search orchestrator via MCP tools.

Coordinates paper-search and Dify MCP servers to retrieve, deduplicate,
and cache literature as EvidenceCards.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vibewriting.literature.dedup import DeduplicationReport, deduplicate
from vibewriting.literature.dify_inventory import (
    dedup_against_inventory,
    load_dify_inventory,
    sync_dify_inventory,
)
from vibewriting.literature.models import RawLiteratureRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """Result of a literature search orchestration."""

    records: list[RawLiteratureRecord] = field(default_factory=list)
    bibtex: str = ""
    dedup_report: DeduplicationReport | None = None
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# MCP tool abstraction
# ---------------------------------------------------------------------------


async def _call_mcp_tool(tool_name: str, **kwargs: Any) -> Any:
    """Placeholder for MCP tool invocation.

    In production this is replaced by the Claude Code MCP runtime.
    During testing it is patched with mock implementations.
    """
    raise NotImplementedError(
        f"MCP tool '{tool_name}' must be called through Claude Code runtime"
    )


# ---------------------------------------------------------------------------
# Paper-search MCP integration
# ---------------------------------------------------------------------------


def _parse_paper_search_results(
    raw_results: list[dict[str, Any]],
) -> list[RawLiteratureRecord]:
    """Convert paper-search JSON results to RawLiteratureRecord list."""
    records: list[RawLiteratureRecord] = []
    for item in raw_results:
        authors = item.get("authors", [])
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(",")]

        records.append(
            RawLiteratureRecord(
                title=item.get("title", ""),
                authors=authors,
                year=int(item.get("year", 0)),
                doi=item.get("doi"),
                arxiv_id=item.get("arxiv_id"),
                pmid=item.get("pmid"),
                abstract=item.get("abstract", ""),
                source="paper-search",
                raw_data=item,
            )
        )
    return records


async def search_via_paper_search(
    query: str,
    max_results: int = 20,
    mode: str = "headless",
) -> tuple[list[RawLiteratureRecord], str]:
    """Search via paper-search MCP and return records + BibTeX.

    Parameters
    ----------
    query:
        Search query string.
    max_results:
        Maximum number of results to return.
    mode:
        ``"headless"`` (auto-accept checkpoints) or ``"interactive"``.

    Returns
    -------
    tuple
        (list of RawLiteratureRecord, BibTeX string)
    """
    try:
        # Step 1: search_papers -> session
        session = await _call_mcp_tool(
            "search_papers", query=query, max_results=max_results
        )
        session_id = session.get("session_id", "")

        if not session_id:
            logger.warning("paper-search returned no session_id")
            return [], ""

        # Step 2: export results
        export = await _call_mcp_tool(
            "export_results", session_id=session_id, format="json"
        )

        raw_results = export.get("results", [])
        bibtex = export.get("bibtex", "")

        records = _parse_paper_search_results(raw_results)
        return records[:max_results], bibtex

    except NotImplementedError:
        raise
    except Exception as exc:
        logger.error("paper-search failed: %s", exc)
        return [], ""


# ---------------------------------------------------------------------------
# Dify MCP integration
# ---------------------------------------------------------------------------


def _parse_dify_results(
    raw_results: list[dict[str, Any]],
) -> list[RawLiteratureRecord]:
    """Convert Dify knowledge retrieval results to RawLiteratureRecord list."""
    records: list[RawLiteratureRecord] = []
    for item in raw_results:
        metadata = item.get("metadata", {})
        records.append(
            RawLiteratureRecord(
                title=metadata.get("title", item.get("content", "")[:100]),
                authors=metadata.get("authors", []),
                year=int(metadata.get("year", 0)),
                doi=metadata.get("doi"),
                abstract=item.get("content", ""),
                source="dify-kb",
                raw_data=item,
            )
        )
    return records


async def search_via_dify(
    query: str,
) -> list[RawLiteratureRecord]:
    """Search via Dify knowledge base MCP with graceful degradation.

    Uses the knowledge base's default retrieval settings configured in Dify.
    Returns an empty list on any failure (does not raise).
    """
    try:
        results = await _call_mcp_tool(
            "retrieve_knowledge", query=query
        )
        if isinstance(results, list):
            return _parse_dify_results(results)
        return []
    except NotImplementedError:
        raise
    except Exception as exc:
        logger.warning("Dify search failed (degrading gracefully): %s", exc)
        return []


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def search_literature(
    query: str,
    max_results: int = 20,
    mode: str = "headless",
    threshold: float = 0.9,
    inventory_path: Path | None = None,
) -> SearchResult:
    """Full literature search orchestration.

    Flow:
    1. Run paper-search MCP and Dify MCP in parallel
    2. Merge with source priority: dify-kb > paper-search > web-search
    3. Three-layer deduplication (L1 primary key + L2 similarity)
    4. Inventory dedup against Dify KB (if inventory_path provided)
    5. Return SearchResult

    Parameters
    ----------
    query:
        Search query string.
    max_results:
        Maximum number of results to return.
    mode:
        ``"headless"`` (auto-accept checkpoints) or ``"interactive"``.
    threshold:
        Jaccard similarity threshold for dedup (default 0.9).
    inventory_path:
        Path to Dify KB inventory JSON file. If provided, syncs the
        inventory from Dify API and filters out papers already in KB.

    Note: Evidence card generation, cache writing, and BibTeX merge
    are handled by the caller (Skill or Agent), not here.
    """
    result = SearchResult()
    ps_records: list[RawLiteratureRecord] = []
    dify_records: list[RawLiteratureRecord] = []

    ps_task = asyncio.create_task(
        search_via_paper_search(query, max_results=max_results, mode=mode)
    )
    dify_task = asyncio.create_task(search_via_dify(query))

    ps_out, dify_out = await asyncio.gather(
        ps_task, dify_task, return_exceptions=True
    )

    if isinstance(ps_out, Exception):
        if isinstance(ps_out, NotImplementedError):
            result.errors.append("paper-search MCP not available in this context")
        else:
            result.errors.append(f"paper-search error: {ps_out}")
    else:
        ps_records, bibtex = ps_out
        result.bibtex = bibtex

    if isinstance(dify_out, Exception):
        if isinstance(dify_out, NotImplementedError):
            result.errors.append("Dify MCP not available in this context")
        else:
            result.errors.append(f"Dify error: {dify_out}")
    else:
        dify_records = list(dify_out)

    # Merge: dify-kb first, then paper-search (priority order)
    merged = [*dify_records, *ps_records]

    if merged:
        deduped, report = deduplicate(merged, threshold=threshold)

        # Inventory dedup: filter against Dify KB documents
        if inventory_path is not None:
            try:
                inventory = await sync_dify_inventory(inventory_path)
            except Exception as exc:
                logger.warning("Inventory sync failed, skipping: %s", exc)
                inventory = load_dify_inventory(inventory_path)

            if inventory is not None:
                deduped, filtered_titles = dedup_against_inventory(
                    deduped, inventory, threshold=threshold,
                )
                report.inventory_filtered_count = len(filtered_titles)
                report.inventory_filtered_titles = filtered_titles

        source_priority = {"dify-kb": 0, "paper-search": 1, "web-search": 2}
        deduped.sort(key=lambda r: source_priority.get(r.source, 99))
        result.records = deduped[:max_results]
        result.dedup_report = report

    return result
