from __future__ import annotations

import csv
from collections.abc import Iterable
from contextlib import closing
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, timezone
import gzip
from hashlib import md5, sha256
import json
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Any
import xml.etree.ElementTree as ET

from app.core.config import Settings
from app.tools.base import ToolResult

PUBMED_LOCAL_SCHEMA_VERSION = "eamos.pubmed_local.v4"
PUBMED_LOCAL_SOURCE_ID = "eamos_pubmed_local"
PUBMED_LOCAL_CLI_VERSION = "pubmed-local-cli-v1"
PUBMED_LOCAL_SOURCE_VERSION_PREFIX = "pubmed-local"

PERMISSIVE_LICENSE_PROFILES = {"cc0", "cc_by", "cc_by_sa", "public_domain", "us_government"}
DEFAULT_BIOMEDICAL_DOMAINS = ("gene", "biology", "biochemistry", "chemistry")
DEFAULT_ALLOWED_LANGUAGES = ("eng", "en", "english")
DEFAULT_EXCLUDED_PUBLICATION_TYPES = (
    "autobiography",
    "bibliography",
    "biography",
    "comment",
    "directory",
    "editorial",
    "festschrift",
    "historical article",
    "interview",
    "lecture",
    "legal case",
    "letter",
    "news",
    "newspaper article",
    "patient education handout",
    "popular work",
    "published erratum",
)
NON_BIOMEDICAL_NEGATIVE_MARKERS = (
    "architecture",
    "astronomy",
    "automotive",
    "bridge engineering",
    "civil engineering",
    "climate model",
    "construction",
    "economic",
    "finance",
    "geology",
    "industrial process",
    "mining",
    "optical fiber",
    "petroleum",
    "polymer synthesis",
    "semiconductor",
    "soil mechanics",
    "wastewater",
)
BIOMEDICAL_DOMAIN_MARKERS = {
    "gene": (
        "gene",
        "genes",
        "genetic",
        "genetics",
        "genomic",
        "genomics",
        "variant",
        "variants",
        "mutation",
        "mutations",
        "allele",
        "alleles",
        "hgvs",
        "transcript",
        "chromosome",
        "dna",
        "rna",
    ),
    "biology": (
        "biology",
        "biological",
        "biomedical",
        "biomedical engineering",
        "bioengineering",
        "biomaterial",
        "biomaterials",
        "disease",
        "disorder",
        "phenotype",
        "clinical",
        "patient",
        "patients",
        "cell",
        "cells",
        "tissue",
        "tissue engineering",
        "organism",
        "retinal",
        "ophthalmology",
        "therapy",
    ),
    "biochemistry": (
        "biochemistry",
        "biochemical",
        "protein",
        "proteins",
        "enzyme",
        "enzymatic",
        "metabolic",
        "metabolism",
        "receptor",
        "expression",
        "assay",
        "activity",
        "western blot",
    ),
    "chemistry": (
        "chemical",
        "chemistry",
        "compound",
        "compounds",
        "chemical engineering",
        "molecule",
        "molecules",
        "drug",
        "drugs",
        "ligand",
        "pharmacology",
    ),
}


@dataclass(frozen=True)
class PubMedLocalInspection:
    source_id: str
    status: str
    ready: bool
    enabled: bool = False
    schema_version: str | None = None
    source_version: str | None = None
    article_count: int = 0
    licensed_abstract_count: int = 0
    metadata_only_count: int = 0
    deleted_count: int = 0
    coverage_count: int = 0
    domain_filtered_count: int = 0
    pmc_license_overlay_count: int = 0
    literature_edge_count: int = 0
    source_file_count: int = 0
    source_kind_counts: dict[str, int] = dataclass_field(default_factory=dict)
    import_stats_by_source: dict[str, dict[str, int]] = dataclass_field(default_factory=dict)
    fts_status: str = "unavailable"
    actual_size_bytes: int | None = None
    checksum_verified: bool = False
    checksum_algorithm: str | None = None
    checksum_value: str | None = None
    input_checksum_status: str = "not_checked"
    input_checksum_verified_count: int = 0
    input_checksum_missing_count: int = 0
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
            "article_count": self.article_count,
            "licensed_abstract_count": self.licensed_abstract_count,
            "metadata_only_count": self.metadata_only_count,
            "deleted_count": self.deleted_count,
            "coverage_count": self.coverage_count,
            "domain_filtered_count": self.domain_filtered_count,
            "pmc_license_overlay_count": self.pmc_license_overlay_count,
            "literature_edge_count": self.literature_edge_count,
            "source_file_count": self.source_file_count,
            "source_kind_counts": dict(self.source_kind_counts),
            "import_stats_by_source": {
                source_kind: dict(counts)
                for source_kind, counts in self.import_stats_by_source.items()
            },
            "fts_status": self.fts_status,
            "actual_size_bytes": self.actual_size_bytes,
            "checksum_verified": self.checksum_verified,
            "checksum_algorithm": self.checksum_algorithm,
            "checksum_value": self.checksum_value if self.checksum_verified else None,
            "input_checksum_status": self.input_checksum_status,
            "input_checksum_verified_count": self.input_checksum_verified_count,
            "input_checksum_missing_count": self.input_checksum_missing_count,
            "message": self.message,
            "notices": list(self.warnings),
            "startup_download_allowed": False,
            "request_time_materialization_allowed": False,
            "secret_values_emitted": False,
            "local_path_values_emitted": False,
            "abstract_values_emitted": False,
        }


