from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry

DEFAULT_REFERENCE_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "reference_genome" / "hg38_tiny.json"
)


class ReferenceGenomeStoreError(ValueError):
    """Structured error for invalid reference genome requests."""

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
class ReferenceGenomeMetadata:
    source_id: str
    source_url: str | None
    source_version: str
    genome_build: str
    relative_path: str
    path: Path
    checksum_algorithm: str
    checksum: str
    reader: str
    source_local_path: str | None
    source_local_md5: str | None
    source_local_size_bytes: int | None


@dataclass(frozen=True)
class ReferenceWindow:
    requested_chrom: str
    chrom: str
    start: int
    end: int
    zero_based_start: int
    zero_based_end_exclusive: int
    sequence: str
    genome_build: str
    source_id: str

    @property
    def length(self) -> int:
        return len(self.sequence)


@dataclass(frozen=True)
class ReferenceBaseCheck:
    requested_chrom: str
    chrom: str
    position: int
    expected_base: str
    observed_base: str | None
    matches: bool
    reason: str
    genome_build: str
    source_id: str


class ReferenceGenomeStore:
    """Fixture-backed reference genome store using 1-based inclusive coordinates."""

    def __init__(
        self,
        fixture_path: Path | None = None,
        registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    ) -> None:
        self._fixture_path = fixture_path or DEFAULT_REFERENCE_FIXTURE_PATH
        self._fixture = _load_fixture(self._fixture_path)
        self._chromosomes = _parse_chromosomes(self._fixture)
        self._alias_to_chrom = _build_alias_map(self._chromosomes)
        self._metadata = self._build_metadata(registry)

    def metadata(self) -> ReferenceGenomeMetadata:
        return self._metadata

    def get_sequence(
        self,
        chrom: str,
        start: int,
        end: int,
        build: str | None = None,
    ) -> ReferenceWindow:
        self._validate_build(build)
        normalized_chrom = self._normalize_chromosome(chrom)
        sequence = self._chromosomes[normalized_chrom]["sequence"]
        self._validate_window(normalized_chrom, start, end, len(sequence))

        zero_based_start = start - 1
        zero_based_end_exclusive = end
        return ReferenceWindow(
            requested_chrom=chrom,
            chrom=normalized_chrom,
            start=start,
            end=end,
            zero_based_start=zero_based_start,
            zero_based_end_exclusive=zero_based_end_exclusive,
            sequence=sequence[zero_based_start:zero_based_end_exclusive],
            genome_build=self._metadata.genome_build,
            source_id=self._metadata.source_id,
        )

    def validate_reference_base(
        self,
        chrom: str,
        position: int,
        expected: str,
        build: str | None = None,
    ) -> ReferenceBaseCheck:
        expected_base = expected.strip().upper()
        if len(expected_base) != 1 or expected_base not in {"A", "C", "G", "T", "N"}:
            return ReferenceBaseCheck(
                requested_chrom=chrom,
                chrom=self._safe_normalize_chromosome(chrom),
                position=position,
                expected_base=expected_base,
                observed_base=None,
                matches=False,
                reason="invalid_expected_base",
                genome_build=self._metadata.genome_build,
                source_id=self._metadata.source_id,
            )

        window = self.get_sequence(chrom, position, position, build=build)
        observed_base = window.sequence
        matches = observed_base == expected_base
        return ReferenceBaseCheck(
            requested_chrom=chrom,
            chrom=window.chrom,
            position=position,
            expected_base=expected_base,
            observed_base=observed_base,
            matches=matches,
            reason="reference_base_match" if matches else "reference_base_mismatch",
            genome_build=window.genome_build,
            source_id=window.source_id,
        )

    def _build_metadata(self, registry: DataSourceRegistry) -> ReferenceGenomeMetadata:
        raw_metadata = _required_mapping(self._fixture.get("metadata"), "metadata")
        source_id = _required_string(raw_metadata.get("source_id"), "metadata.source_id")
        source_record = registry.get(source_id)

        return ReferenceGenomeMetadata(
            source_id=source_id,
            source_url=source_record.source_url,
            source_version=_required_string(
                raw_metadata.get("source_version"), "metadata.source_version"
            ),
            genome_build=_required_string(
                raw_metadata.get("genome_build"), "metadata.genome_build"
            ),
            relative_path=_repo_relative_path(self._fixture_path),
            path=self._fixture_path,
            checksum_algorithm="sha256",
            checksum=_sequence_checksum(self._chromosomes),
            reader=_required_string(raw_metadata.get("reader"), "metadata.reader"),
            source_local_path=source_record.current_local_path,
            source_local_md5=source_record.current_local_md5,
            source_local_size_bytes=source_record.actual_size_bytes_local,
        )

    def _validate_build(self, build: str | None) -> None:
        if build is None or build == self._metadata.genome_build:
            return
        raise ReferenceGenomeStoreError(
            "unsupported_build",
            f"unsupported reference genome build: {build}",
            {"requested_build": build, "available_build": self._metadata.genome_build},
        )

    def _normalize_chromosome(self, chrom: str) -> str:
        alias = _normalize_chromosome_alias(chrom)
        try:
            return self._alias_to_chrom[alias]
        except KeyError as exc:
            raise ReferenceGenomeStoreError(
                "unknown_chromosome",
                f"unknown chromosome for fixture reference genome: {chrom}",
                {"requested_chrom": chrom},
            ) from exc

    def _safe_normalize_chromosome(self, chrom: str) -> str:
        try:
            return self._normalize_chromosome(chrom)
        except ReferenceGenomeStoreError:
            return _normalize_chromosome_alias(chrom)

    @staticmethod
    def _validate_window(chrom: str, start: int, end: int, chromosome_length: int) -> None:
        if start < 1 or end < 1 or start > end:
            raise ReferenceGenomeStoreError(
                "invalid_coordinates",
                "reference genome windows use 1-based inclusive coordinates",
                {"chrom": chrom, "start": start, "end": end},
            )
        if end > chromosome_length:
            raise ReferenceGenomeStoreError(
                "out_of_bounds",
                f"requested window exceeds fixture chromosome length for {chrom}",
                {
                    "chrom": chrom,
                    "start": start,
                    "end": end,
                    "chromosome_length": chromosome_length,
                },
            )


