"""Orchestrator core for multi-agent writing coordination.

The orchestrator is the single file writer. Role agents return payloads;
the orchestrator validates, merges, and persists.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from vibewriting.agents.contracts import (
    MergeDecision,
    OrchestrationReport,
    OrchestrationRound,
    SectionPatchPayload,
    SectionTask,
)
from vibewriting.agents.executor import AgentExecutor, TaskResult
from vibewriting.agents.merge_protocol import (
    apply_merge,
    detect_conflicts,
    resolve_conflicts,
    validate_patch_payload,
)
from vibewriting.agents.planner import build_section_task_graph, get_ready_tasks
from vibewriting.models.glossary import Glossary, SymbolTable
from vibewriting.models.paper_state import PaperState
from vibewriting.writing.quality_gates import GateReport, run_all_gates
from vibewriting.writing.state_manager import PaperStateManager

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorConfig:
    """Configuration for the WritingOrchestrator."""

    max_rounds: int = 3
    max_retries_per_section: int = 2
    enable_git_snapshots: bool = True
    executor_type: str = "mock"  # "mock" | "subagent" | "team"


class WritingOrchestrator:
    """Core orchestrator for multi-agent paper writing.

    The orchestrator coordinates the writing process:
    1. Build section task graph from PaperState
    2. Dispatch tasks to agent executor (by dependency layers)
    3. Validate and merge returned payloads
    4. Run quality gates
    5. Persist results

    The orchestrator is the ONLY entity that writes to files.
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        state_manager: PaperStateManager,
        executor: AgentExecutor,
        paper_dir: Path,
        output_dir: Path,
    ) -> None:
        self._config = config
        self._state_manager = state_manager
        self._executor = executor
        self._paper_dir = paper_dir
        self._output_dir = output_dir

    async def run(
        self,
        state: PaperState,
        evidence_cards: list[dict] | None = None,
        asset_manifest: list[dict] | None = None,
        glossary: Glossary | None = None,
        symbols: SymbolTable | None = None,
        bib_keys: set[str] | None = None,
    ) -> OrchestrationReport:
        """Run the full orchestration process.

        Steps:
        1. Build task graph
        2. For each dependency layer:
           a. Get ready tasks
           b. Dispatch to executor
           c. Validate payloads
           d. Detect and resolve conflicts
           e. Apply merges
           f. Run quality gates
           g. Update state
        3. Return report
        """
        started_at = datetime.now(UTC)
        evidence_cards = evidence_cards or []
        asset_manifest = asset_manifest or []

        # Build lookup sets for validation
        allowed_claim_ids = {ec.get("claim_id", "") for ec in evidence_cards} - {""}
        allowed_asset_ids = {a.get("asset_id", "") for a in asset_manifest} - {""}

        # Build task graph
        tasks = build_section_task_graph(state, evidence_cards, asset_manifest)
        total_sections = len(state.sections)

        rounds: list[OrchestrationRound] = []
        completed_ids: set[str] = set()
        all_conflicts = 0
        all_unresolved = 0
        round_number = 0
        final_gate_summary = ""

        for _ in range(self._config.max_rounds):
            ready = get_ready_tasks(tasks, completed_ids)
            # Filter out already completed tasks
            ready = [t for t in ready if t.section_id not in completed_ids]
            if not ready:
                break

            round_number += 1
            sections_in_round = [t.section_id for t in ready]

            # Dispatch tasks
            task_results = await self._dispatch_role_tasks(ready)

            # Validate payloads
            valid_payloads: list[SectionPatchPayload] = []
            for result in task_results:
                if isinstance(result, SectionPatchPayload):
                    errors = validate_patch_payload(
                        result, allowed_claim_ids, allowed_asset_ids
                    )
                    if errors:
                        logger.warning(
                            "Payload validation errors for %s: %s",
                            result.section_id,
                            errors,
                        )
                    valid_payloads.append(result)

            # Detect and resolve conflicts
            conflicts = detect_conflicts(valid_payloads, glossary, symbols, bib_keys)
            decisions = resolve_conflicts(conflicts, glossary, symbols)

            unresolved = sum(1 for d in decisions if d.requires_human_review)
            all_conflicts += len(conflicts)
            all_unresolved += unresolved

            # Apply merges and persist
            state = self._merge_and_persist(
                state, valid_payloads, decisions, glossary, symbols
            )

            # Run quality gates for each section
            gates_passed = True
            for payload in valid_payloads:
                gate_report = self._post_merge_validation(
                    payload, glossary, symbols
                )
                if not gate_report.all_passed:
                    gates_passed = False
                final_gate_summary = gate_report.summary

            # Mark sections as completed
            for payload in valid_payloads:
                completed_ids.add(payload.section_id)
                state = self._state_manager.update_section_status(
                    state, payload.section_id, "drafted"
                )

            rounds.append(
                OrchestrationRound(
                    round_number=round_number,
                    sections_processed=sections_in_round,
                    payloads_received=len(valid_payloads),
                    conflicts_detected=len(conflicts),
                    conflicts_resolved=len(conflicts) - unresolved,
                    gates_passed=gates_passed,
                )
            )

        # Save final state
        self._state_manager.save(state)

        success = len(completed_ids) == total_sections and all_unresolved == 0

        return OrchestrationReport(
            paper_id=state.paper_id,
            rounds=rounds,
            total_sections=total_sections,
            sections_completed=len(completed_ids),
            total_conflicts=all_conflicts,
            unresolved_conflicts=all_unresolved,
            final_gate_report_summary=final_gate_summary,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            success=success,
        )

    async def _dispatch_role_tasks(
        self,
        tasks: list[SectionTask],
    ) -> list[TaskResult]:
        """Dispatch tasks to executor and collect results.

        Runs tasks concurrently via asyncio.gather.
        """
        coros = [self._executor.run_task(task) for task in tasks]
        results = await asyncio.gather(*coros, return_exceptions=True)

        payloads: list[TaskResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Task %s failed: %s", tasks[i].section_id, result)
                continue
            payloads.append(result)

        return payloads

    def _merge_and_persist(
        self,
        state: PaperState,
        payloads: list[SectionPatchPayload],
        decisions: list[MergeDecision],
        glossary: Glossary | None,
        symbols: SymbolTable | None,
    ) -> PaperState:
        """Apply merge decisions and update paper state.

        For each payload:
        1. Apply merge decisions to get final tex
        2. Write tex file to disk
        3. Update section state (claim_ids, asset_ids, etc.)
        4. Update glossary/symbols with new terms
        """
        for payload in payloads:
            # Apply merge
            final_tex = apply_merge(payload, decisions)

            # Write tex file
            section = next(
                (s for s in state.sections if s.section_id == payload.section_id),
                None,
            )
            if section:
                tex_path = self._paper_dir / section.tex_file
                tex_path.parent.mkdir(parents=True, exist_ok=True)
                tex_path.write_text(final_tex, encoding="utf-8")

            # Update state
            state = self._state_manager.update_section_payload(
                state,
                payload.section_id,
                claim_ids=payload.claim_ids,
                asset_ids=payload.asset_ids,
                citation_keys=payload.citation_keys,
                word_count=payload.word_count,
            )

        return state

    def _post_merge_validation(
        self,
        payload: SectionPatchPayload,
        glossary: Glossary | None,
        symbols: SymbolTable | None,
    ) -> GateReport:
        """Run quality gates on merged content."""
        glossary_terms = {}
        if glossary:
            glossary_terms = {
                term: entry.definition
                for term, entry in glossary.entries.items()
            }

        symbol_entries = {}
        if symbols:
            symbol_entries = {
                sym: entry.meaning
                for sym, entry in symbols.entries.items()
            }

        return run_all_gates(
            tex_content=payload.tex_content,
            section_id=payload.section_id,
            section_type="method",  # simplified; real impl would look up type
            expected_claim_ids=payload.claim_ids,
            expected_asset_ids=payload.asset_ids,
            glossary_terms=glossary_terms,
            symbol_entries=symbol_entries,
        )

    def _handle_failure(
        self,
        error: Exception,
        snapshot_hash: str,
    ) -> None:
        """Handle orchestration failure with rollback."""
        logger.error("Orchestration failed: %s", error)
        if self._config.enable_git_snapshots and snapshot_hash:
            from vibewriting.agents.git_safety import rollback_to_snapshot

            try:
                rollback_to_snapshot(self._paper_dir.parent, snapshot_hash)
                logger.info("Rolled back to snapshot %s", snapshot_hash[:8])
            except Exception as rollback_err:
                logger.error("Rollback failed: %s", rollback_err)
