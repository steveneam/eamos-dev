from __future__ import annotations

import threading
from dataclasses import dataclass
import json
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
    license_gate: str | None


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
    protein_sequence_id: str | None = None
    protein_sequence_id_namespace: str | None = None
    gene: str | None = None
    refseq_protein_id: str | None = None
    ensembl_protein_id: str | None = None


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
        self._manifest = _read_manifest(inspection.manifest_path)
        self._reader_factory = reader_factory or (
            lambda path: _default_reader_factory(path, manifest=self._manifest)
        )
        self._reader_lock = threading.RLock()
        self._reader_path: Path | None = None
        self._reader: Esm1bReader | None = None

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
        transcript_id: str | None = None,
        gene: str | None = None,
        protein_change: str | None = None,
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
            with self._reader_lock:
                reader = self._reader_for_ready_asset()
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
        context_requested = any((transcript_id, gene, protein_change))
        if context_requested:
            matches = tuple(
                score
                for score in matches
                if _score_matches_context(
                    score,
                    transcript_id=transcript_id,
                    gene=gene,
                    protein_change=protein_change,
                )
            )
            if not matches:
                return Esm1bLookup(
                    available=False,
                    prediction=None,
                    unavailable_reason="variant_context_mismatch",
                    warnings=("esm1b_variant_context_mismatch",),
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
        warnings = (
            ("esm1b_license_gate_metadata", self._inspection.launch_gate)
            if self._inspection.launch_gate
            else ()
        )
        return Esm1bLookup(
            available=True,
            prediction=prediction,
            warnings=warnings,
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
            uniprot_isoform=(
                _optional_extra(score, "uniprot_isoform_id")
                or _optional_extra(score, "uniprot_isoform")
            ),
            mane_tx=_optional_extra(score, "mane_tx"),
            aa_sub=_optional_extra(score, "aa_sub"),
            calibrated_label=calibration["calibrated_label"],
            calibration_bucket=calibration["calibration_bucket"],
            calibration_method=calibration["calibration_method"],
            calibration_version=calibration["calibration_version"],
            public_serialization_allowed=True,
            provenance=Esm1bProvenance(
                source_id=ESM1B_SOURCE_ID,
                source_version=_manifest_source_version(self._manifest)
                or self._record.source_version,
                source_url=self._record.source_url,
                file_name=self._inspection.path.name,
                reader="tabix_tsv_predictor_reader",
                license_gate=self._inspection.launch_gate,
            ),
            protein_sequence_id=_optional_extra(score, "protein_sequence_id"),
            protein_sequence_id_namespace=_optional_extra(score, "protein_sequence_id_namespace"),
            gene=_optional_extra(score, "gene"),
            refseq_protein_id=_optional_extra(score, "refseq_protein_id"),
            ensembl_protein_id=_optional_extra(score, "ensembl_protein_id"),
        )

    def close(self) -> None:
        with self._reader_lock:
            reader = self._reader
            self._reader = None
            self._reader_path = None
            close = getattr(reader, "close", None)
            if callable(close):
                close()

    def _reader_for_ready_asset(self) -> Esm1bReader:
        path = self._inspection.path
        if self._reader is None or self._reader_path != path:
            self.close()
            self._reader = self._reader_factory(path)
            self._reader_path = path
        return self._reader


def _default_reader_factory(
    path: Path,
    *,
    manifest: dict[str, object] | None = None,
) -> Esm1bReader:
    if _is_clean_v2_manifest(manifest):
        extra_columns = (
            ("protein_sequence_id", 5),
            ("protein_sequence_id_namespace", 6),
            ("mane_tx", 7),
            ("aa_sub", 8),
            ("gene", 9),
            ("refseq_protein_id", 10),
            ("ensembl_protein_id", 11),
            ("uniprot_isoform_id", 12),
        )
    else:
        extra_columns = (
            ("acmg_band", 5),
            ("uniprot_isoform", 6),
            ("mane_tx", 7),
            ("aa_sub", 8),
        )
    return TabixTsvPredictorReader(
        path,
        source_id=ESM1B_SOURCE_ID,
        columns=TabixTsvPredictorColumns(
            score=4,
            extra_columns=extra_columns,
        ),
    )


def _optional_extra(score: IndexedPredictorScore, key: str) -> str | None:
    value = score.extra.get(key)
    if value is None:
        return None
    text = value.strip()
    return text or None


def _score_matches_context(
    score: IndexedPredictorScore,
    *,
    transcript_id: str | None,
    gene: str | None,
    protein_change: str | None,
) -> bool:
    matched_context_field = False
    if transcript_id:
        requested_transcript = transcript_id.strip().split(":", 1)[0]
        actual_transcript = _optional_extra(score, "mane_tx")
        if actual_transcript is not None:
            matched_context_field = True
            if actual_transcript != requested_transcript:
                return False
    if gene:
        actual_gene = _optional_extra(score, "gene")
        if actual_gene is not None:
            matched_context_field = True
            if actual_gene.upper() != gene.strip().upper():
                return False
    if protein_change:
        normalized = _normalize_protein_change(protein_change)
        actual_change = _optional_extra(score, "aa_sub")
        if actual_change is not None:
            matched_context_field = True
            if normalized is None or actual_change != normalized:
                return False
    return matched_context_field


_THREE_TO_ONE = {
    "Ala": "A",
    "Arg": "R",
    "Asn": "N",
    "Asp": "D",
    "Cys": "C",
    "Gln": "Q",
    "Glu": "E",
    "Gly": "G",
    "His": "H",
    "Ile": "I",
    "Leu": "L",
    "Lys": "K",
    "Met": "M",
    "Phe": "F",
    "Pro": "P",
    "Ser": "S",
    "Thr": "T",
    "Trp": "W",
    "Tyr": "Y",
    "Val": "V",
}


def _normalize_protein_change(value: str) -> str | None:
    text = value.strip()
    if text.startswith("p."):
        text = text[2:]
    if len(text) >= 3 and text[0].isalpha() and text[-1].isalpha():
        if text[0].isupper() and text[-1].isupper() and text[1:-1].isdigit():
            return text
    for ref_name, ref in _THREE_TO_ONE.items():
        if not text.startswith(ref_name):
            continue
        for alt_name, alt in _THREE_TO_ONE.items():
            if not text.endswith(alt_name):
                continue
            position = text[len(ref_name) : -len(alt_name)]
            if position.isdigit():
                return f"{ref}{position}{alt}"
    return None


def _read_manifest(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _is_clean_v2_manifest(manifest: dict[str, object] | None) -> bool:
    if not manifest:
        return False
    output_contract = manifest.get("output_contract")
    return (
        manifest.get("source_id") == "esm1b_clean_regenerated_scores"
        and manifest.get("manifest_schema_version") == "2"
        and isinstance(output_contract, dict)
        and output_contract.get("acmg_band_embedded") is False
    )


def _manifest_source_version(manifest: dict[str, object] | None) -> str | None:
    if not manifest:
        return None
    build_id = manifest.get("build_id")
    route = manifest.get("source_route")
    route_id = route.get("route_id") if isinstance(route, dict) else None
    values = [str(value).strip() for value in (route_id, build_id) if value]
    return "/".join(values) or None
