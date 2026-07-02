from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.services.pubmed_local_constants import PUBMED_LOCAL_SCHEMA_VERSION


def _coverage_key(scope: str, gene: str, terms: tuple[str, ...]) -> str:
    return "|".join((scope, gene.upper(), *sorted(terms)))


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


class PubMedLocalSchemaError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
