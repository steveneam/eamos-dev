from __future__ import annotations

from pathlib import Path

import pytest

from app.cli.eamos_alphamissense_runtime_materialize import _predictor_inspection_summary
from app.services.alphamissense_local import AlphaMissenseLocalAdapter
from app.services.indexed_sources import IndexedPredictorScore, IndexedSourceError
from app.services.predictor_runtime import (
    ALPHAMISSENSE_ASSET_ROLE,
    ALPHAMISSENSE_SOURCE_ID,
    PredictorRuntimeInspection,
    PredictorRuntimeStatus,
)


def test_alphamissense_adapter_maps_exact_hit_with_bergquist_calibration(
    tmp_path: Path,
) -> None:
    adapter = AlphaMissenseLocalAdapter(
        _ready_inspection(tmp_path),
        reader_factory=lambda path: FakeReader(
            (
                _score(
                    chrom="1",
                    position=101,
                    ref="A",
                    alt="G",
                    score=0.792,
                    extra={
                        "genome": "hg38",
                        "uniprot_id": "Q8NH21",
                        "transcript_id": "ENST00000335137.4",
                        "protein_variant": "V2M",
                        "am_class": "likely_pathogenic",
                    },
                ),
            )
        ),
    )

    lookup = adapter.lookup(chrom="NC_000001.11", position=101, ref="A", alt="G")

    assert lookup.available is True
    prediction = lookup.prediction
    assert prediction is not None
    assert prediction.chrom == "1"
    assert prediction.position == 101
    assert prediction.ref == "A"
    assert prediction.alt == "G"
    assert prediction.am_pathogenicity == 0.792
    assert prediction.am_class == "likely_pathogenic"
    assert prediction.uniprot_id == "Q8NH21"
    assert prediction.transcript_id == "ENST00000335137.4"
    assert prediction.protein_variant == "V2M"
    assert prediction.calibrated_label == "PP3_Strong"
    assert prediction.calibration_bucket == "Pathogenic"
    assert prediction.calibration_method == "Bergquist 2025 / ClinGen SVI PP3/BP4"
    assert prediction.provenance.source_id == ALPHAMISSENSE_SOURCE_ID
    assert prediction.provenance.reader == "tabix_tsv_predictor_reader"


def test_alphamissense_adapter_returns_no_hit_without_guessing(
    tmp_path: Path,
) -> None:
    adapter = AlphaMissenseLocalAdapter(
        _ready_inspection(tmp_path),
        reader_factory=lambda path: FakeReader(()),
    )

    lookup = adapter.lookup(chrom="1", position=101, ref="A", alt="T")

    assert lookup.available is False
    assert lookup.prediction is None
    assert lookup.unavailable_reason == "variant_not_found"
    assert lookup.warnings == ("alphamissense_variant_not_found",)


def test_alphamissense_adapter_fails_closed_until_preflight_ready(
    tmp_path: Path,
) -> None:
    adapter = AlphaMissenseLocalAdapter(
        _ready_inspection(tmp_path, status=PredictorRuntimeStatus.MISSING_INDEX),
        reader_factory=lambda path: FakeReader(()),
    )

    lookup = adapter.lookup(chrom="1", position=101, ref="A", alt="G")

    assert lookup.available is False
    assert lookup.unavailable_reason == "missing_index"
    assert lookup.warnings == ("alphamissense_missing_index",)


def test_alphamissense_adapter_fails_closed_on_duplicate_records(
    tmp_path: Path,
) -> None:
    adapter = AlphaMissenseLocalAdapter(
        _ready_inspection(tmp_path),
        reader_factory=lambda path: FakeReader(
            (
                _score(chrom="1", position=101, ref="A", alt="G", score=0.7),
                _score(chrom="1", position=101, ref="A", alt="G", score=0.8),
            )
        ),
    )

    lookup = adapter.lookup(chrom="1", position=101, ref="A", alt="G")

    assert lookup.available is False
    assert lookup.unavailable_reason == "duplicate_variant_records"
    assert lookup.warnings == ("alphamissense_duplicate_variant_records",)


