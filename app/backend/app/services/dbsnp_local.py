from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
from typing import Iterable, Mapping

from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry
from app.services.indexed_sources import IndexedVcfRecord

DBSNP_SOURCE_ID = "ncbi_dbsnp_gcf_000001405_40"
DEFAULT_DBSNP_VCF_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "data_sources" / "dbsnp_tiny.vcf"
)


class DbSnpLocalError(ValueError):
    """Structured error for malformed local dbSNP VCF fixtures."""

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
class DbSnpLocalProvenance:
    source_id: str
    source_version: str | None
    assembly_accession: str | None
    file_date: str | None
    checksum_algorithm: str
    checksum: str
    relative_path: str
    record_id: str | None = None


@dataclass(frozen=True)
class DbSnpAlleleIdentity:
    chrom: str
    position: int
    ref: str
    alt: str
    gnomad_variant_id: str
    genomic_hgvs: str | None


@dataclass(frozen=True)
class DbSnpLocalRecord:
    rsid: str
    chrom: str
    position: int
    ref: str
    alts: tuple[str, ...]
    allele_identities: tuple[DbSnpAlleleIdentity, ...]
    dbsnp_build_id: str | None
    provenance: DbSnpLocalProvenance

    @property
    def is_multiallelic(self) -> bool:
        return len(self.alts) > 1


@dataclass(frozen=True)
class DbSnpLocalLookup:
    available: bool
    record: DbSnpLocalRecord | None
    unavailable_reason: str | None = None
    warnings: tuple[str, ...] = ()


class DbSnpLocalStore:
    """Fixture-first dbSNP GCF adapter for rsID-to-GRCh38 identity lookup."""

    def __init__(
        self,
        vcf_path: Path | None = None,
        registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    ) -> None:
        self._vcf_path = vcf_path or DEFAULT_DBSNP_VCF_FIXTURE_PATH
        self._source_provenance = _source_provenance(self._vcf_path, registry)
        self._records = parse_dbsnp_vcf(
            self._vcf_path,
            provenance=self._source_provenance,
        )
        self._records_by_rsid = {_normalize_rsid(record.rsid): record for record in self._records}
        self._records_by_variant_key: dict[tuple[str, int, str, str], list[DbSnpLocalRecord]] = {}
        for record in self._records:
            for identity in record.allele_identities:
                self._records_by_variant_key.setdefault(
                    _variant_key(identity.chrom, identity.position, identity.ref, identity.alt),
                    [],
                ).append(record)
        self._contig_aliases = _build_alias_map(record.chrom for record in self._records)

    def provenance(self) -> DbSnpLocalProvenance:
        return self._source_provenance

    def records(self) -> tuple[DbSnpLocalRecord, ...]:
        return self._records

    def lookup_rsid(self, rsid: str) -> DbSnpLocalLookup:
        try:
            normalized = _normalize_rsid(rsid)
        except DbSnpLocalError:
            return DbSnpLocalLookup(
                available=False,
                record=None,
                unavailable_reason="invalid_rsid",
                warnings=("dbsnp_local_invalid_rsid",),
            )
        record = self._records_by_rsid.get(normalized)
        if record is None:
            return DbSnpLocalLookup(
                available=False,
                record=None,
                unavailable_reason="rsid_not_found",
                warnings=("dbsnp_local_rsid_not_found",),
            )
        return DbSnpLocalLookup(available=True, record=record)

    def lookup_variant(
        self,
        *,
        chrom: str,
        position: int,
        ref: str,
        alt: str,
    ) -> DbSnpLocalLookup:
        if position < 1:
            return DbSnpLocalLookup(
                available=False,
                record=None,
                unavailable_reason="invalid_coordinates",
                warnings=("dbsnp_local_invalid_coordinates",),
            )
        try:
            normalized_chrom = self._contig_aliases[_normalize_contig_alias(chrom)]
        except KeyError:
            return DbSnpLocalLookup(
                available=False,
                record=None,
                unavailable_reason="contig_not_found",
                warnings=("dbsnp_local_contig_not_found",),
            )
        records = self._records_by_variant_key.get(
            _variant_key(normalized_chrom, position, ref, alt),
            [],
        )
        if records:
            return DbSnpLocalLookup(available=True, record=records[0])
        if any(
            record.chrom == normalized_chrom and record.position == position
            for record in self._records
        ):
            return DbSnpLocalLookup(
                available=False,
                record=None,
                unavailable_reason="allele_mismatch",
                warnings=("dbsnp_local_allele_mismatch",),
            )
        return DbSnpLocalLookup(
            available=False,
            record=None,
            unavailable_reason="variant_not_found",
            warnings=("dbsnp_local_variant_not_found",),
        )

    def records_at(self, chrom: str, position: int) -> tuple[DbSnpLocalRecord, ...]:
        if position < 1:
            raise DbSnpLocalError(
                "invalid_coordinates",
                "dbSNP local queries use 1-based inclusive coordinates",
                {"chrom": chrom, "position": position},
            )
        try:
            normalized_chrom = self._contig_aliases[_normalize_contig_alias(chrom)]
        except KeyError as exc:
            raise DbSnpLocalError(
                "unknown_contig",
                "contig is not present in local dbSNP fixture",
                {"requested_chrom": chrom},
            ) from exc
        return tuple(
            record
            for record in self._records
            if record.chrom == normalized_chrom and record.position == position
        )


