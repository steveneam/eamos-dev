from __future__ import annotations

from typing import Any

from fastapi import status

from app.core.config import Settings
from app.schemas.workbench import (
    AlignReferenceRequest,
    AlignReferenceResponse,
    AlignRequest,
    AlignResponse,
    AlignTraceRequest,
    AlignTraceResponse,
    CrisprOffTargetRequest,
    CrisprOffTargetResponse,
    CrisprRequest,
    CrisprResponse,
    CrisprScreeningPrimerRequest,
    CrisprScreeningPrimerResponse,
    CrisprSsodnRequest,
    CrisprSsodnResponse,
    CrisprTideResponse,
    PrimerRequest,
    PrimerResponse,
    SourceDisclosure,
)
from app.services.crispr_design import (
    CRISPR_PROVIDER_CRISPRSCORE_R,
    CRISPR_PROVIDER_LOCAL_DETERMINISTIC,
    CrisprDesignInputError,
    CrisprScoreRAdapter,
    CrisprScoreRBackedCrisprProvider,
    LocalDeterministicCrisprProvider,
)
from app.services.crispr_offtarget_screening import (
    CRISPR_OFFTARGET_PROVIDER_AUTO,
    CRISPR_OFFTARGET_PROVIDER_INDEXED_SQLITE,
    CRISPR_OFFTARGET_PROVIDER_MOCK,
    CrisprOffTargetScreeningInputError,
    CrisprOffTargetScreeningProviderUnavailable,
    IndexedSqliteCrisprOffTargetProvider,
    MOCK_SCREENING_TEMPLATE_WARNING,
    MockCasOffinderOffTargetProvider,
    SCREENING_REFERENCE_WINDOW_UNAVAILABLE_WARNING,
    ScreeningReferenceWindowProvider,
    design_screening_primers,
)
from app.services.crispr_ssodn import CrisprSsodnInputError, design_ssodn
from app.services.crispr_tide import CrisprTideInputError, analyze_crispr_tide_observed
from app.services.sequence_context import (
    WORKBENCH_SEQUENCE_CONTEXT_UNAVAILABLE,
    SequenceContext,
    SequenceContextResult,
    SequenceContextService,
    unsupported_input_warning,
)
from app.services.trace_analysis import analyze_parsed_trace
from app.services.workbench_design_alignment import (
    LocalSangerAlignmentProvider,
    _parse_ab1_trace,
    _parse_ab1_trace_bytes,
)
from app.services.workbench_design_common import (
    HTTP_UNPROCESSABLE_ENTITY,
    WORKBENCH_PROVIDER_FAILED_PREFIX,
    WorkbenchDesignError,
    WorkbenchModel,
    _settings_path,
)
from app.services.workbench_design_fixture import WorkbenchFixtureProvider
from app.services.workbench_design_primer import (
    Primer3PrimerProvider,
    _default_specificity_provider,
)
from app.services.workbench_design_protocols import (
    AlignProvider,
    CrisprDesignProvider,
    CrisprOffTargetProvider,
    PrimerDesignProvider,
)


def _with_source_disclosure(
    response: WorkbenchModel,
    disclosure: SourceDisclosure,
) -> WorkbenchModel:
    if getattr(response, "source_disclosure", None) is not None:
        return response
    return response.model_copy(update={"source_disclosure": disclosure})


def _primer_source_disclosure(
    *,
    warnings: list[str] | None = None,
) -> SourceDisclosure:
    return SourceDisclosure(
        source_status="local_provider",
        provider_id="primer3_template_specificity",
        provider_label="Primer3 with template specificity screen",
        cache_status="runtime",
        warnings=list(warnings or []),
        requirements=["primer3_py"],
    )


def _crispr_design_source_disclosure(provider: CrisprDesignProvider) -> SourceDisclosure:
    if isinstance(provider, CrisprScoreRBackedCrisprProvider):
        return SourceDisclosure(
            source_status="local_provider",
            provider_id="crisprscore_r",
            provider_label="CRISPRScore R-backed provider",
            cache_status="runtime",
            requirements=["r_runtime", "crisprscore_model_assets"],
        )
    return SourceDisclosure(
        source_status="local_provider",
        provider_id="local_deterministic_spcas9",
        provider_label="Local deterministic SpCas9 provider",
        cache_status="runtime",
        warnings=["advanced_crispr_scoring_gated"],
        requirements=["spcas9_ngg"],
    )


