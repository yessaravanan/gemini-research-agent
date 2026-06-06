# Workflows

## Workflow 1: User Runs Agent from CLI

```mermaid
sequenceDiagram
    participant User
    participant Main as main.py
    participant Agent
    participant Gemini
    participant Tools
    participant Memory as runs/latest/memory.json
    participant Archive as runs/run_id
    participant Artifacts as runs/run_id/artifacts
    participant History as runs/goal_history.jsonl
    participant Report as runs/latest/report.md

    User->>Main: python3 -m gemini_research_agent.main
    Main->>User: Prompt for goal
    User->>Main: Enter goal
    Main->>Agent: Agent()
    Agent->>Agent: Load .env and build Gemini provider
    Main->>Agent: run(goal)
    Agent->>History: Append started event
    Agent->>Memory: Save initial goal and started_at
    Agent->>Archive: Save archived memory
    Agent->>Gemini: Create plan
    Gemini-->>Agent: Plan content
    Agent->>Memory: Save plan
    Agent->>Tools: web_search(goal)
    Tools-->>Agent: Search result object
    Agent->>Memory: Save tool call
    loop Each plan step
        Agent->>Gemini: Execute current step
        alt Gemini requests tools
            Gemini-->>Agent: native function calls
            opt Tool is write_file
                Agent->>Agent: Scope path to current run artifacts
            end
            Agent->>Tools: Execute tool
            opt Tool created file
                Tools->>Artifacts: Write artifact file
            end
            Tools-->>Agent: Tool result
            Agent->>Gemini: Tool result message
        else Gemini returns content
            Gemini-->>Agent: Step result
        end
        Agent->>Memory: Save step result
        Agent->>Archive: Save archived memory
    end
    Agent->>Gemini: Create final answer
    Gemini-->>Agent: Final answer
    Agent->>Report: Write report.md from finalized memory
    Agent->>Archive: Write archived report.md
    Agent->>Memory: Save completed state
    Agent->>Archive: Save completed memory.json
    Agent->>History: Append completed event
    Agent-->>Main: final_answer
    Main-->>User: Print final answer and file locations
```

Evidence:

