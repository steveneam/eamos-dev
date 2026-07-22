from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.schemas.lookup import LookupResponse
from app.schemas.run import (
    AcmgCriteriaScaffold,
    AcmgCriterion,
    FunctionalEvidenceDisplayMetrics,
    FunctionalEvidenceSummary,
    PublicationLiterature,
    PubMedArticle,
    ComputationalDeepDiveSection,
    ComputationalPredictorRow,
    EvidenceSourceSummary,
    ReportPayload,
    TherapiesTrialsSection,
    TrialMatch,
    VariantReportProfile,
    VariantSummaryRow,
)
from app.services.lookup_sections import (
    build_lookup_initial_summary,
    build_lookup_section_fetch_response,
)
from app.services.clinical_consensus import ClinicalConsensusBuilder
from app.services.functional_evidence import FunctionalEvidenceExtractor
from app.services.lookup_service_publications_trials import trials_section_from_result
from app.services.report_call_cards import (
    build_population_frequency_detail,
    build_variant_report_call_cards,
)
from app.services.report_data_currency import build_report_data_currency
from app.services.report_execution_truth import build_report_execution_state_v2
from app.services.search_input_resolver import SearchInputResolution
from app.services.variant_report_orchestrator import VariantReportDataOrchestrator
from app.tools.base import ToolResult

_VARIANT_MATRIX = (
    ("RPE65", "NM_000329.3", "c.260A>G", "p.Asp87Gly", "1-68444869-T-C", "missense_variant"),
    ("ABCA4", "NM_000350.3", "c.5435T>A", "p.Ile1812Asn", "1-94014568-A-T", "missense_variant"),
    ("USH2A", "NM_206933.4", "c.2276G>T", "p.Cys759Phe", "1-216247118-C-A", "missense_variant"),
    ("HBB", "NM_000518.5", "c.20A>T", "p.Glu7Val", "11-5227002-T-A", "missense_variant"),
    ("TP53", "NM_000546.6", "c.215C>G", "p.Pro72Arg", "17-7676154-G-C", "missense_variant"),
    (
        "BRCA1",
        "NM_007294.4",
        "c.68_69delAG",
        "p.Glu23ValfsTer17",
        "NC_000017.11:g.43124028_43124029del",
        "frameshift_variant",
    ),
    (
        "CFTR",
        "NM_000492.4",
        "c.1521_1523delCTT",
        "p.Phe508del",
        "NC_000007.14:g.117559592_117559594del",
        "inframe_deletion",
    ),
    ("F8", "NM_000132.4", "c.6046C>T", "p.Arg2016Trp", "X-154902120-G-A", "missense_variant"),
)


@pytest.mark.parametrize(
    ("gene", "transcript", "cdna", "protein", "genomic", "consequence"),
    _VARIANT_MATRIX,
)
def test_report_execution_state_binds_the_eight_variant_matrix_without_fixture_support(
    gene: str,
    transcript: str,
    cdna: str,
    protein: str,
    genomic: str,
    consequence: str,
) -> None:
    resolution = _resolution(gene, transcript, cdna, protein, genomic)
    payload = _payload(gene, transcript, cdna, protein, genomic, consequence)
    evidence = [
        EvidenceSourceSummary(
            source="variant_validator",
            status="local",
            request_identity={
                "gene": gene,
                "transcript_hgvs": f"{transcript}:{cdna}",
                "variant_id": genomic,
            },
            summary={"variant_id": genomic, "source_version": "vv-local-2026.07"},
            source_version="vv-local-2026.07",
        )
    ]

    result = build_report_execution_state_v2(
        resolution=resolution,
        payload=payload,
        evidence=evidence,
        evidence_map={"variant_validator": evidence[0].summary},
        evidence_statuses={"variant_validator": "local"},
    )

    assert result.state is not None
    state = result.state
    assert state.coverage == "complete"
    assert state.canonical_variant.gene == gene
    assert state.canonical_variant.cdna == cdna
    assert state.canonical_variant.transcript == transcript
    assert state.canonical_variant.protein_hgvs == protein
    assert state.canonical_variant.genomic_hg38 == genomic
    assert state.canonical_variant.source_support == ["variant_validator"]
    assert genomic not in state.canonical_variant.variant_key
    assert len(state.sections) == 12
    assert {section.source_snapshot_id for section in state.sections} == {state.source_snapshot_id}
    assert not any("fixture" in support for support in state.canonical_variant.source_support)


