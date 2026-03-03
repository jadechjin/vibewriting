"""Run metrics aggregation for vibewriting pipeline."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _parse_phase_duration(phase_data: dict) -> float | None:
    """Calculate phase duration in seconds from started_at and completed_at timestamps."""
    started_raw = phase_data.get("started_at")
    completed_raw = phase_data.get("completed_at")
    if started_raw is None or completed_raw is None:
        return None
    try:
        started = datetime.fromisoformat(started_raw)
        completed = datetime.fromisoformat(completed_raw)
        return (completed - started).total_seconds()
    except (ValueError, TypeError):
        return None


class LiteratureMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_searched: int = 0
    after_dedup: int = 0
    evidence_cards: int = 0
    dedup_rate: float = 0.0
    tag_distribution: dict[str, int] = Field(default_factory=dict)


class WritingMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citation_coverage: float = 0.0
    claim_traceability: float = 0.0
    total_sections: int = 0
    total_words: int = 0
    total_claims: int = 0


class CompilationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_pass_success: bool = False
    heal_rounds: int = 0
    heal_success: bool = False
    peer_review_score: float = 0.0
    peer_review_verdict: str = "unknown"
    contract_violations: int = 0


class RunMetricsReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    topic: str
    created_at: datetime = Field(default_factory=_utcnow)
    phase_durations: dict[str, float | None] = Field(default_factory=dict)
    literature: LiteratureMetrics = Field(default_factory=LiteratureMetrics)
    writing: WritingMetrics = Field(default_factory=WritingMetrics)
    compilation: CompilationMetrics = Field(default_factory=CompilationMetrics)
    total_duration_sec: float | None = None


def collect_literature_metrics(cards_path: Path) -> LiteratureMetrics:
    if not cards_path.exists():
        return LiteratureMetrics()

    cards: list[dict] = []
    for line in cards_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                cards.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not cards:
        return LiteratureMetrics()

    tag_dist: dict[str, int] = {}
    for card in cards:
        for tag in card.get("tags", []):
            tag_dist[tag] = tag_dist.get(tag, 0) + 1

    total_searched = sum(
        1 for c in cards if c.get("source_query") is not None or c.get("retrieval_source") is not None
    )
    if total_searched == 0:
        total_searched = len(cards)
    after_dedup = len(cards)
    dedup_rate = (
        round(1.0 - after_dedup / total_searched, 4) if total_searched > 0 else 0.0
    )

    return LiteratureMetrics(
        total_searched=total_searched,
        after_dedup=after_dedup,
        evidence_cards=after_dedup,
        dedup_rate=dedup_rate,
        tag_distribution=tag_dist,
    )


def collect_writing_metrics(paper_state_path: Path) -> WritingMetrics:
    if not paper_state_path.exists():
        return WritingMetrics()

    try:
        data = json.loads(paper_state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return WritingMetrics()

    metrics = data.get("metrics", {})
    sections = data.get("sections", [])
    total_words = sum(s.get("word_count", 0) for s in sections)
    total_claims = sum(len(s.get("claim_ids", [])) for s in sections)

    return WritingMetrics(
        citation_coverage=float(metrics.get("citation_coverage", 0.0)),
        claim_traceability=float(metrics.get("claim_traceability", 0.0)),
        total_sections=len(sections),
        total_words=total_words,
        total_claims=total_claims,
    )


def collect_compilation_metrics(phase6_report_path: Path) -> CompilationMetrics:
    if not phase6_report_path.exists():
        return CompilationMetrics()

    try:
        data = json.loads(phase6_report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return CompilationMetrics()

    return CompilationMetrics(
        first_pass_success=bool(data.get("first_pass_success", False)),
        heal_rounds=int(data.get("heal_rounds", 0)),
        heal_success=bool(data.get("heal_success", False)),
        peer_review_score=float(data.get("peer_review_score", 0.0)),
        peer_review_verdict=str(data.get("peer_review_verdict", "unknown")),
        contract_violations=int(data.get("contract_violations", 0)),
    )


def build_run_metrics(
    run_id: str,
    topic: str,
    checkpoint: dict,
    output_dir: Path,
    data_dir: Path,
) -> RunMetricsReport:
    cards_path = data_dir / "processed" / "literature" / "literature_cards.jsonl"
    paper_state_path = output_dir / "paper_state.json"
    phase6_report_path = output_dir / "phase6_report.json"

    phases_data: dict = checkpoint.get("phases", {})
    phase_durations: dict[str, float | None] = {}
    for name, phase_data in phases_data.items():
        phase_durations[name] = _parse_phase_duration(phase_data)
    total_duration_sec: float | None = checkpoint.get("total_duration_sec", None)

    return RunMetricsReport(
        run_id=run_id,
        topic=topic,
        phase_durations=phase_durations,
        literature=collect_literature_metrics(cards_path),
        writing=collect_writing_metrics(paper_state_path),
        compilation=collect_compilation_metrics(phase6_report_path),
        total_duration_sec=total_duration_sec,
    )


def save_run_metrics(report: RunMetricsReport, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "run_metrics.json"
    out_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return out_path
