from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.run import EamosComputedClassification, ReportPayload
from app.services.acmg_points_engine import AcmgCriterionApplication, compute_acmg_points


def test_report_payload_serializes_eamos_computed_classification_contract() -> None:
    payload = ReportPayload(
        patient_id="patient-1",
        eamos_computed_classification={
            "acmg_version_pin": {
                "framework": "Richards-2015 + Tavtigian-2020 points",
                "ruleset_id": "richards_2015_tavtigian_2020_eamos_v1",
                "ruleset_version": "eamos-historical-replay-v1",
                "conflict_policy_id": "eamos_legacy_vus_cap",
                "pvs1_revision": "Abou-Tayoun-2018",
                "pp3_calibration": "Pejaver-2022",
                "population_policy_id": "acmg_svi_general_frequency_v1",
                "population_policy_version": "1.0.0",
            },
            "net_points": 9,
            "sum_pathogenic": 9,
            "sum_benign": 0,
            "tier": "Likely Pathogenic",
            "classification_basis": "bayesian_points",
            "conflict": {"is_conflicting": False},
            "ba1_override": False,
            "aggregate_evidence_likelihood_ratio": 720,
            "prior_odds": 0.111111,
            "posterior_odds": 80,
            "model_posterior": 0.988,
            "benign_cut": "tavtigian_2020",
            "per_criterion": [
                {
                    "code": "PVS1",
                    "direction": "pathogenic",
                    "triggered": True,
                    "applied_strength": "strong",
                    "points": 4,
                    "source_db": "NMDetective",
                    "source_version": "v1",
                    "svi_reference": "Abou-Tayoun-2018",
                },
                {
                    "code": "BA1",
                    "direction": "benign",
                    "triggered": False,
                    "applied_strength": None,
                    "points": 0,
                },
            ],
        },
    )

    block = payload.model_dump(mode="json")["eamos_computed_classification"]
    assert block["acmg_version_pin"]["framework"] == "Richards-2015 + Tavtigian-2020 points"
    assert block["acmg_version_pin"]["population_policy_diff"] == []
    assert block["net_points"] == "9"
    assert block["tier"] == "Likely Pathogenic"
    assert block["classification_basis"] == "bayesian_points"
    assert block["model_posterior"] == "0.988"
    assert "posterior" not in block
    assert block["benign_cut"] == "tavtigian_2020"
    assert block["per_criterion"][0]["applied_strength"] == "strong"


def test_ba1_contract_rejects_a_fake_point_model_posterior() -> None:
    encoded = compute_acmg_points([AcmgCriterionApplication("BA1")]).model_dump()
    encoded["model_posterior"] = 0.1

    with pytest.raises(ValidationError, match="cannot expose Bayesian model quantities"):
        EamosComputedClassification.model_validate(encoded)
