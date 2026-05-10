from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DecisionInput:
    case_title: str
    evidence: dict[str, dict]
    evidence_statuses: dict[str, str]
    case_label: str | None = None
    patient_context: str | None = None
    clinical_findings: str | None = None
    variant_summary: list[str] = field(default_factory=list)


@dataclass
class DecisionOutput:
    recommendation: str
    evidence_lines: list[str]
    uncertainty: str
    next_step: str
    confidence_label: str
    warnings: list[str] = field(default_factory=list)
