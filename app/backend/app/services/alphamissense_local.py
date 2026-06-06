from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

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
