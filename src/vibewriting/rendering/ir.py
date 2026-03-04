"""Format-neutral intermediate representation (IR) for paper outputs."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from vibewriting.models.paper_state import PaperState, SectionState
from vibewriting.writing.latex_helpers import split_into_paragraphs, strip_claim_annotations

_CITE_RE = re.compile(r"\\cite[tp]?\{([^}]+)\}")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _extract_citation_keys(text: str) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for match in _CITE_RE.finditer(text):
        for raw_key in match.group(1).split(","):
            key = raw_key.strip()
            if key and key not in seen:
                keys.append(key)
                seen.add(key)
    return keys


class ParagraphBlockIR(BaseModel):
    """A paragraph-level semantic block."""

    model_config = ConfigDict(extra="forbid")

    block_type: str = "paragraph"
    text: str = ""
    citation_keys: list[str] = Field(default_factory=list)


class SectionIR(BaseModel):
    """A section in the format-neutral document representation."""

    model_config = ConfigDict(extra="forbid")

    section_id: str
    title: str
    source_tex_file: str
    claim_ids: list[str] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)
    citation_keys: list[str] = Field(default_factory=list)
    blocks: list[ParagraphBlockIR] = Field(default_factory=list)


class DocumentIR(BaseModel):
    """Top-level format-neutral representation for a paper."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    title: str
    topic: str
    language: str = "zh"
    created_at: datetime = Field(default_factory=_utcnow)
    sections: list[SectionIR] = Field(default_factory=list)


def _section_to_ir(section: SectionState, paper_dir: Path) -> SectionIR:
    tex_path = paper_dir / section.tex_file
    content = ""
    if tex_path.exists():
        content = tex_path.read_text(encoding="utf-8")

    cleaned = strip_claim_annotations(content)
    paragraphs = split_into_paragraphs(cleaned)
    blocks = [
        ParagraphBlockIR(
            text=paragraph,
            citation_keys=_extract_citation_keys(paragraph),
        )
        for paragraph in paragraphs
    ]

    derived_citations = _extract_citation_keys(cleaned)
    if section.citation_keys:
        # Keep PaperState as source of truth when available.
        citation_keys = list(dict.fromkeys(section.citation_keys))
    else:
        citation_keys = derived_citations

    return SectionIR(
        section_id=section.section_id,
        title=section.title,
        source_tex_file=section.tex_file,
        claim_ids=list(section.claim_ids),
        asset_ids=list(section.asset_ids),
        citation_keys=citation_keys,
        blocks=blocks,
    )


def build_document_ir_from_paper_state(
    state: PaperState,
    paper_dir: Path,
    language: str | None = None,
) -> DocumentIR:
    """Build DocumentIR from PaperState + current section .tex files."""
    sections = [_section_to_ir(section, paper_dir) for section in state.sections]
    return DocumentIR(
        paper_id=state.paper_id,
        title=state.title,
        topic=state.topic,
        language=language or "zh",
        sections=sections,
    )


def write_document_ir(document_ir: DocumentIR, path: Path) -> Path:
    """Persist DocumentIR to JSON with UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        document_ir.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return path


def load_document_ir(path: Path) -> DocumentIR:
    """Load DocumentIR from JSON path."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return DocumentIR.model_validate(data)

