from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
import gzip
from hashlib import sha256
import json
from pathlib import Path
import re
from threading import Lock
from typing import Any, Iterable, Mapping

from app.core.config import Settings
from app.services.sequence_context import genomic_variant_id_to_refseq_hgvs

COMPACT_COORDINATE_INDEX_SCHEMA_VERSION = "eamos.coordinate_index.v1"
COMPACT_COORDINATE_INDEX_SOURCE_ID = "eamos_compact_coordinate_index"
DEFAULT_COMPACT_COORDINATE_INDEX_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "bio_assets"
    / "transcripts"
    / "eamos-coordinate-index.latest.jsonl.gz"
)
DEFAULT_COMPACT_COORDINATE_INDEX_MAX_VARIANTS = 250_000
DEFAULT_COMPACT_COORDINATE_INDEX_MAX_TRANSCRIPTS = 100_000
_INDEX_LOAD_LOCK = Lock()


class CompactCoordinateIndexError(ValueError):
    """Structured error for malformed compact coordinate indexes."""

    def __init__(
        self,
        code: str,
        message: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


@dataclass(frozen=True)
class CompactCoordinateExon:
    number: int
    cds_start: int
    cds_end: int
    genomic_start: int
    genomic_end: int


@dataclass(frozen=True)
class CompactCoordinateTranscript:
    gene: str
    refseq_transcript: str
    ensembl_transcript: str | None
    chrom: str
    strand: str
    exons: tuple[CompactCoordinateExon, ...]
    transcript_aliases: tuple[str, ...] = ()
    ensembl_gene_id: str | None = None
    genome_build: str = "GRCh38"
    gene_start: int | None = None
    gene_end: int | None = None
    cds_length: int | None = None
    protein_length: int | None = None
    utr5_length: int | None = None
    utr3_length: int | None = None
    mrna_length: int | None = None
    translation_id: str | None = None
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompactCoordinateVariant:
    gene: str
    transcript: str
    cdna: str
    chrom: str
    pos: int
    ref: str
    alt: str
    genomic_hg38: str
    genomic_hgvs: str | None
    source: str = COMPACT_COORDINATE_INDEX_SOURCE_ID
    confidence: str = "high"
    accession: str | None = None
    clinvar_variation_id: str | None = None
    canonical_spdi: str | None = None
    protein_change: str | None = None
    provenance: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompactCoordinateIndexInspection:
    source_id: str
    status: str
    ready: bool
    schema_version: str | None = None
    artifact_version: str | None = None
    genome_build: str | None = None
    variant_count: int = 0
    transcript_count: int = 0
    actual_size_bytes: int | None = None
    checksum_verified: bool = False
    actual_sha256: str | None = None
    message: str | None = None
    warnings: tuple[str, ...] = ()

    def to_sanitized_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "ready": self.ready,
            "schema_version": self.schema_version,
            "artifact_version": self.artifact_version,
            "genome_build": self.genome_build,
            "variant_count": self.variant_count,
            "transcript_count": self.transcript_count,
            "actual_size_bytes": self.actual_size_bytes,
            "checksum_verified": self.checksum_verified,
            "actual_sha256": self.actual_sha256 if self.checksum_verified else None,
            "message": self.message,
            "status_notes": list(self.warnings),
            "source_runtime_scan_allowed": False,
            "startup_download_allowed": False,
        }


@dataclass(frozen=True)
class _LoadedCompactCoordinateIndex:
    metadata: dict[str, Any]
    variants_by_key: dict[str, CompactCoordinateVariant]
    transcripts_by_gene: dict[str, tuple[CompactCoordinateTranscript, ...]]
    transcripts_by_alias: dict[str, CompactCoordinateTranscript]
    accessions: dict[str, CompactCoordinateVariant]
    variation_ids: dict[str, CompactCoordinateVariant]
    inspection: CompactCoordinateIndexInspection