def _screening_primer_source_disclosure(
    primers: list[Any],
    *,
    warnings: list[str],
) -> SourceDisclosure:
    template_sources = {getattr(primer, "template_source", "") for primer in primers}
    if MOCK_SCREENING_TEMPLATE_WARNING in warnings or "mock_screening_window" in template_sources:
        return SourceDisclosure(
            source_status="fallback",
            provider_id="crispr_screening_mock_window",
            provider_label="Mock screening-window fallback",
            warnings=warnings,
            requirements=["reference_window_provider"],
        )
    if (
        SCREENING_REFERENCE_WINDOW_UNAVAILABLE_WARNING in warnings
        or "reference_window" in template_sources
    ):
        return SourceDisclosure(
            source_status="source_backed",
            provider_id="crispr_screening_reference_window",
            provider_label="Reference-window screening primers",
            cache_status="resolved",
            warnings=warnings,
        )
    return SourceDisclosure(
        source_status="local_provider",
        provider_id="crispr_screening_template_sequence",
        provider_label="Template-sequence screening primers",
        cache_status="runtime",
        warnings=warnings,
    )


def _align_reference_source_disclosure(
    *,
    source: str,
    warnings: list[str],
) -> SourceDisclosure:
    if source == "fixture":
        return SourceDisclosure(
            source_status="fixture",
            provider_id="align_reference_fixture",
            provider_label="Fixture alignment reference",
            warnings=warnings,
        )
    return SourceDisclosure(
        source_status="source_backed",
        provider_id="sequence_context_alignment_reference",
        provider_label="Sequence-context alignment reference",
        cache_status="resolved",
        warnings=warnings,
    )


def _align_source_disclosure(*, warnings: list[str] | None = None) -> SourceDisclosure:
    return SourceDisclosure(
        source_status="local_provider",
        provider_id="local_sanger_aligner",
        provider_label="Local Sanger alignment provider",
        cache_status="runtime",
        warnings=list(warnings or []),
    )


def _trace_source_disclosure(*, warnings: list[str] | None = None) -> SourceDisclosure:
    return SourceDisclosure(
        source_status="local_provider",
        provider_id="ab1_trace_parser",
        provider_label="Local AB1 trace parser",
        cache_status="runtime",
        warnings=list(warnings or []),
        requirements=["ab1_input"],
    )


def _default_crispr_provider(settings: Settings | None) -> CrisprDesignProvider:
    provider_name = (
        (settings.crispr_provider if settings is not None else CRISPR_PROVIDER_LOCAL_DETERMINISTIC)
        .strip()
        .lower()
    )
    if provider_name == CRISPR_PROVIDER_LOCAL_DETERMINISTIC:
        return LocalDeterministicCrisprProvider()
    if provider_name == CRISPR_PROVIDER_CRISPRSCORE_R:
        adapter_kwargs = {}
        if settings is not None:
            adapter_kwargs = {
                "rscript_path": settings.crispr_rscript_path,
                "rule_set3_conda_env": settings.crispr_ruleset3_conda_env,
                "lindel_conda_env": settings.crispr_lindel_conda_env,
            }
        return CrisprScoreRBackedCrisprProvider(
            scoring_adapter=CrisprScoreRAdapter(**adapter_kwargs)
        )
    raise ValueError(f"Unknown CRISPR provider: {provider_name}")


def _default_crispr_offtarget_provider(
    settings: Settings | None,
    *,
    live_design_enabled: bool,
) -> CrisprOffTargetProvider:
    provider_name = (
        (
            settings.crispr_offtarget_provider
            if settings is not None
            else CRISPR_OFFTARGET_PROVIDER_AUTO
        )
        .strip()
        .lower()
    )
    if provider_name == CRISPR_OFFTARGET_PROVIDER_MOCK:
        return MockCasOffinderOffTargetProvider()

    if provider_name == CRISPR_OFFTARGET_PROVIDER_INDEXED_SQLITE:
        if settings is None:
            raise ValueError("Indexed CRISPR off-target screening requires backend settings.")
        return IndexedSqliteCrisprOffTargetProvider(
            _settings_path(settings, settings.crispr_offtarget_index_path),
            max_results=settings.crispr_offtarget_max_results,
        )

    if provider_name == CRISPR_OFFTARGET_PROVIDER_AUTO:
        if settings is not None and live_design_enabled:
            indexed_provider = IndexedSqliteCrisprOffTargetProvider(
                _settings_path(settings, settings.crispr_offtarget_index_path),
                max_results=settings.crispr_offtarget_max_results,
            )
            if indexed_provider.available():
                return indexed_provider
        return MockCasOffinderOffTargetProvider()

    raise ValueError(f"Unknown CRISPR off-target provider: {provider_name}")


