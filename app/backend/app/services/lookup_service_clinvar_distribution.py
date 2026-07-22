from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from app.schemas.run import CuratedVariantsDistribution
from app.services.clinvar_local import (
    ClinVarLocalError,
    ClinVarLocalStore,
    build_clinvar_gene_distribution,
    build_clinvar_gene_distribution_from_index,
    inspect_clinvar_gene_distribution_index,
)
from app.services.local_evidence_orchestrator import LocalEvidenceRuntimeGate

CLINVAR_GENE_DISTRIBUTION_EXCLUDED_PENDING_INDEX = (
    "clinvar_gene_distribution_excluded_pending_index"
)


@lru_cache(maxsize=4)
def clinvar_distribution_store(vcf_path: str | None) -> ClinVarLocalStore:
    return ClinVarLocalStore(Path(vcf_path)) if vcf_path else ClinVarLocalStore()


def clinvar_gene_distribution_exclusion_warning(settings: Any) -> str | None:
    if LocalEvidenceRuntimeGate.from_settings(settings).allows(
        "lookup"
    ) and not clinvar_distribution_runtime_path(settings):
        return CLINVAR_GENE_DISTRIBUTION_EXCLUDED_PENDING_INDEX
    return None


def clinvar_distribution_runtime_path(settings: Any) -> str | None:
    if not LocalEvidenceRuntimeGate.from_settings(settings).allows("lookup"):
        return None
    try:
        inspection = inspect_clinvar_gene_distribution_index(
            settings,
            verify_checksum=False,
        )
    except Exception:
        return None
    if not inspection.ready:
        return None
    raw_path = Path(getattr(settings, "clinvar_gene_distribution_index_path"))
    resolved = (
        raw_path if raw_path.is_absolute() else Path(getattr(settings, "backend_root")) / raw_path
    )
    return str(resolved)


def local_clinvar_gene_distribution(
    gene: str,
    settings: Any,
    *,
    variant_id: str | None = None,
) -> CuratedVariantsDistribution:
    index_path = clinvar_distribution_runtime_path(settings)
    if index_path:
        return build_clinvar_gene_distribution_from_index(
            gene,
            index_path=Path(index_path),
            query_variant_id=variant_id,
        )
    if LocalEvidenceRuntimeGate.from_settings(settings).allows("lookup"):
        raise ClinVarLocalError(
            "gene_distribution_index_not_ready",
            "ClinVar gene-distribution index is not ready",
        )
    store = clinvar_distribution_store(None)
    return build_clinvar_gene_distribution(gene, store=store, query_variant_id=variant_id)
