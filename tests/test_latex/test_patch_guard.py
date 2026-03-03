"""Tests for LaTeX patch guard."""

from __future__ import annotations

from pathlib import Path

from vibewriting.latex.patch_guard import (
    PatchProposal,
    apply_patch,
    enforce_single_file,
    validate_patch_scope,
    validate_patch_target,
)


def _make_proposal(**kwargs) -> PatchProposal:
    defaults = {
        "target_file": "sections/intro.tex",
        "start_line": 2,
        "end_line": 3,
        "original_content": "Line 1\nLine 2\n",
        "patched_content": "Fixed 1\nFixed 2\n",
        "error_kind": "syntax_error",
    }
    defaults.update(kwargs)
    return PatchProposal(**defaults)


class TestValidatePatchTarget:
    def test_valid_sections_file(self, tmp_paper_dir: Path):
        p = _make_proposal(target_file="sections/intro.tex")
        assert validate_patch_target(p, tmp_paper_dir) is True

    def test_reject_main_tex(self, tmp_paper_dir: Path):
        p = _make_proposal(target_file="main.tex")
        assert validate_patch_target(p, tmp_paper_dir) is False

    def test_reject_non_sections(self, tmp_paper_dir: Path):
        p = _make_proposal(target_file="preamble.tex")
        assert validate_patch_target(p, tmp_paper_dir) is False

    def test_reject_nonexistent_file(self, tmp_paper_dir: Path):
        p = _make_proposal(target_file="sections/nonexistent.tex")
        assert validate_patch_target(p, tmp_paper_dir) is False

    def test_reject_non_tex(self, tmp_paper_dir: Path):
        p = _make_proposal(target_file="sections/data.csv")
        assert validate_patch_target(p, tmp_paper_dir) is False


class TestValidatePatchScope:
    def test_within_window(self):
        p = _make_proposal(start_line=5, end_line=10)
        assert validate_patch_scope(p, max_window=10) is True

    def test_exceeds_window(self):
        p = _make_proposal(start_line=1, end_line=20)
        assert validate_patch_scope(p, max_window=10) is False

    def test_invalid_start_line(self):
        p = _make_proposal(start_line=0, end_line=5)
        assert validate_patch_scope(p) is False

    def test_end_before_start(self):
        p = _make_proposal(start_line=10, end_line=5)
        assert validate_patch_scope(p) is False


class TestEnforceSingleFile:
    def test_single_file(self):
        proposals = [
            _make_proposal(target_file="sections/intro.tex"),
            _make_proposal(target_file="sections/intro.tex"),
        ]
        assert enforce_single_file(proposals) is True

    def test_multiple_files(self):
        proposals = [
            _make_proposal(target_file="sections/intro.tex"),
            _make_proposal(target_file="sections/method.tex"),
        ]
        assert enforce_single_file(proposals) is False


class TestApplyPatch:
    def test_apply_valid_patch(self, tmp_paper_dir: Path):
        intro = tmp_paper_dir / "sections" / "intro.tex"
        content = intro.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
        original = "".join(lines[1:3])
        p = PatchProposal(
            target_file="sections/intro.tex",
            start_line=2,
            end_line=3,
            original_content=original,
            patched_content="Fixed line\n",
            error_kind="syntax_error",
        )
        result = apply_patch(p, tmp_paper_dir)
        assert result is True
        new_content = intro.read_text(encoding="utf-8")
        assert "Fixed line" in new_content

    def test_reject_main_tex_patch(self, tmp_paper_dir: Path):
        p = _make_proposal(target_file="main.tex")
        assert apply_patch(p, tmp_paper_dir) is False
