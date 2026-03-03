"""LaTeX compiler with self-healing loop."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from vibewriting.agents.git_safety import (
    drop_stash,
    rollback_stash,
    stash_before_patch,
)
from vibewriting.config import settings
from vibewriting.latex.log_parser import (
    ErrorKind,
    LatexError,
    classify_error,
    extract_error_context,
    parse_log,
)
from vibewriting.latex.patch_guard import (
    PatchProposal,
    apply_patch,
    validate_patch_scope,
    validate_patch_target,
)
from vibewriting.review.models import PatchReport

logger = logging.getLogger(__name__)


def compile_full(
    paper_dir: Path, timeout: int | None = None,
) -> tuple[bool, str]:
    timeout = timeout or settings.compile_timeout_sec
    main_tex = paper_dir / "main.tex"
    if not main_tex.exists():
        return False, f"main.tex not found in {paper_dir}"

    cmd = [
        "latexmk", "-xelatex", "-interaction=nonstopmode",
        "-output-directory=build",
        str(main_tex),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(paper_dir), timeout=timeout, check=False,
        )
    except FileNotFoundError:
        return False, "latexmk not found. Install TeX Live."
    except subprocess.TimeoutExpired:
        return False, f"Compilation timed out after {timeout}s"

    log_path = paper_dir / "build" / "main.log"
    log_content = ""
    if log_path.exists():
        log_content = log_path.read_text(encoding="utf-8", errors="replace")

    success = result.returncode == 0
    return success, log_content


def route_error(error: LatexError) -> str:
    kind = classify_error(error)
    if kind == ErrorKind.MISSING_PACKAGE:
        return f"MANUAL: Install missing package. {error.message}"
    if kind == ErrorKind.UNDEFINED_REFERENCE:
        return "AUTO: Check references.bib and literature_cards"
    if kind == ErrorKind.SYNTAX_ERROR:
        return "AUTO: Generate syntax fix patch"
    if kind == ErrorKind.MISSING_FILE:
        return "MANUAL: Check asset_manifest.json for missing file"
    if kind == ErrorKind.ENCODING_ERROR:
        return "MANUAL: Check file encoding"
    return f"SKIP: Unknown error type, requires human review. {error.message}"


def _is_auto_fixable(error: LatexError) -> bool:
    kind = classify_error(error)
    return kind in (ErrorKind.SYNTAX_ERROR, ErrorKind.UNDEFINED_REFERENCE)


def run_self_heal_loop(
    paper_dir: Path,
    max_retries: int | None = None,
    repo_root: Path | None = None,
) -> list[PatchReport]:
    max_retries = max_retries or settings.compile_max_retries
    repo_root = repo_root or settings.project_root
    reports: list[PatchReport] = []

    for round_num in range(1, max_retries + 1):
        logger.info("Compile round %d/%d", round_num, max_retries)
        success, log_content = compile_full(paper_dir)

        if success:
            logger.info("Compilation succeeded on round %d", round_num)
            reports.append(PatchReport(
                round_number=round_num,
                error_kind="none",
                target_file="",
                lines_changed=0,
                success=True,
            ))
            break

        errors = parse_log(log_content)
        if not errors:
            logger.warning("Compilation failed but no errors parsed from log")
            reports.append(PatchReport(
                round_number=round_num,
                error_kind="unparseable",
                target_file="",
                lines_changed=0,
                success=False,
            ))
            break

        fixable = [e for e in errors if _is_auto_fixable(e)]
        if not fixable:
            logger.warning("No auto-fixable errors found. Routes: %s",
                           [route_error(e) for e in errors])
            for e in errors:
                reports.append(PatchReport(
                    round_number=round_num,
                    error_kind=classify_error(e).value,
                    target_file=e.file_path or "",
                    lines_changed=0,
                    success=False,
                ))
            break

        error = fixable[0]
        kind = classify_error(error)
        stash_ref = stash_before_patch(repo_root, f"round-{round_num}")

        context = extract_error_context(log_content, error)
        logger.info("Round %d: %s in %s (line %s)\nContext:\n%s",
                     round_num, kind.value, error.file_path,
                     error.line_number, context[:200])

        reports.append(PatchReport(
            round_number=round_num,
            error_kind=kind.value,
            target_file=error.file_path or "",
            lines_changed=0,
            success=False,
            stash_ref=stash_ref,
        ))

        if stash_ref:
            try:
                drop_stash(repo_root)
            except Exception:
                pass

    return reports


def write_patch_reports(
    reports: list[PatchReport], output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "patch_report.json"
    data = [r.model_dump() for r in reports]
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path
