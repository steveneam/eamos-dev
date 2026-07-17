from __future__ import annotations

from pathlib import Path

from app.services.capice import CapiceLocalAdapter
from app.services.ci_spliceai import CiSpliceAiLocalAdapter
from app.services.indexed_sources import IndexedPredictorScore, IndexedSourceError, IndexedVcfRecord
from app.services.predictor_runtime import (
    AdminPredictorRuntimeInspection,
    CAPICE_FEATURE_CACHE_SOURCE_ID,
    CAPICE_LAUNCH_GATE,
    CAPICE_SOURCE_ID,
    CI_SPLICEAI_LAUNCH_GATE,
    CI_SPLICEAI_SOURCE_ID,
    PRIMATEAI3D_LAUNCH_GATE,
    PRIMATEAI3D_SOURCE_ID,
    REVEL_LAUNCH_GATE,
    REVEL_SOURCE_ID,
)
from app.services.restricted_predictors import (
    PRIMATEAI3D_CONFIG,
    REVEL_CONFIG,
    RestrictedPredictorLocalAdapter,
)


def test_ci_spliceai_local_adapter_maps_vcf_info_with_launch_metadata(
    tmp_path: Path,
) -> None:
    adapter = CiSpliceAiLocalAdapter(
        _ready_inspection(source_id=CI_SPLICEAI_SOURCE_ID, launch_gate=CI_SPLICEAI_LAUNCH_GATE),
        score_cache_path=tmp_path / "scores.vcf.gz",
        reader_factory=lambda path: FakeVcfReader(
            (
                IndexedVcfRecord(
                    requested_chrom="1",
                    chrom="1",
                    position=101,
                    record_id=None,
                    ref="A",
                    alts=("G",),
                    info={
                        "DS_AG": 0.01,
                        "DS_AL": 0.72,
                        "DS_DG": 0.02,
                        "DS_DL": 0.03,
                        "DP_AL": -4,
                    },
                    source_id=CI_SPLICEAI_SOURCE_ID,
                ),
            )
        ),
    )

    lookup = adapter.lookup(chrom="chr1", position=101, ref="A", alt="G")

    assert lookup.available is True
    assert lookup.score is not None
    assert lookup.score.max_delta == 0.72
    assert lookup.score.max_component == "acceptor_loss"
    assert lookup.calibrated_label == "Strong splice impact"
    assert lookup.calibration_bucket is None
    assert lookup.public_serialization_allowed is True
    assert lookup.launch_gate == CI_SPLICEAI_LAUNCH_GATE
    assert lookup.warnings == ("ci_spliceai_launch_gate_metadata", CI_SPLICEAI_LAUNCH_GATE)
    assert lookup.provenance_details is not None
    assert lookup.provenance_details.source_id == CI_SPLICEAI_SOURCE_ID
    assert lookup.provenance_details.reader == "pysam_indexed_vcf_reader"


def test_ci_spliceai_local_adapter_fails_closed_until_runtime_ready(tmp_path: Path) -> None:
    adapter = CiSpliceAiLocalAdapter(
        AdminPredictorRuntimeInspection(
            source_id=CI_SPLICEAI_SOURCE_ID,
            status="score_cache_missing",
            available=False,
            launch_gate=CI_SPLICEAI_LAUNCH_GATE,
            status_notes=("score_cache_materialization_required",),
            components=(),
        ),
        score_cache_path=tmp_path / "scores.vcf.gz",
        reader_factory=lambda path: FakeVcfReader(()),
    )

    lookup = adapter.lookup(chrom="1", position=101, ref="A", alt="G")

    assert lookup.available is False
    assert lookup.unavailable_reason == "score_cache_missing"
    assert lookup.warnings == ("ci_spliceai_score_cache_missing",)


def test_capice_local_adapter_maps_tabix_score_with_launch_metadata(
    tmp_path: Path,
) -> None:
    adapter = CapiceLocalAdapter(
        _ready_inspection(source_id=CAPICE_SOURCE_ID, launch_gate=CAPICE_LAUNCH_GATE),
        feature_cache_path=tmp_path / "features.tsv.gz",
        reader_factory=lambda path: FakePredictorReader(
            (
                IndexedPredictorScore(
                    requested_chrom="1",
                    chrom="1",
                    position=101,
                    ref="A",
                    alt="G",
                    score=0.83,
                    source_id=CAPICE_FEATURE_CACHE_SOURCE_ID,
                    raw_fields=(),
                    extra={"interpretation": "deleterious", "source_version": "test-cache-v1"},
                ),
            )
        ),
    )

    lookup = adapter.lookup(chrom="chr1", position=101, ref="A", alt="G")

    assert lookup.available is True
    assert lookup.score is not None
    assert lookup.score.score == 0.83
    assert lookup.score.interpretation == "deleterious"
    assert lookup.score.source_version == "test-cache-v1"
    assert lookup.public_serialization_allowed is True
    assert lookup.launch_gate == CAPICE_LAUNCH_GATE
    assert lookup.warnings == ("capice_launch_gate_metadata", CAPICE_LAUNCH_GATE)
    assert lookup.provenance_details is not None
    assert lookup.provenance_details.source_id == CAPICE_SOURCE_ID
    assert lookup.provenance_details.feature_cache_source_id == CAPICE_FEATURE_CACHE_SOURCE_ID


