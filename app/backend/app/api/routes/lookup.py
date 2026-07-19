from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.core.rate_limit import RATE_LIMIT_LOOKUP, enforce_rate_limit
from app.schemas.lookup import (
    LookupInitialSummaryResponse,
    LookupRequest,
    LookupResponse,
    LookupSectionFetchRequest,
    LookupSectionFetchResponse,
    PublicationPageRequest,
    SearchInputParseRequest,
    SearchInputParseResponse,
)
from app.schemas.run import PublicationLiterature
from app.schemas.workflow import (
    CanonicalVariantRefV1,
    ConsequenceBucketV1,
    CuratedVariantPageV1,
    RelatedVariantGroupV1,
    RelatedVariantItemV1,
    build_report_href_v1,
)
from app.schemas.workbench import SourceDisclosure
from app.services.lookup_service_clinvar_distribution import (
    local_clinvar_curated_variant_page,
)
from app.services.lookup_timing import LOOKUP_TIMING_HEADER

router = APIRouter(prefix="/api/v1/lookup", tags=["lookup"])

LOOKUP_EAGER_RESPONSE_EXCLUDE = {
    "report_payload": {
        "report_profile": {
            "computational_deep_dive": True,
            "expert_panel": True,
            "therapies_trials": True,
        },
    }
}


@router.post("", response_model=LookupResponse)
def variant_lookup(
    payload: LookupRequest,
    request: Request,
    response: Response,
    refresh: bool = False,
    include_lazy_sections: bool = False,
) -> LookupResponse | JSONResponse:
    enforce_rate_limit(request, RATE_LIMIT_LOOKUP, subject=_lookup_subject(payload))
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    lookup_response = service.lookup(payload, refresh=refresh)
    timing_header = _lookup_timing_header(service, lookup_response)
    if timing_header:
        response.headers[LOOKUP_TIMING_HEADER] = timing_header
    if include_lazy_sections:
        return lookup_response
    return JSONResponse(
        content=jsonable_encoder(lookup_response, exclude=LOOKUP_EAGER_RESPONSE_EXCLUDE),
        headers={LOOKUP_TIMING_HEADER: timing_header} if timing_header else None,
    )


@router.post("/summary", response_model=LookupInitialSummaryResponse)
def lookup_summary(
    payload: LookupRequest,
    request: Request,
    response: Response,
    refresh: bool = False,
) -> LookupInitialSummaryResponse:
    enforce_rate_limit(request, RATE_LIMIT_LOOKUP, subject=_lookup_subject(payload))
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    summary = service.lookup_summary(payload, refresh=refresh)
    timing_header = _lookup_timing_header(service, summary)
    if timing_header:
        response.headers[LOOKUP_TIMING_HEADER] = timing_header
    return summary


@router.post("/sections", response_model=LookupSectionFetchResponse)
def lookup_sections(
    payload: LookupSectionFetchRequest,
    request: Request,
    response: Response,
    refresh: bool = False,
) -> LookupSectionFetchResponse:
    enforce_rate_limit(request, RATE_LIMIT_LOOKUP, subject=_lookup_subject(payload))
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    sections = service.lookup_sections(payload, refresh=refresh)
    timing_header = _lookup_timing_header(service, sections)
    if timing_header:
        response.headers[LOOKUP_TIMING_HEADER] = timing_header
    return sections


@router.post("/parse", response_model=SearchInputParseResponse)
def parse_lookup_input(
    payload: SearchInputParseRequest,
    request: Request,
) -> SearchInputParseResponse:
    enforce_rate_limit(request, RATE_LIMIT_LOOKUP, subject=payload.search_text)
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    # Public parse must not let callers force the heavier coordinate-resolution path.
    safe_payload = payload.model_copy(update={"resolve_coordinates": False})
    return service.parse_search_input(safe_payload)


