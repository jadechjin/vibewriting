"""Dify knowledge base inventory management.

Maintains a local JSON snapshot of all documents in the Dify KB,
used to deduplicate newly retrieved papers against existing KB entries.

Usage::

    inventory = await sync_dify_inventory(path)
    kept, filtered = dedup_against_inventory(records, inventory)
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from vibewriting.literature.dedup import normalize_title, token_jaccard
from vibewriting.literature.runtime_adapter import call_mcp_tool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

_DOI_PATTERN = r"10\.\d{4,9}/[^\s]+"
_FILE_EXTENSIONS = frozenset({
    ".pdf", ".doc", ".docx", ".txt", ".md", ".tex", ".bib",
    ".html", ".htm", ".epub", ".rtf",
})


class DifyDocEntry(BaseModel):
    """A single document entry in the Dify KB inventory."""

    dify_doc_id: str
    name: str
    normalized_title: str
    created_at: str = ""


class DifyInventory(BaseModel):
    """Local snapshot of the Dify knowledge base document list."""

    last_synced: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total: int = 0
    documents: list[DifyDocEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_extension(name: str) -> str:
    """Remove common file extensions from a document name."""
    p = Path(name)
    if p.suffix.lower() in _FILE_EXTENSIONS:
        return p.stem
    return name


def _extract_doi_from_name(name: str) -> str | None:
    """Extract DOI from document name if present."""
    import re

    match = re.search(_DOI_PATTERN, name)
    return match.group(0) if match else None


def _parse_dify_doc(doc: dict[str, Any]) -> DifyDocEntry:
    """Convert a raw Dify API document dict to DifyDocEntry."""
    name = doc.get("name", "")
    title_text = _strip_extension(name)
    return DifyDocEntry(
        dify_doc_id=doc.get("id", ""),
        name=name,
        normalized_title=normalize_title(title_text),
        created_at=str(doc.get("created_at", "")),
    )


# ---------------------------------------------------------------------------
# MCP tool abstraction (same pattern as search.py)
# ---------------------------------------------------------------------------


async def _call_mcp_tool(tool_name: str, **kwargs: Any) -> Any:
    """MCP tool invocation via runtime adapter.

    In tests this function can still be patched directly.
    """
    return await call_mcp_tool(tool_name, **kwargs)


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


async def sync_dify_inventory(
    inventory_path: Path,
    page_limit: int = 100,
) -> DifyInventory:
    """Fetch all documents from Dify KB and save to a local JSON file.

    Paginates through ``list_documents`` until all documents are collected.
    On any API error, returns an empty inventory without raising.

    Parameters
    ----------
    inventory_path:
        Path to save the inventory JSON file.
    page_limit:
        Number of documents per API page (max 100).
    """
    all_docs: list[DifyDocEntry] = []
    page = 1
    total = None

    try:
        while True:
            result = await _call_mcp_tool(
                "list_documents", page=page, limit=page_limit,
            )

            if isinstance(result, dict) and result.get("error"):
                logger.warning(
                    "Dify list_documents failed: %s", result.get("message", "")
                )
                break

            data = result.get("data", []) if isinstance(result, dict) else []
            if total is None:
                total = result.get("total", 0) if isinstance(result, dict) else 0

            for doc in data:
                all_docs.append(_parse_dify_doc(doc))

            # Check if we've collected all documents
            if not data or len(all_docs) >= (total or 0):
                break

            page += 1

    except NotImplementedError:
        logger.info("Dify MCP not available; skipping inventory sync")
    except Exception as exc:
        logger.warning("Failed to sync Dify inventory: %s", exc)

    inventory = DifyInventory(
        last_synced=datetime.now(UTC),
        total=len(all_docs),
        documents=all_docs,
    )

    # Save to disk
    try:
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
        inventory_path.write_text(
            inventory.model_dump_json(indent=2),
            encoding="utf-8",
        )
        logger.info(
            "Synced Dify inventory: %d documents -> %s",
            len(all_docs), inventory_path,
        )
    except OSError as exc:
        logger.warning("Failed to write inventory file: %s", exc)

    return inventory


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------


def load_dify_inventory(inventory_path: Path) -> DifyInventory | None:
    """Load a previously saved Dify inventory from disk.

    Returns ``None`` if the file does not exist or is corrupt.
    """
    if not inventory_path.exists():
        return None

    try:
        raw = inventory_path.read_text(encoding="utf-8")
        return DifyInventory.model_validate_json(raw)
    except Exception as exc:
        logger.warning("Failed to load Dify inventory from %s: %s", inventory_path, exc)
        return None


# ---------------------------------------------------------------------------
# Dedup against inventory
# ---------------------------------------------------------------------------


def dedup_against_inventory(
    records: list,
    inventory: DifyInventory,
    threshold: float = 0.9,
) -> tuple[list, list[str]]:
    """Filter out records that already exist in the Dify KB inventory.

    Matching strategy:
    1. DOI exact match (if DOI is extractable from Dify document name)
    2. Normalized title token Jaccard >= threshold

    Parameters
    ----------
    records:
        List of ``RawLiteratureRecord`` to filter.
    inventory:
        The Dify KB inventory to compare against.
    threshold:
        Jaccard similarity threshold for title matching.

    Returns
    -------
    tuple
        (kept_records, filtered_titles) — records that passed and
        titles of records that were filtered out.
    """
    if not inventory.documents or not records:
        return list(records), []

    # Pre-compute inventory lookup structures
    inv_titles = [doc.normalized_title for doc in inventory.documents]
    inv_dois: set[str] = set()
    for doc in inventory.documents:
        doi = _extract_doi_from_name(doc.name)
        if doi:
            inv_dois.add(doi.lower())

    kept = []
    filtered_titles: list[str] = []

    for rec in records:
        # Strategy 1: DOI exact match
        if rec.doi and rec.doi.lower() in inv_dois:
            filtered_titles.append(rec.title)
            continue

        # Strategy 2: Title similarity
        rec_norm = normalize_title(rec.title)
        matched = False
        for inv_title in inv_titles:
            if inv_title and token_jaccard(rec_norm, inv_title) >= threshold:
                matched = True
                break

        if matched:
            filtered_titles.append(rec.title)
        else:
            kept.append(rec)

    if filtered_titles:
        logger.info(
            "Inventory dedup: filtered %d records already in Dify KB",
            len(filtered_titles),
        )

    return kept, filtered_titles
