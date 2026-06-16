from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
from hashlib import sha256
from io import TextIOWrapper
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from app.services.compact_coordinate_index import (
    COMPACT_COORDINATE_INDEX_SCHEMA_VERSION,
    CompactCoordinateIndex,
    clear_compact_coordinate_index_cache,
)
from app.services.eamos_coordinate_resolver import (
    _TranscriptRecord,
    _load_gff_transcript_models_for_genes,
    _merge_transcript_sources,
    _parse_gff_attributes,
)
from app.services.transcript_model import GENCODE_SOURCE_ID, MANE_SOURCE_ID

REFSEQ_SOURCE_ID = "ncbi_refseq_grch38_p14"
_CUSTOM_GFF_SOURCE_ID = "custom_gff_transcript_source"


@dataclass(frozen=True)
class CompactCoordinateIndexBuildResult:
    status: str
    ready: bool
    artifact_version: str | None = None
    genome_build: str | None = None
    requested_gene_count: int = 0
    gene_count: int = 0
    transcript_count: int = 0
    source_ids: tuple[str, ...] = ()
    schema_validated: bool = False
    actual_size_bytes: int | None = None
    actual_sha256: str | None = None
    warnings: tuple[str, ...] = ()

    def to_sanitized_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "ready": self.ready,
            "artifact_version": self.artifact_version,
            "genome_build": self.genome_build,
            "requested_gene_count": self.requested_gene_count,
            "gene_count": self.gene_count,
            "transcript_count": self.transcript_count,
            "source_ids": list(self.source_ids),
            "schema_validated": self.schema_validated,
            "actual_size_bytes": self.actual_size_bytes,
            "actual_sha256": self.actual_sha256,
            "warnings": list(self.warnings),
        }


