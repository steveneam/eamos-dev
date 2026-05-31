from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


class RegistryValidationError(ValueError):
    """Raised when runtime source registry metadata is incomplete or unsafe."""


class LicenseStatus(str, Enum):
    PENDING_TERMS_RECORD = "pending_terms_record"
    PUBLIC_ALLOWED_AFTER_TERMS_REVIEW = "public_allowed_after_terms_review"
    COMMERCIAL_ALLOWED = "commercial_allowed"
    COMMERCIAL_LICENSE_REVIEW_REQUIRED = "commercial_license_review_required"
    RESTRICTED_UNLICENSED = "restricted_unlicensed"
    LICENSED_ENABLED = "licensed_enabled"
    INTERNAL_FIXTURE_ONLY = "internal_fixture_only"


RESTRICTED_PREDICTOR_SOURCE_IDS = frozenset(
    {
        "illumina_spliceai_precomputed_hg38",
        "illumina_primateai3d_scores",
        "uw_cadd_scores_hg38",
        "zenodo_revel_scores",
    }
)


@dataclass(frozen=True)
class DataSourceRecord:
    source_id: str
    display_name: str
    priority: str
    tier: str
    day1_status: str
    files_or_api: tuple[str, ...]
    upstream_source: str
    source_url: str | None
    source_url_status: str
    expected_size: str
    storage_target: str
    temporary_staging: str
    adapter: str
    license_status: LicenseStatus
    allowed_product_tiers: tuple[str, ...]
    allowed_fields: tuple[str, ...]
    restricted_fields: tuple[str, ...]
    checksum_required: bool
    source_version_required: bool
    cache_policy: str
    download_approved: bool
    actual_size_bytes_local: int | None = None
    current_local_path: str | None = None
    current_local_md5: str | None = None
    source_version: str | None = None
    checksum_plan: str | None = None
    terms_url: str | None = None
    terms_status: str | None = None
    runtime_delivery_modes: tuple[str, ...] = ()
    reader_requires_local_path: bool = False
    storage_policy_reviewed: bool = False
    reader_compatibility_proofed: bool = False
    notes: str | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> DataSourceRecord:
        missing = sorted(_REQUIRED_RECORD_FIELDS - raw.keys())
        if missing:
            raise RegistryValidationError(
                f"data source row is missing required fields: {', '.join(missing)}"
            )

        try:
            license_status = LicenseStatus(str(raw["license_status"]))
        except ValueError as exc:
            source_id = raw.get("source_id", "<missing-source-id>")
            raise RegistryValidationError(
                f"{source_id}: unsupported license_status {raw.get('license_status')!r}"
            ) from exc

        return cls(
            source_id=str(raw["source_id"]),
            display_name=str(raw["display_name"]),
            priority=str(raw["priority"]),
            tier=str(raw["tier"]),
            day1_status=str(raw["day1_status"]),
            files_or_api=_as_string_tuple(raw["files_or_api"]),
            upstream_source=str(raw["upstream_source"]),
            source_url=_optional_string(raw["source_url"]),
            source_url_status=str(raw["source_url_status"]),
            expected_size=str(raw["expected_size"]),
            storage_target=str(raw["storage_target"]),
            temporary_staging=str(raw["temporary_staging"]),
            adapter=str(raw["adapter"]),
            license_status=license_status,
            allowed_product_tiers=_as_string_tuple(raw["allowed_product_tiers"]),
            allowed_fields=_as_string_tuple(raw["allowed_fields"]),
            restricted_fields=_as_string_tuple(raw["restricted_fields"]),
            checksum_required=_require_bool(raw["checksum_required"], "checksum_required"),
            source_version_required=_require_bool(
                raw["source_version_required"], "source_version_required"
            ),
            cache_policy=str(raw["cache_policy"]),
            download_approved=_require_bool(raw["download_approved"], "download_approved"),
            actual_size_bytes_local=raw.get("actual_size_bytes_local"),
            current_local_path=_optional_string(raw.get("current_local_path")),
            current_local_md5=_optional_string(raw.get("current_local_md5")),
            source_version=_optional_string(raw.get("source_version")),
            checksum_plan=_optional_string(raw.get("checksum_plan")),
            terms_url=_optional_string(raw.get("terms_url")),
            terms_status=_optional_string(raw.get("terms_status")),
            runtime_delivery_modes=_as_optional_string_tuple(raw.get("runtime_delivery_modes")),
            reader_requires_local_path=_require_bool(
                raw.get("reader_requires_local_path", False), "reader_requires_local_path"
            ),
            storage_policy_reviewed=_require_bool(
                raw.get("storage_policy_reviewed", False), "storage_policy_reviewed"
            ),
            reader_compatibility_proofed=_require_bool(
                raw.get("reader_compatibility_proofed", False),
                "reader_compatibility_proofed",
            ),
            notes=_optional_string(raw.get("notes")),
        )


