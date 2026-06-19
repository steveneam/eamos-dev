from __future__ import annotations

from collections.abc import Iterable
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Any

from app.core.config import Settings

MAVEDB_LOCAL_SCHEMA_VERSION = "eamos.mavedb_local.v1"
MAVEDB_LOCAL_SOURCE_ID = "mavedb_cc0"
MAVEDB_LOCAL_CLI_VERSION = "mavedb-local-cli-v1"

CC0_LICENSES = frozenset({"cc0", "cc0-1.0", "creative commons zero v1.0 universal"})


@dataclass(frozen=True)
class MaveDbRecord:
    score_set_id: str
    variant: str
    score: float | None
    license: str | None
    gene: str | None = None
    accession: str | None = None
    source_url: str | None = None


@dataclass(frozen=True)
class MaveDbImportResult:
    accepted: tuple[MaveDbRecord, ...]
    rejected: tuple[MaveDbRecord, ...]
    warnings: tuple[str, ...]
    provenance: tuple[str, ...] = ("eamos_mavedb_cc0_gate_v1",)


@dataclass(frozen=True)
class MaveDbLocalInspection:
    source_id: str
    status: str
    ready: bool
    enabled: bool = False
    schema_version: str | None = None
    source_version: str | None = None
    accepted_count: int = 0
    rejected_count: int = 0
    actual_size_bytes: int | None = None
    checksum_verified: bool = False
    checksum_algorithm: str | None = None
    checksum_value: str | None = None
    message: str | None = None
    warnings: tuple[str, ...] = ()

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "ready": self.ready,
            "available": self.ready,
            "enabled": self.enabled,
            "runtime_wired": True,
            "schema_version": self.schema_version,
            "source_version": self.source_version,
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
            "public_serialization_allowed": self.ready,
            "launch_gate": None if self.ready else "mavedb_cc0_import_materialization",
        }


@dataclass(frozen=True)
class MaveDbLocalMaterializationResult:
    ready: bool
    status: str
    schema_version: str = MAVEDB_LOCAL_SCHEMA_VERSION
    source_version: str | None = None
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
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "checksum_algorithm": self.checksum_algorithm,
            "checksum_value": self.checksum_value,
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
    """Read-only local MaveDB CC0 functional score access."""

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
                checksum_verified = False
                checksum_value = str(manifest.get("checksum_value") or "")
                if verify_checksum:
                    actual = _logical_checksum(conn)
                    checksum_verified = bool(checksum_value and checksum_value == actual)
                    if not checksum_verified:
                        return MaveDbLocalInspection(
                            source_id=MAVEDB_LOCAL_SOURCE_ID,
                            status="checksum_mismatch",
                            ready=False,
                            enabled=self.enabled,
                            schema_version=str(manifest.get("schema_version") or ""),
                            source_version=str(manifest.get("source_version") or ""),
                            actual_size_bytes=_safe_size(self.db_path),
                            checksum_algorithm="sha256",
                            message="MaveDB CC0 local logical checksum mismatch",
                        )
                return MaveDbLocalInspection(
                    source_id=MAVEDB_LOCAL_SOURCE_ID,
                    status="ready",
                    ready=True,
                    enabled=self.enabled,
                    schema_version=str(manifest.get("schema_version") or ""),
                    source_version=str(manifest.get("source_version") or ""),
                    accepted_count=int(manifest.get("accepted_count") or 0),
                    rejected_count=int(manifest.get("rejected_count") or 0),
                    actual_size_bytes=_safe_size(self.db_path),
                    checksum_verified=checksum_verified,
                    checksum_algorithm="sha256" if verify_checksum else None,
                    checksum_value=checksum_value if checksum_verified else None,
                    warnings=tuple(_json_list(manifest.get("warnings_json"))),
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
        verify_checksum: bool = False,
    ) -> tuple[list[MaveDbRecord], MaveDbLocalInspection]:
        inspection = self.inspect(verify_checksum=verify_checksum)
        if not inspection.ready:
            return [], inspection

        gene = str(getattr(variant, "gene", "") or "").strip().upper()
        terms = _variant_terms(variant)
        if not gene and not terms:
            return [], inspection

        with closing(_connect_readonly(self.db_path)) as conn:
            rows = _search_records(conn, gene=gene, terms=terms, limit=limit)
        return [_record_from_row(row) for row in rows], inspection


