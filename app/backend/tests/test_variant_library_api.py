from __future__ import annotations

from urllib.parse import quote

from fastapi.testclient import TestClient


def _saved_variant_payload(**overrides) -> dict:
    payload = {
        "id": "ush2a:c.2276g>t",
        "gene": "USH2A",
        "variant": "c.2276G>T",
        "query": "USH2A c.2276G>T",
        "raw": "USH2A c.2276G>T",
        "savedAt": 1_780_000_000_000,
        "folderId": None,
        "classification": "likely_pathogenic",
        "hgvs_full": "NM_206933.4:c.2276G>T",
    }
    payload.update(overrides)
    return payload


def test_variant_library_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/library")

    assert response.status_code == 401


def test_variant_library_replace_requires_authentication(client: TestClient) -> None:
    response = client.put("/api/v1/library", json={"variants": [], "folders": []})

    assert response.status_code == 401


def test_variant_library_whole_document_sync_round_trip(auth_client: TestClient) -> None:
    folder = {"id": "folder-retina", "name": "Retina", "createdAt": 1_780_000_000_001}
    payload = {
        "variants": [_saved_variant_payload(folderId=folder["id"])],
        "folders": [folder],
    }

    replaced = auth_client.put("/api/v1/library", json=payload)
    fetched = auth_client.get("/api/v1/library")

    assert replaced.status_code == 200
    assert fetched.status_code == 200
    assert replaced.json()["variants"] == payload["variants"]
    assert replaced.json()["folders"] == payload["folders"]
    assert isinstance(replaced.json()["updated_at"], str)
    assert fetched.json() == replaced.json()


def test_variant_library_whole_document_is_account_scoped(client: TestClient) -> None:
    first = client.post(
        "/api/v1/auth/register",
        json={"username": "first-user", "password": "first-password"},
    )
    second = client.post(
        "/api/v1/auth/register",
        json={"username": "second-user", "password": "second-password"},
    )
    assert first.status_code == 201
    assert second.status_code == 201

    client.headers.update({"Authorization": f"Bearer {first.json()['access_token']}"})
    stored = client.put(
        "/api/v1/library",
        json={"variants": [_saved_variant_payload()], "folders": []},
    )
    assert stored.status_code == 200

    client.headers.update({"Authorization": f"Bearer {second.json()['access_token']}"})
    other = client.get("/api/v1/library")

    assert other.status_code == 200
    assert other.json()["variants"] == []
    assert other.json()["folders"] == []


