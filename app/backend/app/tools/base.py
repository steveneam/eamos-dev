from __future__ import annotations

import json
from dataclasses import dataclass, field
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
        return json.loads(self.fixture_path().read_text())
