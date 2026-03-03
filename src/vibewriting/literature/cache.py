"""Local knowledge cache backed by JSONL + in-memory index.

Stores EvidenceCard instances as one-JSON-per-line in a JSONL file,
with fast in-memory lookup via primary (claim_id) and secondary
(bib_key, tag, evidence_type) indexes.

Usage::

    cache = LiteratureCache(Path("data/processed/literature/literature_cards.jsonl"))
    loaded = cache.load()
    cache.upsert(card)
    results = cache.query(bib_key="smith2024", tags=["NLP"])
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from vibewriting.models.evidence_card import EvidenceCard

logger = logging.getLogger(__name__)


class LiteratureCache:
    """JSONL-backed local knowledge cache with in-memory indexes.

    The JSONL file is append-only: upserts always append a new line.
    The in-memory ``_index`` keeps only the latest version per ``claim_id``,
    so duplicate lines (from repeated upserts) are naturally deduplicated
    on ``load()``.
    """

    def __init__(self, jsonl_path: Path) -> None:
        self._path = jsonl_path
        self._index: dict[str, EvidenceCard] = {}
        self._bib_index: dict[str, list[str]] = {}
        self._tag_index: dict[str, list[str]] = {}
        self._type_index: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> int:
        """Load all cards from JSONL into memory indexes.

        - If the file does not exist, silently returns 0.
        - Corrupt lines are logged as warnings and skipped.
        - Returns the number of successfully loaded cards.
        """
        self._index.clear()
        self._bib_index.clear()
        self._tag_index.clear()
        self._type_index.clear()

        if not self._path.exists():
            return 0

        loaded = 0
        with self._path.open("r", encoding="utf-8") as fh:
            for lineno, raw_line in enumerate(fh, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    card = EvidenceCard.model_validate_json(line)
                except Exception:
                    logger.warning(
                        "Skipping corrupt line %d in %s", lineno, self._path
                    )
                    continue
                # Last-write-wins: later lines override earlier ones
                self._index[card.claim_id] = card
                loaded += 1

        self._rebuild_indexes()
        return len(self._index)

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def _rebuild_indexes(self) -> None:
        """Rebuild secondary indexes from the primary ``_index``."""
        self._bib_index.clear()
        self._tag_index.clear()
        self._type_index.clear()

        for claim_id, card in self._index.items():
            self._bib_index.setdefault(card.bib_key, []).append(claim_id)

            for tag in card.tags:
                self._tag_index.setdefault(tag, []).append(claim_id)

            self._type_index.setdefault(card.evidence_type, []).append(
                claim_id
            )

    def _add_to_indexes(self, card: EvidenceCard) -> None:
        """Add a single card to secondary indexes (incremental)."""
        claim_id = card.claim_id

        self._bib_index.setdefault(card.bib_key, []).append(claim_id)

        for tag in card.tags:
            self._tag_index.setdefault(tag, []).append(claim_id)

        self._type_index.setdefault(card.evidence_type, []).append(claim_id)

    def _remove_from_indexes(self, card: EvidenceCard) -> None:
        """Remove a single card from secondary indexes."""
        claim_id = card.claim_id

        bib_ids = self._bib_index.get(card.bib_key)
        if bib_ids and claim_id in bib_ids:
            bib_ids.remove(claim_id)
            if not bib_ids:
                del self._bib_index[card.bib_key]

        for tag in card.tags:
            tag_ids = self._tag_index.get(tag)
            if tag_ids and claim_id in tag_ids:
                tag_ids.remove(claim_id)
                if not tag_ids:
                    del self._tag_index[tag]

        type_ids = self._type_index.get(card.evidence_type)
        if type_ids and claim_id in type_ids:
            type_ids.remove(claim_id)
            if not type_ids:
                del self._type_index[card.evidence_type]

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def upsert(self, card: EvidenceCard) -> None:
        """Append *card* to the JSONL file and update in-memory indexes.

        If a card with the same ``claim_id`` already exists in memory,
        the old entry is replaced in the index (the old JSONL line remains
        on disk but will be shadowed by the newer line on next ``load()``).

        The parent directory is created automatically if it does not exist.
        """
        # Ensure parent directory
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Append to JSONL
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(card.model_dump_json() + "\n")
            fh.flush()

        # Update indexes
        existing = self._index.get(card.claim_id)
        if existing is not None:
            self._remove_from_indexes(existing)

        self._index[card.claim_id] = card
        self._add_to_indexes(card)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def has(self, claim_id: str) -> bool:
        """Return ``True`` if *claim_id* exists in the cache."""
        return claim_id in self._index

    def get(self, claim_id: str) -> EvidenceCard | None:
        """Return the card for *claim_id*, or ``None`` if not found."""
        return self._index.get(claim_id)

    def query(
        self,
        *,
        claim_id: str | None = None,
        bib_key: str | None = None,
        tags: list[str] | None = None,
        evidence_type: str | None = None,
    ) -> list[EvidenceCard]:
        """Query cards by one or more criteria (intersection semantics).

        - Multiple criteria are ANDed together.
        - If no criteria are given, all cards are returned.
        """
        candidate_sets: list[set[str]] = []

        if claim_id is not None:
            if claim_id in self._index:
                candidate_sets.append({claim_id})
            else:
                return []

        if bib_key is not None:
            ids = self._bib_index.get(bib_key, [])
            candidate_sets.append(set(ids))

        if tags is not None:
            for tag in tags:
                ids = self._tag_index.get(tag, [])
                candidate_sets.append(set(ids))

        if evidence_type is not None:
            ids = self._type_index.get(evidence_type, [])
            candidate_sets.append(set(ids))

        if not candidate_sets:
            return list(self._index.values())

        result_ids = candidate_sets[0]
        for s in candidate_sets[1:]:
            result_ids = result_ids & s

        return [self._index[cid] for cid in result_ids if cid in self._index]

    # ------------------------------------------------------------------
    # Drift detection
    # ------------------------------------------------------------------

    def detect_drift(self, card: EvidenceCard) -> bool:
        """Return ``True`` if the cached card's ``content_hash`` differs.

        Compares the ``content_hash`` of the given *card* against the
        in-memory version with the same ``claim_id``.  Returns ``False``
        if the card is not in the cache or if both hashes are ``None``.
        """
        existing = self._index.get(card.claim_id)
        if existing is None:
            return False
        if existing.content_hash is None and card.content_hash is None:
            return False
        return existing.content_hash != card.content_hash

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def all_cards(self) -> list[EvidenceCard]:
        """Return a list of all cached cards."""
        return list(self._index.values())

    def count(self) -> int:
        """Return the total number of cached cards."""
        return len(self._index)
