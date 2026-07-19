from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from contextlib import closing
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import md5, sha256
import json
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Any, Literal
from urllib.parse import quote

from app.core.config import Settings
from app.services.mavedb_archive import (
    DEFAULT_MAVEDB_ARCHIVE_LIMITS,
    MaveDbArchiveError,
    MaveDbArchiveInventory,
    MaveDbArchiveLimits,
    MaveDbArchiveNumericValue,
    MaveDbArchiveScoreRow,
    MaveDbArchiveScoreSet,
    inspect_mavedb_archive,
    iter_mavedb_archive_member_digests,
    iter_mavedb_archive_score_rows,
)

MAVEDB_LOCAL_SCHEMA_VERSION = "eamos.mavedb_local.v2"
MAVEDB_LOCAL_SOURCE_ID = "mavedb_cc0_bulk"
MAVEDB_LOCAL_CLI_VERSION = "mavedb-local-cli-v2"
MAVEDB_ARCHIVE_RELEASE_DOI_V4 = "10.5281/zenodo.18511521"
MAVEDB_ARCHIVE_SOURCE_URL_V4 = f"https://doi.org/{MAVEDB_ARCHIVE_RELEASE_DOI_V4}"
MAVEDB_ARCHIVE_FILENAME_V4 = "mavedb-dump.20260206153444.zip"
MAVEDB_ARCHIVE_SIZE_BYTES_V4 = 1_805_088_683
MAVEDB_ARCHIVE_DIGEST_ALGORITHM_V4 = "md5"
MAVEDB_ARCHIVE_DIGEST_VALUE_V4 = "1b25ea356d95277b780de1e78e4e995d"
MAVEDB_ARCHIVE_CITATION = "PMID:39838450"
MAVEDB_FIXTURE_RELEASE_PREFIX = "synthetic-fixture:"
MAVEDB_FIXTURE_SOURCE_URL = "fixture://local"
MAVEDB_SCORE_SET_ORIGIN = "https://www.mavedb.org/score-sets/"

CC0_LICENSES = frozenset({"cc0", "cc0-1.0", "creative commons zero v1.0 universal"})
SUPPORTED_ARCHIVE_DIGESTS = frozenset({"md5", "sha256"})
MaveDbMatchLevel = Literal[
    "exact_vrs",
    "exact_genomic_identity",
    "exact_target_accession_mave_hgvs",
]


@dataclass(frozen=True)
class MaveDbArchiveRecord:
    source_id: str
    release_doi: str
    source_url: str
    archive_filename: str
    archive_size_bytes: int
    upstream_digest_algorithm: str
    upstream_digest_value: str
    upstream_digest_verified: bool
    archive_sha256: str
    verified_at: str


@dataclass(frozen=True)
class MaveDbScoreSetRecord:
    score_set_urn: str
    target_id: str
    license_snapshot: str
    data_usage_policy: str | None
    data_usage_policy_decision: str
    deprecated: bool
    superseded_by: str | None
    source_url: str
    experiment_urn: str | None = None
    experiment_set_urn: str | None = None
    title: str | None = None
    short_description: str | None = None
    score_set_method_text: str | None = None
    experiment_method_text: str | None = None
    experiment_short_description: str | None = None
    doi_identifiers: tuple[str, ...] = ()
    publication_identifiers: tuple[str, ...] = ()


@dataclass(frozen=True)
class MaveDbTargetRecord:
    target_id: str
    target_accession: str | None
    target_sequence_checksum: str
    gene: str | None = None
    target_kind: str = "accession"
    target_assembly: str | None = None
    label: str | None = None

    @property
    def exact_identity(self) -> str:
        return "|".join(
            (
                self.target_kind,
                self.target_accession or "",
                self.target_assembly or "",
                self.target_sequence_checksum,
            )
        )


@dataclass(frozen=True)
class MaveDbNumericValueRecord:
    column: str
    source_value: str
    parsed_value: Decimal
    description: str | None = None
    details: str | None = None


@dataclass(frozen=True)
class MaveDbVariantScoreRecord:
    variant_urn: str
    score_set_urn: str
    target_id: str
    mave_hgvs: str
    raw_score: Decimal
    score_column: str
    score_unit: str
    vrs_id: str | None = None
    genomic_identity: str | None = None
    deprecated: bool = False
    superseded_by: str | None = None
    raw_score_source: str | None = None
    mave_hgvs_nt: str | None = None
    mave_hgvs_splice: str | None = None
    mave_hgvs_pro: str | None = None
    score_column_description: str | None = None
    score_column_details: str | None = None
    uncertainty_values: tuple[MaveDbNumericValueRecord, ...] = ()
    mapping_assembly: str | None = None


@dataclass(frozen=True)
class MaveDbImportRecord:
    score_set: MaveDbScoreSetRecord
    target: MaveDbTargetRecord
    variant_score: MaveDbVariantScoreRecord


@dataclass(frozen=True)
class MaveDbMatchRecord:
    archive_release_doi: str
    archive_digest_algorithm: str
    archive_digest_value: str
    archive_digest_verified: bool
    archive_sha256: str
    archive_member_digests_verified: bool
    metadata_schema_version: str
    local_logical_checksum_verified: bool
    match_level: MaveDbMatchLevel
    requested_identity: str
    matched_identity: str
    score_set: MaveDbScoreSetRecord
    target: MaveDbTargetRecord
    variant_score: MaveDbVariantScoreRecord

    @property
    def score_set_id(self) -> str:
        return self.score_set.score_set_urn

    @property
    def variant(self) -> str:
        return self.variant_score.mave_hgvs

    @property
    def score(self) -> Decimal:
        return self.variant_score.raw_score

    @property
    def license(self) -> str:
        return self.score_set.license_snapshot

    @property
    def gene(self) -> str | None:
        return self.target.gene

    @property
    def accession(self) -> str:
        return self.target.target_accession or ""

    @property
    def source_url(self) -> str:
        return self.score_set.source_url


# Compatibility name for callers that consumed v1 matches. It now denotes a
# provenance-complete exact match, never a loose source row.
MaveDbRecord = MaveDbMatchRecord


@dataclass(frozen=True)
class MaveDbCalibrationRecord:
    calibration_id: str
    source_id: str | None
    source_version: str | None
    status: Literal["reserved_unavailable"] = "reserved_unavailable"
    reason: str = (
        "The CC0 bulk archive does not establish a licensed calibration or "
        "VA-Spec evidence object."
    )


MAVEDB_CALIBRATION_RESERVED = MaveDbCalibrationRecord(
    calibration_id="mavedb_functional_calibration_reserved_v1",
    source_id=None,
    source_version=None,
)


@dataclass(frozen=True)
class MaveDbImportResult:
    accepted: tuple[MaveDbImportRecord, ...]
    rejected: tuple[MaveDbImportRecord, ...]
    warnings: tuple[str, ...]
    provenance: tuple[str, ...] = ("eamos_mavedb_cc0_gate_v2",)


