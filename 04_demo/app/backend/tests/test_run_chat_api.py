from __future__ import annotations

from fastapi.testclient import TestClient

from app.tools.base import ToolResult


def _upload_report(client: TestClient, pdf_bytes: bytes, report_kind: str = 'test') -> str:
    response = client.post(
        '/api/v1/reports/upload',
        files={'file': ('ravi-report.pdf', pdf_bytes, 'application/pdf')},
        data={'report_kind': report_kind},
    )
    assert response.status_code == 201
    return response.json()['report']['report_id']


def _create_run(client: TestClient, pdf_bytes: bytes, patient_id: str = 'RP-CHAT-001') -> str:
    report_id = _upload_report(client, pdf_bytes)
    response = client.post('/api/v1/runs', json={'patient_id': patient_id, 'report_ids': [report_id]})
    assert response.status_code == 200
    return response.json()['run_id']


class FakeEmbeddings:
    def _vector(self, text: str) -> list[float]:
        normalized = text or ''
        score = sum(ord(char) for char in normalized)
        return [float(score % 997) / 997.0, float(len(normalized) % 251) / 251.0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class GroundedAnswerChain:
    def invoke(self, payload: dict[str, str]) -> dict[str, object]:
        assert 'Retrieved context' not in payload['retrieved_context']
        return {
            'answer': 'ClinVar classifies the RPE65 variant as uncertain significance in the current run.',
            'grounded': True,
            'cited_chunk_ids': [1],
        }


class UnknownAnswerChain:
    def invoke(self, payload: dict[str, str]) -> dict[str, object]:
        return {
            'answer': 'I cannot confirm that from the current report.',
            'grounded': False,
            'cited_chunk_ids': [],
        }


def test_run_chat_returns_grounded_answer_with_citations(client: TestClient, app, pdf_bytes: bytes) -> None:
    run_id = _create_run(client, pdf_bytes, patient_id='RP-CHAT-002')
    app.state.run_chat_service.embeddings = FakeEmbeddings()
    app.state.run_chat_service.answer_chain = GroundedAnswerChain()

    response = client.post(f'/api/v1/runs/{run_id}/chat', json={'question': 'What does ClinVar say?'})
    assert response.status_code == 200
    body = response.json()

    assert body['grounded'] is True
    assert 'ClinVar' in body['answer']
    assert len(body['citations']) >= 1
    assert body['citations'][0]['source_type'] in {'run_section', 'report_extract', 'evidence'}


def test_run_chat_returns_unknown_for_unsupported_question(client: TestClient, app, pdf_bytes: bytes) -> None:
    run_id = _create_run(client, pdf_bytes, patient_id='RP-CHAT-003')
    app.state.run_chat_service.embeddings = FakeEmbeddings()
    app.state.run_chat_service.answer_chain = UnknownAnswerChain()

    response = client.post(f'/api/v1/runs/{run_id}/chat', json={'question': 'What medication should be started?'})
    assert response.status_code == 200
    body = response.json()

    assert body['grounded'] is False
    assert body['citations'] == []
    assert 'cannot confirm' in body['answer'].lower()


def test_run_chat_returns_404_for_unknown_run(client: TestClient, app) -> None:
    app.state.run_chat_service.embeddings = FakeEmbeddings()
    app.state.run_chat_service.answer_chain = GroundedAnswerChain()

    response = client.post('/api/v1/runs/run_missing/chat', json={'question': 'What does ClinVar say?'})
    assert response.status_code == 404


def test_run_chat_handles_degraded_runs(client: TestClient, app, pdf_bytes: bytes, monkeypatch) -> None:
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
    run_response = client.post('/api/v1/runs', json={'patient_id': 'RP-CHAT-004', 'report_ids': [report_id]})
    assert run_response.status_code == 200
    run_id = run_response.json()['run_id']

    app.state.run_chat_service.embeddings = FakeEmbeddings()
    app.state.run_chat_service.answer_chain = GroundedAnswerChain()

    response = client.post(f'/api/v1/runs/{run_id}/chat', json={'question': 'What does the evidence show?'})
    assert response.status_code == 200
    assert response.json()['answer']
