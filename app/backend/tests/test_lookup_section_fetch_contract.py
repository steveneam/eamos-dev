from __future__ import annotations

import json


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
    assert "computational_deep_dive" not in profile
    assert "expert_panel" not in profile
    assert profile["acmg_worksheet"]["classification"] == "Likely pathogenic"
    assert full_payload["publications_literature"]["total_count"] == 3
    assert full_payload["report_profile"]["computational_deep_dive"]["predictors"]
    assert full_payload["report_profile"]["expert_panel"]["final_classification"] == (
        "likely_pathogenic"
    )
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
            "include": ["publications", "computational_deep_dive", "clingen_vcep"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "RPE65:c.260A>G"
    sections = body["sections"]
    assert set(sections) == {"publications", "computational_deep_dive", "clingen_vcep"}

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

    computational = sections["computational_deep_dive"]
    assert computational["status"] == "available"
    predictor_names = {row["name"] for row in computational["payload"]["predictors"]}
    assert {"REVEL", "CADD PHRED", "PrimateAI-3D", "MetaLR", "SpliceAI"} <= predictor_names
    assert "AlphaMissense" not in predictor_names
    predictors_by_name = {row["name"]: row for row in computational["payload"]["predictors"]}
    assert predictors_by_name["REVEL"]["calibration_bucket"] == "Likely pathogenic"
    assert predictors_by_name["CADD PHRED"]["calibration_bucket"] == "VUS"
    assert predictors_by_name["SpliceAI"]["calibration_method"] == (
        "Walker 2023 / ClinGen SVI splicing"
    )
    assert predictors_by_name["MetaLR"]["calibration_bucket"] is None
    assert computational["freshness"]["stale_on_failure"] is False

    clingen = sections["clingen_vcep"]
    assert clingen["status"] == "available"
    assert clingen["payload"]["vcep"]["name"] == "Inherited Retinal Dystrophies VCEP"
    assert clingen["payload"]["final_classification"] == "likely_pathogenic"
    assert clingen["payload"]["criteria"][0]["applied_strength"] == "PM2_Moderate"
    assert clingen["payload"]["criteria"][0]["assertion_level"] == "vcep_specified"
    assert clingen["payload"]["freshness"] == "fresh"
    assert "ClinGen Evidence Repository" in clingen["payload"]["source_scope"]
    assert clingen["warnings"] == []
    assert clingen["freshness"]["stale_on_failure"] is False


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
