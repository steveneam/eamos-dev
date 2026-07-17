from __future__ import annotations

from pathlib import Path

from app.services.esm1b_assembly import ESM1B_LICENSE_GATE
from app.services.esm1b_local import Esm1bLocalAdapter
from app.services.indexed_sources import IndexedPredictorScore, IndexedSourceError
from app.services.predictor_runtime import (
    ESM1B_ASSET_ROLE,
    ESM1B_SOURCE_ID,
    PredictorRuntimeInspection,
    PredictorRuntimeStatus,
)


def test_esm1b_adapter_maps_exact_hit_with_calibration_and_license_metadata(
    tmp_path: Path,
) -> None:
    adapter = Esm1bLocalAdapter(
        _ready_inspection(tmp_path),
        reader_factory=lambda path: FakeReader(
            (
                _score(
                    chrom="7",
                    position=117509068,
                    ref="C",
                    alt="T",
                    score=-14.0,
                    extra={
                        "acmg_band": "PP3_Strong",
                        "uniprot_isoform": "P13569-1",
                        "mane_tx": "NM_000492.4",
                        "aa_sub": "V1M",
                    },
                ),
            )
        ),
    )

    lookup = adapter.lookup(chrom="chr7", position=117509068, ref="C", alt="T")

    assert lookup.available is True
    assert lookup.warnings == ("esm1b_license_gate_metadata", ESM1B_LICENSE_GATE)
    prediction = lookup.prediction
    assert prediction is not None
    assert prediction.chrom == "7"
    assert prediction.position == 117509068
    assert prediction.ref == "C"
    assert prediction.alt == "T"
    assert prediction.esm1b_llr == -14.0
    assert prediction.acmg_band == "PP3_Strong"
    assert prediction.uniprot_isoform == "P13569-1"
    assert prediction.mane_tx == "NM_000492.4"
    assert prediction.aa_sub == "V1M"
    assert prediction.calibrated_label == "PP3 3 points"
    assert prediction.calibration_bucket is None
    assert prediction.public_serialization_allowed is True
    assert prediction.provenance.source_id == ESM1B_SOURCE_ID
    assert prediction.provenance.reader == "tabix_tsv_predictor_reader"
    assert prediction.provenance.license_gate == ESM1B_LICENSE_GATE


def test_esm1b_adapter_omits_launch_gate_for_clean_regenerated_manifest(
    tmp_path: Path,
) -> None:
    adapter = Esm1bLocalAdapter(
        _ready_inspection(tmp_path, launch_gate=None),
        reader_factory=lambda path: FakeReader(
            (
                _score(
                    chrom="7",
                    position=117509068,
                    ref="C",
                    alt="T",
                    score=-14.0,
                ),
            )
        ),
    )

    lookup = adapter.lookup(chrom="chr7", position=117509068, ref="C", alt="T")

    assert lookup.available is True
    assert lookup.warnings == ()
    assert lookup.prediction is not None
    assert lookup.prediction.provenance.license_gate is None


def test_esm1b_adapter_returns_no_hit_without_guessing(tmp_path: Path) -> None:
    adapter = Esm1bLocalAdapter(
        _ready_inspection(tmp_path),
        reader_factory=lambda path: FakeReader(()),
    )

    lookup = adapter.lookup(chrom="7", position=117509068, ref="C", alt="A")

    assert lookup.available is False
    assert lookup.prediction is None
    assert lookup.unavailable_reason == "variant_not_found"
    assert lookup.warnings == ("esm1b_variant_not_found",)


def test_esm1b_adapter_fails_closed_until_preflight_ready(tmp_path: Path) -> None:
    adapter = Esm1bLocalAdapter(
        _ready_inspection(tmp_path, status=PredictorRuntimeStatus.MISSING_INDEX),
        reader_factory=lambda path: FakeReader(()),
    )

    lookup = adapter.lookup(chrom="7", position=117509068, ref="C", alt="T")

    assert lookup.available is False
    assert lookup.unavailable_reason == "missing_index"
    assert lookup.warnings == ("esm1b_missing_index",)


def test_esm1b_adapter_fails_closed_on_duplicate_records(tmp_path: Path) -> None:
    adapter = Esm1bLocalAdapter(
        _ready_inspection(tmp_path),
        reader_factory=lambda path: FakeReader(
            (
                _score(chrom="7", position=117509068, ref="C", alt="T", score=-12.2),
                _score(chrom="7", position=117509068, ref="C", alt="T", score=-14.0),
            )
        ),
    )

    lookup = adapter.lookup(chrom="7", position=117509068, ref="C", alt="T")

    assert lookup.available is False
    assert lookup.unavailable_reason == "duplicate_variant_records"
    assert lookup.warnings == ("esm1b_duplicate_variant_records",)


