from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import gzip
from hashlib import sha256
from pathlib import Path
import re
import threading
from typing import Any, Iterable, Mapping

from app.core.paths import find_project_root, repo_relative_path
from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry
from app.data_sources.registry import LicenseStatus
from app.schemas.run import CuratedVariantsDistribution
from app.services.indexed_sources import (
    IndexedSourceError,
    IndexedVcfRecord,
    PysamIndexedVcfReader,
)

CLINVAR_SOURCE_ID = "ncbi_clinvar_vcf"
DEFAULT_CLINVAR_VCF_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "data_sources" / "clinvar_tiny.vcf"
)
CLINVAR_DISTRIBUTION_ROWS = ("pathogenic", "vus", "benign")
CLINVAR_DISTRIBUTION_COLUMNS = ("lof", "missense", "noncoding", "synonymous")


class ClinVarLocalError(ValueError):
    """Structured error for malformed local ClinVar VCF fixtures."""

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
class ClinVarLocalProvenance:
    source_id: str
    source_version: str | None
    file_date: str | None
    checksum_algorithm: str
    checksum: str
    relative_path: str
    record_id: str | None = None


@dataclass(frozen=True)
class ClinVarLocalRecord:
    chrom: str
    position: int
    ref: str
    alt: str
    gnomad_variant_id: str
    record_id: str
    variation_id: str
    accession: str
    classification: str
    review_status: str
    conditions: tuple[str, ...]
    condition_summary: str
    hgvs_aliases: tuple[str, ...]
    gene_symbols: tuple[str, ...]
    provenance: ClinVarLocalProvenance


@dataclass(frozen=True)
class ClinVarLocalLookup:
    available: bool
    record: ClinVarLocalRecord | None
    unavailable_reason: str | None = None
    warnings: tuple[str, ...] = ()


