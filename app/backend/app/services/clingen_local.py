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

CLINGEN_LOCAL_SCHEMA_VERSION = "eamos.clingen_local.v1"
CLINGEN_LOCAL_SOURCE_ID = "eamos_clingen_local"
CLINGEN_LOCAL_CLI_VERSION = "clingen-local-cli-v1"


@dataclass(frozen=True)
class ClinGenLocalInspection:
    source_id: str
    status: str
    ready: bool
    enabled: bool = False
    schema_version: str | None = None
    source_version: str | None = None
    classification_count: int = 0
    cspec_entity_count: int = 0
    cspec_link_count: int = 0
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
            "enabled": self.enabled,
            "schema_version": self.schema_version,
            "source_version": self.source_version,
            "classification_count": self.classification_count,
            "cspec_entity_count": self.cspec_entity_count,
            "cspec_link_count": self.cspec_link_count,
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
            "public_serialization_allowed": True,
            "launch_gate": None if self.ready else "clingen_local_materialization",
        }


@dataclass(frozen=True)
class ClinGenLocalMaterializationResult:
    ready: bool
    status: str
    schema_version: str = CLINGEN_LOCAL_SCHEMA_VERSION
    source_version: str | None = None
    classification_count: int = 0
    cspec_entity_count: int = 0
    cspec_link_count: int = 0
    checksum_algorithm: str = "sha256"
    checksum_value: str | None = None
    warnings: tuple[str, ...] = ()

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "status": self.status,
            "schema_version": self.schema_version,
            "source_version": self.source_version,
            "classification_count": self.classification_count,
            "cspec_entity_count": self.cspec_entity_count,
            "cspec_link_count": self.cspec_link_count,
            "checksum_algorithm": self.checksum_algorithm,
            "checksum_value": self.checksum_value,
            "warnings": list(self.warnings),
            "startup_download_allowed": False,
            "request_time_materialization_allowed": False,
            "secret_values_emitted": False,
            "local_path_values_emitted": False,
            "raw_source_rows_emitted": False,
        }


