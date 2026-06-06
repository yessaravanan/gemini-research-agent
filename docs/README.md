# Documentation Index

This directory contains architecture and system documentation generated from the current codebase.

## Documents

1. [Project Overview](01-project-overview.md)
   - Purpose, capabilities, technology stack, integrations, configuration, dependencies, and absent systems.

2. [System Architecture](02-system-architecture.md)
   - High-level architecture, components, data flow, service dependencies, and architectural decisions.

3. [Agent Catalog](03-agent-catalog.md)
   - Inventory and detailed documentation of the implemented `Agent`.

4. [Workflows](04-workflows.md)
   - End-to-end CLI, construction, planning, tool-calling, search, memory/report, and retry workflows.

5. [Data Model](05-data-model.md)
   - Latest-run files, `runs/goal_history.jsonl`, per-run archives, per-run artifacts, tool result schemas, and absence of databases/vector stores.

6. [API Reference](06-api-reference.md)
   - Internal Python APIs, tool APIs, Gemini API usage, and search integrations.

7. [Project Structure](07-project-structure.md)
   - Folder tree and purpose of major files/directories.

8. [Agent Creation Flow](08-agent-creation-flow.md)
   - Reverse-engineered current agent construction/execution flow and explicit notes on absent platform features.

9. [Improvement Opportunities](09-improvement-opportunities.md)
   - Technical debt, security risks, scalability concerns, documentation gaps, and suggested priorities.

## Evidence Policy

The documentation cites actual files and line ranges where behavior is implemented. When a requested system area is absent, the documents state that explicitly rather than inferring unsupported behavior.