class ClinVarLocalStore:
    """Fixture-first local ClinVar VCF adapter.

    This store proves parsing and lookup semantics for tiny VCF fixtures. It is
    deliberately not wired into the live HTTP ClinVar tool yet.
    """

    def __init__(
        self,
        vcf_path: Path | None = None,
        registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    ) -> None:
        self._vcf_path = vcf_path or DEFAULT_CLINVAR_VCF_FIXTURE_PATH
        self._source_provenance = _source_provenance(self._vcf_path, registry)
        self._records = parse_clinvar_vcf(
            self._vcf_path,
            provenance=self._source_provenance,
        )
        self._records_by_key: dict[tuple[str, int, str, str], ClinVarLocalRecord] = {}
        self._records_by_accession: dict[str, ClinVarLocalRecord] = {}
        for record in self._records:
            key = _variant_key(record.chrom, record.position, record.ref, record.alt)
            existing_key_record = self._records_by_key.get(key)
            if existing_key_record is not None:
                raise ClinVarLocalError(
                    "duplicate_clinvar_variant_identity",
                    "ClinVar fixture has duplicate variant identities",
                    {
                        "variant_id": record.gnomad_variant_id,
                        "first_record_id": existing_key_record.record_id,
                        "second_record_id": record.record_id,
                    },
                )
            self._records_by_key[key] = record
            for accession in {record.accession, record.variation_id, record.record_id}:
                normalized_accession = _normalize_accession(accession)
                existing_accession_record = self._records_by_accession.get(normalized_accession)
                if existing_accession_record is not None and existing_accession_record != record:
                    raise ClinVarLocalError(
                        "duplicate_clinvar_accession",
                        "ClinVar fixture has duplicate accession or Variation ID identities",
                        {
                            "accession": normalized_accession,
                            "first_variant_id": existing_accession_record.gnomad_variant_id,
                            "second_variant_id": record.gnomad_variant_id,
                        },
                    )
                self._records_by_accession[normalized_accession] = record
        self._contig_aliases = _build_alias_map(record.chrom for record in self._records)

    def provenance(self) -> ClinVarLocalProvenance:
        return self._source_provenance

    def source_path(self) -> Path:
        return self._vcf_path

    def source_status(self) -> str:
        return "fixture" if _is_fixture_path(self._vcf_path) else "local"

    def records(self) -> tuple[ClinVarLocalRecord, ...]:
        return self._records

    def lookup_variant_id(self, variant_id: str) -> ClinVarLocalLookup:
        parsed = _parse_gnomad_variant_id(variant_id)
        if parsed is None:
            return ClinVarLocalLookup(
                available=False,
                record=None,
                unavailable_reason="invalid_variant_id",
                warnings=("clinvar_local_invalid_variant_id",),
            )
        chrom, position, ref, alt = parsed
        return self.lookup(chrom=chrom, position=position, ref=ref, alt=alt)

    def lookup_accession(self, accession: str) -> ClinVarLocalLookup:
        record = self._records_by_accession.get(_normalize_accession(accession))
        if record is None:
            return ClinVarLocalLookup(
                available=False,
                record=None,
                unavailable_reason="accession_not_found",
                warnings=("clinvar_local_accession_not_found",),
            )
        return ClinVarLocalLookup(available=True, record=record)

    def lookup(self, *, chrom: str, position: int, ref: str, alt: str) -> ClinVarLocalLookup:
        if position < 1:
            return ClinVarLocalLookup(
                available=False,
                record=None,
                unavailable_reason="invalid_coordinates",
                warnings=("clinvar_local_invalid_coordinates",),
            )
        try:
            normalized_chrom = self._contig_aliases[_normalize_contig_alias(chrom)]
        except KeyError:
            return ClinVarLocalLookup(
                available=False,
                record=None,
                unavailable_reason="contig_not_found",
                warnings=("clinvar_local_contig_not_found",),
            )
        key = _variant_key(normalized_chrom, position, ref, alt)
        record = self._records_by_key.get(key)
        if record is not None:
            return ClinVarLocalLookup(available=True, record=record)
        if any(
            item.chrom == normalized_chrom and item.position == position for item in self._records
        ):
            return ClinVarLocalLookup(
                available=False,
                record=None,
                unavailable_reason="allele_mismatch",
                warnings=("clinvar_local_allele_mismatch",),
            )
        return ClinVarLocalLookup(
            available=False,
            record=None,
            unavailable_reason="variant_not_found",
            warnings=("clinvar_local_variant_not_found",),
        )