def test_report_execution_state_fails_closed_on_identity_mismatch_without_echoing_inputs() -> None:
    resolution = _resolution(
        "ABCA4",
        "NM_000350.3",
        "c.5435T>A",
        "p.Ile1812Asn",
        "1-94014568-A-T",
    )
    payload = _payload(
        "ABCA4",
        "NM_000350.3",
        "c.5435T>A",
        "p.Ile1812Asn",
        "1-94014568-A-T",
        "missense_variant",
    )
    evidence = [
        EvidenceSourceSummary(
            source="variant_validator",
            status="local",
            request_identity={"gene": "RPE65", "variant_id": "1-68444869-T-C"},
            source_version="vv-local-2026.07",
        )
    ]

    result = build_report_execution_state_v2(
        resolution=resolution,
        payload=payload,
        evidence=evidence,
        evidence_map={},
        evidence_statuses={"variant_validator": "local"},
    )

    assert result.state is None
    assert result.warnings == ("report_canonical_identity_source_mismatch",)
    serialized = json.dumps(result.warnings)
    assert "ABCA4" not in serialized
    assert "RPE65" not in serialized
    assert "94042365" not in serialized
    assert "68444869" not in serialized


def test_execution_disclosures_do_not_echo_paths_or_provider_error_details() -> None:
    resolution = _resolution(
        "RPE65",
        "NM_000329.3",
        "c.260A>G",
        "p.Asp87Gly",
        "1-68444869-T-C",
    )
    payload = _payload(
        "RPE65",
        "NM_000329.3",
        "c.260A>G",
        "p.Asp87Gly",
        "1-68444869-T-C",
        "missense_variant",
    )
    evidence = EvidenceSourceSummary(
        source="variant_validator",
        status="local",
        request_identity={
            "gene": "RPE65",
            "transcript_hgvs": "NM_000329.3:c.260A>G",
            "variant_id": "1-68444869-T-C",
        },
        warnings=["provider_failed:/srv/private/provider.json:credential detail"],
        source_version="/srv/private/provider.json",
    )

    state = build_report_execution_state_v2(
        resolution=resolution,
        payload=payload,
        evidence=[evidence],
        evidence_map={},
        evidence_statuses={"variant_validator": "local"},
        section_ids=["header"],
    ).state

    assert state is not None
    serialized = state.model_dump_json()
    assert "/srv/private" not in serialized
    assert "credential detail" not in serialized
    disclosure = state.sections[0].execution_disclosures[0]
    assert disclosure.warnings == ["provider_failed"]
    assert disclosure.source_release is not None
    assert disclosure.source_release.startswith("sv~")


def test_identity_mismatched_source_cannot_populate_legacy_report_facts() -> None:
    resolution = _resolution(
        "ABCA4",
        "NM_000350.3",
        "c.5435T>A",
        "p.Ile1812Asn",
        "1-94014568-A-T",
    )
    payload = _payload(
        "ABCA4",
        "NM_000350.3",
        "c.5435T>A",
        "p.Ile1812Asn",
        "1-94014568-A-T",
        "missense_variant",
    )
    clinvar = EvidenceSourceSummary(
        source="clinvar",
        status="local",
        request_identity={"gene": "RPE65", "variant_id": "1-68444869-T-C"},
        summary={"classification": "Pathogenic", "dbsnp_rsid": "rs000000"},
        source_version="clinvar-local-test",
    )

    profile = VariantReportDataOrchestrator().build_profile(
        resolution=resolution,
        interpretation=None,
        payload=payload,
        evidence=[clinvar],
        evidence_map={"clinvar": clinvar.summary},
        evidence_statuses={"clinvar": "local"},
    )

    assert profile.header is not None
    assert profile.header.classification is None
    assert profile.header.dbsnp_rsid is None
    clinvar_provenance = next(item for item in profile.provenance if item.source == "clinvar")
    assert clinvar_provenance.status == "fallback"
    assert "report_source_identity_mismatch" in clinvar_provenance.warnings


