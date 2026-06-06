# Project Overview

## Project Name

Gemini Agentic AI Project.

Evidence: the current README names the project "Gemini Agentic AI Project" and describes it as a command-line agent using Google's native GenAI SDK with Gemini ([README.md](../README.md#L1-L3)).

## Purpose

This project is a local command-line research and writing agent. It asks a user for a goal, asks Gemini to create a plan, performs a web search, executes each plan step with model calls and optional tool calls, stores latest-run progress in `runs/latest/memory.json`, writes the latest Markdown report to `runs/latest/report.md`, and archives every run under `runs/<run_id>/` with an append-only `runs/goal_history.jsonl` index. Files created through the model-visible `write_file` tool are scoped to the matching `runs/<run_id>/artifacts/` directory.

Evidence:

- The CLI asks for a goal and runs `Agent.run(goal)` ([main.py](../gemini_research_agent/main.py#L6-L14)).
- The module docstring lists planning, web search, tool calling, memory, and report generation as the agent responsibilities ([agent.py](../gemini_research_agent/agent.py#L1-L9)).
- The report formatter writes sections for goal, providers, plan, reasoning steps, rate-limit failures, step results, and final answer ([agent.py](../gemini_research_agent/agent.py#L520-L568)).

## Business Problem Solved

The system automates lightweight research/report generation from a user-provided goal. The business framing is inferred from the implemented behavior: it reduces manual effort for planning, gathering search results, summarizing findings, and producing a reusable Markdown report. There is no product requirements document or business domain file in the repository, so no narrower business domain can be stated with code evidence.

## Major Capabilities

- CLI goal capture: `main()` reads a goal from standard input and exits early if empty ([main.py](../gemini_research_agent/main.py#L6-L11)).
- Gemini provider setup from environment variables ([agent.py](../gemini_research_agent/agent.py#L177-L192)).
- Step-by-step plan generation with a JSON-shaped model instruction ([agent.py](../gemini_research_agent/agent.py#L241-L269)).
- Deterministic web search before step execution ([agent.py](../gemini_research_agent/agent.py#L209-L215)).
- Tool-calling loop for model-requested tools ([agent.py](../gemini_research_agent/agent.py#L347-L424)).
- Local file tools: `read_file`, `write_file`, and `list_files`; model-requested writes are routed into per-run artifacts by the agent ([tools/file_tools.py](../gemini_research_agent/tools/file_tools.py#L19-L48), [agent.py](../gemini_research_agent/agent.py)).
- Web search tool using Tavily first and Brave Search API as fallback ([tools/web_search.py](../gemini_research_agent/tools/web_search.py#L29-L58), [tools/web_search.py](../gemini_research_agent/tools/web_search.py#L93-L204)).
- Progress persistence to latest-run JSON and per-run archive JSON after meaningful actions ([agent.py](../gemini_research_agent/agent.py)).
- Markdown report generation from finalized memory and direct save to latest `runs/latest/report.md` plus archived `runs/<run_id>/report.md` ([agent.py](../gemini_research_agent/agent.py)).
- Per-run file artifacts for model-created files under `runs/<run_id>/artifacts/` ([agent.py](../gemini_research_agent/agent.py)).
- Append-only goal tracking through `runs/goal_history.jsonl` start/completion events ([agent.py](../gemini_research_agent/agent.py)).
- HTTP 429 retry handling with exponential backoff and optional `Retry-After` support ([agent.py](../gemini_research_agent/agent.py#L426-L470), [agent.py](../gemini_research_agent/agent.py#L617-L629)).

## Technology Stack

- Language: Python. The code uses modern type syntax such as `int | None`, which requires Python 3.10 or newer ([agent.py](../gemini_research_agent/agent.py#L648-L660)).
- CLI runtime: standard input/output through `main.py` ([main.py](../gemini_research_agent/main.py#L6-L19)).
- LLM SDK: Google GenAI Python SDK via `google-genai>=1.0.0` ([requirements.txt](../requirements.txt#L1)).
- Environment loading: `python-dotenv>=1.0.0` ([requirements.txt](../requirements.txt#L2)).
- HTTP requests for search: Python standard library `urllib.request` ([tools/web_search.py](../gemini_research_agent/tools/web_search.py#L14-L16), [tools/web_search.py](../gemini_research_agent/tools/web_search.py#L207-L210)).
- Data storage: local latest-run JSON/Markdown files, append-only JSONL goal history, and timestamped per-run archive directories ([agent.py](../gemini_research_agent/agent.py)).

## External Integrations

| Integration | Purpose | Evidence |
| --- | --- | --- |
| Gemini API | Content generation and native function-calling responses | `genai.Client(api_key=gemini_key)` and `client.models.generate_content(...)` ([agent.py](../gemini_research_agent/agent.py), [agent.py](../gemini_research_agent/agent.py)) |
| Tavily Search API | Primary API-backed web search source | `_search_tavily()` ([tools/web_search.py](../gemini_research_agent/tools/web_search.py#L93-L147)) |
| Brave Search API | Secondary API-backed web search source | `_search_brave()` ([tools/web_search.py](../gemini_research_agent/tools/web_search.py#L150-L204)) |
| Local filesystem | Reads/writes workspace files and generated artifacts | File tools ([tools/file_tools.py](../gemini_research_agent/tools/file_tools.py#L11-L48)) |

## Configuration Files

- `.env.example`: documents required and optional environment variables.
- `.env`: local secrets file loaded at runtime but intentionally ignored by git ([.gitignore](../.gitignore#L1)).
- `.gitignore`: ignores `.env`, `.venv/`, Python cache files, latest runtime outputs, goal history, and run archives ([.gitignore](../.gitignore)).
- `requirements.txt`: Python runtime dependencies.

## Environment Variables

| Variable | Required | Purpose | Evidence |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | Yes | Gemini API authentication | Read with `os.getenv()` ([agent.py](../gemini_research_agent/agent.py#L177-L190)) |
| `GEMINI_MODEL` | Yes | Gemini model ID passed to chat completions | Read with `os.getenv()` ([agent.py](../gemini_research_agent/agent.py#L177-L190)) |
| `MODEL_MAX_RETRIES` | No | Number of retries for HTTP 429 failures; defaults to `2` | [agent.py](../gemini_research_agent/agent.py#L426-L429) |
| `MODEL_RETRY_BASE_SECONDS` | No | Base delay for exponential backoff; defaults to `2.0` | [agent.py](../gemini_research_agent/agent.py#L426-L429) |
| `MODEL_RETRY_MAX_SECONDS` | No | Maximum retry delay; defaults to `8.0` | [agent.py](../gemini_research_agent/agent.py#L617-L629) |
| `MODEL_TIMEOUT_MS` | No | Gemini request timeout in milliseconds; defaults to `60000` | [agent.py](../gemini_research_agent/agent.py) |
| `TOOL_MAX_REMOTE_CALLS` | No | Maximum native tool-call turns per plan step; defaults to `4` | [agent.py](../gemini_research_agent/agent.py) |
| `GOAL_HISTORY_PATH` | No | Append-only JSONL goal history path; defaults to `runs/goal_history.jsonl` | [agent.py](../gemini_research_agent/agent.py) |
| `RUN_HISTORY_DIR` | No | Per-run archive root; defaults to `runs` | [agent.py](../gemini_research_agent/agent.py) |

## Dependencies

Runtime dependencies are limited to:

- `google-genai>=1.0.0`
- `python-dotenv>=1.0.0`

Evidence: [requirements.txt](../requirements.txt#L1-L2).

## Build Scripts

No build scripts, package metadata, Makefile, task runner configuration, or CI files are present in the current repository. Setup is documented as manual virtualenv and `pip install -r requirements.txt` commands ([README.md](../README.md#L25-L30)).

## Database Schemas

No database schema files, migrations, ORM models, or database client dependencies are present. The only persistent state is file-based JSON and Markdown.

## API Definitions

The project exposes native Gemini function declarations through `_build_model_tools()` ([agent.py](../gemini_research_agent/agent.py)). It does not expose an HTTP API server.

## Tests

No test files or test configuration are present in the repository inventory. This is a documentation finding, not a runtime assertion.
