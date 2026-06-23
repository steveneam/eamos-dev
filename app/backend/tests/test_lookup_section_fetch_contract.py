from __future__ import annotations

import json

from app.schemas.lookup import LookupResponse
from app.schemas.run import (
    AcmgWorksheetCriterion,
    AcmgWorksheetLedger,
    ClinicalTrialQueryExecution,
    ReportPayload,
    TherapiesTrialsSection,
    VariantReportProfile,
)
from app.services.lookup_sections import build_lookup_section_fetch_response


def test_default_lookup_omits_m11_lazy_heavy_sections(client) -> None:
    response = client.post(
        "/api/v1/lookup",
        json={"gene": "RPE65", "cdna": "c.260A>G"},
    )
    full_response = client.post(
        "/api/v1/lookup?include_lazy_sections=true",
        json={"gene": "RPE65", "cdna": "c.260A>G"},
    )

    assert response.status_code == 200
    assert full_response.status_code == 200
    body = response.json()
    full_payload = full_response.json()["report_payload"]
    payload = body["report_payload"]
    profile = payload["report_profile"]

    assert payload["publications_callout"]["total_count"] == 3
    assert payload["publications_callout"]["scope_counts"]["gene"]["total_count"] == 816
    assert "publications_literature" not in payload
    assert "therapies_trials" not in profile
    assert "computational_deep_dive" not in profile
    assert "expert_panel" not in profile
    assert profile["acmg_worksheet"]["classification"] == "Uncertain significance"
    assert profile["acmg_worksheet"]["classification_source"] == "ClinVar"
    assert full_payload["publications_literature"]["total_count"] == 3
    assert full_payload["report_profile"]["computational_deep_dive"]["predictors"]
    assert full_payload["report_profile"]["expert_panel"] is None
    assert len(response.content) < len(full_response.content)


