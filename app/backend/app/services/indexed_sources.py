from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata as importlib_metadata
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping


class IndexedSourceError(ValueError):
    """Structured error for local indexed-source reader failures."""

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
class IndexedReaderMetadata:
    source_id: str
    path: Path
    reader: str
    version: str


@dataclass(frozen=True)
class IndexedVcfRecord:
    requested_chrom: str
    chrom: str
    position: int
    record_id: str | None
    ref: str
    alts: tuple[str, ...]
    info: Mapping[str, object]
    source_id: str


@dataclass(frozen=True)
class ConservationScore:
    requested_chrom: str
    chrom: str
    position: int
    score: float
    source_id: str


@dataclass(frozen=True)
class ConservationWindowSummary:
    requested_chrom: str
    chrom: str
    start: int
    end: int
    mean_score: float
    bases_with_scores: int
    source_id: str


@dataclass(frozen=True)
class RepeatMaskerInterval:
    chrom: str
    start: int
    end: int
    name: str
    repeat_class: str
    repeat_family: str
    strand: str
    source_id: str = "repeatmasker_rmsk_bb"


@dataclass(frozen=True)
class RepeatMaskerPathDecision:
    strategy: str
    direct_bigbed_reader: bool
    reason: str
    fixture_format: str


class PysamIndexedVcfReader:
    """pysam-backed VCF/tabix reader using 1-based inclusive caller coordinates."""

    def __init__(
        self,
        path: Path,
        *,
        source_id: str,
        index_path: Path | None = None,
    ) -> None:
        self._path = path
        self._index_path = index_path or Path(f"{path}.tbi")
        self._source_id = source_id
        self._validate_indexed_file()
        self._pysam = _load_pysam()
        self._vcf = self._pysam.VariantFile(str(path))
        self._contigs = tuple(str(contig) for contig in self._vcf.header.contigs)
        self._alias_to_contig = _build_alias_map(self._contigs)
        self._metadata = IndexedReaderMetadata(
            source_id=source_id,
            path=path,
            reader="pysam",
            version=_package_version("pysam"),
        )

    def close(self) -> None:
        self._vcf.close()

    def __enter__(self) -> PysamIndexedVcfReader:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def metadata(self) -> IndexedReaderMetadata:
        return self._metadata

    def query_position(self, chrom: str, position: int) -> tuple[IndexedVcfRecord, ...]:
        return tuple(
            record
            for record in self.query_range(chrom, position, position)
            if record.position == position
        )

    def query_range(
        self,
        chrom: str,
        start: int,
        end: int,
    ) -> tuple[IndexedVcfRecord, ...]:
        contig = self._normalize_contig(chrom)
        _validate_interval(contig, start, end)
        try:
            records = self._vcf.fetch(contig, start - 1, end)
        except ValueError as exc:
            raise IndexedSourceError(
                "indexed_query_failed",
                "pysam failed to query indexed VCF",
                {"chrom": contig, "start": start, "end": end},
            ) from exc
        return tuple(self._to_record(chrom, record) for record in records)

    def _to_record(self, requested_chrom: str, raw_record: Any) -> IndexedVcfRecord:
        alts = tuple(str(alt) for alt in (raw_record.alts or ()))
        info = {str(key): _vcf_info_value(value) for key, value in raw_record.info.items()}
        return IndexedVcfRecord(
            requested_chrom=requested_chrom,
            chrom=_normalize_contig_alias(str(raw_record.contig)),
            position=int(raw_record.pos),
            record_id=None if raw_record.id in {None, "."} else str(raw_record.id),
            ref=str(raw_record.ref),
            alts=alts,
            info=info,
            source_id=self._source_id,
        )

    def _normalize_contig(self, chrom: str) -> str:
        alias = _normalize_contig_alias(chrom)
        try:
            return self._alias_to_contig[alias]
        except KeyError as exc:
            raise IndexedSourceError(
                "unknown_contig",
                "contig is not present in indexed VCF",
                {"requested_chrom": chrom},
            ) from exc

    def _validate_indexed_file(self) -> None:
        _validate_file(self._path, code_prefix="indexed_vcf")
        if not self._index_path.exists():
            raise IndexedSourceError(
                "missing_index",
                "indexed VCF requires a tabix .tbi index",
                {"path": str(self._path), "index_path": str(self._index_path)},
            )
        if not self._index_path.is_file():
            raise IndexedSourceError(
                "index_not_file",
                "tabix index path is not a file",
                {"path": str(self._path), "index_path": str(self._index_path)},
            )