@dataclass(frozen=True)
class PubMedLocalMaterializationResult:
    ready: bool
    status: str
    schema_version: str = PUBMED_LOCAL_SCHEMA_VERSION
    article_count: int = 0
    licensed_abstract_count: int = 0
    metadata_only_count: int = 0
    deleted_count: int = 0
    coverage_count: int = 0
    domain_filtered_count: int = 0
    pmc_license_overlay_count: int = 0
    literature_edge_count: int = 0
    source_file_count: int = 0
    source_kind_counts: dict[str, int] = dataclass_field(default_factory=dict)
    import_stats_by_source: dict[str, dict[str, int]] = dataclass_field(default_factory=dict)
    fts_status: str = "unavailable"
    source_version: str | None = None
    checksum_algorithm: str = "sha256"
    checksum_value: str | None = None
    input_checksum_status: str = "not_checked"
    input_checksum_verified_count: int = 0
    input_checksum_missing_count: int = 0
    warnings: tuple[str, ...] = ()

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "status": self.status,
            "schema_version": self.schema_version,
            "article_count": self.article_count,
            "licensed_abstract_count": self.licensed_abstract_count,
            "metadata_only_count": self.metadata_only_count,
            "deleted_count": self.deleted_count,
            "coverage_count": self.coverage_count,
            "domain_filtered_count": self.domain_filtered_count,
            "pmc_license_overlay_count": self.pmc_license_overlay_count,
            "literature_edge_count": self.literature_edge_count,
            "source_file_count": self.source_file_count,
            "source_kind_counts": dict(self.source_kind_counts),
            "import_stats_by_source": {
                source_kind: dict(counts)
                for source_kind, counts in self.import_stats_by_source.items()
            },
            "fts_status": self.fts_status,
            "source_version": self.source_version,
            "checksum_algorithm": self.checksum_algorithm,
            "checksum_value": self.checksum_value,
            "input_checksum_status": self.input_checksum_status,
            "input_checksum_verified_count": self.input_checksum_verified_count,
            "input_checksum_missing_count": self.input_checksum_missing_count,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class PubMedLocalQueryCoverage:
    status: str
    completeness: str | None = None
    query: str | None = None
    result_count: int | None = None
    warnings: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return self.completeness == "complete"


@dataclass(frozen=True)
class PubMedSeedQuery:
    gene: str
    cdna: str | None = None
    transcript: str | None = None
    protein_change: str | None = None
    rsid: str | None = None
    genomic_hg38: str | None = None
    scope: str = "variant"

    @property
    def terms(self) -> tuple[tuple[str, str], ...]:
        terms: list[tuple[str, str]] = [("gene", self.gene)]
        for term_type, value in (
            ("cdna", self.cdna),
            ("transcript", self.transcript),
            ("protein", self.protein_change),
            ("rsid", self.rsid),
            ("genomic", self.genomic_hg38),
        ):
            if value:
                terms.append((term_type, value))
        return tuple(terms)

    @property
    def variant_terms(self) -> tuple[str, ...]:
        return tuple(value for term_type, value in self.terms if term_type != "gene")

    @property
    def source_query(self) -> str:
        visible = [self.gene]
        visible.extend(self.variant_terms)
        return " AND ".join(visible)

    @property
    def coverage_key(self) -> str:
        return _coverage_key(self.scope, self.gene, self.variant_terms)


@dataclass(frozen=True)
class PubMedSourceFileManifest:
    path: Path
    load_order: int
    source_kind: str
    source_format: str
    source_file_name: str
    size_bytes: int | None
    md5_status: str = "not_checked"

    @property
    def source_file_id(self) -> str:
        payload = "|".join(
            (
                self.source_kind,
                self.source_format,
                self.source_file_name,
                str(self.load_order),
                str(self.size_bytes or 0),
            )
        )
        return sha256(payload.encode("utf-8")).hexdigest()[:24]


@dataclass
class PubMedSourceFileImportStats:
    source_file: PubMedSourceFileManifest
    records_seen_count: int = 0
    article_imported_count: int = 0
    deleted_imported_count: int = 0
    domain_filtered_count: int = 0
    seed_filtered_count: int = 0
    invalid_record_count: int = 0
    pmc_license_overlay_count: int = 0
    literature_edge_imported_count: int = 0
    literature_edge_orphan_skipped_count: int = 0
    licensed_abstract_count: int = 0
    metadata_only_count: int = 0
    warnings: list[str] = dataclass_field(default_factory=list)

    def bump_imported_article(self, article: dict[str, Any]) -> None:
        if article["source_status"] == "deleted":
            self.deleted_imported_count += 1
            return
        self.article_imported_count += 1
        if article["abstract_policy"] == "licensed_text_persisted":
            self.licensed_abstract_count += 1
        else:
            self.metadata_only_count += 1


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


class PubMedLocalSchemaError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def inspect_pubmed_local_store(
    settings: Settings, *, verify_checksum: bool = True
) -> PubMedLocalInspection:
    return PubMedLocalStore(
        _resolve_path(settings, settings.pubmed_local_sqlite_path),
        manifest_path=_resolve_path(settings, settings.pubmed_local_manifest_path),
        enabled=settings.pubmed_local_enabled,
    ).inspect(verify_checksum=verify_checksum)


def classify_license_profile(value: str | None) -> str:
    text = _normalize_space(value or "").lower()
    if not text:
        return "unknown"
    if any(token in text for token in ("no-cc", "no cc", "no machine-readable")):
        return "unknown"
    if any(token in text for token in ("noncommercial", "non-commercial", "cc by-nc", "cc-by-nc")):
        return "noncommercial"
    if any(token in text for token in ("no derivatives", "no-derivatives", "cc by-nd", "cc-by-nd")):
        return "no_derivatives"
    if "cc0" in text or "creative commons zero" in text:
        return "cc0"
    if "public domain" in text or text in {"pd", "pdm"}:
        return "public_domain"
    if "u.s. government" in text or "us government" in text:
        return "us_government"
    if (
        "cc by-sa" in text
        or "cc-by-sa" in text
        or "creative commons attribution-sharealike" in text
    ):
        return "cc_by_sa"
    if "cc by" in text or "cc-by" in text or "creative commons attribution" in text:
        return "cc_by"
    if "copyright" in text or "©" in text:
        return "publisher_copyright"
    return "unknown"


