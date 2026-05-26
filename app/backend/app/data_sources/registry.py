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
    runtime_delivery_modes: tuple[str, ...] = ()
    reader_requires_local_path: bool = False
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
            runtime_delivery_modes=_as_optional_string_tuple(raw.get("runtime_delivery_modes")),
            reader_requires_local_path=_require_bool(
                raw.get("reader_requires_local_path", False), "reader_requires_local_path"
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
        elif dbsnp.download_approved:
            errors.append("ncbi_dbsnp_gcf_000001405_40 must not be download-approved")

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
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("reference_sequence_windows",),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_asset_with_manifest_checksum",
        download_approved=False,
        actual_size_bytes_local=835393456,
        current_local_path="app/backend/data/bio_assets/genomes/hg38.2bit",
        current_local_md5="dcc3ea27079aa6dc3f9deccd7275e0f8",
        runtime_delivery_modes=(
            "local_path",
            "object_storage_local_cache",
            "mounted_volume",
        ),
        reader_requires_local_path=True,
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
        files_or_api=("GCF_000001405.40.vcf.gz", "GCF_000001405.40.vcf.gz.tbi"),
        upstream_source="NCBI dbSNP",
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 15 GB",
        storage_target="supabase_storage_after_review",
        temporary_staging="stage_on_C_drive",
        adapter="pysam_tabix_after_compatibility_proof",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
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
        download_approved=False,
        notes=(
            "Day 1 large asset. Preserve upstream GCF_000001405.40 naming even "
            "if a local alias uses .vcf.gz."
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
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 60 MB",
        storage_target="supabase_storage_after_review",
        temporary_staging="not_expected",
        adapter="pysam_tabix_after_compatibility_proof",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
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
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="repeatmasker_rmsk_bb",
        display_name="RepeatMasker rmsk.bb",
        priority="p2_day1_design_context",
        tier="tier_1_object_storage_asset",
        day1_status="active_day1",
        files_or_api=("rmsk.bb",),
        upstream_source="RepeatMasker text / UCSC Table Browser conversion",
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 100 MB",
        storage_target="supabase_storage_after_review",
        temporary_staging="not_expected",
        adapter="bigbed_reader_or_conversion_path_after_proof",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("repeat_overlap", "repeat_family", "design_warning"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_indexed_asset",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="ucsc_phylop100way_hg38",
        display_name="hg38.phyloP100way.bw",
        priority="p2_day1_conservation",
        tier="tier_1_object_storage_asset",
        day1_status="active_day1",
        files_or_api=("hg38.phyloP100way.bw",),
        upstream_source="UCSC PhyloP directory",
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 10 GB",
        storage_target="supabase_storage_after_review",
        temporary_staging="check_actual_size_stage_on_C_if_greater_than_10gb",
        adapter="pyBigWig_after_compatibility_proof",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("conservation_score",),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_indexed_asset_plus_small_window_cache",
        download_approved=False,
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
        display_name="MANE GRCh38 v1.4 Select Ensembl GTF",
        priority="p3_transcript_model",
        tier="tier_2_repo_asset_candidate",
        day1_status="active_day1",
        files_or_api=("MANE.GRCh38.v1.4.select_ensembl.gtf.gz",),
        upstream_source="NCBI MANE FTP",
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 25 MB",
        storage_target="render_repo_candidate_after_review",
        temporary_staging="not_expected",
        adapter="transcript_model_parser",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("mane_select_transcripts", "gene_transcript_mapping", "exon_cds_model"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_repo_asset_or_object_asset_manifest",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="gencode_v45_annotation",
        display_name="GENCODE v45 annotation GTF",
        priority="p3_transcript_model",
        tier="tier_2_repo_asset_candidate",
        day1_status="active_day1",
        files_or_api=("gencode.v45.annotation.gtf.gz",),
        upstream_source="GENCODE Project",
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 60 MB",
        storage_target="render_repo_candidate_after_review",
        temporary_staging="not_expected",
        adapter="transcript_model_parser",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("gene_transcript_mapping", "exon_cds_model"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_repo_asset_or_object_asset_manifest",
        download_approved=False,
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
        day1_status="candidate_after_compatibility_proof",
        files_or_api=("python_package",),
        upstream_source="pysam package",
        source_url=None,
        source_url_status="required_before_install",
        expected_size="package_dependency",
        storage_target="backend_runtime_dependency_after_review",
        temporary_staging="not_applicable",
        adapter="indexed_vcf_bcf_tsv_reader",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("future_after_review",),
        allowed_fields=("indexed_variant_file_access",),
        restricted_fields=(),
        checksum_required=False,
        source_version_required=True,
        cache_policy="not_applicable",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="python_twobit_reader",
        display_name="twobitreader or py2bit",
        priority="p_future_reader_dependency",
        tier="tier_2_5_python_engine",
        day1_status="candidate_after_compatibility_proof",
        files_or_api=("python_package",),
        upstream_source="selected 2bit reader package",
        source_url=None,
        source_url_status="required_before_install",
        expected_size="package_dependency",
        storage_target="backend_runtime_dependency_after_review",
        temporary_staging="not_applicable",
        adapter="reference_genome_store",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("future_after_review",),
        allowed_fields=("reference_sequence_windows",),
        restricted_fields=(),
        checksum_required=False,
        source_version_required=True,
        cache_policy="not_applicable",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="python_pybigwig",
        display_name="pyBigWig",
        priority="p_future_reader_dependency",
        tier="tier_2_5_python_engine",
        day1_status="candidate_after_compatibility_proof",
        files_or_api=("python_package",),
        upstream_source="pyBigWig package",
        source_url=None,
        source_url_status="required_before_install",
        expected_size="package_dependency",
        storage_target="backend_runtime_dependency_after_review",
        temporary_staging="not_applicable",
        adapter="conservation_bigwig_reader",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("future_after_review",),
        allowed_fields=("conservation_score",),
        restricted_fields=(),
        checksum_required=False,
        source_version_required=True,
        cache_policy="not_applicable",
        download_approved=False,
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
        files_or_api=("mondo.json", "mondo.tsv"),
        upstream_source="Mondo Disease Ontology",
        source_url=None,
        source_url_status="required_before_import",
        expected_size="about 40 MB",
        storage_target="supabase_postgres_after_review",
        temporary_staging="not_expected",
        adapter="disease_ontology_table",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("disease_ids", "disease_names", "cross_references"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="postgres_import_with_source_version",
        download_approved=False,
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
        files_or_api=("phenotype.hpoa", "hp.gpad"),
        upstream_source="Human Phenotype Ontology",
        source_url=None,
        source_url_status="required_before_import",
        expected_size="about 5 MB",
        storage_target="supabase_postgres_after_review",
        temporary_staging="not_expected",
        adapter="phenotype_annotation_table",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("phenotype_ids", "phenotype_terms", "gene_or_disease_links"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="postgres_import_with_source_version",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="clingen_gene_validity",
        display_name="ClinGen gene validity",
        priority="p4_small_source_table",
        tier="tier_3_supabase_postgres_table",
        day1_status="active_day1",
        files_or_api=("clingen_gene_validity.csv",),
        upstream_source="ClinGen",
        source_url=None,
        source_url_status="required_before_import",
        expected_size="about 2 MB",
        storage_target="supabase_postgres_after_review",
        temporary_staging="not_expected",
        adapter="gene_disease_validity_table",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("gene", "disease", "validity_classification", "source_date"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="postgres_import_with_source_version",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="gencc_download",
        display_name="GenCC download",
        priority="p4_small_source_table",
        tier="tier_3_supabase_postgres_table",
        day1_status="active_day1",
        files_or_api=("gencc-download.csv",),
        upstream_source="GenCC",
        source_url=None,
        source_url_status="required_before_import",
        expected_size="about 5 MB",
        storage_target="supabase_postgres_after_review",
        temporary_staging="not_expected",
        adapter="gene_disease_assertion_table",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("gene", "disease", "assertion", "submitter", "source_date"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="postgres_import_with_source_version",
        download_approved=False,
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
