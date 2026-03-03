"""Section task planner for multi-agent orchestration.

Builds a task graph from PaperState, assigns agent roles to sections,
and resolves dependencies for layered execution.
"""

from __future__ import annotations

import logging

from vibewriting.agents.contracts import AgentRole, SectionTask
from vibewriting.models.paper_state import PaperState

logger = logging.getLogger(__name__)

# Section type -> default agent roles
# introduction/related-work -> Storyteller primary
# method -> Storyteller primary
# experiments -> Analyst primary
# conclusion -> Storyteller primary
# All sections -> Critic + Formatter pass
SECTION_ROLE_MAP: dict[str, list[AgentRole]] = {
    "introduction": [AgentRole.STORYTELLER],
    "related-work": [AgentRole.STORYTELLER],
    "method": [AgentRole.STORYTELLER],
    "experiments": [AgentRole.ANALYST],
    "conclusion": [AgentRole.STORYTELLER],
    "appendix": [AgentRole.ANALYST],
}

# Section dependencies: section_type -> must be after these section_types
# method should be written before introduction is finalized
# experiments depends on method
SECTION_DEPENDENCIES: dict[str, list[str]] = {
    "introduction": ["method"],  # intro 需等 method 确定
    "conclusion": ["experiments", "method"],  # conclusion 需等实验和方法确定
    "related-work": [],
    "method": [],
    "experiments": ["method"],
    "appendix": [],
}


def _infer_section_type(section_id: str) -> str:
    """Infer section type from section_id.

    Uses simple keyword matching on section_id.
    Falls back to "appendix" if no match.
    """
    section_id_lower = section_id.lower()
    for section_type in [
        "introduction",
        "related-work",
        "method",
        "experiments",
        "conclusion",
        "appendix",
    ]:
        if section_type in section_id_lower:
            return section_type
    # Additional aliases
    if "intro" in section_id_lower:
        return "introduction"
    if "related" in section_id_lower:
        return "related-work"
    if "experiment" in section_id_lower or "result" in section_id_lower:
        return "experiments"
    if "conclu" in section_id_lower:
        return "conclusion"
    return "appendix"


def assign_roles(section_type: str) -> list[AgentRole]:
    """Return the default agent roles for a given section type."""
    return list(SECTION_ROLE_MAP.get(section_type, [AgentRole.STORYTELLER]))


def build_section_task_graph(
    state: PaperState,
    evidence_cards: list[dict] | None = None,
    asset_manifest: list[dict] | None = None,
) -> list[SectionTask]:
    """Build a task graph from PaperState.

    For each section:
    1. Infer section type from section_id
    2. Assign primary agent role
    3. Filter relevant evidence cards (by claim_ids)
    4. Filter relevant assets (by asset_ids)
    5. Set dependencies based on section type ordering

    Args:
        state: Current paper state.
        evidence_cards: All available evidence cards.
        asset_manifest: All available data assets.

    Returns:
        List of SectionTask objects in dependency order.
    """
    evidence_cards = evidence_cards or []
    asset_manifest = asset_manifest or []

    # Build section_id -> section_type mapping
    section_types: dict[str, str] = {}
    for section in state.sections:
        section_types[section.section_id] = _infer_section_type(section.section_id)

    # Build section_type -> section_ids mapping (for dependency resolution)
    type_to_ids: dict[str, list[str]] = {}
    for sid, stype in section_types.items():
        type_to_ids.setdefault(stype, []).append(sid)

    # Build evidence card lookup
    ec_lookup: dict[str, dict] = {}
    for ec in evidence_cards:
        claim_id = ec.get("claim_id", "")
        if claim_id:
            ec_lookup[claim_id] = ec

    # Build asset lookup
    asset_lookup: dict[str, dict] = {}
    for asset in asset_manifest:
        asset_id = asset.get("asset_id", "")
        if asset_id:
            asset_lookup[asset_id] = asset

    tasks: list[SectionTask] = []

    for section in state.sections:
        section_type = section_types[section.section_id]
        roles = assign_roles(section_type)

        # Filter evidence cards for this section
        section_evidence = [
            ec_lookup[cid] for cid in section.claim_ids if cid in ec_lookup
        ]

        # Filter assets for this section
        section_assets = [
            asset_lookup[aid] for aid in section.asset_ids if aid in asset_lookup
        ]

        # Resolve dependencies: find section_ids that this section depends on
        dep_types = SECTION_DEPENDENCIES.get(section_type, [])
        dep_ids: list[str] = []
        for dep_type in dep_types:
            dep_ids.extend(type_to_ids.get(dep_type, []))
        # Remove self-dependency
        dep_ids = [d for d in dep_ids if d != section.section_id]

        # Create task for primary role
        for role in roles:
            task = SectionTask(
                section_id=section.section_id,
                role=role,
                evidence_cards=section_evidence,
                assets=section_assets,
                context={
                    "title": section.title,
                    "outline": section.outline,
                    "section_type": section_type,
                },
                dependencies=dep_ids,
            )
            tasks.append(task)

    return tasks


def get_ready_tasks(
    tasks: list[SectionTask],
    completed_ids: set[str],
) -> list[SectionTask]:
    """Return tasks whose dependencies are all satisfied.

    A task is ready if all section_ids in its dependencies
    are present in completed_ids.
    """
    ready: list[SectionTask] = []
    for task in tasks:
        if all(dep in completed_ids for dep in task.dependencies):
            ready.append(task)
    return ready
