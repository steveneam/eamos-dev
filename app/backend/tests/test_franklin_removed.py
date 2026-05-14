from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import app

APP_ROOT = Path(app.__file__).parent
REMOVED_TOOL = "fr" + "anklin"


def test_removed_tool_module_does_not_exist():
    tool_path = APP_ROOT / "tools" / f"{REMOVED_TOOL}.py"
    assert not tool_path.exists(), "Archived competitor tool should not be active."


def test_removed_tool_fixture_does_not_exist():
    fixture_path = APP_ROOT / "fixtures" / "tools" / f"{REMOVED_TOOL}_fixtures.json"
    assert not fixture_path.exists(), "Archived competitor fixture should not be active."


def test_no_removed_tool_imports():
    leaks = []
    for module_info in pkgutil.walk_packages([str(APP_ROOT)], prefix="app."):
        module = importlib.import_module(module_info.name)
        source_path = getattr(module, "__file__", None)
        if not source_path:
            continue
        text = Path(source_path).read_text(encoding="utf-8")
        if REMOVED_TOOL in text.lower():
            leaks.append(module_info.name)
    assert not leaks, f"Archived competitor references leaked into: {leaks}"