def test_same_cdna_on_wrong_transcript_is_an_identity_mismatch() -> None:
    resolution = _resolution(
        "ABCA4",
        "NM_000350.3",
        "c.5435T>A",
        "p.Ile1812Asn",
        "1-94014568-A-T",
    )
    payload = _payload(
        "ABCA4",
        "NM_000350.3",
        "c.5435T>A",
        "p.Ile1812Asn",
        "1-94014568-A-T",
        "missense_variant",
    )
    evidence = EvidenceSourceSummary(
        source="variant_validator",
        status="local",
        request_identity={
            "gene": "ABCA4",
            "variant_id": "1-94014568-A-T",
            "transcript_hgvs": "NM_999999.1:c.5435T>A",
        },
    )

    result = build_report_execution_state_v2(
        resolution=resolution,
        payload=payload,
        evidence=[evidence],
        evidence_map={},
        evidence_statuses={"variant_validator": "local"},
    )

    assert result.state is None
    assert result.warnings == ("report_canonical_identity_source_mismatch",)


def test_report_execution_state_rejects_fixture_as_canonical_support() -> None:
    resolution = _resolution(
        "RPE65",
        "NM_000329.3",
        "c.260A>G",
        "p.Asp87Gly",
        "1-68444869-T-C",
    )
    payload = _payload(
        "RPE65",
        "NM_000329.3",
        "c.260A>G",
        "p.Asp87Gly",
        "1-68444869-T-C",
        "missense_variant",
    )
    fixture = EvidenceSourceSummary(
        source="variant_validator",
        status="fixture",
        request_identity={"gene": "RPE65", "variant_id": "1-68444869-T-C"},
        source_version="fixture-v1",
    )

    result = build_report_execution_state_v2(
        resolution=resolution,
        payload=payload,
        evidence=[fixture],
        evidence_map={},
        evidence_statuses={"variant_validator": "fixture"},
    )

    assert result.state is None
    assert result.warnings == ("report_canonical_identity_source_unavailable",)


def test_predictors_have_independent_applicability_execution_and_requirements() -> None:
    resolution = _resolution(
        "RPE65",
        "NM_000329.3",
        "c.260A>G",
        "p.Asp87Gly",
        "1-68444869-T-C",
    )
    payload = _payload(
        "RPE65",
        "NM_000329.3",
        "c.260A>G",
        "p.Asp87Gly",
        "1-68444869-T-C",
        "missense_variant",
        predictors=[
            ComputationalPredictorRow(
                name="REVEL",
                score=0.81,
                source="REVEL",
                source_id="zenodo_revel_scores",
                version="REVEL v1.3",
                calibration_id="revel_pejaver_2022_capped",
                public_serialization_allowed=True,
            ),
            ComputationalPredictorRow(
                name="REVEL",
                score=0.80,
                source="REVEL",
                source_id="zenodo_revel_scores_duplicate",
                version="REVEL v1.3",
                public_serialization_allowed=True,
            ),
        ],
    )
    evidence = _identity_evidence("RPE65", "NM_000329.3", "c.260A>G", "1-68444869-T-C")
    evidence.append(
        EvidenceSourceSummary(
            source="computational_annotations",
            status="local",
            request_identity={"gene": "RPE65", "variant_id": "1-68444869-T-C"},
            summary={
                "gene": "RPE65",
                "variant_id": "1-68444869-T-C",
                "warnings": [
                    "alphamissense_missing_source_file",
                    "esm1b_missing_manifest",
                    "capice_model_artifact_missing",
                ],
            },
            source_version="predictor-runtime-v1",
        )
    )

    result = build_report_execution_state_v2(
        resolution=resolution,
        payload=payload,
        evidence=evidence,
        evidence_map={item.source: item.summary for item in evidence},
        evidence_statuses={item.source: item.status for item in evidence},
    )

    assert result.state is not None
    predictors = {item.predictor_id: item for item in result.state.predictors}
    revel = predictors["revel"]
    assert [item.predictor_id for item in result.state.predictors].count("revel") == 1
    assert revel.applicability == "applicable"
    assert revel.state == "executed"
    assert revel.calibration_id == "revel_pejaver_2022_capped"
    assert revel.execution_disclosure.algorithm_version == "REVEL v1.3"
    assert revel.execution_disclosure.source_status == "source_backed"

    alphamissense = predictors["alphamissense"]
    assert alphamissense.state == "unavailable"
    assert alphamissense.execution_disclosure.requirements == [
        "Mount the AlphaMissense source file with an immutable manifest."
    ]
    assert all("/" not in warning for warning in alphamissense.warnings)


