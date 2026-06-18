from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import re
from typing import Any, Iterable, Mapping, Protocol

from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRecord, DataSourceRegistry
from app.services.clinical_source_tables import (
    CLINGEN_GENE_VALIDITY_SOURCE_ID,
    GENCC_SOURCE_ID,
    HPO_SOURCE_ID,
    MONDO_SOURCE_ID,
    ClinicalSourceTableStore,
    ClinicalTableProvenance,
)

HG38_STORAGE_PILOT_ID = "hg38_2bit"
CLINVAR_STORAGE_PILOT_ID = "clinvar_vcf"
DBSNP_PHYLOP_EXISTING_OBJECTS_ID = "dbsnp_phylop"
STORAGE_PILOT_SOURCE_IDS = {
    HG38_STORAGE_PILOT_ID: "ucsc_hg38_2bit",
    CLINVAR_STORAGE_PILOT_ID: "ncbi_clinvar_vcf",
}
EXISTING_OBJECT_SET_SOURCE_IDS = {
    DBSNP_PHYLOP_EXISTING_OBJECTS_ID: (
        "ncbi_dbsnp_gcf_000001405_40",
        "ucsc_phylop100way_hg38",
    ),
}
DEFAULT_SOURCE_ASSET_BUCKET = "eamos-source-assets"

_PLANNED_RUNTIME_PATHS_BY_ROLE = {
    "dbsnp_bgzip_vcf": "/var/data/eamos/bio_assets/dbsnp/GCF_000001405.40.gz",
    "dbsnp_tabix_index": "/var/data/eamos/bio_assets/dbsnp/GCF_000001405.40.gz.tbi",
    "phylop_bigwig": "/var/data/eamos/bio_assets/phylop/hg38.phyloP100way.bw",
    "upstream_checksum": None,
}
_LOCAL_FILE_RUNTIME_ROLES = {
    "dbsnp_bgzip_vcf",
    "dbsnp_tabix_index",
    "phylop_bigwig",
}
_RUNTIME_DELIVERY_MODES_BY_ROLE = {
    "dbsnp_bgzip_vcf": (
        "object_storage_local_cache",
        "mounted_volume",
    ),
    "dbsnp_tabix_index": (
        "object_storage_local_cache",
        "mounted_volume",
    ),
    "phylop_bigwig": (
        "object_storage_local_cache",
        "mounted_volume",
    ),
}


class SourceImportError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


class SourceImportStore(Protocol):
    def record_source_version(self, **kwargs) -> str | None: ...

    def upsert_clinical_source_records(self, **kwargs) -> Mapping[str, int]: ...

    def upsert_source_asset_object(self, **kwargs) -> str | None: ...

    def upsert_source_asset_materialization(self, **kwargs) -> None: ...


@dataclass(frozen=True)
class SourceVersionRegistration:
    source_id: str
    source_name: str
    source_release: str | None
    source_url: str | None
    checksum_md5: str | None
    checksum_sha256: str | None
    license_status: str
    asset_role: str
    asset_path: str
    row_count: int | None
    metadata: dict[str, Any]
    source_version_id: str | None = None


@dataclass(frozen=True)
class ClinicalSourceImportBundle:
    source_versions: tuple[SourceVersionRegistration, ...]
    mondo_rows: tuple[dict[str, Any], ...]
    hpo_term_rows: tuple[dict[str, Any], ...]
    hpo_disease_rows: tuple[dict[str, Any], ...]
    hpo_gene_rows: tuple[dict[str, Any], ...]
    clingen_rows: tuple[dict[str, Any], ...]
    gencc_rows: tuple[dict[str, Any], ...]

    @property
    def row_counts(self) -> dict[str, int]:
        return {
            "clinical_mondo_diseases": len(self.mondo_rows),
            "clinical_hpo_terms": len(self.hpo_term_rows),
            "clinical_hpo_disease_phenotypes": len(self.hpo_disease_rows),
            "clinical_hpo_gene_phenotypes": len(self.hpo_gene_rows),
            "clinical_clingen_gene_validity": len(self.clingen_rows),
            "clinical_gencc_assertions": len(self.gencc_rows),
        }


@dataclass(frozen=True)
class ClinicalSourceImportResult:
    source_versions: tuple[SourceVersionRegistration, ...]
    row_counts: dict[str, int]
    applied: bool


