from __future__ import annotations

from collections.abc import Iterable
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import md5, sha256
import json
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Any, Literal
from urllib.parse import quote

from app.core.config import Settings

MAVEDB_LOCAL_SCHEMA_VERSION = "eamos.mavedb_local.v2"
MAVEDB_LOCAL_SOURCE_ID = "mavedb_cc0_bulk"
MAVEDB_LOCAL_CLI_VERSION = "mavedb-local-cli-v2"
MAVEDB_ARCHIVE_RELEASE_DOI_V4 = "10.5281/zenodo.18511521"
MAVEDB_ARCHIVE_SOURCE_URL_V4 = f"https://doi.org/{MAVEDB_ARCHIVE_RELEASE_DOI_V4}"
MAVEDB_ARCHIVE_FILENAME_V4 = "mavedb-dump.20260206153444.zip"
MAVEDB_ARCHIVE_SIZE_BYTES_V4 = 1_805_088_683
MAVEDB_ARCHIVE_DIGEST_ALGORITHM_V4 = "md5"
MAVEDB_ARCHIVE_DIGEST_VALUE_V4 = "1b25ea356d95277b780de1e78e4e995d"
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


@dataclass(frozen=True)
class MaveDbTargetRecord:
    target_id: str
    target_accession: str
    target_sequence_checksum: str
    gene: str | None = None

    @property
    def exact_identity(self) -> str:
        return f"{self.target_id}|{self.target_accession}|" f"{self.target_sequence_checksum}"


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
        return self.target.target_accession

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

        query = _exact_query_identity(variant)
        if query is None:
            return [], inspection
        with closing(_connect_readonly(self.db_path)) as conn:
            rows = _search_exact_records(conn, query=query, limit=limit)
        return [
            _match_from_row(row, query=query, inspection=inspection) for row in rows
        ], inspection


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
    digest = md5(usedforsecurity=False) if algorithm == "md5" else sha256()
    with archive_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest().lower()
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
        verified_at=_utc_now(),
    )