@lru_cache(maxsize=4)
def _load_fixture(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_chromosomes(fixture: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    raw_chromosomes = _required_mapping(fixture.get("chromosomes"), "chromosomes")
    chromosomes: dict[str, dict[str, Any]] = {}
    for chrom, raw_payload in raw_chromosomes.items():
        payload = _required_mapping(raw_payload, f"chromosomes.{chrom}")
        sequence = _required_string(
            payload.get("sequence"), f"chromosomes.{chrom}.sequence"
        ).upper()
        if any(base not in {"A", "C", "G", "T", "N"} for base in sequence):
            raise ReferenceGenomeStoreError(
                "invalid_fixture_sequence",
                f"fixture chromosome {chrom} contains unsupported bases",
                {"chrom": chrom},
            )
        aliases = _required_string_tuple(payload.get("aliases"), f"chromosomes.{chrom}.aliases")
        canonical_chrom = _normalize_chromosome_alias(str(chrom))
        chromosomes[canonical_chrom] = {"aliases": aliases, "sequence": sequence}
    if not chromosomes:
        raise ReferenceGenomeStoreError(
            "empty_fixture", "reference genome fixture has no chromosomes"
        )
    return chromosomes


def _build_alias_map(chromosomes: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    alias_to_chrom: dict[str, str] = {}
    for chrom, payload in chromosomes.items():
        aliases = tuple(payload["aliases"])
        for alias in (chrom, *aliases):
            normalized_alias = _normalize_chromosome_alias(str(alias))
            existing = alias_to_chrom.get(normalized_alias)
            if existing is not None and existing != chrom:
                raise ReferenceGenomeStoreError(
                    "duplicate_chromosome_alias",
                    f"duplicate chromosome alias in reference fixture: {alias}",
                    {"alias": alias, "first_chrom": existing, "second_chrom": chrom},
                )
            alias_to_chrom[normalized_alias] = chrom
    return alias_to_chrom


def _normalize_chromosome_alias(chrom: str) -> str:
    normalized = chrom.strip()
    if normalized.lower().startswith("chr"):
        normalized = normalized[3:]
    normalized = normalized.upper()
    if normalized == "MT":
        return "M"
    return normalized


def _sequence_checksum(chromosomes: Mapping[str, Mapping[str, Any]]) -> str:
    digest = sha256()
    for chrom in sorted(chromosomes):
        sequence = str(chromosomes[chrom]["sequence"])
        digest.update(f"{chrom}\t{sequence}\n".encode("ascii"))
    return digest.hexdigest()


def _repo_relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(_repo_root()).as_posix()
    except ValueError:
        return str(path)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _required_mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReferenceGenomeStoreError(
            "invalid_fixture_metadata",
            f"{field_name} must be an object",
            {"field": field_name},
        )
    return value


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReferenceGenomeStoreError(
            "invalid_fixture_metadata",
            f"{field_name} must be a non-empty string",
            {"field": field_name},
        )
    return value


def _required_string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise ReferenceGenomeStoreError(
            "invalid_fixture_metadata",
            f"{field_name} must be a non-empty list of strings",
            {"field": field_name},
        )
    return tuple(value)