- CLI prompt and agent call: [main.py](../gemini_research_agent/main.py#L6-L19)
- Provider construction: [agent.py](../gemini_research_agent/agent.py#L177-L192)
- Main run sequence: [agent.py](../gemini_research_agent/agent.py#L194-L239)
- Tool loop: [agent.py](../gemini_research_agent/agent.py#L347-L424)

## Workflow 2: Agent Construction

There is no separate "create agent" feature or UI. The current creation workflow is Python object construction through `Agent()`.

```mermaid
sequenceDiagram
    participant Caller
    participant Agent
    participant Dotenv as python-dotenv
    participant Env as .env/environment
    participant SDK as Google GenAI SDK

    Caller->>Agent: Agent(memory_path="memory.json", report_path="report.md")
    Agent->>Dotenv: load_dotenv(PROJECT_ROOT / ".env")
    Dotenv->>Env: Load variables if present
    Agent->>Env: getenv("GEMINI_API_KEY")
    Agent->>Env: getenv("GEMINI_MODEL")
    alt Both values present
        Agent->>SDK: genai.Client(api_key=key)
        Agent->>Agent: Register tools and initialize memory
    else Missing value
        Agent-->>Caller: RuntimeError
    end
```

Evidence:

- `.env` loading: [agent.py](../gemini_research_agent/agent.py#L27-L31)
- Required provider variables and client construction: [agent.py](../gemini_research_agent/agent.py#L177-L190)
- Missing configuration error: [agent.py](../gemini_research_agent/agent.py#L160-L165)
- Tool registry: [agent.py](../gemini_research_agent/agent.py#L170-L175)

## Workflow 3: Plan Creation

```mermaid
sequenceDiagram
    participant Agent
    participant Gemini
    participant Memory

    Agent->>Gemini: System prompt requests JSON {"steps": [...]}
    Gemini-->>Agent: Plan response
    alt Response starts with "Model request failed:"
        Agent->>Agent: Use fallback four-step plan
    else Response is valid JSON with steps
        Agent->>Agent: Parse JSON steps
    else Response is non-JSON text
        Agent->>Agent: Split non-empty lines, first six
    end
    Agent->>Memory: Save plan
```

Evidence: [agent.py](../gemini_research_agent/agent.py#L241-L269), [agent.py](../gemini_research_agent/agent.py#L495-L518).

## Workflow 4: Tool Calling

```mermaid
sequenceDiagram
    participant Agent
    participant Gemini
    participant Tool as Local Tool Function
    participant Memory

    Agent->>Gemini: generate_content with function declarations
    alt Gemini requests a tool
        Gemini-->>Agent: Function call with signed model content
        opt Tool is write_file
            Agent->>Agent: Rewrite path under runs/run_id/artifacts
        end
        Agent->>Tool: _execute_tool(name, arguments)
        Agent->>Memory: Append tool call result
        Agent->>Gemini: Native function_response part
        Gemini-->>Agent: Final text response
    else Gemini returns text directly
        Gemini-->>Agent: Text response
    end
```

Evidence:

- Gemini function declarations and tool execution: [agent.py](../gemini_research_agent/agent.py)
- Tool execution and memory record: [agent.py](../gemini_research_agent/agent.py)

## Workflow 5: Web Search

```mermaid
flowchart TD
    A[web_search(query, max_results)] --> B[Clamp max_results 1..10]
    B --> C[Read SEARCH_PRIMARY and SEARCH_SECONDARY]
    C --> D[Call primary provider API]
    D --> E{Results returned?}
    E -- yes --> F[Return normalized primary results]
    E -- no --> G[Call secondary provider API]
    G --> H{Results returned?}
    H -- yes --> I[Return normalized secondary results]
    H -- no --> J[Return combined provider error object]
```

Evidence: [tools/web_search.py](../gemini_research_agent/tools/web_search.py#L29-L58), [tools/web_search.py](../gemini_research_agent/tools/web_search.py#L61-L90).

## Workflow 6: Memory and Report Persistence

```mermaid
flowchart LR
    A[Agent state changes] --> B[_save_memory]
    B --> C[(runs/latest/memory.json)]
    B --> G[(runs/run_id/memory.json)]
    A --> T[write_file tool execution]
    T --> K[(runs/run_id/artifacts)]
    A --> D[_format_report_from_memory]
    D --> E[Path.write_text]
    E --> F[(runs/latest/report.md)]
    E --> H[(runs/run_id/report.md)]
    A --> I[_append_goal_history_event]
    I --> J[(runs/goal_history.jsonl)]
```

Evidence:

- Memory write and archive write: [agent.py](../gemini_research_agent/agent.py)
- Artifact writes through scoped `write_file` tool execution: [agent.py](../gemini_research_agent/agent.py), [tools/file_tools.py](../gemini_research_agent/tools/file_tools.py)
- Report formatting: [agent.py](../gemini_research_agent/agent.py#L520-L568)
- Final report save and goal history events: [agent.py](../gemini_research_agent/agent.py)

## Workflow 7: Rate Limit Handling

```mermaid
sequenceDiagram
    participant Agent
    participant Gemini
    participant Memory

    Agent->>Gemini: generate_content
    alt Success
        Gemini-->>Agent: Response
    else HTTP 429
        Agent->>Memory: Record sanitized rate_limit_failure
        alt Retries remain
            Agent->>Agent: Sleep using Retry-After or exponential backoff
            Agent->>Gemini: Retry request
        else No retries remain
            Agent-->>Agent: Raise to caller
        end
    else Other error
        Agent-->>Agent: Raise to caller
    end
```

Evidence: [agent.py](../gemini_research_agent/agent.py#L426-L470), [agent.py](../gemini_research_agent/agent.py#L583-L629).
