from __future__ import annotations

from dataclasses import dataclass
import gzip
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Mapping

from app.core.paths import find_project_root, repo_relative_path
from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry
from app.services.indexed_sources import (
    IndexedSourceError,
    REPEATMASKER_COMPACT_INDEX_SCHEMA,
    RepeatMaskerIndexedTable,
    repeatmasker_path_decision,
)

REPEATMASKER_SOURCE_ID = "repeatmasker_rmsk_bb"
DEFAULT_REPEATMASKER_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "data_sources" / "repeatmasker_tiny.rmsk.txt"
)


class RepeatMaskerLocalError(ValueError):
    """Structured error for local RepeatMasker fixture failures."""

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
class RepeatMaskerLocalProvenance:
    source_id: str
    source_version: str | None
    checksum_algorithm: str
    checksum: str
    relative_path: str
    conversion_strategy: str
    source_format: str


@dataclass(frozen=True)
class RepeatMaskerLocalHit:
    chrom: str
    start: int
    end: int
    name: str
    repeat_class: str
    repeat_family: str
    strand: str
    provenance: RepeatMaskerLocalProvenance


@dataclass(frozen=True)
class RepeatMaskerLocalQuery:
    available: bool
    repeats: tuple[RepeatMaskerLocalHit, ...] = ()
    unavailable_reason: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class RepeatMaskerCompactIndexBuildResult:
    source_id: str
    source_version: str | None
    source_format: str
    output_schema: str
    interval_count: int
    output_byte_size: int
    output_sha256: str
    source_sha256: str


class RepeatMaskerLocalStore:
    """Fixture-first RepeatMasker adapter using deterministic rmsk.txt rows."""

    def __init__(
        self,
        rmsk_path: Path | None = None,
        compact_index_path: Path | None = None,
        registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    ) -> None:
        if compact_index_path is not None:
            self._source_path = compact_index_path
            self._source_format = REPEATMASKER_COMPACT_INDEX_SCHEMA
            self._table = RepeatMaskerIndexedTable.from_compact_jsonl(compact_index_path)
        else:
            self._source_path = rmsk_path or DEFAULT_REPEATMASKER_FIXTURE_PATH
            self._source_format = "ucsc_rmsk_txt_rows"
            self._table = RepeatMaskerIndexedTable.from_ucsc_rmsk_rows(
                _iter_ucsc_rmsk_lines(self._source_path)
            )
        self._provenance = _source_provenance(
            self._source_path,
            registry,
            source_format=self._source_format,
        )

    def provenance(self) -> RepeatMaskerLocalProvenance:
        return self._provenance

    def query_window(self, *, chrom: str, start: int, end: int) -> RepeatMaskerLocalQuery:
        try:
            intervals = self._table.query(chrom, start, end)
        except IndexedSourceError as exc:
            if exc.code == "unknown_contig":
                return RepeatMaskerLocalQuery(
                    available=False,
                    unavailable_reason="contig_not_found",
                    warnings=("repeatmasker_local_contig_not_found",),
                )
            if exc.code == "invalid_coordinates":
                return RepeatMaskerLocalQuery(
                    available=False,
                    unavailable_reason="invalid_coordinates",
                    warnings=("repeatmasker_local_invalid_coordinates",),
                )
            raise RepeatMaskerLocalError(
                exc.code,
                str(exc),
                exc.details,
            ) from exc
        return RepeatMaskerLocalQuery(
            available=True,
            repeats=tuple(
                RepeatMaskerLocalHit(
                    chrom=interval.chrom,
                    start=interval.start,
                    end=interval.end,
                    name=interval.name,
                    repeat_class=interval.repeat_class,
                    repeat_family=interval.repeat_family,
                    strand=interval.strand,
                    provenance=self._provenance,
                )
                for interval in intervals
            ),
        )


def build_repeatmasker_compact_index(
    *,
    source_rmsk_path: Path,
    output_path: Path,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
) -> RepeatMaskerCompactIndexBuildResult:
    record = registry.get(REPEATMASKER_SOURCE_ID)
    table = RepeatMaskerIndexedTable.from_ucsc_rmsk_rows(_iter_ucsc_rmsk_lines(source_rmsk_path))
    interval_count = table.write_compact_jsonl(
        output_path,
        source_id=REPEATMASKER_SOURCE_ID,
        source_version=record.source_version,
    )
    return RepeatMaskerCompactIndexBuildResult(
        source_id=REPEATMASKER_SOURCE_ID,
        source_version=record.source_version,
        source_format="ucsc_rmsk_txt_rows",
        output_schema=REPEATMASKER_COMPACT_INDEX_SCHEMA,
        interval_count=interval_count,
        output_byte_size=output_path.stat().st_size,
        output_sha256=_sha256_file(output_path),
        source_sha256=_sha256_file(source_rmsk_path),
    )


def _source_provenance(
    path: Path,
    registry: DataSourceRegistry,
    *,
    source_format: str,
) -> RepeatMaskerLocalProvenance:
    record = registry.get(REPEATMASKER_SOURCE_ID)
    decision = repeatmasker_path_decision()
    return RepeatMaskerLocalProvenance(
        source_id=REPEATMASKER_SOURCE_ID,
        source_version=record.source_version,
        checksum_algorithm="sha256",
        checksum=_sha256_file(path),
        relative_path=_repo_relative_path(path),
        conversion_strategy=decision.strategy,
        source_format=source_format,
    )


def _iter_ucsc_rmsk_lines(path: Path) -> Iterable[str]:
    try:
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                yield from handle
        else:
            with path.open("r", encoding="utf-8") as handle:
                yield from handle
    except OSError as exc:
        raise RepeatMaskerLocalError(
            "fixture_unavailable",
            "RepeatMasker rmsk fixture is unavailable",
            {"path": str(path)},
        ) from exc


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_relative_path(path: Path) -> str:
    return repo_relative_path(path, anchor=__file__)


def _repo_root() -> Path:
    return find_project_root(__file__)