class DataSourceRegistry:
    def __init__(self, records: Iterable[DataSourceRecord]) -> None:
        self._records = tuple(records)
        self._by_id = self._validate(self._records)

    def all(self) -> tuple[DataSourceRecord, ...]:
        return self._records

    def get(self, source_id: str) -> DataSourceRecord:
        try:
            return self._by_id[source_id]
        except KeyError as exc:
            raise KeyError(f"unknown data source: {source_id}") from exc

    def has(self, source_id: str) -> bool:
        return source_id in self._by_id

    @staticmethod
    def _validate(records: tuple[DataSourceRecord, ...]) -> dict[str, DataSourceRecord]:
        errors: list[str] = []
        by_id: dict[str, DataSourceRecord] = {}

        for record in records:
            source_label = record.source_id or "<missing-source-id>"
            if not record.source_id:
                errors.append("data source row is missing source_id")
                continue
            if record.source_id in by_id:
                errors.append(f"{record.source_id}: duplicate source_id")
                continue
            by_id[record.source_id] = record

            _validate_required_string(record.display_name, source_label, "display_name", errors)
            _validate_required_string(record.priority, source_label, "priority", errors)
            _validate_required_string(record.tier, source_label, "tier", errors)
            _validate_required_string(record.day1_status, source_label, "day1_status", errors)
            _validate_required_tuple(record.files_or_api, source_label, "files_or_api", errors)
            _validate_required_string(
                record.upstream_source, source_label, "upstream_source", errors
            )
            _validate_required_string(
                record.source_url_status, source_label, "source_url_status", errors
            )
            _validate_required_string(record.expected_size, source_label, "expected_size", errors)
            _validate_required_string(record.storage_target, source_label, "storage_target", errors)
            _validate_required_string(
                record.temporary_staging, source_label, "temporary_staging", errors
            )
            _validate_required_string(record.adapter, source_label, "adapter", errors)
            _validate_required_tuple(
                record.allowed_product_tiers, source_label, "allowed_product_tiers", errors
            )
            _validate_optional_tuple(record.allowed_fields, source_label, "allowed_fields", errors)
            _validate_optional_tuple(
                record.restricted_fields, source_label, "restricted_fields", errors
            )
            _validate_required_string(record.cache_policy, source_label, "cache_policy", errors)

            if not isinstance(record.license_status, LicenseStatus):
                errors.append(f"{source_label}: license_status is required")
            if not isinstance(record.checksum_required, bool):
                errors.append(f"{source_label}: checksum_required policy is required")
            if not isinstance(record.source_version_required, bool):
                errors.append(f"{source_label}: source_version_required policy is required")
            if not isinstance(record.download_approved, bool):
                errors.append(f"{source_label}: download_approved status is required")

            if record.download_approved:
                if not record.source_url:
                    errors.append(
                        f"{source_label}: download_approved requires a reviewed source_url"
                    )
                if record.checksum_required is not True:
                    errors.append(f"{source_label}: download_approved requires checksum validation")
                if record.source_version_required is not True:
                    errors.append(
                        f"{source_label}: download_approved requires a source-version policy"
                    )
                if record.source_version_required and not record.source_version:
                    errors.append(
                        f"{source_label}: download_approved requires a recorded source_version"
                    )
                if record.checksum_required and not (
                    record.current_local_md5 or record.checksum_plan
                ):
                    errors.append(
                        f"{source_label}: download_approved requires a checksum plan or checksum"
                    )
                if not record.storage_target:
                    errors.append(f"{source_label}: download_approved requires a storage_target")
                if record.license_status in {
                    LicenseStatus.RESTRICTED_UNLICENSED,
                    LicenseStatus.COMMERCIAL_LICENSE_REVIEW_REQUIRED,
                }:
                    errors.append(
                        f"{source_label}: download_approved is incompatible with "
                        f"{record.license_status.value}"
                    )

            if record.source_id in RESTRICTED_PREDICTOR_SOURCE_IDS:
                if record.license_status is not LicenseStatus.RESTRICTED_UNLICENSED:
                    errors.append(f"{source_label}: restricted predictor must be unlicensed")
                if record.allowed_fields:
                    errors.append(
                        f"{source_label}: restricted predictor must not allow public fields"
                    )
                if not record.restricted_fields:
                    errors.append(f"{source_label}: restricted predictor needs restricted_fields")
                if record.download_approved:
                    errors.append(f"{source_label}: restricted predictor download is not approved")

        hg38 = by_id.get("ucsc_hg38_2bit")
        if hg38 is None:
            errors.append("ucsc_hg38_2bit must be present")
        elif hg38.priority != "p0_first_asset_proof":
            errors.append("ucsc_hg38_2bit must be priority p0_first_asset_proof")
        else:
            if not hg38.source_url:
                errors.append("ucsc_hg38_2bit: source_url is required")
            if not hg38.current_local_path:
                errors.append("ucsc_hg38_2bit: current_local_path is required")
            if not isinstance(hg38.actual_size_bytes_local, int) or (
                hg38.actual_size_bytes_local <= 0
            ):
                errors.append("ucsc_hg38_2bit: actual_size_bytes_local is required")
            if not hg38.current_local_md5:
                errors.append("ucsc_hg38_2bit: current_local_md5 is required")
            required_modes = {"local_path", "object_storage_local_cache", "mounted_volume"}
            missing_modes = sorted(required_modes - set(hg38.runtime_delivery_modes))
            if missing_modes:
                errors.append(
                    "ucsc_hg38_2bit: runtime_delivery_modes is missing " + ", ".join(missing_modes)
                )
            if not hg38.reader_requires_local_path:
                errors.append("ucsc_hg38_2bit: reader_requires_local_path must be true")

        dbsnp = by_id.get("ncbi_dbsnp_gcf_000001405_40")
        if dbsnp is None:
            errors.append("ncbi_dbsnp_gcf_000001405_40 must be present")

        missing_restricted = sorted(RESTRICTED_PREDICTOR_SOURCE_IDS - by_id.keys())
        if missing_restricted:
            errors.append("restricted predictor rows are missing: " + ", ".join(missing_restricted))

        if errors:
            raise RegistryValidationError("; ".join(errors))
        return by_id


_REQUIRED_RECORD_FIELDS = frozenset(
    {
        "source_id",
        "display_name",
        "priority",
        "tier",
        "day1_status",
        "files_or_api",
        "upstream_source",
        "source_url",
        "source_url_status",
        "expected_size",
        "storage_target",
        "temporary_staging",
        "adapter",
        "license_status",
        "allowed_product_tiers",
        "allowed_fields",
        "restricted_fields",
        "checksum_required",
        "source_version_required",
        "cache_policy",
        "download_approved",
    }
)


def _as_string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise RegistryValidationError(f"expected a list of strings, got {type(value).__name__}")
    return tuple(str(item) for item in value)


def _as_optional_string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    return _as_string_tuple(value)


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise RegistryValidationError(f"{field_name} must be a boolean")
    return value


def _validate_required_string(
    value: object,
    source_id: str,
    field_name: str,
    errors: list[str],
) -> None:
    if not isinstance(value, str) or not value:
        errors.append(f"{source_id}: {field_name} is required")


def _validate_required_tuple(
    value: object,
    source_id: str,
    field_name: str,
    errors: list[str],
) -> None:
    if not isinstance(value, tuple) or not value:
        errors.append(f"{source_id}: {field_name} is required")


def _validate_optional_tuple(
    value: object,
    source_id: str,
    field_name: str,
    errors: list[str],
) -> None:
    if not isinstance(value, tuple):
        errors.append(f"{source_id}: {field_name} is required")


