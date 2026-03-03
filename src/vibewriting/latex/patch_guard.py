"""LaTeX patch proposal validation and atomic application."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True, slots=True)
class PatchProposal:
    target_file: str
    start_line: int
    end_line: int
    original_content: str
    patched_content: str
    error_kind: str


def validate_patch_target(proposal: PatchProposal, paper_dir: Path) -> bool:
    parts = PurePosixPath(proposal.target_file).parts
    if len(parts) != 2 or parts[0] != "sections":
        return False
    if not parts[1].endswith(".tex"):
        return False
    target = paper_dir / proposal.target_file
    return target.resolve().is_relative_to(paper_dir.resolve()) and target.exists()


def validate_patch_scope(proposal: PatchProposal, max_window: int = 10) -> bool:
    if proposal.start_line < 1 or proposal.end_line < proposal.start_line:
        return False
    return (proposal.end_line - proposal.start_line + 1) <= max_window


def enforce_single_file(proposals: list[PatchProposal]) -> bool:
    targets = {p.target_file for p in proposals}
    return len(targets) == 1


def apply_patch(proposal: PatchProposal, paper_dir: Path) -> bool:
    if not validate_patch_target(proposal, paper_dir):
        return False

    target = paper_dir / proposal.target_file
    lines = target.read_text(encoding="utf-8").splitlines(keepends=True)

    start_idx = proposal.start_line - 1
    end_idx = proposal.end_line
    if end_idx > len(lines):
        return False

    actual = "".join(lines[start_idx:end_idx])
    if actual != proposal.original_content:
        return False

    patched_lines = lines[:start_idx] + [proposal.patched_content] + lines[end_idx:]
    new_content = "".join(patched_lines)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(target.parent), suffix=".tex.tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp_path, str(target))
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return False
    return True