def test_missense_predictors_are_not_applicable_to_inframe_deletion() -> None:
    resolution = _resolution(
        "CFTR",
        "NM_000492.4",
        "c.1521_1523delCTT",
        "p.Phe508del",
        "NC_000007.14:g.117559592_117559594del",
    )
    payload = _payload(
        "CFTR",
        "NM_000492.4",
        "c.1521_1523delCTT",
        "p.Phe508del",
        "NC_000007.14:g.117559592_117559594del",
        "inframe_deletion",
    )
    evidence = _identity_evidence(
        "CFTR",
        "NM_000492.4",
        "c.1521_1523delCTT",
        "NC_000007.14:g.117559592_117559594del",
    )

    result = build_report_execution_state_v2(
        resolution=resolution,
        payload=payload,
        evidence=evidence,
        evidence_map={item.source: item.summary for item in evidence},
        evidence_statuses={item.source: item.status for item in evidence},
    )

    assert result.state is not None
    predictors = {item.predictor_id: item for item in result.state.predictors}
    for predictor_id in ("alphamissense", "esm1b", "revel", "primateai-3d"):
        predictor = predictors[predictor_id]
        assert predictor.applicability == "not_applicable"
        assert predictor.state == "not_applicable"
        assert predictor.execution_disclosure.source_status == "not_applicable"


def test_explicit_fixture_status_cannot_be_overridden_by_row_metadata() -> None:
    resolution = _resolution(
        "RPE65",
        "NM_000329.3",
        "c.260A>G",
        "p.Asp87Gly",
        "1-68444869-T-C",
    )
    payload = _payload(
        "RPE65",
        "NM_000329.3",
        "c.260A>G",
        "p.Asp87Gly",
        "1-68444869-T-C",
        "missense_variant",
        predictors=[
            ComputationalPredictorRow(
                name="AlphaMissense",
                score=0.9,
                source="AlphaMissense",
                source_id="google_deepmind_alphamissense_hg38",
                version="2023-05",
                public_serialization_allowed=True,
            )
        ],
    )
    evidence = _identity_evidence("RPE65", "NM_000329.3", "c.260A>G", "1-68444869-T-C")

    state = build_report_execution_state_v2(
        resolution=resolution,
        payload=payload,
        evidence=evidence,
        evidence_map={},
        evidence_statuses={
            "variant_validator": "local",
            "computational_annotations": "fixture",
        },
    ).state

    assert state is not None
    alphamissense = next(
        predictor for predictor in state.predictors if predictor.predictor_id == "alphamissense"
    )
    assert alphamissense.state == "unavailable"


def test_lookup_summary_and_lazy_sections_share_the_canonical_v2_snapshot() -> None:
    resolution = _resolution(
        "RPE65",
        "NM_000329.3",
        "c.260A>G",
        "p.Asp87Gly",
        "1-68444869-T-C",
    )
    payload = _payload(
        "RPE65",
        "NM_000329.3",
        "c.260A>G",
        "p.Asp87Gly",
        "1-68444869-T-C",
        "missense_variant",
    )
    evidence = _identity_evidence("RPE65", "NM_000329.3", "c.260A>G", "1-68444869-T-C")
    state = build_report_execution_state_v2(
        resolution=resolution,
        payload=payload,
        evidence=evidence,
        evidence_map={item.source: item.summary for item in evidence},
        evidence_statuses={item.source: item.status for item in evidence},
    ).state
    assert state is not None
    response = LookupResponse(
        query="RPE65:c.260A>G",
        species="human",
        report_payload=payload,
        evidence=evidence,
        warnings=[],
        execution_state_v2=state,
    )

    summary = build_lookup_initial_summary(response)
    sections = build_lookup_section_fetch_response(
        response,
        ["publications", "therapies_trials", "computational_deep_dive", "clingen_vcep"],
    )

    assert summary.execution_state_v2 is not None
    assert summary.execution_state_v2.source_snapshot_id == state.source_snapshot_id
    assert sections.sections["publications"].execution_state_v2 is not None
    assert (
        sections.sections["publications"].execution_state_v2.source_snapshot_id
        == state.source_snapshot_id
    )
    assert sections.sections["computational_deep_dive"].execution_state_v2 is not None