class ClinVarIndexedLocalAdapter:
    """Bounded ClinVar bgzip/tabix adapter for exact variant lookups.

    This adapter intentionally exposes no gene-wide scan API. It is suitable for
    request-path local evidence because each lookup is a one-position indexed
    fetch with a record cap.
    """

    def __init__(
        self,
        *,
        vcf_path: Path,
        index_path: Path,
        registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
        reader_factory: Any | None = None,
    ) -> None:
        self._vcf_path = vcf_path
        self._index_path = index_path
        self._registry = registry
        self._reader_factory = reader_factory or _default_indexed_reader_factory
        self._reader_lock = threading.RLock()
        self._reader_path: tuple[Path, Path] | None = None
        self._reader: Any | None = None

    @classmethod
    def from_settings(
        cls,
        settings: object,
        *,
        registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
        reader_factory: Any | None = None,
    ) -> "ClinVarIndexedLocalAdapter":
        vcf_path = _resolve_backend_path(
            settings, Path(getattr(settings, "clinvar_runtime_vcf_path"))
        )
        index_path = _resolve_backend_path(
            settings,
            Path(getattr(settings, "clinvar_runtime_index_path")),
        )
        return cls(
            vcf_path=vcf_path,
            index_path=index_path,
            registry=registry,
            reader_factory=reader_factory,
        )

    def lookup_variant_id(self, variant_id: str) -> ClinVarLocalLookup:
        parsed = _parse_gnomad_variant_id(variant_id)
        if parsed is None:
            return ClinVarLocalLookup(
                available=False,
                record=None,
                unavailable_reason="invalid_variant_id",
                warnings=("clinvar_local_invalid_variant_id",),
            )
        chrom, position, ref, alt = parsed
        return self.lookup(chrom=chrom, position=position, ref=ref, alt=alt)

    def lookup(self, *, chrom: str, position: int, ref: str, alt: str) -> ClinVarLocalLookup:
        if position < 1:
            return ClinVarLocalLookup(
                available=False,
                record=None,
                unavailable_reason="invalid_coordinates",
                warnings=("clinvar_local_invalid_coordinates",),
            )
        try:
            with self._reader_lock:
                reader = self._reader_for_ready_asset()
                indexed_records = reader.query_position(chrom, position)
        except IndexedSourceError as exc:
            return ClinVarLocalLookup(
                available=False,
                record=None,
                unavailable_reason=exc.code,
                warnings=(f"clinvar_local_{exc.code}",),
            )

        requested_key = _variant_key(chrom, position, ref, alt)
        records_at_position: list[ClinVarLocalRecord] = []
        try:
            for indexed_record in indexed_records:
                records_at_position.extend(
                    _records_from_indexed_vcf_record(
                        indexed_record,
                        provenance=_runtime_source_provenance(self._vcf_path, self._registry),
                    )
                )
        except ClinVarLocalError as exc:
            return ClinVarLocalLookup(
                available=False,
                record=None,
                unavailable_reason=exc.code,
                warnings=(f"clinvar_local_{exc.code}",),
            )

        matches = [
            record
            for record in records_at_position
            if _variant_key(record.chrom, record.position, record.ref, record.alt) == requested_key
        ]
        if len(matches) == 1:
            return ClinVarLocalLookup(available=True, record=matches[0])
        if len(matches) > 1:
            return ClinVarLocalLookup(
                available=False,
                record=None,
                unavailable_reason="duplicate_variant_records",
                warnings=("clinvar_local_duplicate_variant_records",),
            )
        if records_at_position:
            return ClinVarLocalLookup(
                available=False,
                record=None,
                unavailable_reason="allele_mismatch",
                warnings=("clinvar_local_allele_mismatch",),
            )
        return ClinVarLocalLookup(
            available=False,
            record=None,
            unavailable_reason="variant_not_found",
            warnings=("clinvar_local_variant_not_found",),
        )

    def close(self) -> None:
        with self._reader_lock:
            reader = self._reader
            self._reader = None
            self._reader_path = None
            close = getattr(reader, "close", None)
            if callable(close):
                close()

    def _reader_for_ready_asset(self) -> Any:
        reader_path = (self._vcf_path, self._index_path)
        if self._reader is None or self._reader_path != reader_path:
            self.close()
            self._reader = self._reader_factory(self._vcf_path, self._index_path)
            self._reader_path = reader_path
        return self._reader


def build_clinvar_gene_distribution(
    gene: str,
    *,
    store: ClinVarLocalStore | None = None,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    query_variant_id: str | None = None,
) -> CuratedVariantsDistribution:
    """Aggregate all installed local ClinVar records for a gene into report buckets."""

    clinvar_store = store or ClinVarLocalStore(registry=registry)
    gene_symbol = gene.strip().upper()
    records = tuple(
        record
        for record in clinvar_store.records()
        if gene_symbol and gene_symbol in record.gene_symbols
    )
    source_record = registry.get(CLINVAR_SOURCE_ID)
    counts: Counter[str] = Counter()
    for record in records:
        row = _classification_bucket(record.classification)
        column = _variant_effect_bucket(record)
        counts[f"{row}_{column}"] += 1

    cells = {
        f"{row}_{column}": int(counts.get(f"{row}_{column}", 0))
        for row in CLINVAR_DISTRIBUTION_ROWS
        for column in CLINVAR_DISTRIBUTION_COLUMNS
    }
    row_totals = {
        row: sum(cells[f"{row}_{column}"] for column in CLINVAR_DISTRIBUTION_COLUMNS)
        for row in CLINVAR_DISTRIBUTION_ROWS
    }
    total = sum(row_totals.values())
    warnings = list(_distribution_warnings(gene_symbol, clinvar_store, total))
    query_record, query_warnings = _query_record_for_distribution(
        clinvar_store,
        query_variant_id=query_variant_id,
        gene_symbol=gene_symbol,
    )
    warnings.extend(query_warnings)
    query_cell = None
    if query_record is not None:
        query_cell = (
            f"{_classification_bucket(query_record.classification)}_"
            f"{_variant_effect_bucket(query_record)}"
        )
    provenance = clinvar_store.provenance()
    source_status = clinvar_store.source_status()
    source_label = "fixture" if source_status == "fixture" else "local"
    subtitle = (
        f"{total:,} ClinVar {source_label} record{'s' if total != 1 else ''}"
        f" for {gene_symbol or 'gene'}"
    )
    return CuratedVariantsDistribution(
        cells=cells,
        row_totals=row_totals,
        total=total,
        subtitle=subtitle,
        reading=_distribution_reading(gene_symbol, row_totals, cells, total, source_status),
        source_status=source_status,
        source_id=CLINVAR_SOURCE_ID,
        source_version=provenance.source_version,
        source_url=source_record.source_url,
        public_serialization_allowed=(
            source_record.license_status is LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW
        ),
        launch_gate=None,
        license_gate=None,
        query_cell=query_cell,
        query_variant_id=query_record.gnomad_variant_id if query_record is not None else None,
        query_accession=query_record.accession if query_record is not None else None,
        query_classification=query_record.classification if query_record is not None else None,
        warnings=warnings,
    )


