from __future__ import annotations

# ruff: noqa: F401

# Compatibility facade. Keep existing app.services.workbench_design imports stable
# while implementation responsibilities live in focused workbench_design_* modules.
from app.services.trace_parser import parse_ab1_base64, parse_ab1_bytes
from app.services.workbench_design_alignment import (
    AlignmentCell,
    LocalSangerAlignmentProvider,
    _align_sequences,
    _bio_pairwise_alignment,
    _cells_from_bio_alignment,
    _parse_ab1_trace,
    _parse_ab1_trace_bytes,
    _parse_alignment_sequence,
)
from app.services.workbench_design_common import (
    ALIGN_GAP_SCORE,
    ALIGN_MATCH_SCORE,
    ALIGN_MAX_MATRIX_CELLS,
    ALIGN_MAX_SEQUENCE_BASES,
    ALIGN_MISMATCH_SCORE,
    HTTP_UNPROCESSABLE_ENTITY,
    PRIMER_SPECIFICITY_TEMPLATE,
    PRIMER_SPECIFICITY_UCSC_ISPCR,
    WORKBENCH_PROVIDER_FAILED_PREFIX,
    WORKBENCH_PROVIDER_MALFORMED,
    WORKBENCH_PROVIDER_UNAVAILABLE,
    WORKBENCH_SERVICE_UNAVAILABLE,
    WorkbenchDesignError,
)
from app.services.workbench_design_fixture import WorkbenchFixtureProvider
from app.services.workbench_design_primer import (
    PRIMER_MAX_TEMPLATE_BASES,
    IsPcrProduct,
    LocalIsPcrSpecificityProvider,
    Primer3PrimerProvider,
    PrimerAmplicon,
    PrimerSecondaryStructureAssessment,
    PrimerSpecificityProvider,
    PrimerSpecificityResult,
    TemplateAmpliconSpecificityProvider,
    _default_specificity_provider,
    _primer3_global_args,
    _primer3_pairs,
    _template_amplicons,
)
from app.services.workbench_design_primer_snp import (
    PRIMER_SNP_MASK_MAX_INTERVAL_BASES,
    PRIMER_SNP_MASK_MAX_RECORDS,
    IndexedDbSnpPrimerSnpMaskingProvider,
    LocalDbSnpPrimerSnpMaskingProvider,
    NoopPrimerSnpMaskingProvider,
    PrimerSnpMaskingResult,
    PrimerSnpMaskingVariant,
    default_snp_masking_provider as _default_snp_masking_provider,
)
from app.services.workbench_design_protocols import (
    AlignProvider,
    CrisprDesignProvider,
    CrisprOffTargetProvider,
    PrimerDesignProvider,
)
from app.services.workbench_design_service import WorkbenchDesignService
