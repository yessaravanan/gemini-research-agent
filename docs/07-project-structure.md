# Project Structure

## Complete Folder Tree

This tree excludes `.venv/`, `.git/`, and `__pycache__/` internals.

```text
.
├── .env
├── .env.example
├── .gitignore
├── README.md
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
├── gemini_research_agent/
│   ├── __init__.py
│   ├── agent.py
│   ├── main.py
│   └── tools/
│       ├── __init__.py
│       ├── file_tools.py
│       └── web_search.py
├── requirements.txt
└── runs/
    ├── goal_history.jsonl
    ├── latest/
    │   ├── memory.json
    │   └── report.md
    └── <run_id>/
        ├── artifacts/
        ├── memory.json
        └── report.md
```

## Directory Purposes

| Directory | Purpose |
| --- | --- |
| `.` | Project root containing standard project config, docs, package source, dependencies, and generated run output. |
| `gemini_research_agent/` | Python package containing the CLI entrypoint and agent runtime. |
| `gemini_research_agent/tools/` | Local Python tools exposed to Gemini function calling and the agent runtime. |
| `docs/` | Project documentation. |
| `runs/` | Generated latest-run files, append-only goal history, timestamped run archives, and artifacts; ignored by git. |
| `.venv/` | Local virtual environment; ignored and not part of source architecture. |
| `__pycache__/` | Python bytecode cache; ignored and not part of source architecture. |

## File Purposes

| File | Purpose | Evidence |
| --- | --- | --- |
| `gemini_research_agent/main.py` | CLI entrypoint that prompts for a goal and runs the agent | [main.py](../gemini_research_agent/main.py#L6-L23) |
| `gemini_research_agent/agent.py` | Core orchestration: provider config, planning, tool calling, memory, report, retries | [agent.py](../gemini_research_agent/agent.py#L1-L9) |
| `gemini_research_agent/tools/__init__.py` | Re-exports tool functions for package imports | [tools/__init__.py](../gemini_research_agent/tools/__init__.py#L1-L6) |
| `gemini_research_agent/tools/file_tools.py` | Workspace-safe local file operations | [tools/file_tools.py](../gemini_research_agent/tools/file_tools.py#L11-L48) |
| `gemini_research_agent/tools/web_search.py` | Tavily/Brave Search API implementation with normalized result output | [tools/web_search.py](../gemini_research_agent/tools/web_search.py#L29-L58) |
| `requirements.txt` | Python package dependencies | [requirements.txt](../requirements.txt#L1-L2) |
| `.env.example` | Example Gemini, search, retry, and run-history environment variables | [.env.example](../.env.example#L1-L20) |
| `.env` | Local secrets/config file; loaded but ignored by git | [agent.py](../gemini_research_agent/agent.py#L27-L31), [.gitignore](../.gitignore#L1) |
| `.gitignore` | Ignores secrets, virtualenv, cache, and runtime artifacts | [.gitignore](../.gitignore#L1-L8) |
| `README.md` | User-facing setup and run instructions | [README.md](../README.md#L1-L90) |
| `runs/latest/memory.json` | Generated latest-run memory artifact; ignored by git | [agent.py](../gemini_research_agent/agent.py) |
| `runs/latest/report.md` | Generated latest-run report artifact; ignored by git | [agent.py](../gemini_research_agent/agent.py) |
| `runs/goal_history.jsonl` | Generated append-only goal history index; ignored by git | [agent.py](../gemini_research_agent/agent.py) |
| `runs/<run_id>/memory.json` | Archived per-run memory file; ignored by git | [agent.py](../gemini_research_agent/agent.py) |
| `runs/<run_id>/report.md` | Archived per-run report file; ignored by git | [agent.py](../gemini_research_agent/agent.py) |
| `runs/<run_id>/artifacts/` | Generated files created by model `write_file` calls for that run; ignored by git | [agent.py](../gemini_research_agent/agent.py) |

## Source vs Generated Files

Source/config files:

- `gemini_research_agent/*.py`
- `gemini_research_agent/tools/*.py`
- `requirements.txt`
- `.env.example`
- `.gitignore`
- `README.md`
- `docs/*.md`

Generated/local files:

- `.env`
- `.venv/`
- `__pycache__/`
- `runs/`

Evidence: ignored files are listed in [.gitignore](../.gitignore#L1-L8).

## Tests

No `tests/` directory or test files are present.

## Build and Packaging

No Python package metadata (`pyproject.toml`, `setup.py`, `setup.cfg`) or build script exists. The documented run path is module execution with `python3 -m gemini_research_agent.main` ([README.md](../README.md#L84-L88)).