@dataclass(frozen=True)
class SourceAssetObjectRegistration:
    source_id: str
    asset_role: str
    bucket_id: str
    object_path: str
    object_version: str | None
    content_type: str
    byte_size: int | None
    checksum_algorithm: str
    checksum_value: str
    upload_status: str
    approval_status: str
    license_status: str
    materialization_required: bool
    metadata: dict[str, Any]
    warnings: list[str]
    source_version_id: str | None = None
    source_asset_object_id: str | None = None


@dataclass(frozen=True)
class SourceAssetMaterializationRegistration:
    environment: str
    backend_runtime: str
    local_cache_path: str
    materialization_status: str
    byte_size: int | None
    checksum_algorithm: str | None
    checksum_value: str | None
    ready_marker: str | None
    verified_at: str | None
    fail_closed_reason: str | None
    metadata: dict[str, Any]
    warnings: list[str]
    source_asset_object_id: str | None = None


@dataclass(frozen=True)
class StoragePilotRegistration:
    pilot_id: str
    decision_reason: str
    source_version: SourceVersionRegistration
    object: SourceAssetObjectRegistration
    materialization: SourceAssetMaterializationRegistration


@dataclass(frozen=True)
class StoragePilotApplyResult:
    pilot: StoragePilotRegistration
    source_version_id: str | None
    source_asset_object_id: str | None
    applied: bool


@dataclass(frozen=True)
class ExistingSourceAssetMetadataRegistration:
    metadata_set_id: str
    source_versions: tuple[SourceVersionRegistration, ...]
    objects: tuple[SourceAssetObjectRegistration, ...]
    materializations: tuple[SourceAssetMaterializationRegistration, ...]
    storage_heads_verified: bool


@dataclass(frozen=True)
class ExistingSourceAssetMetadataApplyResult:
    metadata_set_id: str
    source_versions: tuple[SourceVersionRegistration, ...]
    source_asset_object_ids: tuple[str | None, ...]
    materialization_count: int
    applied: bool


def build_clinical_source_import_bundle(
    *,
    fixture_store: ClinicalSourceTableStore | None = None,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
) -> ClinicalSourceImportBundle:
    fixture_store = fixture_store or ClinicalSourceTableStore(registry=registry)
    provenance_by_path = {item.relative_path: item for item in fixture_store.provenance()}
    source_versions = tuple(
        _source_version_from_provenance(
            provenance,
            registry=registry,
            row_count=_row_count_for_provenance(fixture_store, provenance),
            asset_role="tier3_clinical_source_fixture",
            metadata={
                "import_scope": "dev_fixture",
                "relative_path": provenance.relative_path,
                "production_download_used": False,
            },
        )
        for provenance in fixture_store.provenance()
    )
    hpo_terms_provenance = _provenance_for_suffix(
        provenance_by_path,
        "hpo_terms_tiny.tsv",
    )

    return ClinicalSourceImportBundle(
        source_versions=source_versions,
        mondo_rows=tuple(
            {
                "source_version_key": record.provenance.relative_path,
                "mondo_id": record.mondo_id,
                "name": record.name,
                "xrefs": list(record.xrefs),
                "definition": record.definition,
                "provenance": _provenance_payload(record.provenance),
                "raw_payload": {
                    "mondo_id": record.mondo_id,
                    "name": record.name,
                    "xrefs": list(record.xrefs),
                    "definition": record.definition,
                },
            }
            for record in fixture_store.mondo_records()
        ),
        hpo_term_rows=tuple(
            {
                "source_version_key": hpo_terms_provenance.relative_path,
                "hpo_id": hpo_id,
                "label": label,
                "provenance": _provenance_payload(hpo_terms_provenance),
            }
            for hpo_id, label in sorted(fixture_store.hpo_terms().items())
        ),
        hpo_disease_rows=tuple(
            {
                "source_version_key": record.provenance.relative_path,
                "disease_id": record.disease_id,
                "disease_name": record.disease_name,
                "hpo_id": record.hpo_id,
                "hpo_label": record.hpo_label,
                "evidence": record.evidence,
                "frequency": record.frequency,
                "provenance": _provenance_payload(record.provenance),
                "raw_payload": {
                    "disease_id": record.disease_id,
                    "disease_name": record.disease_name,
                    "hpo_id": record.hpo_id,
                    "hpo_label": record.hpo_label,
                    "evidence": record.evidence,
                    "frequency": record.frequency,
                },
            }
            for record in fixture_store.hpo_disease_records()
        ),
        hpo_gene_rows=tuple(
            {
                "source_version_key": record.provenance.relative_path,
                "gene_symbol": record.gene_symbol,
                "gene_id": record.gene_id,
                "hpo_id": record.hpo_id,
                "hpo_label": record.hpo_label,
                "provenance": _provenance_payload(record.provenance),
                "raw_payload": {
                    "gene_symbol": record.gene_symbol,
                    "gene_id": record.gene_id,
                    "hpo_id": record.hpo_id,
                    "hpo_label": record.hpo_label,
                },
            }
            for record in fixture_store.hpo_gene_records()
        ),
        clingen_rows=tuple(
            {
                "source_version_key": record.provenance.relative_path,
                "gene_symbol": record.gene_symbol,
                "gene_hgnc_id": record.gene_hgnc_id,
                "disease_label": record.disease_label,
                "disease_id": record.disease_id,
                "mode_of_inheritance": record.mode_of_inheritance,
                "classification": record.classification,
                "source_date": record.source_date,
                "report_url": record.report_url,
                "provenance": _provenance_payload(record.provenance),
                "raw_payload": asdict(record)
                | {"provenance": _provenance_payload(record.provenance)},
            }
            for record in fixture_store.clingen_records()
        ),
        gencc_rows=tuple(
            {
                "source_version_key": record.provenance.relative_path,
                "gene_symbol": record.gene_symbol,
                "gene_curie": record.gene_curie,
                "disease_title": record.disease_title,
                "disease_curie": record.disease_curie,
                "assertion": record.assertion,
                "submitter": record.submitter,
                "source_date": record.source_date,
                "report_url": record.report_url,
                "provenance": _provenance_payload(record.provenance),
                "raw_payload": asdict(record)
                | {"provenance": _provenance_payload(record.provenance)},
            }
            for record in fixture_store.gencc_records()
        ),
    )


