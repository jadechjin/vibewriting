"""Paper outline generation tools."""

from __future__ import annotations

from dataclasses import dataclass, field

from vibewriting.models.paper_state import PaperState, SectionState


SECTION_TYPES: list[tuple[str, str, str]] = [
    ("introduction", "引言", "sections/introduction.tex"),
    ("related-work", "相关工作", "sections/related-work.tex"),
    ("method", "方法", "sections/method.tex"),
    ("experiments", "实验", "sections/experiments.tex"),
    ("conclusion", "结论", "sections/conclusion.tex"),
    ("appendix", "附录", "sections/appendix.tex"),
]

EVIDENCE_TYPE_TO_SECTION: dict[str, list[str]] = {
    "survey": ["related-work"],
    "theoretical": ["introduction", "method"],
    "empirical": ["experiments", "related-work"],
    "meta-analysis": ["related-work", "introduction"],
}

ASSET_KIND_TO_SECTION: dict[str, list[str]] = {
    "figure": ["experiments", "method"],
    "table": ["experiments", "method"],
}


@dataclass
class OutlineSection:
    """A section in the paper outline."""

    section_id: str
    title: str
    key_points: list[str] = field(default_factory=list)
    suggested_claim_ids: list[str] = field(default_factory=list)
    suggested_asset_ids: list[str] = field(default_factory=list)
    section_type: str = ""
    tex_file: str = ""


@dataclass
class PaperOutline:
    """Complete paper outline."""

    title: str
    topic: str
    abstract_draft: str = ""
    sections: list[OutlineSection] = field(default_factory=list)


def build_default_outline(
    topic: str,
    title: str,
    evidence_cards: list[dict] | None = None,
    asset_manifest: list[dict] | None = None,
) -> PaperOutline:
    """Build a default 6-section outline.

    - Uses fixed section structure matching paper/sections/
    - Distributes evidence cards by evidence_type
    - Distributes assets by kind to experiments/method sections

    Args:
        topic: Research topic.
        title: Paper title.
        evidence_cards: List of evidence card dicts with 'claim_id', 'evidence_type', 'tags'.
        asset_manifest: List of asset dicts with 'asset_id', 'kind'.
    """
    cards = evidence_cards or []
    assets = asset_manifest or []

    sections = []
    for section_type, default_title, tex_file in SECTION_TYPES:
        suggested_claims = _distribute_claims(cards, section_type)
        suggested_assets = _distribute_assets(assets, section_type)
        sections.append(OutlineSection(
            section_id=section_type,
            title=default_title,
            section_type=section_type,
            tex_file=tex_file,
            suggested_claim_ids=suggested_claims,
            suggested_asset_ids=suggested_assets,
        ))

    return PaperOutline(
        title=title,
        topic=topic,
        sections=sections,
    )


def _distribute_claims(cards: list[dict], section_type: str) -> list[str]:
    """Distribute evidence card claim_ids to a section based on evidence_type."""
    result = []
    for card in cards:
        etype = card.get("evidence_type", "")
        target_sections = EVIDENCE_TYPE_TO_SECTION.get(etype, [])
        if section_type in target_sections:
            claim_id = card.get("claim_id", "")
            if claim_id:
                result.append(claim_id)
    return result


def _distribute_assets(assets: list[dict], section_type: str) -> list[str]:
    """Distribute asset_ids to a section based on asset kind."""
    result = []
    for asset in assets:
        kind = asset.get("kind", "")
        target_sections = ASSET_KIND_TO_SECTION.get(kind, [])
        if section_type in target_sections:
            asset_id = asset.get("asset_id", "")
            if asset_id:
                result.append(asset_id)
    return result


def outline_to_paper_state(outline: PaperOutline, paper_id: str) -> PaperState:
    """Convert a PaperOutline to PaperState in 'outline' phase."""
    sections = outline_to_sections(outline)
    return PaperState(
        paper_id=paper_id,
        title=outline.title,
        topic=outline.topic,
        phase="outline",
        abstract=outline.abstract_draft,
        sections=sections,
    )


def outline_to_sections(outline: PaperOutline) -> list[SectionState]:
    """Convert outline sections to SectionState list."""
    return [
        SectionState(
            section_id=s.section_id,
            title=s.title,
            outline=s.key_points,
            status="planned",
            claim_ids=s.suggested_claim_ids,
            asset_ids=s.suggested_asset_ids,
            tex_file=s.tex_file,
        )
        for s in outline.sections
    ]