class WorkbenchDesignService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        fixture_provider: WorkbenchFixtureProvider | None = None,
        sequence_context_service: SequenceContextService | None = None,
        primer_provider: PrimerDesignProvider | None = None,
        crispr_provider: CrisprDesignProvider | None = None,
        crispr_offtarget_provider: CrisprOffTargetProvider | None = None,
        screening_reference_provider: ScreeningReferenceWindowProvider | None = None,
        align_provider: AlignProvider | None = None,
    ) -> None:
        self.settings = settings
        self.workbench_live_design_enabled = (
            settings is None
            or bool(getattr(settings, "workbench_live_design_enabled", True))
            or bool(settings.use_real_apis)
        )
        self.fixture_provider = fixture_provider or WorkbenchFixtureProvider()
        self.sequence_context_service = sequence_context_service or SequenceContextService(
            settings=settings
        )
        self.primer_provider = primer_provider or Primer3PrimerProvider(
            specificity_provider=_default_specificity_provider(settings)
        )
        self.crispr_provider = crispr_provider or _default_crispr_provider(settings)
        self.crispr_offtarget_provider = (
            crispr_offtarget_provider
            or _default_crispr_offtarget_provider(
                settings,
                live_design_enabled=self.workbench_live_design_enabled,
            )
        )
        self.screening_reference_provider = screening_reference_provider
        self.align_provider = align_provider or LocalSangerAlignmentProvider()

    def design_primers(self, payload: PrimerRequest) -> PrimerResponse:
        if self.workbench_live_design_enabled:
            return self._design_real_primers(payload, prefer_resolver=True)
        return self.fixture_provider.primers(payload)

    def design_guides(self, payload: CrisprRequest) -> CrisprResponse:
        if self.workbench_live_design_enabled:
            return self._design_real_guides(payload, prefer_resolver=True)
        return self.fixture_provider.crispr(payload)

    def enumerate_crispr_offtargets(
        self,
        payload: CrisprOffTargetRequest,
    ) -> CrisprOffTargetResponse:
        if payload.genome_build.upper() != "GRCH38":
            code = unsupported_input_warning("crispr_offtarget_genome_build")
            raise WorkbenchDesignError(
                code=code,
                message="CRISPR off-target screening requires an explicit GRCh38 locus.",
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=[code],
            )
        if payload.on_target_locus is None:
            code = unsupported_input_warning("crispr_offtarget_on_target_locus")
            raise WorkbenchDesignError(
                code=code,
                message=(
                    "Confirm the resolved on-target chromosome, position, and strand before "
                    "off-target screening."
                ),
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=[code],
            )
        try:
            return self.crispr_offtarget_provider.enumerate(payload)
        except CrisprOffTargetScreeningInputError as exc:
            raise WorkbenchDesignError(
                code=exc.code,
                message=exc.message,
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=exc.warnings,
            ) from exc
        except CrisprOffTargetScreeningProviderUnavailable as exc:
            raise WorkbenchDesignError(
                code=exc.code,
                message=exc.message,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                warnings=[exc.code],
            ) from exc
        except WorkbenchDesignError:
            raise
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="CRISPR off-target provider failed for the requested guide.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

    def design_crispr_screening_primers(
        self,
        payload: CrisprScreeningPrimerRequest,
    ) -> CrisprScreeningPrimerResponse:
        try:
            primers, warnings = design_screening_primers(
                payload,
                primer_provider=self.primer_provider,
                reference_window_provider=self.screening_reference_provider,
            )
        except CrisprOffTargetScreeningInputError as exc:
            raise WorkbenchDesignError(
                code=exc.code,
                message=exc.message,
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=exc.warnings,
            ) from exc
        except WorkbenchDesignError:
            raise
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="CRISPR screening-primer provider failed for the selected sites.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc
        return CrisprScreeningPrimerResponse(
            mode=payload.mode,
            primers=primers,
            warnings=warnings,
            source_disclosure=_screening_primer_source_disclosure(
                primers,
                warnings=warnings,
            ),
        )

    def design_crispr_ssodn(self, payload: CrisprSsodnRequest) -> CrisprSsodnResponse:
        try:
            return design_ssodn(payload, None)
        except CrisprSsodnInputError as local_exc:
            if local_exc.code != unsupported_input_warning("ssodn_sequence_context"):
                raise WorkbenchDesignError(
                    code=local_exc.code,
                    message=local_exc.message,
                    status_code=HTTP_UNPROCESSABLE_ENTITY,
                    warnings=local_exc.warnings,
                ) from local_exc

        try:
            sequence_result = self.sequence_context_service.resolve(
                gene=payload.gene,
                cdna=payload.cdna,
            )
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="Sequence context provider failed while preparing ssODN design.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        try:
            return design_ssodn(
                payload,
                sequence_result.context,
                context_warnings=list(sequence_result.warnings),
            )
        except CrisprSsodnInputError as exc:
            raise WorkbenchDesignError(
                code=exc.code,
                message=exc.message,
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=exc.warnings,
            ) from exc
        except WorkbenchDesignError:
            raise
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="ssODN provider failed for the requested variant.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

    def align(self, payload: AlignRequest) -> AlignResponse:
        if self.workbench_live_design_enabled:
            return self._align_real(payload)
        return self.fixture_provider.align(payload)

    def resolve_align_reference(
        self,
        payload: AlignReferenceRequest,
    ) -> AlignReferenceResponse:
        try:
            sequence_result = self.sequence_context_service.resolve(
                gene=payload.gene,
                cdna=payload.cdna,
                transcript=payload.transcript,
                species=payload.species,
                prefer_resolver=True,
            )
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="Sequence context provider failed while resolving alignment reference.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        context = self._sequence_context_or_error(
            sequence_result,
            purpose="alignment reference resolution",
        )
        return AlignReferenceResponse(
            gene=context.gene,
            cdna=context.cdna,
            transcript=context.transcript,
            transcript_hgvs=context.transcript_hgvs,
            genome_build=context.genome_build,
            genomic_hg38=context.genomic_hg38,
            strand=context.strand,
            reference=context.window_sequence,
            target_position=context.target_offset,
            reference_base=context.reference_base,
            alternate_base=context.alternate_base,
            source=context.source,
            warnings=list(sequence_result.warnings) + list(context.warnings),
            source_disclosure=_align_reference_source_disclosure(
                source=context.source,
                warnings=list(sequence_result.warnings) + list(context.warnings),
            ),
        )

    def analyze_trace(self, payload: AlignTraceRequest) -> AlignTraceResponse:
        trace = _parse_ab1_trace(payload.ab1_blob_base64)
        response = analyze_parsed_trace(trace)
        return _with_source_disclosure(
            response,
            _trace_source_disclosure(warnings=response.warnings),
        )

    def analyze_crispr_tide(
        self,
        *,
        control_bytes: bytes,
        edited_bytes: bytes,
        cut_site_index: int,
    ) -> CrisprTideResponse:
        try:
            control_trace = _parse_ab1_trace_bytes(control_bytes)
            edited_trace = _parse_ab1_trace_bytes(edited_bytes)
            return analyze_crispr_tide_observed(
                control_trace=control_trace,
                edited_trace=edited_trace,
                cut_site_index=cut_site_index,
            )
        except CrisprTideInputError as exc:
            raise WorkbenchDesignError(
                code=exc.code,
                message=exc.message,
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=exc.warnings,
            ) from exc

    def _design_real_primers(
        self,
        payload: PrimerRequest,
        *,
        prefer_resolver: bool = False,
    ) -> PrimerResponse:
        try:
            sequence_result = self.sequence_context_service.resolve(
                gene=payload.gene,
                cdna=payload.cdna,
                prefer_resolver=prefer_resolver,
            )
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="Sequence context provider failed while preparing primer design.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        context = self._sequence_context_or_error(sequence_result)
        response = self.primer_provider.design(payload, context)
        return _with_source_disclosure(response, _primer_source_disclosure())

    def _design_real_guides(
        self,
        payload: CrisprRequest,
        *,
        prefer_resolver: bool = False,
    ) -> CrisprResponse:
        try:
            sequence_result = self.sequence_context_service.resolve(
                gene=payload.gene,
                cdna=payload.cdna,
                prefer_resolver=prefer_resolver,
            )
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="Sequence context provider failed while preparing CRISPR design.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        context = self._sequence_context_or_error(sequence_result, purpose="CRISPR design")
        try:
            response = self.crispr_provider.design(payload, context)
            return _with_source_disclosure(
                response,
                _crispr_design_source_disclosure(self.crispr_provider),
            )
        except CrisprDesignInputError as exc:
            raise WorkbenchDesignError(
                code=exc.code,
                message=exc.message,
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=exc.warnings,
            ) from exc
        except WorkbenchDesignError:
            raise
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="CRISPR provider failed to design guides for the requested context.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

    def _align_real(self, payload: AlignRequest) -> AlignResponse:
        try:
            sequence_result = self.sequence_context_service.resolve(
                gene=payload.gene,
                cdna=payload.cdna,
            )
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="Sequence context provider failed while preparing Sanger alignment.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        context = self._sequence_context_or_error(sequence_result, purpose="Sanger alignment")
        try:
            response = self.align_provider.align(payload, context)
            return _with_source_disclosure(response, _align_source_disclosure())
        except WorkbenchDesignError:
            raise
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="Sanger alignment provider failed for the requested context.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

    def _sequence_context_or_error(
        self,
        result: SequenceContextResult,
        *,
        purpose: str = "primer design",
    ) -> SequenceContext:
        if result.context is not None:
            return result.context

        code = result.warnings[0] if result.warnings else WORKBENCH_SEQUENCE_CONTEXT_UNAVAILABLE
        raise WorkbenchDesignError(
            code=code,
            message=f"Workbench sequence context is unavailable for real-mode {purpose}.",
            status_code=HTTP_UNPROCESSABLE_ENTITY,
            warnings=result.warnings or [code],
        )