def test_capice_local_adapter_handles_reader_errors_as_unavailable(tmp_path: Path) -> None:
    adapter = CapiceLocalAdapter(
        _ready_inspection(source_id=CAPICE_SOURCE_ID, launch_gate=CAPICE_LAUNCH_GATE),
        feature_cache_path=tmp_path / "features.tsv.gz",
        reader_factory=lambda path: ExplodingPredictorReader(),
    )

    lookup = adapter.lookup(chrom="chr7", position=101, ref="A", alt="G")

    assert lookup.available is False
    assert lookup.unavailable_reason == "unknown_contig"
    assert lookup.warnings == ("capice_unknown_contig",)


def test_revel_local_adapter_maps_tabix_score_with_launch_metadata(tmp_path: Path) -> None:
    adapter = RestrictedPredictorLocalAdapter(
        _ready_inspection(source_id=REVEL_SOURCE_ID, launch_gate=REVEL_LAUNCH_GATE),
        score_cache_path=tmp_path / "revel.tsv.gz",
        config=REVEL_CONFIG,
        reader_factory=lambda path: FakePredictorReader(
            (
                IndexedPredictorScore(
                    requested_chrom="1",
                    chrom="1",
                    position=101,
                    ref="A",
                    alt="G",
                    score=0.78,
                    source_id=REVEL_SOURCE_ID,
                    raw_fields=(),
                    extra={"interpretation": "damaging", "source_version": "REVEL test cache"},
                ),
            )
        ),
    )

    lookup = adapter.lookup(chrom="chr1", position=101, ref="A", alt="G")

    assert lookup.available is True
    assert lookup.score is not None
    assert lookup.score.name == "REVEL"
    assert lookup.score.score == 0.78
    assert lookup.calibrated_label == "PP3 Moderate"
    assert lookup.calibration_bucket is None
    assert lookup.public_serialization_allowed is True
    assert lookup.launch_gate == REVEL_LAUNCH_GATE
    assert lookup.warnings == ("revel_launch_gate_metadata", REVEL_LAUNCH_GATE)
    assert lookup.provenance_details is not None
    assert lookup.provenance_details.source_id == REVEL_SOURCE_ID
    assert lookup.provenance_details.reader == "tabix_tsv_predictor_reader"


def test_primateai3d_local_adapter_maps_tabix_score_with_launch_metadata(
    tmp_path: Path,
) -> None:
    adapter = RestrictedPredictorLocalAdapter(
        _ready_inspection(source_id=PRIMATEAI3D_SOURCE_ID, launch_gate=PRIMATEAI3D_LAUNCH_GATE),
        score_cache_path=tmp_path / "primateai3d.tsv.gz",
        config=PRIMATEAI3D_CONFIG,
        reader_factory=lambda path: FakePredictorReader(
            (
                IndexedPredictorScore(
                    requested_chrom="1",
                    chrom="1",
                    position=101,
                    ref="A",
                    alt="G",
                    score=0.61,
                    source_id=PRIMATEAI3D_SOURCE_ID,
                    raw_fields=(),
                    extra={
                        "interpretation": "deleterious",
                        "source_version": "PrimateAI-3D test cache",
                    },
                ),
            )
        ),
    )

    lookup = adapter.lookup(chrom="chr1", position=101, ref="A", alt="G")

    assert lookup.available is True
    assert lookup.score is not None
    assert lookup.score.name == "PrimateAI-3D"
    assert lookup.score.score == 0.61
    assert lookup.calibrated_label == "Indeterminate"
    assert lookup.calibration_bucket is None
    assert lookup.public_serialization_allowed is True
    assert lookup.launch_gate == PRIMATEAI3D_LAUNCH_GATE
    assert lookup.warnings == ("primateai3d_launch_gate_metadata", PRIMATEAI3D_LAUNCH_GATE)
    assert lookup.provenance_details is not None
    assert lookup.provenance_details.source_id == PRIMATEAI3D_SOURCE_ID


def test_restricted_predictor_local_adapter_fails_closed_until_runtime_ready(
    tmp_path: Path,
) -> None:
    adapter = RestrictedPredictorLocalAdapter(
        AdminPredictorRuntimeInspection(
            source_id=REVEL_SOURCE_ID,
            status="score_cache_missing",
            available=False,
            launch_gate=REVEL_LAUNCH_GATE,
            status_notes=("score_cache_materialization_required",),
            components=(),
        ),
        score_cache_path=tmp_path / "revel.tsv.gz",
        config=REVEL_CONFIG,
        reader_factory=lambda path: FakePredictorReader(()),
    )

    lookup = adapter.lookup(chrom="1", position=101, ref="A", alt="G")

    assert lookup.available is False
    assert lookup.unavailable_reason == "score_cache_missing"
    assert lookup.warnings == ("revel_score_cache_missing",)


class FakeVcfReader:
    def __init__(self, records: tuple[IndexedVcfRecord, ...]) -> None:
        self.records = records

    def close(self) -> None:
        return None

    def query_position(self, chrom: str, position: int) -> tuple[IndexedVcfRecord, ...]:
        return tuple(record for record in self.records if record.position == position)


class FakePredictorReader:
    def __init__(self, scores: tuple[IndexedPredictorScore, ...]) -> None:
        self.scores = scores

    def close(self) -> None:
        return None

    def query_variant(
        self,
        chrom: str,
        position: int,
        ref: str,
        alt: str,
    ) -> tuple[IndexedPredictorScore, ...]:
        return self.scores


class ExplodingPredictorReader:
    def close(self) -> None:
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


def _ready_inspection(*, source_id: str, launch_gate: str) -> AdminPredictorRuntimeInspection:
    return AdminPredictorRuntimeInspection(
        source_id=source_id,
        status="ready",
        available=True,
        launch_gate=launch_gate,
        status_notes=(),
        components=(),
    )