@dataclass(frozen=True)
class MaveDbLocalInspection:
    source_id: str
    status: str
    ready: bool
    enabled: bool = False
    schema_version: str | None = None
    source_version: str | None = None
    archive_release_doi: str | None = None
    archive_digest_verified: bool = False
    archive_digest_algorithm: str | None = None
    archive_digest_value: str | None = None
    archive_sha256: str | None = None
    archive_filename: str | None = None
    archive_size_bytes: int = 0
    archive_license: str | None = None
    archive_citation: str | None = None
    metadata_schema_version: str | None = None
    archive_member_count: int = 0
    archive_member_digests_verified: bool = False
    archive_compressed_bytes: int = 0
    archive_expanded_bytes: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    actual_size_bytes: int | None = None
    checksum_verified: bool = False
    checksum_algorithm: str | None = None
    checksum_value: str | None = None
    message: str | None = None
    warnings: tuple[str, ...] = ()

    def to_sanitized_dict(self) -> dict[str, Any]:
        public_allowed = (
            self.status == "ready" and self.archive_digest_verified and self.checksum_verified
        )
        return {
            "source_id": self.source_id,
            "status": self.status,
            "ready": self.ready,
            "available": self.ready,
            "enabled": self.enabled,
            "runtime_wired": True,
            "schema_version": self.schema_version,
            "source_version": self.source_version,
            "archive_release_doi": self.archive_release_doi,
            "archive_digest_verified": self.archive_digest_verified,
            "archive_digest_algorithm": self.archive_digest_algorithm,
            "archive_digest_value": (
                self.archive_digest_value if self.archive_digest_verified else None
            ),
            "archive_sha256": self.archive_sha256 if self.archive_digest_verified else None,
            "archive_filename": self.archive_filename,
            "archive_size_bytes": self.archive_size_bytes,
            "archive_license": self.archive_license,
            "archive_citation": self.archive_citation,
            "metadata_schema_version": self.metadata_schema_version,
            "archive_member_count": self.archive_member_count,
            "archive_member_digests_verified": self.archive_member_digests_verified,
            "archive_compressed_bytes": self.archive_compressed_bytes,
            "archive_expanded_bytes": self.archive_expanded_bytes,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "actual_size_bytes": self.actual_size_bytes,
            "checksum_verified": self.checksum_verified,
            "checksum_algorithm": self.checksum_algorithm,
            "checksum_value": self.checksum_value if self.checksum_verified else None,
            "message": self.message,
            "notices": list(self.warnings),
            "startup_download_allowed": False,
            "request_time_materialization_allowed": False,
            "secret_values_emitted": False,
            "local_path_values_emitted": False,
            "raw_source_rows_emitted": False,
            "public_serialization_allowed": public_allowed,
            "launch_gate": None if public_allowed else "mavedb_v2_archive_and_checksum_proof",
        }


@dataclass(frozen=True)
class MaveDbLocalMaterializationResult:
    ready: bool
    status: str
    schema_version: str = MAVEDB_LOCAL_SCHEMA_VERSION
    source_version: str | None = None
    archive_release_doi: str | None = None
    archive_digest_verified: bool = False
    archive_sha256: str | None = None
    archive_size_bytes: int = 0
    archive_citation: str = MAVEDB_ARCHIVE_CITATION
    metadata_schema_version: str | None = None
    archive_member_count: int = 0
    archive_member_digests_verified: bool = False
    accepted_count: int = 0
    rejected_count: int = 0
    checksum_algorithm: str = "sha256"
    checksum_value: str | None = None
    warnings: tuple[str, ...] = ()

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "status": self.status,
            "schema_version": self.schema_version,
            "source_version": self.source_version,
            "archive_release_doi": self.archive_release_doi,
            "archive_digest_verified": self.archive_digest_verified,
            "archive_sha256": self.archive_sha256 if self.archive_digest_verified else None,
            "archive_size_bytes": self.archive_size_bytes,
            "archive_citation": self.archive_citation,
            "metadata_schema_version": self.metadata_schema_version,
            "archive_member_count": self.archive_member_count,
            "archive_member_digests_verified": self.archive_member_digests_verified,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "checksum_algorithm": self.checksum_algorithm,
            "checksum_value": self.checksum_value if self.ready else None,
            "warnings": list(self.warnings),
            "startup_download_allowed": False,
            "request_time_materialization_allowed": False,
            "secret_values_emitted": False,
            "local_path_values_emitted": False,
            "raw_source_rows_emitted": False,
        }


class MaveDbLocalSchemaError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class MaveDbLocalStore:
    """Read-only local MaveDB CC0 exact-match access."""

    def __init__(
        self,
        db_path: Path,
        *,
        manifest_path: Path | None = None,
        enabled: bool = False,
    ) -> None:
        self.db_path = db_path
        self.manifest_path = manifest_path
        self.enabled = enabled

    def inspect(self, *, verify_checksum: bool = True) -> MaveDbLocalInspection:
        if not self.db_path.is_file():
            return MaveDbLocalInspection(
                source_id=MAVEDB_LOCAL_SOURCE_ID,
                status="cc0_import_not_materialized",
                ready=False,
                enabled=self.enabled,
                message="MaveDB CC0 local SQLite asset is missing",
            )
        if self.manifest_path is not None and not self.manifest_path.is_file():
            return MaveDbLocalInspection(
                source_id=MAVEDB_LOCAL_SOURCE_ID,
                status="manifest_missing",
                ready=False,
                enabled=self.enabled,
                actual_size_bytes=_safe_size(self.db_path),
                message="MaveDB CC0 local manifest is missing",
            )

        try:
            with closing(_connect_readonly(self.db_path)) as conn:
                _require_schema(conn)
                manifest = _manifest_row(conn)
                common = _inspection_manifest_fields(manifest)
                if not common["archive_digest_verified"]:
                    return MaveDbLocalInspection(
                        source_id=MAVEDB_LOCAL_SOURCE_ID,
                        status="archive_digest_unverified",
                        ready=False,
                        enabled=self.enabled,
                        actual_size_bytes=_safe_size(self.db_path),
                        message="MaveDB upstream archive digest was not verified",
                        **common,
                    )
                if not common["archive_member_digests_verified"]:
                    return MaveDbLocalInspection(
                        source_id=MAVEDB_LOCAL_SOURCE_ID,
                        status="archive_member_digests_unverified",
                        ready=False,
                        enabled=self.enabled,
                        actual_size_bytes=_safe_size(self.db_path),
                        message="MaveDB archive member digests were not verified",
                        **common,
                    )
                if not verify_checksum:
                    return MaveDbLocalInspection(
                        source_id=MAVEDB_LOCAL_SOURCE_ID,
                        status="verification_required",
                        ready=False,
                        enabled=self.enabled,
                        actual_size_bytes=_safe_size(self.db_path),
                        message="MaveDB local logical checksum verification is required",
                        warnings=("local_logical_checksum_verification_required",),
                        **common,
                    )
                expected_checksum = str(manifest.get("checksum_value") or "")
                actual_checksum = _logical_checksum(conn)
                if not expected_checksum or expected_checksum != actual_checksum:
                    return MaveDbLocalInspection(
                        source_id=MAVEDB_LOCAL_SOURCE_ID,
                        status="checksum_mismatch",
                        ready=False,
                        enabled=self.enabled,
                        actual_size_bytes=_safe_size(self.db_path),
                        checksum_algorithm="sha256",
                        message="MaveDB local logical checksum mismatch",
                        **common,
                    )
                return MaveDbLocalInspection(
                    source_id=MAVEDB_LOCAL_SOURCE_ID,
                    status=(
                        "ready" if _manifest_is_published_archive(manifest) else "fixture_ready"
                    ),
                    ready=True,
                    enabled=self.enabled,
                    actual_size_bytes=_safe_size(self.db_path),
                    checksum_verified=True,
                    checksum_algorithm="sha256",
                    checksum_value=expected_checksum,
                    warnings=tuple(
                        _dedupe(
                            [
                                *_json_list(manifest.get("warnings_json")),
                                *(
                                    []
                                    if _manifest_is_published_archive(manifest)
                                    else ["synthetic_fixture_not_public"]
                                ),
                            ]
                        )
                    ),
                    **common,
                )
        except sqlite3.DatabaseError:
            return MaveDbLocalInspection(
                source_id=MAVEDB_LOCAL_SOURCE_ID,
                status="db_unreadable",
                ready=False,
                enabled=self.enabled,
                actual_size_bytes=_safe_size(self.db_path),
                message="MaveDB CC0 local SQLite asset is unreadable",
            )
        except MaveDbLocalSchemaError as exc:
            return MaveDbLocalInspection(
                source_id=MAVEDB_LOCAL_SOURCE_ID,
                status=exc.code,
                ready=False,
                enabled=self.enabled,
                actual_size_bytes=_safe_size(self.db_path),
                message=str(exc),
            )

    def search_records(
        self,
        variant: Any,
        *,
        limit: int,
        verify_checksum: bool = True,
    ) -> tuple[list[MaveDbMatchRecord], MaveDbLocalInspection]:
        inspection = self.inspect(verify_checksum=verify_checksum)
        if not inspection.ready:
            return [], inspection

        queries = _exact_query_identities(variant)
        if not queries:
            return [], inspection
        with closing(_connect_readonly(self.db_path)) as conn:
            for query in queries:
                rows = _search_exact_records(conn, query=query, limit=limit)
                if not rows:
                    continue
                bounded_limit = max(1, min(int(limit), 100))
                if len(rows) > bounded_limit:
                    return [], replace(
                        inspection,
                        warnings=tuple(
                            _dedupe([*inspection.warnings, "mavedb_exact_match_limit_exceeded"])
                        ),
                    )
                if len({_exact_row_context(row, query=query) for row in rows}) != 1:
                    return [], replace(
                        inspection,
                        warnings=tuple(
                            _dedupe([*inspection.warnings, "mavedb_ambiguous_exact_context"])
                        ),
                    )
                return [
                    _match_from_row(conn, row, query=query, inspection=inspection) for row in rows
                ], inspection
        return [], inspection


