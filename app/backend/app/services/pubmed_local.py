from __future__ import annotations

from collections.abc import Iterable
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import tempfile
from typing import Any

from app.core.config import Settings
from app.services.pubmed_local_constants import (
    DEFAULT_BIOMEDICAL_DOMAINS,
    PUBMED_LOCAL_CLI_VERSION,
    PUBMED_LOCAL_SCHEMA_VERSION,
    PUBMED_LOCAL_SOURCE_ID,
)
from app.services.pubmed_local_license_policy import (
    abstract_policy_for_license as abstract_policy_for_license,
    classify_license_profile as classify_license_profile,
)
from app.services.pubmed_local_models import (
    PubMedLocalInspection,
    PubMedLocalMaterializationResult,
    PubMedLocalQueryCoverage,
    PubMedLocalSchemaError,
    PubMedSeedQuery,
    PubMedSourceFileImportStats,
)
from app.services.pubmed_local_parsing import (
    _article_matches_allowed_domains,
    _cdna_from_transcript_hgvs,
    _connect_readonly,
    _default_source_version,
    _dedupe,
    _edge_seed_terms_by_pmid,
    _iter_articles_from_source_file,
    _iter_literature_edges_from_source_file,
    _json_dict_int,
    _json_list,
    _json_nested_int,
    _gene_scope_query,
    _gene_scope_url,
    _matched_seed_terms,
    _normalize_allowed_domains,
    _normalize_space,
    _normalize_term,
    _resolve_path,
    _safe_size,
    _source_file_manifests,
    _utc_now,
    _verify_input_md5_sidecars,
    read_pmc_oa_license_map,
    read_seed_queries,
)
from app.tools.base import ToolResult


class PubMedLocalStore:
    """Read-only PubMed local source asset access."""

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

    def inspect(self, *, verify_checksum: bool = True) -> PubMedLocalInspection:
        if not self.db_path.is_file():
            return PubMedLocalInspection(
                source_id=PUBMED_LOCAL_SOURCE_ID,
                status="db_missing",
                ready=False,
                enabled=self.enabled,
                message="PubMed local SQLite asset is missing",
            )
        if self.manifest_path is not None and not self.manifest_path.is_file():
            return PubMedLocalInspection(
                source_id=PUBMED_LOCAL_SOURCE_ID,
                status="manifest_missing",
                ready=False,
                enabled=self.enabled,
                actual_size_bytes=_safe_size(self.db_path),
                message="PubMed local manifest is missing",
            )

        try:
            with closing(_connect_readonly(self.db_path)) as conn:
                _require_schema(conn)
                manifest = _manifest_row(conn)
                fts_status = _fts_status(conn)
                counts = _count_profile(conn)
                checksum_verified = False
                if verify_checksum:
                    expected = str(manifest.get("checksum_value") or "")
                    actual = _logical_checksum(conn)
                    checksum_verified = bool(expected and expected == actual)
                    if not checksum_verified:
                        return PubMedLocalInspection(
                            source_id=PUBMED_LOCAL_SOURCE_ID,
                            status="checksum_mismatch",
                            ready=False,
                            enabled=self.enabled,
                            schema_version=str(manifest.get("schema_version") or ""),
                            source_version=str(manifest.get("source_version") or ""),
                            fts_status=fts_status,
                            actual_size_bytes=_safe_size(self.db_path),
                            checksum_verified=False,
                            checksum_algorithm="sha256",
                            checksum_value=None,
                            message="PubMed local logical checksum mismatch",
                        )
                return PubMedLocalInspection(
                    source_id=PUBMED_LOCAL_SOURCE_ID,
                    status="ready",
                    ready=True,
                    enabled=self.enabled,
                    schema_version=str(manifest.get("schema_version") or ""),
                    source_version=str(manifest.get("source_version") or ""),
                    article_count=counts["article_count"],
                    licensed_abstract_count=counts["licensed_abstract_count"],
                    metadata_only_count=counts["metadata_only_count"],
                    deleted_count=counts["deleted_count"],
                    coverage_count=counts["coverage_count"],
                    domain_filtered_count=int(manifest.get("domain_filtered_count") or 0),
                    pmc_license_overlay_count=int(manifest.get("pmc_license_overlay_count") or 0),
                    literature_edge_count=counts["literature_edge_count"],
                    source_file_count=int(manifest.get("source_file_count") or 0),
                    source_kind_counts=_json_dict_int(manifest.get("source_kind_counts_json")),
                    import_stats_by_source=_json_nested_int(
                        manifest.get("import_stats_by_source_json")
                    ),
                    fts_status=fts_status,
                    actual_size_bytes=_safe_size(self.db_path),
                    checksum_verified=checksum_verified,
                    checksum_algorithm="sha256" if verify_checksum else None,
                    checksum_value=(
                        str(manifest.get("checksum_value") or "") if checksum_verified else None
                    ),
                    input_checksum_status=str(
                        manifest.get("input_checksum_status") or "not_checked"
                    ),
                    input_checksum_verified_count=int(
                        manifest.get("input_checksum_verified_count") or 0
                    ),
                    input_checksum_missing_count=int(
                        manifest.get("input_checksum_missing_count") or 0
                    ),
                    warnings=tuple(_json_list(manifest.get("warnings_json"))),
                )
        except sqlite3.DatabaseError:
            return PubMedLocalInspection(
                source_id=PUBMED_LOCAL_SOURCE_ID,
                status="db_unreadable",
                ready=False,
                enabled=self.enabled,
                actual_size_bytes=_safe_size(self.db_path),
                message="PubMed local SQLite asset is unreadable",
            )
        except PubMedLocalSchemaError as exc:
            return PubMedLocalInspection(
                source_id=PUBMED_LOCAL_SOURCE_ID,
                status=exc.code,
                ready=False,
                enabled=self.enabled,
                actual_size_bytes=_safe_size(self.db_path),
                message=str(exc),
            )

    def search_tool_result(self, variant: Any, *, limit: int) -> tuple[ToolResult, bool]:
        inspection = self.inspect(verify_checksum=False)
        gene = str(getattr(variant, "gene", "") or "").strip().upper()
        source_url = _gene_scope_url(gene) if gene else None
        if not inspection.ready:
            warning = f"pubmed_local_unavailable:{inspection.status}"
            return (
                ToolResult(
                    source="pubmed",
                    status="missing",
                    request_identity={"term": _local_query_identity(variant)},
                    summary={"articles": [], "total": 0},
                    warnings=[warning],
                    raw={},
                    source_url=source_url,
                    source_version=inspection.source_version,
                    cache_status="pubmed_local_unavailable",
                ),
                True,
            )

        with closing(_connect_readonly(self.db_path)) as conn:
            seed = _seed_from_variant(variant)
            articles = _search_articles(conn, seed, limit=limit)
            gene_scope = _gene_scope_count(conn, seed.gene, inspection.source_version)
            coverage = _coverage_for(conn, seed)

        warnings = list(coverage.warnings)
        summary: dict[str, Any] = {
            "articles": articles,
            "total": len(articles),
            "request_identity": {
                "term": _local_query_identity(variant),
                "coverage_status": coverage.status,
                "coverage_completeness": coverage.completeness,
            },
            "source_version": inspection.source_version,
        }
        if gene_scope is not None:
            summary["gene_scope"] = gene_scope
        if not articles and not coverage.complete:
            warnings.append("pubmed_local_no_hit_incomplete_coverage")

        return (
            ToolResult(
                source="pubmed",
                status="local",
                request_identity={"term": _local_query_identity(variant)},
                summary=summary,
                warnings=_dedupe(warnings),
                raw={},
                source_url=source_url,
                source_version=inspection.source_version,
                cache_status="pubmed_local_materialized",
            ),
            bool(not articles and not coverage.complete),
        )


