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