def apply_clinical_source_import_bundle(
    store: SourceImportStore,
    bundle: ClinicalSourceImportBundle,
) -> ClinicalSourceImportResult:
    source_version_ids: dict[str, str | None] = {}
    applied_versions: list[SourceVersionRegistration] = []
    for version in bundle.source_versions:
        source_version_id = store.record_source_version(
            source_id=version.source_id,
            source_name=version.source_name,
            source_release=version.source_release,
            source_url=version.source_url,
            checksum_md5=version.checksum_md5,
            checksum_sha256=version.checksum_sha256,
            license_status=version.license_status,
            asset_role=version.asset_role,
            asset_path=version.asset_path,
            row_count=version.row_count,
            metadata=version.metadata,
        )
        source_version_ids[version.asset_path] = source_version_id
        applied_versions.append(replace(version, source_version_id=source_version_id))

    rows = {
        "mondo_rows": _attach_source_version_ids(bundle.mondo_rows, source_version_ids),
        "hpo_term_rows": _attach_source_version_ids(bundle.hpo_term_rows, source_version_ids),
        "hpo_disease_rows": _attach_source_version_ids(bundle.hpo_disease_rows, source_version_ids),
        "hpo_gene_rows": _attach_source_version_ids(bundle.hpo_gene_rows, source_version_ids),
        "clingen_rows": _attach_source_version_ids(bundle.clingen_rows, source_version_ids),
        "gencc_rows": _attach_source_version_ids(bundle.gencc_rows, source_version_ids),
    }
    row_counts = dict(store.upsert_clinical_source_records(**rows))
    return ClinicalSourceImportResult(
        source_versions=tuple(applied_versions),
        row_counts=row_counts,
        applied=True,
    )