def test_publication_section_does_not_promote_gene_only_rows_to_exact_allele() -> None:
    resolution = _resolution(
        "RPE65",
        "NM_000329.3",
        "c.260A>G",
        "p.Asp87Gly",
        "1-68444869-T-C",
    )
    payload = _payload(
        "RPE65",
        "NM_000329.3",
        "c.260A>G",
        "p.Asp87Gly",
        "1-68444869-T-C",
        "missense_variant",
    )
    payload.publications_literature = PublicationLiterature(
        total_count=1,
        shown_count=1,
        articles=[
            PubMedArticle(
                pmid="99999998",
                title="RPE65 gene therapy follow-up",
                authors="Example et al.",
                journal="Example Journal",
                year="2026",
                url="https://pubmed.ncbi.nlm.nih.gov/99999998/",
                snippet_status="gene_only_no_variant",
            )
        ],
    )
    evidence = _identity_evidence("RPE65", "NM_000329.3", "c.260A>G", "1-68444869-T-C")

    state = build_report_execution_state_v2(
        resolution=resolution,
        payload=payload,
        evidence=evidence,
        evidence_map={item.source: item.summary for item in evidence},
        evidence_statuses={item.source: item.status for item in evidence},
        section_ids=["publications"],
    ).state

    assert state is not None
    assert state.sections[0].match_level == "gene"


def test_trial_section_uses_the_most_conservative_returned_match_level() -> None:
    resolution = _resolution(
        "ABCA4",
        "NM_000350.3",
        "c.5435T>A",
        "p.Ile1812Asn",
        "1-94014568-A-T",
    )
    payload = _payload(
        "ABCA4",
        "NM_000350.3",
        "c.5435T>A",
        "p.Ile1812Asn",
        "1-94014568-A-T",
        "missense_variant",
    )
    assert payload.report_profile is not None
    payload.report_profile.therapies_trials = TherapiesTrialsSection(
        trial_rows=[
            TrialMatch(
                nct_id="NCT00000001",
                title="Exact-variant trial",
                match_level="variant_level",
                source_url="https://clinicaltrials.gov/study/NCT00000001",
            ),
            TrialMatch(
                nct_id="NCT00000002",
                title="Condition discovery trial",
                match_level="disease_level",
                source_url="https://clinicaltrials.gov/study/NCT00000002",
            ),
        ]
    )
    evidence = _identity_evidence("ABCA4", "NM_000350.3", "c.5435T>A", "1-94014568-A-T")

    state = build_report_execution_state_v2(
        resolution=resolution,
        payload=payload,
        evidence=evidence,
        evidence_map={item.source: item.summary for item in evidence},
        evidence_statuses={item.source: item.status for item in evidence},
        section_ids=["therapies_trials"],
    ).state

    assert state is not None
    assert state.sections[0].match_level == "condition"