def abstract_policy_for_license(license_profile: str, abstract_text: str | None) -> str:
    if not abstract_text:
        return "metadata_only_no_abstract"
    if license_profile in PERMISSIVE_LICENSE_PROFILES:
        return "licensed_text_persisted"
    return "metadata_only_license_unverified"


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
    with tempfile.TemporaryDirectory(prefix="eamos-pubmed-local-") as tmp_dir:
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


def read_seed_queries(path: Path) -> list[PubMedSeedQuery]:
    seeds: list[PubMedSeedQuery] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row_number, row in enumerate(reader, start=2):
            gene = str(row.get("gene") or "").strip().upper()
            scope = str(row.get("scope") or "variant").strip().lower()
            if not gene:
                raise ValueError(f"seed row {row_number} missing gene")
            if scope not in {"variant", "gene"}:
                raise ValueError(f"seed row {row_number} has unsupported scope")
            seed = PubMedSeedQuery(
                gene=gene,
                cdna=_clean_optional(row.get("cdna")),
                transcript=_clean_optional(row.get("transcript")),
                protein_change=_clean_optional(row.get("protein_change")),
                rsid=_clean_optional(row.get("rsid")),
                genomic_hg38=_clean_optional(row.get("genomic_hg38")),
                scope=scope,
            )
            if seed.scope == "variant" and not seed.variant_terms:
                raise ValueError(f"seed row {row_number} variant scope needs a variant identifier")
            seeds.append(seed)
    return seeds


def read_pmc_oa_license_map(paths: Iterable[Path]) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for path in paths:
        for row in _iter_pmc_license_rows(path):
            pmcid = _normalize_pmcid(
                row.get("pmcid")
                or row.get("pmc_id")
                or row.get("accession")
                or row.get("article_id")
            )
            if not pmcid:
                continue
            license_value = (
                row.get("license_code")
                or row.get("license")
                or row.get("license_type")
                or row.get("license_url")
            )
            license_profile = classify_license_profile(license_value)
            rows[pmcid] = {
                "license_profile": license_profile,
                "license_source": "pmc_oa_license_metadata",
                "license_raw": _normalize_space(str(license_value or "")),
            }
    return rows


def _iter_pmc_license_rows(path: Path) -> Iterable[dict[str, Any]]:
    if path.suffix.lower() in {".jsonl", ".ndjson"} or path.name.endswith(".jsonl.gz"):
        with _open_text(path) as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    yield row
        return

    with _open_text(path) as handle:
        sample = handle.read(4096)
        handle.seek(0)
        delimiter = "\t" if "\t" in sample and sample.count("\t") >= sample.count(",") else ","
        reader = csv.DictReader(handle, delimiter=delimiter)
        for row in reader:
            yield dict(row)


def _apply_pmc_license_overlay(
    article: dict[str, Any],
    pmc_license_map: dict[str, dict[str, str]],
) -> dict[str, Any]:
    pmcid = _normalize_pmcid(article.get("pmcid"))
    if not pmcid:
        return article
    overlay = pmc_license_map.get(pmcid)
    if not overlay:
        return article

    article = dict(article)
    prior_profile = str(article.get("license_profile") or "unknown")
    overlay_profile = overlay.get("license_profile") or "unknown"
    if overlay_profile != "unknown":
        article["license_profile"] = overlay_profile
        article["license_source"] = overlay.get("license_source") or "pmc_oa_license_metadata"
        transient_abstract = _clean_optional(article.get("_transient_abstract_text"))
        abstract_policy = abstract_policy_for_license(overlay_profile, transient_abstract)
        article["abstract_policy"] = abstract_policy
        if abstract_policy == "licensed_text_persisted" and transient_abstract:
            article["abstract_text"] = transient_abstract
            article["abstract_sha256"] = sha256(transient_abstract.encode("utf-8")).hexdigest()
        else:
            article["abstract_text"] = None
            article["abstract_sha256"] = None

    article["_pmc_license_overlay_used"] = True
    article["provenance_json"] = _merge_provenance(
        article.get("provenance_json"),
        {
            "pmc_license_overlay": {
                "pmcid": pmcid,
                "prior_license_profile": prior_profile,
                "license_profile": article.get("license_profile"),
                "text_policy": article.get("abstract_policy"),
            }
        },
    )
    return article


def _source_file_manifests(
    xml_files: Iterable[Path],
    jsonl_files: Iterable[Path],
    pubtator_edge_files: Iterable[Path],
    litvar_edge_files: Iterable[Path],
    *,
    xml_source_kind: str,
    checksum_summary: dict[str, Any],
) -> tuple[PubMedSourceFileManifest, ...]:
    md5_by_path = checksum_summary.get("by_path") if checksum_summary else {}
    manifests: list[PubMedSourceFileManifest] = []
    for load_order, path in enumerate(xml_files, start=1):
        manifests.append(
            PubMedSourceFileManifest(
                path=path,
                load_order=load_order,
                source_kind=_pubmed_xml_source_kind(path, xml_source_kind),
                source_format="pubmed_xml",
                source_file_name=path.name,
                size_bytes=_safe_size(path),
                md5_status=str(md5_by_path.get(str(path), "not_checked")),
            )
        )
    offset = len(manifests)
    for index, path in enumerate(jsonl_files, start=1):
        manifests.append(
            PubMedSourceFileManifest(
                path=path,
                load_order=offset + index,
                source_kind="import_jsonl",
                source_format="jsonl",
                source_file_name=path.name,
                size_bytes=_safe_size(path),
                md5_status="not_checked",
            )
        )
    offset = len(manifests)
    for index, path in enumerate(pubtator_edge_files, start=1):
        manifests.append(
            PubMedSourceFileManifest(
                path=path,
                load_order=offset + index,
                source_kind="pubtator_edges",
                source_format="literature_edge_jsonl",
                source_file_name=path.name,
                size_bytes=_safe_size(path),
                md5_status="not_checked",
            )
        )
    offset = len(manifests)
    for index, path in enumerate(litvar_edge_files, start=1):
        manifests.append(
            PubMedSourceFileManifest(
                path=path,
                load_order=offset + index,
                source_kind="litvar_edges",
                source_format="literature_edge_jsonl",
                source_file_name=path.name,
                size_bytes=_safe_size(path),
                md5_status="not_checked",
            )
        )
    return tuple(manifests)


