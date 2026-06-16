from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Mapping

from app.core.paths import find_project_root, repo_relative_path
from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry
from app.services.indexed_sources import (
    IndexedSourceError,
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


class RepeatMaskerLocalStore:
    """Fixture-first RepeatMasker adapter using deterministic rmsk.txt rows."""

    def __init__(
        self,
        rmsk_path: Path | None = None,
        registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    ) -> None:
        self._rmsk_path = rmsk_path or DEFAULT_REPEATMASKER_FIXTURE_PATH
        self._provenance = _source_provenance(self._rmsk_path, registry)
        self._table = RepeatMaskerIndexedTable.from_ucsc_rmsk_rows(
            _iter_fixture_lines(self._rmsk_path)
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


def _source_provenance(
    path: Path,
    registry: DataSourceRegistry,
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
        source_format=decision.fixture_format,
    )


def _iter_fixture_lines(path: Path) -> Iterable[str]:
    try:
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
