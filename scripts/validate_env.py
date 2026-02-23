# /// script
# requires-python = ">=3.11"
# ///
"""Environment validation script for vibewriting project.

Usage:
    uv run scripts/validate_env.py          # Colored console output
    uv run scripts/validate_env.py --json   # Machine-readable JSON report

Exit codes:
    0 — All checks pass
    1 — Required dependency failed
    2 — Only optional dependencies failed
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ANSI color codes
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"
BOLD = "\033[1m"


@dataclass
class CheckResult:
    name: str
    status: str  # pass, fail, warn, blocked
    severity: str  # required, optional
    message: str = ""
    install_hint: str = ""


def check_python_version() -> CheckResult:
    major, minor = sys.version_info[:2]
    version_str = f"{major}.{minor}.{sys.version_info[2]}"
    if (major, minor) >= (3, 11):
        return CheckResult("python_version", "pass", "required", f"Python {version_str}")
    return CheckResult(
        "python_version", "fail", "required",
        f"Python {version_str} (requires >=3.11)",
        "Install Python 3.11+: https://www.python.org/downloads/",
    )


def check_package(name: str, severity: str = "required") -> CheckResult:
    """Check if a package is importable in the project venv via subprocess."""
    uv_path = shutil.which("uv")
    if uv_path:
        try:
            result = subprocess.run(
                [uv_path, "run", "python", "-c", f"import {name}"],
                capture_output=True, cwd=str(PROJECT_ROOT), timeout=30,
            )
            ok = result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            ok = False
    else:
        try:
            importlib.import_module(name)
            ok = True
        except ImportError:
            ok = False

    if ok:
        return CheckResult(f"package_{name}", "pass", severity, f"{name} importable")
    hint = "Run: uv sync" if severity == "required" else "Run: uv sync --extra perf"
    return CheckResult(
        f"package_{name}", "fail", severity,
        f"{name} not importable", hint,
    )


def check_command(name: str, severity: str, display: str = "") -> CheckResult:
    display = display or name
    path = shutil.which(name)
    if path:
        return CheckResult(f"command_{name}", "pass", severity, f"{display} found at {path}")
    status = "blocked" if severity == "optional" else "fail"
    hints = {
        "git": "Install Git: https://git-scm.com/downloads",
        "uv": "Install uv: https://docs.astral.sh/uv/getting-started/installation/",
        "xelatex": "Install TeX Live: https://tug.org/texlive/",
        "latexmk": "Install TeX Live (includes latexmk): https://tug.org/texlive/",
        "bibtex": "Install TeX Live (includes bibtex): https://tug.org/texlive/",
        "checkcites": "Install TeX Live (includes checkcites): https://tug.org/texlive/",
    }
    return CheckResult(
        f"command_{name}", status, severity,
        f"{display} not found in PATH", hints.get(name, ""),
    )


def check_env_file() -> CheckResult:
    env_path = PROJECT_ROOT / ".env"
    example_path = PROJECT_ROOT / ".env.example"
    if env_path.exists():
        return CheckResult("env_file", "pass", "required", ".env file exists")
    if example_path.exists():
        return CheckResult(
            "env_file", "warn", "required",
            ".env not found, .env.example exists (copy and configure it)",
            "Run: cp .env.example .env",
        )
    return CheckResult(
        "env_file", "fail", "required",
        "Neither .env nor .env.example found",
        "Create .env from .env.example template",
    )


def check_dify_credentials() -> CheckResult:
    key = os.environ.get("DIFY_API_KEY", "")
    if not key:
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("DIFY_API_KEY=") and line.split("=", 1)[1].strip():
                    key = "configured"
                    break
    if key:
        return CheckResult("dify_credentials", "pass", "optional", "DIFY_API_KEY configured")
    return CheckResult(
        "dify_credentials", "blocked", "optional",
        "DIFY_API_KEY not set (Dify knowledge base unavailable)",
        "Set DIFY_API_KEY in .env file",
    )


def run_all_checks() -> list[CheckResult]:
    results: list[CheckResult] = []

    # Required checks
    results.append(check_python_version())
    for pkg in ("pandas", "matplotlib", "scipy", "pydantic"):
        results.append(check_package(pkg, "required"))
    results.append(check_command("git", "required"))
    results.append(check_command("uv", "required"))
    results.append(check_env_file())

    # Optional checks
    results.append(check_command("xelatex", "optional", "XeLaTeX (TeX Live)"))
    results.append(check_command("latexmk", "optional"))
    results.append(check_command("bibtex", "optional"))
    results.append(check_command("checkcites", "optional"))
    results.append(check_dify_credentials())
    for pkg in ("polars", "pyarrow"):
        results.append(check_package(pkg, "optional"))

    return results


def compute_exit_code(results: list[CheckResult]) -> int:
    has_required_fail = any(
        r.severity == "required" and r.status == "fail" for r in results
    )
    has_optional_fail = any(
        r.severity == "optional" and r.status in ("fail", "blocked") for r in results
    )
    if has_required_fail:
        return 1
    if has_optional_fail:
        return 2
    return 0


STATUS_LABELS = {
    "pass": f"{GREEN}[PASS]{RESET}",
    "fail": f"{RED}[FAIL]{RESET}",
    "warn": f"{YELLOW}[WARN]{RESET}",
    "blocked": f"{YELLOW}[BLOCKED]{RESET}",
}


def print_console(results: list[CheckResult], exit_code: int) -> None:
    print(f"\n{BOLD}vibewriting Environment Validation{RESET}\n")

    prev_severity = None
    for r in results:
        if r.severity != prev_severity:
            header = "Required" if r.severity == "required" else "Optional"
            print(f"\n  {BOLD}--- {header} ---{RESET}")
            prev_severity = r.severity

        label = STATUS_LABELS.get(r.status, r.status)
        print(f"  {label} {r.name}: {r.message}")
        if r.install_hint and r.status in ("fail", "blocked", "warn"):
            print(f"         Hint: {r.install_hint}")

    print()
    if exit_code == 0:
        print(f"  {GREEN}All checks passed.{RESET}")
    elif exit_code == 1:
        print(f"  {RED}Required dependencies missing. Fix before proceeding.{RESET}")
    else:
        print(f"  {YELLOW}Optional dependencies missing. Core functionality available.{RESET}")
    print()


def print_json(results: list[CheckResult], exit_code: int) -> None:
    overall = {0: "pass", 1: "fail", 2: "warn"}[exit_code]
    report = {
        "overall": overall,
        "exit_code": exit_code,
        "checks": [asdict(r) for r in results],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate vibewriting environment")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    results = run_all_checks()
    exit_code = compute_exit_code(results)

    if args.json:
        print_json(results, exit_code)
    else:
        print_console(results, exit_code)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
