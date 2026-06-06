# Improvement Opportunities

This report identifies risks and improvement areas from the current codebase. It does not propose code changes as completed work.

## Technical Debt

### No Automated Tests

No test files or test configuration are present. Core behavior such as plan parsing, path safety, web search parsing, retry behavior, and report formatting is untested.

Evidence: repository inventory contains no `tests/` directory or test files.

Suggested improvements:

- Add unit tests for `_parse_plan()`, `_safe_path()`, `_retry_delay_seconds()`, and `_format_report_from_memory()`.
- Add mocked SDK tests for tool-calling and rate-limit retries.
- Add mocked API-response tests for Tavily and Brave Search result normalization.

### Large `Agent` Class

`Agent` handles provider setup, prompts, planning, execution, tool routing, memory persistence, retry handling, and report formatting in one class.

Evidence: [agent.py](../gemini_research_agent/agent.py#L138-L698).

Suggested improvements:

- Split provider client, memory store, report writer, and tool executor into smaller modules.
- Keep orchestration in `Agent`, but delegate storage and external integrations.

### Inline Prompts

Prompts are hardcoded inside methods.

Evidence: [agent.py](../gemini_research_agent/agent.py#L241-L331).

Suggested improvements:

- Move prompts to named constants or versioned prompt templates.
- Add prompt tests for expected output format constraints.

## Missing Abstractions

### No Memory Store Interface

Memory is directly represented as a dictionary and written with `Path.write_text()`.

Evidence: [agent.py](../gemini_research_agent/agent.py#L148-L158), [agent.py](../gemini_research_agent/agent.py#L576-L581).

Suggested improvements:

- Introduce a `MemoryStore` abstraction.
- Add schema validation for generated memory.
- Consider append-only event logs if auditability matters.

### No Search Provider Interface

`web_search` hardcodes Tavily and Brave Search behavior.

Evidence: [tools/web_search.py](../gemini_research_agent/tools/web_search.py#L29-L90).

Suggested improvements:

- Add a search provider interface.
- Move provider-specific payload and response mapping into separate classes/functions.
- Add provider health metrics and clearer quota/auth diagnostics.

### No Tool Metadata Registry

Tool schemas and runtime mappings are separate structures that must stay manually aligned.

Evidence: schemas in [agent.py](../gemini_research_agent/agent.py#L46-L135), runtime mapping in [agent.py](../gemini_research_agent/agent.py#L170-L175).

Suggested improvements:

- Define tools with a single source of truth that includes schema and callable.
- Validate that every schema has a runtime function and every runtime function has a schema.

## Security Risks

### Tool-Driven File Writes

The model can request `write_file`; the agent scopes those writes into `runs/<run_id>/artifacts/` before calling the file tool. Path traversal outside the workspace is blocked. Remaining risk is mostly around overwrite behavior inside the artifacts directory and accidental exposure of generated files.

Evidence: artifact scoping in [agent.py](../gemini_research_agent/agent.py), path safety in [tools/file_tools.py](../gemini_research_agent/tools/file_tools.py#L11-L16), write behavior in [tools/file_tools.py](../gemini_research_agent/tools/file_tools.py#L25-L30).

Suggested improvements:

- Add overwrite protection or versioned filenames for artifacts.
- Log file diff summaries for tool writes.

### Tool Error Strings May Expose Local Paths

Tool exceptions are stored as `{"error": str(exc)}`.

Evidence: [agent.py](../gemini_research_agent/agent.py#L474-L483).

Suggested improvements:

- Sanitize filesystem errors before exposing them to the model or memory.
- Separate internal debug logs from model-visible tool results.

### Generated Memory May Contain Sensitive Content

`runs/latest/memory.json` stores goals, tool call arguments, tool results, and final answers.

Evidence: [agent.py](../gemini_research_agent/agent.py#L148-L158), [agent.py](../gemini_research_agent/agent.py#L474-L493).

Suggested improvements:

- Keep `runs/latest/memory.json` ignored by git; already configured in [.gitignore](../.gitignore#L5).
- Add redaction for secrets in tool results.
- Avoid allowing `read_file` to read `.env`.

## Scalability Issues

### Local File History Has No Concurrency Control

The agent writes latest-run files (`runs/latest/memory.json`, `runs/latest/report.md`) and archives every run under `runs/<run_id>/` with `runs/goal_history.jsonl` and per-run artifacts. This preserves local history, but it is still plain filesystem storage.

Evidence: [agent.py](../gemini_research_agent/agent.py).

Impact:

- Concurrent runs can still race when writing latest-run files or appending the JSONL index.
- There is no query API, locking, compaction, retention policy, or database-backed index.

Suggested improvements:

- Add file locking around `runs/latest/memory.json`, `runs/latest/report.md`, and `runs/goal_history.jsonl`.
- Add a retention/cleanup policy for `runs/`.
- Move long-term run history to SQLite if querying/filtering becomes important.

### Synchronous Network Calls

Gemini calls, web search, and retries are synchronous.

Evidence: direct SDK calls and `time.sleep()` retry handling ([agent.py](../gemini_research_agent/agent.py#L426-L470)).

Suggested improvements:

- Add request timeouts where SDK supports them.
- Consider async execution only if multi-run or UI concurrency becomes a requirement.

### Search API Availability and Quota Risk

Search now depends on Tavily and Brave API authentication, quotas, and availability.

Evidence: API keys and provider calls are handled in `tools/web_search.py` ([tools/web_search.py](../gemini_research_agent/tools/web_search.py#L93-L204)).

Suggested improvements:

- Add quota-aware retry and backoff for search APIs.
- Add provider-specific smoke tests.
- Preserve structured failure details in `runs/latest/memory.json`.

## Documentation Gaps

Before this documentation set, the README covered setup and basic behavior but not architecture, workflow, APIs, data model, or failure handling.

Evidence: [README.md](../README.md#L1-L56).

Suggested improvements:

- Keep `docs/` synchronized with code changes.
- Add a short "Operational Runbook" for common failures such as missing env vars, Gemini auth errors, and search provider blocking.

## Operational Risks

### Missing Configuration Is Detected Late

Configuration is checked when `Agent()` is constructed, after the CLI has already prompted for user input.

Evidence: `main()` asks for goal before `Agent()` construction ([main.py](../gemini_research_agent/main.py#L6-L14)).

Suggested improvement:

- Validate configuration before asking for the goal, or provide a `--check-config` command.

### Tool-Calling Capability Is Not Smoke-Tested at Startup

The code now uses Google GenAI native function calling, but it does not run a startup smoke test to verify that the configured `GEMINI_MODEL` supports the expected tool behavior.

Evidence: model configuration is read during `Agent()` construction, while tool-calling is first exercised during plan-step execution ([agent.py](../gemini_research_agent/agent.py)).

Suggested improvements:

- Add a startup smoke test for tool-calling support.
- Fall back to text-only execution when tool calling is unsupported.

## Suggested Priorities

1. Add tests around memory, tools, retries, and plan parsing.
2. Add overwrite protection or versioned filenames for generated artifacts.
3. Protect `read_file` from reading sensitive local files such as `.env`.
4. Introduce a unified tool registry abstraction.
5. Add search API quota handling and provider smoke tests.
6. Add configuration validation and clearer startup diagnostics.