def parse_clinvar_vcf(
    path: Path,
    *,
    provenance: ClinVarLocalProvenance,
) -> tuple[ClinVarLocalRecord, ...]:
    lines = _read_fixture_lines(path)
    file_date = _file_date(lines) or provenance.file_date
    header: list[str] | None = None
    records: list[ClinVarLocalRecord] = []
    for row_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        if line.startswith("##"):
            continue
        if line.startswith("#CHROM"):
            header = line.lstrip("#").split("\t")
            continue
        if header is None:
            raise ClinVarLocalError(
                "vcf_missing_header",
                "ClinVar VCF fixture row appeared before the #CHROM header",
                {"path": str(path), "row": row_number},
            )
        records.extend(
            _parse_vcf_row(
                line,
                row_number=row_number,
                header=header,
                provenance=ClinVarLocalProvenance(
                    source_id=provenance.source_id,
                    source_version=provenance.source_version,
                    file_date=file_date,
                    checksum_algorithm=provenance.checksum_algorithm,
                    checksum=provenance.checksum,
                    relative_path=provenance.relative_path,
                ),
            )
        )
    if header is None:
        raise ClinVarLocalError(
            "vcf_missing_header",
            "ClinVar VCF fixture must include a #CHROM header",
            {"path": str(path)},
        )
    if not records:
        raise ClinVarLocalError(
            "empty_clinvar_vcf_fixture",
            "ClinVar VCF fixture must contain at least one variant row",
            {"path": str(path)},
        )
    return tuple(records)