def inspect_pubmed_local_store(
    settings: Settings, *, verify_checksum: bool = True
) -> PubMedLocalInspection:
    return PubMedLocalStore(
        _resolve_path(settings, settings.pubmed_local_sqlite_path),
        manifest_path=_resolve_path(settings, settings.pubmed_local_manifest_path),
        enabled=settings.pubmed_local_enabled,
    ).inspect(verify_checksum=verify_checksum)


def materialize_pubmed_local_store(
    settings: Settings,
    *,
    xml_files: Iterable[Path] = (),
    jsonl_files: Iterable[Path] = (),
    pmc_license_files: Iterable[Path] = (),
    pubtator_edge_files: Iterable[Path] = (),
    litvar_edge_files: Iterable[Path] = (),
    query_file: Path | None = None,
    output_path: Path | None = None,
    manifest_path: Path | None = None,
    source_version: str | None = None,
    coverage_completeness: str = "partial",
    domain_filter: str = "none",
    allowed_domains: Iterable[str] | None = DEFAULT_BIOMEDICAL_DOMAINS,
    verify_md5_sidecars: bool = False,
    xml_source_kind: str = "auto",
    force: bool = False,
) -> PubMedLocalMaterializationResult:
    destination = _resolve_path(settings, output_path or settings.pubmed_local_sqlite_path)
    manifest_destination = _resolve_path(
        settings,
        manifest_path or settings.pubmed_local_manifest_path,
    )
    if destination.exists() and not force:
        inspection = PubMedLocalStore(
            destination,
            manifest_path=manifest_destination,
            enabled=settings.pubmed_local_enabled,
        ).inspect(verify_checksum=True)
        if inspection.ready:
            return PubMedLocalMaterializationResult(
                ready=True,
                status="already_ready",
                article_count=inspection.article_count,
                licensed_abstract_count=inspection.licensed_abstract_count,
                metadata_only_count=inspection.metadata_only_count,
                deleted_count=inspection.deleted_count,
                coverage_count=inspection.coverage_count,
                domain_filtered_count=inspection.domain_filtered_count,
                pmc_license_overlay_count=inspection.pmc_license_overlay_count,
                literature_edge_count=inspection.literature_edge_count,
                source_file_count=inspection.source_file_count,
                source_kind_counts=inspection.source_kind_counts,
                import_stats_by_source=inspection.import_stats_by_source,
                fts_status=inspection.fts_status,
                source_version=inspection.source_version,
                checksum_value=inspection.checksum_value,
                input_checksum_status=inspection.input_checksum_status,
                input_checksum_verified_count=inspection.input_checksum_verified_count,
                input_checksum_missing_count=inspection.input_checksum_missing_count,
                warnings=("existing_pubmed_local_asset_left_unchanged",),
            )

    seeds = read_seed_queries(query_file) if query_file is not None else []
    source_version = source_version or _default_source_version()
    warnings: list[str] = []
    xml_paths = tuple(xml_files)
    jsonl_paths = tuple(jsonl_files)
    pmc_license_paths = tuple(pmc_license_files)
    pubtator_edge_paths = tuple(pubtator_edge_files)
    litvar_edge_paths = tuple(litvar_edge_files)
    pmc_license_map = read_pmc_oa_license_map(pmc_license_paths)
    domain_filter_mode = domain_filter.strip().lower() or "none"
    allowed_domain_set = _normalize_allowed_domains(allowed_domains or DEFAULT_BIOMEDICAL_DOMAINS)
    if not xml_paths and not jsonl_paths and not pubtator_edge_paths and not litvar_edge_paths:
        return PubMedLocalMaterializationResult(
            ready=False,
            status="no_input",
            source_version=source_version,
            warnings=("no_pubmed_input_files_supplied",),
        )
    if domain_filter_mode not in {"none", "biomedical"}:
        return PubMedLocalMaterializationResult(
            ready=False,
            status="unsupported_domain_filter",
            source_version=source_version,
            warnings=(f"unsupported_domain_filter:{domain_filter_mode}",),
        )
    xml_source_kind_mode = xml_source_kind.strip().lower() or "auto"
    if xml_source_kind_mode not in {
        "auto",
        "baseline",
        "update",
        "pubmed_xml",
        "pubmed_baseline",
        "pubmed_update",
    }:
        return PubMedLocalMaterializationResult(
            ready=False,
            status="unsupported_xml_source_kind",
            source_version=source_version,
            warnings=(f"unsupported_xml_source_kind:{xml_source_kind_mode}",),
        )
    checksum_summary = _verify_input_md5_sidecars(xml_paths) if verify_md5_sidecars else {}
    if checksum_summary:
        warnings.extend(checksum_summary.get("warnings", ()))
        if int(checksum_summary.get("mismatched_count", 0)) > 0:
            return PubMedLocalMaterializationResult(
                ready=False,
                status="input_checksum_mismatch",
                source_version=source_version,
                input_checksum_status=str(checksum_summary.get("status") or "mismatch"),
                input_checksum_verified_count=int(checksum_summary.get("verified_count", 0)),
                input_checksum_missing_count=int(checksum_summary.get("missing_count", 0)),
                warnings=tuple(warnings),
            )
    source_files = _source_file_manifests(
        xml_paths,
        jsonl_paths,
        pubtator_edge_paths,
        litvar_edge_paths,
        xml_source_kind=xml_source_kind_mode,
        checksum_summary=checksum_summary,
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="eamos-pubmed-local-",
        dir=destination.parent,
    ) as tmp_dir:
        temp_path = Path(tmp_dir) / "pubmed-local.sqlite"
        with closing(sqlite3.connect(temp_path)) as conn:
            conn.row_factory = sqlite3.Row
            fts_status = _initialize_schema(conn)
            edge_seed_terms_by_pmid = _edge_seed_terms_by_pmid(
                source_files,
                seeds,
                source_version=source_version,
            )
            coverage_hits: dict[str, set[str]] = {seed.coverage_key: set() for seed in seeds}
            seed_by_key = {seed.coverage_key: seed for seed in seeds}
            domain_filtered_count = 0
            pmc_license_overlay_count = 0
            import_stats: list[PubMedSourceFileImportStats] = []

            for source_file in source_files:
                source_file_stats = PubMedSourceFileImportStats(source_file=source_file)
                if source_file.source_format == "literature_edge_jsonl":
                    for edge in _iter_literature_edges_from_source_file(
                        source_file,
                        source_version=source_version,
                    ):
                        source_file_stats.records_seen_count += 1
                        if edge is None:
                            source_file_stats.invalid_record_count += 1
                            continue
                        if not _article_exists(conn, edge["pmid"]):
                            source_file_stats.literature_edge_orphan_skipped_count += 1
                            continue
                        _upsert_literature_edge(conn, edge)
                        source_file_stats.literature_edge_imported_count += 1
                    _insert_source_file_import_stats(
                        conn,
                        source_file_stats,
                        source_version=source_version,
                    )
                    import_stats.append(source_file_stats)
                    continue

                for article in _iter_articles_from_source_file(
                    source_file,
                    source_version=source_version,
                    pmc_license_map=pmc_license_map,
                ):
                    source_file_stats.records_seen_count += 1
                    if article.get("_pmc_license_overlay_used"):
                        pmc_license_overlay_count += 1
                        source_file_stats.pmc_license_overlay_count += 1
                    if article["source_status"] == "deleted":
                        _upsert_article(conn, article)
                        source_file_stats.bump_imported_article(article)
                        continue
                    if domain_filter_mode == "biomedical" and not _article_matches_allowed_domains(
                        article,
                        allowed_domain_set,
                    ):
                        domain_filtered_count += 1
                        source_file_stats.domain_filtered_count += 1
                        continue
                    matched = _matched_seed_terms(
                        article,
                        seeds,
                        extra_terms_by_seed=edge_seed_terms_by_pmid.get(article["pmid"]),
                    )
                    if seeds and not matched:
                        source_file_stats.seed_filtered_count += 1
                        continue
                    _upsert_article(conn, article)
                    source_file_stats.bump_imported_article(article)
                    for seed, matched_terms in matched:
                        coverage_hits.setdefault(seed.coverage_key, set()).add(article["pmid"])
                        _insert_matched_terms(conn, article["pmid"], matched_terms)
                _insert_source_file_import_stats(
                    conn,
                    source_file_stats,
                    source_version=source_version,
                )
                import_stats.append(source_file_stats)

            for seed in seeds:
                pmids = coverage_hits.get(seed.coverage_key, set())
                _upsert_coverage(
                    conn,
                    seed,
                    result_count=len(pmids),
                    completeness=coverage_completeness,
                    source_version=source_version,
                    warnings=(),
                )
                if seed.scope == "variant":
                    gene_seed = PubMedSeedQuery(gene=seed.gene, scope="gene")
                    if gene_seed.coverage_key not in seed_by_key:
                        _upsert_coverage(
                            conn,
                            gene_seed,
                            result_count=_count_gene_pmids(conn, seed.gene),
                            completeness="partial",
                            source_version=source_version,
                            warnings=("derived_from_variant_seed",),
                        )

            counts = _count_profile(conn)
            if counts["article_count"] <= 0:
                return PubMedLocalMaterializationResult(
                    ready=False,
                    status="no_usable_rows",
                    source_version=source_version,
                    fts_status=fts_status,
                    literature_edge_count=counts["literature_edge_count"],
                    domain_filtered_count=domain_filtered_count,
                    pmc_license_overlay_count=pmc_license_overlay_count,
                    source_file_count=len(import_stats),
                    source_kind_counts=_source_kind_counts_from_stats(import_stats),
                    import_stats_by_source=_import_stats_by_source(import_stats),
                    input_checksum_status=str(checksum_summary.get("status") or "not_checked"),
                    input_checksum_verified_count=int(checksum_summary.get("verified_count", 0)),
                    input_checksum_missing_count=int(checksum_summary.get("missing_count", 0)),
                    warnings=("no_articles_matched_policy_or_seed_filter",),
                )

            _write_manifest_row(
                conn,
                source_version=source_version,
                checksum_value="pending",
                domain_filter_mode=domain_filter_mode,
                allowed_domains=allowed_domain_set,
                domain_filtered_count=domain_filtered_count,
                pmc_license_overlay_count=pmc_license_overlay_count,
                input_checksum_summary=checksum_summary,
                warnings=tuple(warnings),
            )
            checksum_value = _logical_checksum(conn)
            _write_manifest_row(
                conn,
                source_version=source_version,
                checksum_value=checksum_value,
                domain_filter_mode=domain_filter_mode,
                allowed_domains=allowed_domain_set,
                domain_filtered_count=domain_filtered_count,
                pmc_license_overlay_count=pmc_license_overlay_count,
                input_checksum_summary=checksum_summary,
                warnings=tuple(warnings),
            )
            conn.commit()

        # Validate before publishing; request handlers must never observe a half-built DB.
        staged_inspection = PubMedLocalStore(temp_path, enabled=False).inspect(verify_checksum=True)
        if not staged_inspection.ready:
            return PubMedLocalMaterializationResult(
                ready=False,
                status=f"staged_{staged_inspection.status}",
                source_version=source_version,
                warnings=tuple([*warnings, "staged_pubmed_local_asset_failed_preflight"]),
            )

        temp_manifest = Path(tmp_dir) / "pubmed-local.manifest.json"
        temp_manifest.write_text(
            json.dumps(
                {
                    "schema_version": PUBMED_LOCAL_SCHEMA_VERSION,
                    "source_version": source_version,
                    "checksum_algorithm": "sha256",
                    "checksum_value": staged_inspection.checksum_value,
                    "article_count": staged_inspection.article_count,
                    "licensed_abstract_count": staged_inspection.licensed_abstract_count,
                    "metadata_only_count": staged_inspection.metadata_only_count,
                    "deleted_count": staged_inspection.deleted_count,
                    "coverage_count": staged_inspection.coverage_count,
                    "domain_filtered_count": staged_inspection.domain_filtered_count,
                    "pmc_license_overlay_count": staged_inspection.pmc_license_overlay_count,
                    "literature_edge_count": staged_inspection.literature_edge_count,
                    "source_file_count": staged_inspection.source_file_count,
                    "source_kind_counts": staged_inspection.source_kind_counts,
                    "import_stats_by_source": staged_inspection.import_stats_by_source,
                    "input_checksum_status": staged_inspection.input_checksum_status,
                    "input_checksum_verified_count": (
                        staged_inspection.input_checksum_verified_count
                    ),
                    "input_checksum_missing_count": staged_inspection.input_checksum_missing_count,
                    "materialized_at": _utc_now(),
                    "cli_version": PUBMED_LOCAL_CLI_VERSION,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        temp_path.replace(destination)
        temp_manifest.replace(manifest_destination)

    final = PubMedLocalStore(
        destination,
        manifest_path=manifest_destination,
        enabled=settings.pubmed_local_enabled,
    ).inspect(verify_checksum=True)
    return PubMedLocalMaterializationResult(
        ready=final.ready,
        status=final.status,
        article_count=final.article_count,
        licensed_abstract_count=final.licensed_abstract_count,
        metadata_only_count=final.metadata_only_count,
        deleted_count=final.deleted_count,
        coverage_count=final.coverage_count,
        domain_filtered_count=final.domain_filtered_count,
        pmc_license_overlay_count=final.pmc_license_overlay_count,
        literature_edge_count=final.literature_edge_count,
        source_file_count=final.source_file_count,
        source_kind_counts=final.source_kind_counts,
        import_stats_by_source=final.import_stats_by_source,
        fts_status=final.fts_status,
        source_version=final.source_version,
        checksum_value=final.checksum_value,
        input_checksum_status=final.input_checksum_status,
        input_checksum_verified_count=final.input_checksum_verified_count,
        input_checksum_missing_count=final.input_checksum_missing_count,
        warnings=final.warnings,
    )


def _initialize_schema(conn: sqlite3.Connection) -> str:
    conn.executescript("""
        create table pubmed_article (
          pmid text primary key,
          title text not null,
          authors_display text not null default '',
          journal text not null default '',
          year text not null default '',
          publication_date text,
          doi text,
          pmcid text,
          pubmed_url text not null,
          source_status text not null,
          source_version text not null,
          fetched_at text not null,
          license_profile text not null,
          license_source text,
          abstract_policy text not null,
          abstract_text text,
          abstract_sha256 text,
          is_retracted integer not null default 0,
          mesh_terms_json text not null default '[]',
          chemical_terms_json text not null default '[]',
          publication_types_json text not null default '[]',
          language text not null default '',
          provenance_json text not null default '{}'
        );

        create table pubmed_article_term (
          pmid text not null references pubmed_article(pmid) on delete cascade,
          term_type text not null,
          term_norm text not null,
          matched_field text not null,
          primary key (pmid, term_type, term_norm, matched_field)
        );
        create index idx_pubmed_article_term_norm on pubmed_article_term(term_norm, term_type);

        create table pubmed_literature_edge (
          edge_id text primary key,
          pmid text not null,
          source text not null,
          entity_type text not null,
          identifier text,
          normalized_identifier text not null default '',
          matched_text text not null default '',
          normalized_mention text not null default '',
          section text not null default '',
          offset_start integer,
          offset_end integer,
          relation_type text,
          evidence_text text,
          source_url text,
          source_file_id text not null,
          source_kind text not null,
          source_file_name text not null,
          load_order integer not null,
          source_version text not null,
          imported_at text not null,
          provenance_json text not null default '{}',
          foreign key (pmid) references pubmed_article(pmid) on delete cascade
        );
        create index idx_pubmed_literature_edge_pmid on pubmed_literature_edge(pmid);
        create index idx_pubmed_literature_edge_lookup on pubmed_literature_edge(
          entity_type, normalized_identifier, normalized_mention
        );
        create index idx_pubmed_literature_edge_source on pubmed_literature_edge(
          source, source_kind
        );

        create table pubmed_coverage (
          coverage_key text primary key,
          scope text not null,
          gene_norm text not null,
          query_terms_json text not null,
          completeness text not null,
          materialized_at text not null,
          source_query text not null,
          result_count integer not null,
          warning_json text not null default '[]'
        );

        create table pubmed_source_file (
          source_file_id text primary key,
          load_order integer not null,
          source_kind text not null,
          source_format text not null,
          source_file_name text not null,
          source_version text not null,
          size_bytes integer,
          md5_status text not null default 'not_checked',
          records_seen_count integer not null default 0,
          article_imported_count integer not null default 0,
          deleted_imported_count integer not null default 0,
          domain_filtered_count integer not null default 0,
          seed_filtered_count integer not null default 0,
          invalid_record_count integer not null default 0,
          pmc_license_overlay_count integer not null default 0,
          literature_edge_imported_count integer not null default 0,
          literature_edge_orphan_skipped_count integer not null default 0,
          licensed_abstract_count integer not null default 0,
          metadata_only_count integer not null default 0,
          warnings_json text not null default '[]'
        );
        create index idx_pubmed_source_file_order on pubmed_source_file(load_order);
        create index idx_pubmed_source_file_kind on pubmed_source_file(source_kind);

        create table pubmed_materialization_manifest (
          id integer primary key check (id = 1),
          schema_version text not null,
          source_version text not null,
          materialized_at text not null,
          cli_version text not null,
          article_count integer not null,
          licensed_abstract_count integer not null,
          metadata_only_count integer not null,
          deleted_count integer not null,
          coverage_count integer not null,
          domain_filter_mode text not null default 'none',
          allowed_domains_json text not null default '[]',
          domain_filtered_count integer not null default 0,
          pmc_license_overlay_count integer not null default 0,
          literature_edge_count integer not null default 0,
          source_file_count integer not null default 0,
          source_kind_counts_json text not null default '{}',
          import_stats_by_source_json text not null default '{}',
          input_checksum_status text not null default 'not_checked',
          input_checksum_verified_count integer not null default 0,
          input_checksum_missing_count integer not null default 0,
          checksum_algorithm text not null,
          checksum_value text not null,
          warnings_json text not null default '[]'
        );
        """)
    try:
        conn.execute("""
            create virtual table pubmed_article_fts using fts5(
              pmid unindexed,
              title,
              abstract_text
            )
            """)
        return "available"
    except sqlite3.OperationalError:
        return "unavailable"


def _upsert_article(conn: sqlite3.Connection, article: dict[str, Any]) -> None:
    conn.execute(
        """
        insert into pubmed_article (
          pmid, title, authors_display, journal, year, publication_date, doi, pmcid,
          pubmed_url, source_status, source_version, fetched_at, license_profile,
          license_source, abstract_policy, abstract_text, abstract_sha256, is_retracted,
          mesh_terms_json, chemical_terms_json, publication_types_json, language,
          provenance_json
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(pmid) do update set
          title=excluded.title,
          authors_display=excluded.authors_display,
          journal=excluded.journal,
          year=excluded.year,
          publication_date=excluded.publication_date,
          doi=excluded.doi,
          pmcid=excluded.pmcid,
          pubmed_url=excluded.pubmed_url,
          source_status=excluded.source_status,
          source_version=excluded.source_version,
          fetched_at=excluded.fetched_at,
          license_profile=excluded.license_profile,
          license_source=excluded.license_source,
          abstract_policy=excluded.abstract_policy,
          abstract_text=excluded.abstract_text,
          abstract_sha256=excluded.abstract_sha256,
          is_retracted=excluded.is_retracted,
          mesh_terms_json=excluded.mesh_terms_json,
          chemical_terms_json=excluded.chemical_terms_json,
          publication_types_json=excluded.publication_types_json,
          language=excluded.language,
          provenance_json=excluded.provenance_json
        """,
        (
            article["pmid"],
            article["title"],
            article["authors_display"],
            article["journal"],
            article["year"],
            article["publication_date"],
            article["doi"],
            article["pmcid"],
            article["pubmed_url"],
            article["source_status"],
            article["source_version"],
            article["fetched_at"],
            article["license_profile"],
            article["license_source"],
            article["abstract_policy"],
            article["abstract_text"],
            article["abstract_sha256"],
            article["is_retracted"],
            json.dumps(list(article.get("mesh_terms") or ()), sort_keys=True),
            json.dumps(list(article.get("chemical_terms") or ()), sort_keys=True),
            json.dumps(list(article.get("publication_types") or ()), sort_keys=True),
            article["language"],
            article["provenance_json"],
        ),
    )
    fts_status = _fts_status(conn)
    if fts_status == "available":
        conn.execute("delete from pubmed_article_fts where pmid = ?", (article["pmid"],))
    if fts_status == "available" and article["source_status"] != "deleted":
        conn.execute(
            "insert into pubmed_article_fts (pmid, title, abstract_text) values (?, ?, ?)",
            (
                article["pmid"],
                article["title"],
                (
                    article["abstract_text"]
                    if article["abstract_policy"] == "licensed_text_persisted"
                    else ""
                ),
            ),
        )


def _insert_matched_terms(
    conn: sqlite3.Connection,
    pmid: str,
    matched_terms: Iterable[tuple[str, str, str]],
) -> None:
    for term_type, value, matched_field in matched_terms:
        term_norm = _normalize_term(value)
        if not term_norm:
            continue
        conn.execute(
            """
            insert or ignore into pubmed_article_term (pmid, term_type, term_norm, matched_field)
            values (?, ?, ?, ?)
            """,
            (pmid, term_type, term_norm, matched_field),
        )


def _article_exists(conn: sqlite3.Connection, pmid: str) -> bool:
    row = conn.execute(
        "select 1 from pubmed_article where pmid = ? and source_status != 'deleted'",
        (pmid,),
    ).fetchone()
    return row is not None


def _upsert_literature_edge(conn: sqlite3.Connection, edge: dict[str, Any]) -> None:
    conn.execute(
        """
        insert into pubmed_literature_edge (
          edge_id, pmid, source, entity_type, identifier, normalized_identifier,
          matched_text, normalized_mention, section, offset_start, offset_end,
          relation_type, evidence_text, source_url, source_file_id, source_kind,
          source_file_name, load_order, source_version, imported_at, provenance_json
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(edge_id) do update set
          pmid=excluded.pmid,
          source=excluded.source,
          entity_type=excluded.entity_type,
          identifier=excluded.identifier,
          normalized_identifier=excluded.normalized_identifier,
          matched_text=excluded.matched_text,
          normalized_mention=excluded.normalized_mention,
          section=excluded.section,
          offset_start=excluded.offset_start,
          offset_end=excluded.offset_end,
          relation_type=excluded.relation_type,
          evidence_text=excluded.evidence_text,
          source_url=excluded.source_url,
          source_file_id=excluded.source_file_id,
          source_kind=excluded.source_kind,
          source_file_name=excluded.source_file_name,
          load_order=excluded.load_order,
          source_version=excluded.source_version,
          imported_at=excluded.imported_at,
          provenance_json=excluded.provenance_json
        """,
        (
            edge["edge_id"],
            edge["pmid"],
            edge["source"],
            edge["entity_type"],
            edge["identifier"],
            edge["normalized_identifier"],
            edge["matched_text"],
            edge["normalized_mention"],
            edge["section"],
            edge["offset_start"],
            edge["offset_end"],
            edge["relation_type"],
            edge["evidence_text"],
            edge["source_url"],
            edge["source_file_id"],
            edge["source_kind"],
            edge["source_file_name"],
            edge["load_order"],
            edge["source_version"],
            edge["imported_at"],
            edge["provenance_json"],
        ),
    )


def _insert_source_file_import_stats(
    conn: sqlite3.Connection,
    stats: PubMedSourceFileImportStats,
    *,
    source_version: str,
) -> None:
    source_file = stats.source_file
    conn.execute(
        """
        insert into pubmed_source_file (
          source_file_id, load_order, source_kind, source_format, source_file_name,
          source_version, size_bytes, md5_status, records_seen_count,
          article_imported_count, deleted_imported_count, domain_filtered_count,
          seed_filtered_count, invalid_record_count, pmc_license_overlay_count,
          literature_edge_imported_count, literature_edge_orphan_skipped_count,
          licensed_abstract_count, metadata_only_count, warnings_json
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(source_file_id) do update set
          load_order=excluded.load_order,
          source_kind=excluded.source_kind,
          source_format=excluded.source_format,
          source_file_name=excluded.source_file_name,
          source_version=excluded.source_version,
          size_bytes=excluded.size_bytes,
          md5_status=excluded.md5_status,
          records_seen_count=excluded.records_seen_count,
          article_imported_count=excluded.article_imported_count,
          deleted_imported_count=excluded.deleted_imported_count,
          domain_filtered_count=excluded.domain_filtered_count,
          seed_filtered_count=excluded.seed_filtered_count,
          invalid_record_count=excluded.invalid_record_count,
          pmc_license_overlay_count=excluded.pmc_license_overlay_count,
          literature_edge_imported_count=excluded.literature_edge_imported_count,
          literature_edge_orphan_skipped_count=excluded.literature_edge_orphan_skipped_count,
          licensed_abstract_count=excluded.licensed_abstract_count,
          metadata_only_count=excluded.metadata_only_count,
          warnings_json=excluded.warnings_json
        """,
        (
            source_file.source_file_id,
            source_file.load_order,
            source_file.source_kind,
            source_file.source_format,
            source_file.source_file_name,
            source_version,
            source_file.size_bytes,
            source_file.md5_status,
            stats.records_seen_count,
            stats.article_imported_count,
            stats.deleted_imported_count,
            stats.domain_filtered_count,
            stats.seed_filtered_count,
            stats.invalid_record_count,
            stats.pmc_license_overlay_count,
            stats.literature_edge_imported_count,
            stats.literature_edge_orphan_skipped_count,
            stats.licensed_abstract_count,
            stats.metadata_only_count,
            json.dumps(_dedupe(stats.warnings), sort_keys=True),
        ),
    )


def _upsert_coverage(
    conn: sqlite3.Connection,
    seed: PubMedSeedQuery,
    *,
    result_count: int,
    completeness: str,
    source_version: str,
    warnings: Iterable[str],
) -> None:
    conn.execute(
        """
        insert into pubmed_coverage (
          coverage_key, scope, gene_norm, query_terms_json, completeness, materialized_at,
          source_query, result_count, warning_json
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(coverage_key) do update set
          completeness=excluded.completeness,
          materialized_at=excluded.materialized_at,
          source_query=excluded.source_query,
          result_count=excluded.result_count,
          warning_json=excluded.warning_json
        """,
        (
            seed.coverage_key,
            seed.scope,
            _normalize_term(seed.gene),
            json.dumps([value for _kind, value in seed.terms], sort_keys=True),
            completeness,
            _utc_now(),
            f"{source_version}:{seed.source_query}",
            result_count,
            json.dumps(list(warnings), sort_keys=True),
        ),
    )


def _search_articles(
    conn: sqlite3.Connection, seed: PubMedSeedQuery, *, limit: int
) -> list[dict[str, Any]]:
    gene_norm = _normalize_term(seed.gene)
    variant_norms = [
        _normalize_term(value) for value in seed.variant_terms if _normalize_term(value)
    ]
    gene_where = """
        (
          exists (
            select 1 from pubmed_article_term t
            where t.pmid = a.pmid and t.term_type = 'gene' and t.term_norm = ?
          )
          or exists (
            select 1 from pubmed_literature_edge e
            where e.pmid = a.pmid
              and e.entity_type = 'gene'
              and (e.normalized_identifier = ? or e.normalized_mention = ?)
          )
        )
    """
    params: list[Any] = [gene_norm, gene_norm, gene_norm]
    if variant_norms:
        placeholders = ",".join("?" for _ in variant_norms)
        params.extend(variant_norms)
        params.extend(variant_norms)
        params.extend(variant_norms)
        where = f"""
            {gene_where}
            and exists (
              select 1 from pubmed_article_term t
              where t.pmid = a.pmid and t.term_norm in ({placeholders})
              union
              select 1 from pubmed_literature_edge e
              where e.pmid = a.pmid
                and e.entity_type in ('variant', 'rsid', 'snp')
                and (
                  e.normalized_identifier in ({placeholders})
                  or e.normalized_mention in ({placeholders})
                )
            )
        """
    else:
        where = gene_where
    params.append(limit)
    rows = conn.execute(
        f"""
        select a.* from pubmed_article a
        where a.source_status != 'deleted' and {where}
        order by coalesce(a.publication_date, a.year, '') desc, a.pmid desc
        limit ?
        """,
        tuple(params),
    ).fetchall()
    return [_row_to_article(conn, row) for row in rows]


def _row_to_article(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    article = {
        "pmid": row["pmid"],
        "title": row["title"],
        "authors": row["authors_display"],
        "journal": row["journal"],
        "year": row["year"],
        "url": row["pubmed_url"],
        "abstract": row["abstract_text"],
        "pmcid": row["pmcid"],
        "doi": row["doi"],
        "publication_date": row["publication_date"],
    }
    snippets = _article_edge_snippets(conn, row["pmid"])
    if snippets["pubtator"]:
        article["pubtator"] = snippets["pubtator"]
    if snippets["litvar2"]:
        article["litvar2_snippet"] = snippets["litvar2"]
    return article


def _article_edge_snippets(conn: sqlite3.Connection, pmid: str) -> dict[str, list[str]]:
    rows = conn.execute(
        """
        select source, matched_text, evidence_text
        from pubmed_literature_edge
        where pmid = ?
        order by load_order, source, edge_id
        limit 20
        """,
        (pmid,),
    ).fetchall()
    snippets: dict[str, list[str]] = {"pubtator": [], "litvar2": []}
    seen: set[tuple[str, str]] = set()
    for row in rows:
        source = str(row["source"] or "").strip().lower()
        bucket = "litvar2" if "litvar" in source else "pubtator" if "pubtator" in source else ""
        if not bucket:
            continue
        text = _normalize_space(str(row["evidence_text"] or row["matched_text"] or ""))
        if not text:
            continue
        key = (bucket, text)
        if key in seen:
            continue
        if len(snippets[bucket]) >= 5:
            continue
        seen.add(key)
        snippets[bucket].append(text)
    return snippets


def _gene_scope_count(
    conn: sqlite3.Connection,
    gene: str,
    source_version: str | None,
) -> dict[str, Any] | None:
    total = _count_gene_pmids(conn, gene)
    coverage = _coverage_for(conn, PubMedSeedQuery(gene=gene, scope="gene"))
    if total <= 0 and coverage.status == "missing":
        return None
    return {
        "query": _gene_scope_query(gene),
        "total_count": total if total > 0 else coverage.result_count or 0,
        "source_status": "local",
        "source_url": _gene_scope_url(gene),
        "source_version": source_version,
        "coverage_status": coverage.status,
        "coverage_completeness": coverage.completeness,
    }


def _count_gene_pmids(conn: sqlite3.Connection, gene: str) -> int:
    gene_norm = _normalize_term(gene)
    row = conn.execute(
        """
        select count(distinct matched.pmid) as total
        from (
          select t.pmid
          from pubmed_article_term t
          where t.term_type = 'gene' and t.term_norm = ?
          union
          select e.pmid
          from pubmed_literature_edge e
          where e.entity_type = 'gene'
            and (e.normalized_identifier = ? or e.normalized_mention = ?)
        ) matched
        join pubmed_article a on a.pmid = matched.pmid
        where a.source_status != 'deleted'
        """,
        (gene_norm, gene_norm, gene_norm),
    ).fetchone()
    return int(row["total"] or 0) if row is not None else 0


def _coverage_for(conn: sqlite3.Connection, seed: PubMedSeedQuery) -> PubMedLocalQueryCoverage:
    row = conn.execute(
        "select * from pubmed_coverage where coverage_key = ?",
        (seed.coverage_key,),
    ).fetchone()
    if row is None and seed.scope == "variant":
        row = conn.execute(
            "select * from pubmed_coverage where coverage_key = ?",
            (_coverage_key("gene", seed.gene, ()),),
        ).fetchone()
    if row is None:
        return PubMedLocalQueryCoverage(
            status="missing",
            warnings=("pubmed_local_coverage_missing",),
        )
    return PubMedLocalQueryCoverage(
        status="covered",
        completeness=row["completeness"],
        query=row["source_query"],
        result_count=int(row["result_count"]),
        warnings=tuple(_json_list(row["warning_json"])),
    )


def _require_schema(conn: sqlite3.Connection) -> None:
    expected_tables = {
        "pubmed_article",
        "pubmed_article_term",
        "pubmed_literature_edge",
        "pubmed_coverage",
        "pubmed_source_file",
        "pubmed_materialization_manifest",
    }
    rows = conn.execute("select name from sqlite_master where type in ('table','view')").fetchall()
    names = {str(row["name"]) for row in rows}
    missing = expected_tables - names
    if missing:
        raise PubMedLocalSchemaError("schema_mismatch", "PubMed local schema is incomplete")
    manifest = _manifest_row(conn)
    if manifest.get("schema_version") != PUBMED_LOCAL_SCHEMA_VERSION:
        raise PubMedLocalSchemaError("schema_mismatch", "PubMed local schema version mismatch")


def _manifest_row(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute("select * from pubmed_materialization_manifest where id = 1").fetchone()
    if row is None:
        raise PubMedLocalSchemaError("manifest_missing", "PubMed local manifest row is missing")
    return dict(row)


def _write_manifest_row(
    conn: sqlite3.Connection,
    *,
    source_version: str,
    checksum_value: str,
    domain_filter_mode: str,
    allowed_domains: Iterable[str],
    domain_filtered_count: int,
    pmc_license_overlay_count: int,
    input_checksum_summary: dict[str, Any],
    warnings: tuple[str, ...],
) -> None:
    counts = _count_profile(conn)
    source_kind_counts = _source_kind_counts(conn)
    import_stats_by_source = _import_stats_by_source_from_db(conn)
    conn.execute(
        """
        insert into pubmed_materialization_manifest (
          id, schema_version, source_version, materialized_at, cli_version,
          article_count, licensed_abstract_count, metadata_only_count, deleted_count,
          coverage_count, domain_filter_mode, allowed_domains_json, domain_filtered_count,
          pmc_license_overlay_count, literature_edge_count, source_file_count, source_kind_counts_json,
          import_stats_by_source_json, input_checksum_status, input_checksum_verified_count,
          input_checksum_missing_count, checksum_algorithm, checksum_value, warnings_json
        ) values (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(id) do update set
          schema_version=excluded.schema_version,
          source_version=excluded.source_version,
          materialized_at=excluded.materialized_at,
          cli_version=excluded.cli_version,
          article_count=excluded.article_count,
          licensed_abstract_count=excluded.licensed_abstract_count,
          metadata_only_count=excluded.metadata_only_count,
          deleted_count=excluded.deleted_count,
          coverage_count=excluded.coverage_count,
          domain_filter_mode=excluded.domain_filter_mode,
          allowed_domains_json=excluded.allowed_domains_json,
          domain_filtered_count=excluded.domain_filtered_count,
          pmc_license_overlay_count=excluded.pmc_license_overlay_count,
          literature_edge_count=excluded.literature_edge_count,
          source_file_count=excluded.source_file_count,
          source_kind_counts_json=excluded.source_kind_counts_json,
          import_stats_by_source_json=excluded.import_stats_by_source_json,
          input_checksum_status=excluded.input_checksum_status,
          input_checksum_verified_count=excluded.input_checksum_verified_count,
          input_checksum_missing_count=excluded.input_checksum_missing_count,
          checksum_algorithm=excluded.checksum_algorithm,
          checksum_value=excluded.checksum_value,
          warnings_json=excluded.warnings_json
        """,
        (
            PUBMED_LOCAL_SCHEMA_VERSION,
            source_version,
            _utc_now(),
            PUBMED_LOCAL_CLI_VERSION,
            counts["article_count"],
            counts["licensed_abstract_count"],
            counts["metadata_only_count"],
            counts["deleted_count"],
            counts["coverage_count"],
            domain_filter_mode,
            json.dumps(sorted(allowed_domains), sort_keys=True),
            domain_filtered_count,
            pmc_license_overlay_count,
            counts["literature_edge_count"],
            sum(source_kind_counts.values()),
            json.dumps(source_kind_counts, sort_keys=True),
            json.dumps(import_stats_by_source, sort_keys=True),
            str(input_checksum_summary.get("status") or "not_checked"),
            int(input_checksum_summary.get("verified_count", 0)),
            int(input_checksum_summary.get("missing_count", 0)),
            "sha256",
            checksum_value,
            json.dumps(list(warnings), sort_keys=True),
        ),
    )


def _count_profile(conn: sqlite3.Connection) -> dict[str, int]:
    article_count = _scalar_int(
        conn, "select count(*) from pubmed_article where source_status != 'deleted'"
    )
    licensed = _scalar_int(
        conn,
        "select count(*) from pubmed_article where abstract_policy = 'licensed_text_persisted'",
    )
    deleted = _scalar_int(
        conn, "select count(*) from pubmed_article where source_status = 'deleted'"
    )
    coverage = _scalar_int(conn, "select count(*) from pubmed_coverage")
    literature_edge_count = _scalar_int(conn, "select count(*) from pubmed_literature_edge")
    return {
        "article_count": article_count,
        "licensed_abstract_count": licensed,
        "metadata_only_count": max(article_count - licensed, 0),
        "deleted_count": deleted,
        "coverage_count": coverage,
        "literature_edge_count": literature_edge_count,
    }


def _source_kind_counts(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute("""
        select source_kind, count(*) as count
        from pubmed_source_file
        group by source_kind
        order by source_kind
        """).fetchall()
    return {str(row["source_kind"]): int(row["count"] or 0) for row in rows}


def _source_kind_counts_from_stats(
    import_stats: Iterable[PubMedSourceFileImportStats],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for stats in import_stats:
        source_kind = stats.source_file.source_kind
        counts[source_kind] = counts.get(source_kind, 0) + 1
    return dict(sorted(counts.items()))


def _import_stats_by_source_from_db(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    rows = conn.execute("""
        select
          source_kind,
          count(*) as source_file_count,
          coalesce(sum(records_seen_count), 0) as records_seen_count,
          coalesce(sum(article_imported_count), 0) as article_imported_count,
          coalesce(sum(deleted_imported_count), 0) as deleted_imported_count,
          coalesce(sum(domain_filtered_count), 0) as domain_filtered_count,
          coalesce(sum(seed_filtered_count), 0) as seed_filtered_count,
          coalesce(sum(invalid_record_count), 0) as invalid_record_count,
          coalesce(sum(pmc_license_overlay_count), 0) as pmc_license_overlay_count,
          coalesce(sum(literature_edge_imported_count), 0) as literature_edge_imported_count,
          coalesce(sum(literature_edge_orphan_skipped_count), 0)
            as literature_edge_orphan_skipped_count,
          coalesce(sum(licensed_abstract_count), 0) as licensed_abstract_count,
          coalesce(sum(metadata_only_count), 0) as metadata_only_count
        from pubmed_source_file
        group by source_kind
        order by source_kind
        """).fetchall()
    return {
        str(row["source_kind"]): {
            key: int(row[key] or 0)
            for key in (
                "source_file_count",
                "records_seen_count",
                "article_imported_count",
                "deleted_imported_count",
                "domain_filtered_count",
                "seed_filtered_count",
                "invalid_record_count",
                "pmc_license_overlay_count",
                "literature_edge_imported_count",
                "literature_edge_orphan_skipped_count",
                "licensed_abstract_count",
                "metadata_only_count",
            )
        }
        for row in rows
    }


def _import_stats_by_source(
    import_stats: Iterable[PubMedSourceFileImportStats],
) -> dict[str, dict[str, int]]:
    grouped: dict[str, dict[str, int]] = {}
    for stats in import_stats:
        source_kind = stats.source_file.source_kind
        bucket = grouped.setdefault(
            source_kind,
            {
                "source_file_count": 0,
                "records_seen_count": 0,
                "article_imported_count": 0,
                "deleted_imported_count": 0,
                "domain_filtered_count": 0,
                "seed_filtered_count": 0,
                "invalid_record_count": 0,
                "pmc_license_overlay_count": 0,
                "literature_edge_imported_count": 0,
                "literature_edge_orphan_skipped_count": 0,
                "licensed_abstract_count": 0,
                "metadata_only_count": 0,
            },
        )
        bucket["source_file_count"] += 1
        bucket["records_seen_count"] += stats.records_seen_count
        bucket["article_imported_count"] += stats.article_imported_count
        bucket["deleted_imported_count"] += stats.deleted_imported_count
        bucket["domain_filtered_count"] += stats.domain_filtered_count
        bucket["seed_filtered_count"] += stats.seed_filtered_count
        bucket["invalid_record_count"] += stats.invalid_record_count
        bucket["pmc_license_overlay_count"] += stats.pmc_license_overlay_count
        bucket["literature_edge_imported_count"] += stats.literature_edge_imported_count
        bucket["literature_edge_orphan_skipped_count"] += stats.literature_edge_orphan_skipped_count
        bucket["licensed_abstract_count"] += stats.licensed_abstract_count
        bucket["metadata_only_count"] += stats.metadata_only_count
    return {key: grouped[key] for key in sorted(grouped)}


def _scalar_int(conn: sqlite3.Connection, query: str) -> int:
    row = conn.execute(query).fetchone()
    return int(row[0] or 0) if row is not None else 0


def _fts_status(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "select name from sqlite_master where type = 'table' and name = 'pubmed_article_fts'"
    ).fetchone()
    return "available" if row is not None else "unavailable"


def _logical_checksum(conn: sqlite3.Connection) -> str:
    digest = sha256()
    table_order = {
        "pubmed_article": "pmid",
        "pubmed_article_term": "pmid, term_type, term_norm, matched_field",
        "pubmed_literature_edge": "pmid, source, entity_type, edge_id",
        "pubmed_coverage": "coverage_key",
        "pubmed_source_file": "load_order, source_file_id",
    }
    for table, order_by in table_order.items():
        rows = conn.execute(f"select * from {table} order by {order_by}").fetchall()
        for row in rows:
            payload = dict(row)
            digest.update(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))
            digest.update(b"\n")
    return digest.hexdigest()


def _seed_from_variant(variant: Any) -> PubMedSeedQuery:
    gene = str(getattr(variant, "gene", "") or "").strip().upper()
    transcript = str(getattr(variant, "transcript_hgvs", "") or "").strip() or None
    cdna = _cdna_from_transcript_hgvs(transcript)
    return PubMedSeedQuery(
        gene=gene,
        cdna=cdna,
        transcript=transcript,
        protein_change=str(getattr(variant, "protein_change", "") or "").strip() or None,
        rsid=str(getattr(variant, "dbsnp_rsid", "") or "").strip() or None,
        genomic_hg38=str(getattr(variant, "genomic_hg38", "") or "").strip() or None,
        scope=(
            "variant"
            if any(
                (
                    cdna,
                    transcript,
                    getattr(variant, "protein_change", None),
                    getattr(variant, "dbsnp_rsid", None),
                    getattr(variant, "genomic_hg38", None),
                )
            )
            else "gene"
        ),
    )


def _local_query_identity(variant: Any) -> str:
    seed = _seed_from_variant(variant)
    if seed.variant_terms:
        identifiers = " OR ".join(seed.variant_terms)
        return f"{seed.gene}[Gene Name] AND ({identifiers})"
    return _gene_scope_query(seed.gene)


def _coverage_key(scope: str, gene: str, terms: Iterable[str]) -> str:
    normalized_terms = sorted(_normalize_term(term) for term in terms if _normalize_term(term))
    digest = sha256(json.dumps(normalized_terms, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"{scope}:{_normalize_term(gene)}:{digest}"
