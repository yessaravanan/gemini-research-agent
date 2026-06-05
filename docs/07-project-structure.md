# Project Structure

## Complete Folder Tree

This tree excludes `.venv/` and `__pycache__/` internals.

```text
.
├── .env
├── .env.example
├── .gitignore
├── README.md
├── agent.py
├── docs/
│   ├── 01-project-overview.md
│   ├── 02-system-architecture.md
│   ├── 03-agent-catalog.md
│   ├── 04-workflows.md
│   ├── 05-data-model.md
│   ├── 06-api-reference.md
│   ├── 07-project-structure.md
│   ├── 08-agent-creation-flow.md
│   ├── 09-improvement-opportunities.md
│   └── README.md
├── main.py
├── memory.json
├── report.md
├── requirements.txt
└── tools/
    ├── __init__.py
    ├── file_tools.py
    └── web_search.py
```

## Directory Purposes

| Directory | Purpose |
| --- | --- |
| `.` | Application root; contains CLI entrypoint, agent runtime, config templates, dependency list, and generated output files. |
| `tools/` | Local Python tools exposed to the agent and/or model function calling. |
| `docs/` | Generated project documentation. |
| `.venv/` | Local virtual environment; ignored and not part of source architecture. |
| `__pycache__/` | Python bytecode cache; ignored and not part of source architecture. |

## File Purposes

| File | Purpose | Evidence |
| --- | --- | --- |
| `main.py` | CLI entrypoint that prompts for a goal and runs the agent | [main.py](../main.py#L6-L23) |
| `agent.py` | Core orchestration: provider config, planning, tool calling, memory, report, retries | [agent.py](../agent.py#L1-L9), [agent.py](../agent.py#L138-L239) |
| `tools/__init__.py` | Re-exports tool functions for `agent.py` imports | [tools/__init__.py](../tools/__init__.py#L1-L6) |
| `tools/file_tools.py` | Workspace-safe local file operations | [tools/file_tools.py](../tools/file_tools.py#L11-L48) |
| `tools/web_search.py` | Tavily/Brave Search API implementation with normalized result output | [tools/web_search.py](../tools/web_search.py#L29-L58), [tools/web_search.py](../tools/web_search.py#L93-L204) |
| `requirements.txt` | Python package dependencies | [requirements.txt](../requirements.txt#L1-L2) |
| `.env.example` | Example Gemini and retry environment variables | [.env.example](../.env.example#L1-L6) |
| `.env` | Local secrets/config file; loaded but ignored by git | [agent.py](../agent.py#L27-L31), [.gitignore](../.gitignore#L1) |
| `.gitignore` | Ignores secrets, virtualenv, cache, and runtime artifacts | [.gitignore](../.gitignore#L1-L5) |
| `README.md` | User-facing setup and run instructions | [README.md](../README.md#L1-L56) |
| `memory.json` | Generated runtime memory artifact; ignored by git | [agent.py](../agent.py#L576-L581), [.gitignore](../.gitignore#L5) |
| `report.md` | Generated final report artifact; ignored by git | [agent.py](../agent.py#L520-L568), [.gitignore](../.gitignore#L6) |

## Source vs Generated Files

Source/config files:

- `main.py`
- `agent.py`
- `tools/*.py`
- `requirements.txt`
- `.env.example`
- `.gitignore`
- `README.md`

Generated/local files:

- `.env`
- `.venv/`
- `__pycache__/`
- `memory.json`
- `report.md`

Evidence: ignored files are listed in [.gitignore](../.gitignore#L1-L6).

## Tests

No `tests/` directory or test files are present.

## Build and Packaging

No Python package metadata (`pyproject.toml`, `setup.py`, `setup.cfg`) or build script exists. The documented run path is direct script execution with `python3 main.py` ([README.md](../README.md#L52-L56)).