def filter_mavedb_cc0_records(records: list[MaveDbImportRecord]) -> MaveDbImportResult:
    accepted: list[MaveDbImportRecord] = []
    rejected: list[MaveDbImportRecord] = []
    warnings: list[str] = []
    for record in records:
        score_set = record.score_set
        record_id = record.variant_score.variant_urn
        if _license_key(score_set.license_snapshot) not in CC0_LICENSES:
            rejected.append(record)
            warnings.append(f"mavedb_non_cc0_rejected:{record_id}")
            continue
        if score_set.data_usage_policy_decision != "no_additional_restriction":
            rejected.append(record)
            warnings.append(f"mavedb_data_usage_policy_rejected:{record_id}")
            continue
        if not record.variant_score.raw_score.is_finite():
            rejected.append(record)
            warnings.append(f"mavedb_invalid_score_rejected:{record_id}")
            continue
        accepted.append(record)
    return MaveDbImportResult(
        accepted=tuple(accepted),
        rejected=tuple(rejected),
        warnings=tuple(warnings),
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
    jsonl_files: Iterable[Path],
    archive_proof: MaveDbArchiveRecord | None = None,
    output_path: Path | None = None,
    manifest_path: Path | None = None,
    source_version: str | None = None,
    force: bool = False,
) -> MaveDbLocalMaterializationResult:
    if not _archive_proof_ready(archive_proof):
        return MaveDbLocalMaterializationResult(
            ready=False,
            status="archive_proof_required",
            source_version=source_version,
            archive_release_doi=(archive_proof.release_doi if archive_proof else None),
            archive_digest_verified=False,
            warnings=("verified_upstream_archive_digest_required",),
        )
    assert archive_proof is not None

    destination = _resolve_path(settings, output_path or settings.mavedb_local_sqlite_path)
    manifest_destination = _resolve_path(
        settings,
        manifest_path or settings.mavedb_local_manifest_path,
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
    warnings: list[str] = []
    gate = MaveDbImportResult(accepted=(), rejected=(), warnings=())
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
            records = list(_iter_jsonl_records(jsonl_files, warnings))
            gate = filter_mavedb_cc0_records(records)
            warnings.extend(gate.warnings)
            for record in gate.accepted:
                _insert_record(conn, record)
            checksum = _logical_checksum(conn)
            _write_manifest(
                conn,
                archive=archive_proof,
                source_version=source_version or archive_proof.release_doi,
                accepted_count=len(gate.accepted),
                rejected_count=len(gate.rejected),
                checksum_value=checksum,
                warnings=tuple(_dedupe(warnings)),
            )
            conn.commit()
        temp_path.replace(destination)
    except (OSError, sqlite3.DatabaseError, ValueError) as exc:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
        return MaveDbLocalMaterializationResult(
            ready=False,
            status=f"materialization_failed:{type(exc).__name__}",
            source_version=source_version,
            archive_release_doi=archive_proof.release_doi,
            archive_digest_verified=True,
            warnings=tuple(_dedupe([*warnings, "mavedb_local_destination_not_modified"])),
        )

    inspection = MaveDbLocalStore(destination, manifest_path=None).inspect(verify_checksum=True)
    manifest_destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_destination.write_text(
        json.dumps(inspection.to_sanitized_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return MaveDbLocalMaterializationResult(
        ready=inspection.ready,
        status=inspection.status,
        source_version=inspection.source_version,
        archive_release_doi=inspection.archive_release_doi,
        archive_digest_verified=inspection.archive_digest_verified,
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
          archive_digest_algorithm text not null,
          archive_digest_value text not null,
          archive_digest_verified integer not null check (archive_digest_verified in (0, 1)),
          archive_verified_at text not null,
          accepted_count integer not null,
          rejected_count integer not null,
          checksum_algorithm text not null,
          checksum_value text not null,
          warnings_json text not null
        );
        create table if not exists mavedb_target (
          target_id text primary key,
          target_accession text not null,
          target_accession_norm text not null,
          target_sequence_checksum text not null,
          gene text
        );
        create table if not exists mavedb_score_set (
          score_set_urn text primary key,
          target_id text not null,
          license_snapshot text not null,
          data_usage_policy text,
          data_usage_policy_decision text not null,
          deprecated integer not null check (deprecated in (0, 1)),
          superseded_by text,
          source_url text not null,
          foreign key (target_id) references mavedb_target(target_id)
        );
        create table if not exists mavedb_variant_score (
          score_set_urn text not null,
          variant_urn text not null,
          target_id text not null,
          mave_hgvs text not null,
          mave_hgvs_norm text not null,
          raw_score text not null,
          score_column text not null,
          score_unit text not null,
          vrs_id text,
          vrs_id_norm text,
          genomic_identity text,
          genomic_identity_norm text,
          deprecated integer not null check (deprecated in (0, 1)),
          superseded_by text,
          primary key (score_set_urn, variant_urn, score_column),
          foreign key (score_set_urn) references mavedb_score_set(score_set_urn),
          foreign key (target_id) references mavedb_target(target_id)
        );
        create index if not exists idx_mavedb_target_accession
          on mavedb_target(target_accession_norm);
        create index if not exists idx_mavedb_score_vrs
          on mavedb_variant_score(vrs_id_norm);
        create index if not exists idx_mavedb_score_genomic
          on mavedb_variant_score(genomic_identity_norm);
        create index if not exists idx_mavedb_score_target_hgvs
          on mavedb_variant_score(target_id, mave_hgvs_norm);
        """)


def _require_schema(conn: sqlite3.Connection) -> None:
    tables = {
        row["name"]
        for row in conn.execute("select name from sqlite_master where type='table'").fetchall()
    }
    required = {
        "mavedb_local_manifest",
        "mavedb_target",
        "mavedb_score_set",
        "mavedb_variant_score",
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


def _iter_jsonl_records(paths: Iterable[Path], warnings: list[str]) -> Iterable[MaveDbImportRecord]:
    for path in paths:
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    text = line.strip()
                    if not text:
                        continue
                    try:
                        decoded = json.loads(text)
                    except json.JSONDecodeError:
                        warnings.append("mavedb_local_invalid_jsonl_row")
                        continue
                    if not isinstance(decoded, dict):
                        warnings.append("mavedb_local_non_object_jsonl_row")
                        continue
                    record, warning = _record_from_mapping(decoded)
                    if record is None:
                        warnings.append(warning or "mavedb_local_incomplete_record")
                        continue
                    yield record
        except OSError:
            warnings.append("mavedb_local_input_file_unreadable")


def _record_from_mapping(
    raw: dict[str, Any],
) -> tuple[MaveDbImportRecord | None, str | None]:
    score_set_raw = raw.get("score_set")
    target_raw = raw.get("target")
    variant_raw = raw.get("variant_score")
    if not isinstance(score_set_raw, dict) or not isinstance(target_raw, dict):
        return None, "mavedb_local_authoritative_score_set_or_target_missing"
    if not isinstance(variant_raw, dict):
        return None, "mavedb_local_variant_score_missing"
    if raw.get("targets") or raw.get("variants"):
        return None, "mavedb_local_ambiguous_multi_context_rejected"

    score_set_urn = _text(score_set_raw.get("urn"))
    target_id = _text(target_raw.get("id") or target_raw.get("target_id"))
    target_accession = _text(target_raw.get("accession"))
    target_checksum = _text(
        target_raw.get("sequence_checksum") or target_raw.get("sequenceChecksum")
    )
    variant_urn = _text(variant_raw.get("urn") or variant_raw.get("variant_urn"))
    mave_hgvs = _text(variant_raw.get("mave_hgvs") or variant_raw.get("hgvs"))
    score_column = _text(variant_raw.get("score_column"))
    score_unit = _text(variant_raw.get("score_unit"))
    raw_score = _decimal_or_none(_first_present(variant_raw, ("raw_score", "score", "score_value")))
    license_snapshot = _text(
        score_set_raw.get("license") or score_set_raw.get("license_short_name")
    )
    data_usage_policy = _policy_text(score_set_raw.get("dataUsagePolicy"))

    required = (
        score_set_urn,
        target_id,
        target_accession,
        target_checksum,
        variant_urn,
        mave_hgvs,
        score_column,
        score_unit,
        license_snapshot,
    )
    if not all(required) or raw_score is None:
        return None, "mavedb_local_incomplete_v2_record"
    if not _valid_mavedb_urn(score_set_urn) or not _valid_mavedb_urn(variant_urn):
        return None, "mavedb_local_invalid_urn_rejected"
    if not _versioned_target_accession(target_accession):
        return None, "mavedb_local_unversioned_target_rejected"

    score_set = MaveDbScoreSetRecord(
        score_set_urn=score_set_urn,
        target_id=target_id,
        license_snapshot=license_snapshot,
        data_usage_policy=data_usage_policy,
        data_usage_policy_decision=(
            "no_additional_restriction"
            if data_usage_policy is None
            else "restricted_or_ambiguous_policy"
        ),
        deprecated=bool(score_set_raw.get("deprecated", False)),
        superseded_by=_optional_text(score_set_raw.get("superseded_by")),
        source_url=_score_set_url(score_set_urn),
    )
    target = MaveDbTargetRecord(
        target_id=target_id,
        target_accession=target_accession,
        target_sequence_checksum=target_checksum,
        gene=_optional_text(target_raw.get("gene") or target_raw.get("gene_symbol")),
    )
    variant_score = MaveDbVariantScoreRecord(
        variant_urn=variant_urn,
        score_set_urn=score_set_urn,
        target_id=target_id,
        mave_hgvs=mave_hgvs,
        raw_score=raw_score,
        score_column=score_column,
        score_unit=score_unit,
        vrs_id=_optional_text(variant_raw.get("vrs_id")),
        genomic_identity=_optional_text(
            variant_raw.get("genomic_identity") or variant_raw.get("genomic_hgvs")
        ),
        deprecated=bool(variant_raw.get("deprecated", False)),
        superseded_by=_optional_text(variant_raw.get("superseded_by")),
    )
    return MaveDbImportRecord(score_set, target, variant_score), None


def _insert_record(conn: sqlite3.Connection, record: MaveDbImportRecord) -> None:
    target = record.target
    conn.execute(
        """
        insert into mavedb_target (
          target_id, target_accession, target_accession_norm,
          target_sequence_checksum, gene
        ) values (?, ?, ?, ?, ?)
        on conflict(target_id) do nothing
        """,
        (
            target.target_id,
            target.target_accession,
            _identity_key(target.target_accession),
            target.target_sequence_checksum,
            target.gene,
        ),
    )
    _require_existing_matches(
        conn,
        table="mavedb_target",
        where="target_id = ?",
        key=(target.target_id,),
        expected={
            "target_accession": target.target_accession,
            "target_sequence_checksum": target.target_sequence_checksum,
            "gene": target.gene,
        },
    )

    score_set = record.score_set
    conn.execute(
        """
        insert into mavedb_score_set (
          score_set_urn, target_id, license_snapshot, data_usage_policy,
          data_usage_policy_decision, deprecated, superseded_by, source_url
        ) values (?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(score_set_urn) do nothing
        """,
        (
            score_set.score_set_urn,
            score_set.target_id,
            score_set.license_snapshot,
            score_set.data_usage_policy,
            score_set.data_usage_policy_decision,
            int(score_set.deprecated),
            score_set.superseded_by,
            score_set.source_url,
        ),
    )
    _require_existing_matches(
        conn,
        table="mavedb_score_set",
        where="score_set_urn = ?",
        key=(score_set.score_set_urn,),
        expected={
            "target_id": score_set.target_id,
            "license_snapshot": score_set.license_snapshot,
            "data_usage_policy": score_set.data_usage_policy,
            "data_usage_policy_decision": score_set.data_usage_policy_decision,
        },
    )

    score = record.variant_score
    conn.execute(
        """
        insert into mavedb_variant_score (
          score_set_urn, variant_urn, target_id, mave_hgvs, mave_hgvs_norm,
          raw_score, score_column, score_unit, vrs_id, vrs_id_norm,
          genomic_identity, genomic_identity_norm, deprecated, superseded_by
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(score_set_urn, variant_urn, score_column) do nothing
        """,
        (
            score.score_set_urn,
            score.variant_urn,
            score.target_id,
            score.mave_hgvs,
            _identity_key(score.mave_hgvs),
            _decimal_string(score.raw_score),
            score.score_column,
            score.score_unit,
            score.vrs_id,
            _identity_key(score.vrs_id),
            score.genomic_identity,
            _identity_key(score.genomic_identity),
            int(score.deprecated),
            score.superseded_by,
        ),
    )
    _require_existing_matches(
        conn,
        table="mavedb_variant_score",
        where="score_set_urn = ? and variant_urn = ? and score_column = ?",
        key=(score.score_set_urn, score.variant_urn, score.score_column),
        expected={
            "target_id": score.target_id,
            "mave_hgvs": score.mave_hgvs,
            "raw_score": _decimal_string(score.raw_score),
            "score_unit": score.score_unit,
            "vrs_id": score.vrs_id,
            "genomic_identity": score.genomic_identity,
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


def _exact_query_identity(variant: Any) -> _ExactQuery | None:
    vrs = _single_text_identity(
        getattr(variant, "vrs_id", None) or getattr(variant, "ga4gh_vrs_id", None)
    )
    if vrs:
        return _ExactQuery("exact_vrs", vrs, _identity_key(vrs))

    genomic = _single_text_identity(
        getattr(variant, "genomic_hgvs", None) or getattr(variant, "genomic_hg38", None)
    )
    if genomic:
        return _ExactQuery("exact_genomic_identity", genomic, _identity_key(genomic))

    explicit_target = _single_text_identity(getattr(variant, "target_accession", None))
    explicit_hgvs = _single_text_identity(getattr(variant, "mave_hgvs", None))
    transcript_hgvs = _single_text_identity(getattr(variant, "transcript_hgvs", None))
    target_accession = explicit_target
    mave_hgvs = explicit_hgvs
    if transcript_hgvs and ":" in transcript_hgvs:
        transcript_target, transcript_variant = transcript_hgvs.split(":", 1)
        target_accession = target_accession or transcript_target
        mave_hgvs = mave_hgvs or transcript_variant
    if target_accession and mave_hgvs and _versioned_target_accession(target_accession):
        requested = f"{target_accession}:{mave_hgvs}"
        return _ExactQuery(
            "exact_target_accession_mave_hgvs",
            requested,
            _identity_key(mave_hgvs),
            target_accession=_identity_key(target_accession),
        )
    return None


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
          t.target_accession, t.target_sequence_checksum, t.gene
        from mavedb_variant_score v
        join mavedb_score_set s on s.score_set_urn = v.score_set_urn
        join mavedb_target t on t.target_id = v.target_id
    """
    if query.match_level == "exact_vrs":
        where = "where v.vrs_id_norm = ?"
        params: tuple[object, ...] = (query.value, bounded_limit)
    elif query.match_level == "exact_genomic_identity":
        where = "where v.genomic_identity_norm = ?"
        params = (query.value, bounded_limit)
    else:
        where = "where t.target_accession_norm = ? and v.mave_hgvs_norm = ?"
        params = (query.target_accession, query.value, bounded_limit)
    return conn.execute(
        f"{select} {where} order by v.score_set_urn, v.variant_urn, v.score_column limit ?",
        params,
    ).fetchall()


def _match_from_row(
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
    )
    target = MaveDbTargetRecord(
        target_id=str(row["target_id"]),
        target_accession=str(row["target_accession"]),
        target_sequence_checksum=str(row["target_sequence_checksum"]),
        gene=str(row["gene"]) if row["gene"] else None,
    )
    variant_score = MaveDbVariantScoreRecord(
        variant_urn=str(row["variant_urn"]),
        score_set_urn=str(row["score_set_urn"]),
        target_id=str(row["target_id"]),
        mave_hgvs=str(row["mave_hgvs"]),
        raw_score=Decimal(str(row["raw_score"])),
        score_column=str(row["score_column"]),
        score_unit=str(row["score_unit"]),
        vrs_id=str(row["vrs_id"]) if row["vrs_id"] else None,
        genomic_identity=(str(row["genomic_identity"]) if row["genomic_identity"] else None),
        deprecated=bool(row["deprecated"]),
        superseded_by=str(row["superseded_by"]) if row["superseded_by"] else None,
    )
    matched_identity = {
        "exact_vrs": variant_score.vrs_id,
        "exact_genomic_identity": variant_score.genomic_identity,
        "exact_target_accession_mave_hgvs": (
            f"{target.target_accession}:{variant_score.mave_hgvs}"
        ),
    }[query.match_level]
    return MaveDbMatchRecord(
        archive_release_doi=inspection.archive_release_doi or "",
        archive_digest_algorithm=inspection.archive_digest_algorithm or "",
        archive_digest_value=inspection.archive_digest_value or "",
        archive_digest_verified=inspection.archive_digest_verified,
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
          archive_release_doi, archive_source_url, archive_filename,
          archive_digest_algorithm, archive_digest_value, archive_digest_verified,
          archive_verified_at, accepted_count, rejected_count,
          checksum_algorithm, checksum_value, warnings_json
        ) values (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            MAVEDB_LOCAL_SCHEMA_VERSION,
            source_version,
            _utc_now(),
            MAVEDB_LOCAL_CLI_VERSION,
            archive.release_doi,
            archive.source_url,
            archive.archive_filename,
            archive.upstream_digest_algorithm,
            archive.upstream_digest_value,
            int(archive.upstream_digest_verified),
            archive.verified_at,
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
        "accepted_count": int(manifest.get("accepted_count") or 0),
        "rejected_count": int(manifest.get("rejected_count") or 0),
    }


def _manifest_is_published_archive(manifest: dict[str, Any]) -> bool:
    return bool(
        manifest.get("archive_release_doi") == MAVEDB_ARCHIVE_RELEASE_DOI_V4
        and manifest.get("archive_source_url") == MAVEDB_ARCHIVE_SOURCE_URL_V4
        and manifest.get("archive_filename") == MAVEDB_ARCHIVE_FILENAME_V4
        and manifest.get("archive_digest_algorithm") == MAVEDB_ARCHIVE_DIGEST_ALGORITHM_V4
        and manifest.get("archive_digest_value") == MAVEDB_ARCHIVE_DIGEST_VALUE_V4
        and manifest.get("archive_digest_verified")
    )


def _logical_checksum(conn: sqlite3.Connection) -> str:
    digest = sha256()
    table_order = {
        "mavedb_target": "target_id",
        "mavedb_score_set": "score_set_urn",
        "mavedb_variant_score": "score_set_urn, variant_urn, score_column",
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


def _score_set_url(score_set_urn: str) -> str:
    return f"{MAVEDB_SCORE_SET_ORIGIN}{quote(score_set_urn, safe=':')}"


def _valid_mavedb_urn(value: str) -> bool:
    return bool(re.fullmatch(r"urn:mavedb:[A-Za-z0-9._:#-]+", value))


def _versioned_target_accession(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_:-]+\.[0-9]+", value))


def _single_text_identity(value: Any) -> str | None:
    if value is None or isinstance(value, bool | list | tuple | set | dict):
        return None
    return _optional_text(value)


def _policy_text(value: Any) -> str | None:
    if value is None or value == "" or value == {} or value == []:
        return None
    if isinstance(value, str):
        return value.strip() or None
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None
    return parsed if parsed.is_finite() else None


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


def _license_key(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _optional_text(value: Any) -> str | None:
    text = _text(value)
    return text or None


def _first_present(mapping: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


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
    payload["variant_score"]["raw_score"] = _decimal_string(record.variant_score.raw_score)
    return payload