def _parse_vcf_row(
    line: str,
    *,
    row_number: int,
    header: list[str],
    provenance: ClinVarLocalProvenance,
) -> tuple[ClinVarLocalRecord, ...]:
    fields = line.rstrip("\n").split("\t")
    if len(fields) != len(header):
        raise ClinVarLocalError(
            "malformed_clinvar_vcf_row",
            "ClinVar VCF row field count does not match header",
            {"row": row_number, "field_count": len(fields), "header_count": len(header)},
        )
    row = dict(zip(header, fields, strict=True))
    try:
        position = int(_required(row, "POS", row_number=row_number))
    except ValueError as exc:
        raise ClinVarLocalError(
            "malformed_clinvar_vcf_row",
            "ClinVar VCF POS must be an integer",
            {"row": row_number, "position": row.get("POS")},
        ) from exc
    chrom = _normalize_contig_alias(_required(row, "CHROM", row_number=row_number))
    ref = _normalize_allele(_required(row, "REF", row_number=row_number))
    alts = tuple(
        _normalize_allele(alt) for alt in _required(row, "ALT", row_number=row_number).split(",")
    )
    if position < 1 or not ref or not alts or any(not alt for alt in alts):
        raise ClinVarLocalError(
            "malformed_clinvar_vcf_row",
            "ClinVar VCF row has invalid coordinates or alleles",
            {"row": row_number, "chrom": chrom, "position": position, "ref": ref, "alts": alts},
        )
    info = _parse_info(_required(row, "INFO", row_number=row_number), row_number=row_number)
    record_id = _record_id(row.get("ID"), info)
    classification = _decode_required_info(info, "CLNSIG", row_number)
    review_status = _decode_required_info(info, "CLNREVSTAT", row_number)
    conditions = _condition_values(info.get("CLNDN"))
    hgvs_aliases = _hgvs_aliases(info)
    gene_symbols = _gene_symbols(info.get("GENEINFO"))
    accession = _normalize_vcv_accession(record_id)
    variation_id = _variation_id(accession)
    return tuple(
        ClinVarLocalRecord(
            chrom=chrom,
            position=position,
            ref=ref,
            alt=alt,
            gnomad_variant_id=_gnomad_variant_id(chrom, position, ref, alt),
            record_id=record_id,
            variation_id=variation_id,
            accession=accession,
            classification=classification,
            review_status=review_status,
            conditions=conditions,
            condition_summary=", ".join(conditions) if conditions else "not provided",
            hgvs_aliases=hgvs_aliases,
            gene_symbols=gene_symbols,
            provenance=ClinVarLocalProvenance(
                source_id=provenance.source_id,
                source_version=provenance.source_version,
                file_date=provenance.file_date,
                checksum_algorithm=provenance.checksum_algorithm,
                checksum=provenance.checksum,
                relative_path=provenance.relative_path,
                record_id=record_id,
            ),
        )
        for alt in alts
    )


def _records_from_indexed_vcf_record(
    record: IndexedVcfRecord,
    *,
    provenance: ClinVarLocalProvenance,
) -> tuple[ClinVarLocalRecord, ...]:
    chrom = _normalize_contig_alias(record.chrom)
    ref = _normalize_allele(record.ref)
    alts = tuple(_normalize_allele(alt) for alt in record.alts)
    if record.position < 1 or not ref or not alts or any(not alt for alt in alts):
        raise ClinVarLocalError(
            "malformed_clinvar_vcf_row",
            "ClinVar indexed VCF record has invalid coordinates or alleles",
            {
                "chrom": chrom,
                "position": record.position,
                "ref": ref,
                "alts": alts,
            },
        )
    info = _indexed_info_map(record.info)
    record_id = _record_id(record.record_id, info)
    classification = _decode_required_info(info, "CLNSIG", 0)
    review_status = _decode_required_info(info, "CLNREVSTAT", 0)
    conditions = _condition_values(info.get("CLNDN"))
    hgvs_aliases = _hgvs_aliases(info)
    gene_symbols = _gene_symbols(info.get("GENEINFO"))
    accession = _normalize_vcv_accession(record_id)
    variation_id = _variation_id(accession)
    return tuple(
        ClinVarLocalRecord(
            chrom=chrom,
            position=record.position,
            ref=ref,
            alt=alt,
            gnomad_variant_id=_gnomad_variant_id(chrom, record.position, ref, alt),
            record_id=record_id,
            variation_id=variation_id,
            accession=accession,
            classification=classification,
            review_status=review_status,
            conditions=conditions,
            condition_summary=", ".join(conditions) if conditions else "not provided",
            hgvs_aliases=hgvs_aliases,
            gene_symbols=gene_symbols,
            provenance=ClinVarLocalProvenance(
                source_id=provenance.source_id,
                source_version=provenance.source_version,
                file_date=provenance.file_date,
                checksum_algorithm=provenance.checksum_algorithm,
                checksum=provenance.checksum,
                relative_path=provenance.relative_path,
                record_id=record_id,
            ),
        )
        for alt in alts
    )


