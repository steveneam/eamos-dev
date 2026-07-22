from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import status
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.gene_viewer import (
    AppliedVariant,
    ClinvarVariant,
    ExonVariantDensity,
    GeneViewerRequest,
    GeneViewerResponse,
    ViewerProvenance,
)
from app.services.sequence_context import (
    NormalizedVariantQuery,
    normalize_sequence_query,
    unsupported_input_warning,
)
from app.services.protein_annotation import ProteinAnnotationService
from app.services.gene_viewer_models import (
    GeneViewerProvider,
    SourceBackedViewerBundle,
    SourceTranscriptExon as SourceTranscriptExon,
    SourceTranscriptIntron as SourceTranscriptIntron,
    SourceTranscriptModel as SourceTranscriptModel,
)
from app.services.gene_viewer_protein_tracks import (
    hydrate_response_with_record_protein_track as _hydrate_response_with_record_protein_track,
    set_windowed_protein_product as _set_windowed_protein_product,
)
from app.services.gene_viewer_source_provider import (
    SourceBackedGeneViewerProvider,
    query_with_source_transcript as _query_with_source_transcript,
)
from app.services.gene_viewer_fixture_records import (
    curated_fixture_provenance_sources as _curated_fixture_provenance_sources,
    curated_fixture_record as _curated_fixture_record,
    source_transcript_from_curated_fixture as _source_transcript_from_curated_fixture,
    transcript_model_from_curated_fixture as _transcript_model_from_curated_fixture,
    validate_curated_fixture_window as _validate_curated_fixture_window,
    variant_from_curated_fixture as _variant_from_curated_fixture,
)
from app.services.gene_viewer_full_locus import (
    full_gene_fixture_response as _full_gene_fixture_response,
)
from app.services.gene_viewer_source_client import (
    HttpGeneViewerSourceClient as HttpGeneViewerSourceClient,
)
from app.services.gene_viewer_utils import dedupe_warnings as _dedupe_warnings
from app.services.gene_viewer_errors import (
    GENE_VIEWER_CURATED_FIXTURE_FALLBACK,
    GENE_VIEWER_LIVE_PROVIDER_FALLBACK_PREFIX,
    GENE_VIEWER_PROVIDER_FAILED_PREFIX,
    GENE_VIEWER_PROVIDER_MALFORMED,
    GENE_VIEWER_PROVIDER_UNAVAILABLE,
    GENE_VIEWER_REFERENCE_MISMATCH,
    GENE_VIEWER_SERVICE_UNAVAILABLE as GENE_VIEWER_SERVICE_UNAVAILABLE,
    HTTP_UNPROCESSABLE_ENTITY,
    GeneViewerError,
)
from app.services.gene_viewer_variants import VariantProjection as VariantProjection
from app.services.gene_viewer_window import (
    TranscriptExon as TranscriptExon,
    TranscriptIntron as TranscriptIntron,
    TranscriptModel as TranscriptModel,
    TranscriptWindowBuilder,
    _replace_at,
    _segment_display_sequence,
)
from app.services.variant_applied_model import build_protein_product_effect


