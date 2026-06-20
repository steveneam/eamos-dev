from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.chat import (
    ChatRequest,
    PaperCandidateContext,
    PaperContext,
    WorkbenchContext,
)
from app.schemas.run import ReportPayload, VariantSummaryRow
from app.services.ai_gateway.retrieval import RetrievedLiterature
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


def _workbench_payload(question: str = "Pick the safest primer pair.") -> ChatRequest:
    # A report-less, Workbench-scoped request: no variant_context, just the
    # active-tool context the /workbench rail carries.
    return ChatRequest(
        question=question,
        workbench=WorkbenchContext(active_tool="primer", selected_primer_pair=2),
    )


def _paper_payload(
    question: str = "Which mentions resolved to a clinical allele?",
) -> ChatRequest:
    # A report-less, Paper-scoped request: no variant_context, just this paper's
    # resolved candidates + source provenance (spec §8).
    return ChatRequest(
        question=question,
        paper=PaperContext(
            source_count=1,
            sources=["Smith · 2021"],
            candidates=[
                PaperCandidateContext(
                    gene="RPE65",
                    hgvs="NM_000329.3:c.260A>G",
                    level="cdna",
                    context="clinical_allele",
                    validation_status="resolved",
                    validated=True,
                    evidence_quote="The proband was homozygous for the RPE65 c.260A>G allele.",
                    source_support=["VariantValidator", "ClinVar"],
                    papers=["Smith · 2021"],
                ),
                PaperCandidateContext(
                    gene="RPE65",
                    hgvs="p.(His241Ala)",
                    level="protein",
                    context="experimental_construct",
                    validation_status="experimental_construct",
                    evidence_quote="We engineered the RPE65 p.His241Ala substitution by site-directed mutagenesis.",
                ),
            ],
        ),
    )


def test_chat_request_requires_a_scoped_context() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(question="Tell me anything.")


def test_chat_request_rejects_oversized_history_before_context_building() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(
            question="What does the current evidence show?",
            variant_context=ReportPayload(patient_id="lookup-test"),
            history=[{"role": "user", "content": f"turn {idx}"} for idx in range(25)],
        )


def test_report_payload_rejects_oversized_variant_summary_rows() -> None:
    with pytest.raises(ValidationError):
        ReportPayload(
            patient_id="lookup-test",
            variant_summary_rows=[VariantSummaryRow(gene=f"GENE{idx}") for idx in range(101)],
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


def test_workbench_only_mock_answer_has_no_variant() -> None:
    service = ChatService(settings=_settings("mock"), llm_client=None)

    response = service.respond(_workbench_payload("Explain this primer design."))

    assert (
        response.answer
        == "[mock] Asked about this variant in primer mode: Explain this primer design."
    )


def test_workbench_only_chat_builds_tool_scoped_context() -> None:
    chain = FakeLookupChatChain()
    service = ChatService(settings=_settings(), llm_client=chain)

    service.respond(_workbench_payload())

    sent = chain.payloads[0]["bounded_context"]
    context = json.loads(sent)
    # Scoped to the Workbench tool only — no report-derived evidence blocks.
    assert context["workbench"]["active_tool"] == "primer"
    assert context["workbench"]["selected_primer_pair"] == 2
    assert "variant_summary_rows" not in context
    assert "call_cards" not in context
    assert "patient_id" not in sent


def test_workbench_only_chat_skips_literature_retrieval() -> None:
    retriever = FakeRetriever([_hit()])
    chain = FakeLookupChatChain()
    service = ChatService(
        settings=_settings("gateway"), llm_client=chain, literature_retriever=retriever
    )

    service.respond(_workbench_payload())

    # No report payload → no genes → retrieval is never attempted.
    assert retriever.calls == []
    context = json.loads(chain.payloads[0]["bounded_context"])
    assert "retrieved_literature" not in context


def test_chat_request_accepts_paper_only_context() -> None:
    # The /paper surface grounds the chat in this paper's resolved candidates,
    # no report payload — the scoped-context validator must accept it.
    payload = _paper_payload()

    assert payload.variant_context is None
    assert payload.workbench is None
    assert payload.paper is not None
    assert payload.paper.candidates[0].gene == "RPE65"


def test_paper_only_mock_answer_names_paper_mode() -> None:
    service = ChatService(settings=_settings("mock"), llm_client=None)

    response = service.respond(_paper_payload("Which are experimental constructs?"))

    assert (
        response.answer
        == "[mock] Asked about RPE65 in paper mode: Which are experimental constructs?"
    )


def test_paper_only_chat_builds_paper_scoped_context() -> None:
    chain = FakeLookupChatChain()
    service = ChatService(settings=_settings(), llm_client=chain)

    service.respond(_paper_payload())

    sent = chain.payloads[0]["bounded_context"]
    context = json.loads(sent)
    # Scoped to the paper's resolved candidates only — no report-derived blocks.
    assert context["paper"]["source_count"] == 1
    assert context["paper"]["candidates"][0]["gene"] == "RPE65"
    assert context["paper"]["candidates"][0]["context"] == "clinical_allele"
    assert context["paper"]["candidates"][1]["validation_status"] == "experimental_construct"
    assert "variant_summary_rows" not in context
    assert "call_cards" not in context
    assert context["workbench"] is None
    assert "patient_id" not in sent


def test_paper_only_chat_skips_literature_retrieval() -> None:
    retriever = FakeRetriever([_hit()])
    chain = FakeLookupChatChain()
    service = ChatService(
        settings=_settings("gateway"), llm_client=chain, literature_retriever=retriever
    )

    service.respond(_paper_payload())

    # No report payload → no genes → retrieval is never attempted.
    assert retriever.calls == []
    context = json.loads(chain.payloads[0]["bounded_context"])
    assert "retrieved_literature" not in context


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
        registration = client.post(
            "/api/v1/auth/register",
            json={"username": "route-chat-user", "password": "route-password"},
        )
        assert registration.status_code == 201
        token = registration.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})

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


