from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfReader



def _prepare_run(client: TestClient, pdf_bytes: bytes) -> str:
    upload = client.post(
        '/api/v1/reports/upload',
        files={'file': ('ravi-report.pdf', pdf_bytes, 'application/pdf')},
        data={'report_kind': 'test'},
    )
    report_id = upload.json()['report']['report_id']
    run_response = client.post(
        '/api/v1/runs',
        json={'patient_id': 'review-case', 'report_ids': [report_id]},
    )
    assert run_response.status_code == 200
    return run_response.json()['run_id']



def test_review_only_stores_note_and_timestamp(client: TestClient, pdf_bytes: bytes) -> None:
    run_id = _prepare_run(client, pdf_bytes)
    response = client.post(
        f'/api/v1/runs/{run_id}/review',
        json={'reviewer_name': 'Leo', 'review_note': 'Looks good, minor wording tweak needed.'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['run_id'] == run_id
    assert body['review_status'] == 'reviewed'
    assert body['review_note'] == 'Looks good, minor wording tweak needed.'



def test_review_requires_note_text(client: TestClient, pdf_bytes: bytes) -> None:
    run_id = _prepare_run(client, pdf_bytes)
    response = client.post(f'/api/v1/runs/{run_id}/review', json={'reviewer_name': 'Leo', 'review_note': ''})
    assert response.status_code == 400



def test_approve_generates_frozen_pdf(client: TestClient, pdf_bytes: bytes) -> None:
    run_id = _prepare_run(client, pdf_bytes)
    client.post(
        f'/api/v1/runs/{run_id}/review',
        json={'reviewer_name': 'Leo', 'review_note': 'Approved with note.'},
    )

    response = client.post(f'/api/v1/runs/{run_id}/approve')
    assert response.status_code == 200
    body = response.json()
    assert body['run_id'] == run_id
    assert body['download_path'].endswith('/pdf')

    pdf = client.get(f'/api/v1/runs/{run_id}/pdf')
    assert pdf.status_code == 200
    assert pdf.headers['content-type'].startswith('application/pdf')
    assert pdf.content.startswith(b'%PDF')

    reader = PdfReader(BytesIO(pdf.content))
    text = '\n'.join((page.extract_text() or '') for page in reader.pages)
    assert 'AI Genomic Report Tool' in text
    assert 'Backend Enhancement Recommendations' in text
    assert 'Section 2 — Clinical Context' in text
    assert 'Section 7 — Clinical Integration' in text



def test_patch_report_payload_updates_preview_pdf_and_preserves_locked_fields(client: TestClient, pdf_bytes: bytes) -> None:
    run_id = _prepare_run(client, pdf_bytes)

    response = client.patch(
        f'/api/v1/runs/{run_id}/report-payload',
        json={
            'patient_context': 'Edited patient context for preview.',
            'ai_clinical_summary': 'Edited summary for preview.',
            'recommendations': 'Edited recommendation for preview.',
            'review_note': 'Draft review note.',
            'patient_id': 'should-not-change',
            'variant_summary_rows': [],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body['report_payload']['patient_id'] == 'review-case'
    assert body['report_payload']['variant_summary_rows']
    assert body['report_payload']['patient_context'] == 'Edited patient context for preview.'
    assert body['report_payload']['ai_clinical_summary'] == 'Edited summary for preview.'
    assert body['review_note'] == 'Draft review note.'

    pdf = client.get(f'/api/v1/runs/{run_id}/pdf')
    assert pdf.status_code == 200
    reader = PdfReader(BytesIO(pdf.content))
    text = '\n'.join((page.extract_text() or '') for page in reader.pages)
    assert 'AI Genomic Report Tool' in text
    assert 'Backend Enhancement Recommendations' in text
    assert 'Edited patient context for preview.' not in text
    assert 'Edited summary for preview.' not in text
    assert 'Edited recommendation for preview.' not in text



def test_patch_report_payload_is_blocked_after_approve(client: TestClient, pdf_bytes: bytes) -> None:
    run_id = _prepare_run(client, pdf_bytes)
    approve = client.post(f'/api/v1/runs/{run_id}/approve')
    assert approve.status_code == 200

    patch = client.patch(
        f'/api/v1/runs/{run_id}/report-payload',
        json={'ai_clinical_summary': 'Should not persist.'},
    )
    assert patch.status_code == 409



def test_drop_marks_run_dropped_and_blocks_pdf(client: TestClient, pdf_bytes: bytes) -> None:
    run_id = _prepare_run(client, pdf_bytes)
    drop = client.post(f'/api/v1/runs/{run_id}/drop', json={'review_note': 'Noisy extraction.'})
    assert drop.status_code == 200
    assert drop.json()['review_status'] == 'dropped'

    pdf = client.get(f'/api/v1/runs/{run_id}/pdf')
    assert pdf.status_code == 409

    patch = client.patch(
        f'/api/v1/runs/{run_id}/report-payload',
        json={'ai_clinical_summary': 'Should not persist.'},
    )
    assert patch.status_code == 409