def filter_mavedb_cc0_records(records: list[MaveDbRecord]) -> MaveDbImportResult:
    accepted: list[MaveDbRecord] = []
    rejected: list[MaveDbRecord] = []
    warnings: list[str] = []
    for record in records:
        license_key = _license_key(record.license)
        if license_key not in CC0_LICENSES:
            rejected.append(record)
            warnings.append(f"mavedb_non_cc0_rejected:{record.score_set_id}")
            continue
        if record.score is None:
            rejected.append(record)
            warnings.append(f"mavedb_missing_score_rejected:{record.score_set_id}")
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
    output_path: Path | None = None,
    manifest_path: Path | None = None,
    source_version: str | None = None,
    force: bool = False,
) -> MaveDbLocalMaterializationResult:
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
            warnings=("use_force_to_replace_existing_mavedb_local_asset",),
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    warnings: list[str] = []
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
            _create_schema(conn)
            records = list(_iter_jsonl_records(jsonl_files, warnings))
            gate = filter_mavedb_cc0_records(records)
            warnings.extend(gate.warnings)
            for record in gate.accepted:
                _insert_record(conn, record)
            checksum = _logical_checksum(conn)
            _write_manifest(
                conn,
                source_version=source_version or _default_source_version(),
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
          source_version text,
          materialized_at text not null,
          cli_version text not null,
          accepted_count integer not null,
          rejected_count integer not null,
          checksum_algorithm text not null,
          checksum_value text not null,
          warnings_json text not null
        );
        create table if not exists mavedb_functional_score (
          score_set_id text primary key,
          variant text not null,
          variant_norm text not null,
          score real not null,
          license text not null,
          gene text,
          gene_norm text,
          accession text,
          source_url text,
          raw_json text not null
        );
        create table if not exists mavedb_functional_score_term (
          score_set_id text not null,
          term_norm text not null,
          matched_field text not null,
          primary key (score_set_id, term_norm, matched_field),
          foreign key (score_set_id) references mavedb_functional_score(score_set_id)
            on delete cascade
        );
        create index if not exists idx_mavedb_score_gene
          on mavedb_functional_score(gene_norm);
        create index if not exists idx_mavedb_score_terms
          on mavedb_functional_score_term(term_norm);
        """)


def _require_schema(conn: sqlite3.Connection) -> None:
    tables = {
        row["name"]
        for row in conn.execute("select name from sqlite_master where type='table'").fetchall()
    }
    required = {
        "mavedb_local_manifest",
        "mavedb_functional_score",
        "mavedb_functional_score_term",
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


def _iter_jsonl_records(paths: Iterable[Path], warnings: list[str]) -> Iterable[MaveDbRecord]:
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
                    if isinstance(decoded, dict):
                        record = _record_from_mapping(decoded)
                        if record is None:
                            warnings.append("mavedb_local_incomplete_record")
                            continue
                        yield record
                    else:
                        warnings.append("mavedb_local_non_object_jsonl_row")
        except OSError:
            warnings.append("mavedb_local_input_file_unreadable")


def _record_from_mapping(raw: dict[str, Any]) -> MaveDbRecord | None:
    score_set = raw.get("score_set")
    score_set_urn = score_set.get("urn") if isinstance(score_set, dict) else None
    score_set_id = _text(
        raw.get("score_set_id") or raw.get("scoreSetId") or raw.get("urn") or score_set_urn
    )
    variant = _text(
        raw.get("variant")
        or raw.get("hgvs")
        or raw.get("hgvs_nt")
        or raw.get("hgvs_pro")
        or raw.get("hgvs_cdna")
    )
    score = _float_or_none(_first_present(raw, ("score", "score_value", "functional_score")))
    license_value = _text(raw.get("license") or raw.get("licence") or raw.get("license_short_name"))
    gene = _text(raw.get("gene") or raw.get("gene_symbol") or raw.get("target_gene")) or None
    accession = _text(raw.get("accession") or raw.get("uniprot_accession")) or None
    source_url = _text(raw.get("source_url") or raw.get("url")) or None
    if not score_set_id or not variant:
        return None
    return MaveDbRecord(
        score_set_id=score_set_id,
        variant=variant,
        score=score,
        license=license_value or None,
        gene=gene,
        accession=accession,
        source_url=source_url,
    )


def _insert_record(conn: sqlite3.Connection, record: MaveDbRecord) -> None:
    conn.execute(
        """
        insert into mavedb_functional_score (
          score_set_id, variant, variant_norm, score, license, gene, gene_norm,
          accession, source_url, raw_json
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(score_set_id) do update set
          variant=excluded.variant,
          variant_norm=excluded.variant_norm,
          score=excluded.score,
          license=excluded.license,
          gene=excluded.gene,
          gene_norm=excluded.gene_norm,
          accession=excluded.accession,
          source_url=excluded.source_url,
          raw_json=excluded.raw_json
        """,
        (
            record.score_set_id,
            record.variant,
            _normalize_term(record.variant),
            float(record.score if record.score is not None else 0.0),
            record.license or "",
            record.gene,
            _normalize_gene(record.gene),
            record.accession,
            record.source_url,
            json.dumps(record.__dict__, sort_keys=True, default=str),
        ),
    )
    conn.execute(
        "delete from mavedb_functional_score_term where score_set_id = ?",
        (record.score_set_id,),
    )
    for field, term in _record_terms(record):
        conn.execute(
            """
            insert or ignore into mavedb_functional_score_term
              (score_set_id, term_norm, matched_field)
            values (?, ?, ?)
            """,
            (record.score_set_id, _normalize_term(term), field),
        )


def _record_terms(record: MaveDbRecord) -> list[tuple[str, str]]:
    terms = [
        ("score_set_id", record.score_set_id),
        ("variant", record.variant),
    ]
    if ":" in record.variant:
        terms.append(("variant_short", record.variant.split(":")[-1]))
    if record.gene:
        terms.append(("gene", record.gene))
    if record.accession:
        terms.append(("accession", record.accession))
    for token in _variant_search_tokens([record.variant]):
        terms.append(("variant_token", token))
    return [(field, term) for field, term in terms if _normalize_term(term)]


def _search_records(
    conn: sqlite3.Connection,
    *,
    gene: str,
    terms: set[str],
    limit: int,
) -> list[sqlite3.Row]:
    bounded_limit = max(1, min(int(limit), 100))
    normalized_terms = sorted(_normalize_term(term) for term in terms if _normalize_term(term))
    if not normalized_terms:
        return []
    placeholders = ",".join("?" for _ in normalized_terms)
    gene_norm = _normalize_gene(gene)
    if gene_norm:
        rows = conn.execute(
            f"""
            select distinct s.*
            from mavedb_functional_score s
            join mavedb_functional_score_term t on t.score_set_id = s.score_set_id
            where t.term_norm in ({placeholders})
              and (s.gene_norm is null or s.gene_norm = ?)
            order by s.score_set_id
            limit ?
            """,
            (*normalized_terms, gene_norm, bounded_limit),
        ).fetchall()
    else:
        rows = conn.execute(
            f"""
            select distinct s.*
            from mavedb_functional_score s
            join mavedb_functional_score_term t on t.score_set_id = s.score_set_id
            where t.term_norm in ({placeholders})
            order by s.score_set_id
            limit ?
            """,
            (*normalized_terms, bounded_limit),
        ).fetchall()
    return rows


def _record_from_row(row: sqlite3.Row) -> MaveDbRecord:
    return MaveDbRecord(
        score_set_id=str(row["score_set_id"]),
        variant=str(row["variant"]),
        score=float(row["score"]),
        license=str(row["license"]),
        gene=str(row["gene"]) if row["gene"] else None,
        accession=str(row["accession"]) if row["accession"] else None,
        source_url=str(row["source_url"]) if row["source_url"] else None,
    )


def _write_manifest(
    conn: sqlite3.Connection,
    *,
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
          accepted_count, rejected_count, checksum_algorithm, checksum_value,
          warnings_json
        ) values (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(id) do update set
          schema_version=excluded.schema_version,
          source_version=excluded.source_version,
          materialized_at=excluded.materialized_at,
          cli_version=excluded.cli_version,
          accepted_count=excluded.accepted_count,
          rejected_count=excluded.rejected_count,
          checksum_algorithm=excluded.checksum_algorithm,
          checksum_value=excluded.checksum_value,
          warnings_json=excluded.warnings_json
        """,
        (
            MAVEDB_LOCAL_SCHEMA_VERSION,
            source_version,
            _utc_now(),
            MAVEDB_LOCAL_CLI_VERSION,
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


def _logical_checksum(conn: sqlite3.Connection) -> str:
    digest = sha256()
    table_order = {
        "mavedb_functional_score": "score_set_id",
        "mavedb_functional_score_term": "score_set_id, term_norm, matched_field",
    }
    for table, order_by in table_order.items():
        rows = conn.execute(f"select * from {table} order by {order_by}").fetchall()
        for row in rows:
            digest.update(json.dumps(dict(row), sort_keys=True, default=str).encode("utf-8"))
            digest.update(b"\n")
    return digest.hexdigest()


def _variant_terms(variant: Any) -> set[str]:
    terms: set[str] = set()
    for value in (
        getattr(variant, "transcript_hgvs", None),
        _cdna_from_transcript_hgvs(getattr(variant, "transcript_hgvs", None)),
        getattr(variant, "protein_change", None),
        getattr(variant, "genomic_hg38", None),
        getattr(variant, "genomic_hgvs", None),
        getattr(variant, "dbsnp_rsid", None),
    ):
        text = _text(value)
        if text:
            terms.add(text)
    terms.update(_variant_search_tokens(terms))
    return terms


def _variant_search_tokens(values: Iterable[str]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        tokens.update(re.findall(r"\bc\.[0-9+\-*?_]+[ACGT]>[ACGT]\b", value, re.IGNORECASE))
        tokens.update(
            re.findall(
                r"\bp\.?\(?[A-Za-z*]{1,16}\d{1,7}[A-Za-z*=?]{0,16}\)?",
                value,
                re.IGNORECASE,
            )
        )
    expanded: set[str] = set()
    for token in tokens:
        expanded.add(token)
        if token.lower().startswith("p."):
            expanded.add(token[2:])
    return expanded


def _cdna_from_transcript_hgvs(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return text.split(":")[-1].strip() or None


def _connect_readonly(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _resolve_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def _safe_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def _license_key(value: str | None) -> str:
    return _normalize_space(value or "").lower()


def _normalize_gene(value: Any) -> str:
    return re.sub(r"[^A-Z0-9-]+", "", _text(value).upper())


def _normalize_term(value: Any) -> str:
    text = _normalize_space(str(value or "")).lower()
    return re.sub(r"[^a-z0-9.>:_+-]+", "", text)


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _default_source_version() -> str:
    return f"mavedb-cc0-local-{datetime.now(timezone.utc).date().isoformat()}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
