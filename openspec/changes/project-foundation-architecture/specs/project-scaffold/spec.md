## ADDED Requirements

### Requirement: Project directory structure
The system SHALL create a project directory structure that maps to the three-layer architecture (Orchestration, Knowledge, Integration) using Python src layout with hatchling build backend.

The required directory tree SHALL be:
```
vibewriting/
├── CLAUDE.md
├── pyproject.toml
├── .mcp.json
├── .gitignore
├── .env.example
├── build.sh
├── paper/
│   ├── main.tex
│   ├── latexmkrc
│   ├── sections/{introduction,related-work,method,experiments,conclusion,appendix}.tex
│   ├── bib/references.bib
│   ├── figures/
│   └── build/
├── src/vibewriting/
│   ├── __init__.py
│   ├── config.py
│   ├── processing/{__init__,cleaners,transformers,statistics}.py
│   ├── visualization/{__init__,figures,tables,pgf_export}.py
│   ├── latex/{__init__,compiler}.py
│   ├── models/{__init__,paper,experiment}.py
│   └── agents/__init__.py
├── data/{raw,processed,cache}/
├── output/{figures,tables,assets}/
├── scripts/{validate_env.py,dify-kb-mcp/server.py}
├── tests/{conftest.py,test_processing/,test_visualization/,test_latex/}
└── .claude/{settings.local.json,skills/}
```

#### Scenario: Fresh project initialization
- **WHEN** the scaffold script runs on a directory containing only `origin.md` and `openspec/`
- **THEN** all directories and placeholder files listed above SHALL exist
- **AND** Python files SHALL contain valid syntax (pass `python -m py_compile`)
- **AND** the `src/vibewriting/` package SHALL be importable

#### Scenario: Idempotent re-run
- **WHEN** the scaffold script runs on an already-scaffolded project
- **THEN** existing files SHALL NOT be overwritten
- **AND** missing files SHALL be created
- **AND** the directory hash (excluding timestamps) SHALL be identical to a single-run result

### Requirement: Git repository initialization
The system SHALL initialize a Git repository using idempotent mode: if `.git/` already exists, only verify and supplement configuration.

The `.gitignore` SHALL cover:
- LaTeX compilation artifacts (*.aux, *.log, *.bbl, *.synctex.gz, *.xdv, paper/build/)
- Python caches (__pycache__, .mypy_cache, .ruff_cache, .venv/)
- Environment files (.env)
- Data large files (data/raw/*.csv, data/raw/*.xlsx with >10MB)

The `.gitignore` SHALL NOT ignore:
- .env.example
- .mcp.json
- paper/figures/*
- paper/bib/*
- uv.lock

#### Scenario: First-time Git initialization
- **WHEN** `git init` runs on a directory without `.git/`
- **THEN** a Git repository SHALL be created
- **AND** `.gitignore` SHALL contain all required patterns
- **AND** `.env` SHALL be ignored, `.env.example` SHALL be tracked

#### Scenario: Idempotent re-initialization
- **WHEN** `git init` runs on a directory that already contains `.git/`
- **THEN** the existing repository SHALL NOT be destroyed
- **AND** `.gitignore` SHALL be verified and supplemented if patterns are missing
- **AND** HEAD reference SHALL remain stable

#### Scenario: Gitignore pattern correctness
- **WHEN** a file matching a LaTeX or Python ignore pattern is created (e.g., `paper/build/main.pdf`, `src/__pycache__/`)
- **THEN** `git status` SHALL report the file as ignored
- **AND** the file SHALL NOT appear in `git add --dry-run .` output
