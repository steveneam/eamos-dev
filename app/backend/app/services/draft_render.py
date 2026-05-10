from __future__ import annotations

import json

from app.rules.base import DecisionOutput
from app.schemas.run import ReportPayload
from app.schemas.draft import DraftPayload


class DraftRenderService:
    def __init__(self, draft_chain) -> None:
        self.draft_chain = draft_chain

    def render(
        self,
        *,
        case_title: str,
        patient_context: str | None,
        clinical_phenotype: str | None,
        variant_summary: str,
        decision: DecisionOutput,
        evidence_statuses: dict[str, str],
        warnings: list[str],
        base_payload: ReportPayload,
    ) -> tuple[DraftPayload, list[str]]:
        deterministic_payload = DraftPayload(
            ai_clinical_summary=base_payload.ai_clinical_summary or '',
            expanded_evidence=base_payload.expanded_evidence or '',
            clinical_integration=base_payload.clinical_integration or '',
            recommendations=base_payload.recommendations or '',
            limitations=base_payload.limitations or '',
        )
        if self.draft_chain is None:
            return deterministic_payload, ['llm_draft_fallback:unavailable']

        payload = {
            'case_title': case_title,
            'patient_context': patient_context or '',
            'clinical_phenotype': clinical_phenotype or '',
            'variant_summary': variant_summary,
            'recommendation': decision.recommendation,
            'evidence_lines': json.dumps(decision.evidence_lines),
            'uncertainty': decision.uncertainty,
            'next_step': decision.next_step,
            'confidence_label': decision.confidence_label,
            'evidence_statuses': json.dumps(evidence_statuses, sort_keys=True),
            'warnings': json.dumps(warnings, sort_keys=True),
            'ai_clinical_summary': deterministic_payload.ai_clinical_summary,
            'expanded_evidence': deterministic_payload.expanded_evidence,
            'clinical_integration': deterministic_payload.clinical_integration,
            'recommendations': deterministic_payload.recommendations,
            'limitations': deterministic_payload.limitations,
        }
        try:
            rewritten = self.draft_chain.invoke(payload)
            drafted = DraftPayload.model_validate(rewritten)
            return drafted, []
        except Exception as exc:
            return deterministic_payload, [f'llm_draft_fallback:{exc.__class__.__name__}']
