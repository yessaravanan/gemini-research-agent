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

Evidence: [agent.py](../agent.py#L138-L698).

Suggested improvements:

- Split provider client, memory store, report writer, and tool executor into smaller modules.
- Keep orchestration in `Agent`, but delegate storage and external integrations.

### Inline Prompts

Prompts are hardcoded inside methods.

Evidence: [agent.py](../agent.py#L241-L331).

Suggested improvements:

- Move prompts to named constants or versioned prompt templates.
- Add prompt tests for expected output format constraints.

## Missing Abstractions

### No Memory Store Interface

Memory is directly represented as a dictionary and written with `Path.write_text()`.

Evidence: [agent.py](../agent.py#L148-L158), [agent.py](../agent.py#L576-L581).

Suggested improvements:

- Introduce a `MemoryStore` abstraction.
- Add schema validation for generated memory.
- Consider append-only event logs if auditability matters.

### No Search Provider Interface

`web_search` hardcodes Tavily and Brave Search behavior.

Evidence: [tools/web_search.py](../tools/web_search.py#L29-L90).

Suggested improvements:

- Add a search provider interface.
- Move provider-specific payload and response mapping into separate classes/functions.
- Add provider health metrics and clearer quota/auth diagnostics.

### No Tool Metadata Registry

Tool schemas and runtime mappings are separate structures that must stay manually aligned.

Evidence: schemas in [agent.py](../agent.py#L46-L135), runtime mapping in [agent.py](../agent.py#L170-L175).

Suggested improvements:

- Define tools with a single source of truth that includes schema and callable.
- Validate that every schema has a runtime function and every runtime function has a schema.

## Security Risks

### Tool-Driven File Writes

The model can request `write_file` for any path under the workspace. Path traversal outside the workspace is blocked, but overwriting important workspace files is still possible.

Evidence: path safety in [tools/file_tools.py](../tools/file_tools.py#L11-L16), write behavior in [tools/file_tools.py](../tools/file_tools.py#L25-L30).

Suggested improvements:

- Restrict write targets to an output directory unless explicitly approved.
- Add overwrite protection for source files.
- Log file diff summaries for tool writes.

### Tool Error Strings May Expose Local Paths

Tool exceptions are stored as `{"error": str(exc)}`.

Evidence: [agent.py](../agent.py#L474-L483).

Suggested improvements:

- Sanitize filesystem errors before exposing them to the model or memory.
- Separate internal debug logs from model-visible tool results.

### Generated Memory May Contain Sensitive Content

`memory.json` stores goals, tool call arguments, tool results, and final answers.

Evidence: [agent.py](../agent.py#L148-L158), [agent.py](../agent.py#L474-L493).

Suggested improvements:

- Keep `memory.json` ignored by git; already configured in [.gitignore](../.gitignore#L5).
- Add redaction for secrets in tool results.
- Avoid allowing `read_file` to read `.env`.

## Scalability Issues

### Single-Run Local Files

The agent writes to fixed default files: `memory.json` and `report.md`.

Evidence: [agent.py](../agent.py#L141-L147).

Impact:

- Concurrent runs can overwrite each other.
- Historical runs are not retained unless files are renamed externally.

Suggested improvements:

- Use run IDs and write to `runs/<timestamp>/memory.json` and `runs/<timestamp>/report.md`.
- Add a configurable output directory.

### Synchronous Network Calls

Gemini calls, web search, and retries are synchronous.

Evidence: direct SDK calls and `time.sleep()` retry handling ([agent.py](../agent.py#L426-L470)).

Suggested improvements:

- Add request timeouts where SDK supports them.
- Consider async execution only if multi-run or UI concurrency becomes a requirement.

### Search API Availability and Quota Risk

Search now depends on Tavily and Brave API authentication, quotas, and availability.

Evidence: API keys and provider calls are handled in `tools/web_search.py` ([tools/web_search.py](../tools/web_search.py#L93-L204)).

Suggested improvements:

- Add quota-aware retry and backoff for search APIs.
- Add provider-specific smoke tests.
- Preserve structured failure details in `memory.json`.

## Documentation Gaps

Before this documentation set, the README covered setup and basic behavior but not architecture, workflow, APIs, data model, or failure handling.

Evidence: [README.md](../README.md#L1-L56).

Suggested improvements:

- Keep `docs/` synchronized with code changes.
- Add a short "Operational Runbook" for common failures such as missing env vars, Gemini auth errors, and search provider blocking.

## Operational Risks

### Missing Configuration Is Detected Late

Configuration is checked when `Agent()` is constructed, after the CLI has already prompted for user input.

Evidence: `main()` asks for goal before `Agent()` construction ([main.py](../main.py#L6-L14)).

Suggested improvement:

- Validate configuration before asking for the goal, or provide a `--check-config` command.

### Tool-Calling Capability Is Not Smoke-Tested at Startup

The code now uses Google GenAI native function calling, but it does not run a startup smoke test to verify that the configured `GEMINI_MODEL` supports the expected tool behavior.

Evidence: model configuration is read during `Agent()` construction, while tool-calling is first exercised during plan-step execution ([agent.py](../agent.py)).

Suggested improvements:

- Add a startup smoke test for tool-calling support.
- Fall back to text-only execution when tool calling is unsupported.

## Suggested Priorities

1. Add tests around memory, tools, retries, and plan parsing.
2. Protect `write_file` from overwriting source files.
3. Move generated outputs into per-run directories.
4. Introduce a unified tool registry abstraction.
5. Add search API quota handling and provider smoke tests.
6. Add configuration validation and clearer startup diagnostics.
