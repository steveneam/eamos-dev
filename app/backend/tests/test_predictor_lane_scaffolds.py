from __future__ import annotations

from app.services.ci_spliceai import CiSpliceAiLane, CiSpliceAiScore
from app.services.mavedb_local import MaveDbRecord, filter_mavedb_cc0_records
from app.services.pvs1_nmd import Pvs1NmdInput, assess_pvs1_nmd, inspect_pvs1_nmd_runtime


def test_ci_spliceai_lane_is_disabled_by_default() -> None:
    lookup = CiSpliceAiLane().lookup(
        CiSpliceAiScore(chrom="1", position=10, ref="A", alt="G", ds_al=0.7)
    )

    assert lookup.available is False
    assert lookup.unavailable_reason == "ci_spliceai_lane_disabled"
    assert lookup.warnings == ("ci_spliceai_isolated_from_main_api_path",)


def test_ci_spliceai_lane_calibrates_when_explicitly_enabled() -> None:
    lookup = CiSpliceAiLane(enabled=True).lookup(
        CiSpliceAiScore(chrom="1", position=10, ref="A", alt="G", ds_al=0.7)
    )

    assert lookup.available is True
    assert lookup.score is not None
    assert lookup.score.max_delta == 0.7
    assert lookup.calibration_bucket == "Pathogenic"


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
    cc0 = MaveDbRecord(
        score_set_id="urn:mavedb:0001",
        variant="BRCA1 c.1A>G",
        score=0.12,
        license="CC0-1.0",
    )
    non_cc0 = MaveDbRecord(
        score_set_id="urn:mavedb:0002",
        variant="BRCA1 c.2A>G",
        score=0.4,
        license="CC BY 4.0",
    )
    missing_score = MaveDbRecord(
        score_set_id="urn:mavedb:0003",
        variant="BRCA1 c.3A>G",
        score=None,
        license="CC0",
    )

    result = filter_mavedb_cc0_records([cc0, non_cc0, missing_score])

    assert result.accepted == (cc0,)
    assert result.rejected == (non_cc0, missing_score)
    assert result.warnings == (
        "mavedb_non_cc0_rejected:urn:mavedb:0002",
        "mavedb_missing_score_rejected:urn:mavedb:0003",
    )
