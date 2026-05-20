"""Field-name parity test between Pydantic models and frontend TS interfaces.

Every Pydantic field on the in-scope models must appear as a key on its
matching ``export interface`` in ``app/frontend/src/lib/backend.ts``.

The check is asymmetric:
- TS may carry extra fields the backend does not declare (view-only state).
- Pydantic fields missing from TS fail the test — that's the contract drift
  the rebuilt frontend cannot tolerate (ReportPage / AIStack read these names).

When this test fails: rename the missing fields in ``backend.ts`` to match the
Pydantic models, then commit both sides together.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.schemas.chat import RunChatRequest, RunChatResponse
from app.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    WorkbenchContext,
    WorkbenchEdit,
)
from app.schemas.lookup import LookupResponse
from app.schemas.run import (
    AcmgCriteriaScaffold,
    AcmgCriterion,
    AssociatedCondition,
    CodonCell,
    CuratedVariantsDistribution,
    EvidenceSourceSummary,
    FunctionalEvidenceSourceBreakdown,
    FunctionalEvidenceSummary,
    FunctionalStudy,
    InSilicoPredictions,
    LocusContext,
    NearbyVariant,
    PredictorCard,
    PublicationLiterature,
    PublicationSnippet,
    PublicationSourceBreakdown,
    PublicationsCallout,
    PubMedArticle,
    ReportPayload,
    VariantSummaryRow,
)
from app.schemas.workbench import (
    AlignRequest,
    AlignResponse,
    CrisprGuide,
    CrisprRequest,
    CrisprResponse,
    HdrSsodn,
    PrimerPair,
    PrimerRequest,
    PrimerResponse,
    TraceChannel,
)

MODEL_TO_TS_INTERFACE: dict[type[BaseModel], str] = {
    LookupResponse: "LookupResponse",
    RunChatRequest: "RunChatRequest",
    RunChatResponse: "RunChatResponse",
    ReportPayload: "ReportPayload",
    EvidenceSourceSummary: "EvidenceSourceSummary",
    VariantSummaryRow: "VariantSummaryRow",
    PubMedArticle: "PubMedArticle",
    LocusContext: "LocusContext",
    NearbyVariant: "NearbyVariant",
    CodonCell: "CodonCell",
    InSilicoPredictions: "InSilicoPredictions",
    PredictorCard: "PredictorCard",
    AcmgCriterion: "AcmgCriterion",
    AcmgCriteriaScaffold: "AcmgCriteriaScaffold",
    CuratedVariantsDistribution: "CuratedVariantsDistribution",
    AssociatedCondition: "AssociatedCondition",
    PublicationsCallout: "PublicationsCallout",
    ChatRequest: "ChatRequest",
    ChatResponse: "ChatResponse",
    ChatMessage: "ChatMessage",
    WorkbenchContext: "WorkbenchContext",
    WorkbenchEdit: "WorkbenchEdit",
    PrimerRequest: "PrimerRequest",
    PrimerResponse: "PrimerResponse",
    PrimerPair: "PrimerPair",
    CrisprRequest: "CrisprRequest",
    CrisprResponse: "CrisprResponse",
    CrisprGuide: "CrisprGuide",
    HdrSsodn: "HdrSsodn",
    AlignRequest: "AlignRequest",
    AlignResponse: "AlignResponse",
    TraceChannel: "TraceChannel",
}


BE6_REPORT_V2_FIELDS: dict[type[BaseModel], set[str]] = {
    CodonCell: {"aa_alt", "dna_ref", "dna_alt"},
    NearbyVariant: {"protein_change"},
    LocusContext: {"coords"},
    PredictorCard: {"verdict_label"},
    AcmgCriteriaScaffold: {"intro", "note"},
    CuratedVariantsDistribution: {"row_totals", "subtitle"},
    AssociatedCondition: {"db_tag", "db_tag_bold", "source_list"},
    PublicationsCallout: {"blurb"},
}


EPVLEX_PENDING_FRONTEND_MIRROR_FIELDS: dict[type[BaseModel], set[str]] = {
    PubMedArticle: {
        "pmcid",
        "doi",
        "publication_date",
        "snippets",
        "source_tags",
        "snippet_status",
    },
    ReportPayload: {"publications_literature", "functional_evidence"},
}


EPVLEX_BACKEND_MODELS: dict[type[BaseModel], set[str]] = {
    PublicationSnippet: {"section", "text", "matched_terms", "source", "confidence"},
    PublicationSourceBreakdown: {"litvar2", "pubmed", "clinvar", "clingen"},
    PublicationLiterature: {
        "total_count",
        "shown_count",
        "offset",
        "limit",
        "sort",
        "variant_terms",
        "source_breakdown",
        "articles",
        "warnings",
    },
}


FUNCTIONAL_EVIDENCE_BACKEND_MODELS: dict[type[BaseModel], set[str]] = {
    FunctionalEvidenceSourceBreakdown: {"clingen", "clinvar", "pubmed"},
    FunctionalStudy: {
        "id",
        "pmid",
        "url",
        "citation",
        "source_tags",
        "evidence_codes",
        "snippet",
    },
    FunctionalEvidenceSummary: {
        "total_count",
        "source_breakdown",
        "evidence_codes",
        "studies",
        "warnings",
    },
}


def _backend_ts_path() -> Path:
    # tests/ -> backend/ -> app/ -> frontend/src/lib/backend.ts
    return Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "backend.ts"


def _extract_ts_interface_body(source: str, name: str) -> str:
    """Return the body slice between { and the matching } for the named interface."""
    match = re.search(rf"export\s+interface\s+{re.escape(name)}\s*\{{", source)
    if not match:
        raise AssertionError(f"export interface {name} not found in backend.ts")
    start = match.end()
    depth = 1
    i = start
    while i < len(source) and depth > 0:
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    if depth != 0:
        raise AssertionError(f"unterminated interface {name} in backend.ts")
    return source[start : i - 1]


@pytest.mark.parametrize(
    "model,ts_name",
    list(MODEL_TO_TS_INTERFACE.items()),
    ids=lambda v: v if isinstance(v, str) else v.__name__,
)
def test_pydantic_field_names_present_in_typescript(model, ts_name):
    backend_ts = _backend_ts_path().read_text(encoding="utf-8")
    body = _extract_ts_interface_body(backend_ts, ts_name)

    pydantic_fields = set(model.model_fields.keys())
    missing = {
        field
        for field in pydantic_fields
        if not re.search(rf"^\s*{re.escape(field)}\??\s*:", body, re.MULTILINE)
    }
    missing -= EPVLEX_PENDING_FRONTEND_MIRROR_FIELDS.get(model, set())
    assert not missing, (
        f"{ts_name} (TS) is missing fields present on {model.__name__} "
        f"(Pydantic): {sorted(missing)}"
    )


@pytest.mark.parametrize(
    "model,fields",
    list(BE6_REPORT_V2_FIELDS.items()),
    ids=lambda v: v.__name__ if isinstance(v, type) else ",".join(sorted(v)),
)
def test_be6_report_v2_fields_are_declared_on_pydantic_models(model, fields):
    assert fields <= set(model.model_fields.keys())


@pytest.mark.parametrize(
    "model,fields",
    list(EPVLEX_BACKEND_MODELS.items()),
    ids=lambda v: v.__name__ if isinstance(v, type) else ",".join(sorted(v)),
)
def test_epvlex_backend_models_are_declared(model, fields):
    assert fields <= set(model.model_fields.keys())


@pytest.mark.parametrize(
    "model,fields",
    list(FUNCTIONAL_EVIDENCE_BACKEND_MODELS.items()),
    ids=lambda v: v.__name__ if isinstance(v, type) else ",".join(sorted(v)),
)
def test_functional_evidence_backend_models_are_declared(model, fields):
    assert fields <= set(model.model_fields.keys())


def test_epvlex_pending_frontend_mirror_fields_are_declared_on_backend_models():
    for model, fields in EPVLEX_PENDING_FRONTEND_MIRROR_FIELDS.items():
        assert fields <= set(model.model_fields.keys())
