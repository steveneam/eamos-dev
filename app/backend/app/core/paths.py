from __future__ import annotations

from pathlib import Path


def find_project_root(anchor: Path | str | None = None) -> Path:
    """Find the checkout or backend root from either local or Docker layouts."""
    current = Path(anchor) if anchor is not None else Path(__file__)
    resolved = current.resolve()
    start = resolved if resolved.is_dir() else resolved.parent
    repo_candidate: Path | None = None
    backend_candidate: Path | None = None
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists() and (candidate / "app" / "backend").is_dir():
            return candidate
        if (candidate / "app" / "backend" / "pyproject.toml").is_file():
            repo_candidate = repo_candidate or candidate
        if (candidate / "pyproject.toml").is_file() and (candidate / "app").is_dir():
            backend_candidate = backend_candidate or candidate
    return repo_candidate or backend_candidate or start


def repo_relative_path(path: Path, *, anchor: Path | str | None = None) -> str:
    root = find_project_root(anchor)
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path)