def build_storage_pilot_registration(
    *,
    pilot_id: str = HG38_STORAGE_PILOT_ID,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    bucket_id: str = DEFAULT_SOURCE_ASSET_BUCKET,
    environment: str = "dev-local",
) -> StoragePilotRegistration:
    if pilot_id not in STORAGE_PILOT_SOURCE_IDS:
        raise SourceImportError(
            "unknown_storage_pilot",
            "storage pilot must be one of the approved pilot ids",
            {"pilot_id": pilot_id, "approved": sorted(STORAGE_PILOT_SOURCE_IDS)},
        )
    record = registry.get(STORAGE_PILOT_SOURCE_IDS[pilot_id])
    checksum_algorithm, checksum_value = _storage_checksum(record)
    if checksum_value is None:
        raise SourceImportError(
            "storage_pilot_checksum_unavailable",
            "storage pilot requires a recorded checksum before object metadata can be registered",
            {"pilot_id": pilot_id, "source_id": record.source_id},
        )
    file_name = record.files_or_api[0]
    source_release = _storage_source_release(record)
    object_path = (
        f"{record.source_id}/{_slug(source_release)}/"
        f"{checksum_algorithm}-{checksum_value}/{file_name}"
    )
    decision_reason = (
        "hg38.2bit is the first private Storage pilot because the registry already "
        "has a verified local size and MD5; ClinVar VCF still lacks an approved "
        "downloaded checksum/materialization in this repo."
    )

    source_version = SourceVersionRegistration(
        source_id=record.source_id,
        source_name=record.display_name,
        source_release=source_release,
        source_url=record.source_url,
        checksum_md5=checksum_value if checksum_algorithm == "md5" else None,
        checksum_sha256=checksum_value if checksum_algorithm == "sha256" else None,
        license_status=record.license_status.value,
        asset_role="tier1_private_storage_pilot",
        asset_path=object_path,
        row_count=None,
        metadata={
            "pilot_id": pilot_id,
            "mode": "metadata_only_private_storage_pilot",
            "storage_upload_performed": False,
            "bucket_creation_performed": False,
            "source_version_required": record.source_version_required,
            "reader_requires_local_path": record.reader_requires_local_path,
        },
    )
    source_object = SourceAssetObjectRegistration(
        source_id=record.source_id,
        asset_role="reference_genome_2bit",
        bucket_id=bucket_id,
        object_path=object_path,
        object_version=source_release,
        content_type="application/octet-stream",
        byte_size=record.actual_size_bytes_local,
        checksum_algorithm=checksum_algorithm,
        checksum_value=checksum_value,
        upload_status="metadata_only",
        approval_status="pending_storage_approval",
        license_status=record.license_status.value,
        materialization_required=True,
        metadata={
            "pilot_id": pilot_id,
            "file_name": file_name,
            "source_url": record.source_url,
            "expected_size": record.expected_size,
            "current_local_path": record.current_local_path,
            "storage_upload_performed": False,
            "frontend_direct_access_allowed": False,
        },
        warnings=[
            "storage_object_not_uploaded",
            "bucket_creation_not_performed",
            "frontend_storage_reads_blocked",
        ],
    )
    materialization = SourceAssetMaterializationRegistration(
        environment=environment,
        backend_runtime="render_backend",
        local_cache_path=record.current_local_path or object_path,
        materialization_status="not_materialized",
        byte_size=record.actual_size_bytes_local,
        checksum_algorithm=checksum_algorithm,
        checksum_value=checksum_value,
        ready_marker=None,
        verified_at=None,
        fail_closed_reason="private_storage_object_not_uploaded",
        metadata={
            "pilot_id": pilot_id,
            "reader_requires_local_path": record.reader_requires_local_path,
            "runtime_delivery_modes": list(record.runtime_delivery_modes),
        },
        warnings=["reader_must_fail_closed_until_materialized_and_verified"],
    )
    return StoragePilotRegistration(
        pilot_id=pilot_id,
        decision_reason=decision_reason,
        source_version=source_version,
        object=source_object,
        materialization=materialization,
    )


