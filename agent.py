"""Agent orchestration for a Gemini-backed Python AI project.

The agent:
1. Reads a user goal.
2. Creates a step-by-step plan with a configured model provider.
3. Searches the web with a local tool.
4. Executes plan steps with native Gemini function calling.
5. Saves progress to memory.json and the final answer to report.md.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from tools import list_files, read_file, web_search, write_file


PROJECT_ROOT = Path(__file__).resolve().parent

# Load local development secrets from the project .env file. Real environment
# variables still win, because python-dotenv does not override them by default.
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class ModelProvider:
    """Gemini model provider configuration."""

    name: str
    model: str
    client: genai.Client


class Agent:
    """Small agent that plans, uses tools, and writes durable output files."""

    def __init__(
        self,
        memory_path: str = "memory.json",
        report_path: str = "report.md",
    ) -> None:
        self.memory_path = Path(memory_path)
        self.report_path = Path(report_path)
        self.memory: dict[str, Any] = {
            "goal": "",
            "started_at": "",
            "completed_at": "",
            "providers": [],
            "plan": [],
            "reasoning_steps": [],
            "rate_limit_failures": [],
            "tool_call_failures": [],
            "tool_calls": [],
            "step_results": [],
            "final_answer": "",
        }
        self.provider = self._build_provider()
        if self.provider is None:
            raise RuntimeError(
                "Gemini is not configured. Set GEMINI_API_KEY and GEMINI_MODEL "
                "in .env."
            )

        self.memory["providers"] = [
            {"name": self.provider.name, "model": self.provider.model}
        ]
        self.available_tools = {
            "read_file": read_file,
            "write_file": write_file,
            "list_files": list_files,
            "web_search": web_search,
        }
        self.model_tools = self._build_model_tools()

    def _build_provider(self) -> ModelProvider | None:
        """Build the Gemini provider from environment."""
        gemini_key = os.getenv("GEMINI_API_KEY")
        gemini_model = (os.getenv("GEMINI_MODEL") or "").strip()
        if gemini_key and gemini_model:
            return ModelProvider(
                name="gemini",
                model=gemini_model,
                client=genai.Client(
                    api_key=gemini_key,
                    http_options=types.HttpOptions(
                        timeout=self._env_int("MODEL_TIMEOUT_MS", 60000)
                    ),
                ),
            )

        return None

    def _build_model_tools(self) -> list[types.Tool]:
        """Create Gemini-native function declarations for local tools."""
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="read_file",
                        description=(
                            "Read a UTF-8 text file from the project workspace."
                        ),
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Relative path to the file to read.",
                                )
                            },
                            required=["path"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="write_file",
                        description=(
                            "Write UTF-8 text to a file inside the project workspace."
                        ),
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Relative path to the file to write.",
                                ),
                                "content": types.Schema(
                                    type=types.Type.STRING,
                                    description="Text content to save.",
                                ),
                            },
                            required=["path", "content"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="list_files",
                        description="List files in the project workspace.",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "path": types.Schema(
                                    type=types.Type.STRING,
                                    description="Relative directory path to list.",
                                    default=".",
                                ),
                                "recursive": types.Schema(
                                    type=types.Type.BOOLEAN,
                                    description=(
                                        "Whether to list files recursively."
                                    ),
                                    default=False,
                                ),
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="web_search",
                        description=(
                            "Search the public web and return concise search results."
                        ),
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "query": types.Schema(
                                    type=types.Type.STRING,
                                    description=(
                                        "Search query to send to the web search "
                                        "provider."
                                    ),
                                ),
                                "max_results": types.Schema(
                                    type=types.Type.INTEGER,
                                    description=(
                                        "Maximum number of search results to return."
                                    ),
                                    default=5,
                                    minimum=1,
                                    maximum=10,
                                ),
                            },
                            required=["query"],
                        ),
                    ),
                ]
            )
        ]

    def run(self, goal: str) -> str:
        """Run the full agent workflow for a user goal."""
        self.memory["goal"] = goal
        self.memory["started_at"] = self._now()
        self._remember_reasoning("Captured the user goal and started planning.")
        self._save_memory()

        plan = self.create_plan(goal)
        self.memory["plan"] = plan
        self._save_memory()

        print("\nPlan:")
        for index, step in enumerate(plan, start=1):
            print(f"{index}. {step}")

        # Make web search deterministic so the project always satisfies the
        # search requirement, even if the model chooses not to call the tool.
        self._remember_reasoning("Searching the web for background information.")
        search_results = self._execute_tool(
            "web_search",
            {"query": goal, "max_results": self._env_int("SEARCH_MAX_RESULTS", 5)},
        )
        self._save_memory()

        step_results: list[str] = []
        for index, step in enumerate(plan, start=1):
            print(f"\nExecuting step {index}: {step}")
            self._remember_reasoning(f"Executing plan step {index}: {step}")
            result = self.execute_step(goal, plan, step, search_results)
            step_results.append(result)
            self.memory["step_results"] = step_results
            self._save_memory()

        final_answer = self.create_final_answer(goal, plan, search_results, step_results)
        self.memory["final_answer"] = final_answer
        self.memory["completed_at"] = self._now()
        self._save_memory()

        # Render the report after the final memory save so report.md reflects
        # the completed memory state for this run.
        report_markdown = self._format_report_from_memory()
        self.report_path.write_text(report_markdown, encoding="utf-8")

        return final_answer

    def create_plan(self, goal: str) -> list[str]:
        """Ask the model for a concise JSON plan."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You create practical plans for research and writing tasks. "
                    "Return JSON only, with this shape: "
                    '{"steps": ["first step", "second step"]}. '
                    "Use 3 to 6 specific steps."
                ),
            },
            {"role": "user", "content": f"Goal: {goal}"},
        ]
        content = self._chat(messages)
        if content.startswith("Model request failed:"):
            self._remember_reasoning(
                "Using a fallback plan because the planning model request failed."
            )
            return [
                "Search the web for relevant information.",
                "Extract the most useful findings.",
                "Summarize the answer clearly.",
                "Write the final report.",
            ]

        steps = self._parse_plan(content)
        self._remember_reasoning("Created a step-by-step plan for the goal.")
        return steps

    def execute_step(
        self,
        goal: str,
        plan: list[str],
        step: str,
        search_results: Any,
    ) -> str:
        """Execute a single plan step using model responses and tool calls."""
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are an agent executing one step of a plan. "
                    "Use function tools when they help. "
                    "Show concise, user-visible reasoning steps, but do not reveal "
                    "hidden chain-of-thought. "
                    "Return a short step result with any useful findings."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Goal:\n{goal}\n\n"
                    f"Full plan:\n{json.dumps(plan, indent=2)}\n\n"
                    f"Current step:\n{step}\n\n"
                    f"Existing web search results:\n"
                    f"{json.dumps(search_results, indent=2)}"
                ),
            },
        ]
        return self._chat_with_tools(messages)

    def create_final_answer(
        self,
        goal: str,
        plan: list[str],
        search_results: Any,
        step_results: list[str],
    ) -> str:
        """Summarize the completed work into a final answer."""
        messages = [
            {
                "role": "system",
                "content": (
                    "Write a clear final answer in markdown. Include a brief "
                    "reasoning summary, key findings, and useful source links when "
                    "search results include URLs. Do not reveal hidden chain-of-thought."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Goal:\n{goal}\n\n"
                    f"Plan:\n{json.dumps(plan, indent=2)}\n\n"
                    f"Web search results:\n{json.dumps(search_results, indent=2)}\n\n"
                    f"Step results:\n{json.dumps(step_results, indent=2)}"
                ),
            },
        ]
        self._remember_reasoning("Synthesizing findings into the final answer.")
        return self._chat(messages)

    def _chat(self, messages: list[dict[str, Any]]) -> str:
        """Call Gemini through the native Google GenAI SDK."""
        system_instruction, contents = self._messages_to_gemini(messages)
        config = types.GenerateContentConfig(
            temperature=0.2,
            system_instruction=system_instruction or None,
        )
        try:
            response = self._request_completion(
                contents=contents,
                config=config,
            )
        except Exception as exc:
            error_message = self._model_error_message(exc)
            self._remember_reasoning(error_message)
            return f"Model request failed: {error_message}"

        return self._response_text(response)

    def _chat_with_tools(self, messages: list[dict[str, Any]]) -> str:
        """Run a bounded native Gemini function-calling loop."""
        system_instruction, contents = self._messages_to_gemini(messages)
        config = types.GenerateContentConfig(
            temperature=0.2,
            system_instruction=system_instruction or None,
            tools=self.model_tools,
        )
        max_tool_turns = max(1, self._env_int("TOOL_MAX_REMOTE_CALLS", 4))
        tool_call_start = len(self.memory["tool_calls"])

        for _ in range(max_tool_turns):
            try:
                response = self._request_completion(
                    contents=contents,
                    config=config,
                )
            except Exception as exc:
                error_message = self._model_error_message(exc)
                if self._status_code(exc) == 429:
                    self._remember_reasoning(error_message)
                    return f"Model request failed: {error_message}"

                self._record_tool_call_failure(error_message)
                fallback_messages = [
                    *messages,
                    {
                        "role": "user",
                        "content": (
                            "The tool-calling request failed with this error:\n"
                            f"{error_message}\n\n"
                            "Continue the current step using the information already "
                            "available in the conversation."
                        ),
                    },
                ]
                return self._chat(fallback_messages)

            function_calls = self._function_calls(response)
            if not function_calls:
                return self._response_text(response)

            model_content = self._response_content(response)
            if model_content is not None:
                contents.append(model_content)

            function_response_parts = []
            for function_call in function_calls:
                name = str(function_call.name or "")
                arguments = dict(function_call.args or {})
                result = self._execute_tool(name, arguments)
                function_response_parts.append(
                    types.Part.from_function_response(
                        name=name,
                        response={"result": result},
                    )
                )

            contents.append(
                types.Content(role="user", parts=function_response_parts)
            )
            self._save_memory()

        tool_results = self.memory["tool_calls"][tool_call_start:]
        self._remember_reasoning(
            "Tool loop reached the configured limit; synthesizing from the "
            "collected tool results."
        )
        fallback_messages = [
            *messages,
            {
                "role": "user",
                "content": (
                    "The function-calling loop reached its configured limit. "
                    "Use these collected tool results to return the current "
                    "step result:\n"
                    f"{json.dumps(tool_results, indent=2)}"
                ),
            },
        ]
        return self._chat(fallback_messages)

    def _request_completion(self, **kwargs: Any) -> Any:
        """Call Gemini and retry bounded HTTP 429 failures."""
        max_retries = self._env_int("MODEL_MAX_RETRIES", default=2)
        base_delay = self._env_float("MODEL_RETRY_BASE_SECONDS", default=2.0)

        return self._request_completion_with_provider(
            provider=self.provider,
            max_retries=max_retries,
            base_delay=base_delay,
            **kwargs,
        )

    def _request_completion_with_provider(
        self,
        provider: ModelProvider,
        max_retries: int,
        base_delay: float,
        **kwargs: Any,
    ) -> Any:
        """Call one provider and retry its HTTP 429 rate-limit failures."""
        for attempt in range(max_retries + 1):
            try:
                return provider.client.models.generate_content(
                    model=provider.model,
                    **kwargs,
                )
            except Exception as exc:
                if self._status_code(exc) != 429:
                    raise

                will_retry = attempt < max_retries
                delay = (
                    self._retry_delay_seconds(exc, base_delay, attempt)
                    if will_retry
                    else 0.0
                )
                self._record_rate_limit_failure(
                    provider=provider,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    retry_in_seconds=delay,
                    will_retry=will_retry,
                )
                if not will_retry:
                    raise

                time.sleep(delay)

        raise RuntimeError("Provider retry loop ended unexpectedly.")

    def _messages_to_gemini(
        self,
        messages: list[dict[str, Any]],
    ) -> tuple[str, list[types.Content]]:
        """Convert simple chat-style messages to Gemini content objects."""
        system_parts: list[str] = []
        contents: list[types.Content] = []

        for message in messages:
            role = message.get("role", "user")
            content = str(message.get("content") or "")
            if role == "system":
                if content:
                    system_parts.append(content)
                continue

            gemini_role = "model" if role == "assistant" else "user"
            contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part(text=content)],
                )
            )

        if not contents:
            contents.append(
                types.Content(role="user", parts=[types.Part(text="")])
            )

        return "\n\n".join(system_parts), contents

    @staticmethod
    def _response_text(response: Any) -> str:
        """Extract text from a Google GenAI response."""
        text = getattr(response, "text", None)
        if text:
            return text

        chunks: list[str] = []
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                part_text = getattr(part, "text", None)
                if part_text:
                    chunks.append(part_text)

        return "\n".join(chunks)

    @staticmethod
    def _function_calls(response: Any) -> list[Any]:
        """Extract native Gemini function calls from a response."""
        function_calls = getattr(response, "function_calls", None)
        if function_calls:
            return list(function_calls)

        calls = []
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                function_call = getattr(part, "function_call", None)
                if function_call is not None:
                    calls.append(function_call)

        return calls

    @staticmethod
    def _response_content(response: Any) -> types.Content | None:
        """Return the first model content object, preserving thought signatures."""
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return None
        return getattr(candidates[0], "content", None)

    def _execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute a registered Python tool and record the result in memory."""
        tool = self.available_tools.get(name)
        if tool is None:
            result: Any = {"error": f"Unknown tool: {name}"}
        else:
            try:
                result = tool(**arguments)
            except Exception as exc:  # Keep the agent alive on tool errors.
                result = {"error": str(exc)}

        self.memory["tool_calls"].append(
            {
                "tool": name,
                "arguments": arguments,
                "result": result,
                "timestamp": self._now(),
            }
        )
        return result

    def _parse_plan(self, content: str) -> list[str]:
        """Parse the model's JSON plan, with a fallback for plain text."""
        try:
            data = json.loads(content)
            steps = data.get("steps", [])
            if isinstance(steps, list) and all(isinstance(step, str) for step in steps):
                return [step.strip() for step in steps if step.strip()]
        except json.JSONDecodeError:
            pass

        fallback_steps = [
            line.lstrip("-0123456789. ").strip()
            for line in content.splitlines()
            if line.strip()
        ]
        if fallback_steps:
            return fallback_steps[:6]

        return [
            "Clarify the question and scope.",
            "Search the web for relevant information.",
            "Summarize the findings.",
            "Write the final answer.",
        ]

    def _format_report_from_memory(self) -> str:
        """Build report.md content from the finalized memory state."""
        goal = self.memory["goal"]
        plan = self.memory["plan"]
        step_results = self.memory["step_results"]
        final_answer = self.memory["final_answer"]
        plan_markdown = "\n".join(
            f"{index}. {step}" for index, step in enumerate(plan, start=1)
        )
        step_markdown = "\n\n".join(
            f"## Step {index}\n\n{result}"
            for index, result in enumerate(step_results, start=1)
        )
        reasoning_markdown = "\n".join(
            f"- {entry['timestamp']}: {entry['note']}"
            for entry in self.memory["reasoning_steps"]
        )
        provider_markdown = "\n".join(
            f"- {provider['name']}: {provider['model']}"
            for provider in self.memory["providers"]
        )
        rate_limit_failures = self.memory["rate_limit_failures"]
        rate_limit_lines = []
        for failure in rate_limit_failures:
            action = "no retries left"
            if failure.get("will_retry"):
                action = f"retrying after {failure['retry_in_seconds']:.1f}s"

            rate_limit_lines.append(
                f"- {failure['timestamp']}: {failure['provider']} model "
                f"`{failure['model']}` hit HTTP 429 on attempt "
                f"{failure['attempt']} of {failure['max_retries'] + 1}; {action}"
            )

        rate_limit_markdown = "\n".join(rate_limit_lines)
        if not rate_limit_markdown:
            rate_limit_markdown = "None"

        tool_call_failures = self.memory.get("tool_call_failures", [])
        tool_call_failure_lines = []
        for failure in tool_call_failures:
            tool_call_failure_lines.append(
                f"- {failure['timestamp']}: {failure['provider']} model "
                f"`{failure['model']}` tool-calling failed; fallback: "
                f"{failure['fallback']}; error: {failure['error']}"
            )

        tool_call_failure_markdown = "\n".join(tool_call_failure_lines)
        if not tool_call_failure_markdown:
            tool_call_failure_markdown = "None"

        return (
            f"# Agent Report\n\n"
            f"## Goal\n\n{goal}\n\n"
            f"## Providers\n\n{provider_markdown}\n\n"
            f"## Plan\n\n{plan_markdown}\n\n"
            f"## Reasoning Steps\n\n{reasoning_markdown}\n\n"
            f"## Rate Limit Failures\n\n{rate_limit_markdown}\n\n"
            f"## Tool-Calling Failures\n\n{tool_call_failure_markdown}\n\n"
            f"## Step Results\n\n{step_markdown}\n\n"
            f"## Final Answer\n\n{final_answer}\n"
        )

    def _remember_reasoning(self, note: str) -> None:
        """Store and display concise progress reasoning."""
        entry = {"timestamp": self._now(), "note": note}
        self.memory["reasoning_steps"].append(entry)
        print(f"[reasoning] {note}")

    def _save_memory(self) -> None:
        """Persist progress after each meaningful action."""
        self.memory_path.write_text(
            json.dumps(self.memory, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _record_rate_limit_failure(
        self,
        provider: ModelProvider,
        attempt: int,
        max_retries: int,
        retry_in_seconds: float,
        will_retry: bool,
    ) -> None:
        """Persist a sanitized rate-limit retry record."""
        if will_retry:
            note = (
                f"{provider.name} returned HTTP 429 rate limit "
                f"(retry {attempt}/{max_retries} in {retry_in_seconds:.1f}s)."
            )
        else:
            note = (
                f"{provider.name} returned HTTP 429 rate limit "
                "with no retries left."
            )

        self.memory["rate_limit_failures"].append(
            {
                "timestamp": self._now(),
                "provider": provider.name,
                "model": provider.model,
                "attempt": attempt,
                "max_retries": max_retries,
                "retry_in_seconds": retry_in_seconds,
                "will_retry": will_retry,
            }
        )
        self._remember_reasoning(note)
        self._save_memory()

    def _record_tool_call_failure(self, error_message: str) -> None:
        """Persist a sanitized tool-calling failure before fallback."""
        self.memory["tool_call_failures"].append(
            {
                "timestamp": self._now(),
                "provider": self.provider.name,
                "model": self.provider.model,
                "error": error_message,
                "fallback": "text-only model response",
            }
        )
        self._remember_reasoning(
            "Tool-calling request failed; falling back to text-only model "
            f"response. Error: {error_message}"
        )
        self._save_memory()

    def _retry_delay_seconds(
        self,
        exc: Exception,
        base_delay: float,
        attempt: int,
    ) -> float:
        """Use Retry-After when available, otherwise exponential backoff."""
        max_delay = self._env_float("MODEL_RETRY_MAX_SECONDS", default=8.0)
        retry_after = self._retry_after_seconds(exc)
        if retry_after is not None:
            return min(retry_after, max_delay)

        return min(base_delay * (2**attempt), max_delay)

    @staticmethod
    def _model_error_message(exc: Exception) -> str:
        """Return a sanitized model error for console, memory, and reports."""
        status_code = Agent._status_code(exc)
        error_type = exc.__class__.__name__
        detail = Agent._sanitized_exception_detail(exc)

        if status_code == 401:
            return "Model request failed with HTTP 401 authentication error."
        if status_code == 429:
            return (
                "Model request failed with HTTP 429 rate limit from Gemini "
                "or the upstream model provider."
            )
        if status_code:
            return (
                f"Model request failed with HTTP {status_code} ({error_type}): "
                f"{detail}"
            )
        return f"Model request failed ({error_type}): {detail}"

    @staticmethod
    def _sanitized_exception_detail(exc: Exception) -> str:
        """Return a short exception detail with known secrets redacted."""
        detail = " ".join(str(exc).split())
        if not detail:
            return "No provider error detail was returned."

        for name, value in os.environ.items():
            is_secret = name.endswith(("_KEY", "_TOKEN", "_SECRET"))
            if is_secret and value and len(value) >= 8:
                detail = detail.replace(value, "[redacted]")

        if len(detail) > 500:
            return f"{detail[:497]}..."
        return detail

    @staticmethod
    def _status_code(exc: Exception) -> int | None:
        """Extract an HTTP status code from SDK exceptions."""
        for attribute in ("status_code", "code"):
            status_code = getattr(exc, attribute, None)
            if isinstance(status_code, int):
                return status_code

        response = getattr(exc, "response", None)
        response_status = getattr(response, "status_code", None)
        if isinstance(response_status, int):
            return response_status

        return None

    @staticmethod
    def _retry_after_seconds(exc: Exception) -> float | None:
        """Extract a numeric Retry-After response header when present."""
        response = getattr(exc, "response", None)
        headers = getattr(response, "headers", None)
        if not headers:
            return None

        retry_after = headers.get("retry-after")
        if retry_after is None:
            return None

        try:
            return max(0.0, float(retry_after))
        except ValueError:
            return None

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        """Read a non-negative integer from the environment."""
        try:
            return max(0, int(os.getenv(name, str(default))))
        except ValueError:
            return default

    @staticmethod
    def _env_float(name: str, default: float) -> float:
        """Read a non-negative float from the environment."""
        try:
            return max(0.0, float(os.getenv(name, str(default))))
        except ValueError:
            return default

    @staticmethod
    def _now() -> str:
        """Return an ISO timestamp for memory entries."""
        return datetime.now(timezone.utc).isoformat()
