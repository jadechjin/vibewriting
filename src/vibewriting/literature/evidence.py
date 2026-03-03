"""Evidence Card generation and claim_id management.

Provides utilities to:
- Generate monotonically increasing claim IDs within a calendar year.
- Compute deterministic content hashes for deduplication.
- Create EvidenceCard instances from raw literature records.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from vibewriting.literature.models import RawLiteratureRecord
from vibewriting.models.evidence_card import EvidenceCard


def next_claim_id(existing_cards: list[EvidenceCard]) -> str:
    """Return the next claim ID in ``EC-{year}-{NNN:03d}`` format.

    Scans *existing_cards* for the maximum sequence number issued in the
    current calendar year and returns the next value.  If no cards exist
    for the current year the sequence starts at ``001``.

    Parameters
    ----------
    existing_cards:
        Previously issued evidence cards (may span multiple years).

    Returns
    -------
    str
        A claim ID such as ``EC-2026-006``.
    """
    current_year = datetime.now(UTC).year
    year_prefix = f"EC-{current_year}-"

    max_seq = 0
    for card in existing_cards:
        if card.claim_id.startswith(year_prefix):
            seq = int(card.claim_id.split("-")[2])
            if seq > max_seq:
                max_seq = seq

    return f"EC-{current_year}-{max_seq + 1:03d}"


def compute_content_hash(claim_text: str) -> str:
    """Return the first 16 hex characters of the SHA-256 hash of *claim_text*.

    Parameters
    ----------
    claim_text:
        The claim text to hash.  Encoded as UTF-8 before hashing.

    Returns
    -------
    str
        A 16-character lowercase hexadecimal string.
    """
    digest = hashlib.sha256(claim_text.encode("utf-8")).hexdigest()
    return digest[:16]


def create_evidence_card(
    raw_record: RawLiteratureRecord,
    claim_text: str,
    supporting_quote: str,
    bib_key: str,
    evidence_type: str,
    existing_cards: list[EvidenceCard] | None = None,
    **kwargs,
) -> EvidenceCard:
    """Build an :class:`EvidenceCard` from a raw literature record.

    Automatically populates derived fields:

    * ``claim_id`` -- next monotonic ID via :func:`next_claim_id`.
    * ``content_hash`` -- SHA-256 prefix via :func:`compute_content_hash`.
    * ``retrieved_at`` -- current UTC timestamp.
    * ``paraphrase`` -- set to ``True`` when *supporting_quote* exceeds
      50 words.
    * ``source_id`` -- taken from ``raw_record.primary_key``.
    * ``retrieval_source`` -- taken from ``raw_record.source``.

    Parameters
    ----------
    raw_record:
        The literature record providing provenance metadata.
    claim_text:
        The claim being asserted.
    supporting_quote:
        A direct quote or close paraphrase from the source.
    bib_key:
        The BibTeX citation key (e.g. ``"smith2024deep"``).
    evidence_type:
        One of ``"empirical"``, ``"theoretical"``, ``"survey"``,
        ``"meta-analysis"``.
    existing_cards:
        Previously issued cards, used to derive the next claim ID.
        Defaults to an empty list.
    **kwargs:
        Additional fields forwarded to the :class:`EvidenceCard`
        constructor (e.g. ``quality_score``, ``tags``,
        ``methodology_notes``, ``key_statistics``, ``location``).

    Returns
    -------
    EvidenceCard
        A fully populated evidence card ready for persistence.
    """
    if existing_cards is None:
        existing_cards = []

    claim_id = next_claim_id(existing_cards)
    content_hash = compute_content_hash(claim_text)

    paraphrase = len(supporting_quote.split()) > 50

    return EvidenceCard(
        claim_id=claim_id,
        claim_text=claim_text,
        supporting_quote=supporting_quote,
        paraphrase=paraphrase,
        bib_key=bib_key,
        evidence_type=evidence_type,
        source_id=raw_record.primary_key,
        retrieval_source=raw_record.source,
        content_hash=content_hash,
        **kwargs,
    )
