# Gemini Agentic AI Project

This project is a Python command-line agent that uses Google's native GenAI SDK with Gemini.

## Features

- Reads `GEMINI_API_KEY` and `GEMINI_MODEL` from `.env` or the shell environment.
- Uses Gemini only.
- Asks the user for a goal.
- Creates a step-by-step plan.
- Searches the web using Tavily as primary and Brave Search API as fallback.
- Executes the plan with function calling and local tools.
- Saves latest progress to `runs/latest/memory.json`.
- Saves the latest final answer report to `runs/latest/report.md`.
- Tracks every run in `runs/goal_history.jsonl` and archives each run under `runs/`.
- Saves model-created file artifacts under the matching `runs/<run_id>/artifacts/` folder.

## Tools

- `read_file`: reads a UTF-8 text file from the workspace.
- `write_file`: writes a UTF-8 text file under the current run's `artifacts/` folder.
- `list_files`: lists files in the workspace.
- `web_search`: searches Tavily first, then Brave Search API if Tavily fails or returns no results.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` and set your Gemini API key and model:

```bash
GEMINI_API_KEY="your_gemini_api_key"
GEMINI_MODEL="gemini-flash-lite-latest"

SEARCH_PRIMARY="tavily"
SEARCH_SECONDARY="brave"
TAVILY_API_KEY="your_tavily_api_key"
BRAVE_SEARCH_API_KEY="your_brave_search_api_key"
SEARCH_MAX_RESULTS=5

MODEL_MAX_RETRIES=2
MODEL_RETRY_BASE_SECONDS=2
MODEL_RETRY_MAX_SECONDS=8
MODEL_TIMEOUT_MS=60000
TOOL_MAX_REMOTE_CALLS=4

GOAL_HISTORY_PATH="runs/goal_history.jsonl"
RUN_HISTORY_DIR="runs"
```

Do not put real API keys in source files, `README.md`, `.env.example`, or any
other committed file. The runtime reads keys only from environment variables
after loading the local `.env` file at the project root.

The agent creates a native Gemini client with `google.genai.Client(api_key=...)`.

The web search endpoints used by the agent are:

```text
Tavily: POST https://api.tavily.com/search
Brave:  GET  https://api.search.brave.com/res/v1/web/search
```

`SEARCH_PRIMARY` and `SEARCH_SECONDARY` can be set to `tavily` or `brave`.
The default recommendation is Tavily primary and Brave secondary.

The retry settings are optional. They control bounded retries when Gemini or an
upstream model provider returns HTTP `429` rate-limit responses.
`MODEL_TIMEOUT_MS` limits individual Gemini requests. `TOOL_MAX_REMOTE_CALLS`
limits native function-calling turns during one plan step.

`runs/latest/memory.json` and `runs/latest/report.md` always contain the latest
run. Every run is also archived under `RUN_HISTORY_DIR` using a timestamped
folder, and each start/end event is appended to `GOAL_HISTORY_PATH`. Files
created by the model with `write_file` are scoped to that run's `artifacts/`
directory so outputs from different goals do not mix in the project root.

## Run

```bash
python3 -m gemini_research_agent.main
```

Enter a goal when prompted. The agent will print its visible reasoning summaries,
show the plan, execute the plan, then write latest outputs under `runs/latest/`
and any tool-created artifacts under the archived run directory.