def test_fallback_computational_fixture_rows_do_not_enter_release_profile() -> None:
    resolution = _resolution(
        "ABCA4",
        "NM_000350.3",
        "c.5435T>A",
        "p.Ile1812Asn",
        "1-94014568-A-T",
    )
    payload = _payload(
        "ABCA4",
        "NM_000350.3",
        "c.5435T>A",
        "p.Ile1812Asn",
        "1-94014568-A-T",
        "missense_variant",
    )
    computational = {
        "gene": "ABCA4",
        "variant_id": "1-94014568-A-T",
        "predictors": [
            {
                "name": "REVEL",
                "score": 0.91,
                "source": "fixture",
                "version": "fixture-v1",
            },
            {
                "name": "AlphaMissense",
                "score": 0.72,
                "source": "AlphaMissense",
                "source_id": "google_deepmind_alphamissense_hg38",
                "version": "2023-05",
                "public_serialization_allowed": True,
            },
            {
                "name": "CAPICE",
                "score": 0.99,
                "source": "CAPICE",
                "source_id": "fixture_capice_scores",
                "version": "fixture-v1",
                "public_serialization_allowed": True,
            },
        ],
        "warnings": ["computational_annotations_curated_fixture_snapshot"],
    }

    profile = VariantReportDataOrchestrator().build_profile(
        resolution=resolution,
        interpretation=None,
        payload=payload,
        evidence=[
            EvidenceSourceSummary(
                source="computational_annotations",
                status="fallback",
                summary=computational,
            )
        ],
        evidence_map={"computational_annotations": computational},
        evidence_statuses={"computational_annotations": "fallback"},
    )

    assert profile.computational_deep_dive is not None
    assert [row.name for row in profile.computational_deep_dive.predictors] == ["AlphaMissense"]
    assert "computational_fixture_rows_rejected" in profile.computational_deep_dive.warnings


def test_unrelated_fixture_source_cannot_enable_acmg_scaffold_assertions() -> None:
    resolution = _resolution(
        "TP53",
        "NM_000546.6",
        "c.215C>G",
        "p.Pro72Arg",
        "17-7676154-G-C",
    )
    payload = _payload(
        "TP53",
        "NM_000546.6",
        "c.215C>G",
        "p.Pro72Arg",
        "17-7676154-G-C",
        "missense_variant",
    )
    payload.acmg_criteria_scaffold = AcmgCriteriaScaffold(
        criteria=[AcmgCriterion(code="PP3", verdict="met")],
    )

    profile = VariantReportDataOrchestrator().build_profile(
        resolution=resolution,
        interpretation=None,
        payload=payload,
        evidence_map={},
        evidence=[],
        evidence_statuses={
            "vep": "fixture",
            "clinical_consensus": "fallback",
            "clinvar": "fallback",
        },
    )

    assert profile.acmg_worksheet is not None
    assert profile.acmg_worksheet.criteria == []


def test_fallback_scientific_payload_does_not_enter_release_report_sections() -> None:
    resolution = _resolution(
        "TP53",
        "NM_000546.6",
        "c.215C>G",
        "p.Pro72Arg",
        "17-7676154-G-C",
    )
    payload = _payload(
        "TP53",
        "NM_000546.6",
        "c.215C>G",
        "p.Pro72Arg",
        "17-7676154-G-C",
        "missense_variant",
    )
    evidence_map = {
        "clinical_consensus": {
            "classification": "Pathogenic",
            "classification_source": "ClinGen",
            "acmg_worksheet": {
                "classification": "Pathogenic",
                "classification_source": "ClinGen",
                "criteria": [],
            },
        },
        "clinvar": {"classification": "Pathogenic", "dbsnp_rsid": "rs1042522"},
        "gene_disease": {
            "primary_condition": "Li-Fraumeni syndrome",
            "disease_ids": ["MONDO:0018875"],
            "inheritance": "autosomal dominant",
            "mechanism": "loss of function",
        },
        "molecular_context": {
            "gnomad_constraint": {"loeuf": 0.2},
            "clingen_dosage": {"haploinsufficiency": "sufficient evidence"},
            "overlapping_cnvs": ["example-CNV"],
        },
        "clinical_trials": {
            "trial_rows": [
                {
                    "nct_id": "NCT00000001",
                    "title": "Fixture trial",
                    "match_level": "disease_level",
                    "source_url": "https://clinicaltrials.gov/study/NCT00000001",
                }
            ],
            "query_executions": [{"query_id": "fixture-query", "result_count": 1}],
        },
    }
    statuses = {source: "fallback" for source in evidence_map}

    profile = VariantReportDataOrchestrator().build_profile(
        resolution=resolution,
        interpretation=None,
        payload=payload,
        evidence=[
            EvidenceSourceSummary(source=source, status="fallback", summary=summary)
            for source, summary in evidence_map.items()
        ],
        evidence_map=evidence_map,
        evidence_statuses=statuses,
    )

    assert profile.header is not None
    assert profile.header.classification is None
    assert profile.header.classification_source is None
    assert profile.header.dbsnp_rsid is None
    assert profile.interpretation_summary is not None
    assert profile.interpretation_summary.fact_refs == ["header"]
    assert profile.disease_mechanism is not None
    assert profile.disease_mechanism.primary_condition is None
    assert profile.disease_mechanism.disease_ids == []
    assert profile.molecular_context is not None
    assert profile.molecular_context.loeuf is None
    assert profile.molecular_context.clingen_haploinsufficiency is None
    assert profile.molecular_context.overlapping_cnvs == []
    assert profile.acmg_worksheet is not None
    assert profile.acmg_worksheet.classification is None
    assert profile.acmg_worksheet.criteria == []
    assert profile.therapies_trials is not None
    assert profile.therapies_trials.trial_rows == []
    assert profile.therapies_trials.query_executions == []
    assert "clinical_trials_source_unavailable" in profile.therapies_trials.warnings


