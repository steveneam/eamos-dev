from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.schemas.chat import ChatRequest, WorkbenchContext
from app.schemas.run import ReportPayload, VariantSummaryRow
from app.services.chat_service import ChatService


def _settings(provider: str = "openai", tmp_path: Path | None = None) -> Settings:
    kwargs = {
        "jwt_secret": "test-secret",
        "llm_provider": provider,
        "openai_api_key": "sk-test" if provider != "mock" else None,
        "use_real_apis": False,
        "supabase_url": None,
        "supabase_service_role_key": None,
        "supabase_jwt_secret": None,
    }
    if tmp_path is not None:
        kwargs.update(
            {
                "upload_dir": tmp_path / "uploads",
                "final_report_dir": tmp_path / "final_reports",
                "database_url": f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
            }
        )
    return Settings(**kwargs)


def _chat_payload(question: str = "What does the current evidence show?") -> ChatRequest:
    return ChatRequest(
        question=question,
        variant_context=ReportPayload(
            patient_id="sensitive-patient-id",
            patient_context="sensitive patient details should not be sent to lookup chat",
            variant_summary_rows=[
                VariantSummaryRow(
                    gene="RPE65",
                    transcript_hgvs="NM_000329.3:c.260A>G",
                    protein_change="p.Asp87Gly",
                    genomic_hg38="1-68444869-T-C",
                    consequence="missense_variant",
                )
            ],
        ),
        workbench=WorkbenchContext(active_tool="primer"),
    )


class FakeLookupChatChain:
    def __init__(self) -> None:
        self.payloads: list[dict[str, str]] = []

    def invoke(self, payload: dict[str, str]) -> dict[str, str]:
        self.payloads.append(payload)
        return {"answer": "The current bounded context contains RPE65 evidence."}


class CompleteOnlyClient:
    def complete(self, _prompt: str) -> str:
        raise AssertionError("ChatService must not call complete().")


class RaisingChain:
    def invoke(self, _payload: dict[str, str]) -> dict[str, str]:
        raise AssertionError("Unsafe lookup-chat questions should not call the chain.")


def test_mock_chat_response_is_unchanged() -> None:
    service = ChatService(settings=_settings("mock"), llm_client=None)

    response = service.respond(_chat_payload("Explain the Workbench view."))

    assert response.answer == "[mock] Asked about RPE65 in primer mode: Explain the Workbench view."


def test_live_chat_uses_invoke_adapter_with_bounded_context() -> None:
    chain = FakeLookupChatChain()
    service = ChatService(settings=_settings(), llm_client=chain)

    response = service.respond(_chat_payload())

    assert response.answer == "The current bounded context contains RPE65 evidence."
    assert len(chain.payloads) == 1
    sent = chain.payloads[0]
    assert sent["question"] == "What does the current evidence show?"
    context = json.loads(sent["bounded_context"])
    assert context["variant_summary_rows"][0]["gene"] == "RPE65"
    assert context["workbench"]["active_tool"] == "primer"
    assert "patient_id" not in sent["bounded_context"]
    assert "sensitive patient details" not in sent["bounded_context"]


def test_live_chat_rejects_complete_only_clients() -> None:
    service = ChatService(settings=_settings(), llm_client=CompleteOnlyClient())

    with pytest.raises(HTTPException) as exc:
        service.respond(_chat_payload())

    assert exc.value.status_code == 503
    assert exc.value.detail == "Lookup chat model is not configured."


def test_live_chat_blocks_treatment_questions_before_model_call() -> None:
    service = ChatService(settings=_settings(), llm_client=RaisingChain())

    response = service.respond(_chat_payload("What medication should be started?"))

    assert "cannot provide diagnosis, prescribing, or treatment guidance" in response.answer


def test_chat_route_wires_lookup_chat_chain(monkeypatch, tmp_path: Path) -> None:
    import app.main as main

    chain = FakeLookupChatChain()
    monkeypatch.setattr(main, "build_extraction_chain", lambda _settings: None)
    monkeypatch.setattr(main, "build_draft_chain", lambda _settings: None)
    monkeypatch.setattr(main, "build_run_chat_chain", lambda _settings: None)
    monkeypatch.setattr(main, "build_embeddings_model", lambda _settings: None)
    monkeypatch.setattr(main, "build_lookup_chat_chain", lambda _settings: chain)

    app = main.create_app(_settings(tmp_path=tmp_path))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat",
            json={
                "question": "What does the current evidence show?",
                "variant_context": {
                    "patient_id": "route-chat",
                    "variant_summary_rows": [{"gene": "RPE65"}],
                },
            },
        )

    assert response.status_code == 200
    assert response.json()["answer"] == "The current bounded context contains RPE65 evidence."
    assert len(chain.payloads) == 1


class FakeStreamingClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def invoke(self, payload: dict) -> dict:
        self.requests.append(payload)
        return {"answer": "full answer"}

    def stream(self, payload: dict):
        self.requests.append(payload)
        for token in ["Streamed ", "evidence ", "answer."]:
            yield token


def test_respond_stream_uses_native_client_streaming() -> None:
    client = FakeStreamingClient()
    service = ChatService(settings=_settings("gateway"), llm_client=client)

    out = "".join(service.respond_stream(_chat_payload()))

    assert out == "Streamed evidence answer."
    assert client.requests[-1]["question"] == "What does the current evidence show?"
    assert "history" in client.requests[-1]
    assert "bounded_context" in client.requests[-1]


def test_respond_stream_mock_word_chunks() -> None:
    service = ChatService(settings=_settings("mock"), llm_client=None)

    out = "".join(service.respond_stream(_chat_payload("Explain the Workbench view.")))

    assert out.strip() == "[mock] Asked about RPE65 in primer mode: Explain the Workbench view."


def test_respond_stream_blocks_unsupported_before_client() -> None:
    client = FakeStreamingClient()
    service = ChatService(settings=_settings("gateway"), llm_client=client)

    out = "".join(service.respond_stream(_chat_payload("What medication should be started?")))

    assert "cannot provide diagnosis, prescribing, or treatment guidance" in out
    assert client.requests == []  # never reached the model
