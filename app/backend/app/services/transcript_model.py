from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry

MANE_SOURCE_ID = "ncbi_mane_grch38_v1_4_select_ensembl"
GENCODE_SOURCE_ID = "gencode_v45_annotation"
DEFAULT_TRANSCRIPT_MODEL_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "transcript_models"
    / "mane_gencode_tiny.json"
)


class TranscriptModelStoreError(ValueError):
    """Structured error for malformed local transcript model fixtures."""

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
class TranscriptModelSource:
    source_id: str
    source_url: str | None
    source_version: str | None


@dataclass(frozen=True)
class TranscriptModelProvenance:
    fixture_version: str
    source_ids: tuple[str, ...]
    sources: tuple[TranscriptModelSource, ...]
    checksum_algorithm: str
    checksum: str
    relative_path: str


@dataclass(frozen=True)
class TranscriptExonInterval:
    number: int
    cds_start: int
    cds_end: int
    genomic_start: int
    genomic_end: int

    @property
    def cds_length(self) -> int:
        return self.cds_end - self.cds_start + 1

    @property
    def genomic_length(self) -> int:
        return self.genomic_end - self.genomic_start + 1


@dataclass(frozen=True)
class TranscriptModel:
    gene: str
    refseq_transcript: str
    ensembl_transcript: str
    chrom: str
    strand: str
    exons: tuple[TranscriptExonInterval, ...]
    provenance: TranscriptModelProvenance
    ensembl_gene_id: str | None = None
    transcript_aliases: tuple[str, ...] = ()
    genome_build: str = "GRCh38"
    gene_start: int | None = None
    gene_end: int | None = None
    cds_length: int | None = None
    protein_length: int | None = None

    @property
    def transcript_span(self) -> tuple[int | None, int | None]:
        if self.gene_start is not None and self.gene_end is not None:
            return (self.gene_start, self.gene_end)
        if not self.exons:
            return (None, None)
        return (
            min(exon.genomic_start for exon in self.exons),
            max(exon.genomic_end for exon in self.exons),
        )

    @property
    def coding_length(self) -> int:
        if self.cds_length is not None:
            return self.cds_length
        return sum(exon.cds_length for exon in self.exons)


@dataclass(frozen=True)
class TranscriptModelLookup:
    gene: str
    transcript: str | None
    model: TranscriptModel | None
    unavailable_reason: str | None = None
    warnings: tuple[str, ...] = ()

    @property
    def available(self) -> bool:
        return self.model is not None and self.unavailable_reason is None


class TranscriptModelStore:
    """Fixture-first local transcript/exon/CDS model store."""

    def __init__(
        self,
        fixture_path: Path | None = None,
        registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    ) -> None:
        self._fixture_path = fixture_path or DEFAULT_TRANSCRIPT_MODEL_FIXTURE_PATH
        self._fixture = _load_fixture(self._fixture_path)
        self._metadata = _required_mapping(self._fixture.get("metadata"), "metadata")
        self._provenance = self._build_provenance(registry)
        self._models = tuple(
            _model_from_record(
                record,
                genome_build=_required_string(
                    self._metadata.get("genome_build"), "metadata.genome_build"
                ),
                provenance=self._provenance,
            )
            for record in _required_list(self._fixture.get("transcripts"), "transcripts")
        )
        if not self._models:
            raise TranscriptModelStoreError(
                "empty_fixture",
                "transcript model fixture must contain at least one transcript",
            )
        self._by_gene = _build_gene_index(self._models)

    def provenance(self) -> TranscriptModelProvenance:
        return self._provenance

    def lookup(self, gene: str, transcript: str | None = None) -> TranscriptModelLookup:
        normalized_gene = gene.strip().upper()
        if not normalized_gene:
            return TranscriptModelLookup(
                gene=gene,
                transcript=transcript,
                model=None,
                unavailable_reason="invalid_gene",
                warnings=("invalid_gene",),
            )

        candidates = self._by_gene.get(normalized_gene)
        if not candidates:
            return TranscriptModelLookup(
                gene=normalized_gene,
                transcript=transcript,
                model=None,
                unavailable_reason="gene_not_found",
                warnings=("transcript_model_gene_not_found",),
            )

        if transcript is None or not transcript.strip():
            return TranscriptModelLookup(
                gene=normalized_gene,
                transcript=transcript,
                model=_choose_mane_select(candidates),
            )

        requested = _versionless(transcript)
        for model in candidates:
            aliases = (
                model.refseq_transcript,
                model.ensembl_transcript,
                *model.transcript_aliases,
            )
            if any(_versionless(alias) == requested for alias in aliases):
                return TranscriptModelLookup(
                    gene=normalized_gene,
                    transcript=transcript,
                    model=model,
                )

        return TranscriptModelLookup(
            gene=normalized_gene,
            transcript=transcript,
            model=None,
            unavailable_reason="transcript_not_found",
            warnings=("transcript_model_transcript_not_found",),
        )

    def _build_provenance(self, registry: DataSourceRegistry) -> TranscriptModelProvenance:
        fixture_source_ids = _required_string_tuple(
            self._metadata.get("source_ids"), "metadata.source_ids"
        )
        sources = tuple(
            TranscriptModelSource(
                source_id=source_id,
                source_url=registry.get(source_id).source_url,
                source_version=registry.get(source_id).source_version,
            )
            for source_id in fixture_source_ids
        )
        return TranscriptModelProvenance(
            fixture_version=_required_string(
                self._metadata.get("fixture_version"), "metadata.fixture_version"
            ),
            source_ids=fixture_source_ids,
            sources=sources,
            checksum_algorithm="sha256",
            checksum=_sha256_file(self._fixture_path),
            relative_path=_repo_relative_path(self._fixture_path),
        )


