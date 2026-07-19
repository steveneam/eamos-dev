from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx

from app.repos.variant_library_repo import (
    SavedVariantRecord,
    SupabaseVariantLibraryRepo,
    make_library_tombstone,
    merge_library_variant_documents,
)


def test_supabase_variant_library_upserts_saved_variant_with_owner_from_backend() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content.decode("utf-8"))
        assert body == {
            "id": "ush2a:c.2276g>t",
            "user_id": "23fc93e9-d351-4a9f-b5a7-f23dd7ceab11",
            "gene": "USH2A",
            "variant": "c.2276G>T",
            "query": "USH2A c.2276G>T",
            "raw": "USH2A c.2276G>T",
            "saved_at": 1_780_000_000_000,
            "folder_id": None,
            "classification": "likely_pathogenic",
            "hgvs_full": "NM_206933.4:c.2276G>T",
        }
        return httpx.Response(status_code=201, json=[body])

    repo = SupabaseVariantLibraryRepo(
        supabase_url="https://cpdjxsgasaesysvxkpmi.supabase.co/",
        service_role_key="service-role-key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    row = repo.save_variant(
        user_id="23fc93e9-d351-4a9f-b5a7-f23dd7ceab11",
        variant=SavedVariantRecord(
            id="ush2a:c.2276g>t",
            gene="USH2A",
            variant="c.2276G>T",
            query="USH2A c.2276G>T",
            raw="USH2A c.2276G>T",
            saved_at=1_780_000_000_000,
            folder_id=None,
            classification="likely_pathogenic",
            hgvs_full="NM_206933.4:c.2276G>T",
        ),
    )

    assert row.id == "ush2a:c.2276g>t"
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == (
        "https://cpdjxsgasaesysvxkpmi.supabase.co/rest/v1/" "saved_variant?on_conflict=id%2Cuser_id"
    )
    assert request.headers["apikey"] == "service-role-key"
    assert request.headers["authorization"] == "Bearer service-role-key"
    assert request.headers["prefer"] == "resolution=merge-duplicates,return=representation"


def test_supabase_variant_library_bulk_upserts_saved_variants_in_one_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            url = str(request.url)
            assert "saved_variant" in url
            assert "select=id" in url
            assert "user_id=eq.23fc93e9-d351-4a9f-b5a7-f23dd7ceab11" in url
            return httpx.Response(status_code=200, json=[{"id": "existing"}])
        body = json.loads(request.content.decode("utf-8"))
        assert request.method == "POST"
        assert isinstance(body, list)
        assert [row["id"] for row in body] == ["existing", "new"]
        assert {row["user_id"] for row in body} == {"23fc93e9-d351-4a9f-b5a7-f23dd7ceab11"}
        return httpx.Response(status_code=201, json=body)

    repo = SupabaseVariantLibraryRepo(
        supabase_url="https://cpdjxsgasaesysvxkpmi.supabase.co/",
        service_role_key="service-role-key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    added, rows = repo.save_variants(
        user_id="23fc93e9-d351-4a9f-b5a7-f23dd7ceab11",
        variants=[
            SavedVariantRecord(
                id="existing",
                gene="RPE65",
                variant="c.260A>G",
                query="RPE65 c.260A>G",
                raw="RPE65 c.260A>G",
                saved_at=1_780_000_000_000,
                folder_id=None,
                classification=None,
                hgvs_full=None,
            ),
            SavedVariantRecord(
                id="new",
                gene="USH2A",
                variant="c.2276G>T",
                query="USH2A c.2276G>T",
                raw="USH2A c.2276G>T",
                saved_at=1_780_000_000_001,
                folder_id=None,
                classification="likely_pathogenic",
                hgvs_full="NM_206933.4:c.2276G>T",
            ),
        ],
    )

    assert added == 1
    assert [row.id for row in rows] == ["existing", "new"]
    assert [request.method for request in requests] == ["GET", "POST"]
    assert str(requests[1].url) == (
        "https://cpdjxsgasaesysvxkpmi.supabase.co/rest/v1/" "saved_variant?on_conflict=id%2Cuser_id"
    )
    assert requests[1].headers["prefer"] == "resolution=merge-duplicates,return=representation"


