from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.core.config import Settings
from app.schemas.workbench import (
    CrisprScreeningPrimerRequest,
    PrimerRequest,
    SourceDisclosure,
)
from app.services.crispr_design import (
    CRISPR_PROVIDER_CRISPRSCORE_R,
    CRISPR_PROVIDER_LOCAL_DETERMINISTIC,
    CrisprScoreRAdapter,
    CrisprScoreRBackedCrisprProvider,
    LocalDeterministicCrisprProvider,
)
from app.services.crispr_offtarget_screening import (
    CRISPR_OFFTARGET_PROVIDER_AUTO,
    CRISPR_OFFTARGET_PROVIDER_INDEXED_SQLITE,
    CRISPR_OFFTARGET_PROVIDER_MOCK,
    IndexedSqliteCrisprOffTargetProvider,
    MockCasOffinderOffTargetProvider,
    SCREENING_REFERENCE_WINDOW_UNAVAILABLE_WARNING,
    UnavailableCrisprOffTargetProvider,
)
from app.services.workbench_design_common import WorkbenchModel, _settings_path
from app.services.workbench_design_context import VerifiedWorkbenchContext
from app.services.workbench_design_primer import (
    LocalIsPcrSpecificityProvider,
    Primer3PrimerProvider,
    TemplateAmpliconSpecificityProvider,
    _primer3_global_args,
)
from app.services.workbench_design_primer_snp import (
    IndexedDbSnpPrimerSnpMaskingProvider,
    LocalDbSnpPrimerSnpMaskingProvider,
    NoopPrimerSnpMaskingProvider,
)
from app.services.workbench_design_protocols import (
    CrisprDesignProvider,
    CrisprOffTargetProvider,
    PrimerDesignProvider,
)


def with_source_disclosure(
    response: WorkbenchModel,
    disclosure: SourceDisclosure,
) -> WorkbenchModel:
    if getattr(response, "source_disclosure", None) is not None:
        return response
    return response.model_copy(update={"source_disclosure": disclosure})


def primer_source_disclosure(*, warnings: list[str] | None = None) -> SourceDisclosure:
    return SourceDisclosure(
        source_status="local_provider",
        provider_id="primer3_template_specificity",
        provider_label="Primer3 with template specificity screen",
        cache_status="runtime",
        warnings=list(warnings or []),
        requirements=["primer3_py"],
    )


def crispr_design_source_disclosure(provider: CrisprDesignProvider) -> SourceDisclosure:
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


def screening_primer_source_disclosure(
    primers: list[Any],
    *,
    warnings: list[str],
) -> SourceDisclosure:
    template_sources = {getattr(primer, "template_source", "") for primer in primers}
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


def align_reference_source_disclosure(
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


def align_source_disclosure(*, warnings: list[str] | None = None) -> SourceDisclosure:
    return SourceDisclosure(
        source_status="local_provider",
        provider_id="local_sanger_aligner",
        provider_label="Local Sanger alignment provider",
        cache_status="runtime",
        warnings=list(warnings or []),
    )


def trace_source_disclosure(*, warnings: list[str] | None = None) -> SourceDisclosure:
    return SourceDisclosure(
        source_status="local_provider",
        provider_id="ab1_trace_parser",
        provider_label="Local AB1 trace parser",
        cache_status="runtime",
        warnings=list(warnings or []),
        requirements=["ab1_input"],
    )


def primer_execution_warnings(
    provider: PrimerDesignProvider,
    payload: PrimerRequest | CrisprScreeningPrimerRequest | None = None,
) -> list[str]:
    if not isinstance(provider, Primer3PrimerProvider):
        return ["primer_provider_execution_metadata_unavailable"]
    warnings: list[str] = []
    if isinstance(provider.specificity_provider, TemplateAmpliconSpecificityProvider):
        warnings.append("specificity_scope:verified_template_only")
    elif isinstance(provider.specificity_provider, LocalIsPcrSpecificityProvider):
        warnings.append("specificity_scope:whole_genome_hg38_ispcr")
    else:
        warnings.append("specificity_scope:provider_declared")
    if isinstance(provider.snp_masking_provider, NoopPrimerSnpMaskingProvider):
        warnings.append("dbsnp_masking:not_assessed")
    elif isinstance(
        provider.snp_masking_provider,
        (LocalDbSnpPrimerSnpMaskingProvider, IndexedDbSnpPrimerSnpMaskingProvider),
    ):
        warnings.append("dbsnp_masking:local_source")
    else:
        warnings.append("dbsnp_masking:provider_declared")
    if payload is not None:
        warnings.append(f"primer3_constraint_profile:{payload.mode}.v1")
        global_args = _primer3_global_args(
            payload,
            product_min=max(1, payload.product_size_min),
            product_max=max(payload.product_size_min, payload.product_size_max),
        )
        warnings.extend(
            f"primer3_global_arg:{key}={value}" for key, value in sorted(global_args.items())
        )
    return warnings


def primer_execution_requirements(provider: PrimerDesignProvider) -> list[str]:
    if not isinstance(provider, Primer3PrimerProvider):
        return ["primer_provider_execution_metadata"]
    requirements: list[str] = []
    if isinstance(provider.specificity_provider, TemplateAmpliconSpecificityProvider):
        requirements.append("whole_genome_ispcr_assets")
    if isinstance(provider.snp_masking_provider, NoopPrimerSnpMaskingProvider):
        requirements.append("dbsnp_primer_mask")
    return requirements


class VerifiedReferenceWindowProvider:
    def __init__(self, verified: VerifiedWorkbenchContext) -> None:
        self.verified = verified

    def get_sequence(
        self,
        chrom: str,
        start: int,
        end: int,
        build: str | None = None,
    ) -> Any:
        if normalize_chromosome(chrom) != normalize_chromosome(
            self.verified.context.reference.chrom
        ) or (build or "GRCh38").upper() not in {"GRCH38", "HG38"}:
            raise ValueError("screening reference request is outside the verified basis")
        sequence = self.verified.reference_sequence_at_genomic_interval(start, end)
        if sequence is None:
            raise ValueError("screening reference request is outside the verified basis")
        return SimpleNamespace(sequence=sequence)


def normalize_chromosome(chromosome: str) -> str:
    raw = chromosome.strip()
    if raw.lower().startswith("chr"):
        raw = raw[3:]
    raw = raw.upper()
    if raw == "MT":
        raw = "M"
    return f"chr{raw}"


def default_crispr_provider(settings: Settings | None) -> CrisprDesignProvider:
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


def default_crispr_offtarget_provider(
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
        if live_design_enabled:
            return UnavailableCrisprOffTargetProvider()
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
        return (
            UnavailableCrisprOffTargetProvider()
            if live_design_enabled
            else MockCasOffinderOffTargetProvider()
        )

    raise ValueError(f"Unknown CRISPR off-target provider: {provider_name}")