class PyBigWigConservationReader:
    """pyBigWig-backed conservation reader using 1-based inclusive coordinates."""

    def __init__(self, path: Path, *, source_id: str = "ucsc_phylop100way_hg38") -> None:
        self._path = path
        self._source_id = source_id
        _validate_file(path, code_prefix="bigwig")
        self._pybigwig = _load_pybigwig()
        self._bigwig = self._pybigwig.open(str(path))
        if self._bigwig is None:
            raise IndexedSourceError(
                "bigwig_open_failed",
                "pyBigWig could not open the bigWig file",
                {"path": str(path)},
            )
        self._chroms = {str(chrom): int(length) for chrom, length in self._bigwig.chroms().items()}
        self._alias_to_contig = _build_alias_map(self._chroms.keys())
        self._metadata = IndexedReaderMetadata(
            source_id=source_id,
            path=path,
            reader="pyBigWig",
            version=_package_version("pyBigWig"),
        )

    def close(self) -> None:
        self._bigwig.close()

    def __enter__(self) -> PyBigWigConservationReader:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def metadata(self) -> IndexedReaderMetadata:
        return self._metadata

    def score(self, chrom: str, position: int) -> ConservationScore:
        contig = self._normalize_contig(chrom)
        _validate_interval(contig, position, position)
        _validate_bounds(contig, position, position, self._chroms[contig])
        values = self._bigwig.values(contig, position - 1, position)
        value = values[0] if values else None
        if value is None or math.isnan(float(value)):
            raise IndexedSourceError(
                "missing_conservation_score",
                "no conservation value is present for this position",
                {"chrom": contig, "position": position},
            )
        return ConservationScore(
            requested_chrom=chrom,
            chrom=_normalize_contig_alias(contig),
            position=position,
            score=float(value),
            source_id=self._source_id,
        )

    def window_summary(self, chrom: str, start: int, end: int) -> ConservationWindowSummary:
        contig = self._normalize_contig(chrom)
        _validate_interval(contig, start, end)
        _validate_bounds(contig, start, end, self._chroms[contig])
        values = self._bigwig.values(contig, start - 1, end)
        numeric_values = [
            float(value) for value in values if value is not None and not math.isnan(float(value))
        ]
        if not numeric_values:
            raise IndexedSourceError(
                "missing_conservation_score",
                "no conservation values are present for this window",
                {"chrom": contig, "start": start, "end": end},
            )
        return ConservationWindowSummary(
            requested_chrom=chrom,
            chrom=_normalize_contig_alias(contig),
            start=start,
            end=end,
            mean_score=sum(numeric_values) / len(numeric_values),
            bases_with_scores=len(numeric_values),
            source_id=self._source_id,
        )

    def _normalize_contig(self, chrom: str) -> str:
        alias = _normalize_contig_alias(chrom)
        try:
            return self._alias_to_contig[alias]
        except KeyError as exc:
            raise IndexedSourceError(
                "unknown_contig",
                "contig is not present in bigWig file",
                {"requested_chrom": chrom},
            ) from exc


class RepeatMaskerIndexedTable:
    """Deterministic RepeatMasker interval index from UCSC rmsk.txt-style rows."""

    def __init__(self, intervals: Iterable[RepeatMaskerInterval]) -> None:
        self._intervals = tuple(
            sorted(intervals, key=lambda item: (item.chrom, item.start, item.end))
        )
        if not self._intervals:
            raise IndexedSourceError(
                "empty_repeatmasker_index",
                "RepeatMasker interval index has no records",
            )
        self._contigs = tuple(dict.fromkeys(interval.chrom for interval in self._intervals))
        self._alias_to_contig = _build_alias_map(self._contigs)

    @classmethod
    def from_ucsc_rmsk_rows(cls, rows: Iterable[str]) -> RepeatMaskerIndexedTable:
        return cls(_parse_ucsc_rmsk_row(row) for row in rows if row.strip())

    def query(self, chrom: str, start: int, end: int) -> tuple[RepeatMaskerInterval, ...]:
        contig = self._normalize_contig(chrom)
        _validate_interval(contig, start, end)
        return tuple(
            interval
            for interval in self._intervals
            if interval.chrom == contig and interval.start <= end and interval.end >= start
        )

    def _normalize_contig(self, chrom: str) -> str:
        alias = _normalize_contig_alias(chrom)
        try:
            return self._alias_to_contig[alias]
        except KeyError as exc:
            raise IndexedSourceError(
                "unknown_contig",
                "contig is not present in RepeatMasker index",
                {"requested_chrom": chrom},
            ) from exc