def test_fallback_population_payload_is_redacted_to_typed_unavailable_state() -> None:
    detail = build_population_frequency_detail(
        {
            "dataset": "gnomad_r4",
            "variant_id": "17-7676154-G-C",
            "allele_frequency": 0.42,
            "allele_count": 42,
            "allele_number": 100,
            "genetic_ancestry_groups": [{"id": "nfe", "allele_frequency": 0.5, "allele_count": 30}],
        },
        source_status="fallback",
        source_identity={"dataset": "gnomad_r4", "variant_id": "17-7676154-G-C"},
    )

    assert detail is not None
    assert detail.unavailable_reason == "source_unavailable"
    assert detail.allele_frequency is None
    assert detail.allele_count is None
    assert detail.genetic_ancestry_groups == []
    assert "gnomad_source_status:fallback" in detail.warnings


def test_mixed_executed_and_failed_call_card_sources_report_partial() -> None:
    payload = ReportPayload(
        patient_id="lookup_test",
        functional_evidence=FunctionalEvidenceSummary(
            total_count=1,
            display_metrics=FunctionalEvidenceDisplayMetrics(
                state="uncurated",
                primary_label="Functional evidence identified",
                acmg_badge_text="No code asserted",
                verdict_source="uncurated",
                study_count_badge_text="1 Unique",
                ui_color_theme="neutral_slate_state",
            ),
        ),
    )

    cards = build_variant_report_call_cards(
        payload,
        {},
        {"clingen": "live", "clinvar": "failed", "pubmed": "missing"},
    )
    card = next(item for item in cards.cards if item.card_id == "lab_functional")

    assert card.source_status == "partial"


def test_fixture_timestamp_never_claims_fresh_source_currency() -> None:
    currency = build_report_data_currency(
        [
            EvidenceSourceSummary(
                source="clinvar",
                status="fixture",
                fetched_at="2026-07-22T12:00:00Z",
                source_version="fixture-v1",
            )
        ],
        {"clinvar": {"classification": "Pathogenic"}},
        generated_at="2026-07-22T13:00:00+00:00",
    )

    assert currency is not None
    assert currency.sources[0].status == "unknown"


def test_local_not_found_is_execution_without_scientific_coverage() -> None:
    resolution = _resolution(
        "F8",
        "NM_000132.4",
        "c.6046C>T",
        "p.Arg2016Trp",
        "X-154902120-G-A",
    )
    payload = _payload(
        "F8",
        "NM_000132.4",
        "c.6046C>T",
        "p.Arg2016Trp",
        "X-154902120-G-A",
        "missense_variant",
    )
    evidence = _identity_evidence("F8", "NM_000132.4", "c.6046C>T", "X-154902120-G-A")
    evidence.append(
        EvidenceSourceSummary(
            source="gnomad",
            status="local",
            request_identity={"variant_id": "X-154902120-G-A"},
            warnings=["gnomad_variant_not_found"],
            source_version="gnomad-r4-local",
        )
    )

    state = build_report_execution_state_v2(
        resolution=resolution,
        payload=payload,
        evidence=evidence,
        evidence_map={},
        evidence_statuses={item.source: item.status for item in evidence},
        section_ids=["population_frequency"],
    ).state

    assert state is not None
    section = state.sections[0]
    assert section.state == "empty"
    assert section.execution_disclosures[0].execution == "eamos_local"
    assert section.execution_disclosures[0].source_status == "not_found"


