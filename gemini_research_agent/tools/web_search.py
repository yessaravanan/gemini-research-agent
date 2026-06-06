"""API-backed web search tool.

The agent uses Tavily as the default primary provider and Brave Search API as
the default secondary provider. Both return structured JSON, which is more
reliable than scraping public search-result HTML.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
SUPPORTED_PROVIDERS = {"tavily", "brave"}


def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the web with configured providers and return normalized results."""
    max_results = _max_results(max_results)
    provider_names = _provider_order()
    attempts = []

    for provider_name in provider_names:
        result = _search_provider(provider_name, query, max_results)
        attempts.append(
            {
                "provider": provider_name,
                "error": result.get("error"),
                "result_count": len(result.get("results", [])),
            }
        )
        if result.get("results"):
            result["attempts"] = attempts
            return result

    errors = [
        f"{attempt['provider']}: {attempt['error'] or 'No results returned'}"
        for attempt in attempts
    ]
    return {
        "query": query,
        "provider": ",".join(provider_names),
        "results": [],
        "attempts": attempts,
        "error": "; ".join(errors) or "No configured search providers.",
    }


def _provider_order() -> list[str]:
    """Return unique configured provider names in fallback order."""
    raw_names = [
        os.getenv("SEARCH_PRIMARY", "tavily"),
        os.getenv("SEARCH_SECONDARY", "brave"),
    ]
    provider_names = []
    for raw_name in raw_names:
        provider_name = (raw_name or "").strip().lower()
        if provider_name in SUPPORTED_PROVIDERS and provider_name not in provider_names:
            provider_names.append(provider_name)
    return provider_names


def _search_provider(
    provider_name: str,
    query: str,
    max_results: int,
) -> dict[str, Any]:
    """Dispatch a search request to one provider."""
    if provider_name == "tavily":
        return _search_tavily(query, max_results)
    if provider_name == "brave":
        return _search_brave(query, max_results)
    return {
        "query": query,
        "provider": provider_name,
        "results": [],
        "error": f"Unsupported search provider: {provider_name}",
    }


def _search_tavily(query: str, max_results: int) -> dict[str, Any]:
    """Search Tavily and normalize the result shape."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {
            "query": query,
            "provider": "tavily",
            "results": [],
            "error": "TAVILY_API_KEY is not configured.",
        }

    payload = {
        "query": query,
        "max_results": max_results,
        "search_depth": os.getenv("TAVILY_SEARCH_DEPTH", "basic"),
        "topic": os.getenv("TAVILY_TOPIC", "general"),
        "include_answer": False,
        "include_raw_content": False,
    }
    request = Request(
        TAVILY_SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        data = _json_request(request)
    except Exception as exc:
        return {
            "query": query,
            "provider": "tavily",
            "results": [],
            "error": _safe_error_message(exc),
        }

    results = []
    for item in data.get("results", [])[:max_results]:
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        snippet = str(item.get("content") or item.get("raw_content") or "").strip()
        if title and url:
            results.append({"title": title, "url": url, "snippet": snippet})

    return {
        "query": query,
        "provider": "tavily",
        "results": results,
        "response_time": data.get("response_time"),
        "request_id": data.get("request_id"),
    }


def _search_brave(query: str, max_results: int) -> dict[str, Any]:
    """Search Brave Search API and normalize the result shape."""
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        return {
            "query": query,
            "provider": "brave",
            "results": [],
            "error": "BRAVE_SEARCH_API_KEY is not configured.",
        }

    params = {
        "q": query,
        "count": max_results,
        "country": os.getenv("BRAVE_SEARCH_COUNTRY", "US"),
        "search_lang": os.getenv("BRAVE_SEARCH_LANG", "en"),
        "ui_lang": os.getenv("BRAVE_UI_LANG", "en-US"),
    }
    request = Request(
        f"{BRAVE_SEARCH_URL}?{urlencode(params)}",
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "X-Subscription-Token": api_key,
        },
    )

    try:
        data = _json_request(request)
    except Exception as exc:
        return {
            "query": query,
            "provider": "brave",
            "results": [],
            "error": _safe_error_message(exc),
        }

    web_results = data.get("web", {}).get("results", [])
    results = []
    for item in web_results[:max_results]:
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        snippets = item.get("extra_snippets") or []
        snippet = str(item.get("description") or "").strip()
        if not snippet and snippets:
            snippet = " ".join(str(snippet).strip() for snippet in snippets if snippet)
        if title and url:
            results.append({"title": title, "url": url, "snippet": snippet})

    return {
        "query": query,
        "provider": "brave",
        "results": results,
        "query_context": data.get("query", {}),
    }


def _json_request(request: Request) -> dict[str, Any]:
    """Execute an HTTP request and decode a JSON response."""
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _max_results(max_results: int) -> int:
    """Clamp result count using env default when caller input is invalid."""
    try:
        requested = int(max_results)
    except (TypeError, ValueError):
        requested = _env_int("SEARCH_MAX_RESULTS", default=5)
    if requested <= 0:
        requested = _env_int("SEARCH_MAX_RESULTS", default=5)
    return max(1, min(requested, 10))


def _safe_error_message(exc: Exception) -> str:
    """Return a sanitized provider error message without secret values."""
    if isinstance(exc, HTTPError):
        return f"HTTP {exc.code}: {exc.reason}"
    if isinstance(exc, URLError):
        return f"Network error: {exc.reason}"
    if isinstance(exc, json.JSONDecodeError):
        return "Search provider returned invalid JSON."
    return exc.__class__.__name__


def _env_int(name: str, default: int) -> int:
    """Read a positive integer environment variable."""
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default