class GeneViewerFixtureProvider:
    curated_fixture_name = "gene_viewer_transcript_models.json"

    def __init__(
        self,
        fixtures_dir: Path | None = None,
        *,
        protein_annotation_service: ProteinAnnotationService | None = None,
    ) -> None:
        self.fixtures_dir = fixtures_dir or (
            Path(__file__).resolve().parents[1] / "fixtures" / "workbench"
        )
        self.protein_annotation_service = protein_annotation_service
        self._fixture_cache: dict[str, dict[str, Any]] = {}

    def viewer(self, payload: GeneViewerRequest) -> GeneViewerResponse:
        query = normalize_sequence_query(payload.gene, payload.cdna, payload.transcript)
        if payload.window.kind == "full_gene":
            fixture = self._load(self.curated_fixture_name)
            rpe65_window = (
                self._load("viewer_rpe65.json")
                if query.gene == "RPE65" and query.hgvs == "c.260A>G"
                else {}
            )
            return _full_gene_fixture_response(
                payload=payload,
                query=query,
                fixture=fixture,
                rpe65_window=rpe65_window,
            )
        if query.gene != "RPE65" or query.hgvs != "c.260A>G":
            return self.viewer_bundle(payload, query=query).response
        try:
            response = GeneViewerResponse(**self._load("viewer_rpe65.json"))
        except ValidationError as exc:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_MALFORMED,
                message="Gene viewer fixture is malformed: viewer_rpe65.json",
                status_code=status.HTTP_502_BAD_GATEWAY,
            ) from exc
        return _viewer_response_for_allele_mode(response, payload.allele_mode)

    def viewer_bundle(
        self,
        payload: GeneViewerRequest,
        *,
        query: NormalizedVariantQuery | None = None,
    ) -> SourceBackedViewerBundle:
        query = query or normalize_sequence_query(payload.gene, payload.cdna, payload.transcript)
        fixture = self._load(self.curated_fixture_name)
        return _curated_fixture_viewer_bundle(
            payload=payload,
            query=query,
            fixture=fixture,
            protein_annotation_service=self.protein_annotation_service,
        )

    def _load(self, name: str) -> dict[str, Any]:
        cached = self._fixture_cache.get(name)
        if cached is not None:
            return cached
        try:
            payload = json.loads((self.fixtures_dir / name).read_text(encoding="utf-8"))
        except OSError as exc:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_UNAVAILABLE,
                message=f"Gene viewer fixture is unavailable: {name}",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc
        except ValueError as exc:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_MALFORMED,
                message=f"Gene viewer fixture is malformed: {name}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            ) from exc
        self._fixture_cache[name] = payload
        return payload


