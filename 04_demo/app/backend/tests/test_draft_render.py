from __future__ import annotations

from app.rules.base import DecisionOutput
from app.schemas.run import ReportPayload
from app.services.draft_render import DraftRenderService


class ValidDraftChain:
    def invoke(self, payload: dict[str, str]) -> dict[str, str]:
        return {
            'ai_clinical_summary': 'Findings remain most consistent with an inherited retinal disease review case and support clinician-led interpretation.',
            'expanded_evidence': 'Available evidence supports a biologically relevant RPE65 finding, with external sources contributing supportive but not definitive interpretive weight.',
            'clinical_integration': 'Correlation of the molecular finding with phenotype and transcript context remains important before any final clinical release.',
            'recommendations': 'Proceed with specialist review, confirm phenotype alignment, and retain governance sign-off prior to final communication.',
            'limitations': 'This report remains constrained by the underlying uncertain-significance signal and should not be treated as an autonomous clinical conclusion.',
        }


class InvalidDraftChain:
    def invoke(self, payload: dict[str, str]) -> dict[str, str]:
        return {
            'ai_clinical_summary': 'Incomplete draft payload.',
        }


def build_decision() -> DecisionOutput:
    return DecisionOutput(
        recommendation='Escalate this case for clinician review.',
        evidence_lines=['ClinVar classification: Uncertain significance.'],
        uncertainty='Evidence remains insufficient for autonomous referral.',
        next_step='Complete phenotype validation before final output.',
        confidence_label='medium',
        warnings=[],
    )


def build_base_payload() -> ReportPayload:
    return ReportPayload(
        patient_id='RP-001',
        patient_context='Ravi is being reviewed in the inherited retinal disease pathway.',
        clinical_phenotype='Inherited retinal disease review case.',
        ai_clinical_summary='Deterministic summary.',
        variant_summary_rows=[],
        expanded_evidence='Deterministic evidence summary.',
        acmg_classification='Deterministic ACMG line.',
        clinical_integration='Deterministic integration step.',
        expected_symptoms='Progressive vision loss.',
        recommendations='Deterministic recommendation.',
        limitations='Deterministic limitations.',
    )


def test_draft_render_rewrites_narrative_fields_when_chain_is_valid() -> None:
    service = DraftRenderService(ValidDraftChain())

    drafted, warnings = service.render(
        case_title='RPE65 demo case',
        patient_context='Ravi is being reviewed in the inherited retinal disease pathway.',
        clinical_phenotype='Inherited retinal disease review case.',
        variant_summary='RPE65 NM_000329.3:c.260A>G (p.Asp87Gly), missense variant',
        decision=build_decision(),
        evidence_statuses={'vep': 'live'},
        warnings=[],
        base_payload=build_base_payload(),
    )

    assert warnings == []
    assert 'clinician-led interpretation' in drafted.ai_clinical_summary
    assert drafted.recommendations.startswith('Proceed with specialist review')



def test_draft_render_returns_deterministic_fields_when_chain_is_missing() -> None:
    service = DraftRenderService(None)

    drafted, warnings = service.render(
        case_title='RPE65 demo case',
        patient_context='Ravi is being reviewed in the inherited retinal disease pathway.',
        clinical_phenotype='Inherited retinal disease review case.',
        variant_summary='RPE65 NM_000329.3:c.260A>G (p.Asp87Gly), missense variant',
        decision=build_decision(),
        evidence_statuses={'vep': 'live'},
        warnings=[],
        base_payload=build_base_payload(),
    )

    assert warnings == ['llm_draft_fallback:unavailable']
    assert drafted.ai_clinical_summary == 'Deterministic summary.'
    assert drafted.expanded_evidence == 'Deterministic evidence summary.'



def test_draft_render_falls_back_when_chain_returns_invalid_output() -> None:
    service = DraftRenderService(InvalidDraftChain())

    drafted, warnings = service.render(
        case_title='RPE65 demo case',
        patient_context='Ravi is being reviewed in the inherited retinal disease pathway.',
        clinical_phenotype='Inherited retinal disease review case.',
        variant_summary='RPE65 NM_000329.3:c.260A>G (p.Asp87Gly), missense variant',
        decision=build_decision(),
        evidence_statuses={'vep': 'live'},
        warnings=[],
        base_payload=build_base_payload(),
    )

    assert warnings == ['llm_draft_fallback:ValidationError']
    assert drafted.clinical_integration == 'Deterministic integration step.'
