"""Parity checks between format-neutral IR and paper_state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vibewriting.models.paper_state import PaperState
from vibewriting.rendering.ir import DocumentIR


def _section_map_from_state(state: PaperState) -> dict[str, Any]:
    return {section.section_id: section for section in state.sections}


def build_parity_report(document_ir: DocumentIR, state: PaperState) -> dict[str, Any]:
    """Build parity report between IR and PaperState section-level payloads."""
    state_sections = _section_map_from_state(state)
    section_reports: list[dict[str, Any]] = []
    all_match = True

    for ir_section in document_ir.sections:
        state_section = state_sections.get(ir_section.section_id)
        if state_section is None:
            all_match = False
            section_reports.append({
                "section_id": ir_section.section_id,
                "exists_in_paper_state": False,
                "claims_match": False,
                "assets_match": False,
                "citations_match": False,
            })
            continue

        claims_match = set(ir_section.claim_ids) == set(state_section.claim_ids)
        assets_match = set(ir_section.asset_ids) == set(state_section.asset_ids)
        citations_match = set(ir_section.citation_keys) == set(state_section.citation_keys)
        section_all_match = claims_match and assets_match and citations_match
        all_match = all_match and section_all_match

        section_reports.append({
            "section_id": ir_section.section_id,
            "exists_in_paper_state": True,
            "claims_match": claims_match,
            "assets_match": assets_match,
            "citations_match": citations_match,
            "ir_claim_count": len(ir_section.claim_ids),
            "state_claim_count": len(state_section.claim_ids),
            "ir_asset_count": len(ir_section.asset_ids),
            "state_asset_count": len(state_section.asset_ids),
            "ir_citation_count": len(ir_section.citation_keys),
            "state_citation_count": len(state_section.citation_keys),
        })

    return {
        "paper_id": document_ir.paper_id,
        "all_match": all_match,
        "section_count": len(document_ir.sections),
        "sections": section_reports,
    }


def write_parity_report(report: dict[str, Any], path: Path) -> Path:
    """Persist parity report to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path

