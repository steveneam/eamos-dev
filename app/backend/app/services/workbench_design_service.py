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
    CrisprDesignInputError,
    LocalDeterministicCrisprProvider,
)
from app.services.crispr_offtarget_screening import (
    CrisprOffTargetScreeningInputError,
    CrisprOffTargetScreeningProviderUnavailable,
    ScreeningReferenceWindowProvider,
    design_screening_primers,
)
from app.services.crispr_ssodn import CrisprSsodnInputError, design_ssodn
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
)
from app.services.workbench_design_common import (
    HTTP_UNPROCESSABLE_ENTITY,
    WORKBENCH_PROVIDER_FAILED_PREFIX,
    WorkbenchDesignError,
)
from app.services.workbench_design_context import (
    VerifiedWorkbenchContext,
    verify_workbench_design_context_v2,
)
from app.services.workbench_design_execution import (
    bind_crispr_design_v2,
    bind_crispr_offtarget_v2,
    bind_workbench_response_v2,
    executed_disclosure,
    mounted_artifact_disclosure,
    package_version,
    unavailable_disclosure,
)
from app.services.workbench_design_fixture import WorkbenchFixtureProvider
from app.services.workbench_design_primer import (
    Primer3PrimerProvider,
    _default_specificity_provider,
)
from app.services.workbench_design_primer_snp import (
    default_snp_masking_provider as _default_snp_masking_provider,
)
from app.services.workbench_design_protocols import (
    AlignProvider,
    CrisprDesignProvider,
    CrisprOffTargetProvider,
    PrimerDesignProvider,
)
from app.services.workbench_design_runtime import (
    VerifiedReferenceWindowProvider as _VerifiedReferenceWindowProvider,
    align_reference_source_disclosure as _align_reference_source_disclosure,
    align_source_disclosure as _align_source_disclosure,
    crispr_design_source_disclosure as _crispr_design_source_disclosure,
    default_crispr_offtarget_provider as _default_crispr_offtarget_provider,
    default_crispr_provider as _default_crispr_provider,
    normalize_chromosome as _normalize_chromosome,
    primer_execution_requirements as _primer_execution_requirements,
    primer_execution_warnings as _primer_execution_warnings,
    primer_source_disclosure as _primer_source_disclosure,
    screening_primer_source_disclosure as _screening_primer_source_disclosure,
    trace_source_disclosure as _trace_source_disclosure,
    with_source_disclosure as _with_source_disclosure,
)


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
            specificity_provider=_default_specificity_provider(settings),
            snp_masking_provider=_default_snp_masking_provider(settings),
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
        if self.workbench_live_design_enabled or payload.design_context_v2 is not None:
            return self._design_real_primers(payload, prefer_resolver=True)
        return self.fixture_provider.primers(payload)

    def design_guides(self, payload: CrisprRequest) -> CrisprResponse:
        if self.workbench_live_design_enabled or payload.design_context_v2 is not None:
            return self._design_real_guides(payload, prefer_resolver=True)
        return self.fixture_provider.crispr(payload)

    def enumerate_crispr_offtargets(
        self,
        payload: CrisprOffTargetRequest,
    ) -> CrisprOffTargetResponse:
        verified = self._verified_context_for_offtarget(payload)
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
        if verified is not None:
            self._verify_guide_identity(payload, verified)
            artifact_getter = getattr(
                self.crispr_offtarget_provider,
                "execution_artifact",
                None,
            )
            artifact = artifact_getter() if callable(artifact_getter) else None
            if artifact is None:
                return self._unavailable_crispr_offtargets_v2(
                    payload,
                    verified,
                    warning="crispr_offtarget_artifact_identity_unavailable",
                    requirement="immutable_index_manifest_binding",
                )
        try:
            response = self.crispr_offtarget_provider.enumerate(payload)
            if verified is None:
                return response
            if (
                response.source_disclosure is None
                or response.source_disclosure.source_status != "source_backed"
            ):
                return self._unavailable_crispr_offtargets_v2(
                    payload,
                    verified,
                    warning="mock_offtarget_results_suppressed",
                    requirement="grch38_crispr_offtarget_index",
                )
            disclosure = mounted_artifact_disclosure(
                verified,
                capability_id="crispr_offtarget_enumeration",
                claim="Enumerated SpCas9 candidates from the configured GRCh38 index",
                algorithm_id="indexed_spcas9_neighbor_search",
                algorithm_version="1.0.0",
                input_scope="verified_guide_identity",
                artifact_manifest_id=artifact.manifest_id,
                artifact_sha256=artifact.sha256,
                source_release=artifact.source_release,
                warnings=[
                    f"enumeration_bound:max_mismatches={payload.max_mismatches}",
                    "cfd_score_unavailable",
                ],
                requirements=["crisprscore_cfd_runtime"],
            )
            assert payload.guide_identity is not None
            return bind_crispr_offtarget_v2(
                response,
                verified=verified,
                identity=payload.guide_identity,
                disclosure=disclosure,
            )
        except CrisprOffTargetScreeningInputError as exc:
            raise WorkbenchDesignError(
                code=exc.code,
                message=exc.message,
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=exc.warnings,
            ) from exc
        except CrisprOffTargetScreeningProviderUnavailable as exc:
            if verified is not None:
                return self._unavailable_crispr_offtargets_v2(
                    payload,
                    verified,
                    warning=exc.code,
                    requirement="grch38_crispr_offtarget_index",
                )
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
        verified = self._verified_context_for_screening(payload)
        reference_provider = (
            _VerifiedReferenceWindowProvider(verified)
            if verified is not None
            else self.screening_reference_provider
        )
        try:
            primers, warnings = design_screening_primers(
                payload,
                primer_provider=self.primer_provider,
                reference_window_provider=reference_provider,
            )
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
                message="CRISPR screening-primer provider failed for the selected sites.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc
        response = CrisprScreeningPrimerResponse(
            mode=payload.mode,
            primers=primers,
            warnings=warnings,
            source_disclosure=_screening_primer_source_disclosure(
                primers,
                warnings=warnings,
            ),
        )
        if verified is None:
            return response
        disclosure = executed_disclosure(
            verified,
            capability_id="crispr_screening_primers",
            claim="Designed screening primers from verified reference windows",
            algorithm_id="primer3_screening_primer_design",
            algorithm_version=package_version("primer3-py"),
            warnings=_primer_execution_warnings(self.primer_provider, payload),
            requirements=_primer_execution_requirements(self.primer_provider),
        )
        return bind_workbench_response_v2(
            response,
            verified=verified,
            disclosure=disclosure,
        )

    def design_crispr_ssodn(self, payload: CrisprSsodnRequest) -> CrisprSsodnResponse:
        sequence_result, context, verified = self._resolve_payload_context(
            payload,
            purpose="ssODN design",
            transcript=payload.transcript,
            species=payload.species,
            prefer_resolver=(
                self.workbench_live_design_enabled or payload.design_context_v2 is not None
            ),
        )
        try:
            response = design_ssodn(
                payload,
                context,
                context_warnings=list(sequence_result.warnings),
                allow_local_transcript=(
                    self.workbench_live_design_enabled or payload.design_context_v2 is not None
                ),
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
        if verified is None:
            return response
        return bind_workbench_response_v2(
            response,
            verified=verified,
            disclosure=executed_disclosure(
                verified,
                capability_id="crispr_ssodn_design",
                claim="Designed an ssODN from the verified reference selection",
                algorithm_id="eamos_ssodn_donor_design",
                algorithm_version="2.0.0",
                warnings=response.warnings,
            ),
        )

    def align(self, payload: AlignRequest) -> AlignResponse:
        if self.workbench_live_design_enabled or payload.design_context_v2 is not None:
            return self._align_real(payload)
        return self.fixture_provider.align(payload)

    def resolve_align_reference(
        self,
        payload: AlignReferenceRequest,
    ) -> AlignReferenceResponse:
        sequence_result, context, verified = self._resolve_payload_context(
            payload,
            purpose="alignment reference resolution",
            transcript=payload.transcript,
            species=payload.species,
        )
        response = AlignReferenceResponse(
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
        if verified is None:
            return response
        return bind_workbench_response_v2(
            response,
            verified=verified,
            disclosure=executed_disclosure(
                verified,
                capability_id="align_reference_resolution",
                claim="Resolved the exact verified Workbench selection reference",
                algorithm_id="workbench_context_v2_replay",
                algorithm_version="2.0.0",
            ),
        )

    def analyze_trace(self, payload: AlignTraceRequest) -> AlignTraceResponse:
        verified: VerifiedWorkbenchContext | None = None
        if payload.design_context_v2 is not None:
            _result, _context, verified = self._resolve_payload_context(
                payload,
                purpose="AB1 trace analysis",
            )
        trace = _parse_ab1_trace(payload.ab1_blob_base64)
        response = analyze_parsed_trace(trace)
        response = _with_source_disclosure(
            response,
            _trace_source_disclosure(warnings=response.warnings),
        )
        if verified is None:
            return response
        return bind_workbench_response_v2(
            response,
            verified=verified,
            disclosure=executed_disclosure(
                verified,
                capability_id="ab1_trace_analysis",
                claim="Parsed and quality-analyzed an AB1 trace in request memory",
                algorithm_id="biopython_ab1_mott_trace_analysis",
                algorithm_version=package_version("biopython"),
                input_scope="request_lifetime_ab1_bound_to_verified_context",
            ),
        )

    def analyze_crispr_tide(
        self,
        *,
        control_bytes: bytes,
        edited_bytes: bytes,
        cut_site_index: int,
    ) -> CrisprTideResponse:
        del control_bytes, edited_bytes, cut_site_index
        raise WorkbenchDesignError(
            code="crispr_tide_decomposition_unavailable",
            message=(
                "TIDE chromatogram-signal decomposition is not installed; the former "
                "consensus-string proxy is no longer returned as TIDE."
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            warnings=[
                "crispr_tide_decomposition_unavailable",
                "requirement:validated_tide_signal_decomposition",
            ],
        )

    def _design_real_primers(
        self,
        payload: PrimerRequest,
        *,
        prefer_resolver: bool = False,
    ) -> PrimerResponse:
        _sequence_result, context, verified = self._resolve_payload_context(
            payload,
            purpose="primer design",
            prefer_resolver=prefer_resolver,
        )
        response = self.primer_provider.design(payload, context)
        response = _with_source_disclosure(
            response,
            _primer_source_disclosure(
                warnings=_primer_execution_warnings(self.primer_provider, payload),
            ),
        )
        if verified is None:
            return response
        return bind_workbench_response_v2(
            response,
            verified=verified,
            disclosure=executed_disclosure(
                verified,
                capability_id="primer_design",
                claim="Ran Primer3 over the exact verified Workbench selection",
                algorithm_id="primer3",
                algorithm_version=package_version("primer3-py"),
                warnings=_primer_execution_warnings(self.primer_provider, payload),
                requirements=_primer_execution_requirements(self.primer_provider),
            ),
        )

    def _design_real_guides(
        self,
        payload: CrisprRequest,
        *,
        prefer_resolver: bool = False,
    ) -> CrisprResponse:
        _sequence_result, context, verified = self._resolve_payload_context(
            payload,
            purpose="CRISPR design",
            prefer_resolver=prefer_resolver,
        )
        if verified is not None and not isinstance(
            self.crispr_provider,
            LocalDeterministicCrisprProvider,
        ):
            raise WorkbenchDesignError(
                code="crispr_v2_score_provenance_unavailable",
                message=(
                    "Context V2 CRISPR scoring requires structured per-score provenance "
                    "from the configured scoring adapter."
                ),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                warnings=[
                    "crispr_v2_score_provenance_unavailable",
                    "requirement:structured_crispr_score_adapter",
                ],
            )
        try:
            response = self.crispr_provider.design(payload, context)
            response = _with_source_disclosure(
                response,
                _crispr_design_source_disclosure(self.crispr_provider),
            )
            if verified is None:
                return response
            return bind_crispr_design_v2(response, verified=verified)
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
        _sequence_result, context, verified = self._resolve_payload_context(
            payload,
            purpose="Sanger alignment",
            prefer_resolver=False,
        )
        try:
            response = self.align_provider.align(payload, context)
            response = _with_source_disclosure(response, _align_source_disclosure())
            if verified is None:
                return response
            return bind_workbench_response_v2(
                response,
                verified=verified,
                disclosure=executed_disclosure(
                    verified,
                    capability_id="sanger_alignment",
                    claim="Aligned the request-lifetime read to the verified selection",
                    algorithm_id="biopython_pairwise_aligner",
                    algorithm_version=package_version("biopython"),
                    input_scope="request_lifetime_read_and_verified_context",
                ),
            )
        except WorkbenchDesignError:
            raise
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="Sanger alignment provider failed for the requested context.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

    def _resolve_payload_context(
        self,
        payload: Any,
        *,
        purpose: str,
        transcript: str | None = None,
        species: str = "human",
        prefer_resolver: bool = True,
    ) -> tuple[SequenceContextResult, SequenceContext, VerifiedWorkbenchContext | None]:
        declared_v2 = getattr(payload, "design_context_v2", None)
        declared_v1 = getattr(payload, "design_context", None)
        if transcript is None:
            declared = declared_v2 or declared_v1
            if declared is not None:
                transcript = declared.variant.transcript
        if declared_v2 is not None:
            gene = declared_v2.variant.gene
            cdna = declared_v2.variant.cdna
            transcript = declared_v2.variant.transcript
        else:
            gene = getattr(payload, "gene", None)
            cdna = getattr(payload, "cdna", None)
        if not gene or not cdna:
            raise WorkbenchDesignError(
                code="workbench_context_identity_mismatch",
                message="A variant-bound context is required for this Workbench operation.",
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=["workbench_context_identity_mismatch"],
            )
        try:
            resolve_kwargs: dict[str, Any] = {"gene": gene, "cdna": cdna}
            if transcript is not None:
                resolve_kwargs["transcript"] = transcript
            if species != "human" or getattr(payload, "species", None) is not None:
                resolve_kwargs["species"] = species
            if prefer_resolver:
                resolve_kwargs["prefer_resolver"] = True
            sequence_result = self.sequence_context_service.resolve(**resolve_kwargs)
        except WorkbenchDesignError:
            raise
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message=f"Sequence context provider failed while preparing {purpose}.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc
        if declared_v2 is not None:
            verified = verify_workbench_design_context_v2(declared_v2, sequence_result)
            return sequence_result, verified.engine_context, verified
        context = self._sequence_context_or_error(sequence_result, purpose=purpose)
        return sequence_result, context, None

    def _verified_context_for_offtarget(
        self,
        payload: CrisprOffTargetRequest,
    ) -> VerifiedWorkbenchContext | None:
        if payload.design_context_v2 is None:
            return None
        _result, _context, verified = self._resolve_payload_context(
            payload,
            purpose="CRISPR off-target enumeration",
        )
        return verified

    def _verified_context_for_screening(
        self,
        payload: CrisprScreeningPrimerRequest,
    ) -> VerifiedWorkbenchContext | None:
        if payload.design_context_v2 is None:
            return None
        _result, _context, verified = self._resolve_payload_context(
            payload,
            purpose="CRISPR screening-primer design",
        )
        return verified

    def _verify_guide_identity(
        self,
        payload: CrisprOffTargetRequest,
        verified: VerifiedWorkbenchContext,
    ) -> None:
        identity = payload.guide_identity
        locus = payload.on_target_locus
        if identity is None or locus is None:
            raise WorkbenchDesignError(
                code="crispr_guide_identity_required",
                message="Context V2 off-target screening requires a verified guide identity.",
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=["crispr_guide_identity_required"],
            )
        expected_chrom = _normalize_chromosome(identity.locus.chromosome)
        if (
            _normalize_chromosome(locus.chromosome) != expected_chrom
            or locus.position != identity.locus.cut_position
            or locus.strand != identity.locus.strand
        ):
            raise WorkbenchDesignError(
                code="crispr_guide_locus_mismatch",
                message="The requested on-target locus does not match the verified guide identity.",
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=["crispr_guide_locus_mismatch"],
            )
        observed_guide = verified.sequence_at_genomic_interval(
            identity.locus.protospacer_start,
            identity.locus.protospacer_end,
            strand=identity.locus.strand,
        )
        observed_pam = verified.sequence_at_genomic_interval(
            identity.locus.pam_start,
            identity.locus.pam_end,
            strand=identity.locus.strand,
        )
        if observed_guide != identity.guide or observed_pam != identity.pam:
            raise WorkbenchDesignError(
                code="crispr_guide_sequence_mismatch",
                message="The verified guide/PAM is not present at its declared context locus.",
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=["crispr_guide_sequence_mismatch"],
            )

    def _unavailable_crispr_offtargets_v2(
        self,
        payload: CrisprOffTargetRequest,
        verified: VerifiedWorkbenchContext,
        *,
        warning: str,
        requirement: str,
    ) -> CrisprOffTargetResponse:
        response = CrisprOffTargetResponse(
            genome_build=payload.genome_build,
            sites=[],
            source_disclosure=SourceDisclosure(
                source_status="unavailable",
                provider_id="crispr_offtarget_index",
                provider_label="GRCh38 CRISPR off-target index",
                warnings=[warning],
                requirements=[requirement],
            ),
            guide_identity=payload.guide_identity,
        )
        return bind_workbench_response_v2(
            response,
            verified=verified,
            disclosure=unavailable_disclosure(
                capability_id="crispr_offtarget_enumeration",
                claim="Genome-wide CRISPR off-target enumeration is unavailable",
                input_scope="verified_guide_identity",
                requirements=[requirement],
                warnings=[warning],
            ),
        )

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