def repeatmasker_path_decision() -> RepeatMaskerPathDecision:
    return RepeatMaskerPathDecision(
        strategy="deterministic_rmsk_text_to_indexed_interval_table",
        direct_bigbed_reader=False,
        reason=(
            "Task 8 verified the official UCSC source as rmsk.txt.gz, not a "
            "published rmsk.bb. Use a deterministic conversion/index path first; "
            "derive bigBed only after a separate conversion proof."
        ),
        fixture_format="ucsc_rmsk_txt_rows",
    )


def _parse_ucsc_rmsk_row(row: str) -> RepeatMaskerInterval:
    fields = row.rstrip("\n").split("\t")
    if len(fields) < 16:
        raise IndexedSourceError(
            "malformed_repeatmasker_row",
            "UCSC rmsk row has fewer than 16 tab-separated fields",
            {"field_count": len(fields)},
        )
    try:
        chrom = _normalize_contig_alias(fields[5])
        zero_based_start = int(fields[6])
        zero_based_end = int(fields[7])
    except ValueError as exc:
        raise IndexedSourceError(
            "malformed_repeatmasker_row",
            "UCSC rmsk row has non-integer coordinates",
            {"chrom": fields[5], "start": fields[6], "end": fields[7]},
        ) from exc
    start = zero_based_start + 1
    end = zero_based_end
    _validate_interval(chrom, start, end)
    return RepeatMaskerInterval(
        chrom=chrom,
        start=start,
        end=end,
        strand=fields[9],
        name=fields[10],
        repeat_class=fields[11],
        repeat_family=fields[12],
    )


def _load_pysam() -> Any:
    try:
        import pysam
    except ImportError as exc:
        raise IndexedSourceError(
            "reader_unavailable",
            "pysam is required for bgzip/tabix VCF reads",
        ) from exc
    return pysam


def _load_pybigwig() -> Any:
    try:
        import pyBigWig
    except ImportError as exc:
        raise IndexedSourceError(
            "reader_unavailable",
            "pyBigWig is required for bigWig conservation reads",
        ) from exc
    return pyBigWig


def _package_version(distribution_name: str) -> str:
    try:
        return importlib_metadata.version(distribution_name)
    except importlib_metadata.PackageNotFoundError:
        return "unknown"


def _validate_file(path: Path, *, code_prefix: str) -> None:
    if not path.exists():
        raise IndexedSourceError(
            f"missing_{code_prefix}_file",
            "indexed source file is missing",
            {"path": str(path)},
        )
    if not path.is_file():
        raise IndexedSourceError(
            f"{code_prefix}_path_not_file",
            "indexed source path is not a file",
            {"path": str(path)},
        )


def _validate_interval(chrom: str, start: int, end: int) -> None:
    if start < 1 or end < 1 or start > end:
        raise IndexedSourceError(
            "invalid_coordinates",
            "indexed source queries use 1-based inclusive coordinates",
            {"chrom": chrom, "start": start, "end": end},
        )


def _validate_bounds(chrom: str, start: int, end: int, contig_length: int) -> None:
    if end > contig_length:
        raise IndexedSourceError(
            "out_of_bounds",
            "indexed source query exceeds contig length",
            {
                "chrom": chrom,
                "start": start,
                "end": end,
                "contig_length": contig_length,
            },
        )


def _build_alias_map(contigs: Iterable[str]) -> dict[str, str]:
    alias_to_contig: dict[str, str] = {}
    for contig in contigs:
        normalized = _normalize_contig_alias(contig)
        aliases = {contig, normalized, f"chr{normalized}", *_grch38_ncbi_aliases(normalized)}
        if normalized == "M":
            aliases.update({"MT", "chrM", "chrMT", "NC_012920.1"})
        for alias in aliases:
            normalized_alias = _normalize_contig_alias(alias)
            existing = alias_to_contig.get(normalized_alias)
            if existing is not None and existing != contig:
                raise IndexedSourceError(
                    "duplicate_contig_alias",
                    "duplicate contig alias in indexed source",
                    {"alias": alias, "first_contig": existing, "second_contig": contig},
                )
            alias_to_contig[normalized_alias] = contig
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


def _vcf_info_value(value: object) -> object:
    if isinstance(value, tuple):
        return tuple(_vcf_info_value(item) for item in value)
    if isinstance(value, list):
        return tuple(_vcf_info_value(item) for item in value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
