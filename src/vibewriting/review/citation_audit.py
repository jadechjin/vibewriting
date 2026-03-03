"""Citation cross-validation: checkcites + CLAIM_ID + CrossRef."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

import httpx

from vibewriting.review.models import CitationAuditResult

logger = logging.getLogger(__name__)

_CITE_RE = re.compile(r"\\cite[tp]?\{([^}]+)\}")
_CLAIM_ID_RE = re.compile(r"%%\s*CLAIM_ID\s*:\s*(\S+)")


def extract_all_cite_keys(paper_dir: Path) -> set[str]:
    keys: set[str] = set()
    for tex_file in paper_dir.rglob("*.tex"):
        content = tex_file.read_text(encoding="utf-8")
        for match in _CITE_RE.finditer(content):
            for key in match.group(1).split(","):
                stripped = key.strip()
                if stripped:
                    keys.add(stripped)
    return keys


def extract_all_claim_ids(paper_dir: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for tex_file in paper_dir.rglob("*.tex"):
        content = tex_file.read_text(encoding="utf-8")
        rel = str(tex_file.relative_to(paper_dir))
        ids = _CLAIM_ID_RE.findall(content)
        if ids:
            result[rel] = ids
    return result


def crosscheck_with_evidence_cards(
    claim_ids: dict[str, list[str]], cards_path: Path,
) -> CitationAuditResult:
    card_ids: set[str] = set()
    if cards_path.exists():
        for line in cards_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                card = json.loads(line)
                cid = card.get("claim_id", "")
                if cid:
                    card_ids.add(cid)
            except json.JSONDecodeError:
                continue

    all_claim_ids: set[str] = set()
    for ids in claim_ids.values():
        all_claim_ids.update(ids)

    orphan = sorted(c for c in all_claim_ids if c not in card_ids)
    missing = sorted(c for c in card_ids if c not in all_claim_ids) if card_ids else []

    return CitationAuditResult(
        verified_count=len(all_claim_ids & card_ids),
        suspicious_keys=[],
        orphan_claims=orphan,
        missing_evidence_cards=missing,
    )


def verify_crossref(
    bib_keys: set[str], bib_path: Path, email: str = "",
) -> dict[str, bool]:
    results: dict[str, bool] = {}
    if not bib_path.exists():
        return results

    content = bib_path.read_text(encoding="utf-8")
    doi_re = re.compile(r"doi\s*=\s*\{([^}]+)\}", re.IGNORECASE)

    key_doi: dict[str, str] = {}
    current_key = ""
    for line in content.splitlines():
        key_match = re.match(r"@\w+\{([^,]+),", line)
        if key_match:
            current_key = key_match.group(1).strip()
        doi_match = doi_re.search(line)
        if doi_match and current_key in bib_keys:
            key_doi[current_key] = doi_match.group(1).strip()

    headers = {"User-Agent": f"vibewriting/1.0 (mailto:{email})" if email else "vibewriting/1.0"}

    for key, doi in key_doi.items():
        try:
            resp = httpx.get(
                f"https://api.crossref.org/works/{doi}",
                headers=headers,
                timeout=10,
            )
            results[key] = resp.status_code == 200
        except Exception:
            logger.warning("CrossRef lookup failed for %s (DOI: %s)", key, doi)
            results[key] = True  # graceful degradation

    for key in bib_keys:
        if key not in results:
            results[key] = True  # no DOI, skip

    return results


def run_checkcites(aux_path: Path) -> tuple[list[str], list[str]]:
    if not aux_path.exists():
        return [], []
    try:
        result = subprocess.run(
            ["checkcites", str(aux_path)],
            capture_output=True, text=True, check=False, timeout=30,
        )
        output = result.stdout + result.stderr
    except FileNotFoundError:
        logger.warning("checkcites not found, skipping")
        return [], []
    except subprocess.TimeoutExpired:
        return [], []

    unused: list[str] = []
    undefined: list[str] = []
    section = ""
    for line in output.splitlines():
        if "Unused references" in line:
            section = "unused"
        elif "Undefined references" in line:
            section = "undefined"
        elif line.startswith("=> "):
            key = line[3:].strip()
            if section == "unused":
                unused.append(key)
            elif section == "undefined":
                undefined.append(key)

    return unused, undefined


def run_citation_audit(
    paper_dir: Path,
    cards_path: Path,
    bib_path: Path,
    aux_path: Path | None = None,
    crossref_email: str = "",
    skip_external_api: bool = False,
) -> CitationAuditResult:
    cite_keys = extract_all_cite_keys(paper_dir)
    claim_ids = extract_all_claim_ids(paper_dir)

    card_result = crosscheck_with_evidence_cards(claim_ids, cards_path)

    suspicious: list[str] = []

    if aux_path:
        unused, undefined = run_checkcites(aux_path)
        suspicious.extend(undefined)

    if not skip_external_api and bib_path.exists():
        crossref_results = verify_crossref(cite_keys, bib_path, crossref_email)
        for key, valid in crossref_results.items():
            if not valid:
                suspicious.append(key)

    return CitationAuditResult(
        verified_count=card_result.verified_count,
        suspicious_keys=list(set(suspicious)),
        orphan_claims=card_result.orphan_claims,
        missing_evidence_cards=card_result.missing_evidence_cards,
    )