class GeneViewerService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        protein_annotation_service: ProteinAnnotationService | None = None,
        fixture_provider: GeneViewerFixtureProvider | None = None,
        live_provider: GeneViewerProvider | None = None,
    ) -> None:
        self.settings = settings
        self.fixture_provider = fixture_provider or GeneViewerFixtureProvider(
            protein_annotation_service=protein_annotation_service,
        )
        self.live_provider = live_provider or SourceBackedGeneViewerProvider(
            settings=settings,
            protein_annotation_service=protein_annotation_service,
        )

    def build_viewer(self, payload: GeneViewerRequest) -> GeneViewerResponse:
        if self.settings is not None and self.settings.use_real_apis:
            try:
                return self.live_provider.viewer(payload)
            except GeneViewerError as exc:
                if payload.window.kind == "full_gene":
                    raise
                fallback = self._fixture_fallback(payload, reason=exc.code)
                if fallback is not None:
                    return fallback
                raise
            except Exception as exc:
                if payload.window.kind == "full_gene":
                    raise GeneViewerError(
                        code=f"{GENE_VIEWER_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                        message="Complete source-backed gene locus is unavailable.",
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    ) from exc
                fallback = self._fixture_fallback(payload, reason=type(exc).__name__)
                if fallback is not None:
                    return fallback
                raise GeneViewerError(
                    code=f"{GENE_VIEWER_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                    message="Gene viewer source provider failed while building the viewer.",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                ) from exc
        return self.fixture_provider.viewer(payload)

    def _fixture_fallback(
        self,
        payload: GeneViewerRequest,
        *,
        reason: str,
    ) -> GeneViewerResponse | None:
        try:
            response = self.fixture_provider.viewer(payload)
        except GeneViewerError:
            return None
        response.provenance.warnings = _dedupe_warnings(
            [
                *response.provenance.warnings,
                GENE_VIEWER_CURATED_FIXTURE_FALLBACK,
                f"{GENE_VIEWER_LIVE_PROVIDER_FALLBACK_PREFIX}:{reason}",
            ]
        )
        return response


def _curated_fixture_viewer_bundle(
    *,
    payload: GeneViewerRequest,
    query: NormalizedVariantQuery,
    fixture: dict[str, Any],
    protein_annotation_service: ProteinAnnotationService | None = None,
) -> SourceBackedViewerBundle:
    record = _curated_fixture_record(fixture=fixture, query=query)
    if record is None:
        code = unsupported_input_warning("fixture")
        raise GeneViewerError(
            code=code,
            message=(
                "Offline gene viewer fixture is available for RPE65 c.260A>G "
                "and curated ClinVar-stack transcript-model cases."
            ),
            status_code=HTTP_UNPROCESSABLE_ENTITY,
            warnings=[code],
        )
    _validate_curated_fixture_window(payload=payload, record=record)
    variant = _variant_from_curated_fixture(record)
    source = _source_transcript_from_curated_fixture(record)
    response = TranscriptWindowBuilder().build(
        request=payload,
        transcript=_transcript_model_from_curated_fixture(record),
        variant=variant,
    )
    query = _query_with_source_transcript(query, source)
    response.provenance = ViewerProvenance(
        sources=_curated_fixture_provenance_sources(
            record=record,
            fixture_version=str(fixture.get("version") or ""),
        ),
        warnings=list(record.get("warnings") or []),
    )
    response.tracks.clinvar_variants = [
        ClinvarVariant(
            cds_pos=variant.cds_pos,
            hgvs_c=variant.hgvs_c,
            hgvs_p=variant.hgvs_p,
            classification=variant.classification,
            clinvar_id=str(record.get("accession") or record.get("clinvar_variation_id") or ""),
            queried=True,
        )
    ]
    response.tracks.protein_product = build_protein_product_effect(
        variant=variant,
        allele_mode=payload.allele_mode,
        reference_protein_length=source.protein_length,
        exons=source.exons,
    )
    _hydrate_response_with_record_protein_track(
        response=response,
        record=record,
        protein_annotation_service=protein_annotation_service,
    )
    exon_number = next(
        (exon.number for exon in source.exons if exon.cds_start <= variant.cds_pos <= exon.cds_end),
        None,
    )
    if exon_number is not None:
        response.tracks.exon_density = [
            ExonVariantDensity(exon_number=exon_number, variant_count=1)
        ]
    return SourceBackedViewerBundle(
        query=query,
        variant=variant,
        transcript_source=source,
        response=response,
    )


def _viewer_response_for_allele_mode(
    response: GeneViewerResponse,
    allele_mode: str,
) -> GeneViewerResponse:
    if allele_mode == response.sequences.allele_mode:
        updated = response.model_copy(deep=True)
        _set_windowed_protein_product(updated, allele_mode=allele_mode)
        return updated
    if allele_mode == "reference":
        updated = response.model_copy(deep=True)
        updated.sequences.allele_mode = "reference"
        updated.sequences.display_window_sequence = updated.sequences.reference_window_sequence
        updated.sequences.applied_variant = None
        _set_windowed_protein_product(updated, allele_mode="reference")
        return updated

    updated = response.model_copy(deep=True)
    variant = updated.queried_variant
    cumulative = 0
    for segment in updated.segments:
        segment_sequence = _segment_display_sequence(segment)
        if (
            segment.kind == "exon"
            and segment.cds_start is not None
            and segment.cds_end is not None
            and segment.cds_start <= variant.cds_pos <= segment.cds_end
        ):
            local_offset = variant.cds_pos - segment.cds_start
            global_offset = cumulative + local_offset
            observed_ref = updated.sequences.reference_window_sequence[global_offset]
            if observed_ref.upper() != variant.ref.upper():
                raise GeneViewerError(
                    code=GENE_VIEWER_REFERENCE_MISMATCH,
                    message=(
                        "Viewer fixture reference base does not match the requested "
                        f"variant at {variant.hgvs_c}."
                    ),
                    status_code=HTTP_UNPROCESSABLE_ENTITY,
                    warnings=[GENE_VIEWER_REFERENCE_MISMATCH],
                )
            updated.sequences.allele_mode = "variant"
            updated.sequences.display_window_sequence = _replace_at(
                updated.sequences.reference_window_sequence,
                global_offset,
                variant.alt,
            )
            updated.sequences.applied_variant = AppliedVariant(
                hgvs_c=variant.hgvs_c,
                cds_pos=variant.cds_pos,
                segment_id=segment.id,
                sequence_offset=global_offset,
                ref=variant.ref,
                alt=variant.alt,
            )
            _set_windowed_protein_product(updated, allele_mode="variant")
            return updated
        cumulative += len(segment_sequence)

    raise GeneViewerError(
        code=unsupported_input_warning("variant_outside_window"),
        message="Queried variant is outside the active viewer fixture window.",
        status_code=HTTP_UNPROCESSABLE_ENTITY,
    )
