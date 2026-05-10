from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.db import UserRecord, session_scope


def _auth_headers(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def test_register_returns_token_and_persists_argon2_hash(client: TestClient) -> None:
    response = client.post(
        '/api/v1/auth/register',
        json={'username': 'leo', 'password': 'Testpass123!'},
    )
    assert response.status_code == 201
    body = response.json()
    assert body['token_type'] == 'bearer'
    assert body['ttl_seconds'] == 7 * 24 * 60 * 60
    assert body['user']['username'] == 'leo'

    with session_scope(client.app.state.db_session_factory) as session:
        record = session.get(UserRecord, body['user']['user_id'])
        assert record is not None
        assert record.hashed_password != 'Testpass123!'
        assert record.hashed_password.startswith('$argon2')


def test_register_rejects_duplicate_username(client: TestClient) -> None:
    first = client.post(
        '/api/v1/auth/register',
        json={'username': 'leo', 'password': 'Testpass123!'},
    )
    assert first.status_code == 201

    duplicate = client.post(
        '/api/v1/auth/register',
        json={'username': 'leo', 'password': 'Anotherpass123!'},
    )
    assert duplicate.status_code == 409


def test_login_me_logout_flow(client: TestClient) -> None:
    register = client.post(
        '/api/v1/auth/register',
        json={'username': 'leo', 'password': 'Testpass123!'},
    )
    assert register.status_code == 201

    login = client.post(
        '/api/v1/auth/login',
        json={'username': 'leo', 'password': 'Testpass123!'},
    )
    assert login.status_code == 200
    token = login.json()['access_token']

    me = client.get('/api/v1/auth/me', headers=_auth_headers(token))
    assert me.status_code == 200
    assert me.json()['username'] == 'leo'

    logout = client.post('/api/v1/auth/logout', headers=_auth_headers(token))
    assert logout.status_code == 204

    stale_me = client.get('/api/v1/auth/me', headers=_auth_headers(token))
    assert stale_me.status_code == 401


def test_login_rejects_invalid_password(client: TestClient) -> None:
    register = client.post(
        '/api/v1/auth/register',
        json={'username': 'leo', 'password': 'Testpass123!'},
    )
    assert register.status_code == 201

    login = client.post(
        '/api/v1/auth/login',
        json={'username': 'leo', 'password': 'wrongpass123'},
    )
    assert login.status_code == 401


def test_existing_health_endpoint_remains_public(client: TestClient) -> None:
    response = client.get('/healthz')
    assert response.status_code == 200
