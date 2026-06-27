from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.cli import eamos_pmat_bounded_slice_benchmark


def test_pmat_bounded_slice_benchmark_reports_required_metrics_without_leaks(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = eamos_pmat_bounded_slice_benchmark.main(
        [
            "--output-dir",
            str(tmp_path),
            "--force",
            "--lookup-runs",
            "2",
            "--batch-size",
            "5",
            "--batch-runs",
            "2",
            "--compact",
            "--require-ready",
        ]
    )

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)

    assert report["mode"] == "pmat_bounded_slice_benchmark"
    assert report["ready"] is True
    assert report["source_scope"] == "tiny_fixture_benchmark"
    assert report["guardrails"]["network"] == {"provider": None, "used": False}
    assert report["guardrails"]["source_download"] == "not_used"
    assert report["guardrails"]["storage_upload"] == "not_used"
    assert report["guardrails"]["runtime_seeding"] == "not_used"
    assert report["guardrails"]["runtime_flag_change"] == "not_used"
    assert report["guardrails"]["supabase_mutation"] == "not_used"
    assert report["guardrails"]["local_path_values_emitted"] is False
    assert report["guardrails"]["abstract_values_emitted"] is False

    measurements = report["measurements"]
    assert measurements["total_wall_time_ms"] >= 0
    assert measurements["temp_disk_peak_bytes"] > 0
    assert measurements["output_size_bytes"]["pubmed_sqlite"] > 0
    assert measurements["output_size_bytes"]["total_generated"] > 0

    assert measurements["row_count_profile"] == {
        "article_count": 2,
        "coverage_count": 6,
        "deleted_count": 1,
        "literature_edge_count": 8,
        "source_file_count": 3,
    }
    assert measurements["license_profile"] == {
        "licensed_abstract_count": 1,
        "metadata_only_count": 1,
        "pmc_license_overlay_count": 0,
    }
    assert measurements["edge_profile"]["pubtator_conversion"]["edge_count"] == 4
    assert measurements["edge_profile"]["litvar_conversion"]["edge_count"] == 12
    assert (
        measurements["edge_profile"]["import_stats_by_source"]["pubtator_edges"][
            "literature_edge_orphan_skipped_count"
        ]
        == 2
    )
    assert (
        measurements["edge_profile"]["import_stats_by_source"]["litvar_edges"][
            "literature_edge_orphan_skipped_count"
        ]
        == 6
    )

    assert measurements["preflight"]["ready"] is True
    assert measurements["preflight"]["checksum_verified"] is True
    assert measurements["lookup_latency_ms"]["runs"] == 2
    assert measurements["lookup_latency_ms"]["ok"] == 2
    assert measurements["lookup_latency_ms"]["elapsed"]["p50"] is not None
    assert measurements["batch_latency_ms"]["batch_size"] == 5
    assert measurements["batch_latency_ms"]["runs"] == 2
    assert measurements["batch_latency_ms"]["ok"] == 2
    assert measurements["batch_latency_ms"]["elapsed"]["p95"] is not None

    assert "wall_time_ms" in report["benchmark_contract"]["minimum_metrics"]
    assert "batch_latency_ms.p50_p95" in report["benchmark_contract"]["minimum_metrics"]
    assert report["representative_slice_requirements"]["approval_required"] is True
    assert len(report["rollback_procedure"]) >= 4

    encoded = json.dumps(report).lower()
    assert str(tmp_path).lower() not in encoded
    assert "linked by pubtator" not in encoded
    assert "asp87gly variant was observed" not in encoded
    assert "d:\\" not in encoded
    assert "/var/data/" not in encoded
