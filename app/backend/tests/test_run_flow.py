from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.draft_render import DraftRenderService
from app.tools.base import ToolResult



def _upload_report(client: TestClient, pdf_bytes: bytes, report_kind: str = 'test') -> str:
    response = client.post(
        '/api/v1/reports/upload',
        files={'file': ('ravi-report.pdf', pdf_bytes, 'application/pdf')},
        data={'report_kind': report_kind},
    )
    assert response.status_code == 201
    return response.json()['report']['report_id']



def test_create_run_with_multiple_reports(client: TestClient, pdf_bytes: bytes) -> None:
    report_ids = [
        _upload_report(client, pdf_bytes, report_kind='test'),
        _upload_report(client, pdf_bytes, report_kind='test'),
    ]

    response = client.post('/api/v1/runs', json={'patient_id': 'RP-001', 'report_ids': report_ids})
    assert response.status_code == 200
    body = response.json()
    assert body['run_id'].startswith('run_')
    assert body['patient_id'] == 'RP-001'
    assert body['report_ids'] == report_ids
    assert body['run_status'] == 'completed'
    assert body['review_status'] == 'pending_review'
    assert body['report_payload']['patient_id'] == 'RP-001'
    assert body['report_payload']['case_label'] is None
    assert body['report_payload']['report_title'] == 'RPE65 variant review demo case'
    assert body['report_payload']['source_filenames'] == []
    assert 'Ravi' not in body['report_payload']['patient_context']
    assert 'patient ID RP-001' in body['report_payload']['patient_context']
    assert 'The patient attended Ophthalmology clinic' in body['report_payload']['patient_context']
    assert 'ERG shows' in body['report_payload']['clinical_phenotype']
    assert 'source snapshot' in body['report_payload']['acmg_classification']
    assert 'clinician support' in body['report_payload']['recommendations']



def test_patient_blocked_run_status_is_marked_blocked(client: TestClient, pdf_bytes: bytes) -> None:
    report_ids = [_upload_report(client, pdf_bytes, report_kind='patient')]
    response = client.post('/api/v1/runs', json={'patient_id': 'RP-002', 'report_ids': report_ids})
    assert response.status_code == 200
    assert response.json()['run_status'] == 'blocked'



def test_run_includes_evidence_without_nulls(client: TestClient, pdf_bytes: bytes) -> None:
    report_id = _upload_report(client, pdf_bytes)
    response = client.post('/api/v1/runs', json={'patient_id': 'RP-003', 'report_ids': [report_id]})
    assert response.status_code == 200
    body = response.json()
    sources = {item['source'] for item in body['evidence']}
    assert sources == {'vep', 'spliceai', 'clinvar', 'franklin'}



def test_run_surface_degraded_evidence_when_tool_falls_back(client: TestClient, app, pdf_bytes: bytes, monkeypatch) -> None:
    report_id = _upload_report(client, pdf_bytes)

    def fake_fallback_result() -> ToolResult:
        return ToolResult(
            source='clinvar',
            status='fallback',
            request_identity={'clinvar_id': '1421454'},
            summary={
                'gene': 'RPE65',
                'classification': 'Uncertain significance',
                'review_status': 'criteria provided, single submitter',
            },
            warnings=['live_fetch_failed:RuntimeError'],
        )

    monkeypatch.setattr(app.state.workflow_service.tool_registry['clinvar'], 'get_evidence', fake_fallback_result)

    response = client.post('/api/v1/runs', json={'patient_id': 'RP-004', 'report_ids': [report_id]})
    assert response.status_code == 200
    body = response.json()
    assert body['run_status'] == 'degraded'
    assert any('fallback' in item['status'] for item in body['evidence'])



def test_run_applies_llm_rewrite_only_to_narrative_fields(client: TestClient, app, pdf_bytes: bytes) -> None:
    report_id = _upload_report(client, pdf_bytes)

    class RewritingDraftChain:
        def invoke(self, payload: dict[str, str]) -> dict[str, str]:
            return {
                'ai_clinical_summary': 'Rewritten clinical summary for clinician review.',
                'expanded_evidence': 'Rewritten evidence narrative preserving source findings.',
                'clinical_integration': 'Rewritten integration guidance.',
                'recommendations': 'Rewritten recommendation guidance.',
                'limitations': 'Rewritten limitations preserving uncertainty.',
            }

    app.state.workflow_service.draft_render_service = DraftRenderService(RewritingDraftChain())

    response = client.post('/api/v1/runs', json={'patient_id': 'RP-005', 'report_ids': [report_id]})
    assert response.status_code == 200
    body = response.json()

    assert body['report_payload']['patient_context'].startswith('This case')
    assert 'Ravi' not in body['report_payload']['patient_context']
    assert body['report_payload']['ai_clinical_summary'] == 'Rewritten clinical summary for clinician review.'
    assert body['report_payload']['expanded_evidence'] == 'Rewritten evidence narrative preserving source findings.'
    assert body['report_payload']['variant_summary_rows'][0]['gene'] == 'RPE65'



def test_run_falls_back_cleanly_when_llm_draft_fails(client: TestClient, app, pdf_bytes: bytes) -> None:
    report_id = _upload_report(client, pdf_bytes)

    class BrokenDraftChain:
        def invoke(self, payload: dict[str, str]) -> dict[str, str]:
            raise RuntimeError('draft unavailable')

    app.state.workflow_service.draft_render_service = DraftRenderService(BrokenDraftChain())

    response = client.post('/api/v1/runs', json={'patient_id': 'RP-006', 'report_ids': [report_id]})
    assert response.status_code == 200
    body = response.json()

    assert body['run_status'] == 'completed'
    assert 'RPE65' in body['report_payload']['ai_clinical_summary']
    assert 'patient-specific interpretation step' in body['report_payload']['ai_clinical_summary']
    assert 'Ravi' not in body['report_payload']['ai_clinical_summary']
    assert 'llm_draft_fallback:RuntimeError' in body['warnings']
