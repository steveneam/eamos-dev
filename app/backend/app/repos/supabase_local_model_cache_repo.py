from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import logging
import re
from typing import Any
from uuid import uuid4

from sqlalchemy import bindparam, text

from app.core.db import build_session_factory, session_scope
from app.data_sources.runtime_assets import SourceAssetMaterializationRecord
from app.repos.source_cache_repo import SourceCachePayload
from app.schemas.protein_annotation import ProteinDomainTrack

logger = logging.getLogger(__name__)

CLINICAL_GENE_DISEASE_STATEMENT_TIMEOUT_MS = 5_000


class SupabaseLocalModelCacheError(RuntimeError):
    pass


@dataclass(frozen=True)
class LocalModelCacheEntry:
    cache_family: str
    source_id: str
    cache_key: str
    normalized_identity: dict[str, Any] = field(default_factory=dict)
    request_identity: dict[str, Any] = field(default_factory=dict)
    status: str = "stored"
    payload: dict[str, Any] = field(default_factory=dict)
    raw_payload: Any = None
    provenance: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    source_url: str | None = None
    source_release: str | None = None
    source_checksum_sha256: str | None = None
    fetched_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SqlAlchemySupabaseLocalModelCacheStore:
    def __init__(self, session_factory, *, schema: str = "eamos_private") -> None:
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", schema):
            raise ValueError("invalid Supabase cache schema name")
        self.session_factory = session_factory
        self.schema = schema

    @property
    def cache_table(self) -> str:
        return f"{self.schema}.local_model_cache_entries"

    @property
    def source_versions_table(self) -> str:
        return f"{self.schema}.local_source_versions"

    @property
    def jobs_table(self) -> str:
        return f"{self.schema}.local_model_jobs"

    @property
    def clinical_mondo_table(self) -> str:
        return f"{self.schema}.clinical_mondo_diseases"

    @property
    def clinical_hpo_terms_table(self) -> str:
        return f"{self.schema}.clinical_hpo_terms"

    @property
    def clinical_hpo_disease_table(self) -> str:
        return f"{self.schema}.clinical_hpo_disease_phenotypes"

    @property
    def clinical_hpo_gene_table(self) -> str:
        return f"{self.schema}.clinical_hpo_gene_phenotypes"

    @property
    def clinical_clingen_table(self) -> str:
        return f"{self.schema}.clinical_clingen_gene_validity"

    @property
    def clinical_gencc_table(self) -> str:
        return f"{self.schema}.clinical_gencc_assertions"

    @property
    def source_asset_objects_table(self) -> str:
        return f"{self.schema}.source_asset_objects"

    @property
    def source_asset_materializations_table(self) -> str:
        return f"{self.schema}.source_asset_materializations"

    def get_entry(
        self,
        *,
        cache_family: str,
        source_id: str,
        cache_key: str,
    ) -> LocalModelCacheEntry | None:
        statement = text(f"""
            select
                cache_family,
                source_id,
                cache_key,
                normalized_identity,
                request_identity,
                status,
                payload,
                raw_payload,
                provenance,
                warnings,
                source_url,
                source_release,
                source_checksum_sha256,
                fetched_at,
                expires_at,
                created_at,
                updated_at
            from {self.cache_table}
            where cache_family = :cache_family
              and source_id = :source_id
              and cache_key = :cache_key
            """)
        try:
            with session_scope(self.session_factory) as session:
                row = (
                    session.execute(
                        statement,
                        {
                            "cache_family": cache_family,
                            "source_id": source_id,
                            "cache_key": cache_key,
                        },
                    )
                    .mappings()
                    .one_or_none()
                )
        except Exception as exc:
            raise SupabaseLocalModelCacheError(
                _safe_error_message("Supabase cache read failed.", exc)
            ) from exc
        if row is None:
            return None
        return LocalModelCacheEntry(
            cache_family=str(row["cache_family"]),
            source_id=str(row["source_id"]),
            cache_key=str(row["cache_key"]),
            normalized_identity=dict(row["normalized_identity"] or {}),
            request_identity=dict(row["request_identity"] or {}),
            status=str(row["status"]),
            payload=dict(row["payload"] or {}),
            raw_payload=row["raw_payload"],
            provenance=dict(row["provenance"] or {}),
            warnings=list(row["warnings"] or []),
            source_url=row["source_url"],
            source_release=row["source_release"],
            source_checksum_sha256=row["source_checksum_sha256"],
            fetched_at=_aware_or_none(row["fetched_at"]),
            expires_at=_aware_or_none(row["expires_at"]),
            created_at=_aware_or_none(row["created_at"]),
            updated_at=_aware_or_none(row["updated_at"]),
        )

    def upsert_entry(self, entry: LocalModelCacheEntry) -> None:
        statement = text(f"""
            insert into {self.cache_table} (
                cache_family,
                source_id,
                cache_key,
                normalized_identity,
                request_identity,
                status,
                payload,
                raw_payload,
                provenance,
                warnings,
                source_url,
                source_release,
                source_checksum_sha256,
                fetched_at,
                expires_at,
                updated_at
            )
            values (
                :cache_family,
                :source_id,
                :cache_key,
                cast(:normalized_identity as jsonb),
                cast(:request_identity as jsonb),
                :status,
                cast(:payload as jsonb),
                cast(:raw_payload as jsonb),
                cast(:provenance as jsonb),
                cast(:warnings as jsonb),
                :source_url,
                :source_release,
                :source_checksum_sha256,
                :fetched_at,
                :expires_at,
                timezone('utc'::text, now())
            )
            on conflict (cache_family, source_id, cache_key)
            do update set
                normalized_identity = excluded.normalized_identity,
                request_identity = excluded.request_identity,
                status = excluded.status,
                payload = excluded.payload,
                raw_payload = excluded.raw_payload,
                provenance = excluded.provenance,
                warnings = excluded.warnings,
                source_url = excluded.source_url,
                source_release = excluded.source_release,
                source_checksum_sha256 = excluded.source_checksum_sha256,
                fetched_at = excluded.fetched_at,
                expires_at = excluded.expires_at,
                restricted_fields_stripped = true,
                public_serialization_policy = 'backend_only_private_cache',
                updated_at = timezone('utc'::text, now())
            """)
        params = {
            "cache_family": entry.cache_family,
            "source_id": entry.source_id,
            "cache_key": entry.cache_key,
            "normalized_identity": _json_param(entry.normalized_identity),
            "request_identity": _json_param(entry.request_identity),
            "status": entry.status,
            "payload": _json_param(entry.payload),
            "raw_payload": _json_param(entry.raw_payload),
            "provenance": _json_param(entry.provenance),
            "warnings": _json_param(entry.warnings),
            "source_url": entry.source_url,
            "source_release": entry.source_release,
            "source_checksum_sha256": entry.source_checksum_sha256,
            "fetched_at": entry.fetched_at or _now(),
            "expires_at": entry.expires_at,
        }
        try:
            with session_scope(self.session_factory) as session:
                session.execute(statement, params)
        except Exception as exc:
            raise SupabaseLocalModelCacheError(
                _safe_error_message("Supabase cache write failed.", exc)
            ) from exc

    def delete_entry(
        self,
        *,
        cache_family: str,
        source_id: str,
        cache_key: str,
    ) -> None:
        statement = text(f"""
            delete from {self.cache_table}
            where cache_family = :cache_family
              and source_id = :source_id
              and cache_key = :cache_key
            """)
        try:
            with session_scope(self.session_factory) as session:
                session.execute(
                    statement,
                    {
                        "cache_family": cache_family,
                        "source_id": source_id,
                        "cache_key": cache_key,
                    },
                )
        except Exception as exc:
            raise SupabaseLocalModelCacheError(
                _safe_error_message("Supabase cache delete failed.", exc)
            ) from exc

    def smoke_test(self) -> None:
        cache_family = "supabase_cache_smoke"
        source_id = "warm_source_cache"
        cache_key = f"smoke:{uuid4().hex}"
        try:
            self.upsert_entry(
                LocalModelCacheEntry(
                    cache_family=cache_family,
                    source_id=source_id,
                    cache_key=cache_key,
                    normalized_identity={"smoke": True},
                    request_identity={"smoke": True},
                    status="smoke",
                    payload={"ok": True},
                    provenance={"repo": "SqlAlchemySupabaseLocalModelCacheStore.smoke_test"},
                    warnings=[],
                    fetched_at=_now(),
                )
            )
            hit = self.get_entry(
                cache_family=cache_family,
                source_id=source_id,
                cache_key=cache_key,
            )
            if hit is None:
                raise SupabaseLocalModelCacheError(
                    "Supabase cache smoke failed: write returned no readable row."
                )
        finally:
            try:
                self.delete_entry(
                    cache_family=cache_family,
                    source_id=source_id,
                    cache_key=cache_key,
                )
            except SupabaseLocalModelCacheError as exc:
                logger.warning("Supabase cache smoke cleanup failed: %s", exc)

    def record_source_version(
        self,
        *,
        source_id: str,
        source_name: str,
        source_release: str | None,
        source_url: str | None = None,
        checksum_md5: str | None = None,
        checksum_sha256: str | None = None,
        license_status: str = "recorded",
        asset_role: str | None = None,
        asset_path: str | None = None,
        row_count: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        statement = text(f"""
            insert into {self.source_versions_table} (
                source_id,
                source_name,
                source_release,
                source_url,
                checksum_md5,
                checksum_sha256,
                license_status,
                asset_role,
                asset_path,
                row_count,
                metadata,
                updated_at
            )
            values (
                :source_id,
                :source_name,
                :source_release,
                :source_url,
                :checksum_md5,
                :checksum_sha256,
                :license_status,
                :asset_role,
                :asset_path,
                :row_count,
                cast(:metadata as jsonb),
                timezone('utc'::text, now())
            )
            on conflict (
                source_id,
                (coalesce(source_release, '')),
                (coalesce(checksum_sha256, ''))
            )
            do update set
                source_name = excluded.source_name,
                source_url = excluded.source_url,
                checksum_md5 = excluded.checksum_md5,
                license_status = excluded.license_status,
                asset_role = excluded.asset_role,
                asset_path = excluded.asset_path,
                row_count = excluded.row_count,
                metadata = excluded.metadata,
                updated_at = timezone('utc'::text, now())
            returning source_version_id
            """)
        try:
            with session_scope(self.session_factory) as session:
                source_version_id = session.execute(
                    statement,
                    {
                        "source_id": source_id,
                        "source_name": source_name,
                        "source_release": source_release,
                        "source_url": source_url,
                        "checksum_md5": checksum_md5,
                        "checksum_sha256": checksum_sha256,
                        "license_status": license_status,
                        "asset_role": asset_role,
                        "asset_path": asset_path,
                        "row_count": row_count,
                        "metadata": _json_param(metadata or {}),
                    },
                ).scalar_one()
        except Exception as exc:
            raise SupabaseLocalModelCacheError(
                _safe_error_message("Supabase source version write failed.", exc)
            ) from exc
        return str(source_version_id) if source_version_id is not None else None

    def upsert_clinical_source_records(
        self,
        *,
        mondo_rows: tuple[dict[str, Any], ...],
        hpo_term_rows: tuple[dict[str, Any], ...],
        hpo_disease_rows: tuple[dict[str, Any], ...],
        hpo_gene_rows: tuple[dict[str, Any], ...],
        clingen_rows: tuple[dict[str, Any], ...],
        gencc_rows: tuple[dict[str, Any], ...],
    ) -> dict[str, int]:
        try:
            with session_scope(self.session_factory) as session:
                _execute_many(
                    session,
                    text(f"""
                        insert into {self.clinical_mondo_table} (
                            source_version_id,
                            mondo_id,
                            name,
                            xrefs,
                            definition,
                            provenance,
                            raw_payload,
                            updated_at
                        )
                        values (
                            :source_version_id,
                            :mondo_id,
                            :name,
                            :xrefs,
                            :definition,
                            cast(:provenance as jsonb),
                            cast(:raw_payload as jsonb),
                            timezone('utc'::text, now())
                        )
                        on conflict (mondo_id)
                        do update set
                            source_version_id = excluded.source_version_id,
                            name = excluded.name,
                            xrefs = excluded.xrefs,
                            definition = excluded.definition,
                            provenance = excluded.provenance,
                            raw_payload = excluded.raw_payload,
                            updated_at = timezone('utc'::text, now())
                        """),
                    [
                        {
                            **row,
                            "xrefs": list(row.get("xrefs") or []),
                            "provenance": _json_param(row.get("provenance") or {}),
                            "raw_payload": _json_param(row.get("raw_payload")),
                        }
                        for row in mondo_rows
                    ],
                )
                _execute_many(
                    session,
                    text(f"""
                        insert into {self.clinical_hpo_terms_table} (
                            source_version_id,
                            hpo_id,
                            label,
                            provenance,
                            updated_at
                        )
                        values (
                            :source_version_id,
                            :hpo_id,
                            :label,
                            cast(:provenance as jsonb),
                            timezone('utc'::text, now())
                        )
                        on conflict (hpo_id)
                        do update set
                            source_version_id = excluded.source_version_id,
                            label = excluded.label,
                            provenance = excluded.provenance,
                            updated_at = timezone('utc'::text, now())
                        """),
                    [
                        {
                            **row,
                            "provenance": _json_param(row.get("provenance") or {}),
                        }
                        for row in hpo_term_rows
                    ],
                )
                _execute_many(
                    session,
                    text(f"""
                        insert into {self.clinical_hpo_disease_table} (
                            source_version_id,
                            disease_id,
                            disease_name,
                            hpo_id,
                            hpo_label,
                            evidence,
                            frequency,
                            provenance,
                            raw_payload,
                            updated_at
                        )
                        values (
                            :source_version_id,
                            :disease_id,
                            :disease_name,
                            :hpo_id,
                            :hpo_label,
                            :evidence,
                            :frequency,
                            cast(:provenance as jsonb),
                            cast(:raw_payload as jsonb),
                            timezone('utc'::text, now())
                        )
                        on conflict (disease_id, hpo_id)
                        do update set
                            source_version_id = excluded.source_version_id,
                            disease_name = excluded.disease_name,
                            hpo_label = excluded.hpo_label,
                            evidence = excluded.evidence,
                            frequency = excluded.frequency,
                            provenance = excluded.provenance,
                            raw_payload = excluded.raw_payload,
                            updated_at = timezone('utc'::text, now())
                        """),
                    [
                        {
                            **row,
                            "provenance": _json_param(row.get("provenance") or {}),
                            "raw_payload": _json_param(row.get("raw_payload")),
                        }
                        for row in hpo_disease_rows
                    ],
                )
                _execute_many(
                    session,
                    text(f"""
                        insert into {self.clinical_hpo_gene_table} (
                            source_version_id,
                            gene_symbol,
                            gene_id,
                            hpo_id,
                            hpo_label,
                            provenance,
                            raw_payload,
                            updated_at
                        )
                        values (
                            :source_version_id,
                            :gene_symbol,
                            :gene_id,
                            :hpo_id,
                            :hpo_label,
                            cast(:provenance as jsonb),
                            cast(:raw_payload as jsonb),
                            timezone('utc'::text, now())
                        )
                        on conflict (gene_symbol, hpo_id)
                        do update set
                            source_version_id = excluded.source_version_id,
                            gene_id = excluded.gene_id,
                            hpo_label = excluded.hpo_label,
                            provenance = excluded.provenance,
                            raw_payload = excluded.raw_payload,
                            updated_at = timezone('utc'::text, now())
                        """),
                    [
                        {
                            **row,
                            "provenance": _json_param(row.get("provenance") or {}),
                            "raw_payload": _json_param(row.get("raw_payload")),
                        }
                        for row in hpo_gene_rows
                    ],
                )
                _execute_many(
                    session,
                    text(f"""
                        insert into {self.clinical_clingen_table} (
                            source_version_id,
                            gene_symbol,
                            gene_hgnc_id,
                            disease_label,
                            disease_id,
                            mode_of_inheritance,
                            classification,
                            source_date,
                            report_url,
                            provenance,
                            raw_payload,
                            updated_at
                        )
                        values (
                            :source_version_id,
                            :gene_symbol,
                            :gene_hgnc_id,
                            :disease_label,
                            :disease_id,
                            :mode_of_inheritance,
                            :classification,
                            :source_date,
                            :report_url,
                            cast(:provenance as jsonb),
                            cast(:raw_payload as jsonb),
                            timezone('utc'::text, now())
                        )
                        on conflict (gene_symbol, disease_id, classification)
                        do update set
                            source_version_id = excluded.source_version_id,
                            gene_hgnc_id = excluded.gene_hgnc_id,
                            disease_label = excluded.disease_label,
                            mode_of_inheritance = excluded.mode_of_inheritance,
                            source_date = excluded.source_date,
                            report_url = excluded.report_url,
                            provenance = excluded.provenance,
                            raw_payload = excluded.raw_payload,
                            updated_at = timezone('utc'::text, now())
                        """),
                    [
                        {
                            **row,
                            "provenance": _json_param(row.get("provenance") or {}),
                            "raw_payload": _json_param(row.get("raw_payload")),
                        }
                        for row in clingen_rows
                    ],
                )
                _execute_many(
                    session,
                    text(f"""
                        insert into {self.clinical_gencc_table} (
                            source_version_id,
                            gene_symbol,
                            gene_curie,
                            disease_title,
                            disease_curie,
                            assertion,
                            submitter,
                            source_date,
                            report_url,
                            provenance,
                            raw_payload,
                            updated_at
                        )
                        values (
                            :source_version_id,
                            :gene_symbol,
                            :gene_curie,
                            :disease_title,
                            :disease_curie,
                            :assertion,
                            :submitter,
                            :source_date,
                            :report_url,
                            cast(:provenance as jsonb),
                            cast(:raw_payload as jsonb),
                            timezone('utc'::text, now())
                        )
                        on conflict (gene_symbol, disease_curie, submitter, assertion)
                        do update set
                            source_version_id = excluded.source_version_id,
                            gene_curie = excluded.gene_curie,
                            disease_title = excluded.disease_title,
                            source_date = excluded.source_date,
                            report_url = excluded.report_url,
                            provenance = excluded.provenance,
                            raw_payload = excluded.raw_payload,
                            updated_at = timezone('utc'::text, now())
                        """),
                    [
                        {
                            **row,
                            "provenance": _json_param(row.get("provenance") or {}),
                            "raw_payload": _json_param(row.get("raw_payload")),
                        }
                        for row in gencc_rows
                    ],
                )
        except Exception as exc:
            raise SupabaseLocalModelCacheError(
                _safe_error_message("Supabase clinical source import failed.", exc)
            ) from exc
        return {
            "clinical_mondo_diseases": len(mondo_rows),
            "clinical_hpo_terms": len(hpo_term_rows),
            "clinical_hpo_disease_phenotypes": len(hpo_disease_rows),
            "clinical_hpo_gene_phenotypes": len(hpo_gene_rows),
            "clinical_clingen_gene_validity": len(clingen_rows),
            "clinical_gencc_assertions": len(gencc_rows),
        }

    def get_gene_disease_summary(self, *, gene: str) -> dict[str, Any] | None:
        normalized_gene = gene.strip().upper()
        if not normalized_gene:
            return None
        clingen_statement = text(f"""
            select
                gene_symbol,
                gene_hgnc_id,
                disease_label,
                disease_id,
                mode_of_inheritance,
                classification,
                source_date,
                report_url,
                provenance
            from {self.clinical_clingen_table}
            where gene_symbol = :gene
            order by source_date desc nulls last, disease_label asc
            limit 50
            """)
        gencc_statement = text(f"""
            select
                gene_symbol,
                gene_curie,
                disease_title,
                disease_curie,
                assertion,
                submitter,
                source_date,
                report_url,
                provenance
            from {self.clinical_gencc_table}
            where gene_symbol = :gene
            order by source_date desc nulls last, disease_title asc
            limit 50
            """)
        mondo_statement = text(f"""
                select
                    mondo_id,
                    name,
                    xrefs,
                    definition,
                    provenance
                from {self.clinical_mondo_table}
                where mondo_id in :disease_ids
                order by name asc
                limit 50
                """).bindparams(bindparam("disease_ids", expanding=True))
        hpo_statement = text(f"""
                with gene_hpo as materialized (
                    select distinct
                        hpo_id,
                        gene_id
                    from {self.clinical_hpo_gene_table}
                    where gene_symbol = :gene
                ),
                disease_matches as materialized (
                    select
                        disease_id,
                        disease_name,
                        hpo_id,
                        hpo_label,
                        evidence,
                        frequency
                    from {self.clinical_hpo_disease_table}
                    where disease_id in :disease_ids
                )
                select distinct
                    d.disease_id,
                    d.disease_name,
                    d.hpo_id,
                    d.hpo_label,
                    d.evidence,
                    d.frequency,
                    g.gene_id
                from disease_matches d
                join gene_hpo g
                  on d.hpo_id = g.hpo_id
                order by d.disease_name asc, d.hpo_label asc
                limit 200
                """).bindparams(bindparam("disease_ids", expanding=True))

        try:
            with session_scope(self.session_factory) as session:
                session.execute(
                    text(
                        "set local statement_timeout = "
                        f"{CLINICAL_GENE_DISEASE_STATEMENT_TIMEOUT_MS}"
                    )
                )
                clingen_rows = [
                    dict(row)
                    for row in session.execute(
                        clingen_statement,
                        {"gene": normalized_gene},
                    )
                    .mappings()
                    .all()
                ]
                gencc_rows = [
                    dict(row)
                    for row in session.execute(
                        gencc_statement,
                        {"gene": normalized_gene},
                    )
                    .mappings()
                    .all()
                ]
                disease_ids = _clinical_disease_ids(
                    clingen_rows=clingen_rows,
                    gencc_rows=gencc_rows,
                )
                mondo_rows = (
                    [
                        dict(row)
                        for row in session.execute(
                            mondo_statement,
                            {"disease_ids": tuple(disease_ids)},
                        )
                        .mappings()
                        .all()
                    ]
                    if disease_ids
                    else []
                )
                expanded_disease_ids = _dedupe_text(
                    [
                        *disease_ids,
                        *(xref for row in mondo_rows for xref in _text_list(row.get("xrefs"))),
                    ]
                )
                hpo_rows = (
                    [
                        dict(row)
                        for row in session.execute(
                            hpo_statement,
                            {
                                "gene": normalized_gene,
                                "disease_ids": tuple(expanded_disease_ids),
                            },
                        )
                        .mappings()
                        .all()
                    ]
                    if expanded_disease_ids
                    else []
                )
        except Exception as exc:
            raise SupabaseLocalModelCacheError(
                _safe_error_message("Supabase clinical source read failed.", exc)
            ) from exc

        return _clinical_gene_disease_summary(
            gene=normalized_gene,
            clingen_rows=clingen_rows,
            gencc_rows=gencc_rows,
            mondo_rows=mondo_rows,
            hpo_rows=hpo_rows,
        )

    def upsert_source_asset_object(
        self,
        *,
        source_version_id: str | None,
        source_id: str,
        asset_role: str,
        bucket_id: str,
        object_path: str,
        object_version: str | None,
        content_type: str | None,
        byte_size: int | None,
        checksum_algorithm: str,
        checksum_value: str,
        upload_status: str,
        approval_status: str,
        license_status: str,
        materialization_required: bool,
        metadata: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
    ) -> str | None:
        statement = text(f"""
            insert into {self.source_asset_objects_table} (
                source_version_id,
                source_id,
                asset_role,
                bucket_id,
                object_path,
                object_version,
                content_type,
                byte_size,
                checksum_algorithm,
                checksum_value,
                upload_status,
                approval_status,
                license_status,
                public_access_allowed,
                frontend_direct_access_allowed,
                materialization_required,
                metadata,
                warnings,
                updated_at
            )
            values (
                :source_version_id,
                :source_id,
                :asset_role,
                :bucket_id,
                :object_path,
                :object_version,
                :content_type,
                :byte_size,
                :checksum_algorithm,
                :checksum_value,
                :upload_status,
                :approval_status,
                :license_status,
                false,
                false,
                :materialization_required,
                cast(:metadata as jsonb),
                cast(:warnings as jsonb),
                timezone('utc'::text, now())
            )
            on conflict (bucket_id, object_path)
            do update set
                source_version_id = excluded.source_version_id,
                source_id = excluded.source_id,
                asset_role = excluded.asset_role,
                object_version = excluded.object_version,
                content_type = excluded.content_type,
                byte_size = excluded.byte_size,
                checksum_algorithm = excluded.checksum_algorithm,
                checksum_value = excluded.checksum_value,
                upload_status = excluded.upload_status,
                approval_status = excluded.approval_status,
                license_status = excluded.license_status,
                public_access_allowed = false,
                frontend_direct_access_allowed = false,
                materialization_required = excluded.materialization_required,
                metadata = excluded.metadata,
                warnings = excluded.warnings,
                updated_at = timezone('utc'::text, now())
            returning source_asset_object_id
            """)
        try:
            with session_scope(self.session_factory) as session:
                source_asset_object_id = session.execute(
                    statement,
                    {
                        "source_version_id": source_version_id,
                        "source_id": source_id,
                        "asset_role": asset_role,
                        "bucket_id": bucket_id,
                        "object_path": object_path,
                        "object_version": object_version,
                        "content_type": content_type,
                        "byte_size": byte_size,
                        "checksum_algorithm": checksum_algorithm,
                        "checksum_value": checksum_value,
                        "upload_status": upload_status,
                        "approval_status": approval_status,
                        "license_status": license_status,
                        "materialization_required": materialization_required,
                        "metadata": _json_param(metadata or {}),
                        "warnings": _json_param(warnings or []),
                    },
                ).scalar_one()
        except Exception as exc:
            raise SupabaseLocalModelCacheError(
                _safe_error_message("Supabase source asset object write failed.", exc)
            ) from exc
        return str(source_asset_object_id) if source_asset_object_id is not None else None

    def upsert_source_asset_materialization(
        self,
        *,
        source_asset_object_id: str | None,
        environment: str,
        backend_runtime: str,
        local_cache_path: str,
        materialization_status: str,
        byte_size: int | None,
        checksum_algorithm: str | None,
        checksum_value: str | None,
        ready_marker: str | None,
        verified_at: str | None,
        fail_closed_reason: str | None,
        metadata: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
    ) -> None:
        if source_asset_object_id is None:
            raise SupabaseLocalModelCacheError(
                "Supabase source asset materialization write failed. "
                "source_asset_object_id is required."
            )
        statement = text(f"""
            insert into {self.source_asset_materializations_table} (
                source_asset_object_id,
                environment,
                backend_runtime,
                local_cache_path,
                materialization_status,
                byte_size,
                checksum_algorithm,
                checksum_value,
                ready_marker,
                verified_at,
                last_attempt_at,
                fail_closed_reason,
                stale_allowed,
                metadata,
                warnings,
                updated_at
            )
            values (
                :source_asset_object_id,
                :environment,
                :backend_runtime,
                :local_cache_path,
                :materialization_status,
                :byte_size,
                :checksum_algorithm,
                :checksum_value,
                :ready_marker,
                :verified_at,
                timezone('utc'::text, now()),
                :fail_closed_reason,
                false,
                cast(:metadata as jsonb),
                cast(:warnings as jsonb),
                timezone('utc'::text, now())
            )
            on conflict (source_asset_object_id, environment, local_cache_path)
            do update set
                backend_runtime = excluded.backend_runtime,
                materialization_status = excluded.materialization_status,
                byte_size = excluded.byte_size,
                checksum_algorithm = excluded.checksum_algorithm,
                checksum_value = excluded.checksum_value,
                ready_marker = excluded.ready_marker,
                verified_at = excluded.verified_at,
                last_attempt_at = timezone('utc'::text, now()),
                fail_closed_reason = excluded.fail_closed_reason,
                stale_allowed = false,
                metadata = excluded.metadata,
                warnings = excluded.warnings,
                updated_at = timezone('utc'::text, now())
            """)
        try:
            with session_scope(self.session_factory) as session:
                session.execute(
                    statement,
                    {
                        "source_asset_object_id": source_asset_object_id,
                        "environment": environment,
                        "backend_runtime": backend_runtime,
                        "local_cache_path": local_cache_path,
                        "materialization_status": materialization_status,
                        "byte_size": byte_size,
                        "checksum_algorithm": checksum_algorithm,
                        "checksum_value": checksum_value,
                        "ready_marker": ready_marker,
                        "verified_at": verified_at,
                        "fail_closed_reason": fail_closed_reason,
                        "metadata": _json_param(metadata or {}),
                        "warnings": _json_param(warnings or []),
                    },
                )
        except Exception as exc:
            raise SupabaseLocalModelCacheError(
                _safe_error_message("Supabase source asset materialization write failed.", exc)
            ) from exc

    def get_source_asset_materialization(
        self,
        *,
        source_id: str,
        asset_role: str,
        bucket_id: str | None = None,
        object_path: str | None = None,
        environment: str | None = None,
        local_cache_path: str | None = None,
    ) -> SourceAssetMaterializationRecord | None:
        statement = self._source_asset_materialization_select_statement()
        try:
            with session_scope(self.session_factory) as session:
                row = (
                    session.execute(
                        statement,
                        {
                            "source_id": source_id,
                            "asset_role": asset_role,
                            "bucket_id": bucket_id,
                            "object_path": object_path,
                            "environment": environment,
                            "local_cache_path": local_cache_path,
                        },
                    )
                    .mappings()
                    .one_or_none()
                )
        except Exception as exc:
            _log_source_asset_materialization_read_fallback(
                source_id=source_id,
                asset_role=asset_role,
                error=exc,
            )
            return None
        if row is None:
            return None
        return SourceAssetMaterializationRecord(
            source_id=str(row["source_id"]),
            asset_role=str(row["asset_role"]),
            bucket_id=str(row["bucket_id"]),
            object_path=str(row["object_path"]),
            upload_status=str(row["upload_status"]),
            approval_status=str(row["approval_status"]),
            public_access_allowed=bool(row["public_access_allowed"]),
            frontend_direct_access_allowed=bool(row["frontend_direct_access_allowed"]),
            environment=str(row["environment"]),
            backend_runtime=str(row["backend_runtime"]),
            local_cache_path=str(row["local_cache_path"]),
            materialization_status=str(row["materialization_status"]),
            byte_size=int(row["byte_size"]) if row["byte_size"] is not None else None,
            checksum_algorithm=row["checksum_algorithm"],
            checksum_value=row["checksum_value"],
            verified_at=_aware_or_none(row["verified_at"]),
            fail_closed_reason=row["fail_closed_reason"],
            metadata=dict(row["metadata"] or {}),
            warnings=list(row["warnings"] or []),
        )

    def _source_asset_materialization_select_statement(self):
        return text(f"""
            select
                o.source_id,
                o.asset_role,
                o.bucket_id,
                o.object_path,
                o.upload_status,
                o.approval_status,
                o.public_access_allowed,
                o.frontend_direct_access_allowed,
                m.environment,
                m.backend_runtime,
                m.local_cache_path,
                m.materialization_status,
                m.byte_size,
                m.checksum_algorithm,
                m.checksum_value,
                m.verified_at,
                m.fail_closed_reason,
                m.metadata,
                m.warnings
            from {self.source_asset_objects_table} as o
            join {self.source_asset_materializations_table} as m
              on m.source_asset_object_id = o.source_asset_object_id
            where o.source_id = :source_id
              and o.asset_role = :asset_role
              and (cast(:bucket_id as text) is null or o.bucket_id = cast(:bucket_id as text))
              and (
                cast(:object_path as text) is null
                or o.object_path = cast(:object_path as text)
              )
              and (
                cast(:environment as text) is null
                or m.environment = cast(:environment as text)
              )
              and (
                cast(:local_cache_path as text) is null
                or m.local_cache_path = cast(:local_cache_path as text)
              )
            order by
                case when m.materialization_status = 'ready' then 0 else 1 end,
                m.updated_at desc
            limit 1
            """)

    def record_job(
        self,
        *,
        job_type: str,
        cache_family: str,
        status: str,
        cache_key: str | None = None,
        fail_closed_reason: str | None = None,
        input_payload: dict[str, Any] | None = None,
        provenance: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        statement = text(f"""
            insert into {self.jobs_table} (
                job_type,
                cache_family,
                cache_key,
                status,
                fail_closed_reason,
                input_payload,
                provenance,
                warnings,
                completed_at,
                updated_at
            )
            values (
                :job_type,
                :cache_family,
                :cache_key,
                :status,
                :fail_closed_reason,
                cast(:input_payload as jsonb),
                cast(:provenance as jsonb),
                cast(:warnings as jsonb),
                :completed_at,
                timezone('utc'::text, now())
            )
            """)
        try:
            with session_scope(self.session_factory) as session:
                session.execute(
                    statement,
                    {
                        "job_type": job_type,
                        "cache_family": cache_family,
                        "cache_key": cache_key,
                        "status": status,
                        "fail_closed_reason": fail_closed_reason,
                        "input_payload": _json_param(input_payload or {}),
                        "provenance": _json_param(provenance or {}),
                        "warnings": _json_param(warnings or []),
                        "completed_at": completed_at,
                    },
                )
        except Exception as exc:
            raise SupabaseLocalModelCacheError(
                _safe_error_message("Supabase local model job write failed.", exc)
            ) from exc


class SupabaseVariantCacheRepo:
    cache_family = "variant_report"
    source_id = "variant_cache"

    def __init__(self, store) -> None:
        self.store = store

    def get_fresh(self, query_string: str, ttl_days: int) -> dict[str, Any] | None:
        entry = self.store.get_entry(
            cache_family=self.cache_family,
            source_id=self.source_id,
            cache_key=query_string,
        )
        if entry is None:
            return None
        created_at = entry.fetched_at or entry.created_at or _now()
        cutoff = _now() - timedelta(days=ttl_days)
        if _as_aware(created_at) < cutoff:
            return None
        return {
            "query_string": query_string,
            "litvar_id": entry.payload.get("litvar_id"),
            "total_publications": entry.payload.get("total_publications"),
            "publication_data": dict(entry.payload.get("publication_data") or {}),
            "strict_genomic_cache": dict(entry.payload.get("strict_genomic_cache") or {}),
            "gene_context_snapshot": dict(entry.payload.get("gene_context_snapshot") or {}),
            "created_at": created_at,
        }

    def upsert(
        self,
        query_string: str,
        *,
        litvar_id: str | None,
        total_publications: int | None,
        publication_data: dict[str, Any],
        strict_genomic_cache: dict[str, Any],
        gene_context_snapshot: dict[str, Any] | None = None,
    ) -> None:
        self.store.upsert_entry(
            LocalModelCacheEntry(
                cache_family=self.cache_family,
                source_id=self.source_id,
                cache_key=query_string,
                normalized_identity={"query_string": query_string},
                request_identity={"query_string": query_string},
                status="stored",
                payload={
                    "litvar_id": litvar_id,
                    "total_publications": total_publications,
                    "publication_data": publication_data,
                    "strict_genomic_cache": strict_genomic_cache,
                    "gene_context_snapshot": gene_context_snapshot or {},
                },
                provenance={"repo": "SupabaseVariantCacheRepo"},
                fetched_at=_now(),
            )
        )

    def update_gene_context_snapshot(
        self,
        query_string: str,
        *,
        gene_context_snapshot: dict[str, Any],
    ) -> None:
        entry = self.store.get_entry(
            cache_family=self.cache_family,
            source_id=self.source_id,
            cache_key=query_string,
        )
        if entry is None:
            return
        payload = dict(entry.payload)
        payload["gene_context_snapshot"] = gene_context_snapshot
        self.store.upsert_entry(
            LocalModelCacheEntry(
                cache_family=self.cache_family,
                source_id=self.source_id,
                cache_key=query_string,
                normalized_identity=dict(entry.normalized_identity),
                request_identity=dict(entry.request_identity),
                status=entry.status,
                payload=payload,
                raw_payload=entry.raw_payload,
                provenance=dict(entry.provenance),
                warnings=list(entry.warnings),
                source_url=entry.source_url,
                source_release=entry.source_release,
                source_checksum_sha256=entry.source_checksum_sha256,
                fetched_at=entry.fetched_at or _now(),
                expires_at=entry.expires_at,
                created_at=entry.created_at,
                updated_at=_now(),
            )
        )

    def update_report_shell(
        self,
        query_string: str,
        *,
        report_shell: dict[str, Any],
    ) -> None:
        entry = self.store.get_entry(
            cache_family=self.cache_family,
            source_id=self.source_id,
            cache_key=query_string,
        )
        if entry is None:
            return
        payload = dict(entry.payload)
        publication_data = dict(payload.get("publication_data") or {})
        publication_data["report_shell"] = report_shell
        payload["publication_data"] = publication_data
        self.store.upsert_entry(
            LocalModelCacheEntry(
                cache_family=self.cache_family,
                source_id=self.source_id,
                cache_key=query_string,
                normalized_identity=dict(entry.normalized_identity),
                request_identity=dict(entry.request_identity),
                status=entry.status,
                payload=payload,
                raw_payload=entry.raw_payload,
                provenance=dict(entry.provenance),
                warnings=list(entry.warnings),
                source_url=entry.source_url,
                source_release=entry.source_release,
                source_checksum_sha256=entry.source_checksum_sha256,
                fetched_at=entry.fetched_at or _now(),
                expires_at=entry.expires_at,
                created_at=entry.created_at,
                updated_at=_now(),
            )
        )

    def update_report_sections(
        self,
        query_string: str,
        *,
        report_sections: dict[str, Any],
    ) -> None:
        entry = self.store.get_entry(
            cache_family=self.cache_family,
            source_id=self.source_id,
            cache_key=query_string,
        )
        if entry is None:
            return
        payload = dict(entry.payload)
        publication_data = dict(payload.get("publication_data") or {})
        publication_data["report_sections"] = report_sections
        payload["publication_data"] = publication_data
        self.store.upsert_entry(
            LocalModelCacheEntry(
                cache_family=self.cache_family,
                source_id=self.source_id,
                cache_key=query_string,
                normalized_identity=dict(entry.normalized_identity),
                request_identity=dict(entry.request_identity),
                status=entry.status,
                payload=payload,
                raw_payload=entry.raw_payload,
                provenance=dict(entry.provenance),
                warnings=list(entry.warnings),
                source_url=entry.source_url,
                source_release=entry.source_release,
                source_checksum_sha256=entry.source_checksum_sha256,
                fetched_at=entry.fetched_at or _now(),
                expires_at=entry.expires_at,
                created_at=entry.created_at,
                updated_at=_now(),
            )
        )


class SupabaseSourceCacheRepo:
    cache_family = "source_cache"

    def __init__(self, store) -> None:
        self.store = store

    def get_fresh(self, source: str, cache_key: str) -> SourceCachePayload | None:
        payload = self.get_any(source, cache_key)
        if payload is None or payload.expires_at is None or _as_aware(payload.expires_at) <= _now():
            return None
        return payload

    def get_stale(self, source: str, cache_key: str) -> SourceCachePayload | None:
        payload = self.get_any(source, cache_key)
        if payload is None:
            return None
        if payload.expires_at is not None and _as_aware(payload.expires_at) > _now():
            return None
        return payload

    def get_any(self, source: str, cache_key: str) -> SourceCachePayload | None:
        entry = self.store.get_entry(
            cache_family=self.cache_family,
            source_id=source,
            cache_key=cache_key,
        )
        if entry is None:
            return None
        return SourceCachePayload(
            source=source,
            cache_key=cache_key,
            normalized_identity=dict(entry.normalized_identity),
            request_identity=dict(entry.request_identity),
            status=entry.status,
            source_version=entry.source_release,
            summary=dict(entry.payload),
            raw=entry.raw_payload,
            warnings=list(entry.warnings),
            source_url=entry.source_url,
            fetched_at=entry.fetched_at,
            expires_at=entry.expires_at,
        )

    def upsert(
        self,
        source: str,
        cache_key: str,
        *,
        normalized_identity: dict[str, Any],
        request_identity: dict[str, Any],
        status: str,
        summary: dict[str, Any],
        raw: Any,
        warnings: list[str],
        source_url: str | None,
        ttl_days: int,
        source_version: str | None = None,
    ) -> None:
        self.store.upsert_entry(
            LocalModelCacheEntry(
                cache_family=self.cache_family,
                source_id=source,
                cache_key=cache_key,
                normalized_identity=dict(normalized_identity),
                request_identity=dict(request_identity),
                status=status,
                payload=dict(summary),
                raw_payload=raw,
                provenance={"repo": "SupabaseSourceCacheRepo"},
                warnings=list(warnings),
                source_url=source_url,
                source_release=source_version,
                fetched_at=_now(),
                expires_at=_now() + timedelta(days=ttl_days),
            )
        )

    def health_summary(self) -> dict[str, Any]:
        return {"remote_supabase_cache": "enabled"}


class SupabaseProteinAnnotationCacheRepo:
    cache_family = "protein_annotation"
    source_id = "eamos_protein_annotation_super_tool"

    def __init__(self, store) -> None:
        self.store = store

    def get(
        self,
        *,
        sequence_hash: str,
        pfam_release: str,
        hmmer_release: str,
        uniprot_release: str | None = None,
    ) -> ProteinDomainTrack | None:
        entry = self.store.get_entry(
            cache_family=self.cache_family,
            source_id=self.source_id,
            cache_key=_protein_annotation_cache_key(
                sequence_hash=sequence_hash,
                pfam_release=pfam_release,
                hmmer_release=hmmer_release,
                uniprot_release=uniprot_release,
            ),
        )
        if entry is None:
            return None
        return ProteinDomainTrack.model_validate(entry.payload)

    def upsert(self, track: ProteinDomainTrack) -> None:
        if (
            not track.protein_sequence_hash
            or not track.pfam_release
            or not track.hmmer_release
            or not track.cache_key
            or track.protein_length is None
        ):
            raise ValueError("protein annotation cache track is missing key fields")
        for item in track.provenance:
            self.store.record_source_version(
                source_id=item.source_id,
                source_name=item.source_name,
                source_release=item.source_release,
                source_url=item.source_url,
                checksum_md5=item.checksum_md5,
                checksum_sha256=item.checksum_sha256,
                license_status=item.license_status,
                metadata={"cache_family": self.cache_family},
            )
        self.store.upsert_entry(
            LocalModelCacheEntry(
                cache_family=self.cache_family,
                source_id=self.source_id,
                cache_key=track.cache_key,
                normalized_identity={
                    "sequence_hash": track.protein_sequence_hash,
                    "sequence_hash_algorithm": "sha256",
                    "protein_length": track.protein_length,
                    "gene_symbol": track.gene_symbol,
                    "transcript": track.transcript,
                    "protein_accession": track.protein_accession,
                },
                request_identity={
                    "sequence_label": track.sequence_label,
                    "gene_symbol": track.gene_symbol,
                    "transcript": track.transcript,
                    "protein_accession": track.protein_accession,
                },
                status=track.status,
                payload=track.model_dump(mode="json"),
                provenance={"sources": [item.model_dump(mode="json") for item in track.provenance]},
                warnings=list(track.warnings),
                source_release="; ".join(
                    item
                    for item in (track.pfam_release, track.hmmer_release, track.uniprot_release)
                    if item
                )
                or None,
                fetched_at=_now(),
            )
        )
        self.store.record_job(
            job_type="protein_annotation_cache_store",
            cache_family=self.cache_family,
            cache_key=track.cache_key,
            status=track.status,
            fail_closed_reason=track.fail_closed_reason,
            input_payload={
                "sequence_hash": track.protein_sequence_hash,
                "gene_symbol": track.gene_symbol,
                "transcript": track.transcript,
                "protein_accession": track.protein_accession,
            },
            provenance={"cache_key": track.cache_key},
            warnings=list(track.warnings),
            completed_at=_now(),
        )


class HybridVariantCacheRepo:
    def __init__(self, *, local_repo, remote_repo) -> None:
        self.local_repo = local_repo
        self.remote_repo = remote_repo

    def get_fresh(self, query_string: str, ttl_days: int) -> dict[str, Any] | None:
        hit = self.local_repo.get_fresh(query_string, ttl_days)
        if hit is not None:
            return hit
        try:
            return self.remote_repo.get_fresh(query_string, ttl_days)
        except SupabaseLocalModelCacheError as exc:
            _log_remote_cache_fallback(
                operation="read",
                cache_family="variant_report",
                source_id="variant_cache",
                error=exc,
            )
            return None

    def upsert(self, query_string: str, **kwargs) -> None:
        self.local_repo.upsert(query_string, **kwargs)
        try:
            self.remote_repo.upsert(query_string, **kwargs)
        except SupabaseLocalModelCacheError as exc:
            _log_remote_cache_fallback(
                operation="write",
                cache_family="variant_report",
                source_id="variant_cache",
                error=exc,
            )
            return

    def update_gene_context_snapshot(
        self,
        query_string: str,
        *,
        gene_context_snapshot: dict[str, Any],
    ) -> None:
        self.local_repo.update_gene_context_snapshot(
            query_string,
            gene_context_snapshot=gene_context_snapshot,
        )
        try:
            self.remote_repo.update_gene_context_snapshot(
                query_string,
                gene_context_snapshot=gene_context_snapshot,
            )
        except SupabaseLocalModelCacheError as exc:
            _log_remote_cache_fallback(
                operation="write",
                cache_family="variant_report",
                source_id="variant_cache",
                error=exc,
            )
            return

    def update_report_shell(
        self,
        query_string: str,
        *,
        report_shell: dict[str, Any],
    ) -> None:
        self.local_repo.update_report_shell(
            query_string,
            report_shell=report_shell,
        )
        try:
            self.remote_repo.update_report_shell(
                query_string,
                report_shell=report_shell,
            )
        except SupabaseLocalModelCacheError as exc:
            _log_remote_cache_fallback(
                operation="write",
                cache_family="variant_report",
                source_id="variant_cache",
                error=exc,
            )
            return

    def update_report_sections(
        self,
        query_string: str,
        *,
        report_sections: dict[str, Any],
    ) -> None:
        self.local_repo.update_report_sections(
            query_string,
            report_sections=report_sections,
        )
        try:
            self.remote_repo.update_report_sections(
                query_string,
                report_sections=report_sections,
            )
        except SupabaseLocalModelCacheError as exc:
            _log_remote_cache_fallback(
                operation="write",
                cache_family="variant_report",
                source_id="variant_cache",
                error=exc,
            )
            return


class HybridSourceCacheRepo:
    def __init__(self, *, local_repo, remote_repo) -> None:
        self.local_repo = local_repo
        self.remote_repo = remote_repo

    def get_fresh(self, source: str, cache_key: str) -> SourceCachePayload | None:
        hit = self.local_repo.get_fresh(source, cache_key)
        if hit is not None:
            return hit
        try:
            return self.remote_repo.get_fresh(source, cache_key)
        except SupabaseLocalModelCacheError as exc:
            _log_remote_cache_fallback(
                operation="read",
                cache_family="source_cache",
                source_id=source,
                error=exc,
            )
            return None

    def get_stale(self, source: str, cache_key: str) -> SourceCachePayload | None:
        hit = self.local_repo.get_stale(source, cache_key)
        if hit is not None:
            return hit
        try:
            return self.remote_repo.get_stale(source, cache_key)
        except SupabaseLocalModelCacheError as exc:
            _log_remote_cache_fallback(
                operation="stale_read",
                cache_family="source_cache",
                source_id=source,
                error=exc,
            )
            return None

    def get_any(self, source: str, cache_key: str) -> SourceCachePayload | None:
        hit = self.local_repo.get_any(source, cache_key)
        if hit is not None:
            return hit
        try:
            return self.remote_repo.get_any(source, cache_key)
        except SupabaseLocalModelCacheError as exc:
            _log_remote_cache_fallback(
                operation="read_any",
                cache_family="source_cache",
                source_id=source,
                error=exc,
            )
            return None

    def upsert(self, source: str, cache_key: str, **kwargs) -> None:
        self.local_repo.upsert(source, cache_key, **kwargs)
        try:
            self.remote_repo.upsert(source, cache_key, **kwargs)
        except SupabaseLocalModelCacheError as exc:
            _log_remote_cache_fallback(
                operation="write",
                cache_family="source_cache",
                source_id=source,
                error=exc,
            )
            return

    def health_summary(self) -> dict[str, Any]:
        summary = self.local_repo.health_summary()
        summary["remote_supabase_cache"] = {"enabled": True, "mode": "fallback"}
        return summary


class HybridProteinAnnotationCacheRepo:
    def __init__(self, *, local_repo, remote_repo) -> None:
        self.local_repo = local_repo
        self.remote_repo = remote_repo

    def get(
        self,
        *,
        sequence_hash: str,
        pfam_release: str,
        hmmer_release: str,
        uniprot_release: str | None = None,
    ) -> ProteinDomainTrack | None:
        hit = self.local_repo.get(
            sequence_hash=sequence_hash,
            pfam_release=pfam_release,
            hmmer_release=hmmer_release,
            uniprot_release=uniprot_release,
        )
        if hit is not None:
            return hit
        try:
            return self.remote_repo.get(
                sequence_hash=sequence_hash,
                pfam_release=pfam_release,
                hmmer_release=hmmer_release,
                uniprot_release=uniprot_release,
            )
        except SupabaseLocalModelCacheError as exc:
            _log_remote_cache_fallback(
                operation="read",
                cache_family="protein_annotation",
                source_id="eamos_protein_annotation_super_tool",
                error=exc,
            )
            return None

    def upsert(self, track: ProteinDomainTrack) -> None:
        self.local_repo.upsert(track)
        try:
            self.remote_repo.upsert(track)
        except SupabaseLocalModelCacheError as exc:
            _log_remote_cache_fallback(
                operation="write",
                cache_family="protein_annotation",
                source_id="eamos_protein_annotation_super_tool",
                error=exc,
            )
            return


def build_supabase_local_model_cache_store(settings):
    if not settings.supabase_local_model_cache_enabled:
        return None
    if not settings.supabase_local_model_cache_database_url:
        return None
    return SqlAlchemySupabaseLocalModelCacheStore(
        build_session_factory(settings.supabase_local_model_cache_database_url),
        schema=settings.supabase_local_model_cache_schema,
    )


def _clinical_disease_ids(
    *,
    clingen_rows: list[dict[str, Any]],
    gencc_rows: list[dict[str, Any]],
) -> list[str]:
    return _dedupe_text(
        [
            *(_row_text(row, "disease_id") for row in clingen_rows),
            *(_row_text(row, "disease_curie") for row in gencc_rows),
        ]
    )


def _clinical_gene_disease_summary(
    *,
    gene: str,
    clingen_rows: list[dict[str, Any]],
    gencc_rows: list[dict[str, Any]],
    mondo_rows: list[dict[str, Any]],
    hpo_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not clingen_rows and not gencc_rows and not mondo_rows and not hpo_rows:
        return None

    mondo_by_id = {
        mondo_id: row for row in mondo_rows if (mondo_id := _row_text(row, "mondo_id")) is not None
    }
    conditions_by_key: dict[str, dict[str, Any]] = {}

    def condition_for(disease_id: str | None, name: str | None) -> dict[str, Any]:
        key = disease_id or name or "unspecified"
        condition = conditions_by_key.get(key)
        if condition is not None:
            return condition
        mondo = mondo_by_id.get(disease_id or "")
        disease_ids = _dedupe_text(
            [
                disease_id,
                *(_text_list(mondo.get("xrefs")) if mondo is not None else []),
            ]
        )
        condition = {
            "name": name or _row_text(mondo or {}, "name") or "",
            "disease_ids": disease_ids,
            "inheritance": None,
            "validity": None,
            "mechanism": None,
            "source_urls": [],
            "phenotypes": [],
        }
        conditions_by_key[key] = condition
        return condition

    for row in clingen_rows:
        disease_id = _row_text(row, "disease_id")
        condition = condition_for(disease_id, _row_text(row, "disease_label"))
        condition["inheritance"] = condition["inheritance"] or _row_text(
            row,
            "mode_of_inheritance",
        )
        condition["validity"] = condition["validity"] or _row_text(row, "classification")
        _append_unique(condition["source_urls"], _row_text(row, "report_url"))

    for row in gencc_rows:
        disease_id = _row_text(row, "disease_curie")
        condition = condition_for(disease_id, _row_text(row, "disease_title"))
        condition["validity"] = condition["validity"] or _row_text(row, "assertion")
        _append_unique(condition["source_urls"], _row_text(row, "report_url"))

    for row in hpo_rows:
        disease_id = _row_text(row, "disease_id")
        condition = _condition_matching_disease_id(conditions_by_key.values(), disease_id)
        if condition is None:
            condition = condition_for(disease_id, _row_text(row, "disease_name"))
        phenotype = {
            "hpo_id": _row_text(row, "hpo_id"),
            "label": _row_text(row, "hpo_label"),
            "evidence": _row_text(row, "evidence"),
            "frequency": _row_text(row, "frequency"),
        }
        if phenotype["hpo_id"] and phenotype not in condition["phenotypes"]:
            condition["phenotypes"].append(phenotype)

    conditions = sorted(
        conditions_by_key.values(),
        key=_gene_disease_condition_sort_key,
    )
    for condition in conditions:
        condition["disease_ids"] = _dedupe_text(condition["disease_ids"])
        condition["source_urls"] = _dedupe_text(condition["source_urls"])
        condition["phenotypes"] = sorted(
            condition["phenotypes"],
            key=lambda item: (item.get("label") or "", item.get("hpo_id") or ""),
        )

    primary = conditions[0] if conditions else {}
    hgnc_id = next(
        (
            value
            for value in (
                *(_row_text(row, "gene_hgnc_id") for row in clingen_rows),
                *(_row_text(row, "gene_curie") for row in gencc_rows),
            )
            if value
        ),
        None,
    )
    gencc_submitters = _dedupe_text(_row_text(row, "submitter") for row in gencc_rows)
    gencc_assertions = _dedupe_text(_row_text(row, "assertion") for row in gencc_rows)
    warnings = ["private_clinical_source_tables", "penetrance_not_source_backed"]
    if not primary.get("mechanism"):
        warnings.append("mechanism_not_source_backed")

    return {
        "gene": gene,
        "approved_symbol": gene,
        "hgnc_id": hgnc_id,
        "gene_name": None,
        "primary_condition": primary.get("name"),
        "disease_ids": _dedupe_text(
            disease_id for condition in conditions for disease_id in condition["disease_ids"]
        ),
        "inheritance": primary.get("inheritance"),
        "penetrance": None,
        "gene_disease_validity": primary.get("validity"),
        "mechanism": primary.get("mechanism"),
        "conditions": conditions,
        "source_counts": {
            "clingen_gene_validity": len(clingen_rows),
            "gencc_assertions": len(gencc_rows),
            "mondo_disease_terms": len(mondo_rows),
            "hpo_annotations": len(hpo_rows),
        },
        "gencc_assertion_count": len(gencc_rows),
        "gencc_submitters": gencc_submitters[:12],
        "gencc_assertions": gencc_assertions[:12],
        "provenance": _clinical_gene_disease_provenance(
            gene=gene,
            clingen_rows=clingen_rows,
            gencc_rows=gencc_rows,
            mondo_rows=mondo_rows,
            hpo_rows=hpo_rows,
        ),
        "warnings": warnings,
    }


_GENE_DISEASE_VALIDITY_RANK = {
    "definitive": 0,
    "strong": 1,
    "moderate": 2,
    "limited": 3,
    "supportive": 4,
    "disputed evidence": 5,
    "disputed": 5,
    "refuted evidence": 6,
    "refuted": 6,
    "no known disease relationship": 7,
}


def _gene_disease_condition_sort_key(condition: dict[str, Any]) -> tuple[int, str]:
    validity = (_row_text(condition, "validity") or "").casefold()
    rank = _GENE_DISEASE_VALIDITY_RANK.get(validity, 8)
    name = (_row_text(condition, "name") or "").casefold()
    return rank, name


def _clinical_gene_disease_provenance(
    *,
    gene: str,
    clingen_rows: list[dict[str, Any]],
    gencc_rows: list[dict[str, Any]],
    mondo_rows: list[dict[str, Any]],
    hpo_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    provenance: list[dict[str, Any]] = []
    if clingen_rows:
        provenance.append(
            {
                "source": "ClinGen Gene-Disease Validity",
                "status": "source_table",
                "query": {"gene": gene},
                "source_url": _first_row_text(clingen_rows, "report_url"),
                "version": "private_clinical_source_table",
                "warnings": [],
            }
        )
    if gencc_rows:
        provenance.append(
            {
                "source": "GenCC",
                "status": "source_table",
                "query": {"gene": gene},
                "source_url": _first_row_text(gencc_rows, "report_url"),
                "version": "private_clinical_source_table",
                "warnings": [],
            }
        )
    if mondo_rows:
        provenance.append(
            {
                "source": "MONDO",
                "status": "source_table",
                "query": {
                    "disease_ids": _dedupe_text(_row_text(row, "mondo_id") for row in mondo_rows)
                },
                "source_url": None,
                "version": "private_clinical_source_table",
                "warnings": [],
            }
        )
    if hpo_rows:
        provenance.append(
            {
                "source": "Human Phenotype Ontology",
                "status": "source_table",
                "query": {"gene": gene},
                "source_url": None,
                "version": "private_clinical_source_table",
                "warnings": [],
            }
        )
    return provenance


def _condition_matching_disease_id(
    conditions: Iterable[dict[str, Any]],
    disease_id: str | None,
) -> dict[str, Any] | None:
    if not disease_id:
        return None
    for condition in conditions:
        if disease_id in _text_list(condition.get("disease_ids")):
            return condition
    return None


def _append_unique(values: list[str], value: str | None) -> None:
    if value and value not in values:
        values.append(value)


def _first_row_text(rows: list[dict[str, Any]], key: str) -> str | None:
    return next((_row_text(row, key) for row in rows if _row_text(row, key)), None)


def _row_text(row: dict[str, Any], key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    text_value = str(value).strip()
    return text_value or None


def _text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text_value = value.strip()
        if text_value.startswith("["):
            try:
                decoded = json.loads(text_value)
            except ValueError:
                return [text_value] if text_value else []
            return _text_list(decoded)
        return [text_value] if text_value else []
    if isinstance(value, Iterable):
        return [text for item in value if (text := _row_scalar_text(item))]
    return [text] if (text := _row_scalar_text(value)) else []


def _row_scalar_text(value: Any) -> str | None:
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def _dedupe_text(items: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text_value = (item or "").strip()
        if not text_value or text_value in seen:
            continue
        seen.add(text_value)
        result.append(text_value)
    return result


def _protein_annotation_cache_key(
    *,
    sequence_hash: str,
    pfam_release: str,
    hmmer_release: str,
    uniprot_release: str | None,
) -> str:
    key = f"protein_annotation:sha256:{sequence_hash}:pfam:{pfam_release}:hmmer:{hmmer_release}"
    if uniprot_release:
        key = f"{key}:uniprot:{uniprot_release}"
    return key


def _execute_many(session, statement, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    session.execute(statement, rows)


def _json_param(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _aware_or_none(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    return _as_aware(value)


def _safe_error_message(prefix: str, exc: Exception) -> str:
    original = getattr(exc, "orig", None)
    if original is not None:
        detail = f"{type(original).__name__}: {_redact_secret_text(str(original))}"
    else:
        first_line = str(exc).splitlines()[0] if str(exc) else ""
        detail = f"{type(exc).__name__}: {_redact_secret_text(first_line)}"
    return f"{prefix} {detail}".strip()


def _safe_exception_type(exc: Exception) -> str:
    original = getattr(exc, "orig", None)
    return type(original or exc).__name__


def _redact_secret_text(value: str) -> str:
    value = re.sub(r"(?i)(password=)[^\\s&]+", r"\1<redacted>", value)
    return re.sub(
        r"(postgres(?:ql)?(?:\\+psycopg)?://[^:\\s/@]+:)[^@\\s]+(@)",
        r"\1<redacted>\2",
        value,
    )


def _log_remote_cache_fallback(
    *,
    operation: str,
    cache_family: str,
    source_id: str,
    error: SupabaseLocalModelCacheError,
) -> None:
    logger.warning(
        "Supabase local model cache %s failed; using local fallback "
        "(cache_family=%s, source_id=%s): %s",
        operation,
        cache_family,
        source_id,
        error,
    )


def _log_source_asset_materialization_read_fallback(
    *,
    source_id: str,
    asset_role: str,
    error: Exception,
) -> None:
    logger.warning(
        "Supabase source asset materialization read failed; treating metadata "
        "as unavailable (source_id=%s, asset_role=%s, error_type=%s)",
        source_id,
        asset_role,
        _safe_exception_type(error),
    )
