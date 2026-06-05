# Workflows

## Workflow 1: User Runs Agent from CLI

```mermaid
sequenceDiagram
    participant User
    participant Main as main.py
    participant Agent
    participant Gemini
    participant Tools
    participant Memory as memory.json
    participant Report as report.md

    User->>Main: python3 main.py
    Main->>User: Prompt for goal
    User->>Main: Enter goal
    Main->>Agent: Agent()
    Agent->>Agent: Load .env and build Gemini provider
    Main->>Agent: run(goal)
    Agent->>Memory: Save initial goal and started_at
    Agent->>Gemini: Create plan
    Gemini-->>Agent: Plan content
    Agent->>Memory: Save plan
    Agent->>Tools: web_search(goal)
    Tools-->>Agent: Search result object
    Agent->>Memory: Save tool call
    loop Each plan step
        Agent->>Gemini: Execute current step
        alt Gemini requests tools
            Gemini-->>Agent: tool_calls
            Agent->>Tools: Execute tool
            Tools-->>Agent: Tool result
            Agent->>Gemini: Tool result message
        else Gemini returns content
            Gemini-->>Agent: Step result
        end
        Agent->>Memory: Save step result
    end
    Agent->>Gemini: Create final answer
    Gemini-->>Agent: Final answer
    Agent->>Report: Write report.md from finalized memory
    Agent->>Memory: Save completed state
    Agent-->>Main: final_answer
    Main-->>User: Print final answer and file locations
```

Evidence:

- CLI prompt and agent call: [main.py](../main.py#L6-L19)
- Provider construction: [agent.py](../agent.py#L177-L192)
- Main run sequence: [agent.py](../agent.py#L194-L239)
- Tool loop: [agent.py](../agent.py#L347-L424)

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

- `.env` loading: [agent.py](../agent.py#L27-L31)
- Required provider variables and client construction: [agent.py](../agent.py#L177-L190)
- Missing configuration error: [agent.py](../agent.py#L160-L165)
- Tool registry: [agent.py](../agent.py#L170-L175)

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

Evidence: [agent.py](../agent.py#L241-L269), [agent.py](../agent.py#L495-L518).

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
        Agent->>Tool: _execute_tool(name, arguments)
        Agent->>Memory: Append tool call result
        Agent->>Gemini: Native function_response part
        Gemini-->>Agent: Final text response
    else Gemini returns text directly
        Gemini-->>Agent: Text response
    end
```

Evidence:

- Gemini function declarations and tool execution: [agent.py](../agent.py)
- Tool execution and memory record: [agent.py](../agent.py)

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

Evidence: [tools/web_search.py](../tools/web_search.py#L29-L58), [tools/web_search.py](../tools/web_search.py#L61-L90).

## Workflow 6: Memory and Report Persistence

```mermaid
flowchart LR
    A[Agent state changes] --> B[_save_memory]
    B --> C[(memory.json)]
    A --> D[_format_report_from_memory]
    D --> E[write_file tool]
    E --> F[(report.md)]
```

Evidence:

- Memory write: [agent.py](../agent.py#L576-L581)
- Report formatting: [agent.py](../agent.py#L520-L568)
- Final report save via `write_file`: [agent.py](../agent.py#L226-L237)

## Workflow 7: Rate Limit Handling

```mermaid
sequenceDiagram
    participant Agent
    participant Gemini
    participant Memory

    Agent->>Gemini: Chat completion
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

Evidence: [agent.py](../agent.py#L426-L470), [agent.py](../agent.py#L583-L629).
