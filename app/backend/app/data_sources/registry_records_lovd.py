from __future__ import annotations

from app.data_sources.registry_models import DataSourceRecord, LicenseStatus

LOVD_SOURCE_RECORDS: tuple[DataSourceRecord, ...] = (
    DataSourceRecord(
        source_id="lovd_global_variome_shared_fixture",
        display_name="Global Variome shared LOVD synthetic basic-record fixture",
        priority="p4_fixture_only_exact_variant_pilot",
        tier="tier_3_internal_fixture_only",
        day1_status="fixture_only_live_access_disabled",
        files_or_api=("hand-authored synthetic JSON and Atom fixtures",),
        upstream_source="Global Variome shared LOVD",
        source_url="https://databases.lovd.nl/shared/docs/",
        source_url_status="official_installation_documentation_reviewed_2026_07_17",
        expected_size="two small hand-authored schema fixtures; no upstream acquisition",
        storage_target="repository_test_fixtures_only",
        temporary_staging="not_allowed",
        adapter="lovd_basic_fixture_adapter",
        license_status=LicenseStatus.INTERNAL_FIXTURE_ONLY,
        allowed_product_tiers=("internal_fixture_only",),
        allowed_fields=(
            "basic_record.presence",
            "basic_record.record_url",
            "basic_record.genome_build",
            "basic_record.transcript_accession",
            "basic_record.hgvs_c",
            "basic_record.source_edited_at",
            "basic_record.installation",
            "basic_record.match_level",
            "basic_record.record_license",
            "basic_record.provenance",
        ),
        restricted_fields=(
            "basic_record.person",
            "basic_record.patient",
            "basic_record.phenotype",
            "basic_record.classification",
            "basic_record.case_count",
            "basic_record.times_reported",
            "basic_record.owner",
            "basic_record.creator",
            "basic_record.submitter",
            "basic_record.curator",
            "basic_record.raw_payload",
        ),
        checksum_required=False,
        source_version_required=True,
        cache_policy="disabled_fixture_only_future_negative_ttl_minimum_14400_seconds",
        download_approved=False,
        source_version="LOVD 3 basic API synthetic schema fixture v1",
        terms_url="https://databases.lovd.nl/shared/docs/",
        terms_status=(
            "Reviewed 2026-07-17 for a link and synthetic-fixture pilot only. "
            "Live API reuse, scraping, cache, export, and record redisplay remain disabled; "
            "every future live record requires its own recognized record-level license."
        ),
        notes=(
            "Canonical installation identity only. The adapter accepts no arbitrary host, "
            "performs no network request, and cannot emit people, phenotype, classification, "
            "case-count, Times_reported, or raw-response fields."
        ),
    ),
)