class ClinGenLocalSchemaError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ClinGenLocalStore:
    """Read-only local ClinGen eRepo/CSpec source asset access."""

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

    def inspect(self, *, verify_checksum: bool = True) -> ClinGenLocalInspection:
        if not self.db_path.is_file():
            return ClinGenLocalInspection(
                source_id=CLINGEN_LOCAL_SOURCE_ID,
                status="db_missing",
                ready=False,
                enabled=self.enabled,
                message="ClinGen local SQLite asset is missing",
            )
        if self.manifest_path is not None and not self.manifest_path.is_file():
            return ClinGenLocalInspection(
                source_id=CLINGEN_LOCAL_SOURCE_ID,
                status="manifest_missing",
                ready=False,
                enabled=self.enabled,
                actual_size_bytes=_safe_size(self.db_path),
                message="ClinGen local manifest is missing",
            )

        try:
            with closing(_connect_readonly(self.db_path)) as conn:
                _require_schema(conn)
                manifest = _manifest_row(conn)
                counts = _count_profile(conn)
                checksum_verified = False
                checksum_value = str(manifest.get("checksum_value") or "")
                if verify_checksum:
                    actual = _logical_checksum(conn)
                    checksum_verified = bool(checksum_value and checksum_value == actual)
                    if not checksum_verified:
                        return ClinGenLocalInspection(
                            source_id=CLINGEN_LOCAL_SOURCE_ID,
                            status="checksum_mismatch",
                            ready=False,
                            enabled=self.enabled,
                            schema_version=str(manifest.get("schema_version") or ""),
                            source_version=str(manifest.get("source_version") or ""),
                            actual_size_bytes=_safe_size(self.db_path),
                            checksum_algorithm="sha256",
                            message="ClinGen local logical checksum mismatch",
                        )
                return ClinGenLocalInspection(
                    source_id=CLINGEN_LOCAL_SOURCE_ID,
                    status="ready",
                    ready=True,
                    enabled=self.enabled,
                    schema_version=str(manifest.get("schema_version") or ""),
                    source_version=str(manifest.get("source_version") or ""),
                    classification_count=counts["classification_count"],
                    cspec_entity_count=counts["cspec_entity_count"],
                    cspec_link_count=counts["cspec_link_count"],
                    actual_size_bytes=_safe_size(self.db_path),
                    checksum_verified=checksum_verified,
                    checksum_algorithm="sha256" if verify_checksum else None,
                    checksum_value=checksum_value if checksum_verified else None,
                    warnings=tuple(_json_list(manifest.get("warnings_json"))),
                )
        except sqlite3.DatabaseError:
            return ClinGenLocalInspection(
                source_id=CLINGEN_LOCAL_SOURCE_ID,
                status="db_unreadable",
                ready=False,
                enabled=self.enabled,
                actual_size_bytes=_safe_size(self.db_path),
                message="ClinGen local SQLite asset is unreadable",
            )
        except ClinGenLocalSchemaError as exc:
            return ClinGenLocalInspection(
                source_id=CLINGEN_LOCAL_SOURCE_ID,
                status=exc.code,
                ready=False,
                enabled=self.enabled,
                actual_size_bytes=_safe_size(self.db_path),
                message=str(exc),
            )

    def search_records(
        self,
        *,
        gene: str,
        terms: Iterable[str],
        limit: int,
        verify_checksum: bool = True,
    ) -> tuple[list[dict[str, Any]], ClinGenLocalInspection, bool]:
        inspection = self.inspect(verify_checksum=verify_checksum)
        if not inspection.ready:
            return [], inspection, True

        normalized_gene = gene.strip().upper()
        normalized_terms = [term for term in (_normalize_term(item) for item in terms) if term]
        if not normalized_gene:
            return [], inspection, False

        with closing(_connect_readonly(self.db_path)) as conn:
            rows = _search_records(conn, normalized_gene, normalized_terms, limit=limit)
            complete = _coverage_complete(conn)
        return rows, inspection, not rows and not complete

    def search_records_by_raw_text(
        self,
        *,
        gene: str,
        terms: Iterable[str],
        limit: int,
        verify_checksum: bool = True,
    ) -> tuple[list[dict[str, Any]], ClinGenLocalInspection, bool]:
        inspection = self.inspect(verify_checksum=verify_checksum)
        if not inspection.ready:
            return [], inspection, True

        normalized_gene = gene.strip().upper()
        raw_terms = [term for term in (_raw_like_term(item) for item in terms) if term]
        if not normalized_gene or not raw_terms:
            return [], inspection, False

        with closing(_connect_readonly(self.db_path)) as conn:
            rows = _search_records_by_raw_text(
                conn,
                normalized_gene,
                raw_terms,
                limit=limit,
            )
            complete = _coverage_complete(conn)
        return rows, inspection, not rows and not complete

    def search_records_by_terms(
        self,
        *,
        terms: Iterable[str],
        limit: int,
        verify_checksum: bool = True,
    ) -> tuple[list[dict[str, Any]], ClinGenLocalInspection, bool]:
        inspection = self.inspect(verify_checksum=verify_checksum)
        if not inspection.ready:
            return [], inspection, True

        normalized_terms = [term for term in (_normalize_term(item) for item in terms) if term]
        if not normalized_terms:
            return [], inspection, False

        with closing(_connect_readonly(self.db_path)) as conn:
            rows = _search_records_by_terms(conn, normalized_terms, limit=limit)
            complete = _coverage_complete(conn)
        return rows, inspection, not rows and not complete


