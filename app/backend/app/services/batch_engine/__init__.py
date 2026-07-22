"""WES/panel-first batch execution primitives.

The package deliberately owns streaming intake, normalization, filtering, and
lease mechanics separately from the HTTP/service compatibility layer.  Runtime
composition may inject approved artifacts later without weakening these seams.
"""

from app.services.batch_engine.intake import (
    DEFAULT_MAX_RAW_RECORDS,
    DEFAULT_MAX_INTAKE_SECONDS,
    StagedVcf,
    StreamedVariant,
    cleanup_expired_staged_vcfs,
    iter_staged_variants,
    remove_staged_vcf,
    stage_vcf_file,
)
from app.services.batch_engine.normalization import (
    BatchAlleleNormalizer,
    BatchNormalizationFailed,
    BatchNormalizationUnavailable,
    BcftoolsBatchNormalizer,
    UnavailableBatchNormalizer,
)
from app.services.batch_engine.filters import (
    BatchFilterUnavailable,
    BatchPreFilterResult,
    BatchPreFilterStats,
    BatchResourceLimitExceeded,
    GenomicInterval,
    filter_post_annotation,
    filter_pre_annotation,
    iter_pre_annotation,
)
from app.services.batch_engine.runtime import (
    SnapshotCursorCodec,
    build_source_snapshot,
    mounted_interval_capability,
    unavailable_interval_capability,
)
from app.services.batch_engine.leases import BatchLease, BatchLeaseStore

__all__ = [
    "DEFAULT_MAX_RAW_RECORDS",
    "DEFAULT_MAX_INTAKE_SECONDS",
    "StagedVcf",
    "StreamedVariant",
    "cleanup_expired_staged_vcfs",
    "iter_staged_variants",
    "remove_staged_vcf",
    "stage_vcf_file",
    "BatchAlleleNormalizer",
    "BatchNormalizationFailed",
    "BatchNormalizationUnavailable",
    "BcftoolsBatchNormalizer",
    "UnavailableBatchNormalizer",
    "BatchFilterUnavailable",
    "BatchPreFilterResult",
    "BatchPreFilterStats",
    "BatchResourceLimitExceeded",
    "GenomicInterval",
    "filter_post_annotation",
    "filter_pre_annotation",
    "iter_pre_annotation",
    "SnapshotCursorCodec",
    "build_source_snapshot",
    "mounted_interval_capability",
    "unavailable_interval_capability",
    "BatchLease",
    "BatchLeaseStore",
]