def parse_dbsnp_vcf(
    path: Path,
    *,
    provenance: DbSnpLocalProvenance,
) -> tuple[DbSnpLocalRecord, ...]:
    lines = _read_fixture_lines(path)
    file_date = _file_date(lines) or provenance.file_date
    assembly_accession = _assembly_accession(lines) or provenance.assembly_accession
    header: list[str] | None = None
    records: list[DbSnpLocalRecord] = []
    for row_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        if line.startswith("##"):
            continue
        if line.startswith("#CHROM"):
            header = line.lstrip("#").split("\t")
            continue
        if header is None:
            raise DbSnpLocalError(
                "vcf_missing_header",
                "dbSNP VCF fixture row appeared before the #CHROM header",
                {"path": str(path), "row": row_number},
            )
        records.extend(
            _parse_vcf_row(
                line,
                row_number=row_number,
                header=header,
                provenance=DbSnpLocalProvenance(
                    source_id=provenance.source_id,
                    source_version=provenance.source_version,
                    assembly_accession=assembly_accession,
                    file_date=file_date,
                    checksum_algorithm=provenance.checksum_algorithm,
                    checksum=provenance.checksum,
                    relative_path=provenance.relative_path,
                ),
            )
        )
    if header is None:
        raise DbSnpLocalError(
            "vcf_missing_header",
            "dbSNP VCF fixture must include a #CHROM header",
            {"path": str(path)},
        )
    if not records:
        raise DbSnpLocalError(
            "empty_dbsnp_vcf_fixture",
            "dbSNP VCF fixture must contain at least one variant row",
            {"path": str(path)},
        )
    return tuple(records)


def _parse_vcf_row(
    line: str,
    *,
    row_number: int,
    header: list[str],
    provenance: DbSnpLocalProvenance,
) -> tuple[DbSnpLocalRecord, ...]:
    fields = line.rstrip("\n").split("\t")
    if len(fields) != len(header):
        raise DbSnpLocalError(
            "malformed_dbsnp_vcf_row",
            "dbSNP VCF row field count does not match header",
            {"row": row_number, "field_count": len(fields), "header_count": len(header)},
        )
    row = dict(zip(header, fields, strict=True))
    try:
        position = int(_required(row, "POS", row_number=row_number))
    except ValueError as exc:
        raise DbSnpLocalError(
            "malformed_dbsnp_vcf_row",
            "dbSNP VCF POS must be an integer",
            {"row": row_number, "position": row.get("POS")},
        ) from exc
    chrom = _normalize_contig_alias(_required(row, "CHROM", row_number=row_number))
    ref = _normalize_allele(_required(row, "REF", row_number=row_number))
    alts = tuple(
        _normalize_allele(alt) for alt in _required(row, "ALT", row_number=row_number).split(",")
    )
    rsids = _row_rsids(_required(row, "ID", row_number=row_number), row_number=row_number)
    if position < 1 or not ref or not alts or any(not alt for alt in alts):
        raise DbSnpLocalError(
            "malformed_dbsnp_vcf_row",
            "dbSNP VCF row has invalid coordinates or alleles",
            {"row": row_number, "chrom": chrom, "position": position, "ref": ref, "alts": alts},
        )
    info = _parse_info(_required(row, "INFO", row_number=row_number), row_number=row_number)
    indexed_record = IndexedVcfRecord(
        requested_chrom=row["CHROM"],
        chrom=chrom,
        position=position,
        record_id=";".join(rsids),
        ref=ref,
        alts=alts,
        info=info,
        source_id=DBSNP_SOURCE_ID,
    )
    return tuple(
        _record_from_indexed_vcf_record(
            indexed_record,
            rsid=rsid,
            provenance=provenance,
        )
        for rsid in rsids
    )


