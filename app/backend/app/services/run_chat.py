from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from threading import Lock
from typing import Iterator

from fastapi import HTTPException, status
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.ownership import OwnerIdentity
from app.schemas.chat import RunChatCitation, RunChatRequest, RunChatResponse


@dataclass(frozen=True)
class _RunChatIndex:
    vector_store: InMemoryVectorStore
    chunk_count: int


class RunChatService:
    def __init__(
        self, settings, run_repo, reports_repo, answer_chain=None, embeddings=None
    ) -> None:
        self.settings = settings
        self.run_repo = run_repo
        self.reports_repo = reports_repo
        self.answer_chain = answer_chain
        self.embeddings = embeddings
        self._executor = ThreadPoolExecutor(
            max_workers=_positive_int(
                getattr(settings, "run_chat_worker_max_workers", 2),
                default=2,
            ),
            thread_name_prefix="eamos-run-chat",
        )
        self._index_cache: OrderedDict[tuple[str, str], _RunChatIndex] = OrderedDict()
        self._index_cache_lock = Lock()

    def stream(
        self,
        run_id: str,
        payload: RunChatRequest,
        *,
        owner: OwnerIdentity,
    ) -> Iterator[str]:
        # Streaming is text/plain word-chunks of the full answer. Token-level streaming
        # would require switching the underlying answer_chain to .stream(); for now we
        # split the resolved answer into ~12-char windows so the UI shows progressive text.
        result = self.answer(run_id, payload, owner=owner)
        return self._stream_text(result.answer)

    @staticmethod
    def _stream_text(text: str) -> Iterator[str]:
        if not text:
            yield ""
            return
        window = 12
        for i in range(0, len(text), window):
            yield text[i : i + window]

    def answer(
        self,
        run_id: str,
        payload: RunChatRequest,
        *,
        owner: OwnerIdentity,
    ) -> RunChatResponse:
        timeout_seconds = _positive_float(
            getattr(self.settings, "run_chat_timeout_seconds", 10.0),
            default=10.0,
        )
        future = self._executor.submit(self._answer_impl, run_id, payload, owner)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Run chat timed out.",
            ) from exc

    def _answer_impl(
        self,
        run_id: str,
        payload: RunChatRequest,
        owner: OwnerIdentity,
    ) -> RunChatResponse:
        run = self.run_repo.get_run_for_owner(run_id, owner=owner)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
        if self.answer_chain is None or self.embeddings is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Run chat model is not configured.",
            )

        reports = [
            report
            for report_id in run.report_ids
            if (report := self.reports_repo.get_for_owner(report_id, owner=owner)) is not None
        ]
        documents = self._build_documents(run, reports)
        if not documents:
            return RunChatResponse(
                question=payload.question,
                answer="I could not find report content to answer from the current run.",
                grounded=False,
                citations=[],
            )

        content_hash = self._content_hash(run, reports)
        index = self._get_or_build_index(run_id, content_hash, documents)
        retrieved_docs = index.vector_store.similarity_search(
            payload.question, k=self.settings.run_chat_top_k
        )
        retrieved_context = self._serialize_docs(retrieved_docs)
        draft = self.answer_chain.invoke(
            {
                "question": payload.question,
                "retrieved_context": retrieved_context,
            }
        )

        cited_ids = [int(item) for item in draft.get("cited_chunk_ids", []) if str(item).isdigit()]
        citations = self._build_citations(
            retrieved_docs, cited_ids, grounded=bool(draft.get("grounded", True))
        )

        return RunChatResponse(
            question=payload.question,
            answer=draft.get("answer", "").strip(),
            grounded=bool(draft.get("grounded", True)),
            citations=citations,
        )

    def _get_or_build_index(
        self,
        run_id: str,
        content_hash: str,
        documents: list[Document],
    ) -> _RunChatIndex:
        cache_key = (run_id, content_hash)
        with self._index_cache_lock:
            cached = self._index_cache.get(cache_key)
            if cached is not None:
                self._index_cache.move_to_end(cache_key)
                return cached

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=900,
            chunk_overlap=150,
            add_start_index=True,
        )
        chunks = splitter.split_documents(documents)
        max_chunks = _positive_int(getattr(self.settings, "run_chat_max_chunks", 256), default=256)
        if len(chunks) > max_chunks:
            chunks = chunks[:max_chunks]
        for idx, chunk in enumerate(chunks, start=1):
            chunk.metadata["chunk_id"] = idx

        vector_store = InMemoryVectorStore(self.embeddings)
        vector_store.add_documents(chunks)
        index = _RunChatIndex(vector_store=vector_store, chunk_count=len(chunks))

        max_entries = _positive_int(
            getattr(self.settings, "run_chat_vector_cache_max_entries", 32),
            default=32,
        )
        with self._index_cache_lock:
            self._index_cache[cache_key] = index
            self._index_cache.move_to_end(cache_key)
            while len(self._index_cache) > max_entries:
                self._index_cache.popitem(last=False)
        return index

    def _content_hash(self, run, reports) -> str:
        payload = {
            "run": run.model_dump(mode="json"),
            "reports": [report.model_dump(mode="json") for report in reports],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _build_documents(self, run, reports) -> list[Document]:
        docs: list[Document] = []
        title = run.report_payload.report_title or "Current run report"

        def append_doc(
            content: str | None, *, section: str, source_type: str, doc_title: str | None = None
        ) -> None:
            text = (content or "").strip()
            if not text:
                return
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "title": doc_title or title,
                        "section": section,
                        "source_type": source_type,
                    },
                )
            )

        append_doc(
            run.report_payload.patient_context,
            section="Patient and referral context",
            source_type="run_section",
        )
        append_doc(
            run.report_payload.clinical_phenotype,
            section="Relevant clinical findings",
            source_type="run_section",
        )
        append_doc(
            run.report_payload.ai_clinical_summary,
            section="Genomic finding summary",
            source_type="run_section",
        )
        append_doc(
            run.report_payload.expanded_evidence,
            section="Evidence snapshot",
            source_type="run_section",
        )
        append_doc(
            run.report_payload.acmg_classification,
            section="Classification snapshot",
            source_type="run_section",
        )
        append_doc(
            run.report_payload.clinical_integration,
            section="Interpretation for this patient",
            source_type="run_section",
        )
        append_doc(
            run.report_payload.expected_symptoms,
            section="Expected symptoms",
            source_type="run_section",
        )
        append_doc(
            run.report_payload.recommendations,
            section="Recommended next steps",
            source_type="run_section",
        )
        append_doc(
            run.report_payload.limitations,
            section="Limitations and uncertainty",
            source_type="run_section",
        )
        append_doc(run.review_note, section="Clinician review note", source_type="run_section")

        if run.report_payload.variant_summary_rows:
            variant_lines = []
            for item in run.report_payload.variant_summary_rows:
                variant_lines.append(
                    " | ".join(
                        filter(
                            None,
                            [
                                item.gene,
                                item.transcript_hgvs,
                                item.protein_change,
                                item.genomic_hg38,
                                item.consequence or item.variation_type,
                            ],
                        )
                    )
                )
            append_doc(
                "\n".join(variant_lines), section="Variant summary", source_type="run_section"
            )

        if run.warnings:
            append_doc("\n".join(run.warnings), section="Run warnings", source_type="run_section")

        for evidence in run.evidence:
            evidence_lines = [
                f"Source: {evidence.source}",
                f"Status: {evidence.status}",
            ]
            for key, value in evidence.summary.items():
                evidence_lines.append(f"{key}: {value}")
            if evidence.warnings:
                evidence_lines.append(f"Warnings: {', '.join(evidence.warnings)}")
            append_doc(
                "\n".join(evidence_lines),
                section=f"{evidence.source.upper()} evidence",
                source_type="evidence",
                doc_title=evidence.source.upper(),
            )

        for report in reports:
            report_title = report.extracted_case.report_title or report.filename
            append_doc(
                report.extracted_case.patient_context,
                section="Extracted patient context",
                source_type="report_extract",
                doc_title=report_title,
            )
            append_doc(
                report.extracted_case.clinical_findings,
                section="Extracted clinical findings",
                source_type="report_extract",
                doc_title=report_title,
            )
            append_doc(
                report.extracted_case.summary,
                section="Extracted summary",
                source_type="report_extract",
                doc_title=report_title,
            )
            if report.extracted_case.variants:
                variant_text = "\n".join(
                    " | ".join(
                        filter(
                            None,
                            [
                                variant.gene,
                                variant.transcript_hgvs,
                                variant.protein_change,
                                variant.genomic_hg38,
                                variant.consequence or variant.variation_type,
                            ],
                        )
                    )
                    for variant in report.extracted_case.variants
                )
                append_doc(
                    variant_text,
                    section="Extracted variants",
                    source_type="report_extract",
                    doc_title=report_title,
                )
            append_doc(
                report.raw_extracted_text,
                section="Raw extracted text",
                source_type="report_extract",
                doc_title=report_title,
            )

        return docs

    def _serialize_docs(self, docs: list[Document]) -> str:
        parts = []
        for doc in docs:
            chunk_id = doc.metadata.get("chunk_id")
            title = doc.metadata.get("title", "Source")
            section = doc.metadata.get("section", "Context")
            source_type = doc.metadata.get("source_type", "run_section")
            parts.append(
                f"[Chunk {chunk_id}] title={title} | section={section} | source_type={source_type}\n{doc.page_content}"
            )
        return "\n\n".join(parts)

    def _build_citations(
        self, docs: list[Document], cited_ids: list[int], *, grounded: bool
    ) -> list[RunChatCitation]:
        docs_by_id: dict[int, Document] = {}
        docs_by_id_str: dict[str, Document] = {}
        for doc in docs:
            chunk_id = doc.metadata.get("chunk_id")
            if chunk_id is None:
                continue
            chunk_key: int | None = None
            chunk_key_text = str(chunk_id)
            docs_by_id_str[chunk_key_text] = doc
            if isinstance(chunk_id, int):
                chunk_key = chunk_id
            else:
                if isinstance(chunk_id, str) and chunk_id.isdigit():
                    chunk_key = int(chunk_id)
            if chunk_key is not None:
                docs_by_id[chunk_key] = doc

        chosen_ids = cited_ids
        if grounded and not chosen_ids and docs:
            fallback_id = docs[0].metadata.get("chunk_id")
            if isinstance(fallback_id, int):
                chosen_ids = [fallback_id]
            elif isinstance(fallback_id, str) and fallback_id.isdigit():
                chosen_ids = [int(fallback_id)]

        citations: list[RunChatCitation] = []
        for chunk_id in chosen_ids:
            doc = docs_by_id.get(chunk_id)
            if doc is None:
                doc = docs_by_id_str.get(str(chunk_id))
            if doc is None:
                continue
            citations.append(
                RunChatCitation(
                    title=str(doc.metadata.get("title", "Source")),
                    snippet=self._build_snippet(doc.page_content),
                    source_type=str(doc.metadata.get("source_type", "run_section")),
                    section=(
                        str(doc.metadata.get("section"))
                        if doc.metadata.get("section") is not None
                        else None
                    ),
                )
            )

        if grounded and not citations and docs:
            fallback_doc = docs[0]
            citations.append(
                RunChatCitation(
                    title=str(fallback_doc.metadata.get("title", "Source")),
                    snippet=self._build_snippet(fallback_doc.page_content),
                    source_type=str(fallback_doc.metadata.get("source_type", "run_section")),
                    section=(
                        str(fallback_doc.metadata.get("section"))
                        if fallback_doc.metadata.get("section") is not None
                        else None
                    ),
                )
            )

        return citations

    def _build_snippet(self, text: str) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= 220:
            return normalized
        return normalized[:217].rstrip() + "..."


def _positive_int(value, *, default: int) -> int:
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        return default
    return coerced if coerced > 0 else default


def _positive_float(value, *, default: float) -> float:
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return default
    return coerced if coerced > 0 else default
