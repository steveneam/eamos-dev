from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import httpx

from app.core.config import Settings
from app.tools.clinical_trials import (
    DISEASE_LEVEL_WARNING,
    DISCOVERY_ONLY_WARNING,
    GENE_LEVEL_WARNING,
    ClinicalTrialQuery,
    ClinicalTrialsTool,
    parse_clinicaltrials_v2_studies,
)


def _settings(**overrides) -> Settings:
    return Settings(jwt_secret="test-secret", **overrides)


def _study(
    *,
    nct_id: str = "NCT01234567",
    title: str = "RPE65 gene therapy study",
    status: str = "RECRUITING",
    phases: list[str] | None = None,
    conditions: list[str] | None = None,
    interventions: list[dict[str, str]] | None = None,
    locations: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": nct_id,
                "briefTitle": title,
                "officialTitle": f"Official title for {title}",
            },
            "statusModule": {"overallStatus": status},
            "designModule": {"phases": phases or ["PHASE1", "PHASE2"]},
            "conditionsModule": {"conditions": conditions or ["Leber congenital amaurosis"]},
            "armsInterventionsModule": {
                "interventions": interventions or [{"type": "BIOLOGICAL", "name": "AAV2-RPE65"}]
            },
            "contactsLocationsModule": {
                "locations": locations
                or [
                    {
                        "facility": "Inherited Retinal Disease Center",
                        "city": "Philadelphia",
                        "state": "Pennsylvania",
                        "country": "United States",
                        "status": "RECRUITING",
                    }
                ]
            },
        }
    }


def test_parser_extracts_variant_level_v2_study_row() -> None:
    payload = {
        "studies": [
            _study(
                title="RPE65 c.260A>G AAV follow-up study",
                interventions=[{"type": "GENETIC", "name": "Voretigene neparvovec"}],
            )
        ]
    }
    query = ClinicalTrialQuery(
        query_term='"c.260A>G"',
        requested_match_level="variant_level",
        variant_aliases=("c.260A>G", "p.Asp87Gly"),
        gene_terms=("RPE65",),
        disease_terms=("Leber congenital amaurosis",),
    )

    rows = parse_clinicaltrials_v2_studies(payload, query=query)

    assert len(rows) == 1
    row = rows[0]
    assert row.nct_id == "NCT01234567"
    assert row.title == "RPE65 c.260A>G AAV follow-up study"
    assert row.status == "RECRUITING"
    assert row.phase == "Phase 1/Phase 2"
    assert row.conditions == ("Leber congenital amaurosis",)
    assert row.interventions == ("Voretigene neparvovec",)
    assert row.locations == (
        "Inherited Retinal Disease Center - Philadelphia, Pennsylvania, United States - RECRUITING",
    )
    assert row.match_level == "variant_level"
    assert row.matched_terms == ("c.260A>G",)
    assert row.source_url == "https://clinicaltrials.gov/study/NCT01234567"
    assert DISCOVERY_ONLY_WARNING in row.warnings


def test_parser_labels_gene_and_disease_level_rows_without_variant_claims() -> None:
    payload = {
        "studies": [
            _study(
                title="RPE65-associated inherited retinal disease natural history",
                conditions=["Inherited retinal dystrophy"],
            ),
            _study(
                nct_id="NCT07654321",
                title="Natural history in Leber congenital amaurosis",
                conditions=["Leber congenital amaurosis"],
                interventions=[],
                locations=[],
            ),
        ]
    }

    gene_rows = parse_clinicaltrials_v2_studies(
        {"studies": [payload["studies"][0]]},
        query=ClinicalTrialQuery(
            query_term="RPE65",
            requested_match_level="gene_level",
            variant_aliases=("c.260A>G",),
            gene_terms=("RPE65",),
            disease_terms=("Leber congenital amaurosis",),
        ),
    )
    disease_rows = parse_clinicaltrials_v2_studies(
        {"studies": [payload["studies"][1]]},
        query=ClinicalTrialQuery(
            query_term='"Leber congenital amaurosis"',
            requested_match_level="disease_level",
            variant_aliases=("c.260A>G",),
            disease_terms=("Leber congenital amaurosis",),
        ),
    )

    assert gene_rows[0].match_level == "gene_level"
    assert gene_rows[0].matched_terms == ("RPE65",)
    assert GENE_LEVEL_WARNING in gene_rows[0].warnings
    assert DISCOVERY_ONLY_WARNING in gene_rows[0].warnings
    assert "not_eligibility" in " ".join(gene_rows[0].warnings)

    assert disease_rows[0].match_level == "disease_level"
    assert disease_rows[0].matched_terms == ("Leber congenital amaurosis",)
    assert DISEASE_LEVEL_WARNING in disease_rows[0].warnings
    assert DISCOVERY_ONLY_WARNING in disease_rows[0].warnings


