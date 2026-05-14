from __future__ import annotations


def test_healthz_returns_mode_flags(client):
    response = client.get('/healthz')
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'ok'
    assert body['database'] == 'ok'
    assert body['llm_provider'] == 'mock'
    assert body['use_real_apis'] is False
