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
    assert hg38.download_approved is True

    dbsnp = registry.get("ncbi_dbsnp_gcf_000001405_40")
    assert dbsnp.day1_status == "active_day1"
    assert dbsnp.download_approved is True
    assert dbsnp.temporary_staging == "stage_on_C_drive"
    assert dbsnp.reader_compatibility_proofed is True

    clinvar = registry.get("ncbi_clinvar_vcf")
    assert clinvar.reader_compatibility_proofed is True

    phylop = registry.get("ucsc_phylop100way_hg38")
    assert phylop.expected_size == "9.2 GB in UCSC phyloP100way listing"
    assert phylop.temporary_staging == "stage_on_C_drive"
    assert phylop.reader_compatibility_proofed is True


def test_default_registry_contains_reviewed_seed_rows() -> None:
    registry = DEFAULT_DATA_SOURCE_REGISTRY
    source_ids = {record.source_id for record in registry.all()}

    assert len(source_ids) == 34
    assert {
        "myvariant_gnomad_only",
        "google_deepmind_alphamissense_hg38",
        "esm1b_hg38_assembled_scores",
        "ci_spliceai_model",
        "gpn_msa_hg38_scores",
        "pangolin_splice_effect_scores",
        "intervar_pipeline_config",
        "ncbi_clinvar_vcf",
        "ncbi_refseq_grch38_p14",
        "mondo_disease_ontology",
        "uniprotkb_reviewed_swissprot",
        "interpro_pfam_protein_matches",
        "interproscan_standalone",
        "interproscan_optional_licensed_apps",
        "hmmer_pfam_a",
    } <= source_ids


def test_protein_annotation_rows_are_commercial_allowed_but_not_runtime_approved() -> None:
    registry = DEFAULT_DATA_SOURCE_REGISTRY
    source_ids = (
        "uniprotkb_reviewed_swissprot",
        "interpro_pfam_protein_matches",
        "interproscan_standalone",
        "hmmer_pfam_a",
    )

    for source_id in source_ids:
        record = registry.get(source_id)
        assert record.license_status is LicenseStatus.COMMERCIAL_ALLOWED
        assert record.download_approved is False
        assert record.terms_url
        assert "allowed" in (record.terms_status or "").lower()

    assert "CC BY 4.0" in (registry.get("uniprotkb_reviewed_swissprot").terms_status or "")
    assert "CC0" in (registry.get("interpro_pfam_protein_matches").terms_status or "")
    assert "Apache" in (registry.get("interproscan_standalone").terms_status or "")
    assert "BSD 3-clause" in (registry.get("hmmer_pfam_a").terms_status or "")
    assert registry.get("interproscan_standalone").adapter == (
        "offline_sequence_to_interpro_features_worker"
    )
    assert registry.get("hmmer_pfam_a").adapter == "offline_hmmscan_pfam_domain_worker"
    assert "API" in (registry.get("uniprotkb_reviewed_swissprot").notes or "")

    optional_apps = registry.get("interproscan_optional_licensed_apps")
    assert optional_apps.license_status is LicenseStatus.COMMERCIAL_LICENSE_REVIEW_REQUIRED
    assert optional_apps.allowed_fields == ()
    assert optional_apps.restricted_fields
    assert optional_apps.download_approved is False
    assert "SignalP" in (optional_apps.terms_status or "")


def test_modern_ai_predictor_rows_record_free_predictor_statuses() -> None:
    registry = DEFAULT_DATA_SOURCE_REGISTRY

    alphamissense = registry.get("google_deepmind_alphamissense_hg38")
    assert alphamissense.license_status is LicenseStatus.COMMERCIAL_ALLOWED
    assert alphamissense.download_approved is True
    assert alphamissense.allowed_product_tiers == ("public_day1_after_review",)
    assert "9fd167735f16a1b87da6eb3e4c25fcb5" in (alphamissense.checksum_plan or "")
    assert "CC BY 4.0" in (alphamissense.terms_status or "")
    assert alphamissense.reader_compatibility_proofed is True

    esm1b = registry.get("esm1b_hg38_assembled_scores")
    assert esm1b.license_status is LicenseStatus.COMMERCIAL_LICENSE_REVIEW_REQUIRED
    assert esm1b.download_approved is False
    assert esm1b.allowed_product_tiers == ("internal_fixture_only",)
    assert "regeneration from the MIT model" in (esm1b.terms_status or "")
    assert esm1b.reader_compatibility_proofed is True

    ci_spliceai = registry.get("ci_spliceai_model")
    assert ci_spliceai.license_status is LicenseStatus.COMMERCIAL_ALLOWED
    assert ci_spliceai.download_approved is False
    assert ci_spliceai.allowed_product_tiers == ("public_day1_after_review",)
    assert "CC BY 4.0" in (ci_spliceai.terms_status or "")
    assert ci_spliceai.reader_compatibility_proofed is True

    gpn_msa = registry.get("gpn_msa_hg38_scores")
    assert gpn_msa.license_status is LicenseStatus.COMMERCIAL_ALLOWED
    assert gpn_msa.download_approved is False
    assert gpn_msa.allowed_product_tiers == ("public_day1_after_review",)
    assert "MIT license" in (gpn_msa.terms_status or "")
    assert gpn_msa.reader_compatibility_proofed is False

    pangolin = registry.get("pangolin_splice_effect_scores")
    assert pangolin.license_status is LicenseStatus.COMMERCIAL_LICENSE_REVIEW_REQUIRED
    assert pangolin.download_approved is False
    assert pangolin.allowed_product_tiers == ("internal_fixture_only",)
    assert "GPL-3.0" in (pangolin.terms_status or "")
    assert pangolin.reader_compatibility_proofed is False


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


def test_task9_reader_dependency_rows_record_platform_limits() -> None:
    pysam = DEFAULT_DATA_SOURCE_REGISTRY.get("python_pysam")
    pybigwig = DEFAULT_DATA_SOURCE_REGISTRY.get("python_pybigwig")

    assert pysam.files_or_api == ("pysam==0.24.0",)
    assert pysam.source_url == "https://pypi.org/project/pysam/0.24.0/"
    assert "no Windows wheels" in pysam.expected_size
    assert pysam.download_approved is False

    assert pybigwig.files_or_api == ("pyBigWig==0.3.25",)
    assert pybigwig.source_url == "https://pypi.org/project/pyBigWig/0.3.25/"
    assert "no Windows wheels" in pybigwig.expected_size
    assert pybigwig.download_approved is False


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
