## 1. P0: Project Scaffold + Git + Python Environment + CLAUDE.md

- [x] 1.1 Create project directory structure (all directories and placeholder `__init__.py` files per REQ-01 spec)
- [x] 1.2 Create `.gitignore` with LaTeX + Python + environment patterns (per REQ-06 spec, ensure .env ignored, .env.example/uv.lock/.mcp.json tracked)
- [x] 1.3 Create `.gitattributes` with `* text=auto eol=lf` and `*.sh text eol=lf` (prevent CRLF issues in bash scripts)
- [x] 1.4 Create `.env.example` with all required environment variable placeholders (SERPAPI_API_KEY, LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL, OPENAI_API_KEY, DIFY_API_BASE_URL, DIFY_API_KEY, DIFY_DATASET_ID)
- [x] 1.5 Create `pyproject.toml` with hatchling build backend, src layout, all dependencies per REQ-05 spec (core + optional groups + dev group)
- [x] 1.6 Create `src/vibewriting/__init__.py` with package version string
- [x] 1.7 Create `src/vibewriting/config.py` with dotenv loading and Pydantic Settings model
- [x] 1.8 Create placeholder modules: `processing/{__init__,cleaners,transformers,statistics}.py`, `visualization/{__init__,figures,tables,pgf_export}.py`, `latex/{__init__,compiler}.py`, `models/{__init__,paper,experiment}.py`, `agents/__init__.py`
- [x] 1.9 Run `uv sync` to resolve dependencies and generate `uv.lock`
- [x] 1.10 Verify: `uv run python -c "import pandas, matplotlib, seaborn, scipy; print('OK')"` returns OK
- [x] 1.11 Initialize Git repository (idempotent: check `.git/` existence first)
- [x] 1.12 Create `CLAUDE.md` with 5 core elements, verify line count <= 300
- [x] 1.13 Verify: `git status` shows clean tracking (no .env in tracked, uv.lock and .mcp.json tracked)

## 2. P1: MCP Server Configuration + paper-search Integration

- [x] 2.1 Create `.mcp.json` with paper-search (stdio, absolute cwd path) and dify-knowledge (bridge server) configurations per REQ-04 spec
- [x] 2.2 Verify: `jq . .mcp.json` parses successfully
- [x] 2.3 Verify: paper-search cwd path `C:/Users/17162/Desktop/Terms/workflow` exists and is accessible
- [x] 2.4 Create `.claude/settings.local.json` with `additionalDirectories` containing paper-search path
- [x] 2.5 Create Skill: `.claude/skills/search-literature/SKILL.md` — references paper-search MCP tools (search_papers, decide, export_results, get_session)
- [x] 2.6 Create Skill: `.claude/skills/retrieve-kb/SKILL.md` — references Dify MCP tools (retrieve_knowledge, list_documents)
- [x] 2.7 Create Skill: `.claude/skills/validate-citations/SKILL.md` — runs checkcites on paper/build/main.aux

## 3. P2: Environment Validation Script (v1)

- [x] 3.1 Create `scripts/validate_env.py` with PEP 723 inline metadata
- [x] 3.2 Implement required checks: Python version, core packages, Git, uv, .env existence
- [x] 3.3 Implement optional checks: TeX Live (xelatex), latexmk, bibtex, checkcites, Dify credentials, optional packages
- [x] 3.4 Implement tiered exit codes: 0=pass, 1=required fail, 2=optional fail
- [x] 3.5 Implement JSON report output (--json flag): check names, statuses, severity, installation instructions for failures
- [x] 3.6 Implement colored console output: [PASS] green, [FAIL] red, [WARN] yellow, [BLOCKED] yellow
- [x] 3.7 Verify: `uv run scripts/validate_env.py` runs without errors, reports TeX as [BLOCKED], Python deps as [PASS]
- [x] 3.8 Verify: `uv run scripts/validate_env.py --json` outputs valid JSON parseable by `python -m json.tool`

## 4. P3: LaTeX Templates + Build Script

- [x] 4.1 Create `paper/latexmkrc` with `$pdf_mode=5`, xelatex flags, bibtex config, output dirs per REQ-02 spec
- [x] 4.2 Create `paper/main.tex` with ctexart document class, all required packages, section inputs, bibliography config per REQ-02 spec
- [x] 4.3 Create section templates: `paper/sections/{introduction,related-work,method,experiments,conclusion,appendix}.tex` with placeholder content
- [x] 4.4 Create `paper/bib/references.bib` with 1-2 sample BibTeX entries (one English, one Chinese author)
- [x] 4.5 Create `build.sh` with 5 subcommands (build, watch, clean, check, doi2bib) per REQ-07 spec
- [x] 4.6 Verify: `bash -n build.sh` syntax check passes
- [x] 4.7 Verify: `bash build.sh clean` works (creates/clears paper/build/ directory)
- [x] 4.8 Verify: `bash build.sh doi2bib 10.1038/s41586-021-03819-2` returns BibTeX (requires internet)
- [x] 4.9 Verify: `bash build.sh build` compiles main.tex to PDF
- [x] 4.10 Verify: `bash build.sh check` runs checkcites without errors

## 5. P4: Dify MCP Bridge (blocked by credentials)

- [x] 5.1 Create `scripts/dify-kb-mcp/server.py` with MCP server skeleton, 2 tools (retrieve_knowledge, list_documents)
- [x] 5.2 Implement httpx async client for Dify `/v1/datasets/{id}/retrieve` API
- [x] 5.3 Implement graceful degradation: connection errors return well-defined error response, process does not crash
- [x] 5.4 Implement retry logic with configurable max_retries limit
- [x] 5.5 Implement missing credentials detection: start successfully, return "credentials not configured" on tool calls
- [x] 5.6 Verify: `python -c "import ast; ast.parse(open('scripts/dify-kb-mcp/server.py').read())"` exit code 0
- [ ] 5.7 [BLOCKED: Dify credentials] Verify: MCP server starts and responds to tool discovery

## 6. Final Validation

- [ ] 6.1 Run `uv run scripts/validate_env.py` — all required checks pass (exit code 0 or 2)
- [ ] 6.2 Verify CLAUDE.md line count: `wc -l CLAUDE.md` <= 300
- [ ] 6.3 Verify all Python files pass syntax check: `uv run python -m py_compile` on each .py file
- [ ] 6.4 Verify `.mcp.json` valid: `jq . .mcp.json` succeeds
- [ ] 6.5 Verify no hardcoded secrets in tracked files: scan for API key patterns
- [ ] 6.6 Verify uv.lock is tracked: `git ls-files uv.lock` returns path
- [ ] 6.7 Run `git status` — no unexpected untracked files, working tree clean after initial commit
