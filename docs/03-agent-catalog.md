# Agent Catalog

## Inventory

Only one agent is implemented: the `Agent` class in [agent.py](../agent.py#L138-L239).

No separate sub-agents, planner agent class, executor agent class, multi-agent router, or external agent registry exists in the current codebase.

## Agent: `Agent`

### Purpose

`Agent` plans and executes a user goal, uses tools when requested by the model, records progress, and produces a Markdown report.

Evidence: class docstring and `run()` workflow ([agent.py](../agent.py#L138-L239)).

### Inputs

| Input | Source | Evidence |
| --- | --- | --- |
| `goal` | CLI standard input passed to `Agent.run(goal)` | [main.py](../main.py#L6-L14), [agent.py](../agent.py#L194-L239) |
| `GEMINI_API_KEY` | Environment or `.env` | [agent.py](../agent.py#L27-L31), [agent.py](../agent.py#L177-L190) |
| `GEMINI_MODEL` | Environment or `.env` | [agent.py](../agent.py#L177-L190) |
| Retry settings | `MODEL_MAX_RETRIES`, `MODEL_RETRY_BASE_SECONDS`, `MODEL_RETRY_MAX_SECONDS` | [agent.py](../agent.py#L426-L429), [agent.py](../agent.py#L617-L629) |
| Tool call arguments | Gemini tool-call response payloads | [agent.py](../agent.py#L381-L422) |

### Outputs

| Output | Destination | Evidence |
| --- | --- | --- |
| Final answer text | Console and `memory.json` | [main.py](../main.py#L16-L19), [agent.py](../agent.py#L226-L228) |
| Progress memory | `memory.json` | [agent.py](../agent.py#L148-L158), [agent.py](../agent.py#L576-L581) |
| Markdown report | `report.md` | [agent.py](../agent.py#L226-L237), [agent.py](../agent.py#L520-L568) |
| Tool call results | `memory["tool_calls"]` | [agent.py](../agent.py#L474-L493) |
| Rate limit records | `memory["rate_limit_failures"]` | [agent.py](../agent.py#L583-L615) |

### Tools Used

The agent registers four local tools in `available_tools` and exposes Gemini-native function declarations through `_build_model_tools()` ([agent.py](../agent.py)).

| Tool | Purpose | Implementation |
| --- | --- | --- |
| `read_file` | Read a UTF-8 workspace file | [tools/file_tools.py](../tools/file_tools.py#L19-L22) |
| `write_file` | Write UTF-8 content under workspace | [tools/file_tools.py](../tools/file_tools.py#L25-L30) |
| `list_files` | List workspace files/directories | [tools/file_tools.py](../tools/file_tools.py#L33-L48) |
| `web_search` | Search web using Tavily then Brave Search API by default | [tools/web_search.py](../tools/web_search.py#L29-L58) |

### Memory Used

`Agent.__init__()` initializes in-memory state with:

- `goal`
- `started_at`
- `completed_at`
- `providers`
- `plan`
- `reasoning_steps`
- `rate_limit_failures`
- `tool_calls`
- `step_results`
- `final_answer`

Evidence: [agent.py](../agent.py#L148-L158).

The memory is persisted by `_save_memory()` using `json.dumps(..., indent=2, ensure_ascii=False)` ([agent.py](../agent.py#L576-L581)).

### Decision Logic

| Decision | Logic | Evidence |
| --- | --- | --- |
| Whether the agent can start | Requires both `GEMINI_API_KEY` and `GEMINI_MODEL`; otherwise raises `RuntimeError` | [agent.py](../agent.py#L160-L192) |
| Plan parsing | Prefer JSON `{"steps": [...]}`; fall back to non-empty lines; final fallback to four default steps | [agent.py](../agent.py#L495-L518) |
| Web search | Always run once for the original goal before plan-step execution | [agent.py](../agent.py#L209-L215) |
| Tool execution | `_chat_with_tools()` reads Gemini function calls, executes mapped Python tools through `_execute_tool()`, and appends native function responses | [agent.py](../agent.py) |
| Tool-loop termination | The native function-call loop stops when Gemini returns text or reaches `TOOL_MAX_REMOTE_CALLS` | [agent.py](../agent.py) |
| Report generation | Render current memory-derived sections into Markdown | [agent.py](../agent.py#L520-L568) |

### Dependencies

- `genai.Client` from the `google-genai` package ([agent.py](../agent.py)).
- `.env` loading through `python-dotenv` ([agent.py](../agent.py#L21-L31)).
- Local tool exports from `tools` package ([agent.py](../agent.py#L24), [tools/__init__.py](../tools/__init__.py#L1-L6)).
- Tavily and Brave Search API requests through `urllib.request` ([tools/web_search.py](../tools/web_search.py#L14-L16), [tools/web_search.py](../tools/web_search.py#L207-L210)).

### Failure Handling

| Failure | Handling | Evidence |
| --- | --- | --- |
| Missing Gemini env config | Raise `RuntimeError` during `Agent` construction | [agent.py](../agent.py#L160-L165) |
| Planning model failure | Use fallback plan if `_chat()` returns `Model request failed:` | [agent.py](../agent.py#L255-L265) |
| HTTP 429 | Retry with backoff, record sanitized rate-limit failure, stop after configured attempts | [agent.py](../agent.py#L426-L470), [agent.py](../agent.py#L583-L629) |
| Tool-calling request failure, non-429 | Fall back to text-only model response with sanitized error message | [agent.py](../agent.py#L357-L379) |
| Invalid tool JSON arguments | Return tool result with error string | [agent.py](../agent.py#L405-L412) |
| Tool implementation exception | Catch exception and store `{"error": str(exc)}` | [agent.py](../agent.py#L474-L483) |
| Search provider failure | Return structured provider error and try the configured fallback provider | [tools/web_search.py](../tools/web_search.py#L29-L58), [tools/web_search.py](../tools/web_search.py#L123-L131), [tools/web_search.py](../tools/web_search.py#L177-L185) |
| Path traversal in file tools | Reject paths outside workspace | [tools/file_tools.py](../tools/file_tools.py#L8-L16) |

## Nonexistent Agents

The codebase does not include:

- A UI-created agent model.
- A persisted agent registry.
- Agent templates.
- Separate planner/executor/reviewer agent classes.
- Multi-agent orchestration.

This conclusion is based on the repository inventory and the only class named `Agent` in [agent.py](../agent.py#L138-L239).