def test_esm1b_adapter_disambiguates_duplicate_genomic_records_by_context(
    tmp_path: Path,
) -> None:
    adapter = Esm1bLocalAdapter(
        _ready_inspection(tmp_path, launch_gate=None),
        reader_factory=lambda path: FakeReader(
            (
                _score(
                    chrom="7",
                    position=117509068,
                    ref="C",
                    alt="T",
                    score=-12.2,
                    extra={
                        "mane_tx": "NM_OTHER.1",
                        "gene": "OTHER",
                        "aa_sub": "V1M",
                    },
                ),
                _score(
                    chrom="7",
                    position=117509068,
                    ref="C",
                    alt="T",
                    score=-14.0,
                    extra={
                        "protein_sequence_id": "NP_TEST.1",
                        "protein_sequence_id_namespace": "refseq",
                        "mane_tx": "NM_TEST.1",
                        "gene": "TEST",
                        "aa_sub": "V1M",
                        "refseq_protein_id": "NP_TEST.1",
                        "ensembl_protein_id": "ENSPTEST",
                    },
                ),
            )
        ),
    )

    lookup = adapter.lookup(
        chrom="7",
        position=117509068,
        ref="C",
        alt="T",
        transcript_id="NM_TEST.1",
        gene="TEST",
        protein_change="p.Val1Met",
    )

    assert lookup.available is True
    assert lookup.prediction is not None
    assert lookup.prediction.esm1b_llr == -14.0
    assert lookup.prediction.protein_sequence_id == "NP_TEST.1"
    assert lookup.prediction.protein_sequence_id_namespace == "refseq"
    assert lookup.prediction.refseq_protein_id == "NP_TEST.1"
    assert lookup.prediction.ensembl_protein_id == "ENSPTEST"


def test_esm1b_adapter_fails_closed_when_requested_context_does_not_match(
    tmp_path: Path,
) -> None:
    adapter = Esm1bLocalAdapter(
        _ready_inspection(tmp_path),
        reader_factory=lambda path: FakeReader(
            (
                _score(
                    chrom="7",
                    position=117509068,
                    ref="C",
                    alt="T",
                    score=-14.0,
                    extra={"mane_tx": "NM_OTHER.1", "gene": "OTHER", "aa_sub": "V1M"},
                ),
            )
        ),
    )

    lookup = adapter.lookup(
        chrom="7",
        position=117509068,
        ref="C",
        alt="T",
        transcript_id="NM_TEST.1",
        gene="TEST",
        protein_change="V1M",
    )

    assert lookup.available is False
    assert lookup.unavailable_reason == "variant_context_mismatch"
    assert lookup.warnings == ("esm1b_variant_context_mismatch",)


def test_esm1b_adapter_handles_reader_errors_as_unavailable(tmp_path: Path) -> None:
    adapter = Esm1bLocalAdapter(
        _ready_inspection(tmp_path),
        reader_factory=lambda path: ExplodingReader(),
    )

    lookup = adapter.lookup(chrom="chr7", position=117509068, ref="C", alt="T")

    assert lookup.available is False
    assert lookup.unavailable_reason == "unknown_contig"
    assert lookup.warnings == ("esm1b_unknown_contig",)


def test_esm1b_adapter_rejects_malformed_non_numeric_score(tmp_path: Path) -> None:
    adapter = Esm1bLocalAdapter(
        _ready_inspection(tmp_path),
        reader_factory=lambda path: FakeReader(
            (_score(chrom="7", position=117509068, ref="C", alt="T", score="not-numeric"),)
        ),
    )

    lookup = adapter.lookup(chrom="7", position=117509068, ref="C", alt="T")

    assert lookup.available is False
    assert lookup.unavailable_reason == "malformed_score"
    assert lookup.warnings == ("esm1b_malformed_score",)


class FakeReader:
    def __init__(self, scores: tuple[IndexedPredictorScore, ...]) -> None:
        self.scores = scores

    def __enter__(self) -> FakeReader:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def query_variant(
        self,
        chrom: str,
        position: int,
        ref: str,
        alt: str,
    ) -> tuple[IndexedPredictorScore, ...]:
        return self.scores


class ExplodingReader:
    def __enter__(self) -> ExplodingReader:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def query_variant(
        self,
        chrom: str,
        position: int,
        ref: str,
        alt: str,
    ) -> tuple[IndexedPredictorScore, ...]:
        raise IndexedSourceError(
            "unknown_contig",
            "contig is not present in indexed predictor TSV",
            {"requested_chrom": chrom},
        )


def _ready_inspection(
    tmp_path: Path,
    *,
    status: PredictorRuntimeStatus = PredictorRuntimeStatus.READY,
    launch_gate: str | None = ESM1B_LICENSE_GATE,
) -> PredictorRuntimeInspection:
    asset = tmp_path / "esm1b_hg38.tsv.gz"
    asset.write_bytes(b"tiny")
    return PredictorRuntimeInspection(
        source_id=ESM1B_SOURCE_ID,
        asset_role=ESM1B_ASSET_ROLE,
        mode="local_path",
        status=status,
        path=asset,
        index_path=Path(f"{asset}.tbi"),
        manifest_path=asset.with_suffix(asset.suffix + ".manifest.json"),
        actual_size_bytes=len(b"tiny") if status is PredictorRuntimeStatus.READY else None,
        expected_md5=None,
        actual_md5=None,
        object_uri=None,
        reader_requires_local_path=True,
        bucket_file_size_limit=50 * 1024 * 1024 * 1024,
        materialization_status=None,
        message="ready" if status is PredictorRuntimeStatus.READY else status.value,
        launch_gate=launch_gate,
    )


def _score(
    *,
    chrom: str,
    position: int,
    ref: str,
    alt: str,
    score: float | str,
    extra: dict[str, str] | None = None,
) -> IndexedPredictorScore:
    return IndexedPredictorScore(
        requested_chrom=chrom,
        chrom=chrom,
        position=position,
        ref=ref,
        alt=alt,
        score=score,
        source_id=ESM1B_SOURCE_ID,
        raw_fields=(),
        extra=extra or {},
    )
