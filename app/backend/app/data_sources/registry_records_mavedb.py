from __future__ import annotations

from app.data_sources.registry_models import DataSourceRecord, LicenseStatus

MAVEDB_SOURCE_RECORDS: tuple[DataSourceRecord, ...] = (
    DataSourceRecord(
        source_id="mavedb_cc0_bulk",
        display_name="MaveDB CC0 bulk archive",
        priority="p4_functional_evidence_contract",
        tier="tier_3_local_archive_candidate",
        day1_status="contract_ready_materialization_not_approved",
        files_or_api=("official MaveDB CC0-only Zenodo archive",),
        upstream_source="MaveDB / Variant Effect",
        source_url="https://doi.org/10.5281/zenodo.18511521",
        source_url_status="immutable_release_doi_verified_2026_07_17",
        expected_size=("1,805,088,683 bytes; mavedb-dump.20260206153444.zip"),
        storage_target="private_object_storage_or_verified_local_asset_after_approval",
        temporary_staging="operator_approved_bounded_archive_staging_only",
        adapter="mavedb_cc0_archive_schema_v2",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=(
            "archive_provenance",
            "score_set_metadata",
            "target_metadata",
            "variant_scores.raw_score",
            "variant_scores.score_column",
            "variant_scores.score_unit",
            "variant_scores.identifiers",
            "deprecation_state",
        ),
        restricted_fields=(
            "non_cc0_records",
            "data_usage_policy_restricted_records",
            "calibration_objects",
            "va_spec_objects",
        ),
        checksum_required=True,
        source_version_required=True,
        cache_policy="immutable_archive_plus_logical_store_checksum",
        download_approved=False,
        source_version="MaveDB CC0 bulk archive v4; DOI 10.5281/zenodo.18511521",
        checksum_plan=(
            "Zenodo-published MD5 1b25ea356d95277b780de1e78e4e995d; verify the "
            "immutable DOI, filename, byte size, and digest before parsing, then verify a "
            "separate local logical-store SHA256 before readiness."
        ),
        terms_url="https://www.mavedb.org/docs/mavedb/finding-data/downloading.html",
        terms_status=(
            "Reviewed 2026-07-17: the official bulk archive is CC0-only. Quarantine any "
            "score set with a non-empty restrictive or ambiguous dataUsagePolicy."
        ),
        notes=(
            "Contract only. No corpus acquisition or materialization is approved in Phase 0. "
            "The bulk archive does not authorize calibration or VA-Spec objects."
        ),
    ),
    DataSourceRecord(
        source_id="mavedb_public_api_metadata",
        display_name="MaveDB public API metadata",
        priority="p_future_metadata_supplement",
        tier="tier_4_optional_live_api",
        day1_status="optional_later_not_enabled",
        files_or_api=("hosted MaveDB REST API metadata only",),
        upstream_source="MaveDB / Variant Effect",
        source_url="https://api.mavedb.org/",
        source_url_status="official_host_recorded_not_runtime_enabled",
        expected_size="request bounded metadata only",
        storage_target="none_until_separate_policy_review",
        temporary_staging="not_allowed",
        adapter="future_bounded_mavedb_metadata_client",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("future_after_review",),
        allowed_fields=("score_set_metadata", "deprecation_state"),
        restricted_fields=("raw_scores", "calibration_objects", "va_spec_objects"),
        checksum_required=False,
        source_version_required=True,
        cache_policy="disabled_until_api_terms_and_cache_policy_review",
        download_approved=False,
        source_version="unresolved_optional_api_version",
        terms_url="https://www.mavedb.org/docs/mavedb/programmatic-access/api-quickstart.html",
        terms_status="Pending separate hosted-API field and cache policy review.",
        notes="Do not import or deploy the AGPL MaveDB server package.",
    ),
)
