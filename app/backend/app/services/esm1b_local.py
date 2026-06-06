from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.config import Settings
from app.data_sources.registry import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry
from app.services.computational_calibration import calibration_field_values
from app.services.esm1b_assembly import ESM1B_LICENSE_GATE
from app.services.indexed_sources import (
    IndexedPredictorScore,
    IndexedSourceError,
    TabixTsvPredictorColumns,
    TabixTsvPredictorReader,
)
from app.services.predictor_runtime import (
    ESM1B_SOURCE_ID,
    PredictorRuntimeInspection,
    inspect_esm1b_runtime_asset,
)


class Esm1bReader(Protocol):
    def __enter__(self) -> Esm1bReader: ...

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None: ...

    def query_variant(
        self,
        chrom: str,
        position: int,
        ref: str,
        alt: str,
    ) -> tuple[IndexedPredictorScore, ...]: ...


class Esm1bReaderFactory(Protocol):
    def __call__(self, path: Path) -> Esm1bReader: ...


@dataclass(frozen=True)
class Esm1bProvenance:
    source_id: str
    source_version: str | None
    source_url: str | None
    file_name: str
    reader: str
    license_gate: str


@dataclass(frozen=True)
class Esm1bPrediction:
    chrom: str
    position: int
    ref: str
    alt: str
    esm1b_llr: float
    acmg_band: str | None
    uniprot_isoform: str | None
    mane_tx: str | None
    aa_sub: str | None
    calibrated_label: str | None
    calibration_bucket: str | None
    calibration_method: str | None
    calibration_version: str | None
    public_serialization_allowed: bool
    provenance: Esm1bProvenance


@dataclass(frozen=True)
class Esm1bLookup:
    available: bool
    prediction: Esm1bPrediction | None
    unavailable_reason: str | None = None
    warnings: tuple[str, ...] = ()


class Esm1bLocalAdapter:
    """Internal ESM1b tabix adapter.

    The report evidence path reads this adapter after materialization preflight
    succeeds. License-gate status is preserved as metadata for launch filtering
    instead of blocking backend/admin serialization.
    """

    def __init__(
        self,
        inspection: PredictorRuntimeInspection,
        *,
        registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
        reader_factory: Esm1bReaderFactory | None = None,
    ) -> None:
        self._inspection = inspection
        self._record = registry.get(ESM1B_SOURCE_ID)
        self._reader_factory = reader_factory or _default_reader_factory

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
        reader_factory: Esm1bReaderFactory | None = None,
    ) -> Esm1bLocalAdapter:
        inspection = inspect_esm1b_runtime_asset(settings, registry=registry)
        return cls(inspection, registry=registry, reader_factory=reader_factory)

    def lookup(
        self,
        *,
        chrom: str,
        position: int,
        ref: str,
        alt: str,
    ) -> Esm1bLookup:
        if not self._inspection.ready:
            return Esm1bLookup(
                available=False,
                prediction=None,
                unavailable_reason=self._inspection.status.value,
                warnings=(f"esm1b_{self._inspection.status.value}",),
            )
        if position < 1:
            return Esm1bLookup(
                available=False,
                prediction=None,
                unavailable_reason="invalid_coordinates",
                warnings=("esm1b_invalid_coordinates",),
            )
        try:
            with self._reader_factory(self._inspection.path) as reader:
                matches = reader.query_variant(chrom, position, ref, alt)
        except IndexedSourceError as exc:
            return Esm1bLookup(
                available=False,
                prediction=None,
                unavailable_reason=exc.code,
                warnings=(f"esm1b_{exc.code}",),
            )

        if not matches:
            return Esm1bLookup(
                available=False,
                prediction=None,
                unavailable_reason="variant_not_found",
                warnings=("esm1b_variant_not_found",),
            )
        if len(matches) > 1:
            return Esm1bLookup(
                available=False,
                prediction=None,
                unavailable_reason="duplicate_variant_records",
                warnings=("esm1b_duplicate_variant_records",),
            )
        prediction = self._prediction_from_score(matches[0])
        if prediction is None:
            return Esm1bLookup(
                available=False,
                prediction=None,
                unavailable_reason="malformed_score",
                warnings=("esm1b_malformed_score",),
            )
        return Esm1bLookup(
            available=True,
            prediction=prediction,
            warnings=("esm1b_license_gate_metadata", ESM1B_LICENSE_GATE),
        )

    def _prediction_from_score(self, score: IndexedPredictorScore) -> Esm1bPrediction | None:
        if isinstance(score.score, str):
            return None
        calibration = calibration_field_values("ESM1b", score.score)
        return Esm1bPrediction(
            chrom=score.chrom,
            position=score.position,
            ref=score.ref.upper(),
            alt=score.alt.upper(),
            esm1b_llr=float(score.score),
            acmg_band=_optional_extra(score, "acmg_band"),
            uniprot_isoform=_optional_extra(score, "uniprot_isoform"),
            mane_tx=_optional_extra(score, "mane_tx"),
            aa_sub=_optional_extra(score, "aa_sub"),
            calibrated_label=calibration["calibrated_label"],
            calibration_bucket=calibration["calibration_bucket"],
            calibration_method=calibration["calibration_method"],
            calibration_version=calibration["calibration_version"],
            public_serialization_allowed=True,
            provenance=Esm1bProvenance(
                source_id=ESM1B_SOURCE_ID,
                source_version=self._record.source_version,
                source_url=self._record.source_url,
                file_name=self._inspection.path.name,
                reader="tabix_tsv_predictor_reader",
                license_gate=ESM1B_LICENSE_GATE,
            ),
        )


def _default_reader_factory(path: Path) -> Esm1bReader:
    return TabixTsvPredictorReader(
        path,
        source_id=ESM1B_SOURCE_ID,
        columns=TabixTsvPredictorColumns(
            score=4,
            extra_columns=(
                ("acmg_band", 5),
                ("uniprot_isoform", 6),
                ("mane_tx", 7),
                ("aa_sub", 8),
            ),
        ),
    )


def _optional_extra(score: IndexedPredictorScore, key: str) -> str | None:
    value = score.extra.get(key)
    if value is None:
        return None
    text = value.strip()
    return text or None