def _parse_info(value: str, *, row_number: int) -> dict[str, str]:
    if not value or value == ".":
        raise ClinVarLocalError(
            "malformed_clinvar_vcf_row",
            "ClinVar VCF row must contain INFO fields",
            {"row": row_number},
        )
    info: dict[str, str] = {}
    for item in value.split(";"):
        if not item:
            continue
        if "=" not in item:
            if item in info:
                raise ClinVarLocalError(
                    "malformed_clinvar_vcf_row",
                    "ClinVar VCF row has duplicate INFO keys",
                    {"row": row_number, "field": item},
                )
            info[item] = "true"
            continue
        key, raw = item.split("=", 1)
        if key in info:
            raise ClinVarLocalError(
                "malformed_clinvar_vcf_row",
                "ClinVar VCF row has duplicate INFO keys",
                {"row": row_number, "field": key},
            )
        info[key] = raw
    return info


def _source_provenance(
    path: Path,
    registry: DataSourceRegistry,
) -> ClinVarLocalProvenance:
    record = registry.get(CLINVAR_SOURCE_ID)
    return ClinVarLocalProvenance(
        source_id=CLINVAR_SOURCE_ID,
        source_version=record.source_version,
        file_date=_file_date(_read_fixture_lines(path)),
        checksum_algorithm="sha256",
        checksum=_sha256_file(path),
        relative_path=_repo_relative_path(path),
    )


def _runtime_source_provenance(
    path: Path,
    registry: DataSourceRegistry,
) -> ClinVarLocalProvenance:
    record = registry.get(CLINVAR_SOURCE_ID)
    return ClinVarLocalProvenance(
        source_id=CLINVAR_SOURCE_ID,
        source_version=record.source_version,
        file_date=None,
        checksum_algorithm="runtime_manifest",
        checksum="not_computed_on_request_path",
        relative_path=f"runtime:{path.name}",
    )


def _indexed_info_map(info: Mapping[str, object]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in info.items():
        text = _indexed_info_text(value)
        if text is not None:
            out[str(key)] = text
    return out


def _indexed_info_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (tuple, list)):
        values = [
            text for item in value for text in (_indexed_info_text(item),) if text is not None
        ]
        return "|".join(values) if values else None
    text = str(value).strip()
    if not text or text == ".":
        return None
    return text


def _read_fixture_lines(path: Path) -> list[str]:
    try:
        if path.suffix.lower() == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                return handle.read().splitlines()
        return path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ClinVarLocalError(
            "fixture_unavailable",
            "ClinVar VCF fixture is unavailable",
            {"path": str(path)},
        ) from exc


def _file_date(lines: Iterable[str]) -> str | None:
    for line in lines:
        if line.startswith("##fileDate="):
            return line.split("=", 1)[1].strip() or None
    return None


def _required(row: Mapping[str, str], field_name: str, *, row_number: int) -> str:
    value = row.get(field_name)
    if value is None or not value.strip():
        raise ClinVarLocalError(
            "malformed_clinvar_vcf_row",
            f"ClinVar VCF row is missing required field {field_name}",
            {"row": row_number, "field": field_name},
        )
    return value.strip()


def _decode_required_info(info: Mapping[str, str], key: str, row_number: int) -> str:
    value = info.get(key)
    if value is None or value == ".":
        raise ClinVarLocalError(
            "malformed_clinvar_vcf_row",
            f"ClinVar VCF row is missing required INFO field {key}",
            {"row": row_number, "field": key},
        )
    return _decode_clinvar_value(value)


def _record_id(row_id: str | None, info: Mapping[str, str]) -> str:
    for value in (info.get("VCV"), row_id, info.get("VariationID"), info.get("VARIATION_ID")):
        if value and value != ".":
            return _normalize_vcv_accession(value)
    raise ClinVarLocalError(
        "malformed_clinvar_vcf_row",
        "ClinVar VCF row is missing a VCV accession or Variation ID",
    )


def _normalize_vcv_accession(value: str) -> str:
    text = value.strip().upper()
    if text.startswith("VCV"):
        digits = text[3:]
    else:
        digits = text
    if not digits.isdigit():
        raise ClinVarLocalError(
            "malformed_clinvar_vcf_row",
            "ClinVar VCV accession must contain a numeric Variation ID",
            {"accession": value},
        )
    return f"VCV{int(digits):09d}"


