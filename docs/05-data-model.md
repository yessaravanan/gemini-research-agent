# Data Model

## Summary

The project has no relational database, no migrations, no ORM models, no vector store, and no external state service. Persistent data is stored in local files:

- `memory.json`: structured JSON run state.
- `report.md`: generated Markdown report.

Evidence:

- Memory path and report path are constructor defaults ([agent.py](../agent.py#L141-L147)).
- Memory is written with `Path.write_text()` ([agent.py](../agent.py#L576-L581)).
- Report is rendered from finalized in-memory state and written directly to `report.md` ([agent.py](../agent.py#L226-L234)).

## `memory.json` Schema

The schema is implicit in `Agent.__init__()` and evolves during execution.

```json
{
  "goal": "string",
  "started_at": "string ISO-8601 UTC timestamp",
  "completed_at": "string ISO-8601 UTC timestamp or empty string",
  "providers": [
    {
      "name": "string",
      "model": "string"
    }
  ],
  "plan": ["string"],
  "reasoning_steps": [
    {
      "timestamp": "string ISO-8601 UTC timestamp",
      "note": "string"
    }
  ],
  "rate_limit_failures": [
    {
      "timestamp": "string ISO-8601 UTC timestamp",
      "provider": "string",
      "model": "string",
      "attempt": "integer",
      "max_retries": "integer",
      "retry_in_seconds": "number",
      "will_retry": "boolean"
    }
  ],
  "tool_call_failures": [
    {
      "timestamp": "string ISO-8601 UTC timestamp",
      "provider": "string",
      "model": "string",
      "error": "string",
      "fallback": "string"
    }
  ],
  "tool_calls": [
    {
      "tool": "string",
      "arguments": "object",
      "result": "object or scalar",
      "timestamp": "string ISO-8601 UTC timestamp"
    }
  ],
  "step_results": ["string"],
  "final_answer": "string"
}
```

Evidence:

- Initial keys: [agent.py](../agent.py#L148-L158)
- Provider records: [agent.py](../agent.py#L167-L169)
- Tool call records: [agent.py](../agent.py#L485-L491)
- Rate-limit records: [agent.py](../agent.py#L603-L612)
- Timestamp generation: [agent.py](../agent.py#L695-L698)

## Relationships

```mermaid
erDiagram
    RUN ||--o{ PROVIDER : records
    RUN ||--o{ PLAN_STEP : includes
    RUN ||--o{ REASONING_STEP : logs
    RUN ||--o{ TOOL_CALL : records
    RUN ||--o{ RATE_LIMIT_FAILURE : records
    RUN ||--o{ TOOL_CALL_FAILURE : records
    RUN ||--o{ STEP_RESULT : includes
    RUN ||--|| FINAL_ANSWER : produces

    RUN {
        string goal
        string started_at
        string completed_at
    }
    PROVIDER {
        string name
        string model
    }
    PLAN_STEP {
        string text
        int order
    }
    REASONING_STEP {
        string timestamp
        string note
    }
    TOOL_CALL {
        string tool
        object arguments
        object result
        string timestamp
    }
    RATE_LIMIT_FAILURE {
        string timestamp
        string provider
        string model
        int attempt
        int max_retries
        number retry_in_seconds
        boolean will_retry
    }
    TOOL_CALL_FAILURE {
        string timestamp
        string provider
        string model
        string error
        string fallback
    }
    STEP_RESULT {
        string text
        int order
    }
    FINAL_ANSWER {
        string markdown
    }
```

This ER diagram models JSON document structure, not database tables.

## `report.md` Structure

`report.md` is generated from `_format_report_from_memory()` and contains these sections:

1. `# Agent Report`
2. `## Goal`
3. `## Providers`
4. `## Plan`
5. `## Reasoning Steps`
6. `## Rate Limit Failures`
7. `## Step Results`
8. `## Final Answer`

Evidence: [agent.py](../agent.py#L520-L568).

## Tool Result Schemas

### `read_file`

```json
{
  "path": "string",
  "content": "string"
}
```

Evidence: [tools/file_tools.py](../tools/file_tools.py#L19-L22).

### `write_file`

```json
{
  "path": "string",
  "status": "written"
}
```

Evidence: [tools/file_tools.py](../tools/file_tools.py#L25-L30).

### `list_files`

```json
{
  "path": "string",
  "files": ["string"]
}
```

Evidence: [tools/file_tools.py](../tools/file_tools.py#L33-L48).

### `web_search`

Success:

```json
{
  "query": "string",
  "provider": "duckduckgo or brave",
  "results": [
    {
      "title": "string",
      "url": "string",
      "snippet": "string"
    }
  ]
}
```

Failure or no parsed results:

```json
{
  "query": "string",
  "provider": "duckduckgo,brave",
  "results": [],
  "error": "string"
}
```

Evidence: [tools/web_search.py](../tools/web_search.py#L29-L58), [tools/web_search.py](../tools/web_search.py#L93-L204).

## Vector Stores

No vector store, embedding model, semantic index, or retrieval database is present.

## Memory Store

The memory store is `memory.json`, overwritten on each `_save_memory()` call. It is not append-only and has no locking, versioning, or schema validation.

Evidence: [agent.py](../agent.py#L576-L581).
