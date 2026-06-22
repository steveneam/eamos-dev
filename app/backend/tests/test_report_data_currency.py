from __future__ import annotations

from app.schemas.lookup import SearchInputInterpretation
from app.schemas.run import EvidenceSourceSummary, ReportPayload, VariantSummaryRow
from app.services.report_data_currency import (
    build_report_data_currency,
    latest_evidence_timestamp,
)
from app.services.search_input_resolver import SearchInputResolution
from app.services.variant_report_orchestrator import VariantReportDataOrchestrator


def test_report_data_currency_uses_only_sanitized_evidence_freshness() -> None:
    evidence = [
        EvidenceSourceSummary(
            source="clinvar",
            status="local",
            source_version="ClinVar GRCh38 VCF weekly release 2026-05-25 / clinvar_20260523",
        ),
        EvidenceSourceSummary(
            source="clingen",
            status="cache",
            source_version="supabase://private/object",
        ),
        EvidenceSourceSummary(
            source="gnomad",
            status="stale",
            fetched_at="2026-06-01T00:00:00Z",
            source_version="gnomad_r4",
            cache_status="stale_on_failure",
        ),
    ]
    evidence_map = {
        "clinvar": {
            "upstream_released_at": "20260523",
        },
        "clingen": {
            "expert_panel": {
                "vcep": {"last_curated_date": "2024-04-02"},
                "provenance": {
                    "fetched_at": "2026-05-28T03:18:00Z",
                    "source_version": "ClinGen Evidence Repo cached",
                },
            }
        },
        "gnomad": {"dataset": "gnomad_r4"},
    }

    currency = build_report_data_currency(
        evidence,
        evidence_map,
        generated_at="2026-06-23T00:00:00+00:00",
    )

    assert currency is not None
    assert currency.generated_at == "2026-06-23T00:00:00+00:00"
    sources = {item.source: item for item in currency.sources}

    clinvar = sources["clinvar"]
    assert clinvar.label == "ClinVar"
    assert clinvar.tier == "volatile"
    assert clinvar.materialized_at is None
    assert clinvar.upstream_released_at == "2026-05-23"
    assert clinvar.status == "fresh"
    assert clinvar.staleness_days == 31
    assert clinvar.source_version == (
        "ClinVar GRCh38 VCF weekly release 2026-05-25 / clinvar_20260523"
    )

    clingen = sources["clingen"]
    assert clingen.materialized_at == "2026-05-28T03:18:00+00:00"
    assert clingen.upstream_released_at == "2024-04-02"
    assert clingen.source_version == "ClinGen Evidence Repo cached"

    gnomad = sources["gnomad"]
    assert gnomad.status == "stale"
    assert gnomad.materialized_at == "2026-06-01T00:00:00+00:00"
    assert gnomad.staleness_days == 22
    assert gnomad.source_version == "gnomad_r4"


def test_latest_evidence_timestamp_prefers_latest_real_source_timestamp() -> None:
    evidence = [
        EvidenceSourceSummary(source="clinvar", status="local"),
        EvidenceSourceSummary(
            source="gnomad",
            status="cache",
            fetched_at="2026-06-01T00:00:00Z",
        ),
    ]
    evidence_map = {"clinvar": {"upstream_released_at": "2026-05-23"}}

    assert latest_evidence_timestamp(evidence, evidence_map) == "2026-06-01T00:00:00+00:00"


def test_variant_report_header_falls_back_to_report_generation_time() -> None:
    payload = _payload(report_generated_at="2026-06-23T01:00:00+00:00")

    profile = VariantReportDataOrchestrator().build_profile(
        resolution=_resolution(),
        interpretation=None,
        payload=payload,
        evidence=[EvidenceSourceSummary(source="clinvar", status="local")],
        evidence_map={"clinvar": {"classification": "VUS"}},
        evidence_statuses={"clinvar": "local"},
    )

    assert profile.header is not None
    assert profile.header.updated_at == "2026-06-23T01:00:00+00:00"


def test_variant_report_header_uses_latest_evidence_timestamp() -> None:
    payload = _payload(report_generated_at="2026-06-23T01:00:00+00:00")

    profile = VariantReportDataOrchestrator().build_profile(
        resolution=_resolution(),
        interpretation=SearchInputInterpretation(
            submitted_text="RPE65 c.260A>G",
            mode="structured",
            confidence="high",
            gene="RPE65",
            cdna="c.260A>G",
        ),
        payload=payload,
        evidence=[
            EvidenceSourceSummary(
                source="clinvar",
                status="local",
                fetched_at="2026-06-20T10:00:00Z",
            ),
            EvidenceSourceSummary(
                source="clingen",
                status="cache",
                fetched_at="2026-06-21T11:00:00Z",
            ),
        ],
        evidence_map={"clinvar": {"classification": "VUS"}, "clingen": {}},
        evidence_statuses={"clinvar": "local", "clingen": "cache"},
    )

    assert profile.header is not None
    assert profile.header.updated_at == "2026-06-21T11:00:00+00:00"


def _payload(*, report_generated_at: str) -> ReportPayload:
    return ReportPayload(
        patient_id="lookup_test",
        report_generated_at=report_generated_at,
        report_title="RPE65 c.260A>G",
        variant_summary_rows=[
            VariantSummaryRow(
                gene="RPE65",
                transcript_hgvs="c.260A>G",
                protein_change="p.Asp87Gly",
                genomic_hg38="1-68444869-T-C",
            )
        ],
    )


def _resolution() -> SearchInputResolution:
    return SearchInputResolution(
        gene="RPE65",
        hgvs="c.260A>G",
        transcript="NM_000329.3",
        protein_change="p.Asp87Gly",
        kind="cdna",
        transcript_hgvs="NM_000329.3:c.260A>G",
        resolver_transcript="NM_000329.3",
        resolver_transcript_hgvs="NM_000329.3:c.260A>G",
        genomic_hg38="1-68444869-T-C",
    )
