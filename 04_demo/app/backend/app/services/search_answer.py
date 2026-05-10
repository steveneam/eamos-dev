from __future__ import annotations

import json

from fastapi import HTTPException, status

from app.schemas.search import (
    SearchAnswerRequest,
    SearchAnswerResponse,
    SearchCitation,
)


class SearchAnswerService:
    def __init__(self, settings, search_service, answer_chain=None) -> None:
        self.settings = settings
        self.search_service = search_service
        self.answer_chain = answer_chain

    def answer(self, payload: SearchAnswerRequest) -> SearchAnswerResponse:
        if not self.settings.search_answer_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI search answers are disabled.",
            )
        if self.answer_chain is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI search answer model is not configured.",
            )

        top_k = min(payload.limit, self.settings.search_answer_top_k)
        results = self.search_service.search(
            query=payload.query,
            limit=top_k,
            doc_type=payload.doc_type,
            run_status=payload.run_status,
            review_status=payload.review_status,
        )
        if not results.results:
            return SearchAnswerResponse(
                query=payload.query,
                answer="I couldn't find a confident matching run or report.",
                grounded=False,
                citations=[],
                results=[],
            )

        context = [
            {
                "rank": idx,
                "doc_type": item.doc_type,
                "run_id": item.run_id,
                "report_id": item.report_id,
                "patient_id": item.patient_id,
                "title": item.title,
                "snippet": item.snippet,
                "run_status": item.run_status,
                "review_status": item.review_status,
                "extraction_status": item.extraction_status,
                "match_type": item.match_type,
                "score": round(item.score, 4),
            }
            for idx, item in enumerate(results.results[:top_k], start=1)
        ]
        model_output = self.answer_chain.invoke(
            {
                "query": payload.query,
                "results_context": json.dumps(context, indent=2),
            }
        )

        citations = []
        allowed_pairs = {
            (item.run_id, item.report_id): item.title for item in results.results
        }
        for item in model_output.get("citations", []):
            citation = SearchCitation.model_validate(item)
            key = (citation.run_id, citation.report_id)
            if key not in allowed_pairs:
                continue
            if citation.title is None:
                citation.title = allowed_pairs[key]
            citations.append(citation)

        return SearchAnswerResponse(
            query=payload.query,
            answer=model_output.get("answer", ""),
            grounded=bool(model_output.get("grounded", True)),
            citations=citations,
            results=results.results,
        )