def test_alphamissense_adapter_handles_reader_errors_as_unavailable(
    tmp_path: Path,
) -> None:
    adapter = AlphaMissenseLocalAdapter(
        _ready_inspection(tmp_path),
        reader_factory=lambda path: ExplodingReader(),
    )

    lookup = adapter.lookup(chrom="chr7", position=101, ref="A", alt="G")

    assert lookup.available is False
    assert lookup.unavailable_reason == "unknown_contig"
    assert lookup.warnings == ("alphamissense_unknown_contig",)


def test_alphamissense_adapter_rejects_malformed_non_numeric_score(
    tmp_path: Path,
) -> None:
    adapter = AlphaMissenseLocalAdapter(
        _ready_inspection(tmp_path),
        reader_factory=lambda path: FakeReader(
            (_score(chrom="1", position=101, ref="A", alt="G", score="not-numeric"),)
        ),
    )

    lookup = adapter.lookup(chrom="1", position=101, ref="A", alt="G")

    assert lookup.available is False
    assert lookup.unavailable_reason == "malformed_score"
    assert lookup.warnings == ("alphamissense_malformed_score",)


def test_alphamissense_adapter_builds_bounded_residue_heatmap(
    tmp_path: Path,
) -> None:
    adapter = AlphaMissenseLocalAdapter(
        _ready_inspection(tmp_path),
        reader_factory=lambda path: FakeReader(
            (
                _score(chrom="1", position=100, ref="A", alt="C", score=0.2),
                _score(chrom="1", position=100, ref="A", alt="G", score=0.8),
                _score(chrom="1", position=101, ref="A", alt="G", score=0.6),
                _score(chrom="1", position=105, ref="T", alt="C", score=0.9),
            )
        ),
    )

    heatmap = adapter.heatmap(
        chrom="1",
        coding_sequence="AAATTT",
        coding_genomic_positions=(100, 101, 102, 103, 104, 105),
        protein_length=2,
        aa_start=1,
        aa_end=2,
        queried_cds_pos=1,
        queried_ref="A",
        queried_alt="G",
        queried_aa=1,
    )

    assert heatmap.status == "available"
    assert heatmap.queried_score == 0.8
    assert heatmap.queried_calibrated_label == "PP3_Strong"
    assert [item.aa for item in heatmap.residues] == [1, 2]
    assert heatmap.residues[0].scored_variant_count == 3
    assert heatmap.residues[0].mean_score == pytest.approx((0.2 + 0.8 + 0.6) / 3)
    assert heatmap.residues[0].max_score == 0.8
    assert heatmap.residues[1].scored_variant_count == 1


def test_alphamissense_materializer_preflight_summary_is_sanitized(
    tmp_path: Path,
) -> None:
    inspection = _ready_inspection(tmp_path)

    summary = _predictor_inspection_summary(inspection)

    encoded = str(summary).lower()
    assert summary["status"] == "ready"
    assert summary["ready"] is True
    assert str(tmp_path).lower() not in encoded
    assert "alphamissense_hg38.tsv.gz.tbi" not in encoded


class FakeReader:
    def __init__(self, scores: tuple[IndexedPredictorScore, ...]) -> None:
        self.scores = scores

    def __enter__(self) -> FakeReader:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def query_position(self, chrom: str, position: int) -> tuple[IndexedPredictorScore, ...]:
        return tuple(
            score for score in self.scores if score.chrom == chrom and score.position == position
        )

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
) -> PredictorRuntimeInspection:
    asset = tmp_path / "AlphaMissense_hg38.tsv.gz"
    asset.write_bytes(b"tiny")
    return PredictorRuntimeInspection(
        source_id=ALPHAMISSENSE_SOURCE_ID,
        asset_role=ALPHAMISSENSE_ASSET_ROLE,
        mode="local_path",
        status=status,
        path=asset,
        index_path=Path(f"{asset}.tbi"),
        manifest_path=asset.with_suffix(asset.suffix + ".manifest.json"),
        actual_size_bytes=len(b"tiny") if status is PredictorRuntimeStatus.READY else None,
        expected_md5="0" * 32,
        actual_md5=None,
        object_uri=None,
        reader_requires_local_path=True,
        bucket_file_size_limit=50 * 1024 * 1024 * 1024,
        materialization_status=None,
        message="ready" if status is PredictorRuntimeStatus.READY else status.value,
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
        source_id=ALPHAMISSENSE_SOURCE_ID,
        raw_fields=(),
        extra=extra or {},
    )
