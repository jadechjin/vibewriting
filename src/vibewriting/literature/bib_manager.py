"""BibTeX management using bibtexparser 2.x.

Provides parsing, normalization, merge, and writing of .bib files.
All functions operate on the lightweight BibEntry dataclass, converting
to/from bibtexparser 2.x model objects only at I/O boundaries.
"""

from __future__ import annotations

import logging
import os
import re
import string
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import bibtexparser
from bibtexparser.library import Library
from bibtexparser.model import Entry, Field

import httpx

logger = logging.getLogger(__name__)

# ── Stop-words for cite key generation ──────────────────────────────
_STOP_WORDS = frozenset(
    {"the", "a", "an", "of", "for", "in", "on", "to", "and", "with", "is", "by", "from"}
)

# ── Dataclasses ─────────────────────────────────────────────────────


@dataclass
class BibEntry:
    """Lightweight representation of a single BibTeX entry."""

    key: str
    entry_type: str  # article, inproceedings, etc.
    fields: dict[str, str] = field(default_factory=dict)


@dataclass
class MergeReport:
    """Summary of a merge operation between two bib lists."""

    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


# ── Helpers ─────────────────────────────────────────────────────────


def _to_ascii(text: str) -> str:
    """Transliterate unicode to closest ASCII using NFKD decomposition.

    Strips combining characters (accents) after decomposition, then
    encodes to ASCII ignoring remaining non-ASCII bytes.
    """
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_bytes = nfkd.encode("ascii", "ignore")
    return ascii_bytes.decode("ascii")


def _extract_first_author_surname(author_field: str) -> str:
    """Extract the surname of the first author.

    Handles both ``Surname, Given`` and ``Given Surname`` formats,
    as well as ``and``-separated multi-author strings.
    """
    # Take the first author (split on " and ")
    first_author = re.split(r"\s+and\s+", author_field, maxsplit=1)[0].strip()

    if "," in first_author:
        # "Surname, Given" format
        surname = first_author.split(",")[0].strip()
    else:
        # "Given Surname" format – last token is the surname
        parts = first_author.split()
        surname = parts[-1] if parts else first_author

    # Remove braces that BibTeX sometimes uses
    surname = surname.replace("{", "").replace("}", "")
    return surname


def _first_keyword(title: str) -> str:
    """Return the first non-stop-word from a title, lowercased.

    Falls back to the very first word if every word is a stop-word.
    """
    # Strip braces and punctuation
    cleaned = title.replace("{", "").replace("}", "")
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    words = cleaned.lower().split()

    for word in words:
        if word not in _STOP_WORDS:
            return word

    # Fallback: return first word even if it is a stop-word
    return words[0] if words else "unknown"


# ── Public API ──────────────────────────────────────────────────────


def parse_bib(path: Path) -> list[BibEntry]:
    """Parse a .bib file into a list of :class:`BibEntry` objects.

    Uses ``bibtexparser.parse_file`` (2.x API).  Any blocks that failed
    to parse are logged as warnings and silently skipped.
    """
    library = bibtexparser.parse_file(str(path))

    if library.failed_blocks:
        logger.warning(
            "Failed to parse %d block(s) in %s",
            len(library.failed_blocks),
            path,
        )

    entries: list[BibEntry] = []
    for entry in library.entries:
        fields = {f.key: str(f.value) for f in entry.fields}
        entries.append(
            BibEntry(
                key=entry.key,
                entry_type=entry.entry_type,
                fields=fields,
            )
        )
    return entries


def normalize_entry(entry: BibEntry) -> BibEntry:
    """Return a new BibEntry with field names lowercased and values trimmed.

    The original *entry* is not mutated (immutable pattern).
    """
    normalized_fields: dict[str, str] = {}
    for k, v in entry.fields.items():
        clean_key = k.strip().lower()
        # Collapse internal whitespace runs and strip outer whitespace
        clean_value = " ".join(v.split())
        normalized_fields[clean_key] = clean_value

    return BibEntry(
        key=entry.key,
        entry_type=entry.entry_type.strip().lower(),
        fields=normalized_fields,
    )


