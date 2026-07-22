from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.schemas.run import (
    EvidenceSourceSummary,
    FunctionalEvidenceSummary,
    PublicationLiterature,
    PubMedArticle,
    ReportPayload,
    VariantReportProfile,
    VariantSummaryRow,
)
from app.services.lookup_service_cache import (
    FUNCTIONAL_EVIDENCE_CACHE_VERSION,
    GENE_CONTEXT_SNAPSHOT_CACHE_VERSION,
)
from app.services.lookup_service_report_payload import (
    _report_safe_decision,
    build_lookup_report_payload,
    finalize_lookup_report_payload,
)
from app.tools.base import ToolResult


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        use_real_apis=False,
        local_evidence_enabled=True,
        local_evidence_allowed_flows_raw="lookup",
        local_evidence_require_real_apis=False,
    )


def _variant() -> SimpleNamespace:
    return SimpleNamespace(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.260A>G",
        protein_change="p.Asp87Gly",
        genomic_hg38="1-68444869-T-C",
        genomic_hgvs="NC_000001.11:g.68444869T>C",
        variation_type="single nucleotide variant",
        consequence="missense_variant",
        dbsnp_rsid="rs61751299",
    )


def test_report_safe_decision_filters_weak_source_facts() -> None:
    evidence_map = {
        "clinvar": {"classification": "Pathogenic"},
        "vep": {"most_severe_consequence": "missense_variant"},
        "spliceai": {"acceptor_loss": 0.99},
        "gnomad": {"allele_frequency": 0.42},
    }

    safe = _report_safe_decision(
        evidence_map,
        {"clinvar": "live", "vep": "fallback", "spliceai": "failed", "gnomad": "missing"},
    )

    assert safe.evidence_lines == ["ClinVar classification: Pathogenic."]

    unavailable = _report_safe_decision(
        evidence_map,
        {"clinvar": "fallback", "vep": "failed", "spliceai": "missing"},
    )
    assert unavailable.evidence_lines == []
    assert "Pathogenic" not in unavailable.recommendation
    assert unavailable.warnings == ["report_sources_unavailable"]

    unsafe = _report_safe_decision(
        {"clinvar": {"classification": "/srv/private/provider-error"}},
        {"clinvar": "live"},
    )
    assert "/srv/private" not in " ".join(unsafe.evidence_lines)


def _variant_row() -> VariantSummaryRow:
    return VariantSummaryRow(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.260A>G",
        protein_change="p.Asp87Gly",
        genomic_hg38="1-68444869-T-C",
        variation_type="single nucleotide variant",
        consequence="missense_variant",
    )


def _input_resolution() -> SimpleNamespace:
    return SimpleNamespace(
        transcript_hgvs="NM_000329.3:c.260A>G",
        resolver_transcript="NM_000329.3",
    )


def _decision() -> SimpleNamespace:
    return SimpleNamespace(
        recommendation="Variant-level evidence summary.",
        evidence_lines=["ClinVar source snapshot."],
        next_step="Review source provenance.",
        warnings=["decision_warning"],
    )


def _cached_functional_summary() -> dict[str, Any]:
    return FunctionalEvidenceSummary(total_count=0).model_dump(mode="json")


def test_report_payload_builder_reuses_cached_functional_and_gene_context() -> None:
    functional = _FailingFunctionalEvidence()
    gene_context = _FailingGeneContextSnapshot()
    phases: list[tuple[str, dict[str, Any] | None]] = []
    evidence_map: dict[str, dict[str, Any]] = {
        "clinvar": {
            "classification": "Uncertain significance",
            "review_status": "criteria provided, single submitter",
        },
        "vep": {"most_severe_consequence": "missense_variant"},
        "litvar2": {"scholar_url": "https://scholar.example.test/rpe65"},
    }
    evidence_statuses = {"clinvar": "fixture", "vep": "fixture", "litvar2": "fixture"}
    warnings: list[str] = []

    assembly = build_lookup_report_payload(
        gene="RPE65",
        cdna="c.260A>G",
        protein_change="p.Asp87Gly",
        species="human",
        query_kind="transcript_hgvs",
        input_resolution=_input_resolution(),
        variant=_variant(),
        variant_row=_variant_row(),
        variant_label="RPE65 NM_000329.3:c.260A>G (p.Asp87Gly)",
        decision=_decision(),
        lookup_modules={},
        evidence=[],
        evidence_map=evidence_map,
        evidence_raw={},
        evidence_statuses=evidence_statuses,
        warnings=warnings,
        publication_cache={
            "functional_evidence_cache_version": FUNCTIONAL_EVIDENCE_CACHE_VERSION,
            "functional_evidence": _cached_functional_summary(),
        },
        cache_hit={
            "gene_context_snapshot": {
                "gene_context_snapshot_cache_version": GENE_CONTEXT_SNAPSHOT_CACHE_VERSION,
                "snapshot": {
                    "source_status": "cache",
                    "protein_domain_track": {"status": "cache_hit"},
                },
            }
        },
        litvar_result=ToolResult(
            source="litvar2",
            status="fixture",
            request_identity={},
            summary={},
            warnings=[],
            raw=None,
        ),
        tool_registry={},
        publication_literature=_StaticPublicationLiterature(),
        functional_evidence=functional,
        clinical_consensus=_StaticClinicalConsensus(),
        sequence_context=_MissingSequenceContext(),
        gene_context_snapshot=gene_context,
        settings=_settings(),
        cached_report_source_results={},
        source_cached_result=lambda *_args, **_kwargs: pytest.fail(
            "clinical trial source should not run without a tool"
        ),
        record_result=lambda *_args, **_kwargs: pytest.fail(
            "no source results should be recorded in this scenario"
        ),
        timing_start=lambda: 0.0,
        record_phase=lambda name, _started_at, **kwargs: phases.append(
            (name, kwargs.get("metadata"))
        ),
    )

    assert assembly.payload.functional_evidence is not None
    assert assembly.payload.functional_evidence.total_count == 0
    assert functional.calls == 0
    assert gene_context.calls == 0
    assert assembly.rebuild_functional_evidence_cache is False
    assert assembly.rebuild_gene_context_snapshot_cache is False
    assert assembly.gene_context_snapshot_cache == {
        "gene_context_snapshot_cache_version": GENE_CONTEXT_SNAPSHOT_CACHE_VERSION,
        "snapshot": {
            "source_status": "cache",
            "protein_domain_track": {"status": "cache_hit"},
        },
    }
    assert evidence_statuses["gene_context_snapshot"] == "cache"
    assert "clinvar_gene_distribution_excluded_pending_index" in warnings
    assert ("functional_evidence", {"cached": True}) in phases
    assert ("gene_context_snapshot", {"cached": True}) in phases


