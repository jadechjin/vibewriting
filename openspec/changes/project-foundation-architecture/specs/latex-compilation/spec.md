## ADDED Requirements

### Requirement: LaTeX compilation environment
The system SHALL configure a LaTeX compilation environment using XeLaTeX via latexmk with `$pdf_mode=5` and ctexart document class.

The `paper/latexmkrc` SHALL contain:
- `$pdf_mode = 5` (XeLaTeX mode, the ONLY valid value)
- `$xelatex = 'xelatex -file-line-error -interaction=nonstopmode -synctex=1 %O %S'`
- `$bibtex = 'bibtex %O %B'`
- `$out_dir = 'build'` and `$aux_dir = 'build'`
- `$max_repeat = 5`

The `paper/main.tex` SHALL:
- Use `\documentclass[UTF8, a4paper, 12pt, zihao=-4]{ctexart}`
- Load required packages: geometry, amsmath, amssymb, amsthm, graphicx, booktabs, natbib, hyperref
- Use `\bibliographystyle{unsrtnat}` with `\bibliography{bib/references}`
- Use `\input{sections/...}` for chapter inclusion (NOT `\include`)
- Set page margins: 2.54cm top/bottom, 3.17cm left/right

#### Scenario: Successful compilation with TeX Live
- **WHEN** TeX Live is installed and `cd paper && latexmk` is executed
- **THEN** `paper/build/main.pdf` SHALL be generated
- **AND** the exit code SHALL be 0
- **AND** Chinese and English text SHALL render correctly

#### Scenario: Compilation idempotency
- **WHEN** `latexmk` is run twice with no source changes
- **THEN** the second run SHALL produce the same exit code (0)
- **AND** the PDF content SHALL be identical (excluding metadata timestamps)

#### Scenario: TeX Live not installed
- **WHEN** `xelatex` is not found in PATH
- **THEN** the build script SHALL exit with non-zero code
- **AND** SHALL output a clear error message with TeX Live installation instructions

### Requirement: Build script
The system SHALL provide `build.sh` compatible with Git Bash on Windows, implementing 5 subcommands.

| Subcommand | Behavior |
|------------|----------|
| `bash build.sh build` | Run `latexmk` in `paper/` directory, output to `paper/build/` |
| `bash build.sh watch` | Run `latexmk -pvc` for continuous compilation |
| `bash build.sh clean` | Remove all files in `paper/build/` |
| `bash build.sh check` | Run `checkcites build/main.aux` for citation integrity |
| `bash build.sh doi2bib <DOI>` | Use curl content negotiation to convert DOI to BibTeX |

The script SHALL:
- Start with `#!/usr/bin/env bash` and `set -euo pipefail`
- Use colored output (red=error, green=success, yellow=warning)
- Exit with non-zero code on any failure (fail-fast via `set -e`)
- NOT contain any PowerShell or CMD syntax
- Pass `bash -n build.sh` syntax check

#### Scenario: Build subcommand with TeX Live
- **WHEN** `bash build.sh build` is executed with TeX Live installed
- **THEN** `latexmk` SHALL be invoked in the `paper/` directory
- **AND** PDF SHALL be generated at `paper/build/main.pdf`

#### Scenario: Clean subcommand
- **WHEN** `bash build.sh clean` is executed
- **THEN** all files in `paper/build/` SHALL be removed
- **AND** the `paper/build/` directory itself SHALL remain

#### Scenario: DOI to BibTeX conversion
- **WHEN** `bash build.sh doi2bib 10.1038/s41586-021-03819-2` is executed
- **THEN** a valid BibTeX entry SHALL be returned to stdout
- **AND** no third-party tools beyond curl SHALL be used

#### Scenario: Fail-fast execution
- **WHEN** step K of a subcommand fails
- **THEN** no step after K SHALL execute
- **AND** the exit code SHALL be non-zero