def build_compact_coordinate_index(
    *,
    output_path: Path,
    gff_paths: Sequence[Path],
    genes: Iterable[str] = (),
    discover_all_genes: bool = False,
    artifact_version: str | None = None,
    genome_build: str = "GRCh38",
    generated_at: str | None = None,
) -> CompactCoordinateIndexBuildResult:
    """Build a compact transcript index from raw GFF inputs for offline materialization."""

    source_paths = tuple(path for path in gff_paths if path is not None)
    if not source_paths:
        return CompactCoordinateIndexBuildResult(status="source_unconfigured", ready=False)

    missing_paths = tuple(path for path in source_paths if not path.is_file())
    if missing_paths:
        return CompactCoordinateIndexBuildResult(
            status="source_missing",
            ready=False,
            warnings=("one_or_more_gff_sources_missing",),
        )

    normalized_genes = set(_normalize_genes(genes))
    if discover_all_genes:
        for path in source_paths:
            normalized_genes.update(_discover_gff_genes(path))

    requested_genes = tuple(sorted(normalized_genes))
    if not requested_genes:
        return CompactCoordinateIndexBuildResult(status="no_genes_requested", ready=False)

    source_ids = tuple(dict.fromkeys(_source_id_for_path(path) for path in source_paths))
    source_records = tuple(
        _load_gff_transcript_models_for_genes(path, requested_genes) for path in source_paths
    )
    merged = _merge_transcript_sources(*source_records)

    rows: list[dict[str, Any]] = [
        _metadata_row(
            artifact_version=artifact_version or _default_artifact_version(),
            genome_build=genome_build,
            source_ids=source_ids,
            generated_at=generated_at,
        )
    ]
    for gene in sorted(merged):
        for record in sorted(merged[gene], key=lambda item: _versionless(item.transcript)):
            row = _transcript_row(record)
            if row is not None:
                rows.append(row)

    transcript_count = len(rows) - 1
    gene_count = len({row["gene"] for row in rows[1:]})
    rows[0]["variant_count"] = 0
    rows[0]["transcript_count"] = transcript_count
    warnings: list[str] = []
    if gene_count < len(requested_genes):
        warnings.append("one_or_more_requested_genes_missing")

    if transcript_count == 0:
        return CompactCoordinateIndexBuildResult(
            status="no_transcripts_built",
            ready=False,
            artifact_version=str(rows[0]["artifact_version"]),
            genome_build=genome_build,
            requested_gene_count=len(requested_genes),
            source_ids=source_ids,
            warnings=tuple(warnings),
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_jsonl(rows, output_path)
    clear_compact_coordinate_index_cache()
    inspection = CompactCoordinateIndex(output_path).inspection(verify_checksum=True)
    artifact_sha256 = _sha256_file(output_path) if output_path.is_file() else None
    return CompactCoordinateIndexBuildResult(
        status="ready" if inspection.ready else inspection.status,
        ready=inspection.ready,
        artifact_version=str(rows[0]["artifact_version"]),
        genome_build=genome_build,
        requested_gene_count=len(requested_genes),
        gene_count=gene_count,
        transcript_count=transcript_count,
        source_ids=source_ids,
        schema_validated=inspection.ready,
        actual_size_bytes=output_path.stat().st_size if output_path.is_file() else None,
        actual_sha256=artifact_sha256,
        warnings=tuple(warnings),
    )


def discover_gff_genes(paths: Sequence[Path]) -> tuple[str, ...]:
    genes: set[str] = set()
    for path in paths:
        if path.is_file():
            genes.update(_discover_gff_genes(path))
    return tuple(sorted(genes))


def _metadata_row(
    *,
    artifact_version: str,
    genome_build: str,
    source_ids: tuple[str, ...],
    generated_at: str | None,
) -> dict[str, Any]:
    return {
        "record_type": "metadata",
        "schema_version": COMPACT_COORDINATE_INDEX_SCHEMA_VERSION,
        "artifact_version": artifact_version,
        "genome_build": genome_build,
        "source_ids": list(source_ids),
        "build_mode": "offline_raw_gff_to_compact_index",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "raw_gff_runtime_scan_allowed": False,
        "startup_download_allowed": False,
    }


def _transcript_row(record: _TranscriptRecord) -> dict[str, Any] | None:
    exons = _coding_exon_rows(record)
    if not exons:
        return None

    transcript_bounds = [
        coordinate for exon in record.exons for coordinate in (exon.genomic_start, exon.genomic_end)
    ]
    cds_length = record.cds_transcript_end - record.cds_transcript_start + 1
    mrna_length = sum(exon.transcript_end - exon.transcript_start + 1 for exon in record.exons)
    row: dict[str, Any] = {
        "record_type": "transcript",
        "gene": record.gene,
        "refseq_transcript": record.transcript,
        "transcript_aliases": list(_transcript_aliases_for_record(record)),
        "chrom": record.chrom,
        "strand": record.strand,
        "gene_start": min(transcript_bounds),
        "gene_end": max(transcript_bounds),
        "cds_length": cds_length,
        "mrna_length": mrna_length,
        "source_ids": list(_source_ids_for_record(record)),
        "exons": exons,
    }
    return row


def _coding_exon_rows(record: _TranscriptRecord) -> list[dict[str, int]]:
    exons: list[dict[str, int]] = []
    for exon in record.exons:
        coding_start = max(exon.transcript_start, record.cds_transcript_start)
        coding_end = min(exon.transcript_end, record.cds_transcript_end)
        if coding_start > coding_end:
            continue

        left = _transcript_position_to_genomic(exon, coding_start, record.strand)
        right = _transcript_position_to_genomic(exon, coding_end, record.strand)
        exons.append(
            {
                "number": exon.number,
                "cds_start": coding_start - record.cds_transcript_start + 1,
                "cds_end": coding_end - record.cds_transcript_start + 1,
                "genomic_start": min(left, right),
                "genomic_end": max(left, right),
            }
        )
    return sorted(exons, key=lambda exon: exon["cds_start"])


def _transcript_position_to_genomic(exon: Any, position: int, strand: str) -> int:
    offset = position - exon.transcript_start
    if strand == "-":
        return exon.genomic_end - offset
    return exon.genomic_start + offset


def _discover_gff_genes(path: Path) -> tuple[str, ...]:
    genes: set[str] = set()
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            columns = line.rstrip("\n").split("\t")
            if len(columns) != 9:
                continue
            attrs = _parse_gff_attributes(columns[8])
            gene = str(attrs.get("gene") or "").strip().upper()
            if gene:
                genes.add(gene)
    return tuple(sorted(genes))


def _source_id_for_path(path: Path) -> str:
    name = path.name.lower()
    if "mane" in name:
        return MANE_SOURCE_ID
    if "gcf_000001405.40" in name or "refseq" in name:
        return REFSEQ_SOURCE_ID
    if "gencode" in name:
        return GENCODE_SOURCE_ID
    return _CUSTOM_GFF_SOURCE_ID


def _source_ids_for_record(record: _TranscriptRecord) -> tuple[str, ...]:
    source = record.source.lower()
    if "mane" in source:
        return (MANE_SOURCE_ID,)
    if "refseq" in source:
        return (REFSEQ_SOURCE_ID,)
    if "gencode" in source:
        return (GENCODE_SOURCE_ID,)
    return (_CUSTOM_GFF_SOURCE_ID,)


def _transcript_aliases_for_record(record: _TranscriptRecord) -> tuple[str, ...]:
    aliases = []
    for alias in record.transcript_aliases:
        normalized = alias.strip()
        if not normalized:
            continue
        if normalized.upper() == "MANE SELECT":
            continue
        if _versionless(normalized) == _versionless(record.transcript):
            continue
        aliases.append(normalized)
    return tuple(dict.fromkeys(aliases))


def _normalize_genes(genes: Iterable[str]) -> tuple[str, ...]:
    normalized: set[str] = set()
    for gene in genes:
        for item in str(gene).replace(",", "\n").splitlines():
            value = item.strip().upper()
            if value:
                normalized.add(value)
    return tuple(sorted(normalized))


def _write_jsonl(rows: Sequence[Mapping[str, Any]], path: Path) -> None:
    if path.suffix.lower() == ".gz":
        with path.open("wb") as raw_handle:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, mtime=0) as gzip_handle:
                with TextIOWrapper(gzip_handle, encoding="utf-8") as text_handle:
                    _write_rows(rows, text_handle)
        return

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        _write_rows(rows, handle)


def _write_rows(rows: Sequence[Mapping[str, Any]], handle: Any) -> None:
    for row in rows:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")))
        handle.write("\n")


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _default_artifact_version() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _versionless(value: str | None) -> str:
    if not value:
        return ""
    return str(value).split(".", 1)[0]
