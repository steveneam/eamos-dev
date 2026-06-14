from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from app.core.config import Settings
from app.data_sources.registry import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry
from app.services.computational_calibration import calibration_field_values
from app.services.indexed_sources import (
    IndexedPredictorScore,
    IndexedSourceError,
    TabixTsvPredictorColumns,
    TabixTsvPredictorReader,
)
from app.services.predictor_runtime import (
    ALPHAMISSENSE_SOURCE_ID,
    PredictorRuntimeInspection,
    inspect_alphamissense_runtime_asset,
)


class AlphaMissenseReader(Protocol):
    def __enter__(self) -> AlphaMissenseReader: ...

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None: ...

    def query_position(self, chrom: str, position: int) -> tuple[IndexedPredictorScore, ...]: ...

    def query_variant(
        self,
        chrom: str,
        position: int,
        ref: str,
        alt: str,
    ) -> tuple[IndexedPredictorScore, ...]: ...


class AlphaMissenseReaderFactory(Protocol):
    def __call__(self, path: Path) -> AlphaMissenseReader: ...


@dataclass(frozen=True)
class AlphaMissenseProvenance:
    source_id: str
    source_version: str | None
    source_url: str | None
    file_name: str
    reader: str


@dataclass(frozen=True)
class AlphaMissensePrediction:
    chrom: str
    position: int
    ref: str
    alt: str
    am_pathogenicity: float
    am_class: str | None
    genome: str | None
    uniprot_id: str | None
    transcript_id: str | None
    protein_variant: str | None
    calibrated_label: str | None
    calibration_bucket: str | None
    calibration_method: str | None
    calibration_version: str | None
    provenance: AlphaMissenseProvenance


@dataclass(frozen=True)
class AlphaMissenseLookup:
    available: bool
    prediction: AlphaMissensePrediction | None
    unavailable_reason: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class AlphaMissenseResidueScore:
    aa: int
    mean_score: float | None
    max_score: float | None
    scored_variant_count: int


@dataclass(frozen=True)
class AlphaMissenseHeatmap:
    status: Literal["available", "unavailable", "partial"]
    fail_closed_reason: str | None
    protein_length: int | None
    aa_start: int
    aa_end: int | None
    source_id: str
    source_release: str | None
    calibrated_method: str | None
    queried_aa: int | None
    queried_score: float | None
    queried_calibrated_label: str | None
    residues: tuple[AlphaMissenseResidueScore, ...]
    warnings: tuple[str, ...] = ()


