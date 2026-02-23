# claude-config Specification

## Purpose
TBD - created by archiving change project-foundation-architecture. Update Purpose after archive.
## Requirements
### Requirement: CLAUDE.md project configuration
The system SHALL create a CLAUDE.md file in the project root that configures Claude Code behavior for academic paper writing.

The file SHALL:
- Contain no more than 300 lines (inclusive of blank lines)
- Include all 5 core elements defined below
- Use progressive disclosure (summary first, details on demand)
- NOT contain specific business logic or API documentation

**Core Element 1 — Architecture and Tech Stack:**
- XeLaTeX + ctexart, BibTeX + natbib
- Python 3.12, uv, hatchling, src layout
- Three-layer architecture description

**Core Element 2 — Tool and Resource Pointers:**
- paper-search MCP tool list (4 tools with usage)
- Dify MCP knowledge retrieval tool
- Data directory path mapping
- Build script usage

**Core Element 3 — Validation Standards and Workflow Discipline:**
- Run `latexmk` after modifying .tex files
- Run `checkcites` after modifying .bib files
- One sentence per line in LaTeX (for git diff)

**Core Element 4 — Academic Style Constraints:**
- Objective third-person narrative tone
- Avoid LLM cliches
- Citation format: `\citep{}` for parenthetical, `\citet{}` for textual
- Use amsmath environments (prohibit `$$...$$`)

**Core Element 5 — Safety Boundaries:**
- Do not modify global config or system fonts
- Do not leak .env API keys
- Do not execute unapproved `git push`

#### Scenario: Line count validation
- **WHEN** CLAUDE.md is created
- **THEN** `wc -l CLAUDE.md` SHALL return a value <= 300

#### Scenario: Core elements presence
- **WHEN** CLAUDE.md is parsed
- **THEN** all 5 core element sections SHALL be present and non-empty
- **AND** each section SHALL contain at least one actionable instruction

#### Scenario: Path pointer validity
- **WHEN** all referenced paths in CLAUDE.md are checked
- **THEN** each path SHALL point to an existing file or directory in the project
- **OR** SHALL be clearly marked as conditional (e.g., "requires TeX Live")

#### Scenario: Update idempotency
- **WHEN** CLAUDE.md normalization is run twice
- **THEN** the file content SHALL be identical after both runs