def _record_from_indexed_vcf_record(
    record: IndexedVcfRecord,
    *,
    rsid: str,
    provenance: DbSnpLocalProvenance,
) -> DbSnpLocalRecord:
    identities = tuple(
        DbSnpAlleleIdentity(
            chrom=record.chrom,
            position=record.position,
            ref=record.ref,
            alt=alt,
            gnomad_variant_id=_gnomad_variant_id(record.chrom, record.position, record.ref, alt),
            genomic_hgvs=_refseq_genomic_hgvs(record.chrom, record.position, record.ref, alt),
        )
        for alt in record.alts
    )
    return DbSnpLocalRecord(
        rsid=rsid,
        chrom=record.chrom,
        position=record.position,
        ref=record.ref,
        alts=record.alts,
        allele_identities=identities,
        dbsnp_build_id=_optional_info_text(record.info.get("dbSNPBuildID")),
        provenance=DbSnpLocalProvenance(
            source_id=provenance.source_id,
            source_version=provenance.source_version,
            assembly_accession=provenance.assembly_accession,
            file_date=provenance.file_date,
            checksum_algorithm=provenance.checksum_algorithm,
            checksum=provenance.checksum,
            relative_path=provenance.relative_path,
            record_id=rsid,
        ),
    )


def _parse_info(value: str, *, row_number: int) -> dict[str, str]:
    if not value or value == ".":
        return {}
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
) -> DbSnpLocalProvenance:
    record = registry.get(DBSNP_SOURCE_ID)
    lines = _read_fixture_lines(path)
    return DbSnpLocalProvenance(
        source_id=DBSNP_SOURCE_ID,
        source_version=record.source_version,
        assembly_accession=_assembly_accession(lines),
        file_date=_file_date(lines),
        checksum_algorithm="sha256",
        checksum=_sha256_file(path),
        relative_path=_repo_relative_path(path),
    )


def _read_fixture_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DbSnpLocalError(
            "fixture_unavailable",
            "dbSNP VCF fixture is unavailable",
            {"path": str(path)},
        ) from exc


def _file_date(lines: Iterable[str]) -> str | None:
    for line in lines:
        if line.startswith("##fileDate="):
            return line.split("=", 1)[1].strip() or None
    return None


def _assembly_accession(lines: Iterable[str]) -> str | None:
    for line in lines:
        if line.startswith("##assembly="):
            return line.split("=", 1)[1].strip() or None
    return None


def _required(row: Mapping[str, str], field_name: str, *, row_number: int) -> str:
    value = row.get(field_name)
    if value is None or not value.strip():
        raise DbSnpLocalError(
            "malformed_dbsnp_vcf_row",
            f"dbSNP VCF row is missing required field {field_name}",
            {"row": row_number, "field": field_name},
        )
    return value.strip()


def _row_rsids(value: str, *, row_number: int) -> tuple[str, ...]:
    if value == ".":
        raise DbSnpLocalError(
            "malformed_dbsnp_vcf_row",
            "dbSNP VCF row is missing an rsID",
            {"row": row_number},
        )
    rsids: list[str] = []
    for item in re.split(r"[;,]", value):
        if not item.strip():
            continue
        rsids.append(_normalize_rsid(item))
    if not rsids:
        raise DbSnpLocalError(
            "malformed_dbsnp_vcf_row",
            "dbSNP VCF row is missing an rsID",
            {"row": row_number},
        )
    return tuple(dict.fromkeys(rsids))


def _normalize_rsid(value: str) -> str:
    match = re.fullmatch(r"rs(\d+)", value.strip(), flags=re.IGNORECASE)
    if match is None:
        raise DbSnpLocalError(
            "invalid_rsid",
            "dbSNP identifiers must use rs-prefixed numeric IDs",
            {"rsid": value},
        )
    return f"rs{int(match.group(1))}"


def _variant_key(chrom: str, position: int, ref: str, alt: str) -> tuple[str, int, str, str]:
    return (
        _normalize_contig_alias(chrom),
        position,
        _normalize_allele(ref),
        _normalize_allele(alt),
    )


def _gnomad_variant_id(chrom: str, position: int, ref: str, alt: str) -> str:
    return (
        f"{_normalize_contig_alias(chrom)}-{position}-"
        f"{_normalize_allele(ref)}-{_normalize_allele(alt)}"
    )


def _refseq_genomic_hgvs(chrom: str, position: int, ref: str, alt: str) -> str | None:
    refseq_aliases = _grch38_ncbi_aliases(_normalize_contig_alias(chrom))
    if not refseq_aliases:
        return None
    if (
        len(ref) == 1
        and len(alt) == 1
        and re.fullmatch(r"[ACGT]", ref)
        and re.fullmatch(r"[ACGT]", alt)
    ):
        return f"{refseq_aliases[0]}:g.{position}{ref}>{alt}"
    return None


def _normalize_allele(value: str) -> str:
    return value.strip().upper()


def _optional_info_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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
    try:
        return path.resolve().relative_to(_repo_root()).as_posix()
    except ValueError:
        return str(path)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]
