from __future__ import annotations

from app.schemas.run import ReportPayload


def test_report_payload_serializes_eamos_computed_classification_contract() -> None:
    payload = ReportPayload(
        patient_id="patient-1",
        eamos_computed_classification={
            "acmg_version_pin": {
                "framework": "Richards-2015 + Tavtigian-2020 points",
                "pvs1_revision": "Abou-Tayoun-2018",
                "pp3_calibration": "Pejaver-2022",
            },
            "net_points": 9,
            "sum_pathogenic": 9,
            "sum_benign": 0,
            "tier": "Likely Pathogenic",
            "conflict": {"is_conflicting": False},
            "ba1_override": False,
            "posterior": 0.988,
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
    assert block["net_points"] == 9
    assert block["tier"] == "Likely Pathogenic"
    assert block["benign_cut"] == "tavtigian_2020"
    assert block["per_criterion"][0]["applied_strength"] == "strong"