def _variation_id(accession: str) -> str:
    return str(int(accession[3:]))


def _condition_values(value: str | None) -> tuple[str, ...]:
    if value is None or value == ".":
        return ()
    values = [
        _decode_clinvar_value(item)
        for item in value.split("|")
        if item and item not in {".", "not_provided"}
    ]
    return tuple(dict.fromkeys(values))


def _hgvs_aliases(info: Mapping[str, str]) -> tuple[str, ...]:
    aliases: list[str] = []
    for key in ("CLNHGVS", "HGVS"):
        value = info.get(key)
        if not value or value == ".":
            continue
        aliases.extend(item for item in value.split("|") if item and item != ".")
    return tuple(dict.fromkeys(aliases))


def _gene_symbols(value: str | None) -> tuple[str, ...]:
    if value is None or value == ".":
        return ()
    symbols = []
    for item in value.split("|"):
        symbol = item.split(":", 1)[0].strip().upper()
        if symbol:
            symbols.append(symbol)
    return tuple(dict.fromkeys(symbols))


def _decode_clinvar_value(value: str) -> str:
    return value.replace("_", " ").replace("%2C", ",").strip()


def _parse_gnomad_variant_id(value: str) -> tuple[str, int, str, str] | None:
    match = re.fullmatch(r"([^-]+)-(\d+)-([A-Za-z]+)-([A-Za-z]+)", value.strip())
    if match is None:
        return None
    chrom, position, ref, alt = match.groups()
    return chrom, int(position), _normalize_allele(ref), _normalize_allele(alt)


def _variant_key(chrom: str, position: int, ref: str, alt: str) -> tuple[str, int, str, str]:
    return (
        _normalize_contig_alias(chrom),
        position,
        _normalize_allele(ref),
        _normalize_allele(alt),
    )


def _gnomad_variant_id(chrom: str, position: int, ref: str, alt: str) -> str:
    return f"{_normalize_contig_alias(chrom)}-{position}-{_normalize_allele(ref)}-{_normalize_allele(alt)}"


def _normalize_allele(value: str) -> str:
    return value.strip().upper()


def _normalize_accession(value: str) -> str:
    text = value.strip().upper()
    if text.startswith("VCV"):
        return _normalize_vcv_accession(text)
    if text.isdigit():
        return _normalize_vcv_accession(text)
    return text


def _build_alias_map(contigs: Iterable[str]) -> dict[str, str]:
    alias_to_contig: dict[str, str] = {}
    for contig in contigs:
        normalized = _normalize_contig_alias(contig)
        aliases = {contig, normalized, f"chr{normalized}", *_grch38_ncbi_aliases(normalized)}
        if normalized == "M":
            aliases.update({"MT", "chrM", "chrMT", "NC_012920.1"})
        for alias in aliases:
            alias_to_contig[_normalize_contig_alias(alias)] = normalized
    return alias_to_contig


def _normalize_contig_alias(chrom: str) -> str:
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
    if normalized == "NC_012920.1":
        return "M"
    if normalized == "MT":
        return "M"
    return normalized


def _grch38_ncbi_aliases(canonical_chrom: str) -> tuple[str, ...]:
    try:
        chrom_number = int(canonical_chrom)
    except ValueError:
        chrom_number = 0
    if 1 <= chrom_number <= 22:
        return (f"NC_{chrom_number:06d}.11",)
    if canonical_chrom == "X":
        return ("NC_000023.11",)
    if canonical_chrom == "Y":
        return ("NC_000024.10",)
    return ()


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _repo_relative_path(path: Path) -> str:
    return repo_relative_path(path, anchor=__file__)


def _repo_root() -> Path:
    return find_project_root(__file__)


def _is_fixture_path(path: Path) -> bool:
    try:
        return path.resolve() == DEFAULT_CLINVAR_VCF_FIXTURE_PATH.resolve()
    except OSError:
        return path == DEFAULT_CLINVAR_VCF_FIXTURE_PATH