@router.post("/publications", response_model=PublicationLiterature)
def lookup_publications(
    payload: PublicationPageRequest,
    request: Request,
    refresh: bool = False,
) -> PublicationLiterature:
    enforce_rate_limit(
        request,
        RATE_LIMIT_LOOKUP,
        subject=":".join(part for part in (payload.gene, payload.cdna) if part),
    )
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    try:
        if refresh:
            payload = payload.model_copy(update={"refresh": True})
        return service.page_publications(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.get("/related", response_model=RelatedVariantGroupV1)
def lookup_related_variants(
    request: Request,
    gene: str = Query(min_length=1, max_length=64),
    cdna: str = Query(min_length=1, max_length=256),
    transcript: str | None = Query(default=None, max_length=256),
) -> RelatedVariantGroupV1:
    enforce_rate_limit(request, RATE_LIMIT_LOOKUP, subject=f"related:{gene}:{cdna}")
    service = getattr(request.app.state, "lookup_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup service is unavailable.",
        )
    response = service.lookup(
        LookupRequest(gene=gene, cdna=cdna, transcript=transcript),
        refresh=False,
    )
    locus = response.report_payload.locus_context
    if locus is None:
        return RelatedVariantGroupV1(
            items=[],
            warnings=["related_variant_identities_unavailable"],
        )
    profile = response.report_payload.report_profile
    header = profile.header if profile is not None else None
    resolved_transcript = transcript or (header.transcript if header is not None else None)
    source_disclosure = SourceDisclosure(
        source_status="fixture",
        provider_id="eamos_lookup_v2_fixture",
        provider_label="Eamos report locus fixture",
        source_version="lookup-v2-modules.v1",
        cache_status="bundled_fixture",
        warnings=["related_variants_fixture_scope"],
        requirements=["Use source-backed per-variant identities for release data."],
    )
    query_position = _cdna_position(cdna)
    items: list[RelatedVariantItemV1] = []
    seen: set[str] = set()
    for nearby in locus.nearby_variants:
        if nearby.hgvs == cdna:
            continue
        variant_key = f"{gene.upper()}:{nearby.hgvs}"
        if variant_key in seen:
            continue
        seen.add(variant_key)
        variant = CanonicalVariantRefV1(
            schema_version="canonical_variant_ref.v1",
            gene=gene,
            cdna=nearby.hgvs,
            transcript=resolved_transcript,
            protein_hgvs=nearby.protein_change,
            genomic_hg38=None,
            variant_key=variant_key,
            species="human",
            genome_build="GRCh38",
            resolution_status="unresolved",
            source_support=["eamos_lookup_v2_fixture"],
            warnings=["genomic_identity_not_resolved"],
        )
        nearby_position = _cdna_position(nearby.hgvs)
        distance = (
            abs(nearby_position - query_position)
            if query_position is not None and nearby_position is not None
            else None
        )
        items.append(
            RelatedVariantItemV1(
                variant=variant,
                relationship="nearby",
                distance_bp=distance,
                classification=nearby.classification,
                evidence_axis_summary=None,
                source_disclosure=source_disclosure,
                report_href=build_report_href_v1(variant, from_surface="report"),
            )
        )
    return RelatedVariantGroupV1(
        items=items,
        warnings=["related_variants_fixture_scope"],
    )


@router.get("/curated", response_model=CuratedVariantPageV1)
def lookup_curated_variants(
    request: Request,
    gene: str = Query(min_length=1, max_length=64),
    classification: str | None = Query(
        default=None,
        pattern="^(pathogenic|likely_pathogenic|vus|likely_benign|benign)$",
    ),
    consequence: ConsequenceBucketV1 | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=512),
) -> CuratedVariantPageV1:
    enforce_rate_limit(request, RATE_LIMIT_LOOKUP, subject=f"curated:{gene}")
    try:
        return local_clinvar_curated_variant_page(
            gene,
            request.app.state.settings,
            classification=classification,
            consequence=consequence,
            limit=limit,
            cursor=cursor,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def _lookup_subject(payload: LookupRequest) -> str | None:
    if payload.raw_search_text:
        return payload.raw_search_text
    if payload.selected_candidate_id:
        return payload.selected_candidate_id
    return ":".join(
        part
        for part in (payload.gene, payload.cdna, payload.transcript, payload.protein_change)
        if part
    )


def _cdna_position(value: str) -> int | None:
    match = re.match(r"^c\.(-?\d+)", value)
    return int(match.group(1)) if match else None


def _lookup_timing_header(service, response) -> str | None:
    settings = getattr(service, "settings", None)
    if not bool(getattr(settings, "lookup_timing_diagnostics_enabled", False)):
        return None
    return getattr(response, "lookup_timing_header", None)