DEFAULT_SOURCE_RECORDS: tuple[DataSourceRecord, ...] = (
    DataSourceRecord(
        source_id="ucsc_hg38_2bit",
        display_name="hg38.2bit",
        priority="p0_first_asset_proof",
        tier="tier_1_object_storage_asset",
        day1_status="active_day1",
        files_or_api=("hg38.2bit",),
        upstream_source="UCSC Genome Browser",
        source_url="https://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/hg38.2bit",
        source_url_status="known_from_prior_isPcr_asset_install",
        expected_size="about 800 MB",
        storage_target="supabase_storage_after_review",
        temporary_staging="not_expected",
        adapter="twobitreader_or_py2bit_after_compatibility_proof",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("reference_sequence_windows",),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_asset_with_manifest_checksum",
        download_approved=True,
        actual_size_bytes_local=835393456,
        current_local_path="app/backend/data/bio_assets/genomes/hg38.2bit",
        current_local_md5="dcc3ea27079aa6dc3f9deccd7275e0f8",
        source_version="UCSC hg38.2bit initial GRCh38 release / GCA_000001405.15",
        terms_url="https://genome.ucsc.edu/license/",
        terms_status=(
            "Reviewed 2026-05-31: UCSC raw binary data are freely available "
            "for public and commercial use with UCSC citation/credit and "
            "source/version notices."
        ),
        runtime_delivery_modes=(
            "local_path",
            "object_storage_local_cache",
            "mounted_volume",
        ),
        reader_requires_local_path=True,
        storage_policy_reviewed=True,
        notes=(
            "Runtime readers require a local filesystem path. Hosted deployments "
            "should use object storage plus checksum-validated local cache, or a "
            "persistent mounted volume, before enabling full reference reads."
        ),
    ),
    DataSourceRecord(
        source_id="ncbi_dbsnp_gcf_000001405_40",
        display_name="dbSNP GRCh38 GCF_000001405.40",
        priority="p1_day1_identity_after_reference_proof",
        tier="tier_1_object_storage_asset",
        day1_status="active_day1",
        files_or_api=("GCF_000001405.40.gz", "GCF_000001405.40.gz.tbi"),
        upstream_source="NCBI dbSNP",
        source_url="https://ftp.ncbi.nih.gov/snp/latest_release/VCF/GCF_000001405.40.gz",
        source_url_status="verified_official_ftp_listing_2026_05_27",
        expected_size="28 GB plus 3.0 MB tabix index in NCBI latest_release listing",
        storage_target="supabase_storage_after_review",
        temporary_staging="stage_on_C_drive",
        adapter="pysam_tabix_after_compatibility_proof",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=(
            "rsid",
            "chrom",
            "position",
            "ref",
            "alt",
            "merge_identity_if_later_approved",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="local_identity_store_plus_source_cache",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="dbSNP latest_release GRCh38 GCF_000001405.40",
        checksum_plan=(
            "Use NCBI CHECKSUMS plus GCF_000001405.40.gz.md5 and "
            "GCF_000001405.40.gz.tbi.md5 before any approved download."
        ),
        terms_url="https://www.ncbi.nlm.nih.gov/home/about/policies/",
        terms_status=(
            "Reviewed 2026-05-31: NCBI places no restrictions on use or "
            "distribution of molecular data it provides, with standard "
            "third-party-rights caveats, attribution, and disclaimer display."
        ),
        notes=(
            "Day 1 large asset. Preserve upstream GCF_000001405.40 naming even "
            "if a local alias later adds a .vcf.gz suffix."
        ),
    ),
    DataSourceRecord(
        source_id="ncbi_clinvar_vcf",
        display_name="ClinVar VCF",
        priority="p2_day1_variant_classification",
        tier="tier_1_object_storage_asset",
        day1_status="active_day1",
        files_or_api=("clinvar.vcf.gz", "clinvar.vcf.gz.tbi"),
        upstream_source="NCBI ClinVar FTP",
        source_url="https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz",
        source_url_status="verified_official_ftp_listing_2026_05_27",
        expected_size="183 MB plus 595 KB tabix index in 2026-05-25 listing",
        storage_target="supabase_storage_after_review",
        temporary_staging="not_expected",
        adapter="pysam_tabix_after_compatibility_proof",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=(
            "variation_id",
            "classification",
            "review_status",
            "condition_summary",
            "hgvs_aliases",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="local_variant_classification_store_plus_source_cache",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="ClinVar GRCh38 VCF weekly release 2026-05-25 / clinvar_20260523",
        checksum_plan=(
            "Use upstream clinvar.vcf.gz.md5; record index size/checksum and "
            "VCF header fileDate during approved staging."
        ),
        terms_url="https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/",
        terms_status=(
            "Reviewed 2026-05-31: ClinVar is a freely accessible public NCBI "
            "archive; use requires source/submission attribution, release "
            "labeling, and medical-use disclaimers."
        ),
    ),
    DataSourceRecord(
        source_id="repeatmasker_rmsk_bb",
        display_name="RepeatMasker rmsk table / derived bigBed",
        priority="p2_day1_design_context",
        tier="tier_1_object_storage_asset",
        day1_status="active_day1",
        files_or_api=("rmsk.txt.gz", "derived rmsk.bb after approved conversion"),
        upstream_source="UCSC Genome Browser hg38 database",
        source_url="https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/rmsk.txt.gz",
        source_url_status="verified_official_database_listing_2026_05_27",
        expected_size="148 MB text table before derived bigBed conversion",
        storage_target="supabase_storage_after_review",
        temporary_staging="not_expected",
        adapter="bigbed_reader_or_conversion_path_after_proof",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("repeat_overlap", "repeat_family", "design_warning"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_indexed_asset",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="UCSC hg38 rmsk table dump 2022-10-18",
        checksum_plan=(
            "No verified UCSC per-table md5 sidecar found for rmsk.txt.gz; "
            "record downloaded source SHA256 and derived rmsk.bb SHA256 in manifest."
        ),
        terms_url="https://genome.ucsc.edu/FAQ/FAQdownloads.html",
        terms_status=(
            "Reviewed 2026-05-31: UCSC raw table data are freely available "
            "for public and commercial use with citation/credit; preserve "
            "RepeatMasker/RepBase provenance."
        ),
    ),
    DataSourceRecord(
        source_id="ucsc_phylop100way_hg38",
        display_name="hg38.phyloP100way.bw",
        priority="p2_day1_conservation",
        tier="tier_1_object_storage_asset",
        day1_status="active_day1",
        files_or_api=("hg38.phyloP100way.bw",),
        upstream_source="UCSC PhyloP directory",
        source_url="https://hgdownload.soe.ucsc.edu/goldenPath/hg38/phyloP100way/hg38.phyloP100way.bw",
        source_url_status="verified_official_directory_listing_2026_05_27",
        expected_size="9.2 GB in UCSC phyloP100way listing",
        storage_target="supabase_storage_after_review",
        temporary_staging="stage_on_C_drive",
        adapter="pyBigWig_after_compatibility_proof",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("conservation_score",),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_indexed_asset_plus_small_window_cache",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="UCSC hg38 100-way phyloP bigWig 2015-05-08",
        checksum_plan="Use UCSC md5sum.txt plus manifest SHA256/size before any approved download.",
        terms_url="https://genome.ucsc.edu/goldenPath/credits.html",
        terms_status=(
            "Reviewed 2026-05-31: UCSC phyloP100way files are available for "
            "public use and UCSC data terms allow commercial use with citation, "
            "credits, and derived-genome provenance."
        ),
        notes=(
            "Listed size is below the original 10 GB automatic C-drive rule, "
            "but user directed phyloP to C-drive staging with dbSNP/GCF on "
            "2026-05-27 because it is still a large 9.2 GB asset."
        ),
    ),
    DataSourceRecord(
        source_id="illumina_spliceai_precomputed_hg38",
        display_name="SpliceAI masked SNV hg38 precomputed scores",
        priority="p6_restricted_predictor",
        tier="tier_1_object_storage_asset",
        day1_status="pro_waitlist_only",
        files_or_api=(
            "spliceai_scores.masked.snv.hg38.vcf.gz",
            "spliceai_scores.masked.snv.hg38.vcf.gz.tbi",
        ),
        upstream_source="Illumina BaseSpace",
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 20 GB",
        storage_target="supabase_storage_after_license_approval",
        temporary_staging="stage_on_C_drive",
        adapter="pysam_tabix_after_license_and_compatibility_proof",
        license_status=LicenseStatus.RESTRICTED_UNLICENSED,
        allowed_product_tiers=("licensed_pro_future", "internal_fixture_only"),
        allowed_fields=(),
        restricted_fields=(
            "spliceai",
            "DS_AG",
            "DS_AL",
            "DS_DG",
            "DS_DL",
            "DP_AG",
            "DP_AL",
            "DP_DG",
            "DP_DL",
        ),
        checksum_required=True,
        source_version_required=True,
        cache_policy="locked_until_license_enabled",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="illumina_primateai3d_scores",
        display_name="PrimateAI-3D precomputed scores",
        priority="p6_restricted_predictor",
        tier="tier_1_object_storage_asset",
        day1_status="pro_waitlist_only",
        files_or_api=("primateai3d_scores.vcf.gz", "primateai3d_scores.vcf.gz.tbi"),
        upstream_source="Illumina GitHub/BaseSpace",
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 10 GB",
        storage_target="supabase_storage_after_license_approval",
        temporary_staging="check_actual_size_stage_on_C_if_greater_than_10gb",
        adapter="pysam_tabix_after_license_and_compatibility_proof",
        license_status=LicenseStatus.RESTRICTED_UNLICENSED,
        allowed_product_tiers=("licensed_pro_future", "internal_fixture_only"),
        allowed_fields=(),
        restricted_fields=("primateai_3d", "PrimateAI-3D"),
        checksum_required=True,
        source_version_required=True,
        cache_policy="locked_until_license_enabled",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="uw_cadd_scores_hg38",
        display_name="CADD scores",
        priority="p6_restricted_predictor",
        tier="tier_1_object_storage_asset",
        day1_status="pro_waitlist_only",
        files_or_api=("cadd_scores.tsv.gz", "cadd_scores.tsv.gz.tbi"),
        upstream_source="University of Washington",
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 30 GB",
        storage_target="supabase_storage_after_license_approval",
        temporary_staging="stage_on_C_drive",
        adapter="pysam_tabix_after_license_and_compatibility_proof",
        license_status=LicenseStatus.RESTRICTED_UNLICENSED,
        allowed_product_tiers=("licensed_pro_future", "internal_fixture_only"),
        allowed_fields=(),
        restricted_fields=("cadd", "CADD", "CADD PHRED"),
        checksum_required=True,
        source_version_required=True,
        cache_policy="locked_until_license_enabled",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="zenodo_revel_scores",
        display_name="REVEL scores",
        priority="p6_restricted_predictor",
        tier="tier_1_object_storage_asset",
        day1_status="pro_waitlist_only",
        files_or_api=("revel_scores.tsv.gz", "revel_scores.tsv.gz.tbi"),
        upstream_source="Zenodo public repo",
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 2 GB",
        storage_target="supabase_storage_after_license_approval",
        temporary_staging="not_expected",
        adapter="pysam_tabix_after_license_and_compatibility_proof",
        license_status=LicenseStatus.RESTRICTED_UNLICENSED,
        allowed_product_tiers=("licensed_pro_future", "internal_fixture_only"),
        allowed_fields=(),
        restricted_fields=("revel", "REVEL"),
        checksum_required=True,
        source_version_required=True,
        cache_policy="locked_until_license_enabled",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="ncbi_mane_grch38_v1_4_select_ensembl",
        display_name="MANE GRCh38 v1.4 Ensembl genomic GTF",
        priority="p3_transcript_model",
        tier="tier_2_repo_asset_candidate",
        day1_status="active_day1",
        files_or_api=("MANE.GRCh38.v1.4.ensembl_genomic.gtf.gz",),
        upstream_source="NCBI MANE FTP",
        source_url=(
            "https://ftp.ncbi.nlm.nih.gov/refseq/MANE/MANE_human/release_1.4/"
            "MANE.GRCh38.v1.4.ensembl_genomic.gtf.gz"
        ),
        source_url_status="verified_official_release_page_2026_05_27",
        expected_size="8.1 MB in MANE release 1.4 FTP listing",
        storage_target="render_repo_candidate_after_review",
        temporary_staging="not_expected",
        adapter="transcript_model_parser",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("mane_select_transcripts", "gene_transcript_mapping", "exon_cds_model"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_repo_asset_or_object_asset_manifest",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version=("MANE v1.4; RefSeq GCF_000001405.40-RS_2024_08; Ensembl release 114"),
        checksum_plan=(
            "Record upstream FTP size/date plus manifest SHA256; use an upstream "
            "checksum sidecar if present during approved staging."
        ),
        terms_url="https://www.ncbi.nlm.nih.gov/refseq/MANE/",
        terms_status=(
            "Reviewed 2026-05-31: MANE bulk FTP use appears allowed under "
            "NCBI molecular-data policy; retain NCBI/EMBL-EBI attribution, "
            "release identity, retrieval date, and disclaimer."
        ),
        notes=(
            "Official v1.4 GTF observed as ensembl_genomic; select rows must be "
            "extracted by MANE Select tags rather than assuming a separate "
            "select_ensembl GTF file."
        ),
    ),
    DataSourceRecord(
        source_id="gencode_v45_annotation",
        display_name="GENCODE v45 annotation GTF",
        priority="p3_transcript_model",
        tier="tier_2_repo_asset_candidate",
        day1_status="active_day1",
        files_or_api=("gencode.v45.annotation.gtf.gz",),
        upstream_source="GENCODE Project",
        source_url=(
            "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/"
            "release_45/gencode.v45.annotation.gtf.gz"
        ),
        source_url_status="verified_official_release_page_2026_05_27",
        expected_size="GENCODE release 45 comprehensive CHR GTF",
        storage_target="render_repo_candidate_after_review",
        temporary_staging="not_expected",
        adapter="transcript_model_parser",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("gene_transcript_mapping", "exon_cds_model"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_repo_asset_or_object_asset_manifest",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="GENCODE v45; GRCh38.p14; Ensembl release 111; released 2024-01",
        checksum_plan=(
            "Use GENCODE/EBI FTP checksum metadata if present plus manifest "
            "SHA256/size before approved staging."
        ),
        terms_url="https://www.ebi.ac.uk/about/terms-of-use/",
        terms_status=(
            "Reviewed 2026-05-31: GENCODE data are open access and EMBL-EBI "
            "adds no extra redistribution restrictions beyond original-owner "
            "terms; retain attribution and exact release metadata."
        ),
    ),
    DataSourceRecord(
        source_id="intervar_pipeline_config",
        display_name="InterVar pipeline configuration files",
        priority="p6_license_blocked_optional",
        tier="tier_2_repo_asset_candidate",
        day1_status="docx_intended_day1_blocked_for_commercial_production",
        files_or_api=("InterVar pipeline configuration files",),
        upstream_source="GitHub InterVar repo",
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 10 MB",
        storage_target="blocked_until_license_review",
        temporary_staging="not_expected",
        adapter="optional_licensed_intervar_integration",
        license_status=LicenseStatus.COMMERCIAL_LICENSE_REVIEW_REQUIRED,
        allowed_product_tiers=("internal_review_only",),
        allowed_fields=(),
        restricted_fields=(
            "intervar_acmg_classification",
            "annovar_dependencies",
            "omim_derived_inputs",
        ),
        checksum_required=True,
        source_version_required=True,
        cache_policy="blocked_until_license_enabled",
        download_approved=False,
        notes=(
            "DOCX-intended, but commercial production requires InterVar, "
            "ANNOVAR, and OMIM rights review."
        ),
    ),
    DataSourceRecord(
        source_id="python_primer3_py",
        display_name="primer3-py",
        priority="p_existing_runtime_dependency",
        tier="tier_2_5_python_engine",
        day1_status="already_present",
        files_or_api=("app/backend/requirements.txt",),
        upstream_source="primer3-py package",
        source_url=None,
        source_url_status="record_package_source_before_runtime_policy_change",
        expected_size="package_dependency",
        storage_target="backend_runtime_dependency",
        temporary_staging="not_applicable",
        adapter="existing_primer_provider",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("existing_runtime",),
        allowed_fields=("primer_thermodynamics",),
        restricted_fields=(),
        checksum_required=False,
        source_version_required=True,
        cache_policy="provider_version_invalidation",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="python_biopython",
        display_name="biopython",
        priority="p_existing_runtime_dependency",
        tier="tier_2_5_python_engine",
        day1_status="already_present",
        files_or_api=("app/backend/requirements.txt",),
        upstream_source="Biopython package",
        source_url=None,
        source_url_status="record_package_source_before_runtime_policy_change",
        expected_size="package_dependency",
        storage_target="backend_runtime_dependency",
        temporary_staging="not_applicable",
        adapter="existing_alignment_and_sequence_helpers",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("existing_runtime",),
        allowed_fields=("sequence_helpers", "alignment_support"),
        restricted_fields=(),
        checksum_required=False,
        source_version_required=True,
        cache_policy="provider_version_invalidation",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="python_pysam",
        display_name="pysam",
        priority="p_future_reader_dependency",
        tier="tier_2_5_python_engine",
        day1_status="selected_for_task_9_linux_reader_proof_windows_unavailable",
        files_or_api=("pysam==0.24.0",),
        upstream_source="PyPI pysam package",
        source_url="https://pypi.org/project/pysam/0.24.0/",
        source_url_status="verified_pypi_metadata_2026_05_27",
        expected_size=(
            "22.7 MB CPython 3.10 manylinux x86_64 wheel; no Windows wheels "
            "found in PyPI release metadata"
        ),
        storage_target="backend_runtime_dependency_after_review",
        temporary_staging="not_applicable",
        adapter="pysam_indexed_vcf_reader",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("future_after_review",),
        allowed_fields=("indexed_variant_file_access",),
        restricted_fields=(),
        checksum_required=False,
        source_version_required=True,
        cache_policy="not_applicable",
        download_approved=False,
        source_version="pysam 0.24.0",
        checksum_plan=(
            "Pin exact PyPI distribution version; use pip hash lock before "
            "production dependency freeze."
        ),
        terms_url="https://github.com/pysam-developers/pysam",
        terms_status="Package metadata recorded; dependency/license review still required",
        notes=(
            "PyPI provides Linux/mac wheels for 0.24.0 but no Windows wheels. "
            "The Windows host cannot install this natively; Render/Linux can "
            "install via the platform-marked requirements pin."
        ),
    ),
    DataSourceRecord(
        source_id="python_twobit_reader",
        display_name="twobitreader",
        priority="p_future_reader_dependency",
        tier="tier_2_5_python_engine",
        day1_status="selected_for_task_7_reference_proof",
        files_or_api=("twobitreader==3.1.8",),
        upstream_source="PyPI twobitreader package",
        source_url="https://pypi.org/project/twobitreader/3.1.8/",
        source_url_status="verified_pypi_metadata_2026_05_27",
        expected_size="14.1 kB py3-none-any wheel",
        storage_target="backend_runtime_dependency_after_review",
        temporary_staging="not_applicable",
        adapter="twobitreader_reference_genome_store",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("future_after_review",),
        allowed_fields=("reference_sequence_windows",),
        restricted_fields=(),
        checksum_required=False,
        source_version_required=True,
        cache_policy="not_applicable",
        download_approved=False,
        notes=(
            "Selected over py2bit for Task 7 because PyPI publishes a pure "
            "Python py3-none-any wheel for twobitreader 3.1.8, while py2bit is "
            "a C extension with POSIX/manylinux-oriented artifacts."
        ),
    ),
    DataSourceRecord(
        source_id="python_pybigwig",
        display_name="pyBigWig",
        priority="p_future_reader_dependency",
        tier="tier_2_5_python_engine",
        day1_status="selected_for_task_9_linux_reader_proof_windows_unavailable",
        files_or_api=("pyBigWig==0.3.25",),
        upstream_source="PyPI pyBigWig package",
        source_url="https://pypi.org/project/pyBigWig/0.3.25/",
        source_url_status="verified_pypi_metadata_2026_05_27",
        expected_size=(
            "183.5 kB CPython 3.10 manylinux x86_64 wheel; no Windows wheels "
            "found in PyPI release metadata"
        ),
        storage_target="backend_runtime_dependency_after_review",
        temporary_staging="not_applicable",
        adapter="pybigwig_conservation_reader",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("future_after_review",),
        allowed_fields=("conservation_score",),
        restricted_fields=(),
        checksum_required=False,
        source_version_required=True,
        cache_policy="not_applicable",
        download_approved=False,
        source_version="pyBigWig 0.3.25",
        checksum_plan=(
            "Pin exact PyPI distribution version; use pip hash lock before "
            "production dependency freeze."
        ),
        terms_url="https://github.com/deeptools/pyBigWig",
        terms_status="Package metadata recorded; dependency/license review still required",
        notes=(
            "PyPI provides Linux wheels for 0.3.25 but no Windows wheels. The "
            "Windows host cannot install this natively; Render/Linux can "
            "install via the platform-marked requirements pin."
        ),
    ),
    DataSourceRecord(
        source_id="python_duckdb_pyarrow",
        display_name="duckdb and optional pyarrow",
        priority="p_future_reader_dependency",
        tier="tier_2_5_python_engine",
        day1_status="candidate_after_store_design",
        files_or_api=("python_package",),
        upstream_source="DuckDB and PyArrow packages",
        source_url=None,
        source_url_status="required_before_install",
        expected_size="package_dependency",
        storage_target="backend_runtime_dependency_after_review",
        temporary_staging="not_applicable",
        adapter="optional_columnar_local_store",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("future_after_review",),
        allowed_fields=("local_columnar_queries",),
        restricted_fields=(),
        checksum_required=False,
        source_version_required=True,
        cache_policy="provider_version_invalidation",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="mondo_disease_ontology",
        display_name="Mondo Disease Ontology",
        priority="p4_small_source_table",
        tier="tier_3_supabase_postgres_table",
        day1_status="active_day1",
        files_or_api=("mondo.json", "derived mondo.tsv after parser proof"),
        upstream_source="Mondo Disease Ontology",
        source_url="https://purl.obolibrary.org/obo/mondo.json",
        source_url_status="verified_official_download_page_2026_05_27",
        expected_size="about 100 MB JSON edition",
        storage_target="supabase_postgres_after_review",
        temporary_staging="not_expected",
        adapter="disease_ontology_table",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("disease_ids", "disease_names", "cross_references"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="postgres_import_with_source_version",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="Mondo stable release; latest observed release 2026-05-05",
        checksum_plan=(
            "Record release version IRI and local SHA256/size for mondo.json; "
            "record derived TSV checksum if generated."
        ),
        terms_url="https://mondo.monarchinitiative.org/pages/download/",
        terms_status=(
            "Reviewed 2026-05-31: Mondo is CC BY 4.0; commercial use and "
            "redistribution are allowed with attribution, license link, "
            "change notices, and release/version display."
        ),
        notes=(
            "DOCX label says OMIM and Orphanet combined, but listed files are "
            "Mondo. Do not import OMIM-derived files without separate review."
        ),
    ),
    DataSourceRecord(
        source_id="human_phenotype_ontology",
        display_name="Human Phenotype Ontology annotations",
        priority="p4_small_source_table",
        tier="tier_3_supabase_postgres_table",
        day1_status="active_day1",
        files_or_api=(
            "hp.json",
            "phenotype.hpoa",
            "genes_to_phenotype.txt",
            "phenotype_to_genes.txt",
            "genes_to_disease.txt",
        ),
        upstream_source="Human Phenotype Ontology",
        source_url="https://obophenotype.github.io/human-phenotype-ontology/annotations/phenotype_hpoa/",
        source_url_status="verified_official_annotation_docs_2026_05_27",
        expected_size="small annotation files; exact sizes recorded at import approval",
        storage_target="supabase_postgres_after_review",
        temporary_staging="not_expected",
        adapter="phenotype_annotation_table",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("phenotype_ids", "phenotype_terms", "gene_or_disease_links"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="postgres_import_with_source_version",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="HPO release 2026-02-16 observed; record annotation file headers at import",
        checksum_plan=(
            "Use GitHub release SHA256 assets where available; otherwise record "
            "local SHA256/size for approved HPO ontology and annotation files "
            "before import."
        ),
        terms_url="https://human-phenotype-ontology.github.io/license.html",
        terms_status=(
            "Reviewed 2026-05-31: HPO files are freely available with required "
            "HPO acknowledgement/citation and file date/version display; do "
            "not alter HPO meanings in transformed tables."
        ),
        notes=(
            "The draft hp.gpad path was not verified at the expected OBO PURL; "
            "start from the official HPO annotation files documented by HPO."
        ),
    ),
    DataSourceRecord(
        source_id="clingen_gene_validity",
        display_name="ClinGen gene validity",
        priority="p4_small_source_table",
        tier="tier_3_supabase_postgres_table",
        day1_status="active_day1",
        files_or_api=("clingen_gene_validity.csv",),
        upstream_source="ClinGen",
        source_url="https://search.clinicalgenome.org/kb/gene-validity/download",
        source_url_status="verified_official_download_page_2026_05_27",
        expected_size="real-time generated CSV; exact size recorded at import approval",
        storage_target="supabase_postgres_after_review",
        temporary_staging="not_expected",
        adapter="gene_disease_validity_table",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("gene", "disease", "validity_classification", "source_date"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="postgres_import_with_source_version",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="ClinGen Gene-Disease Validity real-time CSV export",
        checksum_plan="Record export timestamp, source URL, local SHA256, and row count before import.",
        terms_url="https://clinicalgenome.org/docs/terms-of-use/",
        terms_status=(
            "Reviewed 2026-05-31: ClinGen curated content is available under "
            "CC0 with requested attribution/date accessed and medical-use "
            "disclaimer display."
        ),
    ),
    DataSourceRecord(
        source_id="gencc_download",
        display_name="GenCC download",
        priority="p4_small_source_table",
        tier="tier_3_supabase_postgres_table",
        day1_status="active_day1",
        files_or_api=("gencc-download.csv",),
        upstream_source="GenCC",
        source_url="https://search.thegencc.org/download/action/submissions-export-csv",
        source_url_status="verified_official_site_2026_05_27",
        expected_size="live submissions export; exact size recorded at import approval",
        storage_target="supabase_postgres_after_review",
        temporary_staging="not_expected",
        adapter="gene_disease_assertion_table",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("gene", "disease", "assertion", "submitter", "source_date"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="postgres_import_with_source_version",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="GenCC live submissions export; version by export date",
        checksum_plan="Record export timestamp, local SHA256, row count, and source statistics before import.",
        terms_url="https://search.thegencc.org/terms",
        terms_status=(
            "Reviewed 2026-05-31: GenCC download data are CC0 with requested "
            "GenCC/contributor attribution and access date; OMIM-derived data "
            "are excluded and must not be added without separate license."
        ),
    ),
    DataSourceRecord(
        source_id="uniprotkb_reviewed_swissprot",
        display_name="UniProtKB reviewed Swiss-Prot protein annotations",
        priority="p5_protein_annotation_terms_recorded",
        tier="tier_3_5_protein_annotation_asset",
        day1_status="candidate_terms_recorded_not_enabled",
        files_or_api=(
            "UniProtKB reviewed Swiss-Prot canonical entries",
            "optional human reviewed subset",
        ),
        upstream_source="UniProt Consortium",
        source_url="https://www.uniprot.org/help/downloads",
        source_url_status="official_download_docs_recorded_no_runtime_api_dependency",
        expected_size="download/subset size to be recorded during approved staging",
        storage_target="object_storage_or_mounted_volume_after_import_approval",
        temporary_staging="check_actual_size_stage_on_C_if_greater_than_10gb",
        adapter="local_uniprotkb_feature_store",
        license_status=LicenseStatus.COMMERCIAL_ALLOWED,
        allowed_product_tiers=("public_and_commercial_after_import_approval",),
        allowed_fields=(
            "protein_accession",
            "protein_name",
            "sequence_length",
            "curated_feature_ranges",
            "active_sites",
            "binding_sites",
            "ptm_sites",
            "cross_references",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="local_static_release_with_manifest_checksum",
        download_approved=False,
        actual_size_bytes_local=692563345,
        current_local_path=(
            "app/backend/data/bio_assets/protein_annotation/downloads/" "uniprot_sprot.dat.gz"
        ),
        current_local_md5="d6bd6e9435cd819b64cd888068530a45",
        source_version="UniProtKB/Swiss-Prot current_release downloaded 2026-05-29",
        checksum_plan=(
            "Local staged SHA256 "
            "bb3815e7b6445566ad9c8479f659033aa2115ed3cf2b06e61ae37c1dabc60438; "
            "record upstream release notes before production import."
        ),
        terms_url="https://www.uniprot.org/help/license",
        terms_status=(
            "UniProt databases are CC BY 4.0 for copyrightable database "
            "content. Commercial use is allowed with attribution, license "
            "link, change notices when applicable, no endorsement implication, "
            "and UniProt disclaimer/patent caveats recorded."
        ),
        notes=(
            "Use as the curated protein-feature source via release-pinned "
            "local import/mirror only. Live UniProt API calls are not an "
            "approved runtime dependency."
        ),
    ),
    DataSourceRecord(
        source_id="interpro_pfam_protein_matches",
        display_name="InterPro/Pfam protein-domain matches",
        priority="p5_protein_annotation_terms_recorded",
        tier="tier_3_5_protein_annotation_asset",
        day1_status="candidate_terms_recorded_not_enabled",
        files_or_api=("InterPro/Pfam protein match data", "Pfam protein-coordinate ranges"),
        upstream_source="EMBL-EBI InterPro / Pfam",
        source_url="https://interpro-documentation.readthedocs.io/en/latest/license.html",
        source_url_status="official_license_docs_recorded_no_runtime_api_dependency",
        expected_size="download/subset size to be recorded during approved staging",
        storage_target="object_storage_or_mounted_volume_after_import_approval",
        temporary_staging="check_actual_size_stage_on_C_if_greater_than_10gb",
        adapter="local_interpro_pfam_match_store",
        license_status=LicenseStatus.COMMERCIAL_ALLOWED,
        allowed_product_tiers=("public_and_commercial_after_import_approval",),
        allowed_fields=(
            "pfam_accession",
            "interpro_accession",
            "domain_name",
            "aa_start",
            "aa_end",
            "match_score",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="local_static_release_with_manifest_checksum",
        download_approved=False,
        actual_size_bytes_local=384357362,
        current_local_path=(
            "app/backend/data/bio_assets/protein_annotation/downloads/" "Pfam-A.hmm.gz"
        ),
        current_local_md5="dc814cc181ece09102c09c4e6c19f2fd",
        source_version="Pfam current_release downloaded 2026-05-29",
        checksum_plan=(
            "Local staged Pfam-A.hmm.gz SHA256 "
            "d3d30c8e6801bfedecf783408ecc98916f8f1dda8974c6e51036fcbdd765f591; "
            "Pfam-A.hmm.dat.gz sidecar size 718721 bytes, MD5 "
            "41a8fb4c9391e814795587fcdc8baa33, SHA256 "
            "4da981816a630fd77171cc5d369716bbe16e58dae8be8047ac1118e0bd64ebe4."
        ),
        terms_url="https://www.ebi.ac.uk/about/terms-of-use/",
        terms_status=(
            "InterPro, Pfam, PRINTS, and SFLD downloadable data on the "
            "InterPro website are CC0; no special commercial license is "
            "required, so commercial use is allowed. Citations and bundled "
            "copyright statements still need to be retained."
        ),
        notes=(
            "Preferred domain-architecture source for the richer protein "
            "view. Use local release data only; API access is not approved by "
            "this row."
        ),
    ),
    DataSourceRecord(
        source_id="interproscan_standalone",
        display_name="InterProScan standalone sequence annotator",
        priority="p5_local_sequence_annotation_terms_recorded",
        tier="tier_2_5_local_annotation_engine",
        day1_status="candidate_terms_recorded_not_enabled",
        files_or_api=("InterProScan standalone package", "InterProScan data bundle"),
        upstream_source="EMBL-EBI InterPro",
        source_url="https://interproscan-docs.readthedocs.io/en/v6/HowToInstall.html",
        source_url_status="official_install_docs_recorded_no_runtime_api_dependency",
        expected_size="large local tool/data bundle; exact size to be recorded before staging",
        storage_target="mounted_volume_or_worker_image_after_import_approval",
        temporary_staging="check_actual_size_stage_on_C_if_greater_than_10gb",
        adapter="offline_sequence_to_interpro_features_worker",
        license_status=LicenseStatus.COMMERCIAL_ALLOWED,
        allowed_product_tiers=("public_and_commercial_after_import_approval",),
        allowed_fields=(
            "local_sequence_domain_predictions",
            "families",
            "domains",
            "functional_sites",
            "go_terms_if_available",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="offline_job_cache_by_sequence_hash_and_tool_release",
        download_approved=False,
        actual_size_bytes_local=58031205,
        current_local_path=(
            "app/backend/data/bio_assets/protein_annotation/downloads/" "interproscan6-main.zip"
        ),
        current_local_md5="97d76552a7886ebe6ac944786fae4363",
        source_version="ebi-pf-team/interproscan6 main zip downloaded 2026-05-29",
        checksum_plan=(
            "Local staged SHA256 "
            "80ed03963f9f313c1e717b53fae54f063938e30bfaf415801599df18cab670e5; "
            "pin a tagged InterProScan release before production worker image build."
        ),
        terms_url="https://interproscan-docs.readthedocs.io/en/v6/index.html",
        terms_status=(
            "InterProScan software is Apache licensed. Core local processing "
            "is allowed, but included tools/signature collections can have "
            "different terms; SignalP, Phobius, and DeepTMHMM remain disabled "
            "unless separately licensed."
        ),
        notes=(
            "This is the no-API path for annotating novel user sequences. It "
            "should run as a bounded backend job with --no-matches-api or a "
            "local MLS, not a Render startup download."
        ),
    ),
    DataSourceRecord(
        source_id="interproscan_optional_licensed_apps",
        display_name="InterProScan optional licensed apps",
        priority="p5_optional_protein_annotation_licensed_apps",
        tier="tier_2_5_local_annotation_engine",
        day1_status="blocked_until_component_licenses",
        files_or_api=("SignalP", "Phobius", "DeepTMHMM"),
        upstream_source="SignalP, Phobius, and DeepTMHMM providers",
        source_url="https://interproscan-docs.readthedocs.io/en/v6/InstallingLicensedApps.html",
        source_url_status="official_docs_recorded_separate_licenses_required",
        expected_size="component-specific licensed downloads",
        storage_target="not_enabled_until_license_proof",
        temporary_staging="not_applicable_until_licensed",
        adapter="disabled_optional_interproscan_apps_policy",
        license_status=LicenseStatus.COMMERCIAL_LICENSE_REVIEW_REQUIRED,
        allowed_product_tiers=("blocked_until_licensed",),
        allowed_fields=(),
        restricted_fields=(
            "signal_peptide_predictions",
            "transmembrane_topology_predictions",
        ),
        checksum_required=True,
        source_version_required=True,
        cache_policy="disabled_until_component_license_and_version_record",
        download_approved=False,
        terms_url="https://interproscan-docs.readthedocs.io/en/v6/InstallingLicensedApps.html",
        terms_status=(
            "InterProScan docs state SignalP, Phobius, and DeepTMHMM analyses "
            "are deactivated by default due to licensing and require licenses "
            "and files from their respective providers."
        ),
        notes=(
            "Not required for the core Pfam/InterPro domain track. Keep these "
            "apps disabled until component licenses, checksums, and leak tests "
            "are recorded."
        ),
    ),
    DataSourceRecord(
        source_id="hmmer_pfam_a",
        display_name="HMMER hmmscan with Pfam-A profiles",
        priority="p5_local_sequence_annotation_terms_recorded",
        tier="tier_2_5_local_annotation_engine",
        day1_status="candidate_terms_recorded_not_enabled",
        files_or_api=("hmmscan", "Pfam-A.hmm", "hmmpress indexes"),
        upstream_source="HMMER / EMBL-EBI Pfam",
        source_url="http://hmmer.org/",
        source_url_status="official_source_docs_recorded_no_runtime_api_dependency",
        expected_size="Pfam-A profile database is large; exact size to be recorded before staging",
        storage_target="mounted_volume_or_worker_image_after_import_approval",
        temporary_staging="check_actual_size_stage_on_C_if_greater_than_10gb",
        adapter="offline_hmmscan_pfam_domain_worker",
        license_status=LicenseStatus.COMMERCIAL_ALLOWED,
        allowed_product_tiers=("public_and_commercial_after_import_approval",),
        allowed_fields=(
            "pfam_accession",
            "domain_name",
            "aa_start",
            "aa_end",
            "e_value",
            "bit_score",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="offline_job_cache_by_sequence_hash_and_pfam_release",
        download_approved=False,
        actual_size_bytes_local=19669667,
        current_local_path=(
            "app/backend/data/bio_assets/protein_annotation/downloads/" "hmmer.tar.gz"
        ),
        current_local_md5="b1ed21ceea33930222c84f8c4d9f4240",
        source_version="HMMER source tarball 3.4 downloaded 2026-05-29",
        checksum_plan=(
            "Local staged SHA256 "
            "ca70d94fd0cf271bd7063423aabb116d42de533117343a9b27a65c17ff06fbf3; "
            "build/install step remains explicit and is not performed by "
            "download staging."
        ),
        terms_url="https://raw.githubusercontent.com/EddyRivasLab/hmmer/master/LICENSE",
        terms_status=(
            "HMMER source is BSD 3-clause licensed. Pfam is CC0 through the "
            "InterPro/Pfam docs. Commercial local hmmscan use is allowed when "
            "notices and citations are retained."
        ),
        notes=(
            "Lean fallback if full InterProScan is too heavy. This predicts "
            "Pfam domains locally, but it is not a substitute for UniProtKB "
            "expert curation."
        ),
    ),
    DataSourceRecord(
        source_id="myvariant_gnomad_only",
        display_name="MyVariant gnomAD-only API adapter",
        priority="p2_day1_api_after_policy",
        tier="tier_4_live_api",
        day1_status="active_day1",
        files_or_api=("myvariant.info API", "gnomad_genome", "gnomad_exome"),
        upstream_source="MyVariant.info",
        source_url=None,
        source_url_status="required_before_adapter_enablement",
        expected_size="zero-download live public cloud API",
        storage_target="live_api_plus_source_cache",
        temporary_staging="not_applicable",
        adapter="httpx_provider",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("gnomad_genome", "gnomad_exome"),
        restricted_fields=(
            "cadd",
            "dbnsfp.revel",
            "dbnsfp.primateai",
            "spliceai",
            "revel",
            "primateai_3d",
        ),
        checksum_required=False,
        source_version_required=True,
        cache_policy="source_cache_by_normalized_variant_field_set_and_adapter_version",
        download_approved=False,
        notes=(
            "Use only for gnomAD frequency lookup. Aggregation does not remove "
            "upstream licensing obligations."
        ),
    ),
)

DEFAULT_DATA_SOURCE_REGISTRY = DataSourceRegistry(DEFAULT_SOURCE_RECORDS)