def apply_storage_pilot_registration(
    store: SourceImportStore,
    pilot: StoragePilotRegistration,
) -> StoragePilotApplyResult:
    source_version_id = store.record_source_version(
        source_id=pilot.source_version.source_id,
        source_name=pilot.source_version.source_name,
        source_release=pilot.source_version.source_release,
        source_url=pilot.source_version.source_url,
        checksum_md5=pilot.source_version.checksum_md5,
        checksum_sha256=pilot.source_version.checksum_sha256,
        license_status=pilot.source_version.license_status,
        asset_role=pilot.source_version.asset_role,
        asset_path=pilot.source_version.asset_path,
        row_count=pilot.source_version.row_count,
        metadata=pilot.source_version.metadata,
    )
    source_asset_object_id = store.upsert_source_asset_object(
        source_version_id=source_version_id,
        source_id=pilot.object.source_id,
        asset_role=pilot.object.asset_role,
        bucket_id=pilot.object.bucket_id,
        object_path=pilot.object.object_path,
        object_version=pilot.object.object_version,
        content_type=pilot.object.content_type,
        byte_size=pilot.object.byte_size,
        checksum_algorithm=pilot.object.checksum_algorithm,
        checksum_value=pilot.object.checksum_value,
        upload_status=pilot.object.upload_status,
        approval_status=pilot.object.approval_status,
        license_status=pilot.object.license_status,
        materialization_required=pilot.object.materialization_required,
        metadata=pilot.object.metadata,
        warnings=pilot.object.warnings,
    )
    store.upsert_source_asset_materialization(
        source_asset_object_id=source_asset_object_id,
        environment=pilot.materialization.environment,
        backend_runtime=pilot.materialization.backend_runtime,
        local_cache_path=pilot.materialization.local_cache_path,
        materialization_status=pilot.materialization.materialization_status,
        byte_size=pilot.materialization.byte_size,
        checksum_algorithm=pilot.materialization.checksum_algorithm,
        checksum_value=pilot.materialization.checksum_value,
        ready_marker=pilot.materialization.ready_marker,
        verified_at=pilot.materialization.verified_at,
        fail_closed_reason=pilot.materialization.fail_closed_reason,
        metadata=pilot.materialization.metadata,
        warnings=pilot.materialization.warnings,
    )
    return StoragePilotApplyResult(
        pilot=pilot,
        source_version_id=source_version_id,
        source_asset_object_id=source_asset_object_id,
        applied=True,
    )


