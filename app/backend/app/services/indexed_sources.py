from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from importlib import metadata as importlib_metadata
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

DEFAULT_INDEXED_VCF_MAX_WINDOW_BP = 1_000_000
DEFAULT_INDEXED_VCF_MAX_RECORDS = 10_000
DEFAULT_PREDICTOR_POSITION_MAX_RECORDS = 1_000
DEFAULT_CONSERVATION_MAX_WINDOW_BP = 100_000


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
class TabixTsvPredictorColumns:
    chrom: int = 0
    position: int = 1
    ref: int = 2
    alt: int = 3
    score: int = 4
    extra_columns: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class IndexedPredictorScore:
    requested_chrom: str
    chrom: str
    position: int
    ref: str
    alt: str
    score: float | str
    source_id: str
    raw_fields: tuple[str, ...]
    extra: Mapping[str, str]


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
        max_window_bp: int = DEFAULT_INDEXED_VCF_MAX_WINDOW_BP,
        max_records: int = DEFAULT_INDEXED_VCF_MAX_RECORDS,
    ) -> None:
        self._path = path
        self._index_path = index_path or Path(f"{path}.tbi")
        self._source_id = source_id
        self._max_window_bp = max(1, int(max_window_bp))
        self._max_records = max(1, int(max_records))
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
        _validate_window_width(
            contig,
            start,
            end,
            max_window_bp=self._max_window_bp,
            code="indexed_query_window_too_large",
        )
        try:
            records = self._vcf.fetch(contig, start - 1, end)
        except ValueError as exc:
            raise IndexedSourceError(
                "indexed_query_failed",
                "pysam failed to query indexed VCF",
                {"chrom": contig, "start": start, "end": end},
            ) from exc
        out: list[IndexedVcfRecord] = []
        for record in records:
            if len(out) >= self._max_records:
                raise IndexedSourceError(
                    "indexed_query_too_many_records",
                    "indexed VCF query returned more records than the configured cap",
                    {
                        "chrom": contig,
                        "start": start,
                        "end": end,
                        "max_records": self._max_records,
                    },
                )
            out.append(self._to_record(chrom, record))
        return tuple(out)

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


class TabixTsvPredictorReader:
    """pysam-backed tabix TSV reader for coordinate-keyed predictor scores."""

    def __init__(
        self,
        path: Path,
        *,
        source_id: str,
        columns: TabixTsvPredictorColumns = TabixTsvPredictorColumns(),
        index_path: Path | None = None,
        delimiter: str = "\t",
        max_records: int = DEFAULT_PREDICTOR_POSITION_MAX_RECORDS,
    ) -> None:
        self._path = path
        self._index_path = index_path or Path(f"{path}.tbi")
        self._source_id = source_id
        self._columns = columns
        self._delimiter = delimiter
        self._max_records = max(1, int(max_records))
        self._validate_indexed_file()
        self._validate_columns()
        self._pysam = _load_pysam()
        self._tabix = self._pysam.TabixFile(str(path))
        self._contigs = tuple(str(contig) for contig in self._tabix.contigs)
        self._alias_to_contig = _build_alias_map(self._contigs)
        self._metadata = IndexedReaderMetadata(
            source_id=source_id,
            path=path,
            reader="pysam.TabixFile",
            version=_package_version("pysam"),
        )

    def close(self) -> None:
        self._tabix.close()

    def __enter__(self) -> TabixTsvPredictorReader:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def metadata(self) -> IndexedReaderMetadata:
        return self._metadata

    def query_variant(
        self,
        chrom: str,
        position: int,
        ref: str,
        alt: str,
    ) -> tuple[IndexedPredictorScore, ...]:
        requested_ref = ref.strip().upper()
        requested_alt = alt.strip().upper()
        return tuple(
            score
            for score in self.query_position(chrom, position)
            if score.ref.upper() == requested_ref and score.alt.upper() == requested_alt
        )

    def query_position(self, chrom: str, position: int) -> tuple[IndexedPredictorScore, ...]:
        contig = self._normalize_contig(chrom)
        _validate_interval(contig, position, position)
        try:
            lines = self._tabix.fetch(contig, position - 1, position)
        except ValueError as exc:
            raise IndexedSourceError(
                "indexed_query_failed",
                "pysam failed to query indexed predictor TSV",
                {"chrom": contig, "position": position},
            ) from exc
        out: list[IndexedPredictorScore] = []
        for line in lines:
            if not line or line.startswith("#"):
                continue
            score = self._to_score(chrom, line)
            if score.position != position:
                continue
            if len(out) >= self._max_records:
                raise IndexedSourceError(
                    "indexed_predictor_query_too_many_records",
                    "indexed predictor TSV query returned more rows than the configured cap",
                    {
                        "chrom": contig,
                        "position": position,
                        "max_records": self._max_records,
                    },
                )
            out.append(score)
        return tuple(out)

    def _to_score(self, requested_chrom: str, line: str) -> IndexedPredictorScore:
        fields = tuple(line.rstrip("\n").split(self._delimiter))
        max_column = self._max_column_index()
        if len(fields) <= max_column:
            raise IndexedSourceError(
                "malformed_predictor_tsv_row",
                "indexed predictor TSV row has fewer fields than the configured schema",
                {"field_count": len(fields), "required_index": max_column},
            )
        try:
            position = int(fields[self._columns.position])
        except ValueError as exc:
            raise IndexedSourceError(
                "malformed_predictor_tsv_row",
                "indexed predictor TSV row has a non-integer position",
                {"position": fields[self._columns.position]},
            ) from exc
        return IndexedPredictorScore(
            requested_chrom=requested_chrom,
            chrom=_normalize_contig_alias(fields[self._columns.chrom]),
            position=position,
            ref=fields[self._columns.ref],
            alt=fields[self._columns.alt],
            score=_float_or_text(fields[self._columns.score]),
            source_id=self._source_id,
            raw_fields=fields,
            extra={
                name: fields[index]
                for name, index in self._columns.extra_columns
                if index < len(fields)
            },
        )

    def _normalize_contig(self, chrom: str) -> str:
        alias = _normalize_contig_alias(chrom)
        try:
            return self._alias_to_contig[alias]
        except KeyError as exc:
            raise IndexedSourceError(
                "unknown_contig",
                "contig is not present in indexed predictor TSV",
                {"requested_chrom": chrom},
            ) from exc

    def _validate_indexed_file(self) -> None:
        _validate_file(self._path, code_prefix="indexed_predictor_tsv")
        if not self._index_path.exists():
            raise IndexedSourceError(
                "missing_index",
                "indexed predictor TSV requires a tabix .tbi index",
                {"path": str(self._path), "index_path": str(self._index_path)},
            )
        if not self._index_path.is_file():
            raise IndexedSourceError(
                "index_not_file",
                "tabix index path is not a file",
                {"path": str(self._path), "index_path": str(self._index_path)},
            )

    def _validate_columns(self) -> None:
        for name, index in (
            ("chrom", self._columns.chrom),
            ("position", self._columns.position),
            ("ref", self._columns.ref),
            ("alt", self._columns.alt),
            ("score", self._columns.score),
            *self._columns.extra_columns,
        ):
            if index < 0:
                raise IndexedSourceError(
                    "invalid_predictor_tsv_schema",
                    "indexed predictor TSV column indexes must be non-negative",
                    {"column": name, "index": index},
                )

    def _max_column_index(self) -> int:
        return max(
            self._columns.chrom,
            self._columns.position,
            self._columns.ref,
            self._columns.alt,
            self._columns.score,
            *(index for _, index in self._columns.extra_columns),
        )