def test_fallback_clinical_consensus_sources_cannot_create_assertions() -> None:
    result = ClinicalConsensusBuilder().build_for_lookup(
        SimpleNamespace(),
        ReportPayload(patient_id="lookup_test"),
        {"clinvar": {"classification": "Pathogenic", "accession": "VCV000000001"}},
        evidence_raw={
            "clingen": {
                "classification": "Pathogenic",
                "criteria": ["PVS1"],
            }
        },
        source_statuses={"clingen": "fallback", "clinvar": "failed"},
    )

    assert result.ledger.classification is None
    assert result.ledger.criteria == []
    assert result.status == "missing"


def test_fallback_publication_payload_cannot_create_functional_evidence() -> None:
    variant = SimpleNamespace(
        gene="TP53",
        transcript_hgvs="NM_000546.6:c.215C>G",
        protein_change="p.Pro72Arg",
        genomic_hg38="17-7676154-G-C",
        genomic_hgvs="NC_000017.11:g.7676154G>C",
        dbsnp_rsid="rs1042522",
    )
    summary = FunctionalEvidenceExtractor().build_for_lookup(
        variant,
        {
            "pubmed": {
                "articles": [
                    {
                        "pmid": "99999999",
                        "title": "TP53 c.215C>G functional assay",
                        "abstract": "A functional assay measured p.Pro72Arg activity.",
                    }
                ]
            }
        },
        source_statuses={"pubmed": "fallback"},
    )

    assert summary.total_count == 0
    assert summary.studies == []


def test_fallback_lazy_trial_result_cannot_render_trial_rows() -> None:
    section = trials_section_from_result(
        ToolResult(
            source="clinical_trials",
            status="fallback",
            request_identity={"gene": "TP53"},
            summary={
                "trial_rows": [
                    {
                        "nct_id": "NCT00000001",
                        "title": "Fixture trial",
                        "match_level": "disease_level",
                        "source_url": "https://clinicaltrials.gov/study/NCT00000001",
                    }
                ]
            },
            warnings=["clinical_trials_fetch_failed:TimeoutException"],
            raw=None,
        )
    )

    assert section.trial_rows == []
    assert "clinical_trials_source_unavailable" in section.warnings


def _resolution(
    gene: str,
    transcript: str,
    cdna: str,
    protein: str,
    genomic: str,
) -> SearchInputResolution:
    return SearchInputResolution(
        gene=gene,
        hgvs=cdna,
        transcript=transcript,
        protein_change=protein,
        kind="cdna",
        transcript_hgvs=f"{transcript}:{cdna}",
        resolver_transcript=transcript,
        resolver_transcript_hgvs=f"{transcript}:{cdna}",
        genomic_hg38=genomic,
    )


def _payload(
    gene: str,
    transcript: str,
    cdna: str,
    protein: str,
    genomic: str,
    consequence: str,
    *,
    predictors: list[ComputationalPredictorRow] | None = None,
) -> ReportPayload:
    return ReportPayload(
        patient_id="lookup_test",
        report_title=f"{gene} {cdna}",
        variant_summary_rows=[
            VariantSummaryRow(
                gene=gene,
                transcript_hgvs=f"{transcript}:{cdna}",
                protein_change=protein,
                genomic_hg38=genomic,
                variation_type="single nucleotide variant" if ">" in cdna else "deletion",
                consequence=consequence,
            )
        ],
        report_profile=VariantReportProfile(
            computational_deep_dive=ComputationalDeepDiveSection(
                predictors=list(predictors or []),
                warnings=[] if predictors else ["computational_predictors_unavailable"],
            )
        ),
    )


def _identity_evidence(
    gene: str,
    transcript: str,
    cdna: str,
    genomic: str,
) -> list[EvidenceSourceSummary]:
    return [
        EvidenceSourceSummary(
            source="variant_validator",
            status="local",
            request_identity={
                "gene": gene,
                "transcript_hgvs": f"{transcript}:{cdna}",
                "variant_id": genomic,
            },
            summary={"variant_id": genomic, "source_version": "vv-local-2026.07"},
            source_version="vv-local-2026.07",
        )
    ]