def _pubmed_xml_source_kind(path: Path, mode: str) -> str:
    if mode in {"baseline", "pubmed_baseline"}:
        return "pubmed_baseline"
    if mode in {"update", "pubmed_update"}:
        return "pubmed_update"
    if mode == "pubmed_xml":
        return "pubmed_xml"
    folded = "/".join(part.lower() for part in path.parts)
    if "baseline" in folded:
        return "pubmed_baseline"
    if "update" in folded:
        return "pubmed_update"
    return "pubmed_xml"


def _iter_articles_from_source_file(
    source_file: PubMedSourceFileManifest,
    *,
    source_version: str,
    pmc_license_map: dict[str, dict[str, str]],
) -> Iterable[dict[str, Any]]:
    if source_file.source_format == "pubmed_xml":
        iterator = _parse_pubmed_xml(
            source_file.path,
            source_version=source_version,
            pmc_license_map=pmc_license_map,
        )
    else:
        iterator = _parse_pubmed_jsonl(
            source_file.path,
            source_version=source_version,
            pmc_license_map=pmc_license_map,
        )
    for article in iterator:
        yield _with_source_file_provenance(article, source_file)


def _with_source_file_provenance(
    article: dict[str, Any],
    source_file: PubMedSourceFileManifest,
) -> dict[str, Any]:
    provenance = _json_object(article.get("provenance_json"))
    provenance["source_file"] = {
        "file_name": source_file.source_file_name,
        "load_order": source_file.load_order,
        "source_kind": source_file.source_kind,
        "source_format": source_file.source_format,
    }
    article["provenance_json"] = json.dumps(provenance, sort_keys=True)
    return article


def _iter_literature_edges_from_source_file(
    source_file: PubMedSourceFileManifest,
    *,
    source_version: str,
) -> Iterable[dict[str, Any] | None]:
    with _open_text(source_file.path) as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                yield None
                continue
            if not isinstance(row, dict):
                yield None
                continue
            yield _literature_edge_from_jsonl_row(
                row,
                source_file=source_file,
                line_number=line_number,
                source_version=source_version,
            )


def _literature_edge_from_jsonl_row(
    row: dict[str, Any],
    *,
    source_file: PubMedSourceFileManifest,
    line_number: int,
    source_version: str,
) -> dict[str, Any] | None:
    pmid = str(row.get("pmid") or row.get("pubmed_id") or "").strip()
    if not re.fullmatch(r"\d{1,9}", pmid):
        return None

    source = _clean_optional(row.get("source")) or _literature_edge_source(source_file.source_kind)
    raw_entity_type = (
        row.get("entity_type")
        or row.get("type")
        or row.get("annotation_type")
        or ("variant" if source_file.source_kind == "litvar_edges" else "entity")
    )
    entity_type = _normalize_edge_entity_type(raw_entity_type)
    identifier = _clean_optional(
        row.get("identifier")
        or row.get("normalized_id")
        or row.get("concept_id")
        or row.get("variant_id")
        or row.get("rsid")
        or row.get("hgvs")
        or row.get("cdna")
        or row.get("variant")
    )
    matched_text = _clean_optional(
        row.get("matched_text") or row.get("mention") or row.get("text") or row.get("name")
    )
    normalized_identifier = _normalize_term(identifier or matched_text)
    normalized_mention = _normalize_term(matched_text)
    if not normalized_identifier and not normalized_mention:
        return None

    evidence_text = _clean_optional(
        row.get("evidence_text") or row.get("snippet") or row.get("context")
    )
    annotation_id = _clean_optional(row.get("annotation_id") or row.get("id"))
    provenance = {
        "source_channel": "literature_edge_jsonl",
        "line_number": line_number,
        "annotation_id": annotation_id,
        "source_file": {
            "file_name": source_file.source_file_name,
            "load_order": source_file.load_order,
            "source_kind": source_file.source_kind,
            "source_format": source_file.source_format,
        },
    }
    return {
        "edge_id": _literature_edge_id(
            source_file=source_file,
            line_number=line_number,
            pmid=pmid,
            source=source,
            entity_type=entity_type,
            identifier=identifier,
            matched_text=matched_text,
            annotation_id=annotation_id,
        ),
        "pmid": pmid,
        "source": source,
        "entity_type": entity_type,
        "identifier": identifier,
        "normalized_identifier": normalized_identifier,
        "matched_text": matched_text or "",
        "normalized_mention": normalized_mention,
        "section": _clean_optional(row.get("section")) or "",
        "offset_start": _optional_int(row.get("offset_start"), row.get("start")),
        "offset_end": _optional_int(row.get("offset_end"), row.get("end")),
        "relation_type": _clean_optional(row.get("relation_type") or row.get("relation")),
        "evidence_text": evidence_text,
        "source_url": _clean_optional(row.get("source_url") or row.get("url")),
        "source_file_id": source_file.source_file_id,
        "source_kind": source_file.source_kind,
        "source_file_name": source_file.source_file_name,
        "load_order": source_file.load_order,
        "source_version": source_version,
        "imported_at": _utc_now(),
        "provenance_json": json.dumps(provenance, sort_keys=True),
    }