class CompactCoordinateIndex:
    """Read-only compact coordinate index for runtime coordinate resolution."""

    def __init__(
        self,
        path: Path | None = None,
        *,
        max_variants: int = DEFAULT_COMPACT_COORDINATE_INDEX_MAX_VARIANTS,
        max_transcripts: int = DEFAULT_COMPACT_COORDINATE_INDEX_MAX_TRANSCRIPTS,
    ) -> None:
        self.path = path or DEFAULT_COMPACT_COORDINATE_INDEX_PATH
        self.max_variants = max(0, int(max_variants))
        self.max_transcripts = max(0, int(max_transcripts))

    def inspection(
        self,
        *,
        verify_checksum: bool = False,
        load_records: bool = True,
    ) -> CompactCoordinateIndexInspection:
        if not load_records:
            return _inspect_index_metadata(self.path, verify_checksum=verify_checksum)

        loaded = _load_index(
            self.path,
            max_variants=self.max_variants,
            max_transcripts=self.max_transcripts,
        )
        if not verify_checksum or not self.path.is_file():
            return loaded.inspection
        return replace(
            loaded.inspection,
            checksum_verified=True,
            actual_sha256=_sha256_file(self.path),
        )

    def resolve_variant(
        self,
        *,
        gene: str,
        cdna: str,
        transcript: str | None = None,
        accession: str | None = None,
        clinvar_variation_id: str | None = None,
    ) -> CompactCoordinateVariant | None:
        loaded = _load_index(
            self.path,
            max_variants=self.max_variants,
            max_transcripts=self.max_transcripts,
        )
        if not loaded.inspection.ready:
            return None

        normalized_gene = _normalize_gene(gene)
        normalized_cdna = _normalize_cdna(cdna)
        keys = [
            _variant_key(normalized_gene, transcript, normalized_cdna),
            _variant_key(normalized_gene, None, normalized_cdna),
        ]
        for key in keys:
            row = loaded.variants_by_key.get(key)
            if row is not None:
                return row
        if accession:
            row = loaded.accessions.get(f"accession:{_normalize_accession(accession)}")
            if row is not None:
                return row
        if clinvar_variation_id:
            row = loaded.variation_ids.get(f"variation:{_digits(clinvar_variation_id)}")
            if row is not None:
                return row
        return None

    def transcript(
        self,
        *,
        gene: str,
        transcript: str | None = None,
    ) -> CompactCoordinateTranscript | None:
        loaded = _load_index(
            self.path,
            max_variants=self.max_variants,
            max_transcripts=self.max_transcripts,
        )
        if not loaded.inspection.ready:
            return None

        normalized_gene = _normalize_gene(gene)
        candidates = loaded.transcripts_by_gene.get(normalized_gene, ())
        if not candidates:
            return None
        if not transcript:
            return candidates[0]

        requested = _versionless(transcript)
        alias_match = loaded.transcripts_by_alias.get(f"{normalized_gene}:{requested}")
        if alias_match is not None:
            return alias_match
        return None


def compact_coordinate_index_from_settings(settings: Settings | None) -> CompactCoordinateIndex:
    if settings is None:
        return CompactCoordinateIndex()
    return CompactCoordinateIndex(
        _resolve_settings_path(
            settings,
            getattr(settings, "coordinate_resolver_compact_index_path", None),
        ),
        max_variants=getattr(
            settings,
            "coordinate_resolver_compact_index_max_variants",
            DEFAULT_COMPACT_COORDINATE_INDEX_MAX_VARIANTS,
        ),
        max_transcripts=getattr(
            settings,
            "coordinate_resolver_compact_index_max_transcripts",
            DEFAULT_COMPACT_COORDINATE_INDEX_MAX_TRANSCRIPTS,
        ),
    )


def inspect_compact_coordinate_index(
    settings: Settings,
    *,
    verify_checksum: bool = False,
    load_records: bool = True,
) -> CompactCoordinateIndexInspection:
    return compact_coordinate_index_from_settings(settings).inspection(
        verify_checksum=verify_checksum,
        load_records=load_records,
    )


def clear_compact_coordinate_index_cache() -> None:
    with _INDEX_LOAD_LOCK:
        _load_index_cached.cache_clear()


def _load_index(
    path: Path,
    *,
    max_variants: int,
    max_transcripts: int,
) -> _LoadedCompactCoordinateIndex:
    with _INDEX_LOAD_LOCK:
        return _load_index_cached(path, max(0, int(max_variants)), max(0, int(max_transcripts)))