class AlphaMissenseLocalAdapter:
    """Internal AlphaMissense tabix adapter.

    The report evidence path reads this adapter after materialization preflight
    succeeds. Missing or malformed runtime assets fail closed with warnings.
    """

    def __init__(
        self,
        inspection: PredictorRuntimeInspection,
        *,
        registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
        reader_factory: AlphaMissenseReaderFactory | None = None,
    ) -> None:
        self._inspection = inspection
        self._record = registry.get(ALPHAMISSENSE_SOURCE_ID)
        self._reader_factory = reader_factory or _default_reader_factory

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
        reader_factory: AlphaMissenseReaderFactory | None = None,
    ) -> AlphaMissenseLocalAdapter:
        inspection = inspect_alphamissense_runtime_asset(settings, registry=registry)
        return cls(inspection, registry=registry, reader_factory=reader_factory)

    def lookup(
        self,
        *,
        chrom: str,
        position: int,
        ref: str,
        alt: str,
    ) -> AlphaMissenseLookup:
        if not self._inspection.ready:
            return AlphaMissenseLookup(
                available=False,
                prediction=None,
                unavailable_reason=self._inspection.status.value,
                warnings=(f"alphamissense_{self._inspection.status.value}",),
            )
        if position < 1:
            return AlphaMissenseLookup(
                available=False,
                prediction=None,
                unavailable_reason="invalid_coordinates",
                warnings=("alphamissense_invalid_coordinates",),
            )
        try:
            with self._reader_factory(self._inspection.path) as reader:
                matches = reader.query_variant(chrom, position, ref, alt)
        except IndexedSourceError as exc:
            return AlphaMissenseLookup(
                available=False,
                prediction=None,
                unavailable_reason=exc.code,
                warnings=(f"alphamissense_{exc.code}",),
            )

        if not matches:
            return AlphaMissenseLookup(
                available=False,
                prediction=None,
                unavailable_reason="variant_not_found",
                warnings=("alphamissense_variant_not_found",),
            )
        if len(matches) > 1:
            return AlphaMissenseLookup(
                available=False,
                prediction=None,
                unavailable_reason="duplicate_variant_records",
                warnings=("alphamissense_duplicate_variant_records",),
            )
        prediction = self._prediction_from_score(matches[0])
        if prediction is None:
            return AlphaMissenseLookup(
                available=False,
                prediction=None,
                unavailable_reason="malformed_score",
                warnings=("alphamissense_malformed_score",),
            )
        return AlphaMissenseLookup(available=True, prediction=prediction)

    def heatmap(
        self,
        *,
        chrom: str,
        genomic_strand: str = "+",
        coding_sequence: str,
        coding_genomic_positions: tuple[int, ...],
        protein_length: int | None,
        aa_start: int,
        aa_end: int,
        queried_cds_pos: int | None = None,
        queried_ref: str | None = None,
        queried_alt: str | None = None,
        queried_aa: int | None = None,
    ) -> AlphaMissenseHeatmap:
        if not self._inspection.ready:
            return self._unavailable_heatmap(
                self._inspection.status.value,
                protein_length=protein_length,
                aa_start=aa_start,
                aa_end=aa_end,
                queried_aa=queried_aa,
                warnings=(f"alphamissense_{self._inspection.status.value}",),
            )
        sequence = coding_sequence.strip().upper()
        if (
            not sequence
            or len(sequence) != len(coding_genomic_positions)
            or aa_start < 1
            or aa_end < aa_start
        ):
            return self._unavailable_heatmap(
                "invalid_heatmap_request",
                protein_length=protein_length,
                aa_start=aa_start,
                aa_end=aa_end,
                queried_aa=queried_aa,
                warnings=("alphamissense_invalid_heatmap_request",),
            )

        bounded_end = min(aa_end, max(1, len(sequence) // 3))
        reverse_strand = genomic_strand.strip() == "-"
        queried_genomic_ref = _genomic_allele(queried_ref, reverse_strand)
        queried_genomic_alt = _genomic_allele(queried_alt, reverse_strand)
        residues: list[AlphaMissenseResidueScore] = []
        queried_score: float | None = None
        queried_calibrated_label: str | None = None
        position_cache: dict[int, tuple[IndexedPredictorScore, ...]] = {}
        try:
            with self._reader_factory(self._inspection.path) as reader:
                for aa in range(aa_start, bounded_end + 1):
                    codon_start = (aa - 1) * 3
                    scores: list[float] = []
                    for offset in range(3):
                        cds_index = codon_start + offset
                        if cds_index >= len(sequence):
                            continue
                        genomic_position = coding_genomic_positions[cds_index]
                        ref = _genomic_allele(sequence[cds_index], reverse_strand)
                        rows = position_cache.get(genomic_position)
                        if rows is None:
                            rows = reader.query_position(chrom, genomic_position)
                            position_cache[genomic_position] = rows
                        for row in rows:
                            row_ref = row.ref.upper()
                            row_alt = row.alt.upper()
                            if row_ref != ref:
                                continue
                            if isinstance(row.score, str):
                                continue
                            if row_alt == ref or row_alt not in {"A", "C", "G", "T"}:
                                continue
                            scores.append(float(row.score))
                            if (
                                queried_cds_pos is not None
                                and queried_genomic_ref is not None
                                and queried_genomic_alt is not None
                                and cds_index + 1 == queried_cds_pos
                                and row_ref == queried_genomic_ref
                                and row_alt == queried_genomic_alt
                            ):
                                queried_score = float(row.score)
                                calibration = calibration_field_values(
                                    "AlphaMissense",
                                    queried_score,
                                )
                                queried_calibrated_label = calibration["calibrated_label"]
                    residues.append(
                        AlphaMissenseResidueScore(
                            aa=aa,
                            mean_score=(sum(scores) / len(scores) if scores else None),
                            max_score=(max(scores) if scores else None),
                            scored_variant_count=len(scores),
                        )
                    )
        except IndexedSourceError as exc:
            return self._unavailable_heatmap(
                exc.code,
                protein_length=protein_length,
                aa_start=aa_start,
                aa_end=bounded_end,
                queried_aa=queried_aa,
                warnings=(f"alphamissense_{exc.code}",),
            )

        scored_count = sum(1 for residue in residues if residue.scored_variant_count > 0)
        if scored_count == 0:
            return self._unavailable_heatmap(
                "no_scores_in_window",
                protein_length=protein_length,
                aa_start=aa_start,
                aa_end=bounded_end,
                queried_aa=queried_aa,
                warnings=("alphamissense_no_scores_in_window",),
            )
        return AlphaMissenseHeatmap(
            status="available" if scored_count == len(residues) else "partial",
            fail_closed_reason=None,
            protein_length=protein_length,
            aa_start=aa_start,
            aa_end=bounded_end,
            source_id=ALPHAMISSENSE_SOURCE_ID,
            source_release=self._record.source_version,
            calibrated_method="Bergquist 2025 / ClinGen SVI PP3/BP4",
            queried_aa=queried_aa,
            queried_score=queried_score,
            queried_calibrated_label=queried_calibrated_label,
            residues=tuple(residues),
            warnings=(
                () if scored_count == len(residues) else ("alphamissense_heatmap_partial_window",)
            ),
        )

    def _prediction_from_score(
        self,
        score: IndexedPredictorScore,
    ) -> AlphaMissensePrediction | None:
        if isinstance(score.score, str):
            return None
        calibration = calibration_field_values("AlphaMissense", score.score)
        return AlphaMissensePrediction(
            chrom=score.chrom,
            position=score.position,
            ref=score.ref.upper(),
            alt=score.alt.upper(),
            am_pathogenicity=float(score.score),
            am_class=_optional_extra(score, "am_class"),
            genome=_optional_extra(score, "genome"),
            uniprot_id=_optional_extra(score, "uniprot_id"),
            transcript_id=_optional_extra(score, "transcript_id"),
            protein_variant=_optional_extra(score, "protein_variant"),
            calibrated_label=calibration["calibrated_label"],
            calibration_bucket=calibration["calibration_bucket"],
            calibration_method=calibration["calibration_method"],
            calibration_version=calibration["calibration_version"],
            provenance=AlphaMissenseProvenance(
                source_id=ALPHAMISSENSE_SOURCE_ID,
                source_version=self._record.source_version,
                source_url=self._record.source_url,
                file_name=self._inspection.path.name,
                reader="tabix_tsv_predictor_reader",
            ),
        )

    def _unavailable_heatmap(
        self,
        reason: str,
        *,
        protein_length: int | None,
        aa_start: int,
        aa_end: int | None,
        queried_aa: int | None,
        warnings: tuple[str, ...],
    ) -> AlphaMissenseHeatmap:
        return AlphaMissenseHeatmap(
            status="unavailable",
            fail_closed_reason=reason,
            protein_length=protein_length,
            aa_start=aa_start,
            aa_end=aa_end,
            source_id=ALPHAMISSENSE_SOURCE_ID,
            source_release=self._record.source_version,
            calibrated_method="Bergquist 2025 / ClinGen SVI PP3/BP4",
            queried_aa=queried_aa,
            queried_score=None,
            queried_calibrated_label=None,
            residues=(),
            warnings=warnings,
        )


_BASE_COMPLEMENT = str.maketrans("ACGT", "TGCA")


def _genomic_allele(value: str | None, reverse_strand: bool) -> str | None:
    if value is None:
        return None
    allele = value.strip().upper()
    if not allele or not reverse_strand:
        return allele
    return allele.translate(_BASE_COMPLEMENT)[::-1]


def _default_reader_factory(path: Path) -> AlphaMissenseReader:
    return TabixTsvPredictorReader(
        path,
        source_id=ALPHAMISSENSE_SOURCE_ID,
        columns=TabixTsvPredictorColumns(
            score=8,
            extra_columns=(
                ("genome", 4),
                ("uniprot_id", 5),
                ("transcript_id", 6),
                ("protein_variant", 7),
                ("am_class", 9),
            ),
        ),
    )


def _optional_extra(score: IndexedPredictorScore, key: str) -> str | None:
    value = score.extra.get(key)
    if value is None:
        return None
    text = value.strip()
    return text or None
