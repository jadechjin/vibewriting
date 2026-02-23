## ADDED Requirements

### Requirement: Python data processing environment
The system SHALL configure a Python development environment using uv + hatchling with src layout.

The `pyproject.toml` SHALL specify:
- `[build-system]` using hatchling
- `[project]` with name="vibewriting", requires-python=">=3.11"
- Source layout: packages in `src/`

**Core dependencies:**
```
pandas>=2.2,<3.0
numpy>=1.26,<2.0
matplotlib>=3.10
seaborn>=0.13
scipy>=1.14
statsmodels>=0.14
pydantic>=2.0
httpx
python-dotenv
tabulate>=0.9
jinja2>=3.1
```

**Optional dependency groups:**
- `perf`: polars>=1.30, pyarrow>=15.0
- `latex`: pylatex>=1.4

**Dev dependency group:**
- pytest>=8.0, pytest-asyncio>=0.23, ruff>=0.14, mypy>=1.10

The `uv.lock` file SHALL be committed to Git for reproducibility.

#### Scenario: Dependency resolution
- **WHEN** `uv sync` is executed in the project root
- **THEN** all core dependencies SHALL install successfully
- **AND** the exit code SHALL be 0
- **AND** no version conflicts SHALL be reported

#### Scenario: Lock file reproducibility
- **WHEN** `uv sync` is run twice with no pyproject.toml changes
- **THEN** `uv.lock` SHALL NOT change between runs
- **AND** the installed package set SHALL be identical

#### Scenario: Import validation
- **WHEN** `uv run python -c "import pandas, matplotlib, seaborn, scipy; print('OK')"` is executed
- **THEN** the output SHALL contain "OK"
- **AND** the exit code SHALL be 0

#### Scenario: Lock file tracking
- **WHEN** `uv.lock` exists in the project root
- **THEN** `git ls-files uv.lock` SHALL return the file path (file is tracked)
- **AND** `.gitignore` SHALL NOT contain a pattern matching `uv.lock`

#### Scenario: Extras do not remove base dependencies
- **WHEN** `uv sync --extra perf` is executed
- **THEN** all core dependencies SHALL still be installed
- **AND** additional polars and pyarrow packages SHALL also be installed
