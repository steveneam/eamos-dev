from __future__ import annotations

from app.data_sources.registry_models import DataSourceRecord, LicenseStatus

OMIM_SOURCE_RECORDS: tuple[DataSourceRecord, ...] = (
    DataSourceRecord(
        source_id="omim_mim2gene",
        display_name="OMIM mim2gene mapping file",
        priority="p_future_terms_review",
        tier="tier_3_gated_mapping_file",
        day1_status="blocked_pending_written_terms_decision",
        files_or_api=("mim2gene.txt",),
        upstream_source="Online Mendelian Inheritance in Man (OMIM)",
        source_url="https://omim.org/static/omim/data/mim2gene.txt",
        source_url_status="official_mapping_url_recorded_not_approved_for_acquisition",
        expected_size="small mapping file; acquisition not approved",
        storage_target="none_until_written_terms_decision",
        temporary_staging="not_allowed",
        adapter="future_mapping_only_parser",
        license_status=LicenseStatus.COMMERCIAL_LICENSE_REVIEW_REQUIRED,
        allowed_product_tiers=("blocked_until_written_terms",),
        allowed_fields=(),
        restricted_fields=(
            "mim_number",
            "entry_type",
            "gene_identifiers",
            "gene_disease_validity",
        ),
        checksum_required=True,
        source_version_required=True,
        cache_policy="disabled_until_written_display_cache_export_backup_terms",
        download_approved=False,
        terms_url="https://omim.org/help/agreement",
        terms_status=(
            "Pending a written decision covering acquisition, display, cache, export, backup, "
            "public API, and ML/RAG use. The file is a mapping resource and must never be "
            "treated as gene-disease validity evidence."
        ),
        notes="Reserved identity only; no parser, download, or runtime provider is enabled.",
    ),
    DataSourceRecord(
        source_id="omim_licensed_api",
        display_name="OMIM licensed API",
        priority="p_future_signed_license",
        tier="tier_4_gated_licensed_api",
        day1_status="blocked_until_signed_license",
        files_or_api=("OMIM API",),
        upstream_source="Online Mendelian Inheritance in Man (OMIM)",
        source_url="https://api.omim.org/api/html",
        source_url_status="official_api_documentation_recorded_not_enabled",
        expected_size="bounded API responses only after a signed license",
        storage_target="none_until_signed_license_and_field_policy",
        temporary_staging="not_allowed",
        adapter="future_licensed_omim_api",
        license_status=LicenseStatus.COMMERCIAL_LICENSE_REVIEW_REQUIRED,
        allowed_product_tiers=("blocked_until_licensed",),
        allowed_fields=(),
        restricted_fields=(
            "titles",
            "clinical_synopses",
            "inheritance",
            "gene_phenotype_associations",
            "allelic_variants",
            "api_payloads",
            "derived_facts",
        ),
        checksum_required=False,
        source_version_required=True,
        cache_policy="disabled_until_signed_license_and_field_policy",
        download_approved=False,
        terms_url="https://omim.org/help/agreement",
        terms_status=(
            "No signed Eamos license is recorded. Display, cache, export, backup, public API, "
            "and ML/RAG permissions remain denied."
        ),
        notes="Reserved identity only; no API client, credential, cache, or provider is enabled.",
    ),
)