def test_report_payload_finalizer_adds_currency_profile_and_computed_layer() -> None:
    evidence = [
        EvidenceSourceSummary(
            source="gnomad",
            status="live",
            request_identity={"variant_id": "1-68444869-T-C", "dataset": "gnomad_r4"},
            summary={"variant_id": "1-68444869-T-C", "dataset": "gnomad_r4"},
            source_version="gnomad_r4",
        )
    ]
    payload = ReportPayload(
        patient_id="lookup_test",
        variant_summary_rows=[_variant_row()],
    )
    orchestrator = _CapturingReportOrchestrator()
    phases: list[str] = []
    warnings: list[str] = []

    finalize_lookup_report_payload(
        payload=payload,
        gene="RPE65",
        cdna="c.260A>G",
        variant_label="RPE65 NM_000329.3:c.260A>G",
        decision=_decision(),
        input_resolution=_input_resolution(),
        search_interpretation=None,
        evidence=evidence,
        evidence_map={"gnomad": {"variant_id": "1-68444869-T-C", "dataset": "gnomad_r4"}},
        evidence_statuses={"gnomad": "live"},
        warnings=warnings,
        draft_render_service=None,
        report_orchestrator=orchestrator,
        timing_start=lambda: 0.0,
        record_phase=lambda name, _started_at, **_kwargs: phases.append(name),
    )

    assert payload.report_generated_at
    assert payload.report_data_currency is not None
    assert payload.report_data_currency.generated_at == payload.report_generated_at
    assert payload.source_versions["gnomad"] == "gnomad_r4"
    assert payload.report_profile == VariantReportProfile()
    assert orchestrator.payload is payload
    assert "draft_render" in phases
    assert "report_profile" in phases
    assert "eamos_computed_classification" in phases


class _StaticPublicationLiterature:
    def build_for_lookup(self, *_args, **_kwargs) -> PublicationLiterature:
        return PublicationLiterature(
            total_count=1,
            shown_count=1,
            articles=[
                PubMedArticle(
                    pmid="38191234",
                    title="RPE65 publication",
                    authors="Walia S et al.",
                    journal="Ophthalmology",
                    year="2024",
                    url="https://pubmed.ncbi.nlm.nih.gov/38191234/",
                )
            ],
        )


class _FailingFunctionalEvidence:
    def __init__(self) -> None:
        self.calls = 0

    def build_for_lookup(self, *_args, **_kwargs) -> FunctionalEvidenceSummary:
        self.calls += 1
        raise AssertionError("functional evidence should come from cache")


class _StaticClinicalConsensus:
    def build_for_lookup(self, *_args, **_kwargs) -> SimpleNamespace:
        return SimpleNamespace(
            summary={"status": "not_configured"},
            status="missing",
            warnings=["clinical_consensus_fixture"],
        )


class _MissingSequenceContext:
    def resolve(self, *_args, **_kwargs) -> SimpleNamespace:
        return SimpleNamespace(context=None, warnings=["sequence_context_fixture_missing"])


class _FailingGeneContextSnapshot:
    def __init__(self) -> None:
        self.calls = 0

    def build(self, *_args, **_kwargs) -> Any:
        self.calls += 1
        raise AssertionError("gene context should come from cache")


class _CapturingReportOrchestrator:
    def __init__(self) -> None:
        self.payload: ReportPayload | None = None

    def build_profile(self, *, payload: ReportPayload, **_kwargs) -> VariantReportProfile:
        self.payload = payload
        return VariantReportProfile()