def test_lookup_summary_returns_m7_tile_contract_without_heavy_sections(client) -> None:
    response = client.post(
        "/api/v1/lookup/summary",
        json={"gene": "RPE65", "cdna": "c.260A>G"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "RPE65:c.260A>G"
    assert body["header"]["gene"] == "RPE65"
    assert body["header"]["cdna"] == "c.260A>G"
    assert [section["section_id"] for section in body["lazy_sections"]] == [
        "publications",
        "therapies_trials",
        "computational_deep_dive",
        "clingen_vcep",
    ]

    tiles = {tile["tile_id"]: tile for tile in body["tiles"]}
    assert set(tiles) == {
        "population_frequency",
        "computational",
        "lab_functional",
        "clinical_consensus",
    }
    assert tiles["computational"]["fetch_section_id"] == "computational_deep_dive"
    assert tiles["clinical_consensus"]["fetch_section_id"] == "clingen_vcep"
    assert tiles["population_frequency"]["fetch_section_id"] is None
    assert tiles["population_frequency"]["primary_label"] == "Rare (0.00159% AF)"

    serialized = json.dumps(body)
    assert "report_payload" not in body
    assert "publications_literature" not in serialized
    assert "functional_evidence" not in serialized


def test_lookup_sections_returns_requested_payloads_with_freshness_fields(client) -> None:
    response = client.post(
        "/api/v1/lookup/sections",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "include": [
                "publications",
                "therapies_trials",
                "computational_deep_dive",
                "clingen_vcep",
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "RPE65:c.260A>G"
    sections = body["sections"]
    assert set(sections) == {
        "publications",
        "therapies_trials",
        "computational_deep_dive",
        "clingen_vcep",
    }

    publications = sections["publications"]
    assert publications["status"] == "available"
    assert publications["payload"]["total_count"] == 3
    assert publications["payload"]["scope"] == "variant"
    assert publications["payload"]["scope_counts"]["variant"]["total_count"] == 3
    assert publications["payload"]["scope_counts"]["variant"]["count_kind"] == "deduped_pmids"
    assert publications["payload"]["scope_counts"]["gene"]["total_count"] == 816
    assert publications["payload"]["scope_counts"]["gene"]["count_kind"] == "gene_wide_source_count"
    assert publications["payload"]["articles"][0]["pmid"] == "38191234"
    assert set(publications["freshness"]) == {
        "fetched_at",
        "source_version",
        "stale_on_failure",
        "source_status",
        "source_url",
    }
    assert publications["freshness"]["stale_on_failure"] is False

    trials = sections["therapies_trials"]
    assert trials["section_id"] == "therapies_trials"
    assert trials["status"] in {"available", "partial"}
    assert "trial_rows" in trials["payload"]
    assert "query_executions" in trials["payload"]
    assert set(trials["freshness"]) == {
        "fetched_at",
        "source_version",
        "stale_on_failure",
        "source_status",
        "source_url",
    }

    computational = sections["computational_deep_dive"]
    assert computational["status"] == "available"
    predictor_names = {row["name"] for row in computational["payload"]["predictors"]}
    assert {"REVEL", "CADD PHRED", "PrimateAI-3D", "MetaLR", "SpliceAI"} <= predictor_names
    predictors_by_name = {row["name"]: row for row in computational["payload"]["predictors"]}
    assert predictors_by_name["REVEL"]["calibration_bucket"] == "Likely pathogenic"
    assert predictors_by_name["CADD PHRED"]["calibration_bucket"] == "VUS"
    assert predictors_by_name["SpliceAI"]["calibration_method"] == (
        "Walker 2023 / ClinGen SVI splicing"
    )
    assert predictors_by_name["MetaLR"]["calibration_bucket"] is None
    assert computational["freshness"]["stale_on_failure"] is False

    clingen = sections["clingen_vcep"]
    assert clingen["status"] == "partial"
    assert clingen["payload"]["classification"] == "Uncertain significance"
    assert clingen["payload"]["classification_source"] == "ClinVar"
    assert clingen["payload"]["source_scope"] == "current_clinical_consensus_snapshot"
    assert clingen["payload"]["criteria"][0]["assertion_level"] == "eamos_hint"
    assert clingen["payload"]["synthesis"] == (
        "ClinVar aggregate classification is used because no ClinGen/VCEP classification was "
        "available; Eamos criteria remain worksheet hints only."
    )
    assert clingen["warnings"] == ["clingen_vcep_evidence_repo_source_cache_not_integrated"]
    assert clingen["freshness"]["stale_on_failure"] is False


def test_trials_section_envelope_distinguishes_no_rows_from_missing_payload() -> None:
    response = LookupResponse(
        query="ABCA4:c.1A>G",
        species="human",
        report_payload=ReportPayload(
            patient_id="lookup_test",
            report_profile=VariantReportProfile(
                therapies_trials=TherapiesTrialsSection(
                    query_executions=[
                        ClinicalTrialQueryExecution(
                            query_id="gene_term:abca4",
                            lane="gene_term",
                            query_term="ABCA4",
                            params={"query.term": "ABCA4"},
                            status="ok",
                            result_count=0,
                        )
                    ],
                    warnings=["clinical_trials_no_active_matches"],
                )
            ),
        ),
        evidence=[],
        warnings=[],
    )

    result = build_lookup_section_fetch_response(response, ["therapies_trials"])

    trials = result.sections["therapies_trials"]
    assert trials.status == "available"
    assert trials.payload is not None
    assert trials.payload["trial_rows"] == []
    assert trials.payload["query_executions"][0]["query_id"] == "gene_term:abca4"
    assert trials.warnings == ["clinical_trials_no_active_matches"]


def test_lookup_sections_rejects_deferred_population_detail_until_m11_full(client) -> None:
    response = client.post(
        "/api/v1/lookup/sections",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "include": ["population_frequency"],
        },
    )

    assert response.status_code == 422


def test_clingen_partial_section_tolerates_legacy_nullable_criterion_warnings() -> None:
    criterion = AcmgWorksheetCriterion(
        code="PM2",
        state="met",
        assertion_level="source_asserted",
        rationale="Rare in population databases.",
        warnings=["population_frequency_source_snapshot"],
    ).model_copy(update={"warnings": None})
    response = LookupResponse(
        query="USH2A:c.2276G>T",
        species="human",
        report_payload=ReportPayload(
            patient_id="lookup_test",
            acmg_classification="ClinVar currently lists this variant as unavailable.",
            report_profile=VariantReportProfile(
                acmg_worksheet=AcmgWorksheetLedger(criteria=[criterion])
            ),
        ),
        evidence=[],
        warnings=[],
    )

    result = build_lookup_section_fetch_response(response, ["clingen_vcep"])

    clingen = result.sections["clingen_vcep"]
    assert clingen.status == "partial"
    assert clingen.payload is not None
    assert clingen.payload["narrative"] == "ClinVar currently lists this variant as unavailable."
    assert clingen.warnings == ["clingen_vcep_evidence_repo_source_cache_not_integrated"]