def normalize_cite_key(
    entry: BibEntry,
    existing_keys: set[str] | None = None,
) -> str:
    """Generate a normalised cite key: ``<surname><year><keyword>``.

    Rules:
    * First-author surname -> ASCII transliterate -> lowercase
    * Year: 4-digit year from the ``year`` field
    * First non-stop-word from title, lowercased
    * If the key already exists in *existing_keys*, append ``a``, ``b``, ...

    Examples: ``vaswani2017attention``, ``devlin2019bert``
    """
    existing_keys = existing_keys or set()

    # -- surname --
    author = entry.fields.get("author", "")
    surname = _extract_first_author_surname(author) if author else "unknown"
    surname_ascii = _to_ascii(surname).lower()
    # Keep only alphabetic characters
    surname_ascii = re.sub(r"[^a-z]", "", surname_ascii) or "unknown"

    # -- year --
    year = entry.fields.get("year", "0000").strip()
    # Extract just the digits (handles e.g. "{2017}")
    year_digits = re.sub(r"[^0-9]", "", year)
    year_str = year_digits[:4] if len(year_digits) >= 4 else year_digits.ljust(4, "0")

    # -- keyword from title --
    title = entry.fields.get("title", "")
    keyword = _first_keyword(title) if title else "untitled"
    keyword_ascii = _to_ascii(keyword).lower()
    keyword_ascii = re.sub(r"[^a-z]", "", keyword_ascii) or "untitled"

    base_key = f"{surname_ascii}{year_str}{keyword_ascii}"

    if base_key not in existing_keys:
        return base_key

    # Resolve conflict by appending a, b, c, ...
    for suffix in string.ascii_lowercase:
        candidate = f"{base_key}{suffix}"
        if candidate not in existing_keys:
            return candidate

    # Extremely unlikely: 26 collisions
    raise ValueError(f"Cannot resolve cite key for base '{base_key}' after 26 attempts")


def doi_to_bibtex(doi: str) -> str | None:
    """Fetch a BibTeX string for *doi* from doi.org content negotiation.

    Returns ``None`` on any HTTP error, timeout (5 s), or non-2xx response.
    """
    url = f"https://doi.org/{doi}"
    headers = {"Accept": "application/x-bibtex"}
    try:
        response = httpx.get(url, headers=headers, timeout=5.0, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("doi_to_bibtex failed for %s: %s", doi, exc)
        return None


def merge_bib(
    existing: list[BibEntry],
    new: list[BibEntry],
) -> tuple[list[BibEntry], MergeReport]:
    """Merge *new* entries into *existing*, respecting manual-edit priority.

    Merge rules:
    * If a key from *new* is **not** in *existing* -> **add** (with
      ``note = {auto-generated}``).
    * If a key from *new* already exists in *existing* **and** the
      existing entry has ``note`` equal to ``auto-generated`` -> **update**
      (replace with new entry, keep auto-generated note).
    * If a key from *new* already exists but is **not** auto-generated ->
      **conflict**: the human-edited entry wins, new entry is discarded.

    Returns the merged list and a :class:`MergeReport`.
    """
    report = MergeReport()

    # Index existing entries by key for fast lookup
    merged: dict[str, BibEntry] = {e.key: e for e in existing}

    for entry in new:
        if entry.key not in merged:
            # New entry – mark as auto-generated
            new_fields = dict(entry.fields)
            new_fields["note"] = "auto-generated"
            merged[entry.key] = BibEntry(
                key=entry.key,
                entry_type=entry.entry_type,
                fields=new_fields,
            )
            report.added.append(entry.key)
        else:
            existing_entry = merged[entry.key]
            is_auto = existing_entry.fields.get("note", "").strip() == "auto-generated"
            if is_auto:
                # Update auto-generated entry
                new_fields = dict(entry.fields)
                new_fields["note"] = "auto-generated"
                merged[entry.key] = BibEntry(
                    key=entry.key,
                    entry_type=entry.entry_type,
                    fields=new_fields,
                )
                report.updated.append(entry.key)
            else:
                # Human-edited entry wins
                report.conflicts.append(entry.key)

    return list(merged.values()), report


def write_bib(entries: list[BibEntry], path: Path) -> None:
    """Write *entries* to a .bib file using bibtexparser 2.x.

    * Entries are sorted by key (alphabetical, ascending).
    * Uses atomic write: writes to ``<path>.tmp`` then renames.
    * Output is UTF-8 encoded.
    """
    # Sort entries alphabetically by key
    sorted_entries = sorted(entries, key=lambda e: e.key)

    # Convert BibEntry -> bibtexparser Entry
    bp_entries: list[Entry] = []
    for bib_entry in sorted_entries:
        fields = [
            Field(key=k, value=v)
            for k, v in bib_entry.fields.items()
        ]
        bp_entries.append(
            Entry(
                entry_type=bib_entry.entry_type,
                key=bib_entry.key,
                fields=fields,
            )
        )

    library = Library(bp_entries)
    bibtex_str = bibtexparser.write_string(library)

    # Atomic write: write to .tmp then rename
    tmp_path = path.with_suffix(".bib.tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(bibtex_str, encoding="utf-8")
    # os.replace is atomic on POSIX; best-effort on Windows
    os.replace(str(tmp_path), str(path))
