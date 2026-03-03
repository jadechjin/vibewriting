"""Checkpoint system for phase state tracking and recovery."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PhaseStatus(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class PhaseRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: PhaseStatus = PhaseStatus.not_started
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


PHASE_ORDER: list[str] = [
    "infrastructure",
    "data_pipeline",
    "literature",
    "single_draft",
    "multi_agent",
    "compilation",
    "integration",
]


class Checkpoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    topic: str
    phases: dict[str, PhaseRecord] = Field(default_factory=dict)
    config_snapshot: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


def create_checkpoint(run_id: str, topic: str, config: dict) -> Checkpoint:
    now = _utcnow()
    phases = {phase: PhaseRecord() for phase in PHASE_ORDER}
    return Checkpoint(
        run_id=run_id,
        topic=topic,
        phases=phases,
        config_snapshot=config,
        created_at=now,
        updated_at=now,
    )


def update_phase(
    cp: Checkpoint,
    phase: str,
    status: PhaseStatus,
    error: str | None = None,
) -> Checkpoint:
    if phase not in PHASE_ORDER:
        raise ValueError(f"Unknown phase: {phase!r}. Must be one of {PHASE_ORDER}")
    now = _utcnow()
    old = cp.phases.get(phase, PhaseRecord())
    started_at = old.started_at
    completed_at = old.completed_at

    if status == PhaseStatus.in_progress and started_at is None:
        started_at = now
    if status in (PhaseStatus.completed, PhaseStatus.failed):
        completed_at = now

    new_record = PhaseRecord(
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        error=error,
    )
    new_phases = {**cp.phases, phase: new_record}
    return cp.model_copy(update={"phases": new_phases, "updated_at": now})


def get_resume_phase(cp: Checkpoint) -> str | None:
    for phase in PHASE_ORDER:
        record = cp.phases.get(phase, PhaseRecord())
        if record.status != PhaseStatus.completed:
            return phase
    return None


def should_skip_phase(cp: Checkpoint, phase: str) -> bool:
    record = cp.phases.get(phase, PhaseRecord())
    return record.status == PhaseStatus.completed


def save_checkpoint(cp: Checkpoint, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "checkpoint.json"
    tmp = output_dir / "checkpoint.json.tmp"
    tmp.write_text(cp.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(target)


def detect_checkpoint(output_dir: Path) -> Checkpoint | None:
    path = output_dir / "checkpoint.json"
    if not path.exists():
        return None
    try:
        return Checkpoint.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def validate_checkpoint(
    cp: Checkpoint,
    output_dir: Path,
    data_dir: Path,
) -> list[str]:
    errors: list[str] = []

    if not cp.run_id:
        errors.append("run_id is empty")
    if not cp.topic:
        errors.append("topic is empty")

    for phase in PHASE_ORDER:
        if phase not in cp.phases:
            errors.append(f"missing phase record: {phase}")

    if not output_dir.exists():
        errors.append(f"output_dir does not exist: {output_dir}")
    if not data_dir.exists():
        errors.append(f"data_dir does not exist: {data_dir}")

    return errors
