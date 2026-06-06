"""Workspace-safe file tools for the agent."""

from __future__ import annotations

from pathlib import Path


WORKSPACE_ROOT = Path.cwd().resolve()


def _safe_path(path: str) -> Path:
    """Resolve a path and ensure it stays inside the workspace."""
    candidate = (WORKSPACE_ROOT / path).resolve()
    if candidate != WORKSPACE_ROOT and WORKSPACE_ROOT not in candidate.parents:
        raise ValueError(f"Path is outside the workspace: {path}")
    return candidate


def read_file(path: str) -> dict[str, str]:
    """Read a UTF-8 text file from the workspace."""
    file_path = _safe_path(path)
    return {"path": path, "content": file_path.read_text(encoding="utf-8")}


def write_file(path: str, content: str) -> dict[str, str]:
    """Write UTF-8 text to a file in the workspace."""
    file_path = _safe_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return {"path": path, "status": "written"}


def list_files(path: str = ".", recursive: bool = False) -> dict[str, list[str]]:
    """List files or directories under a workspace path."""
    directory = _safe_path(path)
    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {path}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path}")

    pattern = "**/*" if recursive else "*"
    entries = []
    for entry in sorted(directory.glob(pattern)):
        if "__pycache__" in entry.parts:
            continue
        entries.append(str(entry.relative_to(WORKSPACE_ROOT)))

    return {"path": path, "files": entries}
