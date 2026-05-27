from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.data_sources.registry import (
    DEFAULT_DATA_SOURCE_REGISTRY,
    DataSourceRecord,
    DataSourceRegistry,
    LicenseStatus,
)

POST_REFERENCE_DAY1_SOURCE_IDS: tuple[str, ...] = (
    "ncbi_dbsnp_gcf_000001405_40",
    "ncbi_clinvar_vcf",
    "repeatmasker_rmsk_bb",
    "ucsc_phylop100way_hg38",
    "ncbi_mane_grch38_v1_4_select_ensembl",
    "gencode_v45_annotation",
    "mondo_disease_ontology",
    "human_phenotype_ontology",
    "clingen_gene_validity",
    "gencc_download",
)


@dataclass(frozen=True)
class SourceAssetReadiness:
    source_id: str
    display_name: str
    files_or_api: tuple[str, ...]
    source_url: str | None
    source_url_status: str
    source_version: str | None
    checksum_plan: str | None
    terms_url: str | None
    terms_status: str | None
    storage_target: str
    temporary_staging: str
    adapter: str
    license_status: LicenseStatus
    download_approved: bool
    missing_requirements: tuple[str, ...]
    backend_owned_storage: bool
    requires_c_drive_staging: bool
    needs_actual_size_check: bool

    @property
    def ready_for_download_or_import(self) -> bool:
        return self.download_approved and not self.missing_requirements


def build_post_reference_source_readiness(
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    source_ids: Iterable[str] = POST_REFERENCE_DAY1_SOURCE_IDS,
) -> tuple[SourceAssetReadiness, ...]:
    return tuple(source_asset_readiness(registry.get(source_id)) for source_id in source_ids)


def source_asset_readiness(record: DataSourceRecord) -> SourceAssetReadiness:
    missing = list(_missing_requirements(record))
    return SourceAssetReadiness(
        source_id=record.source_id,
        display_name=record.display_name,
        files_or_api=record.files_or_api,
        source_url=record.source_url,
        source_url_status=record.source_url_status,
        source_version=record.source_version,
        checksum_plan=record.checksum_plan,
        terms_url=record.terms_url,
        terms_status=record.terms_status,
        storage_target=record.storage_target,
        temporary_staging=record.temporary_staging,
        adapter=record.adapter,
        license_status=record.license_status,
        download_approved=record.download_approved,
        missing_requirements=tuple(missing),
        backend_owned_storage=_is_backend_owned_storage(record),
        requires_c_drive_staging=record.temporary_staging == "stage_on_C_drive",
        needs_actual_size_check="check_actual_size" in record.temporary_staging,
    )


def _missing_requirements(record: DataSourceRecord) -> tuple[str, ...]:
    missing: list[str] = []
    if not record.source_url:
        missing.append("source_url")
    if record.source_url_status.startswith("required"):
        missing.append(record.source_url_status)
    if record.source_version_required and not record.source_version:
        missing.append("source_version_record")
    if record.checksum_required and not (record.current_local_md5 or record.checksum_plan):
        missing.append("checksum_or_manifest")
    if record.license_status is LicenseStatus.PENDING_TERMS_RECORD and not record.terms_url:
        missing.append("terms_url")
    if record.license_status is LicenseStatus.PENDING_TERMS_RECORD and not record.terms_status:
        missing.append("terms_status")
    if record.license_status is LicenseStatus.PENDING_TERMS_RECORD:
        missing.append("terms_review")
    if _is_backend_owned_storage(record):
        missing.append("backend_storage_policy_review")
    if _needs_reader_proof(record):
        missing.append("reader_compatibility_proof")
    if not record.download_approved:
        missing.append("explicit_download_or_import_approval")
    return tuple(dict.fromkeys(missing))


def _is_backend_owned_storage(record: DataSourceRecord) -> bool:
    return record.storage_target.startswith("supabase_") or record.storage_target in {
        "render_repo_candidate_after_review",
        "live_api_plus_source_cache",
    }


def _needs_reader_proof(record: DataSourceRecord) -> bool:
    adapter = record.adapter.lower()
    return any(
        token in adapter
        for token in (
            "after_compatibility_proof",
            "after_proof",
            "parser",
            "table",
        )
    )