class PyBigWigConservationReader:
    """pyBigWig-backed conservation reader using 1-based inclusive coordinates."""

    def __init__(
        self,
        path: Path,
        *,
        source_id: str = "ucsc_phylop100way_hg38",
        max_window_bp: int = DEFAULT_CONSERVATION_MAX_WINDOW_BP,
    ) -> None:
        self._path = path
        self._source_id = source_id
        self._max_window_bp = max(1, int(max_window_bp))
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
        _validate_window_width(
            contig,
            start,
            end,
            max_window_bp=self._max_window_bp,
            code="conservation_window_too_large",
        )
        values = self._bigwig.values(contig, start - 1, end)
        total = 0.0
        count = 0
        for value in values:
            if value is None:
                continue
            numeric = float(value)
            if math.isnan(numeric):
                continue
            total += numeric
            count += 1
        if count == 0:
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
            mean_score=total / count,
            bases_with_scores=count,
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
        sorted_intervals = tuple(
            sorted(intervals, key=lambda item: (item.chrom, item.start, item.end))
        )
        if not sorted_intervals:
            raise IndexedSourceError(
                "empty_repeatmasker_index",
                "RepeatMasker interval index has no records",
            )
        intervals_by_contig: dict[str, list[RepeatMaskerInterval]] = {}
        for interval in sorted_intervals:
            intervals_by_contig.setdefault(interval.chrom, []).append(interval)
        self._intervals_by_contig = {
            contig: tuple(items) for contig, items in intervals_by_contig.items()
        }
        self._starts_by_contig = {
            contig: tuple(item.start for item in items)
            for contig, items in self._intervals_by_contig.items()
        }
        self._max_span_by_contig = {
            contig: max(item.end - item.start + 1 for item in items)
            for contig, items in self._intervals_by_contig.items()
        }
        self._contigs = tuple(self._intervals_by_contig)
        self._alias_to_contig = _build_alias_map(self._contigs)

    @classmethod
    def from_ucsc_rmsk_rows(cls, rows: Iterable[str]) -> RepeatMaskerIndexedTable:
        return cls(_parse_ucsc_rmsk_row(row) for row in rows if row.strip())

    def query(self, chrom: str, start: int, end: int) -> tuple[RepeatMaskerInterval, ...]:
        contig = self._normalize_contig(chrom)
        _validate_interval(contig, start, end)
        intervals = self._intervals_by_contig[contig]
        starts = self._starts_by_contig[contig]
        max_span = self._max_span_by_contig[contig]
        lower_start = max(1, start - max_span + 1)
        lower_index = bisect_left(starts, lower_start)
        upper_index = bisect_right(starts, end)
        return tuple(
            interval for interval in intervals[lower_index:upper_index] if interval.end >= start
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
        canonical_chrom = _normalize_contig_alias(chrom)
        raise IndexedSourceError(
            "out_of_bounds",
            "indexed source query exceeds contig length",
            {
                "chrom": canonical_chrom,
                "start": start,
                "end": end,
                "contig_length": contig_length,
            },
        )


def _validate_window_width(
    chrom: str,
    start: int,
    end: int,
    *,
    max_window_bp: int,
    code: str,
) -> None:
    width = end - start + 1
    if width > max_window_bp:
        raise IndexedSourceError(
            code,
            "indexed source query window exceeds the configured base-pair cap",
            {
                "chrom": _normalize_contig_alias(chrom),
                "start": start,
                "end": end,
                "window_bp": width,
                "max_window_bp": max_window_bp,
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


def _float_or_text(value: str) -> float | str:
    try:
        return float(value)
    except ValueError:
        return value
