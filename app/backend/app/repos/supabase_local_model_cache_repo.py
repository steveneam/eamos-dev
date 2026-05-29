from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import logging
import re
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.core.db import build_session_factory, session_scope
from app.repos.source_cache_repo import SourceCachePayload
from app.schemas.protein_annotation import ProteinDomainTrack

logger = logging.getLogger(__name__)


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
    ) -> None:
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
            """)
        try:
            with session_scope(self.session_factory) as session:
                session.execute(
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
                )
        except Exception as exc:
            raise SupabaseLocalModelCacheError(
                _safe_error_message("Supabase source version write failed.", exc)
            ) from exc

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
                },
                provenance={"repo": "SupabaseVariantCacheRepo"},
                fetched_at=_now(),
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
