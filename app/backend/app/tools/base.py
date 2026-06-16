from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from functools import lru_cache
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from app.core.config import Settings


@dataclass
class ToolResult:
    source: str
    status: str
    request_identity: dict[str, Any]
    summary: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    raw: Any = None
    source_url: str | None = None
    fetched_at: str | None = None
    source_version: str | None = None
    cache_status: str | None = None


class ToolError(RuntimeError):
    pass


class FixtureBackedTool:
    source: str = "tool"
    fixture_name: str = ""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def fixture_path(self) -> Path:
        return self.settings.fixtures_root / "tools" / self.fixture_name

    def load_fixture(self) -> dict[str, Any]:
        try:
            path = self.fixture_path()
            stat = path.stat()
            return deepcopy(_load_fixture_cached(str(path), stat.st_mtime_ns, stat.st_size))
        except (FileNotFoundError, OSError):
            return {}


@lru_cache(maxsize=64)
def _load_fixture_cached(path: str, mtime_ns: int, size: int) -> dict[str, Any]:
    del mtime_ns, size
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
