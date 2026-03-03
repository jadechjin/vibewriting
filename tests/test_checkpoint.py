"""Tests for the checkpoint system."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibewriting.checkpoint import (
    PHASE_ORDER,
    Checkpoint,
    PhaseRecord,
    PhaseStatus,
    create_checkpoint,
    detect_checkpoint,
    get_resume_phase,
    save_checkpoint,
    should_skip_phase,
    update_phase,
    validate_checkpoint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cp(run_id: str = "run-001", topic: str = "test topic") -> Checkpoint:
    return create_checkpoint(run_id, topic, config={"seed": 42})


# ---------------------------------------------------------------------------
# PHASE_ORDER
# ---------------------------------------------------------------------------

def test_phase_order_has_seven_phases() -> None:
    assert len(PHASE_ORDER) == 7


def test_phase_order_contains_expected_phases() -> None:
    expected = {
        "infrastructure",
        "data_pipeline",
        "literature",
        "single_draft",
        "multi_agent",
        "compilation",
        "integration",
    }
    assert set(PHASE_ORDER) == expected


# ---------------------------------------------------------------------------
# create_checkpoint
# ---------------------------------------------------------------------------

def test_create_checkpoint_run_id() -> None:
    cp = _make_cp(run_id="my-run")
    assert cp.run_id == "my-run"


def test_create_checkpoint_topic() -> None:
    cp = _make_cp(topic="quantum computing")
    assert cp.topic == "quantum computing"


def test_create_checkpoint_all_phases_not_started() -> None:
    cp = _make_cp()
    for phase in PHASE_ORDER:
        assert cp.phases[phase].status == PhaseStatus.not_started


def test_create_checkpoint_initialises_all_seven_phases() -> None:
    cp = _make_cp()
    assert set(cp.phases.keys()) == set(PHASE_ORDER)


def test_create_checkpoint_config_snapshot() -> None:
    cp = create_checkpoint("r1", "topic", config={"key": "value"})
    assert cp.config_snapshot == {"key": "value"}


# ---------------------------------------------------------------------------
# update_phase – immutability
# ---------------------------------------------------------------------------

def test_update_phase_returns_new_object() -> None:
    cp = _make_cp()
    cp2 = update_phase(cp, "infrastructure", PhaseStatus.in_progress)
    assert cp2 is not cp


def test_update_phase_original_unchanged() -> None:
    cp = _make_cp()
    update_phase(cp, "infrastructure", PhaseStatus.in_progress)
    assert cp.phases["infrastructure"].status == PhaseStatus.not_started


# ---------------------------------------------------------------------------
# update_phase – status transitions
# ---------------------------------------------------------------------------

def test_update_phase_in_progress_sets_started_at() -> None:
    cp = _make_cp()
    cp2 = update_phase(cp, "infrastructure", PhaseStatus.in_progress)
    assert cp2.phases["infrastructure"].started_at is not None


def test_update_phase_in_progress_does_not_override_started_at() -> None:
    cp = _make_cp()
    cp2 = update_phase(cp, "infrastructure", PhaseStatus.in_progress)
    first_started = cp2.phases["infrastructure"].started_at
    cp3 = update_phase(cp2, "infrastructure", PhaseStatus.in_progress)
    assert cp3.phases["infrastructure"].started_at == first_started


def test_update_phase_completed_sets_completed_at() -> None:
    cp = _make_cp()
    cp2 = update_phase(cp, "infrastructure", PhaseStatus.completed)
    assert cp2.phases["infrastructure"].completed_at is not None


def test_update_phase_failed_sets_completed_at() -> None:
    cp = _make_cp()
    cp2 = update_phase(cp, "infrastructure", PhaseStatus.failed, error="oops")
    assert cp2.phases["infrastructure"].completed_at is not None


def test_update_phase_failed_stores_error() -> None:
    cp = _make_cp()
    cp2 = update_phase(cp, "infrastructure", PhaseStatus.failed, error="something went wrong")
    assert cp2.phases["infrastructure"].error == "something went wrong"


def test_update_phase_unknown_phase_raises_value_error() -> None:
    cp = _make_cp()
    with pytest.raises(ValueError, match="Unknown phase"):
        update_phase(cp, "nonexistent_phase", PhaseStatus.in_progress)


def test_update_phase_updates_updated_at() -> None:
    cp = _make_cp()
    original_ts = cp.updated_at
    cp2 = update_phase(cp, "infrastructure", PhaseStatus.in_progress)
    # updated_at must be >= original (may be equal on very fast machines)
    assert cp2.updated_at >= original_ts


# ---------------------------------------------------------------------------
# get_resume_phase
# ---------------------------------------------------------------------------

def test_get_resume_phase_all_not_started_returns_first() -> None:
    cp = _make_cp()
    assert get_resume_phase(cp) == PHASE_ORDER[0]


def test_get_resume_phase_partial_completion_returns_first_incomplete() -> None:
    cp = _make_cp()
    cp = update_phase(cp, "infrastructure", PhaseStatus.completed)
    cp = update_phase(cp, "data_pipeline", PhaseStatus.completed)
    assert get_resume_phase(cp) == "literature"


def test_get_resume_phase_all_completed_returns_none() -> None:
    cp = _make_cp()
    for phase in PHASE_ORDER:
        cp = update_phase(cp, phase, PhaseStatus.completed)
    assert get_resume_phase(cp) is None


def test_get_resume_phase_failed_phase_is_not_skipped() -> None:
    cp = _make_cp()
    cp = update_phase(cp, "infrastructure", PhaseStatus.completed)
    cp = update_phase(cp, "data_pipeline", PhaseStatus.failed, error="err")
    assert get_resume_phase(cp) == "data_pipeline"


# ---------------------------------------------------------------------------
# should_skip_phase
# ---------------------------------------------------------------------------

def test_should_skip_phase_completed_returns_true() -> None:
    cp = _make_cp()
    cp = update_phase(cp, "literature", PhaseStatus.completed)
    assert should_skip_phase(cp, "literature") is True


def test_should_skip_phase_not_started_returns_false() -> None:
    cp = _make_cp()
    assert should_skip_phase(cp, "literature") is False


def test_should_skip_phase_in_progress_returns_false() -> None:
    cp = _make_cp()
    cp = update_phase(cp, "literature", PhaseStatus.in_progress)
    assert should_skip_phase(cp, "literature") is False


def test_should_skip_phase_failed_returns_false() -> None:
    cp = _make_cp()
    cp = update_phase(cp, "literature", PhaseStatus.failed, error="e")
    assert should_skip_phase(cp, "literature") is False


# ---------------------------------------------------------------------------
# save_checkpoint + detect_checkpoint (round-trip)
# ---------------------------------------------------------------------------

def test_save_and_detect_checkpoint_roundtrip(tmp_path: Path) -> None:
    cp = _make_cp(run_id="rt-001", topic="round-trip")
    save_checkpoint(cp, tmp_path)
    loaded = detect_checkpoint(tmp_path)
    assert loaded is not None
    assert loaded.run_id == "rt-001"
    assert loaded.topic == "round-trip"


def test_detect_checkpoint_nonexistent_returns_none(tmp_path: Path) -> None:
    result = detect_checkpoint(tmp_path / "does_not_exist")
    assert result is None


def test_detect_checkpoint_no_file_in_dir_returns_none(tmp_path: Path) -> None:
    result = detect_checkpoint(tmp_path)
    assert result is None


def test_save_checkpoint_creates_json_file(tmp_path: Path) -> None:
    cp = _make_cp()
    save_checkpoint(cp, tmp_path)
    assert (tmp_path / "checkpoint.json").exists()


def test_save_checkpoint_no_tmp_file_left(tmp_path: Path) -> None:
    cp = _make_cp()
    save_checkpoint(cp, tmp_path)
    assert not (tmp_path / "checkpoint.json.tmp").exists()


def test_save_checkpoint_creates_output_dir(tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "nested"
    cp = _make_cp()
    save_checkpoint(cp, nested)
    assert (nested / "checkpoint.json").exists()


def test_detect_checkpoint_preserves_phase_statuses(tmp_path: Path) -> None:
    cp = _make_cp()
    cp = update_phase(cp, "infrastructure", PhaseStatus.completed)
    cp = update_phase(cp, "data_pipeline", PhaseStatus.in_progress)
    save_checkpoint(cp, tmp_path)
    loaded = detect_checkpoint(tmp_path)
    assert loaded is not None
    assert loaded.phases["infrastructure"].status == PhaseStatus.completed
    assert loaded.phases["data_pipeline"].status == PhaseStatus.in_progress


# ---------------------------------------------------------------------------
# validate_checkpoint
# ---------------------------------------------------------------------------

def test_validate_checkpoint_valid_returns_empty(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    data_dir = tmp_path / "data"
    output_dir.mkdir()
    data_dir.mkdir()
    cp = _make_cp()
    errors = validate_checkpoint(cp, output_dir, data_dir)
    assert errors == []


def test_validate_checkpoint_missing_phase_returns_issue(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    data_dir = tmp_path / "data"
    output_dir.mkdir()
    data_dir.mkdir()
    # Build a checkpoint missing one phase by direct construction
    cp = _make_cp()
    incomplete_phases = {k: v for k, v in cp.phases.items() if k != "literature"}
    cp_bad = cp.model_copy(update={"phases": incomplete_phases})
    errors = validate_checkpoint(cp_bad, output_dir, data_dir)
    assert any("literature" in e for e in errors)


def test_validate_checkpoint_output_dir_missing_returns_issue(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    cp = _make_cp()
    errors = validate_checkpoint(cp, tmp_path / "nonexistent", data_dir)
    assert any("output_dir" in e for e in errors)


def test_validate_checkpoint_data_dir_missing_returns_issue(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    cp = _make_cp()
    errors = validate_checkpoint(cp, output_dir, tmp_path / "nonexistent")
    assert any("data_dir" in e for e in errors)


def test_validate_checkpoint_empty_run_id_returns_issue(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    data_dir = tmp_path / "data"
    output_dir.mkdir()
    data_dir.mkdir()
    cp = create_checkpoint("", "topic", config={})
    errors = validate_checkpoint(cp, output_dir, data_dir)
    assert any("run_id" in e for e in errors)


def test_validate_checkpoint_empty_topic_returns_issue(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    data_dir = tmp_path / "data"
    output_dir.mkdir()
    data_dir.mkdir()
    cp = create_checkpoint("r1", "", config={})
    errors = validate_checkpoint(cp, output_dir, data_dir)
    assert any("topic" in e for e in errors)


# ---------------------------------------------------------------------------
# JSON serialization / deserialization
# ---------------------------------------------------------------------------

def test_checkpoint_json_serialisation_roundtrip() -> None:
    cp = _make_cp()
    cp = update_phase(cp, "infrastructure", PhaseStatus.completed)
    json_str = cp.model_dump_json()
    cp2 = Checkpoint.model_validate_json(json_str)
    assert cp2.run_id == cp.run_id
    assert cp2.topic == cp.topic
    assert cp2.phases["infrastructure"].status == PhaseStatus.completed


def test_checkpoint_json_is_valid_json() -> None:
    cp = _make_cp()
    json_str = cp.model_dump_json(indent=2)
    parsed = json.loads(json_str)
    assert parsed["run_id"] == cp.run_id
    assert "phases" in parsed