# --- literature RAG wiring (docs/ai-gateway-rag/spec.md) -------------------


class FakeRetriever:
    def __init__(self, hits: list[RetrievedLiterature]) -> None:
        self.hits = hits
        self.calls: list[tuple[str, list[str]]] = []

    def retrieve(self, question: str, genes) -> list[RetrievedLiterature]:
        self.calls.append((question, list(genes)))
        return self.hits


def _hit() -> RetrievedLiterature:
    return RetrievedLiterature(
        pmid="35901234",
        title="RPE65 functional study",
        snippet="RPE65 loss-of-function reduces isomerohydrolase activity.",
        year=2022,
        source_url="https://pubmed.ncbi.nlm.nih.gov/35901234/",
        score=0.83,
    )


def test_gateway_chat_injects_retrieved_literature_into_bounded_context() -> None:
    retriever = FakeRetriever([_hit()])
    chain = FakeLookupChatChain()
    service = ChatService(
        settings=_settings("gateway"), llm_client=chain, literature_retriever=retriever
    )

    service.respond(_chat_payload())

    assert retriever.calls[0] == ("What does the current evidence show?", ["RPE65"])
    context = json.loads(chain.payloads[0]["bounded_context"])
    assert context["retrieved_literature"][0]["pmid"] == "35901234"
    assert context["retrieved_literature"][0]["snippet"].startswith("RPE65 loss-of-function")
    # still PHI-clean despite the new block
    assert "patient_id" not in chain.payloads[0]["bounded_context"]


def test_no_retrieved_literature_key_when_retriever_returns_nothing() -> None:
    retriever = FakeRetriever([])
    chain = FakeLookupChatChain()
    service = ChatService(
        settings=_settings("gateway"), llm_client=chain, literature_retriever=retriever
    )

    service.respond(_chat_payload())

    context = json.loads(chain.payloads[0]["bounded_context"])
    assert "retrieved_literature" not in context


def test_mock_provider_skips_retrieval_entirely() -> None:
    retriever = FakeRetriever([_hit()])
    service = ChatService(
        settings=_settings("mock"), llm_client=None, literature_retriever=retriever
    )

    service.respond(_chat_payload())

    assert retriever.calls == []  # mock path never builds the bounded context