def build_existing_source_asset_metadata_registration(
    *,
    metadata_set_id: str = DBSNP_PHYLOP_EXISTING_OBJECTS_ID,
    upload_items: Iterable[Any],
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    environment: str = "sg-render",
    backend_runtime: str = "render_backend",
    storage_heads_verified: bool = False,
) -> ExistingSourceAssetMetadataRegistration:
    if metadata_set_id not in EXISTING_OBJECT_SET_SOURCE_IDS:
        raise SourceImportError(
            "unknown_existing_object_set",
            "existing object metadata set must be approved before registration",
            {
                "metadata_set_id": metadata_set_id,
                "approved": sorted(EXISTING_OBJECT_SET_SOURCE_IDS),
            },
        )
    source_ids = EXISTING_OBJECT_SET_SOURCE_IDS[metadata_set_id]
    items = tuple(item for item in upload_items if getattr(item, "source_id", None) in source_ids)
    if not items:
        raise SourceImportError(
            "existing_object_metadata_items_missing",
            "no upload-plan items were available for the requested metadata set",
            {"metadata_set_id": metadata_set_id, "source_ids": list(source_ids)},
        )
    blocked = [
        {
            "source_id": getattr(item, "source_id", None),
            "asset_id": getattr(item, "asset_id", None),
            "status": _status_value(getattr(item, "status", None)),
        }
        for item in items
        if _status_value(getattr(item, "status", None)) != "planned"
    ]
    if blocked:
        raise SourceImportError(
            "existing_object_metadata_plan_not_ready",
            "existing object metadata registration requires local files and manifests",
            {"blocked": blocked},
        )
    missing_checksums = [
        {
            "source_id": item.source_id,
            "asset_id": item.asset_id,
        }
        for item in items
        if not item.sha256 and not item.md5
    ]
    if missing_checksums:
        raise SourceImportError(
            "existing_object_metadata_checksum_missing",
            "existing object metadata registration requires MD5 or SHA256 for every object",
            {"items": missing_checksums},
        )

    source_versions: list[SourceVersionRegistration] = []
    for source_id in source_ids:
        record = registry.get(source_id)
        source_items = tuple(item for item in items if item.source_id == source_id)
        source_versions.append(
            SourceVersionRegistration(
                source_id=record.source_id,
                source_name=record.display_name,
                source_release=record.source_version,
                source_url=record.source_url,
                checksum_md5=None,
                checksum_sha256=None,
                license_status=record.license_status.value,
                asset_role="tier1_existing_private_storage_object_set",
                asset_path=f"supabase://{_first_bucket_id(source_items)}/{record.source_id}",
                row_count=None,
                metadata={
                    "metadata_set_id": metadata_set_id,
                    "mode": "existing_private_storage_object_metadata",
                    "storage_heads_verified": storage_heads_verified,
                    "source_url_status": record.source_url_status,
                    "terms_url": record.terms_url,
                    "terms_status": record.terms_status,
                    "storage_policy_reviewed": record.storage_policy_reviewed,
                    "reader_compatibility_proofed": record.reader_compatibility_proofed,
                    "asset_count": len(source_items),
                    "assets": [_source_version_asset_metadata(item) for item in source_items],
                },
            )
        )

    objects: list[SourceAssetObjectRegistration] = []
    materializations: list[SourceAssetMaterializationRegistration] = []
    for item in items:
        record = registry.get(item.source_id)
        object_status = "verified" if storage_heads_verified else "uploaded"
        object_warnings = (
            [] if storage_heads_verified else ["storage_head_not_verified_in_this_run"]
        )
        objects.append(
            SourceAssetObjectRegistration(
                source_id=item.source_id,
                asset_role=item.role,
                bucket_id=item.bucket_id,
                object_path=item.object_path,
                object_version=record.source_version,
                content_type=item.content_type,
                byte_size=item.byte_size,
                checksum_algorithm="sha256" if item.sha256 else "md5",
                checksum_value=item.sha256 or item.md5,
                upload_status=object_status,
                approval_status="approved",
                license_status=record.license_status.value,
                materialization_required=_materialization_required_for_role(item.role),
                metadata={
                    "metadata_set_id": metadata_set_id,
                    "asset_id": item.asset_id,
                    "manifest_object_path": item.manifest_object_path,
                    "md5": item.md5,
                    "sha256": item.sha256,
                    "source_url": record.source_url,
                    "source_url_status": record.source_url_status,
                    "terms_url": record.terms_url,
                    "terms_status": record.terms_status,
                    "storage_upload_performed_by_this_import": False,
                    "storage_heads_verified": storage_heads_verified,
                    "frontend_direct_access_allowed": False,
                    "public_access_allowed": False,
                },
                warnings=object_warnings,
            )
        )
        materializations.append(
            SourceAssetMaterializationRegistration(
                environment=environment,
                backend_runtime=backend_runtime,
                local_cache_path=_planned_runtime_path(item),
                materialization_status="not_materialized",
                byte_size=item.byte_size,
                checksum_algorithm="sha256" if item.sha256 else "md5",
                checksum_value=item.sha256 or item.md5,
                ready_marker=None,
                verified_at=None,
                fail_closed_reason="render_disk_seed_not_performed",
                metadata={
                    "metadata_set_id": metadata_set_id,
                    "asset_id": item.asset_id,
                    "asset_role": item.role,
                    "reader_requires_local_path": _reader_requires_local_path(item.role, record),
                    "runtime_delivery_modes": list(_runtime_delivery_modes(item.role, record)),
                    "render_disk_seed_performed": False,
                },
                warnings=["reader_must_fail_closed_until_render_disk_seed_verified"],
            )
        )

    return ExistingSourceAssetMetadataRegistration(
        metadata_set_id=metadata_set_id,
        source_versions=tuple(source_versions),
        objects=tuple(objects),
        materializations=tuple(materializations),
        storage_heads_verified=storage_heads_verified,
    )