def inspect_clingen_local_store(
    settings: Settings, *, verify_checksum: bool = True
) -> ClinGenLocalInspection:
    return ClinGenLocalStore(
        _resolve_path(settings, settings.clingen_local_sqlite_path),
        manifest_path=_resolve_path(settings, settings.clingen_local_manifest_path),
        enabled=settings.clingen_local_enabled,
    ).inspect(verify_checksum=verify_checksum)


def materialize_clingen_local_store(
    settings: Settings,
    *,
    erepo_jsonl_files: Iterable[Path] = (),
    cspec_jsonl_files: Iterable[Path] = (),
    output_path: Path | None = None,
    manifest_path: Path | None = None,
    source_version: str | None = None,
    force: bool = False,
) -> ClinGenLocalMaterializationResult:
    destination = _resolve_path(settings, output_path or settings.clingen_local_sqlite_path)
    manifest_destination = _resolve_path(
        settings, manifest_path or settings.clingen_local_manifest_path
    )
    if destination.exists() and not force:
        return ClinGenLocalMaterializationResult(
            ready=False,
            status="destination_exists",
            source_version=source_version,
            warnings=("use_force_to_replace_existing_clingen_local_asset",),
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
            erepo_count = 0
            for record in _iter_jsonl_records(erepo_jsonl_files, warnings):
                _insert_erepo_record(conn, record, source_version=source_version)
                erepo_count += 1
            cspec_count = 0
            for record in _iter_jsonl_records(cspec_jsonl_files, warnings):
                _insert_cspec_entity(conn, record)
                cspec_count += 1
            checksum = _logical_checksum(conn)
            _write_manifest(
                conn,
                source_version=source_version or _default_source_version(),
                classification_count=erepo_count,
                cspec_entity_count=cspec_count,
                checksum_value=checksum,
                warnings=tuple(_dedupe(warnings)),
            )
            conn.commit()
        temp_path.replace(destination)
    except (OSError, sqlite3.DatabaseError, ValueError) as exc:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
        return ClinGenLocalMaterializationResult(
            ready=False,
            status=f"materialization_failed:{type(exc).__name__}",
            source_version=source_version,
            warnings=tuple(_dedupe([*warnings, "clingen_local_destination_not_modified"])),
        )

    inspection = ClinGenLocalStore(destination, manifest_path=None).inspect(verify_checksum=True)
    manifest_destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_destination.write_text(
        json.dumps(inspection.to_sanitized_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return ClinGenLocalMaterializationResult(
        ready=inspection.ready,
        status=inspection.status,
        source_version=inspection.source_version,
        classification_count=inspection.classification_count,
        cspec_entity_count=inspection.cspec_entity_count,
        cspec_link_count=inspection.cspec_link_count,
        checksum_value=inspection.checksum_value,
        warnings=inspection.warnings,
    )


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        create table if not exists clingen_local_manifest (
          id integer primary key check (id = 1),
          schema_version text not null,
          source_version text,
          materialized_at text not null,
          cli_version text not null,
          classification_count integer not null,
          cspec_entity_count integer not null,
          cspec_link_count integer not null,
          checksum_algorithm text not null,
          checksum_value text not null,
          warnings_json text not null
        );
        create table if not exists clingen_erepo_classification (
          record_id text primary key,
          gene text not null,
          caid text,
          clinvar_variation_id text,
          uuid text,
          classification text,
          review_status text,
          assertion_method text,
          approved_date text,
          published_date text,
          source_url text,
          source_version text,
          fetched_at text,
          raw_json text not null
        );
        create table if not exists clingen_erepo_classification_term (
          record_id text not null,
          term_norm text not null,
          matched_field text not null,
          primary key (record_id, term_norm, matched_field),
          foreign key (record_id) references clingen_erepo_classification(record_id)
            on delete cascade
        );
        create index if not exists idx_clingen_erepo_gene
          on clingen_erepo_classification(gene);
        create index if not exists idx_clingen_erepo_terms
          on clingen_erepo_classification_term(term_norm);
        create table if not exists clingen_cspec_entity (
          entity_id text primary key,
          entity_type text not null,
          ldh_id text,
          ent_iri text,
          ldh_iri text,
          modified text,
          raw_json text not null
        );
        create table if not exists clingen_cspec_link (
          entity_id text not null,
          linked_type text not null,
          linked_id text not null,
          primary key (entity_id, linked_type, linked_id),
          foreign key (entity_id) references clingen_cspec_entity(entity_id)
            on delete cascade
        );
        """)


def _require_schema(conn: sqlite3.Connection) -> None:
    tables = {
        row["name"]
        for row in conn.execute("select name from sqlite_master where type='table'").fetchall()
    }
    required = {
        "clingen_local_manifest",
        "clingen_erepo_classification",
        "clingen_erepo_classification_term",
        "clingen_cspec_entity",
        "clingen_cspec_link",
    }
    missing = sorted(required - tables)
    if missing:
        raise ClinGenLocalSchemaError(
            "schema_missing_tables",
            f"ClinGen local asset missing tables: {', '.join(missing)}",
        )
    manifest = _manifest_row(conn)
    if manifest.get("schema_version") != CLINGEN_LOCAL_SCHEMA_VERSION:
        raise ClinGenLocalSchemaError("schema_version_mismatch", "ClinGen schema mismatch")


def _insert_erepo_record(
    conn: sqlite3.Connection,
    record: dict[str, Any],
    *,
    source_version: str | None,
) -> None:
    raw = dict(record)
    record_id = _record_id(raw)
    gene = _text(raw.get("gene") or raw.get("geneSymbol")).upper()
    if not record_id or not gene:
        return
    source_url = _text(raw.get("sourceUrl") or raw.get("url") or raw.get("iri"))
    row_source_version = _text(raw.get("sourceVersion") or raw.get("source_version"))
    fetched_at = _text(raw.get("fetchedAt") or raw.get("lastFetchedAt"))
    conn.execute(
        """
        insert into clingen_erepo_classification (
          record_id, gene, caid, clinvar_variation_id, uuid, classification,
          review_status, assertion_method, approved_date, published_date, source_url,
          source_version, fetched_at, raw_json
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(record_id) do update set
          gene=excluded.gene,
          caid=excluded.caid,
          clinvar_variation_id=excluded.clinvar_variation_id,
          uuid=excluded.uuid,
          classification=excluded.classification,
          review_status=excluded.review_status,
          assertion_method=excluded.assertion_method,
          approved_date=excluded.approved_date,
          published_date=excluded.published_date,
          source_url=excluded.source_url,
          source_version=excluded.source_version,
          fetched_at=excluded.fetched_at,
          raw_json=excluded.raw_json
        """,
        (
            record_id,
            gene,
            _text(raw.get("caId") or raw.get("caid")),
            _clinvar_variation_id(raw),
            _text(raw.get("uuid")),
            _classification(raw),
            _review_status(raw),
            _text(raw.get("assertionMethod") or raw.get("criteriaSet")),
            _text(raw.get("approvedDate") or raw.get("dateLastEvaluated")),
            _text(raw.get("publishedDate")),
            source_url,
            row_source_version or source_version,
            fetched_at,
            json.dumps(raw, sort_keys=True, default=str),
        ),
    )
    conn.execute("delete from clingen_erepo_classification_term where record_id = ?", (record_id,))
    for field, term in _erepo_terms(raw):
        conn.execute(
            """
            insert or ignore into clingen_erepo_classification_term
              (record_id, term_norm, matched_field)
            values (?, ?, ?)
            """,
            (record_id, _normalize_term(term), field),
        )


def _insert_cspec_entity(conn: sqlite3.Connection, record: dict[str, Any]) -> None:
    entity_id = _text(record.get("entId") or record.get("entity_id") or record.get("id"))
    ldh_id = _text(record.get("ldhId") or record.get("ldh_id"))
    if not entity_id and ldh_id:
        entity_id = ldh_id
    if not entity_id:
        return
    entity_type = _text(record.get("entType") or record.get("entity_type") or record.get("type"))
    if not entity_type:
        entity_type = _infer_cspec_entity_type(record)
    conn.execute(
        """
        insert into clingen_cspec_entity (
          entity_id, entity_type, ldh_id, ent_iri, ldh_iri, modified, raw_json
        ) values (?, ?, ?, ?, ?, ?, ?)
        on conflict(entity_id) do update set
          entity_type=excluded.entity_type,
          ldh_id=excluded.ldh_id,
          ent_iri=excluded.ent_iri,
          ldh_iri=excluded.ldh_iri,
          modified=excluded.modified,
          raw_json=excluded.raw_json
        """,
        (
            entity_id,
            entity_type,
            ldh_id,
            _text(record.get("entIri") or record.get("ent_iri")),
            _text(record.get("ldhIri") or record.get("ldh_iri")),
            _text(record.get("modified")),
            json.dumps(record, sort_keys=True, default=str),
        ),
    )
    for linked_type, linked_id in _cspec_links(record):
        conn.execute(
            """
            insert or ignore into clingen_cspec_link (entity_id, linked_type, linked_id)
            values (?, ?, ?)
            """,
            (entity_id, linked_type, linked_id),
        )


def _iter_jsonl_records(paths: Iterable[Path], warnings: list[str]):
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
                        warnings.append("clingen_local_invalid_jsonl_row")
                        continue
                    if isinstance(decoded, dict):
                        yield decoded
                    else:
                        warnings.append("clingen_local_non_object_jsonl_row")
        except OSError:
            warnings.append("clingen_local_input_file_unreadable")


def _search_records(
    conn: sqlite3.Connection,
    gene: str,
    terms: list[str],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    bounded_limit = max(1, min(int(limit), 100))
    if terms:
        placeholders = ",".join("?" for _ in terms)
        rows = conn.execute(
            f"""
            select distinct c.*
            from clingen_erepo_classification c
            join clingen_erepo_classification_term t on t.record_id = c.record_id
            where c.gene = ? and t.term_norm in ({placeholders})
            order by coalesce(c.approved_date, c.published_date, '') desc, c.record_id
            limit ?
            """,
            (gene, *terms, bounded_limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            select distinct c.*
            from clingen_erepo_classification c
            where c.gene = ?
            order by coalesce(c.approved_date, c.published_date, '') desc, c.record_id
            limit ?
            """,
            (gene, bounded_limit),
        ).fetchall()
    return [_record_from_row(row) for row in rows]


def _search_records_by_raw_text(
    conn: sqlite3.Connection,
    gene: str,
    terms: list[str],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    bounded_limit = max(1, min(int(limit), 100))
    clauses = " or ".join("lower(c.raw_json) like ?" for _ in terms)
    rows = conn.execute(
        f"""
        select distinct c.*
        from clingen_erepo_classification c
        where c.gene = ? and ({clauses})
        order by coalesce(c.approved_date, c.published_date, '') desc, c.record_id
        limit ?
        """,
        (gene, *(f"%{term}%" for term in terms), bounded_limit),
    ).fetchall()
    return [_record_from_row(row) for row in rows]


def _search_records_by_terms(
    conn: sqlite3.Connection,
    terms: list[str],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    bounded_limit = max(1, min(int(limit), 100))
    placeholders = ",".join("?" for _ in terms)
    rows = conn.execute(
        f"""
        select distinct c.*
        from clingen_erepo_classification c
        join clingen_erepo_classification_term t on t.record_id = c.record_id
        where t.term_norm in ({placeholders})
        order by coalesce(c.approved_date, c.published_date, '') desc, c.record_id
        limit ?
        """,
        (*terms, bounded_limit),
    ).fetchall()
    return [_record_from_row(row) for row in rows]


def _record_from_row(row: sqlite3.Row) -> dict[str, Any]:
    record = _json_object(row["raw_json"])
    if row["source_version"] and not record.get("sourceVersion"):
        record["sourceVersion"] = row["source_version"]
    if row["source_url"] and not record.get("sourceUrl"):
        record["sourceUrl"] = row["source_url"]
    if row["fetched_at"] and not record.get("fetchedAt"):
        record["fetchedAt"] = row["fetched_at"]
    return record


def _write_manifest(
    conn: sqlite3.Connection,
    *,
    source_version: str,
    classification_count: int,
    cspec_entity_count: int,
    checksum_value: str,
    warnings: tuple[str, ...],
) -> None:
    cspec_link_count = _scalar_int(conn, "select count(*) from clingen_cspec_link")
    conn.execute(
        """
        insert into clingen_local_manifest (
          id, schema_version, source_version, materialized_at, cli_version,
          classification_count, cspec_entity_count, cspec_link_count,
          checksum_algorithm, checksum_value, warnings_json
        ) values (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(id) do update set
          schema_version=excluded.schema_version,
          source_version=excluded.source_version,
          materialized_at=excluded.materialized_at,
          cli_version=excluded.cli_version,
          classification_count=excluded.classification_count,
          cspec_entity_count=excluded.cspec_entity_count,
          cspec_link_count=excluded.cspec_link_count,
          checksum_algorithm=excluded.checksum_algorithm,
          checksum_value=excluded.checksum_value,
          warnings_json=excluded.warnings_json
        """,
        (
            CLINGEN_LOCAL_SCHEMA_VERSION,
            source_version,
            _utc_now(),
            CLINGEN_LOCAL_CLI_VERSION,
            classification_count,
            cspec_entity_count,
            cspec_link_count,
            "sha256",
            checksum_value,
            json.dumps(list(warnings), sort_keys=True),
        ),
    )


def _manifest_row(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute("select * from clingen_local_manifest where id = 1").fetchone()
    if row is None:
        raise ClinGenLocalSchemaError("manifest_missing", "ClinGen local manifest row missing")
    return dict(row)


def _count_profile(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        "classification_count": _scalar_int(
            conn, "select count(*) from clingen_erepo_classification"
        ),
        "cspec_entity_count": _scalar_int(conn, "select count(*) from clingen_cspec_entity"),
        "cspec_link_count": _scalar_int(conn, "select count(*) from clingen_cspec_link"),
    }


def _coverage_complete(conn: sqlite3.Connection) -> bool:
    counts = _count_profile(conn)
    return counts["classification_count"] > 0


def _logical_checksum(conn: sqlite3.Connection) -> str:
    digest = sha256()
    table_order = {
        "clingen_erepo_classification": "record_id",
        "clingen_erepo_classification_term": "record_id, term_norm, matched_field",
        "clingen_cspec_entity": "entity_id",
        "clingen_cspec_link": "entity_id, linked_type, linked_id",
    }
    for table, order_by in table_order.items():
        rows = conn.execute(f"select * from {table} order by {order_by}").fetchall()
        for row in rows:
            digest.update(json.dumps(dict(row), sort_keys=True, default=str).encode("utf-8"))
            digest.update(b"\n")
    return digest.hexdigest()


def _erepo_terms(record: dict[str, Any]) -> list[tuple[str, str]]:
    terms: list[tuple[str, str]] = []
    for field in (
        "gene",
        "geneSymbol",
        "caId",
        "caid",
        "cvId",
        "clinvarVariationId",
        "uuid",
        "_id",
        "_key",
        "classificationId",
        "preferredVarTitle",
        "variantTitle",
    ):
        for value in _string_values(record.get(field)):
            _append_term(terms, field, value)
    for value in _string_values(record.get("hgvs")):
        _append_term(terms, "hgvs", value)
        if ":" in value:
            _append_term(terms, "hgvs_cdna", value.split(":")[-1])
    for value in _string_values(record.get("metCodes", record.get("metCriteria"))):
        _append_term(terms, "criteria", value)
    expert_panel = record.get("expertPanel")
    if isinstance(expert_panel, dict):
        for value in _string_values(expert_panel):
            _append_term(terms, "expertPanel", value)
    return terms


def _append_term(terms: list[tuple[str, str]], field: str, value: str | None) -> None:
    normalized = _normalize_term(value)
    if normalized:
        terms.append((field, value or ""))


def _cspec_links(record: dict[str, Any]) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for key in ("ld", "ldFor"):
        value = record.get(key)
        if isinstance(value, dict):
            items = [value]
        elif isinstance(value, list):
            items = value
        else:
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            for linked_type, rows in item.items():
                if not isinstance(rows, list):
                    rows = [rows]
                for row in rows:
                    if isinstance(row, dict):
                        linked_id = _text(row.get("entId") or row.get("ldhId") or row.get("id"))
                    else:
                        linked_id = _text(row)
                    if linked_id:
                        links.append((str(linked_type), linked_id))
    return links


def _infer_cspec_entity_type(record: dict[str, Any]) -> str:
    iri = _text(record.get("entIri") or record.get("ldhIri")) or ""
    match = re.search(r"/cspec/([^/]+)/", iri)
    return match.group(1) if match else "CSpecEntity"


def _record_id(record: dict[str, Any]) -> str:
    for key in ("uuid", "_id", "_key", "id", "classificationId", "caId"):
        value = _text(record.get(key))
        if value:
            return value
    payload = json.dumps(record, sort_keys=True, default=str)
    return f"sha256:{sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def _classification(record: dict[str, Any]) -> str | None:
    for key in (
        "classification",
        "classificationDescription",
        "provisionalClassification",
        "provisionalVariantClassification",
        "clinicalSignificance",
    ):
        value = _text(record.get(key))
        if value:
            return value
    return None


def _review_status(record: dict[str, Any]) -> str | None:
    for key in ("reviewStatus", "classificationStatus", "approvalStatus", "status"):
        value = _text(record.get(key))
        if value:
            return value
    return _text(record.get("assertionMethod"))


def _clinvar_variation_id(record: dict[str, Any]) -> str | None:
    for key in ("cvId", "clinvarVariationId", "variation_id", "variationId"):
        text = _text(record.get(key))
        if text:
            return text
    for text in _string_values(record):
        match = re.search(r"\bVCV0*(\d{1,12})\b", text, flags=re.IGNORECASE)
        if match:
            return f"VCV{int(match.group(1)):09d}"
    return None


def _scalar_int(conn: sqlite3.Connection, query: str) -> int:
    row = conn.execute(query).fetchone()
    return int(row[0] or 0) if row is not None else 0


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


def _json_list(value: Any) -> list[str]:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return []
    else:
        decoded = value
    return [str(item) for item in decoded] if isinstance(decoded, list) else []


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
    else:
        decoded = value
    return dict(decoded) if isinstance(decoded, dict) else {}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("description", "label", "name", "value"):
            text = _text(value.get(key))
            if text:
                return text
        return ""
    text = str(value).strip()
    return text


def _string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, dict):
        values: list[str] = []
        for child in value.values():
            values.extend(_string_values(child))
        return values
    if isinstance(value, (list, tuple, set)):
        values = []
        for child in value:
            values.extend(_string_values(child))
        return values
    if value is None:
        return []
    return [str(value).strip()]


def _normalize_term(value: Any) -> str:
    text = _normalize_space(str(value or "")).lower()
    return re.sub(r"[^a-z0-9.>:_+-]+", "", text)


def _raw_like_term(value: Any) -> str:
    return _normalize_space(str(value or "")).lower()


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _default_source_version() -> str:
    return f"clingen-local-{datetime.now(timezone.utc).date().isoformat()}"


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