def _default_indexed_reader_factory(path: Path, index_path: Path) -> PysamIndexedVcfReader:
    return PysamIndexedVcfReader(
        path,
        source_id=CLINVAR_SOURCE_ID,
        index_path=index_path,
        max_window_bp=1,
        max_records=64,
    )


def _resolve_backend_path(settings: object, path: Path) -> Path:
    if path.is_absolute():
        return path
    backend_root = Path(getattr(settings, "backend_root"))
    return backend_root / path


def _classification_bucket(classification: str) -> str:
    normalized = classification.lower()
    conflicting = "conflicting" in normalized
    has_pathogenic = "pathogenic" in normalized
    has_benign = "benign" in normalized
    if has_pathogenic and not has_benign and not conflicting:
        return "pathogenic"
    if has_benign and not has_pathogenic and not conflicting:
        return "benign"
    return "vus"


def _variant_effect_bucket(record: ClinVarLocalRecord) -> str:
    aliases = tuple(alias.lower() for alias in record.hgvs_aliases)
    protein_aliases = tuple(alias for alias in aliases if ":p." in alias or alias.startswith("p."))
    if any("p.=" in alias or "synonymous" in alias for alias in protein_aliases):
        return "synonymous"
    if any(
        token in alias
        for alias in protein_aliases
        for token in ("ter", "*", "fs", "frameshift", "splice")
    ):
        return "lof"
    if protein_aliases:
        return "missense"
    if len(record.ref) != len(record.alt):
        return "missense"
    return "noncoding"


def _distribution_warnings(
    gene_symbol: str,
    store: ClinVarLocalStore,
    total: int,
) -> tuple[str, ...]:
    warnings: list[str] = []
    if total == 0:
        warnings.append("clinvar_local_gene_no_records")
    if store.source_status() == "fixture":
        warnings.append("clinvar_local_fixture_scope")
    if not store.provenance().source_version:
        warnings.append("clinvar_local_source_version_missing")
    if not gene_symbol:
        warnings.append("clinvar_local_gene_missing")
    return tuple(warnings)


def _query_record_for_distribution(
    store: ClinVarLocalStore,
    *,
    query_variant_id: str | None,
    gene_symbol: str,
) -> tuple[ClinVarLocalRecord | None, tuple[str, ...]]:
    if not query_variant_id:
        return None, ()
    lookup = store.lookup_variant_id(query_variant_id)
    if not lookup.available or lookup.record is None:
        return None, ("clinvar_local_query_variant_not_found", *lookup.warnings)
    if gene_symbol and gene_symbol not in lookup.record.gene_symbols:
        return None, ("clinvar_local_query_variant_gene_mismatch",)
    return lookup.record, ()


def _distribution_reading(
    gene_symbol: str,
    row_totals: Mapping[str, int],
    cells: Mapping[str, int],
    total: int,
    source_status: str,
) -> str:
    label = gene_symbol or "this gene"
    if total == 0:
        return f"No ClinVar records for {label} are present in the installed local source."
    top_key, top_count = max(cells.items(), key=lambda item: item[1])
    top_row, top_col = top_key.split("_", 1)
    row_label = {
        "pathogenic": "pathogenic or likely pathogenic",
        "vus": "uncertain or conflicting",
        "benign": "benign or likely benign",
    }.get(top_row, top_row)
    col_label = {
        "lof": "loss-of-function",
        "missense": "missense/indel",
        "noncoding": "non-coding",
        "synonymous": "synonymous",
    }.get(top_col, top_col)
    pathogenic_total = row_totals.get("pathogenic", 0)
    benign_total = row_totals.get("benign", 0)
    scope = "fixture" if source_status == "fixture" else "local ClinVar"
    return (
        f"The installed {scope} aggregate contains {total:,} {label} ClinVar "
        f"record{'s' if total != 1 else ''}. The largest bucket is {row_label} "
        f"{col_label} ({top_count:,}); pathogenic/likely pathogenic total "
        f"{pathogenic_total:,}, benign/likely benign total {benign_total:,}."
    )
