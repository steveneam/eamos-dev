from __future__ import annotations

from dataclasses import replace
import inspect

import pytest

from app.data_sources import (
    DEFAULT_DATA_SOURCE_REGISTRY,
    DEFAULT_SOURCE_RECORDS,
    DataSourceRegistry,
    LicenseStatus,
    RegistryValidationError,
)
from app.data_sources import registry as registry_module
from app.data_sources.registry import RESTRICTED_PREDICTOR_SOURCE_IDS


def test_default_registry_exposes_expected_priority_sources() -> None:
    registry = DEFAULT_DATA_SOURCE_REGISTRY

    hg38 = registry.get("ucsc_hg38_2bit")
    assert hg38.priority == "p0_first_asset_proof"
    assert hg38.source_url == "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/hg38.2bit"
    assert hg38.current_local_path == "app/backend/data/bio_assets/genomes/hg38.2bit"
    assert hg38.actual_size_bytes_local == 835393456
    assert hg38.current_local_md5 == "dcc3ea27079aa6dc3f9deccd7275e0f8"
    assert hg38.reader_requires_local_path is True
    assert hg38.runtime_delivery_modes == (
        "local_path",
        "object_storage_local_cache",
        "mounted_volume",
    )
    assert hg38.download_approved is False

    dbsnp = registry.get("ncbi_dbsnp_gcf_000001405_40")
    assert dbsnp.day1_status == "active_day1"
    assert dbsnp.download_approved is False
    assert dbsnp.temporary_staging == "stage_on_C_drive"


def test_default_registry_contains_reviewed_seed_rows() -> None:
    registry = DEFAULT_DATA_SOURCE_REGISTRY
    source_ids = {record.source_id for record in registry.all()}

    assert len(source_ids) == 23
    assert {
        "myvariant_gnomad_only",
        "intervar_pipeline_config",
        "ncbi_clinvar_vcf",
        "mondo_disease_ontology",
    } <= source_ids


def test_restricted_predictor_rows_are_present_and_unlicensed() -> None:
    for source_id in RESTRICTED_PREDICTOR_SOURCE_IDS:
        record = DEFAULT_DATA_SOURCE_REGISTRY.get(source_id)

        assert record.license_status is LicenseStatus.RESTRICTED_UNLICENSED
        assert record.allowed_fields == ()
        assert record.restricted_fields
        assert record.download_approved is False


def test_myvariant_runtime_row_is_gnomad_only() -> None:
    record = DEFAULT_DATA_SOURCE_REGISTRY.get("myvariant_gnomad_only")

    assert record.allowed_fields == ("gnomad_genome", "gnomad_exome")
    assert {"cadd", "spliceai", "revel", "primateai_3d"} <= set(record.restricted_fields)
    assert record.download_approved is False


def test_validation_rejects_missing_license_status() -> None:
    hg38 = DEFAULT_DATA_SOURCE_REGISTRY.get("ucsc_hg38_2bit")
    bad_record = replace(hg38, license_status=None)  # type: ignore[arg-type]

    with pytest.raises(RegistryValidationError, match="license_status is required"):
        DataSourceRegistry([bad_record])


def test_validation_rejects_missing_storage_target() -> None:
    hg38 = DEFAULT_DATA_SOURCE_REGISTRY.get("ucsc_hg38_2bit")
    bad_record = replace(hg38, storage_target="")

    with pytest.raises(RegistryValidationError, match="storage_target is required"):
        DataSourceRegistry([bad_record])


def test_validation_rejects_missing_allowed_or_restricted_field_policy() -> None:
    hg38 = DEFAULT_DATA_SOURCE_REGISTRY.get("ucsc_hg38_2bit")
    bad_record = replace(hg38, restricted_fields=None)  # type: ignore[arg-type]

    with pytest.raises(RegistryValidationError, match="restricted_fields is required"):
        DataSourceRegistry([bad_record])


def test_validation_rejects_download_approval_without_review_metadata() -> None:
    dbsnp = DEFAULT_DATA_SOURCE_REGISTRY.get("ncbi_dbsnp_gcf_000001405_40")
    bad_record = replace(
        dbsnp,
        download_approved=True,
        source_url=None,
        checksum_required=False,
    )

    with pytest.raises(RegistryValidationError, match="download_approved requires"):
        DataSourceRegistry([DEFAULT_DATA_SOURCE_REGISTRY.get("ucsc_hg38_2bit"), bad_record])


def test_validation_enforces_hg38_first_asset_priority() -> None:
    records = [
        (
            replace(record, priority="p2_day1_reference")
            if record.source_id == "ucsc_hg38_2bit"
            else record
        )
        for record in DEFAULT_SOURCE_RECORDS
    ]

    with pytest.raises(RegistryValidationError, match="ucsc_hg38_2bit.*p0_first_asset_proof"):
        DataSourceRegistry(records)


def test_validation_enforces_hg38_inventory_metadata() -> None:
    records = [
        (
            replace(
                record,
                source_url=None,
                current_local_path=None,
                actual_size_bytes_local=None,
                current_local_md5=None,
            )
            if record.source_id == "ucsc_hg38_2bit"
            else record
        )
        for record in DEFAULT_SOURCE_RECORDS
    ]

    with pytest.raises(RegistryValidationError) as exc_info:
        DataSourceRegistry(records)

    message = str(exc_info.value)
    assert "ucsc_hg38_2bit: source_url is required" in message
    assert "ucsc_hg38_2bit: current_local_path is required" in message
    assert "ucsc_hg38_2bit: actual_size_bytes_local is required" in message
    assert "ucsc_hg38_2bit: current_local_md5 is required" in message


def test_runtime_registry_does_not_load_planning_seed() -> None:
    source = inspect.getsource(registry_module)

    assert "source-registry.seed.json" not in source
    assert "plans/data-source-registry" not in source
    assert "plans\\data-source-registry" not in source
