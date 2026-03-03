"""Three-layer deduplication pipeline.

L1: Primary key dedup (DOI > arXiv > PMID > title+year)
L2: Approximate title similarity dedup (token Jaccard)
L3: Claim-level dedup on EvidenceCards (content_hash within same bib_key)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from vibewriting.literature.models import RawLiteratureRecord
from vibewriting.models.evidence_card import EvidenceCard

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STOP_WORDS: frozenset[str] = frozenset({
    "the", "a", "an", "of", "for", "in", "on", "to",
    "and", "with", "is", "by", "from", "at", "or",
    "as", "its", "this", "that",
})

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclass
class DeduplicationReport:
    """Counts at each dedup stage plus removed keys."""

    input_count: int
    l1_count: int   # after primary-key dedup
    l2_count: int   # after similarity dedup
    l3_count: int   # after claim-level dedup (filled later)
    removed_keys: list[str]
    inventory_filtered_count: int = 0   # filtered by Dify KB inventory
    inventory_filtered_titles: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def normalize_title(title: str) -> str:
    """Lowercase, strip punctuation, remove stop words, collapse spaces."""
    text = title.lower()
    # keep only letters, digits, spaces
    text = re.sub(r"[^a-z0-9\s]", "", text)
    tokens = [t for t in text.split() if t not in STOP_WORDS]
    return " ".join(tokens).strip()


def token_jaccard(a: str, b: str) -> float:
    """Token-level Jaccard similarity between two strings."""
    set_a = set(a.split())
    set_b = set(b.split())
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# L1 -- primary key dedup
# ---------------------------------------------------------------------------

_KEY_PRIORITY = {"doi": 0, "arxiv": 1, "pmid": 2, "title": 3}


def _key_priority(pk: str) -> int:
    prefix = pk.split(":")[0]
    return _KEY_PRIORITY.get(prefix, 99)


def dedup_by_primary_key(
    records: list[RawLiteratureRecord],
) -> list[RawLiteratureRecord]:
    """Remove duplicates by ``primary_key``, keeping first occurrence.

    Records with stronger identifiers (DOI > arXiv > PMID > title+year)
    are preferred when two records share the same primary key.
    """
    # Sort stably: lower priority number = stronger key comes first,
    # but we also want to preserve original order among equal-priority items.
    indexed = list(enumerate(records))
    indexed.sort(key=lambda pair: (_key_priority(pair[1].primary_key), pair[0]))

    seen: set[str] = set()
    kept: list[tuple[int, RawLiteratureRecord]] = []
    for idx, rec in indexed:
        pk = rec.primary_key
        if pk not in seen:
            seen.add(pk)
            kept.append((idx, rec))

    # Restore original insertion order
    kept.sort(key=lambda pair: pair[0])
    return [rec for _, rec in kept]


# ---------------------------------------------------------------------------
# L2 -- approximate similarity dedup
# ---------------------------------------------------------------------------


def dedup_by_similarity(
    records: list[RawLiteratureRecord],
    threshold: float = 0.9,
) -> list[RawLiteratureRecord]:
    """Remove near-duplicate titles via token Jaccard similarity.

    For each pair, if ``token_jaccard(normalized_a, normalized_b) >= threshold``
    the later record is dropped.
    """
    if not records:
        return []

    normed = [normalize_title(r.title) for r in records]
    keep_flags = [True] * len(records)

    for i in range(len(records)):
        if not keep_flags[i]:
            continue
        for j in range(i + 1, len(records)):
            if not keep_flags[j]:
                continue
            if token_jaccard(normed[i], normed[j]) >= threshold:
                keep_flags[j] = False

    return [r for r, keep in zip(records, keep_flags) if keep]


# ---------------------------------------------------------------------------
# L3 -- claim-level dedup on EvidenceCards
# ---------------------------------------------------------------------------


def _normalize_claim(text: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def dedup_claims(cards: list[EvidenceCard]) -> list[EvidenceCard]:
    """Deduplicate evidence cards by ``content_hash`` within the same ``bib_key``.

    Rules:
    - Normalize ``claim_text`` (lowercase + strip + collapse spaces).
    - Cards sharing the same ``bib_key`` AND ``content_hash`` are duplicates;
      keep only the one with the highest ``quality_score``.
    - Cards with different ``bib_key`` but identical ``content_hash``
      are all retained (same evidence from independent sources).
    - Cards without ``content_hash`` are never considered duplicates.
    """
    if not cards:
        return []

    # Group by (bib_key, content_hash) -- only when content_hash is set.
    # For cards without content_hash we keep them unconditionally.
    groups: dict[tuple[str, str], list[EvidenceCard]] = {}
    ungrouped: list[EvidenceCard] = []

    for card in cards:
        if card.content_hash is None:
            ungrouped.append(card)
            continue
        key = (card.bib_key, card.content_hash)
        groups.setdefault(key, []).append(card)

    result: list[EvidenceCard] = list(ungrouped)
    for group in groups.values():
        best = max(group, key=lambda c: c.quality_score)
        result.append(best)

    # Preserve original ordering (stable)
    card_id_order = {id(c): i for i, c in enumerate(cards)}
    result.sort(key=lambda c: card_id_order.get(id(c), len(cards)))
    return result


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def deduplicate(
    records: list[RawLiteratureRecord],
    threshold: float = 0.9,
) -> tuple[list[RawLiteratureRecord], DeduplicationReport]:
    """Run the three-layer dedup pipeline (L1 + L2).

    L3 (claim-level) is designed to run separately via :func:`dedup_claims`
    after evidence cards have been generated.

    Returns the deduplicated records and a :class:`DeduplicationReport`.
    """
    input_count = len(records)

    # L1 -- primary key
    after_l1 = dedup_by_primary_key(records)
    l1_count = len(after_l1)

    # L2 -- similarity
    after_l2 = dedup_by_similarity(after_l1, threshold=threshold)
    l2_count = len(after_l2)

    # Invariants
    assert l2_count <= l1_count <= input_count, (
        f"Dedup invariant violated: l2={l2_count}, l1={l1_count}, input={input_count}"
    )

    # Compute removed keys
    kept_keys = {r.primary_key for r in after_l2}
    removed_keys = [
        r.primary_key for r in records if r.primary_key not in kept_keys
    ]

    report = DeduplicationReport(
        input_count=input_count,
        l1_count=l1_count,
        l2_count=l2_count,
        l3_count=0,  # filled after dedup_claims is called separately
        removed_keys=removed_keys,
    )

    return after_l2, report