def test_supabase_variant_library_replaces_whole_document_with_owner_from_backend() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            assert "user_id=eq.23fc93e9-d351-4a9f-b5a7-f23dd7ceab11" in str(request.url)
            return httpx.Response(status_code=200, json=[])
        body = json.loads(request.content.decode("utf-8"))
        assert body["user_id"] == "23fc93e9-d351-4a9f-b5a7-f23dd7ceab11"
        assert body["variants"] == [
            {
                "id": "rpe65:c.938a>g",
                "gene": "RPE65",
                "variant": "c.938A>G",
                "query": "RPE65 c.938A>G",
                "raw": "RPE65 c.938A>G",
                "savedAt": 1_780_000_000_000,
                "folderId": "folder-retina",
            }
        ]
        assert body["folders"] == [
            {"id": "folder-retina", "name": "Retina", "createdAt": 1_780_000_000_001}
        ]
        assert "updated_at" in body
        return httpx.Response(status_code=201, json=[body])

    repo = SupabaseVariantLibraryRepo(
        supabase_url="https://cpdjxsgasaesysvxkpmi.supabase.co/",
        service_role_key="service-role-key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    row = repo.replace_document(
        user_id="23fc93e9-d351-4a9f-b5a7-f23dd7ceab11",
        variants=[
            {
                "id": "rpe65:c.938a>g",
                "gene": "RPE65",
                "variant": "c.938A>G",
                "query": "RPE65 c.938A>G",
                "raw": "RPE65 c.938A>G",
                "savedAt": 1_780_000_000_000,
                "folderId": "folder-retina",
            }
        ],
        folders=[{"id": "folder-retina", "name": "Retina", "createdAt": 1_780_000_000_001}],
    )

    assert row.user_id == "23fc93e9-d351-4a9f-b5a7-f23dd7ceab11"
    assert row.variants[0]["id"] == "rpe65:c.938a>g"
    assert len(requests) == 2
    request = requests[1]
    assert str(request.url) == (
        "https://cpdjxsgasaesysvxkpmi.supabase.co/rest/v1/" "user_library?on_conflict=user_id"
    )
    assert request.headers["apikey"] == "service-role-key"
    assert request.headers["authorization"] == "Bearer service-role-key"
    assert request.headers["prefer"] == "resolution=ignore-duplicates,return=representation"


def test_variant_library_document_merge_is_commutative_and_tombstone_safe() -> None:
    active = {
        "id": "RPE65:C.260A>G",
        "gene": "RPE65",
        "variant": "c.260A>G",
        "query": "RPE65 c.260A>G",
        "raw": "RPE65 c.260A>G",
        "savedAt": 100,
        "folderId": None,
    }
    tombstone = make_library_tombstone("rpe65:c.260a>g", saved_at=100)

    left_to_right = merge_library_variant_documents([active], [tombstone])
    right_to_left = merge_library_variant_documents([tombstone], [active])

    assert left_to_right == right_to_left == [tombstone]
    newer_active = {**active, "savedAt": 101}
    assert merge_library_variant_documents([tombstone], [newer_active]) == [
        {**newer_active, "id": "rpe65:c.260a>g"}
    ]


