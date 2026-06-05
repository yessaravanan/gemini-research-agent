# API Reference

## Scope

This project does not expose a network API. The APIs documented here are:

- Internal Python functions/classes.
- Model-visible tool schemas.
- External HTTP/API integrations used by the runtime.

## Internal Python APIs

### `main.main()`

Purpose: prompt for a goal, instantiate `Agent`, run it, and print output paths.

Signature:

```python
def main() -> None
```

Evidence: [main.py](../main.py#L6-L23).

### `Agent.__init__(memory_path="memory.json", report_path="report.md")`

Purpose: initialize runtime paths, memory structure, Gemini provider, and local tools.

Inputs:

- `memory_path`: output path for JSON memory.
- `report_path`: output path for Markdown report.

Raises:

- `RuntimeError` if `GEMINI_API_KEY` or `GEMINI_MODEL` is missing.

Evidence: [agent.py](../agent.py#L141-L192).

### `Agent.run(goal: str) -> str`

Purpose: complete the full plan/search/execute/summarize/persist workflow.

Input:

- `goal`: user request text.

Output:

- final answer string.

Side effects:

- writes `memory.json`.
- writes `report.md`.
- prints plan and reasoning messages to stdout.

Evidence: [agent.py](../agent.py#L194-L239).

### `Agent.create_plan(goal: str) -> list[str]`

Purpose: ask Gemini for a 3-6 step JSON plan and parse it.

Failure behavior:

- If the model request fails, returns a built-in fallback plan.
- If JSON parsing fails, falls back to line parsing, then a final static plan.

Evidence: [agent.py](../agent.py#L241-L269), [agent.py](../agent.py#L495-L518).

### `Agent.execute_step(goal, plan, step, search_results) -> str`

Purpose: execute one plan step with context and optional model-requested tools.

Evidence: [agent.py](../agent.py#L271-L301).

### `Agent.create_final_answer(goal, plan, search_results, step_results) -> str`

Purpose: synthesize final Markdown answer using prior outputs.

Evidence: [agent.py](../agent.py#L303-L331).

## Tool APIs

### Model-Visible Tool Functions

`_build_model_tools()` exposes four Python function tools to Gemini:

- `read_file`
- `write_file`
- `list_files`
- `web_search`

Evidence: [agent.py](../agent.py).

### `read_file(path: str) -> dict[str, str]`

Request:

```json
{
  "path": "relative/path.txt"
}
```

Response:

```json
{
  "path": "relative/path.txt",
  "content": "file contents"
}
```

Security:

- Path must remain under the process workspace root.

Evidence: [tools/file_tools.py](../tools/file_tools.py#L11-L22).

### `write_file(path: str, content: str) -> dict[str, str]`

Request:

```json
{
  "path": "relative/path.txt",
  "content": "file contents"
}
```

Response:

```json
{
  "path": "relative/path.txt",
  "status": "written"
}
```

Security:

- Path must remain under the process workspace root.
- Parent directories are created automatically.

Evidence: [tools/file_tools.py](../tools/file_tools.py#L25-L30).

### `list_files(path: str = ".", recursive: bool = False) -> dict[str, list[str]]`

Request:

```json
{
  "path": ".",
  "recursive": false
}
```

Response:

```json
{
  "path": ".",
  "files": ["README.md", "agent.py"]
}
```

Errors:

- `FileNotFoundError` if path does not exist.
- `NotADirectoryError` if path is not a directory.
- `ValueError` if path escapes workspace.

Evidence: [tools/file_tools.py](../tools/file_tools.py#L33-L48).

### `web_search(query: str, max_results: int = 5) -> dict`

Request:

```json
{
  "query": "search terms",
  "max_results": 5
}
```

Response:

```json
{
  "query": "search terms",
  "provider": "tavily",
  "results": [
    {
      "title": "Result title",
      "url": "https://example.com",
      "snippet": "Short snippet"
    }
  ]
}
```

Failure response:

```json
{
  "query": "search terms",
  "provider": "tavily,brave",
  "results": [],
  "attempts": [
    {
      "provider": "tavily",
      "error": "HTTP 401: Unauthorized",
      "result_count": 0
    },
    {
      "provider": "brave",
      "error": "HTTP 429: Too Many Requests",
      "result_count": 0
    }
  ],
  "error": "tavily: HTTP 401: Unauthorized; brave: HTTP 429: Too Many Requests"
}
```

Behavior:

- Clamps `max_results` to `1..10`.
- Reads provider order from `SEARCH_PRIMARY` and `SEARCH_SECONDARY`.
- Supports `tavily` and `brave`.
- Returns normalized `title`, `url`, and `snippet` entries.
- Returns structured provider attempts when all providers fail.

Evidence: [tools/web_search.py](../tools/web_search.py#L29-L58), [tools/web_search.py](../tools/web_search.py#L61-L90).

## External APIs

### Gemini Native Generate Content API

Authentication:

- `GEMINI_API_KEY` is read from environment and passed to `genai.Client(api_key=...)`.

Model:

- `GEMINI_MODEL` is read from environment and passed as the `model` argument to `client.models.generate_content(...)`.

Evidence: [agent.py](../agent.py).

Request shape used by `_chat()`:

```python
client.models.generate_content(
    model=provider.model,
    contents=contents,
    config=types.GenerateContentConfig(
        temperature=0.2,
        system_instruction=system_instruction,
    ),
)
```

Evidence: [agent.py](../agent.py).

Request shape used by `_chat_with_tools()`:

```python
client.models.generate_content(
    model=provider.model,
    contents=contents,
    config=types.GenerateContentConfig(
        temperature=0.2,
        system_instruction=system_instruction,
        tools=self.model_tools,
    ),
)
```

Evidence: [agent.py](../agent.py).

Response handling:

- Text content is read from `response.text`, with a candidate/part fallback.
- Tool calls are read from Gemini response parts.
- The agent executes mapped Python tools with `_execute_tool()`.
- The agent appends native `Part.from_function_response(...)` parts and continues the loop.

Evidence: [agent.py](../agent.py).

### Tavily Search API

Request:

```text
POST https://api.tavily.com/search
```

Authentication:

- `TAVILY_API_KEY` is read from environment and sent as `Authorization: Bearer <key>`.

Request body:

```json
{
  "query": "search terms",
  "max_results": 5,
  "search_depth": "basic",
  "topic": "general",
  "include_answer": false,
  "include_raw_content": false
}
```

Response handling:

- Reads `results[]`.
- Maps `title`, `url`, and `content` to the normalized result format.
- Preserves Tavily `response_time` and `request_id` when present.

Evidence: [tools/web_search.py](../tools/web_search.py#L93-L147).

### Brave Search API

Request:

```text
GET https://api.search.brave.com/res/v1/web/search?q={query}
```

Authentication:

- `BRAVE_SEARCH_API_KEY` is read from environment and sent as `X-Subscription-Token`.

Query parameters:

```json
{
  "q": "search terms",
  "count": 5,
  "country": "US",
  "search_lang": "en",
  "ui_lang": "en-US"
}
```

Response handling:

- Reads `web.results[]`.
- Maps `title`, `url`, and `description` or `extra_snippets` to the normalized result format.
- Preserves Brave `query` context when present.

Evidence: [tools/web_search.py](../tools/web_search.py#L150-L204).

## Error Responses and Authentication Failures

Model request failures are converted to sanitized messages in `_model_error_message()`:

- HTTP 401 -> authentication error.
- HTTP 429 -> rate-limit error.
- Other HTTP status -> status-specific error.
- Unknown exception -> class-name-only message.

Evidence: [agent.py](../agent.py#L631-L646).
