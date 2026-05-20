from __future__ import annotations

from fastapi.testclient import TestClient


def test_protected_route_rejects_missing_bearer_token(client: TestClient) -> None:
    response = client.post("/api/v1/runs", json={"patient_id": "AUTH-001", "report_ids": []})

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
