from __future__ import annotations

from app.services.population_frequency_section import build_population_frequency_section
from app.services.report_call_cards import build_population_frequency_detail


def test_population_frequency_section_marks_missing_detail_reason() -> None:
    section = build_population_frequency_section(None, source_status="failed")

    assert section.source_status == "failed"
    assert section.unavailable_reason == "detail_unavailable"
    assert "population_frequency_detail_unavailable" in section.warnings


def test_population_frequency_detail_marks_gnomad_variant_not_found_reason() -> None:
    detail = build_population_frequency_detail(
        {
            "dataset": "gnomad_r4",
            "variant_id": "1-68444869-T-C",
            "url": "https://gnomad.broadinstitute.org/variant/1-68444869-T-C?dataset=gnomad_r4",
        },
        source_status="live",
        source_warnings=["gnomad_variant_not_found"],
    )

    assert detail is not None
    assert detail.unavailable_reason == "variant_not_found"

    section = build_population_frequency_section(
        detail,
        source_status="live",
        gnomad_summary={"dataset": "gnomad_r4", "variant_id": "1-68444869-T-C"},
    )

    assert section.source_status == "live"
    assert section.unavailable_reason == "variant_not_found"
    assert "allele_frequency_unavailable" in section.warnings


def test_population_frequency_detail_preserves_failed_source_reason() -> None:
    detail = build_population_frequency_detail(
        {},
        source_status="failed",
        source_url="https://gnomad.broadinstitute.org/variant/1-123-A-G?dataset=gnomad_r4",
        source_warnings=["live_fetch_failed:ReadTimeout"],
        source_identity={"variant_id": "1-123-A-G", "dataset": "gnomad_r4"},
    )

    assert detail is not None
    assert detail.dataset == "gnomad_r4"
    assert detail.variant_id == "1-123-A-G"
    assert detail.unavailable_reason == "source_unavailable"
    assert "gnomad_source_status:failed" in detail.warnings

    section = build_population_frequency_section(
        detail,
        source_status="failed",
        gnomad_summary={},
    )

    assert section.source_status == "failed"
    assert section.unavailable_reason == "source_unavailable"
    assert "allele_frequency_unavailable" in section.warnings