def test_variant_library_crud_round_trip(auth_client: TestClient) -> None:
    folder = auth_client.post("/api/v1/library/folders", json={"name": " Retina "})
    assert folder.status_code == 201
    folder_body = folder.json()
    assert folder_body["name"] == "Retina"
    assert isinstance(folder_body["createdAt"], int)

    duplicate = auth_client.post("/api/v1/library/folders", json={"name": "retina"})
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == folder_body["id"]

    saved = auth_client.post(
        "/api/v1/library/variants",
        json=_saved_variant_payload(folderId=folder_body["id"]),
    )
    assert saved.status_code == 201
    assert saved.json() == _saved_variant_payload(folderId=folder_body["id"])

    library = auth_client.get("/api/v1/library")
    assert library.status_code == 200
    assert library.json()["folders"] == [folder_body]
    assert library.json()["variants"] == [_saved_variant_payload(folderId=folder_body["id"])]

    renamed = auth_client.patch(
        f"/api/v1/library/folders/{folder_body['id']}",
        json={"name": "Retina review"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Retina review"

    moved_top = auth_client.patch(
        f"/api/v1/library/variants/{quote('ush2a:c.2276g>t', safe='')}/folder",
        json={"folder_id": None},
    )
    assert moved_top.status_code == 200
    assert moved_top.json()["folderId"] is None

    remove_folder = auth_client.delete(f"/api/v1/library/folders/{folder_body['id']}")
    assert remove_folder.status_code == 204

    after_folder_delete = auth_client.get("/api/v1/library")
    assert after_folder_delete.status_code == 200
    assert after_folder_delete.json()["folders"] == []
    assert after_folder_delete.json()["variants"][0]["folderId"] is None

    remove_variant = auth_client.delete(
        f"/api/v1/library/variants/{quote('ush2a:c.2276g>t', safe='')}"
    )
    assert remove_variant.status_code == 204
    assert auth_client.get("/api/v1/library").json()["variants"] == []


def test_variant_library_bulk_save_reports_added_count(auth_client: TestClient) -> None:
    payload = {
        "variants": [
            _saved_variant_payload(),
            _saved_variant_payload(
                id="rpe65:c.260a>g",
                gene="RPE65",
                variant="c.260A>G",
                query="RPE65 c.260A>G",
                raw="RPE65 c.260A>G",
                classification=None,
                hgvs_full=None,
            ),
        ]
    }

    first = auth_client.post("/api/v1/library/variants/bulk", json=payload)
    second = auth_client.post("/api/v1/library/variants/bulk", json=payload)

    assert first.status_code == 200
    assert first.json()["added"] == 2
    assert len(first.json()["library"]["variants"]) == 2
    assert second.status_code == 200
    assert second.json()["added"] == 0
    assert len(second.json()["library"]["variants"]) == 2


def test_variant_library_get_library_paginates_saved_variants(auth_client: TestClient) -> None:
    payload = {
        "variants": [
            _saved_variant_payload(id="variant-a", query="variant a", savedAt=10),
            _saved_variant_payload(id="variant-b", query="variant b", savedAt=20),
            _saved_variant_payload(id="variant-c", query="variant c", savedAt=30),
        ]
    }
    saved = auth_client.post("/api/v1/library/variants/bulk", json=payload)
    assert saved.status_code == 200

    page = auth_client.get("/api/v1/library?limit=2&offset=1")

    assert page.status_code == 200
    assert [variant["id"] for variant in page.json()["variants"]] == ["variant-b", "variant-a"]


def test_variant_library_rejects_oversized_bulk_save(auth_client: TestClient) -> None:
    payload = {
        "variants": [
            _saved_variant_payload(id=f"variant-{idx}", query=f"variant {idx}")
            for idx in range(101)
        ]
    }

    response = auth_client.post("/api/v1/library/variants/bulk", json=payload)

    assert response.status_code == 422


def test_variant_library_path_ids_allow_slashes_for_move_and_delete(
    auth_client: TestClient,
) -> None:
    folder = auth_client.post("/api/v1/library/folders", json={"name": "Protein notes"})
    assert folder.status_code == 201
    folder_id = folder.json()["id"]
    variant_id = "rpe65:c.260a>g / p.asp87gly"

    saved = auth_client.post(
        "/api/v1/library/variants",
        json=_saved_variant_payload(
            id=variant_id,
            gene="RPE65",
            variant="c.260A>G / p.Asp87Gly",
            query="RPE65 c.260A>G / p.Asp87Gly",
            raw="RPE65 c.260A>G / p.Asp87Gly",
            classification=None,
            hgvs_full=None,
        ),
    )
    assert saved.status_code == 201

    encoded_id = quote(variant_id, safe="")
    moved = auth_client.patch(
        f"/api/v1/library/variants/{encoded_id}/folder",
        json={"folderId": folder_id},
    )
    assert moved.status_code == 200
    assert moved.json()["folderId"] == folder_id

    removed = auth_client.delete(f"/api/v1/library/variants/{encoded_id}")
    assert removed.status_code == 204


def test_variant_library_rejects_move_to_other_or_missing_folder(auth_client: TestClient) -> None:
    saved = auth_client.post("/api/v1/library/variants", json=_saved_variant_payload())
    assert saved.status_code == 201

    response = auth_client.patch(
        f"/api/v1/library/variants/{quote('ush2a:c.2276g>t', safe='')}/folder",
        json={"folderId": "missing-folder"},
    )

    assert response.status_code == 404


def test_variant_library_popularity_counter(auth_client: TestClient) -> None:
    empty = auth_client.get("/api/v1/library/popular")
    assert empty.status_code == 200
    assert empty.json() == {"variants": []}

    query_id = quote("USH2A c.2276G>T", safe="")
    first = auth_client.post(f"/api/v1/library/views/{query_id}")
    second = auth_client.post(f"/api/v1/library/views/{query_id}")

    assert first.status_code == 200
    assert first.json()["variant"]["query_id"] == "ush2a c.2276g>t"
    assert first.json()["variant"]["view_count"] == 1
    assert second.status_code == 200
    assert second.json()["variant"]["view_count"] == 2

    popular = auth_client.get("/api/v1/library/popular?limit=5")
    assert popular.status_code == 200
    assert popular.json()["variants"][0]["query_id"] == "ush2a c.2276g>t"
    assert popular.json()["variants"][0]["view_count"] == 2