def _normalize_edge_entity_type(value: Any) -> str:
    text = _normalize_space(str(value or "")).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    if text in {"mutation", "mutations", "sequence_variant", "dna_variant"}:
        return "variant"
    if text in {"genes", "gene_symbol"}:
        return "gene"
    return text or "entity"


def _literature_edge_source(source_kind: str) -> str:
    if source_kind == "litvar_edges":
        return "litvar2"
    if source_kind == "pubtator_edges":
        return "pubtator"
    return source_kind


def _literature_edge_id(
    *,
    source_file: PubMedSourceFileManifest,
    line_number: int,
    pmid: str,
    source: str,
    entity_type: str,
    identifier: str | None,
    matched_text: str | None,
    annotation_id: str | None,
) -> str:
    payload = "|".join(
        (
            source_file.source_file_id,
            str(line_number),
            pmid,
            source,
            entity_type,
            identifier or "",
            matched_text or "",
            annotation_id or "",
        )
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _optional_int(*values: Any) -> int | None:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _edge_seed_terms_by_pmid(
    source_files: Iterable[PubMedSourceFileManifest],
    seeds: list[PubMedSeedQuery],
    *,
    source_version: str,
) -> dict[str, dict[str, list[tuple[str, str, str]]]]:
    if not seeds:
        return {}
    edge_sources = [
        source_file
        for source_file in source_files
        if source_file.source_format == "literature_edge_jsonl"
    ]
    if not edge_sources:
        return {}
    by_pmid: dict[str, dict[str, list[tuple[str, str, str]]]] = {}
    for source_file in edge_sources:
        for edge in _iter_literature_edges_from_source_file(
            source_file,
            source_version=source_version,
        ):
            if edge is None:
                continue
            for seed in seeds:
                matched_terms = _edge_matched_seed_terms(edge, seed)
                if not matched_terms:
                    continue
                seed_terms = by_pmid.setdefault(edge["pmid"], {}).setdefault(
                    seed.coverage_key,
                    [],
                )
                seed_terms.extend(matched_terms)
    return {
        pmid: {
            coverage_key: _dedupe_term_matches(matches) for coverage_key, matches in by_seed.items()
        }
        for pmid, by_seed in by_pmid.items()
    }


def _edge_matched_seed_terms(
    edge: dict[str, Any],
    seed: PubMedSeedQuery,
) -> list[tuple[str, str, str]]:
    edge_type = str(edge.get("entity_type") or "")
    source = str(edge.get("source") or "edge")
    field = f"edge:{source}"
    normalized_values = {
        str(edge.get("normalized_identifier") or ""),
        str(edge.get("normalized_mention") or ""),
    }
    matches: list[tuple[str, str, str]] = []
    if edge_type == "gene" and _normalize_term(seed.gene) in normalized_values:
        matches.append(("gene", seed.gene, field))
    if edge_type in {"variant", "rsid", "snp"}:
        for term_type, value in seed.terms:
            if term_type == "gene":
                continue
            if _normalize_term(value) in normalized_values:
                matches.append((term_type, value, field))
    return matches


def _dedupe_term_matches(
    matches: Iterable[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    deduped: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for term_type, value, field in matches:
        key = (term_type, value, field)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    return deduped


def _iter_articles(
    xml_files: Iterable[Path],
    jsonl_files: Iterable[Path],
    *,
    source_version: str,
    pmc_license_map: dict[str, dict[str, str]] | None = None,
) -> Iterable[dict[str, Any]]:
    pmc_license_map = pmc_license_map or {}
    for path in xml_files:
        yield from _parse_pubmed_xml(
            path,
            source_version=source_version,
            pmc_license_map=pmc_license_map,
        )
    for path in jsonl_files:
        yield from _parse_pubmed_jsonl(
            path,
            source_version=source_version,
            pmc_license_map=pmc_license_map,
        )


def _parse_pubmed_jsonl(
    path: Path,
    *,
    source_version: str,
    pmc_license_map: dict[str, dict[str, str]],
) -> Iterable[dict[str, Any]]:
    with _open_text(path) as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            pmid = str(row.get("pmid") or "").strip()
            if not re.fullmatch(r"\d{1,9}", pmid):
                continue
            license_profile = classify_license_profile(
                str(row.get("license_profile") or row.get("copyright") or "")
            )
            abstract = _clean_optional(row.get("abstract"))
            abstract_policy = abstract_policy_for_license(license_profile, abstract)
            if abstract_policy != "licensed_text_persisted":
                abstract = None
            title = _clean_optional(row.get("title")) or "Untitled"
            article = {
                "pmid": pmid,
                "title": title,
                "authors_display": _clean_optional(row.get("authors")) or "",
                "journal": _clean_optional(row.get("journal")) or "",
                "year": _clean_optional(row.get("year"))
                or _year_from_date(row.get("publication_date")),
                "publication_date": _clean_optional(row.get("publication_date")),
                "doi": _clean_optional(row.get("doi")),
                "pmcid": _clean_optional(row.get("pmcid")),
                "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "source_status": _clean_optional(row.get("source_status")) or "available",
                "source_version": source_version,
                "fetched_at": _utc_now(),
                "license_profile": license_profile,
                "license_source": _clean_optional(row.get("license_source")) or "import_jsonl",
                "abstract_policy": abstract_policy,
                "abstract_text": abstract,
                "abstract_sha256": (
                    sha256(abstract.encode("utf-8")).hexdigest() if abstract else None
                ),
                "is_retracted": 1 if bool(row.get("is_retracted")) else 0,
                "mesh_terms": tuple(_string_list(row.get("mesh_terms"))),
                "chemical_terms": tuple(_string_list(row.get("chemical_terms"))),
                "publication_types": tuple(_string_list(row.get("publication_types"))),
                "language": _clean_optional(row.get("language")) or "",
                "provenance_json": json.dumps(
                    {
                        "source_channel": "import_jsonl",
                        "line_number": line_number,
                        "text_policy": abstract_policy,
                    },
                    sort_keys=True,
                ),
                "_transient_abstract_text": _clean_optional(row.get("abstract")) or "",
            }
            yield _apply_pmc_license_overlay(article, pmc_license_map)


def _parse_pubmed_xml(
    path: Path,
    *,
    source_version: str,
    pmc_license_map: dict[str, dict[str, str]],
) -> Iterable[dict[str, Any]]:
    with _open_binary(path) as handle:
        context = ET.iterparse(handle, events=("start", "end"))
        root: ET.Element | None = None
        for event, elem in context:
            if event == "start":
                if root is None:
                    root = elem
                continue
            if elem.tag == "PubmedArticle":
                article = _article_from_pubmed_xml(elem, source_version=source_version)
                if article is not None:
                    yield _apply_pmc_license_overlay(article, pmc_license_map)
                _clear_parsed_xml_element(elem, root)
            elif elem.tag == "DeleteCitation":
                for pmid_el in elem.findall(".//PMID"):
                    pmid = (pmid_el.text or "").strip()
                    if re.fullmatch(r"\d{1,9}", pmid):
                        yield _deleted_article(pmid, source_version=source_version)
                _clear_parsed_xml_element(elem, root)


def _clear_parsed_xml_element(elem: ET.Element, root: ET.Element | None) -> None:
    elem.clear()
    if root is not None and root is not elem:
        root.clear()


def _article_from_pubmed_xml(elem: ET.Element, *, source_version: str) -> dict[str, Any] | None:
    pmid = _find_text(elem, ".//MedlineCitation/PMID")
    if not pmid or not re.fullmatch(r"\d{1,9}", pmid):
        return None
    title = _normalize_space(_iter_text_first(elem, ".//Article/ArticleTitle")) or "Untitled"
    abstract_parts: list[str] = []
    for abstract_el in elem.findall(".//Article/Abstract/AbstractText"):
        text = _normalize_space("".join(abstract_el.itertext()))
        if not text:
            continue
        label = abstract_el.get("Label")
        abstract_parts.append(f"{label}: {text}" if label else text)
    abstract = " ".join(abstract_parts) if abstract_parts else None
    copyright_text = _find_text(elem, ".//Article/Abstract/CopyrightInformation")
    license_profile = classify_license_profile(copyright_text)
    abstract_policy = abstract_policy_for_license(license_profile, abstract)
    stored_abstract = abstract if abstract_policy == "licensed_text_persisted" else None
    journal = (
        _find_text(elem, ".//Article/Journal/ISOAbbreviation")
        or _find_text(elem, ".//Article/Journal/Title")
        or ""
    )
    publication_date = _publication_date(elem)
    year = (
        _year_from_date(publication_date)
        or _find_text(elem, ".//Article/Journal/JournalIssue/PubDate/Year")
        or ""
    )
    authors = _authors_display(elem)
    doi = _article_id(elem, "doi") or _elocation_id(elem, "doi")
    pmcid = _article_id(elem, "pmc")
    mesh_terms = tuple(
        _normalize_space("".join(item.itertext()))
        for item in elem.findall(".//MeshHeading/DescriptorName")
        if _normalize_space("".join(item.itertext()))
    )
    chemical_terms = tuple(
        _normalize_space("".join(item.itertext()))
        for item in elem.findall(".//Chemical/NameOfSubstance")
        if _normalize_space("".join(item.itertext()))
    )
    publication_types = tuple(
        _normalize_space("".join(item.itertext()))
        for item in elem.findall(".//PublicationTypeList/PublicationType")
        if _normalize_space("".join(item.itertext()))
    )
    language = _find_text(elem, ".//Article/Language") or ""
    provenance = {
        "source_channel": "pubmed_xml",
        "source_release": source_version,
        "text_policy": abstract_policy,
        "license_source": "CopyrightInformation" if copyright_text else "not_present",
    }
    return {
        "pmid": pmid,
        "title": title,
        "authors_display": authors,
        "journal": journal,
        "year": year,
        "publication_date": publication_date,
        "doi": doi,
        "pmcid": pmcid,
        "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "source_status": "available",
        "source_version": source_version,
        "fetched_at": _utc_now(),
        "license_profile": license_profile,
        "license_source": "pubmed_xml_copyright_information" if copyright_text else None,
        "abstract_policy": abstract_policy,
        "abstract_text": stored_abstract,
        "abstract_sha256": (
            sha256(stored_abstract.encode("utf-8")).hexdigest() if stored_abstract else None
        ),
        "is_retracted": 1 if _is_retracted(publication_types) else 0,
        "mesh_terms": mesh_terms,
        "chemical_terms": chemical_terms,
        "publication_types": publication_types,
        "language": language,
        "provenance_json": json.dumps(provenance, sort_keys=True),
        "_transient_abstract_text": abstract or "",
    }


def _deleted_article(pmid: str, *, source_version: str) -> dict[str, Any]:
    return {
        "pmid": pmid,
        "title": "Deleted PubMed citation",
        "authors_display": "",
        "journal": "",
        "year": "",
        "publication_date": None,
        "doi": None,
        "pmcid": None,
        "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "source_status": "deleted",
        "source_version": source_version,
        "fetched_at": _utc_now(),
        "license_profile": "metadata_only",
        "license_source": "pubmed_deletecitation",
        "abstract_policy": "metadata_only_no_abstract",
        "abstract_text": None,
        "abstract_sha256": None,
        "is_retracted": 0,
        "mesh_terms": (),
        "chemical_terms": (),
        "publication_types": (),
        "language": "",
        "provenance_json": json.dumps({"source_channel": "pubmed_xml_deletecitation"}),
    }


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


def _normalize_allowed_domains(values: Iterable[str]) -> set[str]:
    domains = {str(value).strip().lower() for value in values if str(value).strip()}
    return {domain for domain in domains if domain in BIOMEDICAL_DOMAIN_MARKERS}


def _article_matches_allowed_domains(article: dict[str, Any], allowed_domains: set[str]) -> bool:
    if not allowed_domains:
        return True
    if str(article.get("source_status") or "") != "available":
        return False
    if int(article.get("is_retracted") or 0):
        return False
    language = str(article.get("language") or "").strip().lower()
    if language and language not in DEFAULT_ALLOWED_LANGUAGES:
        return False
    publication_types = tuple(
        str(item).strip().lower() for item in article.get("publication_types") or ()
    )
    if any(item in DEFAULT_EXCLUDED_PUBLICATION_TYPES for item in publication_types):
        return False

    haystack = _domain_filter_text(article)
    if any(marker in haystack for marker in NON_BIOMEDICAL_NEGATIVE_MARKERS) and not any(
        _domain_matches(haystack, domain) for domain in allowed_domains
    ):
        return False
    return any(_domain_matches(haystack, domain) for domain in allowed_domains)


def _domain_matches(text: str, domain: str) -> bool:
    return any(
        _contains_domain_marker(text, marker)
        for marker in BIOMEDICAL_DOMAIN_MARKERS.get(domain, ())
    )


def _contains_domain_marker(text: str, marker: str) -> bool:
    marker = marker.strip().lower()
    if not marker:
        return False
    if " " in marker:
        return marker in text
    return re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", text) is not None


def _domain_filter_text(article: dict[str, Any]) -> str:
    fields = _article_search_fields(article)
    return _normalize_space(" ".join(fields.values())).lower()


def _matched_seed_terms(
    article: dict[str, Any],
    seeds: list[PubMedSeedQuery],
    *,
    extra_terms_by_seed: dict[str, list[tuple[str, str, str]]] | None = None,
) -> list[tuple[PubMedSeedQuery, list[tuple[str, str, str]]]]:
    if not seeds:
        return []
    fields = _article_search_fields(article)
    matches: list[tuple[PubMedSeedQuery, list[tuple[str, str, str]]]] = []
    for seed in seeds:
        extra_terms = tuple((extra_terms_by_seed or {}).get(seed.coverage_key, ()))
        extra_gene_match = next(
            (
                matched_field
                for term_type, _value, matched_field in extra_terms
                if term_type == "gene"
            ),
            None,
        )
        gene_match = _find_seed_term_field(seed.gene, "gene", fields)
        if gene_match is None:
            gene_match = extra_gene_match
        if gene_match is None:
            continue
        matched_terms: list[tuple[str, str, str]] = [("gene", seed.gene, gene_match)]
        variant_matched = False
        for term_type, value in seed.terms:
            if term_type == "gene":
                continue
            field = _find_seed_term_field(value, term_type, fields)
            if field is None:
                field = next(
                    (
                        matched_field
                        for extra_type, extra_value, matched_field in extra_terms
                        if extra_type == term_type
                        and _normalize_term(extra_value) == _normalize_term(value)
                    ),
                    None,
                )
            if field is None:
                continue
            matched_terms.append((term_type, value, field))
            variant_matched = True
        if seed.scope == "variant" and not variant_matched:
            continue
        matches.append((seed, matched_terms))
    return matches


def _article_search_fields(article: dict[str, Any]) -> dict[str, str]:
    return {
        "title": str(article.get("title") or ""),
        "abstract": str(
            article.get("abstract_text") or article.get("_transient_abstract_text") or ""
        ),
        "journal": str(article.get("journal") or ""),
        "authors": str(article.get("authors_display") or ""),
        "doi": str(article.get("doi") or ""),
        "pmcid": str(article.get("pmcid") or ""),
        "mesh": " ".join(article.get("mesh_terms") or ()),
        "chemical": " ".join(article.get("chemical_terms") or ()),
        "publication_types": " ".join(article.get("publication_types") or ()),
    }


def _find_seed_term_field(term: str, term_type: str, fields: dict[str, str]) -> str | None:
    if term_type == "gene":
        return _find_gene_term_field(term, fields)
    return _find_term_field(term, fields)


def _find_gene_term_field(term: str, fields: dict[str, str]) -> str | None:
    symbol = str(term or "").strip()
    if not symbol:
        return None
    for field, text in fields.items():
        if _contains_gene_symbol(text, symbol):
            return field
    return None


def _contains_gene_symbol(text: str | None, symbol: str) -> bool:
    if not text:
        return False
    token = re.escape(symbol)
    if symbol.isalpha() and len(symbol) <= 4:
        return re.search(rf"(?<![A-Za-z0-9]){token}(?![A-Za-z0-9])", text) is not None
    return re.search(rf"(?<![A-Za-z0-9]){token}(?![A-Za-z0-9])", text, re.IGNORECASE) is not None


def _find_term_field(term: str, fields: dict[str, str]) -> str | None:
    norm = _normalize_term(term)
    if not norm:
        return None
    for field, text in fields.items():
        if norm in _normalize_text_for_contains(text):
            return field
    return None


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


def _verify_input_md5_sidecars(xml_paths: Iterable[Path]) -> dict[str, Any]:
    verified = 0
    missing = 0
    mismatched = 0
    warnings: list[str] = []
    by_path: dict[str, str] = {}
    for path in xml_paths:
        sidecar = _md5_sidecar_path(path)
        if sidecar is None:
            missing += 1
            by_path[str(path)] = "missing"
            warnings.append("input_md5_sidecar_missing")
            continue
        expected = _read_md5_sidecar(sidecar)
        actual = _file_md5(path)
        if not expected or expected.lower() != actual.lower():
            mismatched += 1
            by_path[str(path)] = "mismatch"
            warnings.append("input_md5_sidecar_mismatch")
            continue
        verified += 1
        by_path[str(path)] = "verified"
    if mismatched:
        status = "mismatch"
    elif missing:
        status = "partial"
    else:
        status = "verified" if verified else "not_checked"
    return {
        "status": status,
        "verified_count": verified,
        "missing_count": missing,
        "mismatched_count": mismatched,
        "by_path": by_path,
        "warnings": tuple(_dedupe(warnings)),
    }


def _md5_sidecar_path(path: Path) -> Path | None:
    candidates = (
        path.with_name(f"{path.name}.md5"),
        path.with_suffix(f"{path.suffix}.md5"),
        path.with_suffix(".md5"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _read_md5_sidecar(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"\b([a-fA-F0-9]{32})\b", text)
    return match.group(1) if match else None


def _file_md5(path: Path) -> str:
    digest = md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_pmcid(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    if not text:
        return None
    text = re.sub(r"[^A-Z0-9]", "", text)
    if not text:
        return None
    return text if text.startswith("PMC") else f"PMC{text}"


def _merge_provenance(value: Any, patch: dict[str, Any]) -> str:
    base: dict[str, Any] = {}
    if isinstance(value, str) and value.strip():
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            decoded = {}
        if isinstance(decoded, dict):
            base = dict(decoded)
    base.update(patch)
    return json.dumps(base, sort_keys=True)


def _normalize_term(value: str | None) -> str:
    text = _normalize_space(value or "").lower()
    return re.sub(r"[^a-z0-9.>:_-]+", "", text)


def _normalize_text_for_contains(value: str | None) -> str:
    text = _normalize_space(value or "").lower()
    return re.sub(r"[^a-z0-9.>:_-]+", " ", text)


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _cdna_from_transcript_hgvs(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(":")[-1].strip() or None


def _gene_scope_query(gene: str) -> str:
    return f"{gene}[Gene Name]"


def _gene_scope_url(gene: str) -> str:
    return f"https://pubmed.ncbi.nlm.nih.gov/?term={gene}[gene]"


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
    if not isinstance(decoded, list):
        return []
    return [str(item) for item in decoded if isinstance(item, str)]


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
    else:
        decoded = value
    return dict(decoded) if isinstance(decoded, dict) else {}


def _json_dict_int(value: Any) -> dict[str, int]:
    decoded = _json_object(value)
    return {str(key): int(raw or 0) for key, raw in decoded.items()}


def _json_nested_int(value: Any) -> dict[str, dict[str, int]]:
    decoded = _json_object(value)
    nested: dict[str, dict[str, int]] = {}
    for key, raw in decoded.items():
        if not isinstance(raw, dict):
            continue
        nested[str(key)] = {
            str(child_key): int(child_value or 0) for child_key, child_value in raw.items()
        }
    return nested


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, Iterable):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _open_binary(path: Path):
    return gzip.open(path, "rb") if path.suffix == ".gz" else path.open("rb")


def _open_text(path: Path):
    return (
        gzip.open(path, "rt", encoding="utf-8")
        if path.suffix == ".gz"
        else path.open(
            "r",
            encoding="utf-8",
        )
    )


def _find_text(elem: ET.Element, path: str) -> str | None:
    item = elem.find(path)
    if item is None or item.text is None:
        return None
    return _normalize_space(item.text)


def _iter_text_first(elem: ET.Element, path: str) -> str:
    item = elem.find(path)
    return "".join(item.itertext()) if item is not None else ""


def _publication_date(elem: ET.Element) -> str | None:
    pub_date = elem.find(".//Article/Journal/JournalIssue/PubDate")
    if pub_date is None:
        return None
    year = _find_text(pub_date, "Year")
    month = _find_text(pub_date, "Month")
    day = _find_text(pub_date, "Day")
    if not year:
        medline = _find_text(pub_date, "MedlineDate")
        return medline
    parts = [year]
    if month:
        parts.append(month)
    if day:
        parts.append(day)
    return "-".join(parts)


def _year_from_date(value: Any) -> str:
    text = str(value or "")
    match = re.search(r"(\d{4})", text)
    return match.group(1) if match else ""


def _authors_display(elem: ET.Element) -> str:
    names: list[str] = []
    for author in elem.findall(".//Article/AuthorList/Author"):
        collective = _find_text(author, "CollectiveName")
        if collective:
            names.append(collective)
            continue
        last = _find_text(author, "LastName")
        initials = _find_text(author, "Initials")
        if last:
            names.append(f"{last} {initials}".strip())
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return f"{names[0]} et al."


def _article_id(elem: ET.Element, id_type: str) -> str | None:
    for item in elem.findall(".//PubmedData/ArticleIdList/ArticleId"):
        if (item.get("IdType") or "").lower() == id_type and item.text:
            return item.text.strip()
    return None


def _elocation_id(elem: ET.Element, id_type: str) -> str | None:
    for item in elem.findall(".//Article/ELocationID"):
        if (item.get("EIdType") or "").lower() == id_type and item.text:
            return item.text.strip()
    return None


def _is_retracted(publication_types: Iterable[str]) -> bool:
    return any("retract" in item.lower() for item in publication_types)


def _default_source_version() -> str:
    return f"{PUBMED_LOCAL_SOURCE_VERSION_PREFIX}-{datetime.now(timezone.utc).date().isoformat()}"


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