def test_parser_filters_gene_scope_rows_without_matched_terms() -> None:
    payload = {
        "studies": [
            _study(
                nct_id="NCT05919342",
                title="SYMPHONY-HF heart failure trial",
                conditions=["Heart Failure"],
                interventions=[{"type": "DRUG", "name": "sotagliflozin"}],
            )
        ]
    }

    rows = parse_clinicaltrials_v2_studies(
        payload,
        query=ClinicalTrialQuery(
            query_term="USH2A",
            requested_match_level="gene_level",
            gene_terms=("USH2A",),
        ),
    )

    assert rows == []


def test_parser_filters_brca_query_scope_rows_without_exact_gene_match() -> None:
    payload = {
        "studies": [
            _study(
                nct_id="NCT07156253",
                title="Study of SYN818 With Olaparib for advanced solid tumors",
                conditions=["Metastatic Solid Tumor", "BRCA 1 /2 and / or HRD"],
                interventions=[{"type": "DRUG", "name": "SYN818 and Olaparib"}],
            )
        ]
    }

    rows = parse_clinicaltrials_v2_studies(
        payload,
        query=ClinicalTrialQuery(
            query_term="BRCA1",
            requested_match_level="gene_level",
            gene_terms=("BRCA1",),
        ),
    )

    assert rows == []


def test_tool_queries_variant_aliases_before_gene_disease_fallback(monkeypatch) -> None:
    calls: list[str] = []

    class Response:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return self.payload

    def fake_get(url: str, *, params: dict[str, Any], timeout: float) -> Response:
        calls.append(params["query.term"])
        assert url == "https://clinicaltrials.gov/api/v2/studies"
        assert params["filter.overallStatus"] == (
            "RECRUITING,ACTIVE_NOT_RECRUITING,NOT_YET_RECRUITING"
        )
        if len(calls) == 1:
            return Response({"studies": []})
        return Response(
            {
                "studies": [
                    _study(
                        title="RPE65 gene therapy in Leber congenital amaurosis",
                        conditions=["Leber congenital amaurosis"],
                    )
                ]
            }
        )

    monkeypatch.setattr("app.tools.clinical_trials.httpx.get", fake_get)
    variant = SimpleNamespace(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.260A>G",
        protein_change="p.Asp87Gly",
    )

    result = ClinicalTrialsTool(_settings(use_real_apis=True)).get_trial_matches(
        variant,
        disease_terms=["Leber congenital amaurosis"],
        limit=5,
    )

    assert len(calls) == 2
    assert calls[0].startswith('"NM_000329.3:c.260A>G" OR "p.Asp87Gly"')
    assert calls[1] == 'RPE65 "Leber congenital amaurosis"'
    assert result.status == "live"
    assert result.summary["trial_rows"][0]["match_level"] == "gene_level"
    assert result.summary["trial_rows"][0]["source_url"].endswith("/NCT01234567")
    assert "clinical_trials_variant_level_not_found" in result.warnings
    assert "variant_level_trial_not_found:using_lower_match_level" in result.warnings
    assert DISCOVERY_ONLY_WARNING in result.summary["trial_rows"][0]["warnings"]


def test_tool_degrades_source_failure_to_empty_rows(monkeypatch) -> None:
    def fail_get(*args, **kwargs):
        raise httpx.TimeoutException("clinicaltrials timeout")

    monkeypatch.setattr("app.tools.clinical_trials.httpx.get", fail_get)

    result = ClinicalTrialsTool(_settings(use_real_apis=True)).get_trial_matches(
        gene="RPE65",
        limit=3,
    )

    assert result.status == "fallback"
    assert result.summary["trial_rows"] == []
    assert result.summary["total"] == 0
    assert "clinical_trials_fetch_failed:TimeoutException" in result.warnings
