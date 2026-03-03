"""Full end-to-end contract integrity validation."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from vibewriting.contracts.integrity import (
    IntegrityViolation,
    _extract_bib_keys,
    validate_referential_integrity,
)

_CITE_RE = re.compile(r"\\cite[tp]?\{([^}]+)\}")


def validate_all_tex_citations(
    paper_dir: Path, bib_path: Path,
) -> list[IntegrityViolation]:
    bib_keys = _extract_bib_keys(bib_path)
    violations: list[IntegrityViolation] = []

    for tex_file in paper_dir.rglob("*.tex"):
        content = tex_file.read_text(encoding="utf-8")
        rel = str(tex_file.relative_to(paper_dir))
        for match in _CITE_RE.finditer(content):
            for key in match.group(1).split(","):
                k = key.strip()
                if k and k not in bib_keys:
                    violations.append(IntegrityViolation(
                        source=f"tex:{rel}",
                        field="citation_key",
                        missing_key=k,
                        target="references.bib",
                    ))
    return violations


def validate_asset_hashes(
    asset_manifest: list[dict[str, Any]], output_dir: Path,
) -> list[IntegrityViolation]:
    violations: list[IntegrityViolation] = []
    for asset in asset_manifest:
        asset_id = asset.get("asset_id", "<unknown>")
        rel_path = asset.get("file_path", "")
        expected_hash = asset.get("content_hash", "")

        full_path = output_dir / rel_path
        if not full_path.exists():
            violations.append(IntegrityViolation(
                source=f"asset:{asset_id}",
                field="file_path",
                missing_key=rel_path,
                target="output_dir",
            ))
            continue

        if expected_hash:
            actual_hash = hashlib.sha256(
                full_path.read_bytes()
            ).hexdigest()
            if actual_hash != expected_hash:
                violations.append(IntegrityViolation(
                    source=f"asset:{asset_id}",
                    field="content_hash",
                    missing_key=f"expected={expected_hash[:12]}...",
                    target=rel_path,
                ))

    return violations


def validate_sections_complete(
    paper_state: dict[str, Any],
) -> list[IntegrityViolation]:
    violations: list[IntegrityViolation] = []
    for section in paper_state.get("sections", []):
        sid = section.get("section_id", "<unknown>")
        status = section.get("status", "")
        if status != "complete":
            violations.append(IntegrityViolation(
                source=f"section:{sid}",
                field="status",
                missing_key=status or "<empty>",
                target="expected:complete",
            ))
    return violations


def validate_glossary_in_tex(
    glossary: dict[str, Any], paper_dir: Path,
) -> list[IntegrityViolation]:
    violations: list[IntegrityViolation] = []
    entries = glossary.get("entries", {})

    all_tex = ""
    for tex_file in paper_dir.rglob("*.tex"):
        all_tex += tex_file.read_text(encoding="utf-8") + "\n"

    for term_id, entry in entries.items():
        term = entry.get("term", term_id)
        if term.lower() not in all_tex.lower():
            violations.append(IntegrityViolation(
                source="glossary",
                field="term",
                missing_key=term_id,
                target="tex_files",
            ))
    return violations


def validate_symbols_in_tex(
    symbols: dict[str, Any], paper_dir: Path,
) -> list[IntegrityViolation]:
    violations: list[IntegrityViolation] = []
    entries = symbols.get("entries", {})

    all_tex = ""
    for tex_file in paper_dir.rglob("*.tex"):
        all_tex += tex_file.read_text(encoding="utf-8") + "\n"

    for sym_id, entry in entries.items():
        latex_cmd = entry.get("latex", sym_id)
        if latex_cmd not in all_tex:
            violations.append(IntegrityViolation(
                source="symbols",
                field="latex",
                missing_key=sym_id,
                target="tex_files",
            ))
    return violations


def validate_end_to_end(
    paper_dir: Path,
    output_dir: Path,
    data_dir: Path,
    paper_state: dict[str, Any] | None = None,
    evidence_cards: list[dict[str, Any]] | None = None,
    asset_manifest: list[dict[str, Any]] | None = None,
    glossary: dict[str, Any] | None = None,
    symbols: dict[str, Any] | None = None,
    bib_path: Path | None = None,
) -> list[IntegrityViolation]:
    violations: list[IntegrityViolation] = []

    if bib_path and bib_path.exists():
        violations.extend(validate_all_tex_citations(paper_dir, bib_path))

    if asset_manifest:
        violations.extend(validate_asset_hashes(asset_manifest, output_dir))

    if paper_state:
        violations.extend(validate_sections_complete(paper_state))

        if evidence_cards is not None or asset_manifest is not None:
            violations.extend(validate_referential_integrity(
                paper_state,
                evidence_cards or [],
                asset_manifest or [],
                glossary=glossary,
                symbols=symbols,
                bib_path=bib_path,
            ))

    if glossary:
        violations.extend(validate_glossary_in_tex(glossary, paper_dir))

    if symbols:
        violations.extend(validate_symbols_in_tex(symbols, paper_dir))

    return violations
