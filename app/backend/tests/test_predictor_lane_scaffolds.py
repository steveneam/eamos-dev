from __future__ import annotations

from decimal import Decimal

from app.services.capice import CapiceLane, CapiceScore
from app.services.ci_spliceai import CiSpliceAiLane, CiSpliceAiScore
from app.services.mavedb_local import (
    MaveDbImportRecord,
    MaveDbScoreSetRecord,
    MaveDbTargetRecord,
    MaveDbVariantScoreRecord,
    filter_mavedb_cc0_records,
)
from app.services.pvs1_nmd import Pvs1NmdInput, assess_pvs1_nmd, inspect_pvs1_nmd_runtime


def test_ci_spliceai_lane_is_admin_enabled_by_default() -> None:
    lookup = CiSpliceAiLane().lookup(
        CiSpliceAiScore(chrom="1", position=10, ref="A", alt="G", ds_al=0.7)
    )

    assert lookup.available is True
    assert lookup.score is not None
    assert lookup.score.max_delta == 0.7
    assert lookup.calibrated_label == "Strong splice impact"
    assert lookup.calibration_bucket is None
    assert lookup.public_serialization_allowed is True
    assert lookup.launch_gate == "ci_spliceai_launch_filter_metadata"


def test_ci_spliceai_lane_calibrates_when_explicitly_enabled() -> None:
    lookup = CiSpliceAiLane(enabled=True).lookup(
        CiSpliceAiScore(chrom="1", position=10, ref="A", alt="G", ds_al=0.7)
    )

    assert lookup.available is True
    assert lookup.score is not None
    assert lookup.score.max_delta == 0.7
    assert lookup.calibrated_label == "Strong splice impact"
    assert lookup.calibration_bucket is None


def test_ci_spliceai_lane_reports_missing_score_not_license_block() -> None:
    lookup = CiSpliceAiLane().lookup(None)

    assert lookup.available is False
    assert lookup.unavailable_reason == "ci_spliceai_score_missing"
    assert lookup.warnings == ("ci_spliceai_score_missing",)
    assert lookup.public_serialization_allowed is True


def test_capice_lane_is_admin_enabled_and_requires_materialized_score() -> None:
    missing = CapiceLane().lookup(None)

    assert missing.available is False
    assert missing.unavailable_reason == "capice_score_missing"
    assert missing.warnings == ("capice_score_missing",)
    assert missing.public_serialization_allowed is True
    assert missing.launch_gate == "capice_launch_filter_metadata"

    lookup = CapiceLane().lookup(CapiceScore(chrom="1", position=10, ref="A", alt="G", score=0.83))

    assert lookup.available is True
    assert lookup.score is not None
    assert lookup.score.score == 0.83
    assert lookup.public_serialization_allowed is True


def test_capice_lane_rejects_invalid_scores() -> None:
    lookup = CapiceLane().lookup(CapiceScore(chrom="1", position=10, ref="A", alt="G", score=1.5))

    assert lookup.available is False
    assert lookup.unavailable_reason == "capice_score_out_of_range"
    assert lookup.warnings == ("capice_score_out_of_range",)


def test_pvs1_nmd_assessment_is_conservative_without_context() -> None:
    assessment = assess_pvs1_nmd(Pvs1NmdInput(consequence="stop_gained"))

    assert assessment.applicable is True
    assert assessment.pvs1_support == "uncertain"
    assert assessment.nmd_predicted is None
    assert assessment.warnings == ("nmd_exon_context_missing",)


def test_pvs1_nmd_runtime_probe_is_pure_code_and_advisory() -> None:
    inspection = inspect_pvs1_nmd_runtime()

    assert inspection.available is True
    assert inspection.status == "pure_code_available"
    assert inspection.runtime_wired is True
    assert inspection.public_serialization_allowed is True
    assert inspection.storage_required is False
    assert inspection.warnings == ("advisory_engine_only", "autopvs1_code_not_used")


def test_pvs1_nmd_assessment_supports_possible_when_nmd_context_is_clear() -> None:
    assessment = assess_pvs1_nmd(
        Pvs1NmdInput(
            consequence="frameshift",
            exon_number=2,
            exon_count=8,
            distance_to_last_exon_junction_bp=1000,
            critical_region=True,
        )
    )

    assert assessment.applicable is True
    assert assessment.pvs1_support == "possible"
    assert assessment.nmd_predicted is True


def test_pvs1_nmd_assessment_marks_last_exon_as_uncertain() -> None:
    assessment = assess_pvs1_nmd(
        Pvs1NmdInput(consequence="stop_gained", exon_number=8, exon_count=8)
    )

    assert assessment.pvs1_support == "uncertain"
    assert assessment.nmd_predicted is False
    assert assessment.reason == "single_or_last_exon_nmd_escape_possible"


def test_mavedb_gate_accepts_only_cc0_records_with_scores() -> None:
    def record(
        suffix: str,
        *,
        license_value: str = "CC0-1.0",
        score: str = "0.12",
        policy_decision: str = "no_additional_restriction",
    ) -> MaveDbImportRecord:
        score_set_urn = f"urn:mavedb:000{suffix}-a-1"
        target = MaveDbTargetRecord(
            target_id="target:brca1",
            target_accession="NM_007294.4",
            target_sequence_checksum="sha256:synthetic",
            gene="BRCA1",
        )
        score_set = MaveDbScoreSetRecord(
            score_set_urn=score_set_urn,
            target_id=target.target_id,
            license_snapshot=license_value,
            data_usage_policy=None,
            data_usage_policy_decision=policy_decision,
            deprecated=False,
            superseded_by=None,
            source_url=f"https://www.mavedb.org/score-sets/{score_set_urn}",
        )
        variant = MaveDbVariantScoreRecord(
            variant_urn=f"{score_set_urn}#{suffix}",
            score_set_urn=score_set_urn,
            target_id=target.target_id,
            mave_hgvs=f"c.{suffix}A>G",
            raw_score=Decimal(score),
            score_column="score",
            score_unit="assay_specific_raw",
        )
        return MaveDbImportRecord(score_set, target, variant)

    cc0 = record("1")
    non_cc0 = record("2", license_value="CC BY 4.0")
    nonfinite_score = record("3", score="NaN")

    result = filter_mavedb_cc0_records([cc0, non_cc0, nonfinite_score])

    assert result.accepted == (cc0,)
    assert result.rejected == (non_cc0, nonfinite_score)
    assert result.warnings == (
        "mavedb_non_cc0_rejected:urn:mavedb:0002-a-1#2",
        "mavedb_invalid_score_rejected:urn:mavedb:0003-a-1#3",
    )