@lru_cache(maxsize=2)
def _load_index_cached(
    path: Path,
    max_variants: int,
    max_transcripts: int,
) -> _LoadedCompactCoordinateIndex:
    if not path.exists():
        return _empty_loaded(
            CompactCoordinateIndexInspection(
                source_id=COMPACT_COORDINATE_INDEX_SOURCE_ID,
                status="missing",
                ready=False,
                message="compact coordinate index artifact is not present",
            )
        )
    if not path.is_file():
        return _empty_loaded(
            CompactCoordinateIndexInspection(
                source_id=COMPACT_COORDINATE_INDEX_SOURCE_ID,
                status="not_file",
                ready=False,
                message="compact coordinate index path is not a file",
            )
        )

    try:
        actual_size = path.stat().st_size
        loaded = _build_loaded_index(
            _iter_jsonl(path),
            max_variants=max_variants,
            max_transcripts=max_transcripts,
        )
    except CompactCoordinateIndexError as exc:
        return _empty_loaded(
            CompactCoordinateIndexInspection(
                source_id=COMPACT_COORDINATE_INDEX_SOURCE_ID,
                status=exc.code,
                ready=False,
                actual_size_bytes=path.stat().st_size,
                message=str(exc),
            )
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _empty_loaded(
            CompactCoordinateIndexInspection(
                source_id=COMPACT_COORDINATE_INDEX_SOURCE_ID,
                status="malformed",
                ready=False,
                actual_size_bytes=path.stat().st_size if path.exists() else None,
                message=type(exc).__name__,
            )
        )

    inspection = replace(
        loaded.inspection,
        actual_size_bytes=actual_size,
    )
    return _LoadedCompactCoordinateIndex(
        metadata=loaded.metadata,
        variants_by_key=loaded.variants_by_key,
        transcripts_by_gene=loaded.transcripts_by_gene,
        transcripts_by_alias=loaded.transcripts_by_alias,
        accessions=loaded.accessions,
        variation_ids=loaded.variation_ids,
        inspection=inspection,
    )


def _build_loaded_index(
    rows: Iterable[dict[str, Any]],
    *,
    max_variants: int,
    max_transcripts: int,
) -> _LoadedCompactCoordinateIndex:
    metadata: dict[str, Any] | None = None
    metadata_count = 0
    variant_count = 0
    transcript_count = 0
    variants_by_key: dict[str, CompactCoordinateVariant] = {}
    transcripts_by_gene: dict[str, list[CompactCoordinateTranscript]] = {}
    transcripts_by_alias: dict[str, CompactCoordinateTranscript] = {}
    accessions: dict[str, CompactCoordinateVariant] = {}
    variation_ids: dict[str, CompactCoordinateVariant] = {}

    for row in rows:
        record_type = row.get("record_type")
        if record_type == "metadata":
            metadata_count += 1
            metadata = dict(row)
            continue
        if record_type == "variant":
            variant_count += 1
            _enforce_index_limit(
                count=variant_count,
                limit=max_variants,
                record_type="variant",
            )
            variant = _variant_from_row(row)
            for key in (
                _variant_key(variant.gene, variant.transcript, variant.cdna),
                _variant_key(variant.gene, None, variant.cdna),
            ):
                _insert_unique(variants_by_key, key, variant, "duplicate_variant_key")
            if variant.accession:
                _insert_unique(
                    accessions,
                    f"accession:{_normalize_accession(variant.accession)}",
                    variant,
                    "duplicate_accession_key",
                )
            if variant.clinvar_variation_id:
                _insert_unique(
                    variation_ids,
                    f"variation:{_digits(variant.clinvar_variation_id)}",
                    variant,
                    "duplicate_variation_key",
                )
            continue
        if record_type == "transcript":
            transcript_count += 1
            _enforce_index_limit(
                count=transcript_count,
                limit=max_transcripts,
                record_type="transcript",
            )
            transcript = _transcript_from_row(row)
            transcripts_by_gene.setdefault(transcript.gene, []).append(transcript)
            for alias in (
                transcript.refseq_transcript,
                transcript.ensembl_transcript,
                *transcript.transcript_aliases,
            ):
                if alias:
                    _insert_unique(
                        transcripts_by_alias,
                        f"{transcript.gene}:{_versionless(alias)}",
                        transcript,
                        "duplicate_transcript_alias",
                    )
            continue
        raise CompactCoordinateIndexError(
            "unknown_record_type",
            "compact coordinate index contains an unknown record type",
            {"record_type": str(record_type)},
        )

    if metadata_count != 1 or metadata is None:
        raise CompactCoordinateIndexError(
            "metadata_record_invalid",
            "compact coordinate index requires exactly one metadata record",
        )
    if metadata.get("schema_version") != COMPACT_COORDINATE_INDEX_SCHEMA_VERSION:
        raise CompactCoordinateIndexError(
            "schema_version_mismatch",
            "compact coordinate index schema version is not supported",
        )

    if not variants_by_key and not transcripts_by_gene:
        raise CompactCoordinateIndexError(
            "empty_index",
            "compact coordinate index must contain variant or transcript records",
        )

    return _LoadedCompactCoordinateIndex(
        metadata=dict(metadata),
        variants_by_key=variants_by_key,
        transcripts_by_gene={gene: tuple(items) for gene, items in transcripts_by_gene.items()},
        transcripts_by_alias=transcripts_by_alias,
        accessions=accessions,
        variation_ids=variation_ids,
        inspection=CompactCoordinateIndexInspection(
            source_id=COMPACT_COORDINATE_INDEX_SOURCE_ID,
            status="ready",
            ready=True,
            schema_version=str(metadata.get("schema_version") or ""),
            artifact_version=_optional_str(metadata.get("artifact_version")),
            genome_build=_optional_str(metadata.get("genome_build")),
            variant_count=variant_count,
            transcript_count=transcript_count,
            warnings=_metadata_warnings(metadata),
        ),
    )


def _inspect_index_metadata(
    path: Path,
    *,
    verify_checksum: bool,
) -> CompactCoordinateIndexInspection:
    if not path.exists():
        return CompactCoordinateIndexInspection(
            source_id=COMPACT_COORDINATE_INDEX_SOURCE_ID,
            status="missing",
            ready=False,
            message="compact coordinate index artifact is not present",
        )
    if not path.is_file():
        return CompactCoordinateIndexInspection(
            source_id=COMPACT_COORDINATE_INDEX_SOURCE_ID,
            status="not_file",
            ready=False,
            message="compact coordinate index path is not a file",
        )

    actual_size = path.stat().st_size
    try:
        metadata = _read_metadata_row(path)
    except CompactCoordinateIndexError as exc:
        return CompactCoordinateIndexInspection(
            source_id=COMPACT_COORDINATE_INDEX_SOURCE_ID,
            status=exc.code,
            ready=False,
            actual_size_bytes=actual_size,
            message=str(exc),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return CompactCoordinateIndexInspection(
            source_id=COMPACT_COORDINATE_INDEX_SOURCE_ID,
            status="malformed",
            ready=False,
            actual_size_bytes=actual_size,
            message=type(exc).__name__,
        )

    if metadata.get("schema_version") != COMPACT_COORDINATE_INDEX_SCHEMA_VERSION:
        return CompactCoordinateIndexInspection(
            source_id=COMPACT_COORDINATE_INDEX_SOURCE_ID,
            status="schema_version_mismatch",
            ready=False,
            schema_version=_optional_str(metadata.get("schema_version")),
            actual_size_bytes=actual_size,
            message="compact coordinate index schema version is not supported",
        )

    variant_count = _metadata_count(metadata, "variant_count")
    transcript_count = _metadata_count(metadata, "transcript_count")
    warnings = list(_metadata_warnings(metadata))
    if "variant_count" not in metadata or "transcript_count" not in metadata:
        warnings.append("compact_coordinate_index_metadata_counts_unavailable")

    return CompactCoordinateIndexInspection(
        source_id=COMPACT_COORDINATE_INDEX_SOURCE_ID,
        status="ready",
        ready=True,
        schema_version=str(metadata.get("schema_version") or ""),
        artifact_version=_optional_str(metadata.get("artifact_version")),
        genome_build=_optional_str(metadata.get("genome_build")),
        variant_count=variant_count,
        transcript_count=transcript_count,
        actual_size_bytes=actual_size,
        checksum_verified=verify_checksum,
        actual_sha256=_sha256_file(path) if verify_checksum else None,
        warnings=tuple(warnings),
    )


def _read_metadata_row(path: Path) -> dict[str, Any]:
    for row in _iter_jsonl(path):
        if row.get("record_type") != "metadata":
            raise CompactCoordinateIndexError(
                "metadata_record_invalid",
                "compact coordinate index metadata record must be first",
            )
        return row
    raise CompactCoordinateIndexError(
        "metadata_record_invalid",
        "compact coordinate index requires a metadata record",
    )


def _enforce_index_limit(
    *,
    count: int,
    limit: int,
    record_type: str,
) -> None:
    if count <= limit:
        return
    raise CompactCoordinateIndexError(
        "index_too_large",
        "compact coordinate index exceeds the configured runtime load ceiling",
        {
            "record_type": record_type,
            "count": count,
            "limit": limit,
        },
    )


def _metadata_warnings(metadata: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(item) for item in metadata.get("warnings", []) if isinstance(item, str) and item
    )


def _metadata_count(metadata: Mapping[str, Any], field: str) -> int:
    value = metadata.get(field)
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    opener = gzip.open if _is_gzip_path_or_payload(path) else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise CompactCoordinateIndexError(
                    "record_not_object",
                    "compact coordinate index records must be objects",
                    {"line_number": line_number},
                )
            yield payload


def _is_gzip_path_or_payload(path: Path) -> bool:
    if path.suffix.lower() == ".gz":
        return True
    try:
        with path.open("rb") as handle:
            return handle.read(2) == b"\x1f\x8b"
    except OSError:
        return False


def _variant_from_row(row: Mapping[str, Any]) -> CompactCoordinateVariant:
    gene = _required_string(row, "gene").upper()
    transcript = _required_string(row, "transcript")
    cdna = _normalize_cdna(_required_string(row, "cdna"))
    chrom = _normalize_chrom(_required_string(row, "chrom"))
    pos = _required_int(row, "pos")
    ref = _required_allele(row, "ref")
    alt = _required_allele(row, "alt")
    genomic_hg38 = str(row.get("genomic_hg38") or f"{chrom}-{pos}-{ref}-{alt}")
    return CompactCoordinateVariant(
        gene=gene,
        transcript=transcript,
        cdna=cdna,
        chrom=chrom,
        pos=pos,
        ref=ref,
        alt=alt,
        genomic_hg38=genomic_hg38,
        genomic_hgvs=_optional_str(row.get("genomic_hgvs"))
        or genomic_variant_id_to_refseq_hgvs(genomic_hg38),
        source=str(row.get("source") or COMPACT_COORDINATE_INDEX_SOURCE_ID),
        confidence=str(row.get("confidence") or "high"),
        accession=_optional_str(row.get("accession")),
        clinvar_variation_id=_optional_str(row.get("clinvar_variation_id")),
        canonical_spdi=_optional_str(row.get("canonical_spdi")),
        protein_change=_optional_str(row.get("protein_change")),
        provenance=_string_tuple(row.get("provenance")),
        warnings=_string_tuple(row.get("warnings")),
    )


def _transcript_from_row(row: Mapping[str, Any]) -> CompactCoordinateTranscript:
    gene = _required_string(row, "gene").upper()
    exons = tuple(_exon_from_row(item) for item in _required_list(row, "exons"))
    if not exons:
        raise CompactCoordinateIndexError("transcript_has_no_exons", "transcript row has no exons")
    strand = _required_string(row, "strand")
    if strand not in {"+", "-"}:
        raise CompactCoordinateIndexError("invalid_strand", "transcript strand must be + or -")
    return CompactCoordinateTranscript(
        gene=gene,
        refseq_transcript=_required_string(row, "refseq_transcript"),
        ensembl_transcript=_optional_str(row.get("ensembl_transcript")),
        chrom=_normalize_chrom(_required_string(row, "chrom")),
        strand=strand,
        exons=exons,
        transcript_aliases=_string_tuple(row.get("transcript_aliases")),
        ensembl_gene_id=_optional_str(row.get("ensembl_gene_id")),
        genome_build=str(row.get("genome_build") or "GRCh38"),
        gene_start=_optional_int(row.get("gene_start")),
        gene_end=_optional_int(row.get("gene_end")),
        cds_length=_optional_int(row.get("cds_length")),
        protein_length=_optional_int(row.get("protein_length")),
        utr5_length=_optional_int(row.get("utr5_length")),
        utr3_length=_optional_int(row.get("utr3_length")),
        mrna_length=_optional_int(row.get("mrna_length")),
        translation_id=_optional_str(row.get("translation_id")),
        source_ids=_string_tuple(row.get("source_ids")),
    )


def _exon_from_row(row: object) -> CompactCoordinateExon:
    if not isinstance(row, Mapping):
        raise CompactCoordinateIndexError("invalid_exon", "transcript exons must be objects")
    return CompactCoordinateExon(
        number=_required_int(row, "number"),
        cds_start=_required_int(row, "cds_start"),
        cds_end=_required_int(row, "cds_end"),
        genomic_start=_required_int(row, "genomic_start"),
        genomic_end=_required_int(row, "genomic_end"),
    )


def _insert_unique(
    index: dict[str, Any],
    key: str,
    value: Any,
    error_code: str,
) -> None:
    existing = index.get(key)
    if existing is not None:
        if existing == value:
            return
        raise CompactCoordinateIndexError(
            error_code,
            "compact coordinate index contains duplicate keys",
            {"key": key},
        )
    index[key] = value


def _empty_loaded(
    inspection: CompactCoordinateIndexInspection,
) -> _LoadedCompactCoordinateIndex:
    return _LoadedCompactCoordinateIndex(
        metadata={},
        variants_by_key={},
        transcripts_by_gene={},
        transcripts_by_alias={},
        accessions={},
        variation_ids={},
        inspection=inspection,
    )


def _required_string(row: Mapping[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CompactCoordinateIndexError(
            "required_field_missing",
            "compact coordinate index record is missing a required string field",
            {"field": key},
        )
    return value.strip()


def _required_int(row: Mapping[str, Any], key: str) -> int:
    value = row.get(key)
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise CompactCoordinateIndexError(
            "required_field_invalid",
            "compact coordinate index record is missing a required integer field",
            {"field": key},
        ) from exc
    if parsed < 1:
        raise CompactCoordinateIndexError(
            "required_field_invalid",
            "compact coordinate index integer fields must be positive",
            {"field": key},
        )
    return parsed


def _required_list(row: Mapping[str, Any], key: str) -> list[Any]:
    value = row.get(key)
    if not isinstance(value, list):
        raise CompactCoordinateIndexError(
            "required_field_invalid",
            "compact coordinate index record is missing a required list field",
            {"field": key},
        )
    return value


def _required_allele(row: Mapping[str, Any], key: str) -> str:
    value = _required_string(row, key).upper()
    if not re.fullmatch(r"[ACGTN]+", value):
        raise CompactCoordinateIndexError(
            "invalid_allele",
            "compact coordinate index allele fields must contain only DNA bases",
            {"field": key},
        )
    return value


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _variant_key(gene: str, transcript: str | None, cdna: str) -> str:
    transcript_key = _versionless(transcript) if transcript else ""
    return f"variant:{_normalize_gene(gene)}:{transcript_key}:{_normalize_cdna(cdna).upper()}"


def _normalize_gene(gene: str) -> str:
    return str(gene or "").strip().upper()


def _normalize_cdna(cdna: str) -> str:
    text = re.sub(r"\s+", "", cdna.strip())
    if ":" in text:
        text = text.split(":", 1)[1]
    return text


def _normalize_chrom(chrom: str) -> str:
    normalized = chrom.strip()
    if normalized.lower().startswith("chr"):
        normalized = normalized[3:]
    normalized = normalized.upper()
    ncbi_match = re.fullmatch(r"NC_0*(\d+)\.\d+", normalized)
    if ncbi_match is not None:
        chrom_number = int(ncbi_match.group(1))
        if 1 <= chrom_number <= 22:
            return str(chrom_number)
        if chrom_number == 23:
            return "X"
        if chrom_number == 24:
            return "Y"
    if normalized in {"MT", "NC_012920.1"}:
        return "M"
    return normalized


def _versionless(transcript: str | None) -> str:
    text = str(transcript or "").strip()
    if not text:
        return ""
    return text.split(".", 1)[0].upper()


def _normalize_accession(accession: str) -> str:
    return accession.strip().upper().split(".", 1)[0]


def _digits(value: str) -> str:
    return "".join(ch for ch in str(value) if ch.isdigit())


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_settings_path(settings: Settings, path: Path | str | None) -> Path:
    resolved = Path(path) if path is not None else DEFAULT_COMPACT_COORDINATE_INDEX_PATH
    if resolved.is_absolute():
        return resolved
    return settings.backend_root / resolved