def verify_mavedb_archive_file(
    archive_path: Path,
    *,
    expected_digest_algorithm: str,
    expected_digest_value: str,
    release_doi: str = MAVEDB_ARCHIVE_RELEASE_DOI_V4,
    source_url: str = MAVEDB_ARCHIVE_SOURCE_URL_V4,
    allow_synthetic_fixture: bool = False,
) -> MaveDbArchiveRecord:
    algorithm = expected_digest_algorithm.strip().lower()
    expected = expected_digest_value.strip().lower()
    if algorithm not in SUPPORTED_ARCHIVE_DIGESTS or not expected:
        raise ValueError("unsupported or missing MaveDB archive digest")
    expected_length = 32 if algorithm == "md5" else 64
    if not re.fullmatch(rf"[0-9a-f]{{{expected_length}}}", expected):
        raise ValueError("invalid MaveDB archive digest")
    upstream_digest = md5(usedforsecurity=False) if algorithm == "md5" else sha256()
    archive_sha256 = sha256()
    with archive_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            upstream_digest.update(chunk)
            archive_sha256.update(chunk)
    actual = upstream_digest.hexdigest().lower()
    archive_size_bytes = archive_path.stat().st_size
    published_metadata = (
        release_doi == MAVEDB_ARCHIVE_RELEASE_DOI_V4
        and source_url == MAVEDB_ARCHIVE_SOURCE_URL_V4
        and archive_path.name == MAVEDB_ARCHIVE_FILENAME_V4
        and archive_size_bytes == MAVEDB_ARCHIVE_SIZE_BYTES_V4
        and algorithm == MAVEDB_ARCHIVE_DIGEST_ALGORITHM_V4
        and expected == MAVEDB_ARCHIVE_DIGEST_VALUE_V4
    )
    fixture_metadata = (
        allow_synthetic_fixture
        and release_doi.startswith(MAVEDB_FIXTURE_RELEASE_PREFIX)
        and source_url == MAVEDB_FIXTURE_SOURCE_URL
    )
    return MaveDbArchiveRecord(
        source_id=MAVEDB_LOCAL_SOURCE_ID,
        release_doi=release_doi,
        source_url=source_url,
        archive_filename=archive_path.name,
        archive_size_bytes=archive_size_bytes,
        upstream_digest_algorithm=algorithm,
        upstream_digest_value=expected,
        upstream_digest_verified=actual == expected and (published_metadata or fixture_metadata),
        archive_sha256=archive_sha256.hexdigest(),
        verified_at=_utc_now(),
    )


def filter_mavedb_cc0_records(records: list[MaveDbImportRecord]) -> MaveDbImportResult:
    accepted: list[MaveDbImportRecord] = []
    rejected: list[MaveDbImportRecord] = []
    warnings: list[str] = []
    for record in records:
        score_set = record.score_set
        if _license_key(score_set.license_snapshot) not in CC0_LICENSES:
            rejected.append(record)
            warnings.append("mavedb_non_cc0_rejected")
            continue
        if score_set.data_usage_policy_decision != "no_additional_restriction":
            rejected.append(record)
            warnings.append("mavedb_data_usage_policy_rejected")
            continue
        if not record.variant_score.raw_score.is_finite():
            rejected.append(record)
            warnings.append("mavedb_invalid_score_rejected")
            continue
        accepted.append(record)
    return MaveDbImportResult(
        accepted=tuple(accepted),
        rejected=tuple(rejected),
        warnings=tuple(_dedupe(warnings)),
    )


def inspect_mavedb_local_store(
    settings: Settings, *, verify_checksum: bool = True
) -> MaveDbLocalInspection:
    return MaveDbLocalStore(
        _resolve_path(settings, settings.mavedb_local_sqlite_path),
        manifest_path=_resolve_path(settings, settings.mavedb_local_manifest_path),
        enabled=settings.mavedb_local_enabled,
    ).inspect(verify_checksum=verify_checksum)


