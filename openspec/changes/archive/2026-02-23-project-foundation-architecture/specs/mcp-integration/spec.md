## ADDED Requirements

### Requirement: MCP server configuration
The system SHALL create `.mcp.json` in the project root containing configurations for paper-search (stdio) and dify-knowledge (custom bridge) MCP servers.

The `.mcp.json` SHALL:
- Be valid JSON parseable by `jq .`
- Contain exactly 2 server entries: `paper-search` and `dify-knowledge`
- Use environment variable interpolation (`${VAR_NAME}`) for all secrets
- NOT contain hardcoded API keys or credentials

**paper-search configuration:**
- command: `uv`
- args: `["run", "paper-search-mcp"]`
- cwd: `C:/Users/17162/Desktop/Terms/workflow` (absolute path)
- env: SERPAPI_API_KEY, LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL, OPENAI_API_KEY

**dify-knowledge configuration:**
- command: `uv`
- args: `["run", "python", "scripts/dify-kb-mcp/server.py"]`
- env: DIFY_API_BASE_URL, DIFY_API_KEY, DIFY_DATASET_ID

#### Scenario: JSON format validation
- **WHEN** `.mcp.json` is parsed by `jq .`
- **THEN** parsing SHALL succeed with exit code 0
- **AND** `mcpServers` object SHALL contain exactly `paper-search` and `dify-knowledge` keys

#### Scenario: Configuration round-trip
- **WHEN** `.mcp.json` is parsed, serialized, and re-parsed
- **THEN** the semantic content (server names, commands, args) SHALL be identical

#### Scenario: No hardcoded secrets
- **WHEN** `.mcp.json` is scanned for patterns matching API key formats
- **THEN** no actual API keys SHALL be found
- **AND** all secret values SHALL use `${...}` interpolation syntax

### Requirement: paper-search MCP integration
The system SHALL integrate paper-search exclusively through MCP stdio protocol as configured in `.mcp.json`. No paper-search source code SHALL be copied into the vibewriting repository.

The integration SHALL expose 4 MCP tools:
- `search_papers(query, domain, max_results)` — Start search session
- `decide(session_id, action, user_response)` — Submit checkpoint decision
- `export_results(session_id, format)` — Export results
- `get_session(session_id)` — Query session state

#### Scenario: No vendored code
- **WHEN** the vibewriting repository is scanned
- **THEN** zero files from paper-search source code SHALL be found
- **AND** only MCP configuration and CLAUDE.md documentation SHALL reference paper-search

#### Scenario: MCP connectivity verification
- **WHEN** paper-search MCP server is started via `.mcp.json` configuration
- **THEN** the server SHALL respond to tool discovery requests
- **AND** all 4 tools SHALL be listed in the capability response

#### Scenario: External path validation
- **WHEN** the configured `cwd` path `C:/Users/17162/Desktop/Terms/workflow` is checked
- **THEN** the directory SHALL exist and be accessible
- **AND** `uv run paper-search-mcp` SHALL be executable from that directory

### Requirement: Dify MCP bridge server
The system SHALL provide a custom MCP bridge server at `scripts/dify-kb-mcp/server.py` that bridges Dify knowledge base API to MCP protocol with graceful degradation.

The bridge SHALL expose 2 tools:
- `retrieve_knowledge(query, top_k, search_method, score_threshold)` — Hybrid search
- `list_documents(page, limit, keyword)` — Document listing

The bridge SHALL:
- Use httpx for async HTTP calls to Dify API
- Support 3 search methods: hybrid_search, keyword_search, semantic_search
- Enable reranking by default
- Read config from environment variables: DIFY_API_BASE_URL, DIFY_API_KEY, DIFY_DATASET_ID

**Graceful degradation behavior:**
- When Dify service is unavailable (timeout/connection refused/5xx), the bridge SHALL return a well-defined error response
- The MCP server process SHALL NOT crash or exit
- The error response SHALL include the failure reason and a suggestion to check credentials
- Retry attempts SHALL NOT exceed a configurable max_retries limit

#### Scenario: Syntax validation
- **WHEN** `python -c "import ast; ast.parse(open('scripts/dify-kb-mcp/server.py').read())"` is executed
- **THEN** the exit code SHALL be 0

#### Scenario: Graceful degradation on connection failure
- **WHEN** DIFY_API_BASE_URL points to an unreachable host
- **AND** `retrieve_knowledge` is called
- **THEN** the bridge SHALL return an error response within timeout
- **AND** the MCP server process SHALL remain alive
- **AND** subsequent requests SHALL be handled normally

#### Scenario: Graceful degradation on missing credentials
- **WHEN** DIFY_API_KEY is empty or unset
- **THEN** the bridge SHALL start successfully
- **AND** tool calls SHALL return a clear "credentials not configured" message
- **AND** the MCP server SHALL NOT crash

### Requirement: Custom Claude Code Skills
The system SHALL create 3 custom Skills in `.claude/skills/` directory.

| Skill | Trigger | Description |
|-------|---------|-------------|
| `/search-literature` | Literature search workflow | Invokes paper-search MCP tools |
| `/retrieve-kb` | Knowledge base retrieval | Invokes Dify MCP tools |
| `/validate-citations` | Citation integrity check | Runs checkcites on LaTeX aux files |

Each Skill SHALL:
- Have a valid `SKILL.md` file with YAML frontmatter
- Contain clear instructions for Claude Code to follow
- Reference the correct MCP tools or shell commands

#### Scenario: SKILL.md format validation
- **WHEN** each SKILL.md file is parsed
- **THEN** YAML frontmatter SHALL parse successfully
- **AND** the instruction body SHALL be non-empty

#### Scenario: Skill invocation reference correctness
- **WHEN** `/search-literature` skill references are checked
- **THEN** all referenced MCP tool names SHALL match the paper-search tool list