def test_supabase_document_replace_retries_concurrent_write_without_resurrection() -> None:
    user_id = "23fc93e9-d351-4a9f-b5a7-f23dd7ceab11"
    active = {
        "id": "rpe65:c.260a>g",
        "gene": "RPE65",
        "variant": "c.260A>G",
        "query": "RPE65 c.260A>G",
        "raw": "RPE65 c.260A>G",
        "savedAt": 150,
        "folderId": None,
    }
    tombstone = make_library_tombstone(active["id"], saved_at=200)
    requests: list[httpx.Request] = []

    def document(variants: list[dict], updated_at: str) -> dict:
        return {
            "user_id": user_id,
            "variants": variants,
            "folders": [],
            "updated_at": updated_at,
        }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        request_number = len(requests)
        if request_number == 1:
            return httpx.Response(
                status_code=200,
                json=[document([{**active, "savedAt": 100}], "2026-07-19T12:00:00Z")],
            )
        if request_number == 2:
            assert request.method == "PATCH"
            assert request.url.params["user_id"] == f"eq.{user_id}"
            assert request.url.params["updated_at"] == "eq.2026-07-19T12:00:00+00:00"
            return httpx.Response(status_code=200, json=[])
        if request_number == 3:
            return httpx.Response(
                status_code=200,
                json=[document([tombstone], "2026-07-19T12:00:01Z")],
            )
        if request_number == 4:
            body = json.loads(request.content.decode("utf-8"))
            assert request.method == "PATCH"
            assert request.url.params["updated_at"] == "eq.2026-07-19T12:00:01+00:00"
            assert body["variants"] == [tombstone]
            return httpx.Response(status_code=200, json=[body])
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    repo = SupabaseVariantLibraryRepo(
        supabase_url="https://cpdjxsgasaesysvxkpmi.supabase.co",
        service_role_key="service-role-key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    row = repo.replace_document(user_id=user_id, variants=[active], folders=[])

    assert row.variants == [tombstone]
    assert len(requests) == 4


def test_supabase_variant_library_gets_whole_document_by_owner() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == "GET"
        assert "user_id=eq.23fc93e9-d351-4a9f-b5a7-f23dd7ceab11" in str(request.url)
        return httpx.Response(
            status_code=200,
            json=[
                {
                    "user_id": "23fc93e9-d351-4a9f-b5a7-f23dd7ceab11",
                    "variants": [],
                    "folders": [],
                    "updated_at": "2026-06-14T09:58:00Z",
                }
            ],
        )

    repo = SupabaseVariantLibraryRepo(
        supabase_url="https://cpdjxsgasaesysvxkpmi.supabase.co",
        service_role_key="service-role-key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    row = repo.get_document(user_id="23fc93e9-d351-4a9f-b5a7-f23dd7ceab11")

    assert row is not None
    assert row.variants == []
    assert row.folders == []
    assert row.updated_at == datetime(2026, 6, 14, 9, 58, tzinfo=timezone.utc)


def test_supabase_variant_library_folder_crud_uses_owner_filters() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            assert "user_id=eq.23fc93e9-d351-4a9f-b5a7-f23dd7ceab11" in str(request.url)
            return httpx.Response(status_code=200, json=[])
        if request.method == "POST":
            body = json.loads(request.content.decode("utf-8"))
            assert body == {
                "user_id": "23fc93e9-d351-4a9f-b5a7-f23dd7ceab11",
                "name": "Retina",
            }
            return httpx.Response(
                status_code=201,
                json=[
                    {
                        "id": "a8ff9c92-84b6-4d6a-b26e-f236c87d4c86",
                        "name": "Retina",
                        "created_at": "2026-06-06T03:30:00Z",
                    }
                ],
            )
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    repo = SupabaseVariantLibraryRepo(
        supabase_url="https://cpdjxsgasaesysvxkpmi.supabase.co",
        service_role_key="service-role-key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    folder = repo.create_folder(
        user_id="23fc93e9-d351-4a9f-b5a7-f23dd7ceab11",
        name="Retina",
    )

    assert folder.id == "a8ff9c92-84b6-4d6a-b26e-f236c87d4c86"
    assert folder.created_at == datetime(2026, 6, 6, 3, 30, tzinfo=timezone.utc)
    assert [request.method for request in requests] == ["GET", "POST"]


def test_supabase_variant_library_popularity_uses_service_role_rpc() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content.decode("utf-8"))
        assert body == {"p_query_id": "ush2a c.2276g>t"}
        return httpx.Response(
            status_code=200,
            json=[
                {
                    "query_id": "ush2a c.2276g>t",
                    "view_count": 3,
                    "last_viewed": "2026-06-06T03:31:00Z",
                }
            ],
        )

    repo = SupabaseVariantLibraryRepo(
        supabase_url="https://cpdjxsgasaesysvxkpmi.supabase.co",
        service_role_key="service-role-key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = repo.record_view(query_id="ush2a c.2276g>t")

    assert result.view_count == 3
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == (
        "https://cpdjxsgasaesysvxkpmi.supabase.co/rest/v1/" "rpc/increment_variant_view_count"
    )
    assert request.headers["authorization"] == "Bearer service-role-key"
