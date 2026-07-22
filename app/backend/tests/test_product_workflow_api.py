from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event

import httpx
import pytest
from fastapi import Response
from starlette.requests import Request

from app.api.routes.batch import _tsv_line
from app.api.routes.paper_variants import extract_paper_variants
from app.core.deps import AuthenticatedPrincipal
from app.repos.product_workflow_repo import (
    ProductWorkflowRunRecord,
    SupabaseProductWorkflowRepo,
    UnsafeWorkflowPayloadError,
    _encode_item_cursor,
    _encode_run_cursor,
)
from app.services.batch import BatchService
from app.services.panels import PanelService


def _register_headers(client, username: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "test-password"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _batch_variant(index: int) -> dict:
    return {
        "query": f"1-{100 + index}-A-C",
        "chrom": "1",
        "pos": 100 + index,
        "ref": "A",
        "alt": "C",
        "gene": "RPE65",
        "variant": f"c.{index + 1}A>C",
        "filter": "PASS",
    }


def _wait_for_batch(client, run_id: str, *, headers: dict[str, str] | None = None) -> dict:
    deadline = time.monotonic() + 5
    last: dict | None = None
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/batch/{run_id}?limit=100", headers=headers)
        assert response.status_code == 200
        last = response.json()
        if last["status"] in {"completed", "failed", "cancelled"}:
            return last
        time.sleep(0.02)
    raise AssertionError(f"batch workflow did not finish: {last}")


def test_batch_workflow_is_durable_paged_exportable_and_owner_scoped(
    auth_client,
    tmp_path: Path,
) -> None:
    created = auth_client.post(
        "/api/v1/batch",
        json={"variants": [_batch_variant(index) for index in range(3)]},
    )
    assert created.status_code == 200
    run_id = created.json()["job_id"]
    completed = _wait_for_batch(auth_client, run_id)
    assert completed["status"] == "completed"
    assert completed["done"] == completed["total"] == 3

    first_page = auth_client.get(f"/api/v1/batch/{run_id}?limit=2")
    assert first_page.status_code == 200
    first_body = first_page.json()
    assert len(first_body["results"]) == 2
    assert first_body["page"]["total"] == 3
    assert first_body["page"]["next_cursor"]
    second_page = auth_client.get(
        f"/api/v1/batch/{run_id}",
        params={"limit": 2, "cursor": first_body["page"]["next_cursor"]},
    )
    assert second_page.status_code == 200
    assert len(second_page.json()["results"]) == 1
    assert second_page.json()["page"]["total"] == 3
    invalid_page = auth_client.get(
        f"/api/v1/batch/{run_id}",
        params={"cursor": "%%%"},
    )
    assert invalid_page.status_code == 422

    owner_user_id = _current_user_id(auth_client)
    workflow = auth_client.app.state.product_workflow_service
    for suffix in ("history-a", "history-b"):
        workflow.create_run(
            kind="batch",
            run_id=f"batch-{suffix}",
            user_id=owner_user_id,
            owner_provider="eamos",
            status="draft",
        )
    history = auth_client.get("/api/v1/batch/runs?limit=2")
    assert history.status_code == 200
    assert history.headers["X-Total-Count"] == "3"
    assert len(history.json()) == 2
    assert history.headers["X-Next-Cursor"]
    history_tail = auth_client.get(
        "/api/v1/batch/runs",
        params={"limit": 2, "cursor": history.headers["X-Next-Cursor"]},
    )
    assert history_tail.status_code == 200
    assert history_tail.headers["X-Total-Count"] == "3"
    assert len(history_tail.json()) == 1
    assert {item["run_id"] for item in [*history.json(), *history_tail.json()]} == {
        run_id,
        "batch-history-a",
        "batch-history-b",
    }

    tsv = auth_client.get(f"/api/v1/batch/{run_id}/export?format=tsv")
    manifest = auth_client.get(f"/api/v1/batch/{run_id}/export?format=manifest")
    assert tsv.status_code == 200
    assert tsv.text.count("\n") == 4
    assert "/report?gene=RPE65&cdna=" in tsv.text
    assert manifest.status_code == 200
    assert manifest.json()["raw_input_included"] is False
    assert manifest.json()["result_count"] == 3

    # A fresh in-memory BatchService must reconstruct the result from the
    # durable workflow ledger rather than its process-local registry.
    auth_client.app.state.batch_service = BatchService(
        upload_dir=tmp_path / "restarted-uploads",
        panel_service=PanelService(),
        workflow_service=auth_client.app.state.product_workflow_service,
    )
    restarted = auth_client.get(f"/api/v1/batch/{run_id}?limit=100")
    assert restarted.status_code == 200
    assert restarted.json()["results"] == completed["results"]

    other_headers = _register_headers(auth_client, "workflow-batch-other")
    assert auth_client.get(f"/api/v1/batch/{run_id}", headers=other_headers).status_code == 404
    assert (
        auth_client.post(f"/api/v1/batch/{run_id}/cancel", headers=other_headers).status_code == 404
    )
    assert (
        auth_client.get(f"/api/v1/batch/{run_id}/export", headers=other_headers).status_code == 404
    )
    assert auth_client.delete(f"/api/v1/batch/{run_id}", headers=other_headers).status_code == 404
    other_history = auth_client.get("/api/v1/batch/runs", headers=other_headers)
    assert other_history.status_code == 200
    assert other_history.json() == []
    assert other_history.headers["X-Total-Count"] == "0"

    assert auth_client.delete(f"/api/v1/batch/{run_id}").status_code == 204
    assert auth_client.get(f"/api/v1/batch/{run_id}").status_code == 404
    assert auth_client.get(f"/api/v1/batch/{run_id}/export").status_code == 404


def test_batch_upload_never_writes_plaintext_snapshot(auth_client) -> None:
    secret_marker = "EAMOS_RAW_VCF_MUST_NOT_PERSIST"
    vcf = (
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        f"1\t100\t.\tA\tC\t.\tPASS\tGENE=RPE65;NOTE={secret_marker}\n"
    )
    upload = auth_client.post(
        "/api/v1/batch/uploads",
        files={"file": ("private-sample.vcf", vcf, "text/plain")},
    )
    assert upload.status_code == 200
    upload_root = Path(auth_client.app.state.settings.upload_dir)
    persisted_files = [path for path in upload_root.rglob("*") if path.is_file()]
    assert persisted_files == []

    created = auth_client.post(
        "/api/v1/batch",
        json={"upload_ref": upload.json()["upload_ref"]},
    )
    assert created.status_code == 200
    assert (
        auth_client.post(
            "/api/v1/batch",
            json={"upload_ref": upload.json()["upload_ref"]},
        ).status_code
        == 404
    )
    result = _wait_for_batch(auth_client, created.json()["job_id"])
    assert secret_marker not in json.dumps(result)


def test_batch_cancel_is_owner_scoped_and_remains_terminal(auth_client, tmp_path: Path) -> None:
    class SlowLookup:
        def lookup(self, request, refresh: bool = False):  # noqa: ARG002
            time.sleep(0.25)
            raise RuntimeError("bounded slow lookup")

    auth_client.app.state.batch_service = BatchService(
        upload_dir=tmp_path / "cancel-uploads",
        panel_service=PanelService(),
        lookup_service=SlowLookup(),
        max_lookup_workers=1,
        workflow_service=auth_client.app.state.product_workflow_service,
    )
    created = auth_client.post(
        "/api/v1/batch",
        json={"variants": [_batch_variant(index) for index in range(3)]},
    )
    assert created.status_code == 200
    run_id = created.json()["job_id"]

    cancelled = auth_client.post(f"/api/v1/batch/{run_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    time.sleep(0.35)
    assert auth_client.get(f"/api/v1/batch/{run_id}").json()["status"] == "cancelled"


def test_paper_workflow_disclosure_result_history_and_owner_isolation(auth_client) -> None:
    disclosure = auth_client.get("/api/v1/paper-variants/disclosure?input_class=paper_text")
    assert disclosure.status_code == 200
    assert disclosure.json()["raw_input_persisted"] is False
    assert disclosure.json()["retention"] == "request_lifetime"

    raw_text = "RPE65 c.260A>G was identified in a patient. PRIVATE_RAW_SENTENCE"
    extracted = auth_client.post(
        "/api/v1/paper-variants/extract",
        json={"text": raw_text},
    )
    assert extracted.status_code == 200
    run_id = extracted.headers["X-Workflow-Run-Id"]
    assert raw_text not in extracted.text

    run = auth_client.get(f"/api/v1/paper-variants/runs/{run_id}")
    result = auth_client.get(f"/api/v1/paper-variants/runs/{run_id}/result")
    history = auth_client.get("/api/v1/paper-variants/runs?limit=1")
    assert run.status_code == 200
    assert run.json()["status"] == "completed"
    assert run.json()["processing_disclosure"]["raw_input_persisted"] is False
    assert result.status_code == 200
    assert raw_text not in result.text
    assert all(variant["evidence_quote"] is None for variant in result.json()["variants"])
    assert history.status_code == 200
    assert history.headers["X-Total-Count"] == "1"
    assert history.json()[0]["run_id"] == run_id

    record = auth_client.app.state.product_workflow_service.get_record(
        run_id=run_id,
        user_id=_current_user_id(auth_client),
        owner_provider="eamos",
    )
    assert record is not None
    assert raw_text not in json.dumps(record.result_payload)
    assert "evidence_quote" not in json.dumps(record.result_payload)

    other_headers = _register_headers(auth_client, "workflow-paper-other")
    for suffix in ("", "/result"):
        assert (
            auth_client.get(
                f"/api/v1/paper-variants/runs/{run_id}{suffix}",
                headers=other_headers,
            ).status_code
            == 404
        )
    assert (
        auth_client.post(
            f"/api/v1/paper-variants/runs/{run_id}/cancel",
            headers=other_headers,
        ).status_code
        == 404
    )
    assert (
        auth_client.delete(
            f"/api/v1/paper-variants/runs/{run_id}",
            headers=other_headers,
        ).status_code
        == 404
    )
    assert auth_client.delete(f"/api/v1/paper-variants/runs/{run_id}").status_code == 204
    assert auth_client.get(f"/api/v1/paper-variants/runs/{run_id}").status_code == 404


def test_paper_deterministic_route_stays_local_under_gateway_config(auth_client) -> None:
    auth_client.app.state.settings.llm_provider = "gateway"

    disclosure = auth_client.get("/api/v1/paper-variants/disclosure?input_class=pdf")
    assert disclosure.status_code == 200
    assert disclosure.json()["execution"] == "eamos_backend"
    assert disclosure.json()["provider_id"] == "eamos_deterministic_extractor"
    assert disclosure.json()["consent_required"] is False

    response = auth_client.post(
        "/api/v1/paper-variants/extract",
        content=b"this is deliberately not JSON",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Request body must be valid JSON."
    assert auth_client.get("/api/v1/paper-variants/runs").json() == []


def test_paper_validation_error_does_not_echo_raw_input(auth_client) -> None:
    marker = "PRIVATE_PAPER_VALIDATION_MARKER"
    response = auth_client.post(
        "/api/v1/paper-variants/extract",
        json={"text": marker + ("x" * 1_000_000)},
    )

    assert response.status_code == 422
    assert marker not in response.text
    assert len(response.content) < 2_000


def test_workbench_workspace_is_durable_owner_scoped_and_trace_requires_auth(
    auth_client,
) -> None:
    context = {
        "schema_version": "workflow_context.v1",
        "context_id": None,
        "variant": None,
        "origin_surface": "workbench",
        "return_to": "/workbench?view=window",
        "batch_run_id": None,
        "paper_run_id": None,
        "workspace_id": None,
        "active_tool": None,
        "selection": None,
        "created_at": datetime.now(UTC).isoformat(),
        "expires_at": None,
    }
    created = auth_client.post("/api/v1/workbench/workspaces", json=context)
    assert created.status_code == 200
    workspace_id = created.json()["run_id"]
    assert created.json()["context"]["workspace_id"] == workspace_id

    fetched = auth_client.get(f"/api/v1/workbench/workspaces/{workspace_id}")
    assert fetched.status_code == 200
    assert fetched.json() == created.json()
    disclosure = auth_client.get("/api/v1/workbench/trace-disclosure")
    assert disclosure.status_code == 200
    assert disclosure.json()["raw_input_persisted"] is False
    assert disclosure.json()["input_classes"] == ["trace"]

    other_headers = _register_headers(auth_client, "workflow-workbench-other")
    assert (
        auth_client.get(
            f"/api/v1/workbench/workspaces/{workspace_id}",
            headers=other_headers,
        ).status_code
        == 404
    )
    assert (
        auth_client.delete(
            f"/api/v1/workbench/workspaces/{workspace_id}",
            headers=other_headers,
        ).status_code
        == 404
    )
    assert auth_client.delete(f"/api/v1/workbench/workspaces/{workspace_id}").status_code == 204

    auth_client.headers.pop("Authorization")
    assert auth_client.get("/api/v1/workbench/trace-disclosure").status_code == 401
    assert auth_client.post("/api/v1/align/trace", json={}).status_code == 401
    assert auth_client.post("/api/v1/crispr/tide?cut_site_index=1").status_code == 401


def test_crispr_offtarget_requires_explicit_grch38_on_target_locus(auth_client) -> None:
    missing = auth_client.post(
        "/api/v1/crispr/offtargets",
        json={"guide": "GAGTCCGAGCAGAAGAAGAT"},
    )
    wrong_build = auth_client.post(
        "/api/v1/crispr/offtargets",
        json={
            "guide": "GAGTCCGAGCAGAAGAAGAT",
            "genome_build": "GRCh37",
            "on_target_locus": {"chromosome": "7", "position": 117509080, "strand": "+"},
        },
    )
    assert missing.status_code == 422
    assert "on_target_locus" in missing.json()["detail"]["code"]
    assert wrong_build.status_code == 422
    assert "genome_build" in wrong_build.json()["detail"]["code"]


def test_workflow_kind_routes_cannot_mutate_another_kind(auth_client) -> None:
    workflow = auth_client.app.state.product_workflow_service
    user_id = _current_user_id(auth_client)
    paper = workflow.create_run(
        kind="paper",
        user_id=user_id,
        owner_provider="eamos",
        status="running",
        total=1,
    )
    batch = workflow.create_run(
        kind="batch",
        user_id=user_id,
        owner_provider="eamos",
        status="draft",
    )

    assert auth_client.post(f"/api/v1/batch/{paper.run_id}/cancel").status_code == 404
    assert auth_client.delete(f"/api/v1/batch/{paper.run_id}").status_code == 404
    assert auth_client.post(f"/api/v1/paper-variants/runs/{batch.run_id}/cancel").status_code == 404
    assert auth_client.delete(f"/api/v1/paper-variants/runs/{batch.run_id}").status_code == 404
    assert (
        workflow.get_run(
            run_id=paper.run_id,
            user_id=user_id,
            owner_provider="eamos",
        ).status
        == "running"
    )
    assert (
        workflow.get_run(
            run_id=batch.run_id,
            user_id=user_id,
            owner_provider="eamos",
        ).status
        == "draft"
    )


def test_cancelled_paper_run_cannot_be_overwritten_by_late_result(auth_client) -> None:
    workflow = auth_client.app.state.product_workflow_service
    user_id = _current_user_id(auth_client)
    run = workflow.create_run(
        kind="paper",
        user_id=user_id,
        owner_provider="eamos",
        status="running",
        total=1,
    )
    cancelled = auth_client.post(f"/api/v1/paper-variants/runs/{run.run_id}/cancel")
    assert cancelled.status_code == 200

    late = workflow.update_run(
        run_id=run.run_id,
        user_id=user_id,
        owner_provider="eamos",
        status="completed",
        done=1,
        total=1,
        result_payload={"candidate_count": 1},
    )
    record = workflow.get_record(
        run_id=run.run_id,
        user_id=user_id,
        owner_provider="eamos",
    )
    assert late is not None
    assert late.status == "cancelled"
    assert record is not None
    assert record.status == "cancelled"
    assert record.result_payload is None


def test_aborted_paper_request_marks_its_durable_run_cancelled(
    auth_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = Event()
    release = Event()

    def slow_extract(_service, _text: str, *, validate: bool = True):  # noqa: ARG001
        started.set()
        release.wait(timeout=2)
        raise AssertionError("cancelled request must not resume response handling")

    monkeypatch.setattr("app.api.routes.paper_variants.PaperVariantsService.extract", slow_extract)
    body = json.dumps({"text": "RPE65 c.260A>G in a publication."}).encode("utf-8")
    delivered = False

    async def receive() -> dict:
        nonlocal delivered
        if not delivered:
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    request = Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/paper-variants/extract",
            "raw_path": b"/api/v1/paper-variants/extract",
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "app": auth_client.app,
        },
        receive,
    )
    user_id = _current_user_id(auth_client)
    principal = AuthenticatedPrincipal(
        user_id=user_id,
        provider="eamos",
        token="test-token",
    )
    workflow = auth_client.app.state.product_workflow_service

    async def cancel_mid_request() -> str:
        task = asyncio.create_task(extract_paper_variants(request, Response(), principal))
        for _ in range(100):
            if started.is_set():
                break
            await asyncio.sleep(0.01)
        assert started.is_set()
        records, _cursor, total = workflow.repo.list_runs(
            user_id=user_id,
            owner_provider="eamos",
            kind="paper",
            limit=10,
            cursor=None,
        )
        assert total == 1
        run_id = records[0].run_id
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return run_id

    try:
        run_id = asyncio.run(cancel_mid_request())
    finally:
        release.set()

    record = workflow.repo.get_run(
        run_id=run_id,
        user_id=user_id,
        owner_provider="eamos",
    )
    assert record is not None
    assert record.status == "cancelled"


def test_related_and_curated_variant_contracts_are_backend_derived(auth_client) -> None:
    related = auth_client.get(
        "/api/v1/lookup/related",
        params={"gene": "RPE65", "cdna": "c.260A>G", "transcript": "NM_000329.3"},
    )
    curated = auth_client.get(
        "/api/v1/lookup/curated",
        params={"gene": "RPE65", "limit": 1},
    )
    invalid_cursor = auth_client.get(
        "/api/v1/lookup/curated",
        params={"gene": "RPE65", "cursor": "%%%"},
    )

    assert related.status_code == 200
    assert related.json()["warnings"] == ["related_variants_fixture_scope"]
    for item in related.json()["items"]:
        assert item["variant"]["gene"] == "RPE65"
        assert item["report_href"].startswith("/report?gene=RPE65&cdna=")
        assert item["source_disclosure"]["source_status"] == "fixture"
    assert curated.status_code == 200
    assert curated.json()["gene"] == "RPE65"
    assert curated.json()["source_disclosure"]["source_status"] in {
        "fixture",
        "source_backed",
        "unavailable",
    }
    assert invalid_cursor.status_code == 422


def test_workflow_repo_rejects_raw_durable_payload(auth_client) -> None:
    with pytest.raises(UnsafeWorkflowPayloadError):
        auth_client.app.state.product_workflow_service.create_run(
            kind="paper",
            user_id=_current_user_id(auth_client),
            owner_provider="eamos",
            status="running",
            total=1,
            result_payload={"paper_text": "must never persist"},
        )


def test_expired_workflows_and_items_are_purged_before_read(auth_client) -> None:
    now = datetime.now(UTC)
    created_at = now - timedelta(days=2)
    expires_at = now - timedelta(days=1)
    run_id = "workbench-expired-test"
    user_id = _current_user_id(auth_client)
    repo = auth_client.app.state.product_workflow_repo
    workflow = auth_client.app.state.product_workflow_service
    repo.create_run(
        ProductWorkflowRunRecord(
            run_id=run_id,
            user_id=user_id,
            owner_provider="eamos",
            kind="workbench",
            status="completed",
            owner_scope="account",
            context={
                "schema_version": "workflow_context.v1",
                "context_id": run_id,
                "variant": None,
                "origin_surface": "workbench",
                "return_to": f"/workbench?context_id={run_id}",
                "batch_run_id": None,
                "paper_run_id": None,
                "workspace_id": run_id,
                "active_tool": None,
                "selection": None,
                "created_at": created_at.isoformat(),
                "expires_at": expires_at.isoformat(),
            },
            done=1,
            total=1,
            warnings=[],
            source_disclosures=[],
            processing_disclosure=None,
            artifacts=[],
            result_payload={"summary": "safe durable result"},
            created_at=created_at,
            updated_at=created_at,
            expires_at=expires_at,
        )
    )
    repo.replace_items(
        run_id=run_id,
        user_id=user_id,
        owner_provider="eamos",
        items=[{"query": "1-100-A-C"}],
    )

    workflow._last_expiry_sweep = 0.0
    assert (
        workflow.get_record(
            run_id=run_id,
            user_id=user_id,
            owner_provider="eamos",
        )
        is None
    )
    assert repo.page_items(
        run_id=run_id,
        user_id=user_id,
        owner_provider="eamos",
        limit=10,
        cursor=None,
    ) == ([], None, 0)


def test_batch_tsv_export_neutralizes_spreadsheet_formulas() -> None:
    assert _tsv_line(["=1+1", "+cmd", "-2", "@payload"]) == ("'=1+1\t'+cmd\t'-2\t'@payload\n")


def test_supabase_workflow_repo_applies_owner_filters_and_keeps_service_key_server_only() -> None:
    requests: list[httpx.Request] = []
    service_key = "test-key"

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status_code=200, json=[], headers={"Content-Range": "*/0"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    repo = SupabaseProductWorkflowRepo(
        supabase_url="https://cpdjxsgasaesysvxkpmi.supabase.co",
        service_role_key=service_key,
        http_client=client,
    )
    owner = {
        "run_id": "batch-test",
        "user_id": "23fc93e9-d351-4a9f-b5a7-f23dd7ceab11",
        "owner_provider": "supabase",
    }
    assert repo.get_run(**owner) is None
    assert repo.update_run(**owner, changes={"status": "cancelled"}) is None
    assert repo.delete_run(**owner) is False
    assert repo.page_items(**owner, limit=10, cursor=None) == ([], None, 0)
    assert repo.list_runs(
        user_id=owner["user_id"],
        owner_provider=owner["owner_provider"],
        kind="batch",
        limit=10,
        cursor=None,
    ) == ([], None, 0)

    assert len(requests) == 5
    for request in requests:
        assert f"user_id=eq.{owner['user_id']}" in str(request.url)
        assert "owner_provider=eq.supabase" in str(request.url)
        assert request.headers["apikey"] == service_key
        assert request.headers["authorization"] == f"Bearer {service_key}"
        assert service_key not in request.content.decode("utf-8")


def test_supabase_workflow_create_serializes_timestamps_and_server_owner() -> None:
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        captured.append(body)
        return httpx.Response(status_code=201, json=[body])

    repo = SupabaseProductWorkflowRepo(
        supabase_url="https://cpdjxsgasaesysvxkpmi.supabase.co",
        service_role_key="service-role-key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    now = datetime.now(UTC)
    record = ProductWorkflowRunRecord(
        run_id="paper-test",
        user_id="23fc93e9-d351-4a9f-b5a7-f23dd7ceab11",
        owner_provider="supabase",
        kind="paper",
        status="running",
        owner_scope="account",
        context={"schema_version": "workflow_context.v1"},
        done=0,
        total=1,
        warnings=[],
        source_disclosures=[],
        processing_disclosure=None,
        artifacts=[],
        result_payload=None,
        created_at=now,
        updated_at=now,
        expires_at=None,
    )
    created = repo.create_run(record)

    assert created.user_id == record.user_id
    assert captured[0]["user_id"] == record.user_id
    assert captured[0]["owner_provider"] == "supabase"
    assert captured[0]["created_at"].endswith("+00:00")


def test_supabase_workflow_cursor_pages_report_unfiltered_owner_total() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        url = str(request.url)
        if "product_workflow_run" in url:
            total = 1 if "or=" in url else 7
        else:
            total = 1 if "position=gt." in url else 5
        return httpx.Response(
            status_code=200,
            json=[],
            headers={"Content-Range": f"*/{total}"},
        )

    repo = SupabaseProductWorkflowRepo(
        supabase_url="https://cpdjxsgasaesysvxkpmi.supabase.co",
        service_role_key="service-role-key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    user_id = "23fc93e9-d351-4a9f-b5a7-f23dd7ceab11"
    runs = repo.list_runs(
        user_id=user_id,
        owner_provider="supabase",
        kind="batch",
        limit=2,
        cursor=_encode_run_cursor(datetime.now(UTC), "batch-cursor"),
    )
    items = repo.page_items(
        run_id="batch-cursor",
        user_id=user_id,
        owner_provider="supabase",
        limit=2,
        cursor=_encode_item_cursor(1),
    )

    assert runs == ([], None, 7)
    assert items == ([], None, 5)
    assert len(requests) == 4
    assert all(f"user_id=eq.{user_id}" in str(request.url) for request in requests)


def _current_user_id(client) -> str:
    token = client.headers["Authorization"].removeprefix("Bearer ")
    return client.app.state.auth_service.get_current_user(token).user_id
