from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "FinalReportService",
    "IntakeService",
    "RecommendationService",
    "ReportDraftService",
    "RunChatService",
    "WorkflowService",
]

_SERVICE_MODULES = {
    "FinalReportService": ".final_report",
    "IntakeService": ".intake",
    "RecommendationService": ".recommendation",
    "ReportDraftService": ".report_draft",
    "RunChatService": ".run_chat",
    "WorkflowService": ".workflow",
}


def __getattr__(name: str) -> Any:
    try:
        module_name = _SERVICE_MODULES[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name, __name__), name)
    globals()[name] = value
    return value
