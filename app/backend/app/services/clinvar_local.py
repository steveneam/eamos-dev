from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
from typing import Iterable, Mapping

from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry

CLINVAR_SOURCE_ID = "ncbi_clinvar_vcf"
DEFAULT_CLINVAR_VCF_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "data_sources" / "clinvar_tiny.vcf"
)


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
        self._records_by_key = {
            _variant_key(record.chrom, record.position, record.ref, record.alt): record
            for record in self._records
        }
        self._records_by_accession: dict[str, ClinVarLocalRecord] = {}
        for record in self._records:
            for accession in {record.accession, record.variation_id, record.record_id}:
                self._records_by_accession[_normalize_accession(accession)] = record
        self._contig_aliases = _build_alias_map(record.chrom for record in self._records)

    def provenance(self) -> ClinVarLocalProvenance:
        return self._source_provenance

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
            info[item] = "true"
            continue
        key, raw = item.split("=", 1)
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


def _read_fixture_lines(path: Path) -> list[str]:
    try:
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
    try:
        return path.resolve().relative_to(_repo_root()).as_posix()
    except ValueError:
        return str(path)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]
