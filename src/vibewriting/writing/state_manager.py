"""Paper state manager with atomic persistence and immutable updates."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from vibewriting.models.paper_state import PaperMetrics, PaperState, SectionState

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PaperStateManager:
    """Manages paper_state.json with atomic writes and immutable updates.

    All state-modifying methods return a NEW PaperState instance.
    The save() method uses atomic write (tmp + rename) for safety.
    """

    def __init__(self, state_path: Path) -> None:
        self._path = state_path

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> PaperState | None:
        """Load PaperState from JSON file. Returns None if file doesn't exist."""
        if not self._path.exists():
            return None
        content = self._path.read_text(encoding="utf-8")
        return PaperState.model_validate_json(content)

    def save(self, state: PaperState) -> None:
        """Atomically write PaperState to JSON file.

        Writes to a .tmp file first, then renames to final path.
        Creates parent directories if needed.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(".tmp")
        data = state.model_dump_json(indent=2)
        tmp_path.write_text(data, encoding="utf-8")
        tmp_path.replace(self._path)

    def create(
        self,
        paper_id: str,
        title: str,
        topic: str,
        sections: list[dict],
    ) -> PaperState:
        """Create a new PaperState in 'outline' phase.

        Args:
            paper_id: Unique paper identifier.
            title: Paper title.
            topic: Research topic.
            sections: List of section dicts, each with at minimum:
                - section_id: str
                - title: str
                - tex_file: str
                Optional:
                - outline: list[str]
                - claim_ids, asset_ids, citation_keys: list[str]
        """
        section_states = [SectionState(**s) for s in sections]
        now = _utcnow()
        return PaperState(
            paper_id=paper_id,
            title=title,
            topic=topic,
            phase="outline",
            sections=section_states,
            created_at=now,
            updated_at=now,
        )

    def update_section_status(
        self,
        state: PaperState,
        section_id: str,
        new_status: str,
    ) -> PaperState:
        """Return new PaperState with updated section status (immutable)."""
        new_sections = []
        for s in state.sections:
            if s.section_id == section_id:
                new_sections.append(s.model_copy(update={"status": new_status}))
            else:
                new_sections.append(s)
        return state.model_copy(update={
            "sections": new_sections,
            "updated_at": _utcnow(),
        })

    def update_metrics(self, state: PaperState, metrics: PaperMetrics) -> PaperState:
        """Return new PaperState with updated metrics (immutable)."""
        return state.model_copy(update={
            "metrics": metrics,
            "updated_at": _utcnow(),
        })

    def advance_phase(self, state: PaperState) -> PaperState:
        """Advance paper phase: outline -> drafting -> review -> complete.

        Returns new PaperState. Raises ValueError if already complete.
        """
        transitions = {
            "outline": "drafting",
            "drafting": "review",
            "review": "complete",
        }
        if state.phase not in transitions:
            raise ValueError(f"Cannot advance from phase '{state.phase}'")
        return state.model_copy(update={
            "phase": transitions[state.phase],
            "updated_at": _utcnow(),
        })

    def add_claim_to_section(
        self,
        state: PaperState,
        section_id: str,
        claim_id: str,
    ) -> PaperState:
        """Return new PaperState with claim_id added to section (immutable).

        Does not add duplicates.
        """
        new_sections = []
        for s in state.sections:
            if s.section_id == section_id:
                if claim_id not in s.claim_ids:
                    new_claims = [*s.claim_ids, claim_id]
                    new_sections.append(s.model_copy(update={"claim_ids": new_claims}))
                else:
                    new_sections.append(s)
            else:
                new_sections.append(s)
        return state.model_copy(update={
            "sections": new_sections,
            "updated_at": _utcnow(),
        })

    def add_asset_to_section(
        self,
        state: PaperState,
        section_id: str,
        asset_id: str,
    ) -> PaperState:
        """Return new PaperState with asset_id added to section (immutable).

        Does not add duplicates.
        """
        new_sections = []
        for s in state.sections:
            if s.section_id == section_id:
                if asset_id not in s.asset_ids:
                    new_assets = [*s.asset_ids, asset_id]
                    new_sections.append(s.model_copy(update={"asset_ids": new_assets}))
                else:
                    new_sections.append(s)
            else:
                new_sections.append(s)
        return state.model_copy(update={
            "sections": new_sections,
            "updated_at": _utcnow(),
        })

    def update_section_payload(
        self,
        state: PaperState,
        section_id: str,
        claim_ids: list[str] | None = None,
        asset_ids: list[str] | None = None,
        citation_keys: list[str] | None = None,
        word_count: int | None = None,
        paragraph_count: int | None = None,
    ) -> PaperState:
        """Batch update multiple fields on a section (immutable).

        Only updates fields that are not None.
        Returns new PaperState.
        """
        new_sections = []
        for s in state.sections:
            if s.section_id == section_id:
                patch: dict = {}
                if claim_ids is not None:
                    patch["claim_ids"] = claim_ids
                if asset_ids is not None:
                    patch["asset_ids"] = asset_ids
                if citation_keys is not None:
                    patch["citation_keys"] = citation_keys
                if word_count is not None:
                    patch["word_count"] = word_count
                if paragraph_count is not None:
                    patch["paragraph_count"] = paragraph_count
                new_sections.append(s.model_copy(update=patch))
            else:
                new_sections.append(s)
        return state.model_copy(update={
            "sections": new_sections,
            "updated_at": _utcnow(),
        })

    def set_current_section_index(self, state: PaperState, index: int) -> PaperState:
        """Set the current section index (immutable).

        Raises ValueError if index is out of range.
        Returns new PaperState.
        """
        if index < 0 or index >= len(state.sections):
            raise ValueError(
                f"Section index {index} out of range [0, {len(state.sections) - 1}]"
            )
        return state.model_copy(update={
            "current_section_index": index,
            "updated_at": _utcnow(),
        })

    def batch_update_sections(
        self,
        state: PaperState,
        updates: dict[str, dict],
    ) -> PaperState:
        """Batch update multiple sections at once (immutable).

        Args:
            state: Current paper state.
            updates: {section_id: {field: value}} mapping.
                Valid fields: status, claim_ids, asset_ids, citation_keys,
                             word_count, paragraph_count

        Returns new PaperState with all updates applied.
        Ignores section_ids not found in state.
        """
        new_sections = []
        for s in state.sections:
            if s.section_id in updates:
                patch = updates[s.section_id]
                new_sections.append(s.model_copy(update=patch))
            else:
                new_sections.append(s)
        return state.model_copy(update={
            "sections": new_sections,
            "updated_at": _utcnow(),
        })
