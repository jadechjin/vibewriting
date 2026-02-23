# env-validation Specification

## Purpose
TBD - created by archiving change project-foundation-architecture. Update Purpose after archive.
## Requirements
### Requirement: Environment validation script
The system SHALL provide `scripts/validate_env.py` that validates the development environment completeness with tiered exit codes and JSON reporting.

The script SHALL:
- Use PEP 723 inline metadata for `uv run` compatibility
- Check: Python version, core dependencies, LaTeX toolchain, optional dependencies
- Output colored `[PASS]`/`[FAIL]`/`[WARN]`/`[BLOCKED]` status for each check
- Output a machine-readable JSON report to stdout (when `--json` flag is used)
- Use tiered exit codes:
  - 0: All checks pass
  - 1: One or more required dependencies failed
  - 2: Only optional dependencies failed (all required pass)

**Required checks (exit code 1 if any fail):**
- Python version >= 3.11
- Core Python packages importable (pandas, matplotlib, scipy, pydantic)
- Git installed and functional
- uv installed and functional
- .env file exists (or .env.example exists as fallback)

**Optional checks (exit code 2 if any fail, all required pass):**
- TeX Live installed (xelatex in PATH)
- latexmk installed
- bibtex installed
- checkcites installed
- Dify credentials configured (DIFY_API_KEY non-empty)
- Optional Python packages (polars, pyarrow)

#### Scenario: Fully compliant environment
- **WHEN** all required and optional dependencies are installed
- **THEN** all checks SHALL report `[PASS]`
- **AND** the exit code SHALL be 0
- **AND** the JSON report SHALL show `{"overall": "pass", "exit_code": 0}`

#### Scenario: Required dependency missing
- **WHEN** Python version is < 3.11 or a core package cannot be imported
- **THEN** the failed check SHALL report `[FAIL]`
- **AND** the exit code SHALL be 1
- **AND** subsequent checks SHALL still execute (no early termination)

#### Scenario: Only optional dependency missing
- **WHEN** all required checks pass but TeX Live is not installed
- **THEN** the TeX-related checks SHALL report `[BLOCKED]` or `[WARN]`
- **AND** the exit code SHALL be 2
- **AND** the JSON report SHALL list blocked items with installation instructions

#### Scenario: JSON report round-trip
- **WHEN** the JSON report is serialized and re-parsed
- **THEN** the check names, statuses, and severity levels SHALL be preserved

#### Scenario: Validation idempotency
- **WHEN** the script is run twice with no environment changes
- **THEN** both runs SHALL produce the same exit code
- **AND** the JSON reports SHALL be identical (excluding timestamps and run_id)

#### Scenario: Exit code dominance
- **WHEN** a required check transitions from pass to fail
- **THEN** the exit code SHALL be 1 regardless of optional check states
- **AND** adding more optional failures SHALL NOT change the exit code from 1