def materialize_mavedb_local_store(
    settings: Settings,
    *,
    archive_path: Path,
    archive_proof: MaveDbArchiveRecord | None = None,
    output_path: Path | None = None,
    manifest_path: Path | None = None,
    source_version: str | None = None,
    archive_limits: MaveDbArchiveLimits = DEFAULT_MAVEDB_ARCHIVE_LIMITS,
    force: bool = False,
) -> MaveDbLocalMaterializationResult:
    if not _archive_proof_ready(archive_proof) or not _archive_path_matches_proof(
        archive_path, archive_proof
    ):
        return MaveDbLocalMaterializationResult(
            ready=False,
            status="archive_proof_required",
            source_version=source_version,
            archive_release_doi=(archive_proof.release_doi if archive_proof else None),
            archive_digest_verified=False,
            warnings=("verified_upstream_archive_digest_required",),
        )
    assert archive_proof is not None

    try:
        inventory = inspect_mavedb_archive(archive_path, limits=archive_limits)
        member_digests = tuple(
            iter_mavedb_archive_member_digests(archive_path, limits=archive_limits)
        )
    except MaveDbArchiveError as exc:
        return MaveDbLocalMaterializationResult(
            ready=False,
            status=f"archive_rejected:{exc.code}",
            source_version=source_version,
            archive_release_doi=archive_proof.release_doi,
            archive_digest_verified=True,
            archive_sha256=archive_proof.archive_sha256,
            archive_size_bytes=archive_proof.archive_size_bytes,
            warnings=(f"mavedb_archive_{exc.code}",),
        )

    destination = _resolve_path(settings, output_path or settings.mavedb_local_sqlite_path)
    manifest_destination = _resolve_path(
        settings,
        manifest_path or settings.mavedb_local_manifest_path,
    )
    try:
        archive_identity = archive_path.resolve(strict=True)
        destination_identity = destination.resolve(strict=False)
        manifest_identity = manifest_destination.resolve(strict=False)
    except OSError:
        return MaveDbLocalMaterializationResult(
            ready=False,
            status="invalid_materialization_paths",
            archive_release_doi=archive_proof.release_doi,
            archive_digest_verified=True,
            archive_sha256=archive_proof.archive_sha256,
            archive_size_bytes=archive_proof.archive_size_bytes,
            warnings=("mavedb_local_invalid_materialization_paths",),
        )
    if len({archive_identity, destination_identity, manifest_identity}) != 3:
        return MaveDbLocalMaterializationResult(
            ready=False,
            status="materialization_path_collision",
            archive_release_doi=archive_proof.release_doi,
            archive_digest_verified=True,
            archive_sha256=archive_proof.archive_sha256,
            archive_size_bytes=archive_proof.archive_size_bytes,
            warnings=("mavedb_local_materialization_path_collision",),
        )
    if destination.exists() and not force:
        return MaveDbLocalMaterializationResult(
            ready=False,
            status="destination_exists",
            source_version=source_version,
            archive_release_doi=archive_proof.release_doi,
            archive_digest_verified=True,
            warnings=("use_force_to_replace_existing_mavedb_local_asset",),
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    manifest_temp_name: str | None = None
    warning_counts: Counter[str] = Counter()
    accepted_count = 0
    rejected_count = 0
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
        temp_path = Path(temp_name)
        with closing(sqlite3.connect(temp_path)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("pragma foreign_keys = on")
            _create_schema(conn)
            metadata_by_urn = inventory.score_set_map()
            for archive_row in iter_mavedb_archive_score_rows(
                archive_path,
                inventory,
                limits=archive_limits,
            ):
                metadata = metadata_by_urn[archive_row.score_set_urn]
                rejection = _archive_record_rejection(metadata, archive_row)
                if rejection is not None:
                    rejected_count += 1
                    warning_counts[rejection] += 1
                    continue
                record = _record_from_archive_row(metadata, archive_row)
                _insert_record(conn, record)
                accepted_count += 1
            for member in member_digests:
                conn.execute(
                    """
                    insert into mavedb_archive_member (
                      member_name, expanded_bytes, compressed_bytes, sha256
                    ) values (?, ?, ?, ?)
                    """,
                    (
                        member.member_name,
                        member.expanded_bytes,
                        member.compressed_bytes,
                        member.sha256,
                    ),
                )
            checksum = _logical_checksum(conn)
            warnings = tuple(f"{code}:{count}" for code, count in sorted(warning_counts.items()))
            _write_manifest(
                conn,
                archive=archive_proof,
                inventory=inventory,
                source_version=_materialization_source_version(archive_proof, source_version),
                accepted_count=accepted_count,
                rejected_count=rejected_count,
                checksum_value=checksum,
                warnings=warnings,
            )
            conn.commit()
        if not _archive_path_matches_proof(archive_path, archive_proof):
            raise MaveDbArchiveError("archive_changed_after_proof")
        inspection = MaveDbLocalStore(temp_path, manifest_path=None).inspect(verify_checksum=True)
        if not inspection.ready:
            raise ValueError("materialized MaveDB store failed verification")
        manifest_destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=manifest_destination.parent,
            prefix=f".{manifest_destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as manifest_temp:
            manifest_temp_name = manifest_temp.name
            json.dump(
                inspection.to_sanitized_dict(),
                manifest_temp,
                indent=2,
                sort_keys=True,
            )
            manifest_temp.write("\n")
        Path(manifest_temp_name).replace(manifest_destination)
        manifest_temp_name = None
        temp_path.replace(destination)
    except MaveDbArchiveError as exc:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
        if manifest_temp_name is not None:
            Path(manifest_temp_name).unlink(missing_ok=True)
        return MaveDbLocalMaterializationResult(
            ready=False,
            status=f"archive_rejected:{exc.code}",
            source_version=source_version,
            archive_release_doi=archive_proof.release_doi,
            archive_digest_verified=True,
            archive_sha256=archive_proof.archive_sha256,
            archive_size_bytes=archive_proof.archive_size_bytes,
            metadata_schema_version=inventory.metadata_schema_version,
            archive_member_count=inventory.member_count,
            archive_member_digests_verified=bool(member_digests),
            warnings=(f"mavedb_archive_{exc.code}", "mavedb_local_destination_not_modified"),
        )
    except (OSError, sqlite3.DatabaseError, ValueError) as exc:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
        if manifest_temp_name is not None:
            Path(manifest_temp_name).unlink(missing_ok=True)
        return MaveDbLocalMaterializationResult(
            ready=False,
            status=f"materialization_failed:{type(exc).__name__}",
            source_version=source_version,
            archive_release_doi=archive_proof.release_doi,
            archive_digest_verified=True,
            archive_sha256=archive_proof.archive_sha256,
            archive_size_bytes=archive_proof.archive_size_bytes,
            metadata_schema_version=inventory.metadata_schema_version,
            archive_member_count=inventory.member_count,
            archive_member_digests_verified=bool(member_digests),
            warnings=(
                f"mavedb_local_{type(exc).__name__.lower()}",
                "mavedb_local_destination_not_modified",
            ),
        )
    return MaveDbLocalMaterializationResult(
        ready=inspection.ready,
        status=inspection.status,
        source_version=inspection.source_version,
        archive_release_doi=inspection.archive_release_doi,
        archive_digest_verified=inspection.archive_digest_verified,
        archive_sha256=inspection.archive_sha256,
        archive_size_bytes=inspection.archive_size_bytes,
        archive_citation=inspection.archive_citation or MAVEDB_ARCHIVE_CITATION,
        metadata_schema_version=inspection.metadata_schema_version,
        archive_member_count=inspection.archive_member_count,
        archive_member_digests_verified=inspection.archive_member_digests_verified,
        accepted_count=inspection.accepted_count,
        rejected_count=inspection.rejected_count,
        checksum_value=inspection.checksum_value,
        warnings=inspection.warnings,
    )


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        create table if not exists mavedb_local_manifest (
          id integer primary key check (id = 1),
          schema_version text not null,
          source_version text not null,
          materialized_at text not null,
          cli_version text not null,
          archive_release_doi text not null,
          archive_source_url text not null,
          archive_filename text not null,
          archive_size_bytes integer not null,
          archive_digest_algorithm text not null,
          archive_digest_value text not null,
          archive_digest_verified integer not null check (archive_digest_verified in (0, 1)),
          archive_sha256 text not null,
          archive_license text not null,
          archive_citation text not null,
          archive_verified_at text not null,
          metadata_schema_version text not null,
          archive_member_count integer not null,
          archive_member_digests_verified integer not null
            check (archive_member_digests_verified in (0, 1)),
          archive_compressed_bytes integer not null,
          archive_expanded_bytes integer not null,
          accepted_count integer not null,
          rejected_count integer not null,
          checksum_algorithm text not null,
          checksum_value text not null,
          warnings_json text not null
        );
        create table if not exists mavedb_archive_member (
          member_name text primary key,
          expanded_bytes integer not null,
          compressed_bytes integer not null,
          sha256 text not null
        );
        create table if not exists mavedb_experiment_set (
          experiment_set_urn text primary key
        );
        create table if not exists mavedb_experiment (
          experiment_urn text primary key,
          experiment_set_urn text not null,
          foreign key (experiment_set_urn)
            references mavedb_experiment_set(experiment_set_urn)
        );
        create table if not exists mavedb_target (
          target_id text primary key,
          target_kind text not null check (target_kind in ('accession', 'sequence')),
          target_accession text,
          target_accession_norm text,
          target_assembly text,
          target_sequence_checksum text not null,
          gene text,
          label text
        );
        create table if not exists mavedb_score_set (
          score_set_urn text primary key,
          experiment_urn text not null,
          experiment_set_urn text not null,
          target_id text not null,
          license_snapshot text not null,
          data_usage_policy text,
          data_usage_policy_decision text not null,
          deprecated integer not null check (deprecated in (0, 1)),
          superseded_by text,
          source_url text not null,
          title text,
          short_description text,
          score_set_method_text text,
          experiment_method_text text,
          experiment_short_description text,
          doi_identifiers_json text not null,
          publication_identifiers_json text not null,
          foreign key (target_id) references mavedb_target(target_id),
          foreign key (experiment_urn) references mavedb_experiment(experiment_urn),
          foreign key (experiment_set_urn)
            references mavedb_experiment_set(experiment_set_urn)
        );
        create table if not exists mavedb_variant_score (
          variant_urn text primary key,
          score_set_urn text not null,
          target_id text not null,
          mave_hgvs text not null,
          mave_hgvs_norm text not null,
          mave_hgvs_nt text,
          mave_hgvs_splice text,
          mave_hgvs_pro text,
          raw_score_source text not null,
          raw_score_decimal text not null,
          score_column text not null,
          score_unit text not null,
          score_column_description text,
          score_column_details text,
          vrs_id text,
          vrs_id_norm text,
          genomic_identity text,
          genomic_identity_norm text,
          mapping_assembly text,
          deprecated integer not null check (deprecated in (0, 1)),
          superseded_by text,
          unique (score_set_urn, variant_urn),
          foreign key (score_set_urn) references mavedb_score_set(score_set_urn),
          foreign key (target_id) references mavedb_target(target_id)
        );
        create table if not exists mavedb_variant_numeric_value (
          score_set_urn text not null,
          variant_urn text not null,
          column_name text not null,
          source_value text not null,
          decimal_value text not null,
          description text,
          details text,
          primary key (score_set_urn, variant_urn, column_name),
          foreign key (score_set_urn, variant_urn)
            references mavedb_variant_score(score_set_urn, variant_urn)
        );
        create index if not exists idx_mavedb_target_accession
          on mavedb_target(target_accession_norm);
        create index if not exists idx_mavedb_score_vrs
          on mavedb_variant_score(vrs_id_norm);
        create index if not exists idx_mavedb_score_genomic
          on mavedb_variant_score(genomic_identity_norm);
        create index if not exists idx_mavedb_score_target_hgvs
          on mavedb_variant_score(target_id, mave_hgvs_norm);
        create index if not exists idx_mavedb_score_set_target_hgvs
          on mavedb_variant_score(score_set_urn, target_id, mave_hgvs_norm);
        """)


def _require_schema(conn: sqlite3.Connection) -> None:
    tables = {
        row["name"]
        for row in conn.execute("select name from sqlite_master where type='table'").fetchall()
    }
    required = {
        "mavedb_local_manifest",
        "mavedb_archive_member",
        "mavedb_experiment_set",
        "mavedb_experiment",
        "mavedb_target",
        "mavedb_score_set",
        "mavedb_variant_score",
        "mavedb_variant_numeric_value",
    }
    missing = sorted(required - tables)
    if missing:
        raise MaveDbLocalSchemaError(
            "schema_missing_tables",
            f"MaveDB local asset missing tables: {', '.join(missing)}",
        )
    manifest = _manifest_row(conn)
    if manifest.get("schema_version") != MAVEDB_LOCAL_SCHEMA_VERSION:
        raise MaveDbLocalSchemaError("schema_version_mismatch", "MaveDB schema mismatch")
    required_columns = {
        "mavedb_local_manifest": {
            "archive_sha256",
            "archive_size_bytes",
            "archive_citation",
            "metadata_schema_version",
            "archive_member_digests_verified",
        },
        "mavedb_score_set": {"experiment_urn", "doi_identifiers_json"},
        "mavedb_target": {"target_kind", "target_assembly"},
        "mavedb_variant_score": {
            "variant_urn",
            "raw_score_source",
            "raw_score_decimal",
            "mave_hgvs_nt",
            "mapping_assembly",
        },
    }
    for table, columns in required_columns.items():
        actual = {str(row["name"]) for row in conn.execute(f"pragma table_info({table})")}
        if not columns.issubset(actual):
            raise MaveDbLocalSchemaError(
                "schema_v2_signature_mismatch",
                "MaveDB schema-v2 signature mismatch",
            )


def _archive_path_matches_proof(
    archive_path: Path,
    archive_proof: MaveDbArchiveRecord | None,
) -> bool:
    if archive_proof is None or not archive_path.is_file():
        return False
    try:
        return bool(
            archive_path.name == archive_proof.archive_filename
            and archive_path.stat().st_size == archive_proof.archive_size_bytes
            and _sha256_file(archive_path) == archive_proof.archive_sha256
        )
    except OSError:
        return False


def _archive_record_rejection(
    metadata: MaveDbArchiveScoreSet,
    row: MaveDbArchiveScoreRow,
) -> str | None:
    if metadata.admission_error is not None:
        return f"mavedb_{metadata.admission_error}"
    if _license_key(metadata.license_snapshot) not in CC0_LICENSES:
        return "mavedb_non_cc0_rejected"
    if metadata.data_usage_policy_decision != "no_additional_restriction":
        return "mavedb_data_usage_policy_rejected"
    if row.rejection_code is not None:
        return f"mavedb_{row.rejection_code}"
    if metadata.target is None:
        return "mavedb_target_missing"
    if row.variant_urn is None or not row.variant_urn.startswith(f"{metadata.score_set_urn}#"):
        return "mavedb_variant_score_set_mismatch"
    if row.raw_score is None or row.raw_score_source is None or not row.raw_score.is_finite():
        return "mavedb_raw_score_invalid"
    if metadata.target.target_kind == "accession":
        accession = metadata.target.target_accession
        qualified_values = [value for value in (row.mave_hgvs_nt, row.mave_hgvs_pro) if value]
        if (
            not accession
            or not qualified_values
            or any(not value.startswith(f"{accession}:") for value in qualified_values)
        ):
            return "mavedb_target_variant_context_mismatch"
    if row.vrs_id is not None and not re.fullmatch(r"ga4gh:VA\.[A-Za-z0-9_-]+", row.vrs_id):
        return "mavedb_vrs_id_invalid"
    if row.genomic_identity is not None and not re.fullmatch(
        r"[A-Za-z0-9_.-]+:[gmncrp]\.\S+", row.genomic_identity
    ):
        return "mavedb_genomic_identity_invalid"
    return None


def _record_from_archive_row(
    metadata: MaveDbArchiveScoreSet,
    row: MaveDbArchiveScoreRow,
) -> MaveDbImportRecord:
    assert metadata.target is not None
    assert row.variant_urn is not None
    assert row.raw_score_source is not None
    assert row.raw_score is not None
    mave_hgvs = row.mave_hgvs_nt or row.mave_hgvs_pro
    assert mave_hgvs is not None
    score_column = next(column for column in metadata.score_columns if column.name == "score")
    score_set = MaveDbScoreSetRecord(
        score_set_urn=metadata.score_set_urn,
        target_id=metadata.target.target_id,
        license_snapshot=metadata.license_snapshot,
        data_usage_policy=metadata.data_usage_policy,
        data_usage_policy_decision=metadata.data_usage_policy_decision,
        deprecated=metadata.deprecated,
        superseded_by=metadata.superseded_by,
        source_url=_score_set_url(metadata.score_set_urn),
        experiment_urn=metadata.experiment_urn,
        experiment_set_urn=metadata.experiment_set_urn,
        title=metadata.title,
        short_description=metadata.short_description,
        score_set_method_text=metadata.score_set_method_text,
        experiment_method_text=metadata.experiment_method_text,
        experiment_short_description=metadata.experiment_short_description,
        doi_identifiers=metadata.doi_identifiers,
        publication_identifiers=metadata.publication_identifiers,
    )
    target = MaveDbTargetRecord(
        target_id=metadata.target.target_id,
        target_accession=metadata.target.target_accession,
        target_sequence_checksum=metadata.target.target_sequence_checksum,
        gene=metadata.target.gene,
        target_kind=metadata.target.target_kind,
        target_assembly=metadata.target.target_assembly,
        label=metadata.target.label,
    )
    variant_score = MaveDbVariantScoreRecord(
        variant_urn=row.variant_urn,
        score_set_urn=metadata.score_set_urn,
        target_id=metadata.target.target_id,
        mave_hgvs=mave_hgvs,
        raw_score=row.raw_score,
        score_column="score",
        score_unit="assay_specific_raw",
        vrs_id=row.vrs_id,
        genomic_identity=row.genomic_identity,
        deprecated=False,
        superseded_by=None,
        raw_score_source=row.raw_score_source,
        mave_hgvs_nt=row.mave_hgvs_nt,
        mave_hgvs_splice=row.mave_hgvs_splice,
        mave_hgvs_pro=row.mave_hgvs_pro,
        score_column_description=score_column.description,
        score_column_details=score_column.details,
        uncertainty_values=tuple(_numeric_value(value) for value in row.uncertainty_values),
        mapping_assembly=row.mapping_assembly,
    )
    return MaveDbImportRecord(score_set, target, variant_score)


def _numeric_value(value: MaveDbArchiveNumericValue) -> MaveDbNumericValueRecord:
    return MaveDbNumericValueRecord(
        column=value.column,
        source_value=value.source_value,
        parsed_value=value.parsed_value,
        description=value.description,
        details=value.details,
    )


def _insert_record(conn: sqlite3.Connection, record: MaveDbImportRecord) -> None:
    score_set = record.score_set
    experiment_urn = score_set.experiment_urn or score_set.score_set_urn.rsplit("-", 1)[0]
    experiment_set_urn = score_set.experiment_set_urn or experiment_urn.rsplit("-", 1)[0]
    conn.execute(
        "insert into mavedb_experiment_set (experiment_set_urn) values (?) "
        "on conflict(experiment_set_urn) do nothing",
        (experiment_set_urn,),
    )
    conn.execute(
        """
        insert into mavedb_experiment (experiment_urn, experiment_set_urn)
        values (?, ?) on conflict(experiment_urn) do nothing
        """,
        (experiment_urn, experiment_set_urn),
    )
    _require_existing_matches(
        conn,
        table="mavedb_experiment",
        where="experiment_urn = ?",
        key=(experiment_urn,),
        expected={"experiment_set_urn": experiment_set_urn},
    )

    target = record.target
    conn.execute(
        """
        insert into mavedb_target (
          target_id, target_kind, target_accession, target_accession_norm,
          target_assembly, target_sequence_checksum, gene, label
        ) values (?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(target_id) do nothing
        """,
        (
            target.target_id,
            target.target_kind,
            target.target_accession,
            _identity_key(target.target_accession) if target.target_accession else None,
            target.target_assembly,
            target.target_sequence_checksum,
            target.gene,
            target.label,
        ),
    )
    _require_existing_matches(
        conn,
        table="mavedb_target",
        where="target_id = ?",
        key=(target.target_id,),
        expected={
            "target_kind": target.target_kind,
            "target_accession": target.target_accession,
            "target_assembly": target.target_assembly,
            "target_sequence_checksum": target.target_sequence_checksum,
            "gene": target.gene,
        },
    )

    conn.execute(
        """
        insert into mavedb_score_set (
          score_set_urn, experiment_urn, experiment_set_urn, target_id,
          license_snapshot, data_usage_policy, data_usage_policy_decision,
          deprecated, superseded_by, source_url, title, short_description,
          score_set_method_text, experiment_method_text,
          experiment_short_description, doi_identifiers_json,
          publication_identifiers_json
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(score_set_urn) do nothing
        """,
        (
            score_set.score_set_urn,
            experiment_urn,
            experiment_set_urn,
            score_set.target_id,
            score_set.license_snapshot,
            score_set.data_usage_policy,
            score_set.data_usage_policy_decision,
            int(score_set.deprecated),
            score_set.superseded_by,
            score_set.source_url,
            score_set.title,
            score_set.short_description,
            score_set.score_set_method_text,
            score_set.experiment_method_text,
            score_set.experiment_short_description,
            json.dumps(score_set.doi_identifiers, separators=(",", ":")),
            json.dumps(score_set.publication_identifiers, separators=(",", ":")),
        ),
    )
    _require_existing_matches(
        conn,
        table="mavedb_score_set",
        where="score_set_urn = ?",
        key=(score_set.score_set_urn,),
        expected={
            "experiment_urn": experiment_urn,
            "experiment_set_urn": experiment_set_urn,
            "target_id": score_set.target_id,
            "license_snapshot": score_set.license_snapshot,
            "data_usage_policy": score_set.data_usage_policy,
            "data_usage_policy_decision": score_set.data_usage_policy_decision,
            "deprecated": int(score_set.deprecated),
            "superseded_by": score_set.superseded_by,
        },
    )

    score = record.variant_score
    raw_score_source = score.raw_score_source or str(score.raw_score)
    if (
        conn.execute(
            "select 1 from mavedb_variant_score where variant_urn = ?",
            (score.variant_urn,),
        ).fetchone()
        is not None
    ):
        raise ValueError("duplicate MaveDB variant identity")
    conn.execute(
        """
        insert into mavedb_variant_score (
          variant_urn, score_set_urn, target_id, mave_hgvs, mave_hgvs_norm,
          mave_hgvs_nt, mave_hgvs_splice, mave_hgvs_pro,
          raw_score_source, raw_score_decimal, score_column, score_unit,
          score_column_description, score_column_details, vrs_id, vrs_id_norm,
          genomic_identity, genomic_identity_norm, mapping_assembly,
          deprecated, superseded_by
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            score.variant_urn,
            score.score_set_urn,
            score.target_id,
            score.mave_hgvs,
            _identity_key(score.mave_hgvs),
            score.mave_hgvs_nt,
            score.mave_hgvs_splice,
            score.mave_hgvs_pro,
            raw_score_source,
            _decimal_string(score.raw_score),
            score.score_column,
            score.score_unit,
            score.score_column_description,
            score.score_column_details,
            score.vrs_id,
            _identity_key(score.vrs_id) if score.vrs_id else None,
            score.genomic_identity,
            _identity_key(score.genomic_identity) if score.genomic_identity else None,
            score.mapping_assembly,
            int(score.deprecated),
            score.superseded_by,
        ),
    )
    _require_existing_matches(
        conn,
        table="mavedb_variant_score",
        where="variant_urn = ?",
        key=(score.variant_urn,),
        expected={
            "score_set_urn": score.score_set_urn,
            "target_id": score.target_id,
            "mave_hgvs": score.mave_hgvs,
            "raw_score_source": raw_score_source,
            "raw_score_decimal": _decimal_string(score.raw_score),
            "score_unit": score.score_unit,
            "vrs_id": score.vrs_id,
            "genomic_identity": score.genomic_identity,
        },
    )
    for value in score.uncertainty_values:
        conn.execute(
            """
            insert into mavedb_variant_numeric_value (
              score_set_urn, variant_urn, column_name, source_value,
              decimal_value, description, details
            ) values (?, ?, ?, ?, ?, ?, ?)
            on conflict(score_set_urn, variant_urn, column_name) do nothing
            """,
            (
                score.score_set_urn,
                score.variant_urn,
                value.column,
                value.source_value,
                _decimal_string(value.parsed_value),
                value.description,
                value.details,
            ),
        )
        _require_existing_matches(
            conn,
            table="mavedb_variant_numeric_value",
            where="score_set_urn = ? and variant_urn = ? and column_name = ?",
            key=(score.score_set_urn, score.variant_urn, value.column),
            expected={
                "source_value": value.source_value,
                "decimal_value": _decimal_string(value.parsed_value),
                "description": value.description,
                "details": value.details,
            },
        )


def _require_existing_matches(
    conn: sqlite3.Connection,
    *,
    table: str,
    where: str,
    key: tuple[object, ...],
    expected: dict[str, object],
) -> None:
    row = conn.execute(f"select * from {table} where {where}", key).fetchone()
    if row is None or any(row[field] != value for field, value in expected.items()):
        raise ValueError(f"conflicting MaveDB identity in {table}")


@dataclass(frozen=True)
class _ExactQuery:
    match_level: MaveDbMatchLevel
    requested_identity: str
    value: str
    target_accession: str | None = None
    assembly: str | None = None


def _exact_query_identities(variant: Any) -> tuple[_ExactQuery, ...]:
    queries: list[_ExactQuery] = []
    explicit_target = _single_text_identity(getattr(variant, "target_accession", None))
    explicit_hgvs = _single_text_identity(getattr(variant, "mave_hgvs", None))
    transcript_hgvs = _single_text_identity(getattr(variant, "transcript_hgvs", None))
    target_accession = explicit_target
    qualified_mave_hgvs: str | None = None
    if transcript_hgvs and ":" in transcript_hgvs:
        transcript_target, _ = transcript_hgvs.split(":", 1)
        target_accession = target_accession or transcript_target
        qualified_mave_hgvs = transcript_hgvs
    elif explicit_target and explicit_hgvs:
        qualified_mave_hgvs = (
            explicit_hgvs
            if explicit_hgvs.startswith(f"{explicit_target}:")
            else f"{explicit_target}:{explicit_hgvs}"
        )
    target_norm = (
        _identity_key(target_accession)
        if target_accession and _versioned_target_accession(target_accession)
        else None
    )
    assembly = _single_text_identity(
        getattr(variant, "assembly", None)
        or getattr(variant, "genome_assembly", None)
        or getattr(variant, "genome_build", None)
    )

    vrs = _single_text_identity(
        getattr(variant, "vrs_id", None) or getattr(variant, "ga4gh_vrs_id", None)
    )
    if vrs:
        queries.append(
            _ExactQuery(
                "exact_vrs",
                vrs,
                _identity_key(vrs),
                target_accession=target_norm,
                assembly=_identity_key(assembly) if assembly else None,
            )
        )

    genomic_hgvs = _single_text_identity(getattr(variant, "genomic_hgvs", None))
    genomic_hg38 = _single_text_identity(getattr(variant, "genomic_hg38", None))
    genomic = genomic_hgvs or genomic_hg38
    if genomic:
        query_assembly = assembly or ("GRCh38" if genomic_hg38 else None)
        queries.append(
            _ExactQuery(
                "exact_genomic_identity",
                genomic,
                _identity_key(genomic),
                target_accession=target_norm,
                assembly=_identity_key(query_assembly) if query_assembly else None,
            )
        )

    if target_norm and qualified_mave_hgvs:
        queries.append(
            _ExactQuery(
                "exact_target_accession_mave_hgvs",
                qualified_mave_hgvs,
                _identity_key(qualified_mave_hgvs),
                target_accession=target_norm,
            )
        )
    unique: dict[tuple[str, str, str | None, str | None], _ExactQuery] = {}
    for query in queries:
        unique[(query.match_level, query.value, query.target_accession, query.assembly)] = query
    return tuple(unique.values())


def _search_exact_records(
    conn: sqlite3.Connection,
    *,
    query: _ExactQuery,
    limit: int,
) -> list[sqlite3.Row]:
    bounded_limit = max(1, min(int(limit), 100))
    select = """
        select
          v.*, s.license_snapshot, s.data_usage_policy,
          s.data_usage_policy_decision, s.deprecated as score_set_deprecated,
          s.superseded_by as score_set_superseded_by, s.source_url,
          s.experiment_urn, s.experiment_set_urn, s.title,
          s.short_description, s.score_set_method_text,
          s.experiment_method_text, s.experiment_short_description,
          s.doi_identifiers_json, s.publication_identifiers_json,
          t.target_kind, t.target_accession, t.target_assembly,
          t.target_sequence_checksum, t.gene, t.label
        from mavedb_variant_score v
        join mavedb_score_set s on s.score_set_urn = v.score_set_urn
        join mavedb_target t on t.target_id = v.target_id
    """
    clauses = [
        "s.deprecated = 0",
        "v.deprecated = 0",
        "s.superseded_by is null",
        "v.superseded_by is null",
        "s.data_usage_policy_decision = 'no_additional_restriction'",
    ]
    values: list[object] = []
    if query.match_level == "exact_vrs":
        clauses.append("v.vrs_id_norm = ?")
        values.append(query.value)
    elif query.match_level == "exact_genomic_identity":
        clauses.append("v.genomic_identity_norm = ?")
        values.append(query.value)
    else:
        clauses.extend(("t.target_accession_norm = ?", "v.mave_hgvs_norm = ?"))
        values.extend((query.target_accession, query.value))
    if query.target_accession and query.match_level != "exact_target_accession_mave_hgvs":
        clauses.append("t.target_accession_norm = ?")
        values.append(query.target_accession)
    if query.assembly:
        clauses.append("lower(coalesce(v.mapping_assembly, t.target_assembly, '')) = ?")
        values.append(query.assembly)
    values.append(bounded_limit + 1)
    return conn.execute(
        f"{select} where {' and '.join(clauses)} "
        "order by v.score_set_urn, v.variant_urn limit ?",
        tuple(values),
    ).fetchall()


def _exact_row_context(row: sqlite3.Row, *, query: _ExactQuery) -> tuple[str, ...]:
    fields = [
        "target_kind",
        "target_accession",
        "target_assembly",
        "target_sequence_checksum",
        "mave_hgvs_nt",
        "mave_hgvs_splice",
        "mave_hgvs_pro",
    ]
    if query.match_level == "exact_vrs":
        fields.append("vrs_id")
    elif query.match_level == "exact_genomic_identity":
        fields.extend(("genomic_identity", "mapping_assembly"))
    return tuple(str(row[field] or "").casefold() for field in fields)


def _match_from_row(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    *,
    query: _ExactQuery,
    inspection: MaveDbLocalInspection,
) -> MaveDbMatchRecord:
    score_set = MaveDbScoreSetRecord(
        score_set_urn=str(row["score_set_urn"]),
        target_id=str(row["target_id"]),
        license_snapshot=str(row["license_snapshot"]),
        data_usage_policy=(str(row["data_usage_policy"]) if row["data_usage_policy"] else None),
        data_usage_policy_decision=str(row["data_usage_policy_decision"]),
        deprecated=bool(row["score_set_deprecated"]),
        superseded_by=(
            str(row["score_set_superseded_by"]) if row["score_set_superseded_by"] else None
        ),
        source_url=str(row["source_url"]),
        experiment_urn=str(row["experiment_urn"]),
        experiment_set_urn=str(row["experiment_set_urn"]),
        title=str(row["title"]) if row["title"] else None,
        short_description=(str(row["short_description"]) if row["short_description"] else None),
        score_set_method_text=(
            str(row["score_set_method_text"]) if row["score_set_method_text"] else None
        ),
        experiment_method_text=(
            str(row["experiment_method_text"]) if row["experiment_method_text"] else None
        ),
        experiment_short_description=(
            str(row["experiment_short_description"])
            if row["experiment_short_description"]
            else None
        ),
        doi_identifiers=tuple(_json_list(row["doi_identifiers_json"])),
        publication_identifiers=tuple(_json_list(row["publication_identifiers_json"])),
    )
    target = MaveDbTargetRecord(
        target_id=str(row["target_id"]),
        target_accession=str(row["target_accession"]) if row["target_accession"] else None,
        target_sequence_checksum=str(row["target_sequence_checksum"]),
        gene=str(row["gene"]) if row["gene"] else None,
        target_kind=str(row["target_kind"]),
        target_assembly=str(row["target_assembly"]) if row["target_assembly"] else None,
        label=str(row["label"]) if row["label"] else None,
    )
    numeric_rows = conn.execute(
        """
        select * from mavedb_variant_numeric_value
        where score_set_urn = ? and variant_urn = ? order by column_name
        """,
        (str(row["score_set_urn"]), str(row["variant_urn"])),
    ).fetchall()
    variant_score = MaveDbVariantScoreRecord(
        variant_urn=str(row["variant_urn"]),
        score_set_urn=str(row["score_set_urn"]),
        target_id=str(row["target_id"]),
        mave_hgvs=str(row["mave_hgvs"]),
        raw_score=Decimal(str(row["raw_score_decimal"])),
        score_column=str(row["score_column"]),
        score_unit=str(row["score_unit"]),
        vrs_id=str(row["vrs_id"]) if row["vrs_id"] else None,
        genomic_identity=(str(row["genomic_identity"]) if row["genomic_identity"] else None),
        deprecated=bool(row["deprecated"]),
        superseded_by=str(row["superseded_by"]) if row["superseded_by"] else None,
        raw_score_source=str(row["raw_score_source"]),
        mave_hgvs_nt=str(row["mave_hgvs_nt"]) if row["mave_hgvs_nt"] else None,
        mave_hgvs_splice=(str(row["mave_hgvs_splice"]) if row["mave_hgvs_splice"] else None),
        mave_hgvs_pro=str(row["mave_hgvs_pro"]) if row["mave_hgvs_pro"] else None,
        score_column_description=(
            str(row["score_column_description"]) if row["score_column_description"] else None
        ),
        score_column_details=(
            str(row["score_column_details"]) if row["score_column_details"] else None
        ),
        uncertainty_values=tuple(
            MaveDbNumericValueRecord(
                column=str(value["column_name"]),
                source_value=str(value["source_value"]),
                parsed_value=Decimal(str(value["decimal_value"])),
                description=str(value["description"]) if value["description"] else None,
                details=str(value["details"]) if value["details"] else None,
            )
            for value in numeric_rows
        ),
        mapping_assembly=(str(row["mapping_assembly"]) if row["mapping_assembly"] else None),
    )
    matched_identity = {
        "exact_vrs": variant_score.vrs_id,
        "exact_genomic_identity": variant_score.genomic_identity,
        "exact_target_accession_mave_hgvs": variant_score.mave_hgvs,
    }[query.match_level]
    return MaveDbMatchRecord(
        archive_release_doi=inspection.archive_release_doi or "",
        archive_digest_algorithm=inspection.archive_digest_algorithm or "",
        archive_digest_value=inspection.archive_digest_value or "",
        archive_digest_verified=inspection.archive_digest_verified,
        archive_sha256=inspection.archive_sha256 or "",
        archive_member_digests_verified=inspection.archive_member_digests_verified,
        metadata_schema_version=inspection.metadata_schema_version or "",
        local_logical_checksum_verified=inspection.checksum_verified,
        match_level=query.match_level,
        requested_identity=query.requested_identity,
        matched_identity=matched_identity or "",
        score_set=score_set,
        target=target,
        variant_score=variant_score,
    )


def _write_manifest(
    conn: sqlite3.Connection,
    *,
    archive: MaveDbArchiveRecord,
    inventory: MaveDbArchiveInventory,
    source_version: str,
    accepted_count: int,
    rejected_count: int,
    checksum_value: str,
    warnings: tuple[str, ...],
) -> None:
    conn.execute(
        """
        insert into mavedb_local_manifest (
          id, schema_version, source_version, materialized_at, cli_version,
          archive_release_doi, archive_source_url, archive_filename, archive_size_bytes,
          archive_digest_algorithm, archive_digest_value, archive_digest_verified,
          archive_sha256, archive_license, archive_citation, archive_verified_at,
          metadata_schema_version, archive_member_count,
          archive_member_digests_verified, archive_compressed_bytes,
          archive_expanded_bytes, accepted_count, rejected_count,
          checksum_algorithm, checksum_value, warnings_json
        ) values (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            MAVEDB_LOCAL_SCHEMA_VERSION,
            source_version,
            _utc_now(),
            MAVEDB_LOCAL_CLI_VERSION,
            archive.release_doi,
            archive.source_url,
            archive.archive_filename,
            archive.archive_size_bytes,
            archive.upstream_digest_algorithm,
            archive.upstream_digest_value,
            int(archive.upstream_digest_verified),
            archive.archive_sha256,
            "CC0-1.0",
            MAVEDB_ARCHIVE_CITATION,
            archive.verified_at,
            inventory.metadata_schema_version,
            inventory.member_count,
            1,
            inventory.compressed_bytes,
            inventory.expanded_bytes,
            accepted_count,
            rejected_count,
            "sha256",
            checksum_value,
            json.dumps(list(warnings), sort_keys=True),
        ),
    )


def _manifest_row(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute("select * from mavedb_local_manifest where id = 1").fetchone()
    if row is None:
        raise MaveDbLocalSchemaError("manifest_missing", "MaveDB local manifest row missing")
    return dict(row)


def _inspection_manifest_fields(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": str(manifest.get("schema_version") or ""),
        "source_version": str(manifest.get("source_version") or ""),
        "archive_release_doi": str(manifest.get("archive_release_doi") or ""),
        "archive_digest_verified": bool(manifest.get("archive_digest_verified")),
        "archive_digest_algorithm": str(manifest.get("archive_digest_algorithm") or ""),
        "archive_digest_value": str(manifest.get("archive_digest_value") or ""),
        "archive_sha256": str(manifest.get("archive_sha256") or ""),
        "archive_filename": str(manifest.get("archive_filename") or ""),
        "archive_size_bytes": int(manifest.get("archive_size_bytes") or 0),
        "archive_license": str(manifest.get("archive_license") or ""),
        "archive_citation": str(manifest.get("archive_citation") or ""),
        "metadata_schema_version": str(manifest.get("metadata_schema_version") or ""),
        "archive_member_count": int(manifest.get("archive_member_count") or 0),
        "archive_member_digests_verified": bool(manifest.get("archive_member_digests_verified")),
        "archive_compressed_bytes": int(manifest.get("archive_compressed_bytes") or 0),
        "archive_expanded_bytes": int(manifest.get("archive_expanded_bytes") or 0),
        "accepted_count": int(manifest.get("accepted_count") or 0),
        "rejected_count": int(manifest.get("rejected_count") or 0),
    }


def _manifest_is_published_archive(manifest: dict[str, Any]) -> bool:
    return bool(
        manifest.get("archive_release_doi") == MAVEDB_ARCHIVE_RELEASE_DOI_V4
        and manifest.get("source_version") == MAVEDB_ARCHIVE_RELEASE_DOI_V4
        and manifest.get("archive_source_url") == MAVEDB_ARCHIVE_SOURCE_URL_V4
        and manifest.get("archive_filename") == MAVEDB_ARCHIVE_FILENAME_V4
        and manifest.get("archive_size_bytes") == MAVEDB_ARCHIVE_SIZE_BYTES_V4
        and manifest.get("archive_digest_algorithm") == MAVEDB_ARCHIVE_DIGEST_ALGORITHM_V4
        and manifest.get("archive_digest_value") == MAVEDB_ARCHIVE_DIGEST_VALUE_V4
        and manifest.get("archive_digest_verified")
        and re.fullmatch(r"[0-9a-f]{64}", str(manifest.get("archive_sha256") or ""))
        and manifest.get("archive_license") == "CC0-1.0"
        and manifest.get("archive_citation") == MAVEDB_ARCHIVE_CITATION
        and manifest.get("archive_member_digests_verified")
    )


def _logical_checksum(conn: sqlite3.Connection) -> str:
    digest = sha256()
    table_order = {
        "mavedb_archive_member": "member_name",
        "mavedb_experiment_set": "experiment_set_urn",
        "mavedb_experiment": "experiment_urn",
        "mavedb_target": "target_id",
        "mavedb_score_set": "score_set_urn",
        "mavedb_variant_score": "score_set_urn, variant_urn",
        "mavedb_variant_numeric_value": "score_set_urn, variant_urn, column_name",
    }
    for table, order_by in table_order.items():
        rows = conn.execute(f"select * from {table} order by {order_by}").fetchall()
        for row in rows:
            digest.update(json.dumps(dict(row), sort_keys=True, default=str).encode("utf-8"))
            digest.update(b"\n")
    return digest.hexdigest()


def _archive_proof_ready(archive: MaveDbArchiveRecord | None) -> bool:
    base_ready = bool(
        archive is not None
        and archive.source_id == MAVEDB_LOCAL_SOURCE_ID
        and archive.release_doi
        and archive.upstream_digest_algorithm in SUPPORTED_ARCHIVE_DIGESTS
        and archive.upstream_digest_value
        and archive.upstream_digest_verified
        and re.fullmatch(r"[0-9a-f]{64}", archive.archive_sha256)
        and archive.verified_at
    )
    if not base_ready or archive is None:
        return False
    published = (
        archive.release_doi == MAVEDB_ARCHIVE_RELEASE_DOI_V4
        and archive.source_url == MAVEDB_ARCHIVE_SOURCE_URL_V4
        and archive.archive_filename == MAVEDB_ARCHIVE_FILENAME_V4
        and archive.archive_size_bytes == MAVEDB_ARCHIVE_SIZE_BYTES_V4
        and archive.upstream_digest_algorithm == MAVEDB_ARCHIVE_DIGEST_ALGORITHM_V4
        and archive.upstream_digest_value == MAVEDB_ARCHIVE_DIGEST_VALUE_V4
    )
    fixture = (
        archive.release_doi.startswith(MAVEDB_FIXTURE_RELEASE_PREFIX)
        and archive.source_url == MAVEDB_FIXTURE_SOURCE_URL
    )
    return published or fixture


def _materialization_source_version(
    archive: MaveDbArchiveRecord,
    requested: str | None,
) -> str:
    if archive.release_doi == MAVEDB_ARCHIVE_RELEASE_DOI_V4:
        return archive.release_doi
    return requested or archive.release_doi


def _score_set_url(score_set_urn: str) -> str:
    if not re.fullmatch(r"urn:mavedb:[0-9]{8}-(?:[a-z]+|0)-[1-9][0-9]*", score_set_urn):
        raise ValueError("invalid MaveDB score-set URN")
    return f"{MAVEDB_SCORE_SET_ORIGIN}{quote(score_set_urn, safe=':')}"


def _valid_mavedb_urn(value: str) -> bool:
    return bool(
        re.fullmatch(
            r"urn:mavedb:[0-9]{8}-(?:[a-z]+|0)-[1-9][0-9]*(?:#[1-9][0-9]*)?",
            value,
        )
    )


def _versioned_target_accession(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_:-]+\.[0-9]+", value))


def _single_text_identity(value: Any) -> str | None:
    if value is None or isinstance(value, bool | list | tuple | set | dict):
        return None
    return _optional_text(value)


def _decimal_string(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _identity_key(value: Any) -> str:
    return re.sub(r"\s+", "", _text(value)).casefold()


def _connect_readonly(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma foreign_keys = on")
    return conn


def _resolve_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def _safe_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _license_key(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _optional_text(value: Any) -> str | None:
    text = _text(value)
    return text or None


def _json_list(value: Any) -> list[str]:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return []
    else:
        decoded = value
    return [str(item) for item in decoded] if isinstance(decoded, list) else []


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def mavedb_record_to_canonical_dict(record: MaveDbMatchRecord) -> dict[str, Any]:
    """Stable audit helper that keeps Decimal values as canonical strings."""

    payload = asdict(record)
    payload["variant_score"]["raw_score"] = record.variant_score.raw_score_source or str(
        record.variant_score.raw_score
    )
    payload["variant_score"]["parsed_raw_score"] = _decimal_string(record.variant_score.raw_score)
    for index, value in enumerate(record.variant_score.uncertainty_values):
        payload["variant_score"]["uncertainty_values"][index]["parsed_value"] = _decimal_string(
            value.parsed_value
        )
    return payload