@lru_cache(maxsize=4)
def _load_fixture(path: Path) -> Mapping[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise TranscriptModelStoreError(
            "fixture_unavailable",
            "transcript model fixture is unavailable",
            {"path": str(path)},
        ) from exc
    except ValueError as exc:
        raise TranscriptModelStoreError(
            "fixture_malformed",
            "transcript model fixture is not valid JSON",
            {"path": str(path)},
        ) from exc


def _model_from_record(
    record: object,
    *,
    genome_build: str,
    provenance: TranscriptModelProvenance,
) -> TranscriptModel:
    payload = _required_mapping(record, "transcripts[]")
    gene = _required_string(payload.get("gene"), "transcripts[].gene").upper()
    exons = tuple(
        _exon_from_record(exon, field_prefix=f"{gene}.exons[]")
        for exon in _required_list(payload.get("exons"), f"{gene}.exons")
    )
    _validate_exons(
        gene=gene,
        strand=_required_string(payload.get("strand"), f"{gene}.strand"),
        exons=exons,
    )
    return TranscriptModel(
        gene=gene,
        refseq_transcript=_required_string(
            payload.get("refseq_transcript"), f"{gene}.refseq_transcript"
        ),
        ensembl_transcript=_required_string(
            payload.get("ensembl_transcript"), f"{gene}.ensembl_transcript"
        ),
        chrom=_required_string(payload.get("chrom"), f"{gene}.chrom").removeprefix("chr"),
        strand=_required_string(payload.get("strand"), f"{gene}.strand"),
        exons=exons,
        provenance=provenance,
        ensembl_gene_id=_optional_string(payload.get("ensembl_gene_id")),
        transcript_aliases=_required_string_tuple(
            payload.get("transcript_aliases"), f"{gene}.transcript_aliases"
        ),
        genome_build=genome_build,
        gene_start=_optional_int(payload.get("gene_start"), f"{gene}.gene_start"),
        gene_end=_optional_int(payload.get("gene_end"), f"{gene}.gene_end"),
        cds_length=_optional_int(payload.get("cds_length"), f"{gene}.cds_length"),
        protein_length=_optional_int(payload.get("protein_length"), f"{gene}.protein_length"),
    )


def _exon_from_record(record: object, *, field_prefix: str) -> TranscriptExonInterval:
    payload = _required_mapping(record, field_prefix)
    return TranscriptExonInterval(
        number=_required_int(payload.get("number"), f"{field_prefix}.number"),
        cds_start=_required_int(payload.get("cds_start"), f"{field_prefix}.cds_start"),
        cds_end=_required_int(payload.get("cds_end"), f"{field_prefix}.cds_end"),
        genomic_start=_required_int(payload.get("genomic_start"), f"{field_prefix}.genomic_start"),
        genomic_end=_required_int(payload.get("genomic_end"), f"{field_prefix}.genomic_end"),
    )


def _validate_exons(
    *,
    gene: str,
    strand: str,
    exons: tuple[TranscriptExonInterval, ...],
) -> None:
    if strand not in {"+", "-"}:
        raise TranscriptModelStoreError(
            "invalid_strand",
            "transcript model strand must be + or -",
            {"gene": gene, "strand": strand},
        )
    if not exons:
        raise TranscriptModelStoreError(
            "empty_transcript", "transcript has no exons", {"gene": gene}
        )

    for exon in exons:
        if exon.cds_start > exon.cds_end:
            raise TranscriptModelStoreError(
                "invalid_cds_interval",
                "exon cds_start must be <= cds_end",
                {"gene": gene, "exon": exon.number},
            )
        if exon.genomic_start > exon.genomic_end:
            raise TranscriptModelStoreError(
                "invalid_genomic_interval",
                "exon genomic_start must be <= genomic_end",
                {"gene": gene, "exon": exon.number},
            )
        if exon.cds_length != exon.genomic_length:
            raise TranscriptModelStoreError(
                "cds_genomic_length_mismatch",
                "tiny fixture exons must map CDS intervals one-to-one",
                {"gene": gene, "exon": exon.number},
            )

    cds_starts = [exon.cds_start for exon in exons]
    if cds_starts != sorted(cds_starts):
        raise TranscriptModelStoreError(
            "invalid_transcript_order",
            "fixture exons must be ordered by transcript CDS position",
            {"gene": gene},
        )

    genomic_starts = [exon.genomic_start for exon in exons]
    expected_genomic_starts = (
        sorted(genomic_starts) if strand == "+" else sorted(genomic_starts, reverse=True)
    )
    if genomic_starts != expected_genomic_starts:
        raise TranscriptModelStoreError(
            "invalid_strand_genomic_order",
            "fixture exon genomic order must match transcript strand",
            {"gene": gene, "strand": strand},
        )


def _build_gene_index(
    models: tuple[TranscriptModel, ...],
) -> dict[str, tuple[TranscriptModel, ...]]:
    by_gene: dict[str, list[TranscriptModel]] = {}
    for model in models:
        by_gene.setdefault(model.gene.upper(), []).append(model)
    return {gene: tuple(records) for gene, records in by_gene.items()}


def _choose_mane_select(candidates: tuple[TranscriptModel, ...]) -> TranscriptModel:
    for candidate in candidates:
        if any(alias.lower() == "mane select" for alias in candidate.transcript_aliases):
            return candidate
    return candidates[0]


def _versionless(identifier: str | None) -> str:
    text = str(identifier or "").strip()
    if not text:
        return ""
    return text.split(".", 1)[0]


def _required_mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TranscriptModelStoreError(
            "invalid_fixture_metadata",
            f"{field_name} must be an object",
            {"field": field_name},
        )
    return value


def _required_list(value: object, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise TranscriptModelStoreError(
            "invalid_fixture_metadata",
            f"{field_name} must be a list",
            {"field": field_name},
        )
    return value


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise TranscriptModelStoreError(
            "invalid_fixture_metadata",
            f"{field_name} must be a non-empty string",
            {"field": field_name},
        )
    return value


def _required_string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise TranscriptModelStoreError(
            "invalid_fixture_metadata",
            f"{field_name} must be a non-empty list of strings",
            {"field": field_name},
        )
    return tuple(value)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _required_int(value: object, field_name: str) -> int:
    parsed = _optional_int(value, field_name)
    if parsed is None:
        raise TranscriptModelStoreError(
            "invalid_fixture_metadata",
            f"{field_name} must be an integer",
            {"field": field_name},
        )
    return parsed


def _optional_int(value: object, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TranscriptModelStoreError(
            "invalid_fixture_metadata",
            f"{field_name} must be an integer",
            {"field": field_name},
        ) from exc


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _repo_relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(_repo_root()).as_posix()
    except ValueError:
        return str(path)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]
