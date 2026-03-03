"""Tests for vibewriting metrics aggregation module."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from vibewriting.metrics import (
    CompilationMetrics,
    LiteratureMetrics,
    RunMetricsReport,
    WritingMetrics,
    build_run_metrics,
    collect_compilation_metrics,
    collect_literature_metrics,
    collect_writing_metrics,
    save_run_metrics,
)


# ---------------------------------------------------------------------------
# Default / zero-value tests
# ---------------------------------------------------------------------------


def test_literature_metrics_default_zeros():
    m = LiteratureMetrics()
    assert m.total_searched == 0
    assert m.after_dedup == 0
    assert m.evidence_cards == 0
    assert m.dedup_rate == 0.0
    assert m.tag_distribution == {}


def test_writing_metrics_default_zeros():
    m = WritingMetrics()
    assert m.citation_coverage == 0.0
    assert m.claim_traceability == 0.0
    assert m.total_sections == 0
    assert m.total_words == 0
    assert m.total_claims == 0


def test_compilation_metrics_default_zeros():
    m = CompilationMetrics()
    assert m.first_pass_success is False
    assert m.heal_rounds == 0
    assert m.heal_success is False
    assert m.peer_review_score == 0.0
    assert m.peer_review_verdict == "unknown"
    assert m.contract_violations == 0


# ---------------------------------------------------------------------------
# collect_literature_metrics
# ---------------------------------------------------------------------------


def test_collect_literature_metrics_file_not_exists(tmp_path: Path):
    result = collect_literature_metrics(tmp_path / "nonexistent.jsonl")
    assert isinstance(result, LiteratureMetrics)
    assert result.total_searched == 0
    assert result.evidence_cards == 0


def test_collect_literature_metrics_empty_file(tmp_path: Path):
    cards_path = tmp_path / "literature_cards.jsonl"
    cards_path.write_text("", encoding="utf-8")
    result = collect_literature_metrics(cards_path)
    assert result.total_searched == 0
    assert result.evidence_cards == 0


def test_collect_literature_metrics_normal_aggregation(tmp_path: Path):
    cards_path = tmp_path / "literature_cards.jsonl"
    cards = [
        {
            "claim_id": "EC-2024-001",
            "retrieval_source": "paper-search",
            "tags": ["nlp", "bert"],
        },
        {
            "claim_id": "EC-2024-002",
            "retrieval_source": "dify-kb",
            "tags": ["nlp", "gpt"],
        },
        {
            "claim_id": "EC-2024-003",
            "retrieval_source": "manual",
            "tags": ["bert"],
        },
    ]
    lines = "\n".join(json.dumps(c) for c in cards)
    cards_path.write_text(lines, encoding="utf-8")

    result = collect_literature_metrics(cards_path)

    assert result.evidence_cards == 3
    assert result.after_dedup == 3
    assert result.total_searched == 3


def test_collect_literature_metrics_tag_distribution(tmp_path: Path):
    cards_path = tmp_path / "literature_cards.jsonl"
    cards = [
        {"retrieval_source": "paper-search", "tags": ["nlp", "bert"]},
        {"retrieval_source": "dify-kb", "tags": ["nlp", "gpt"]},
        {"retrieval_source": "manual", "tags": ["bert", "transformer"]},
    ]
    lines = "\n".join(json.dumps(c) for c in cards)
    cards_path.write_text(lines, encoding="utf-8")

    result = collect_literature_metrics(cards_path)

    assert result.tag_distribution["nlp"] == 2
    assert result.tag_distribution["bert"] == 2
    assert result.tag_distribution["gpt"] == 1
    assert result.tag_distribution["transformer"] == 1


def test_collect_literature_metrics_fallback_when_no_source_fields(tmp_path: Path):
    """Cards without retrieval_source or source_query should still count via fallback."""
    cards_path = tmp_path / "literature_cards.jsonl"
    cards = [
        {"claim_id": "EC-2024-001", "tags": []},
        {"claim_id": "EC-2024-002", "tags": []},
    ]
    lines = "\n".join(json.dumps(c) for c in cards)
    cards_path.write_text(lines, encoding="utf-8")

    result = collect_literature_metrics(cards_path)

    assert result.total_searched == 2
    assert result.evidence_cards == 2


def test_collect_literature_metrics_skips_invalid_json_lines(tmp_path: Path):
    cards_path = tmp_path / "literature_cards.jsonl"
    content = (
        '{"retrieval_source": "paper-search", "tags": ["nlp"]}\n'
        "this is not json\n"
        '{"retrieval_source": "dify-kb", "tags": ["bert"]}\n'
    )
    cards_path.write_text(content, encoding="utf-8")

    result = collect_literature_metrics(cards_path)

    assert result.evidence_cards == 2


# ---------------------------------------------------------------------------
# collect_writing_metrics
# ---------------------------------------------------------------------------


def test_collect_writing_metrics_file_not_exists(tmp_path: Path):
    result = collect_writing_metrics(tmp_path / "paper_state.json")
    assert isinstance(result, WritingMetrics)
    assert result.total_sections == 0
    assert result.total_words == 0


def test_collect_writing_metrics_normal_aggregation(tmp_path: Path):
    paper_state_path = tmp_path / "paper_state.json"
    data = {
        "metrics": {
            "citation_coverage": 0.85,
            "claim_traceability": 0.9,
        },
        "sections": [
            {"word_count": 500, "claim_ids": ["EC-2024-001", "EC-2024-002"]},
            {"word_count": 300, "claim_ids": ["EC-2024-003"]},
        ],
    }
    paper_state_path.write_text(json.dumps(data), encoding="utf-8")

    result = collect_writing_metrics(paper_state_path)

    assert result.citation_coverage == pytest.approx(0.85)
    assert result.claim_traceability == pytest.approx(0.9)
    assert result.total_sections == 2
    assert result.total_words == 800
    assert result.total_claims == 3


# ---------------------------------------------------------------------------
# collect_compilation_metrics
# ---------------------------------------------------------------------------


def test_collect_compilation_metrics_file_not_exists(tmp_path: Path):
    result = collect_compilation_metrics(tmp_path / "phase6_report.json")
    assert isinstance(result, CompilationMetrics)
    assert result.first_pass_success is False
    assert result.peer_review_verdict == "unknown"


def test_collect_compilation_metrics_normal_aggregation(tmp_path: Path):
    report_path = tmp_path / "phase6_report.json"
    data = {
        "first_pass_success": True,
        "heal_rounds": 2,
        "heal_success": True,
        "peer_review_score": 8.5,
        "peer_review_verdict": "accept",
        "contract_violations": 1,
    }
    report_path.write_text(json.dumps(data), encoding="utf-8")

    result = collect_compilation_metrics(report_path)

    assert result.first_pass_success is True
    assert result.heal_rounds == 2
    assert result.heal_success is True
    assert result.peer_review_score == pytest.approx(8.5)
    assert result.peer_review_verdict == "accept"
    assert result.contract_violations == 1


def test_collect_compilation_metrics_missing_verdict_defaults_to_unknown(tmp_path: Path):
    report_path = tmp_path / "phase6_report.json"
    data = {"first_pass_success": True}
    report_path.write_text(json.dumps(data), encoding="utf-8")

    result = collect_compilation_metrics(report_path)

    assert result.peer_review_verdict == "unknown"


# ---------------------------------------------------------------------------
# build_run_metrics
# ---------------------------------------------------------------------------


def _make_checkpoint(with_phases: bool = True, total_dur: float | None = 120.0) -> dict:
    checkpoint: dict = {"total_duration_sec": total_dur}
    if with_phases:
        t0 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        t1 = t0 + timedelta(seconds=30)
        t2 = t1 + timedelta(seconds=45)
        t3 = t2 + timedelta(seconds=25)
        checkpoint["phases"] = {
            "literature": {
                "started_at": t0.isoformat(),
                "completed_at": t1.isoformat(),
            },
            "writing": {
                "started_at": t1.isoformat(),
                "completed_at": t2.isoformat(),
            },
            "compilation": {
                "started_at": t2.isoformat(),
                "completed_at": t3.isoformat(),
            },
        }
    return checkpoint


def test_build_run_metrics_normal(tmp_path: Path):
    checkpoint = _make_checkpoint()
    result = build_run_metrics(
        run_id="run-001",
        topic="test topic",
        checkpoint=checkpoint,
        output_dir=tmp_path,
        data_dir=tmp_path,
    )

    assert isinstance(result, RunMetricsReport)
    assert result.run_id == "run-001"
    assert result.topic == "test topic"
    assert result.total_duration_sec == pytest.approx(120.0)


def test_build_run_metrics_missing_files_graceful(tmp_path: Path):
    """build_run_metrics should not raise when artifact files are absent."""
    checkpoint = _make_checkpoint(with_phases=False, total_dur=None)
    result = build_run_metrics(
        run_id="run-002",
        topic="graceful degradation",
        checkpoint=checkpoint,
        output_dir=tmp_path / "nonexistent_output",
        data_dir=tmp_path / "nonexistent_data",
    )

    assert result.literature.total_searched == 0
    assert result.writing.total_sections == 0
    assert result.compilation.peer_review_verdict == "unknown"
    assert result.total_duration_sec is None


def test_build_run_metrics_phase_duration_calculation(tmp_path: Path):
    checkpoint = _make_checkpoint()
    result = build_run_metrics(
        run_id="run-003",
        topic="phase timing",
        checkpoint=checkpoint,
        output_dir=tmp_path,
        data_dir=tmp_path,
    )

    assert result.phase_durations["literature"] == pytest.approx(30.0)
    assert result.phase_durations["writing"] == pytest.approx(45.0)
    assert result.phase_durations["compilation"] == pytest.approx(25.0)


def test_build_run_metrics_phase_duration_missing_completed_at(tmp_path: Path):
    """Phase duration should be None when completed_at is absent."""
    checkpoint = {
        "phases": {
            "literature": {
                "started_at": "2025-01-01T10:00:00+00:00",
                # no completed_at
            }
        },
        "total_duration_sec": 10.0,
    }
    result = build_run_metrics(
        run_id="run-004",
        topic="partial phase",
        checkpoint=checkpoint,
        output_dir=tmp_path,
        data_dir=tmp_path,
    )
    assert result.phase_durations["literature"] is None


# ---------------------------------------------------------------------------
# save_run_metrics
# ---------------------------------------------------------------------------


def test_save_run_metrics_creates_file(tmp_path: Path):
    report = RunMetricsReport(run_id="run-010", topic="save test")
    out_path = save_run_metrics(report, tmp_path / "output")

    assert out_path.exists()
    assert out_path.name == "run_metrics.json"


def test_save_run_metrics_roundtrip_json(tmp_path: Path):
    report = RunMetricsReport(
        run_id="run-011",
        topic="roundtrip",
        total_duration_sec=99.5,
        phase_durations={"p1": 10.0, "p2": None},
    )
    out_path = save_run_metrics(report, tmp_path / "output")

    raw = json.loads(out_path.read_text(encoding="utf-8"))
    assert raw["run_id"] == "run-011"
    assert raw["topic"] == "roundtrip"
    assert raw["total_duration_sec"] == pytest.approx(99.5)
    assert raw["phase_durations"]["p1"] == pytest.approx(10.0)
    assert raw["phase_durations"]["p2"] is None
    assert raw["compilation"]["peer_review_verdict"] == "unknown"


# ---------------------------------------------------------------------------
# RunMetricsReport serialization
# ---------------------------------------------------------------------------


def test_run_metrics_report_serialization():
    report = RunMetricsReport(run_id="run-020", topic="serialization")
    dumped = json.loads(report.model_dump_json())

    assert dumped["run_id"] == "run-020"
    assert "created_at" in dumped
    assert dumped["literature"]["total_searched"] == 0
    assert dumped["writing"]["total_sections"] == 0
    assert dumped["compilation"]["peer_review_verdict"] == "unknown"


def test_run_metrics_report_default_zeros():
    report = RunMetricsReport(run_id="run-021", topic="defaults")

    assert report.total_duration_sec is None
    assert report.phase_durations == {}
    assert report.literature.evidence_cards == 0
    assert report.writing.total_words == 0
    assert report.compilation.contract_violations == 0