def apply_existing_source_asset_metadata_registration(
    store: SourceImportStore,
    registration: ExistingSourceAssetMetadataRegistration,
) -> ExistingSourceAssetMetadataApplyResult:
    source_version_ids: dict[str, str | None] = {}
    applied_versions: list[SourceVersionRegistration] = []
    for version in registration.source_versions:
        source_version_id = store.record_source_version(
            source_id=version.source_id,
            source_name=version.source_name,
            source_release=version.source_release,
            source_url=version.source_url,
            checksum_md5=version.checksum_md5,
            checksum_sha256=version.checksum_sha256,
            license_status=version.license_status,
            asset_role=version.asset_role,
            asset_path=version.asset_path,
            row_count=version.row_count,
            metadata=version.metadata,
        )
        source_version_ids[version.source_id] = source_version_id
        applied_versions.append(replace(version, source_version_id=source_version_id))

    object_ids: list[str | None] = []
    for source_object, materialization in zip(
        registration.objects,
        registration.materializations,
        strict=True,
    ):
        source_asset_object_id = store.upsert_source_asset_object(
            source_version_id=source_version_ids.get(source_object.source_id),
            source_id=source_object.source_id,
            asset_role=source_object.asset_role,
            bucket_id=source_object.bucket_id,
            object_path=source_object.object_path,
            object_version=source_object.object_version,
            content_type=source_object.content_type,
            byte_size=source_object.byte_size,
            checksum_algorithm=source_object.checksum_algorithm,
            checksum_value=source_object.checksum_value,
            upload_status=source_object.upload_status,
            approval_status=source_object.approval_status,
            license_status=source_object.license_status,
            materialization_required=source_object.materialization_required,
            metadata=source_object.metadata,
            warnings=source_object.warnings,
        )
        object_ids.append(source_asset_object_id)
        store.upsert_source_asset_materialization(
            source_asset_object_id=source_asset_object_id,
            environment=materialization.environment,
            backend_runtime=materialization.backend_runtime,
            local_cache_path=materialization.local_cache_path,
            materialization_status=materialization.materialization_status,
            byte_size=materialization.byte_size,
            checksum_algorithm=materialization.checksum_algorithm,
            checksum_value=materialization.checksum_value,
            ready_marker=materialization.ready_marker,
            verified_at=materialization.verified_at,
            fail_closed_reason=materialization.fail_closed_reason,
            metadata=materialization.metadata,
            warnings=materialization.warnings,
        )

    return ExistingSourceAssetMetadataApplyResult(
        metadata_set_id=registration.metadata_set_id,
        source_versions=tuple(applied_versions),
        source_asset_object_ids=tuple(object_ids),
        materialization_count=len(registration.materializations),
        applied=True,
    )


def clinical_bundle_report(bundle: ClinicalSourceImportBundle) -> dict[str, Any]:
    return {
        "mode": "tier3_clinical_source_fixture_import",
        "source_versions": [asdict(version) for version in bundle.source_versions],
        "row_counts": bundle.row_counts,
        "guardrails": _guardrails(),
    }


def storage_pilot_report(pilot: StoragePilotRegistration) -> dict[str, Any]:
    return {
        "mode": "private_storage_metadata_pilot",
        "pilot_id": pilot.pilot_id,
        "decision_reason": pilot.decision_reason,
        "source_version": asdict(pilot.source_version),
        "object": asdict(pilot.object),
        "materialization": asdict(pilot.materialization),
        "guardrails": _guardrails(),
    }


def existing_source_asset_metadata_report(
    registration: ExistingSourceAssetMetadataRegistration,
) -> dict[str, Any]:
    return {
        "mode": "existing_private_storage_object_metadata",
        "metadata_set_id": registration.metadata_set_id,
        "storage_heads_verified": registration.storage_heads_verified,
        "source_versions": [asdict(version) for version in registration.source_versions],
        "objects": [asdict(source_object) for source_object in registration.objects],
        "materializations": [
            asdict(materialization) for materialization in registration.materializations
        ],
        "guardrails": _guardrails()
        | {
            "render_disk_seed": "not_used",
            "local_evidence_enablement": "not_used",
            "runtime_provider_flip": "not_used",
        },
    }


def _source_version_from_provenance(
    provenance: ClinicalTableProvenance,
    *,
    registry: DataSourceRegistry,
    row_count: int,
    asset_role: str,
    metadata: dict[str, Any],
) -> SourceVersionRegistration:
    record = registry.get(provenance.source_id)
    return SourceVersionRegistration(
        source_id=provenance.source_id,
        source_name=record.display_name,
        source_release=provenance.source_version,
        source_url=record.source_url,
        checksum_md5=None,
        checksum_sha256=provenance.checksum,
        license_status=record.license_status.value,
        asset_role=asset_role,
        asset_path=provenance.relative_path,
        row_count=row_count,
        metadata=metadata,
    )


def _row_count_for_provenance(
    fixture_store: ClinicalSourceTableStore,
    provenance: ClinicalTableProvenance,
) -> int:
    if provenance.source_id == MONDO_SOURCE_ID:
        return len(fixture_store.mondo_records())
    if provenance.source_id == CLINGEN_GENE_VALIDITY_SOURCE_ID:
        return len(fixture_store.clingen_records())
    if provenance.source_id == GENCC_SOURCE_ID:
        return len(fixture_store.gencc_records())
    if provenance.source_id == HPO_SOURCE_ID:
        if provenance.relative_path.endswith("hpo_terms_tiny.tsv"):
            return len(fixture_store.hpo_terms())
        if provenance.relative_path.endswith("phenotype_tiny.hpoa"):
            return len(fixture_store.hpo_disease_records())
        if provenance.relative_path.endswith("genes_to_phenotype_tiny.txt"):
            return len(fixture_store.hpo_gene_records())
    raise SourceImportError(
        "unknown_clinical_provenance",
        "cannot map clinical source provenance to an import row count",
        {"source_id": provenance.source_id, "relative_path": provenance.relative_path},
    )


def _provenance_for_suffix(
    provenance_by_path: Mapping[str, ClinicalTableProvenance],
    suffix: str,
) -> ClinicalTableProvenance:
    for path, provenance in provenance_by_path.items():
        if path.endswith(suffix):
            return provenance
    raise SourceImportError(
        "clinical_provenance_missing",
        "expected clinical fixture provenance was not present",
        {"suffix": suffix},
    )


def _provenance_payload(provenance: ClinicalTableProvenance) -> dict[str, Any]:
    return asdict(provenance)


def _attach_source_version_ids(
    rows: tuple[dict[str, Any], ...],
    source_version_ids: Mapping[str, str | None],
) -> tuple[dict[str, Any], ...]:
    resolved: list[dict[str, Any]] = []
    for row in rows:
        source_version_key = str(row["source_version_key"])
        payload = {key: value for key, value in row.items() if key != "source_version_key"}
        payload["source_version_id"] = source_version_ids.get(source_version_key)
        resolved.append(payload)
    return tuple(resolved)


def _storage_checksum(record: DataSourceRecord) -> tuple[str, str | None]:
    if record.current_local_md5:
        return ("md5", record.current_local_md5.lower())
    return ("sha256", None)


def _storage_source_release(record: DataSourceRecord) -> str:
    if record.source_id == "ucsc_hg38_2bit":
        return "hg38"
    if record.source_version:
        return record.source_version
    return "unversioned"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-").lower()
    return slug or "unversioned"


def _status_value(value: Any) -> str:
    status = getattr(value, "value", value)
    return str(status) if status is not None else ""


def _first_bucket_id(items: tuple[Any, ...]) -> str:
    if not items:
        return DEFAULT_SOURCE_ASSET_BUCKET
    return str(items[0].bucket_id)


def _source_version_asset_metadata(item: Any) -> dict[str, Any]:
    return {
        "asset_id": item.asset_id,
        "role": item.role,
        "bucket_id": item.bucket_id,
        "object_path": item.object_path,
        "manifest_object_path": item.manifest_object_path,
        "byte_size": item.byte_size,
        "md5": item.md5,
        "sha256": item.sha256,
    }


def _materialization_required_for_role(role: str) -> bool:
    return role != "upstream_checksum"


def _planned_runtime_path(item: Any) -> str:
    if item.role == "upstream_checksum":
        return f"not_materialized://{item.source_id}/{item.asset_id}"
    planned = _PLANNED_RUNTIME_PATHS_BY_ROLE.get(item.role)
    if planned is not None:
        return planned
    return f"not_materialized://{item.source_id}/{item.asset_id}"


def _reader_requires_local_path(role: str, record: DataSourceRecord) -> bool:
    return role in _LOCAL_FILE_RUNTIME_ROLES or record.reader_requires_local_path


def _runtime_delivery_modes(role: str, record: DataSourceRecord) -> tuple[str, ...]:
    return _RUNTIME_DELIVERY_MODES_BY_ROLE.get(role, record.runtime_delivery_modes)


def _guardrails() -> dict[str, str]:
    return {
        "production_downloads": "not_used",
        "storage_bucket_creation": "not_used",
        "storage_uploads": "not_used",
        "frontend_direct_sql": "blocked",
        "public_bucket": "blocked",
        "browser_roles": "no_grants",
        "restricted_predictor_unlocks": "not_used",
    }
