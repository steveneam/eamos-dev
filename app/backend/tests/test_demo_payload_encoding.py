from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.tools.base import FixtureBackedTool

MOJIBAKE_MARKERS = ("\u00c2", "\u00e2")
CONTROL_MOJIBAKE_RANGE = range(0x80, 0xA0)


def test_lookup_payload_does_not_emit_utf8_as_latin1_mojibake(client) -> None:
    response = client.post(
        "/api/v1/lookup",
        json={"gene": "RPE65", "cdna": "c.260A>G"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    _assert_no_mojibake(payload)

    report = payload["report_payload"]
    assert report["locus_context"]["coords"] == (
        "chr1 : 68,444,849 — 68,444,889  ·  RPE65 exon 4  ·  (+) strand"
    )
    assert report["curated_variants_distribution"]["subtitle"] == (
        "1,286 classified variants · ClinVar + UniProt"
    )
    assert "No disagreement to flag — the in-silico signal" in (
        report["in_silico_predictions"]["consensus_note"]
    )


def test_report_demo_sample_json_does_not_ship_utf8_as_latin1_mojibake() -> None:
    sample_path = Path(__file__).resolve().parents[2] / "web" / "lib" / "rpe65-sample.json"
    payload = json.loads(sample_path.read_text(encoding="utf-8"))

    _assert_no_mojibake(payload)

    report = payload["report_payload"]
    assert report["locus_context"]["coords"] == (
        "chr1 : 68,444,849 — 68,444,889  ·  RPE65 exon 4  ·  (+) strand"
    )
    assert report["associated_conditions"][0]["source_list"] == (
        "OMIM · Monarch · DECIPHER · GenCC · ClinGen"
    )


def test_report_demo_sample_json_carries_calibrated_predictor_fields() -> None:
    sample_path = Path(__file__).resolve().parents[2] / "web" / "lib" / "rpe65-sample.json"
    payload = json.loads(sample_path.read_text(encoding="utf-8"))

    predictors = {
        row["name"]: row
        for row in payload["report_payload"]["report_profile"]["computational_deep_dive"][
            "predictors"
        ]
    }

    assert predictors["REVEL"]["calibration_bucket"] == "Likely pathogenic"
    assert predictors["CADD PHRED"]["calibration_bucket"] == "VUS"
    assert predictors["SpliceAI"]["calibration_method"] == "Walker 2023 / ClinGen SVI splicing"
    assert predictors["PrimateAI-3D"]["calibrated_label"] is None
    assert predictors["MetaLR"]["calibration_version"] is None


def test_fixture_backed_tool_reads_fixtures_as_utf8(tmp_path: Path) -> None:
    fixtures_root = tmp_path / "fixtures"
    tools_root = fixtures_root / "tools"
    tools_root.mkdir(parents=True)
    (tools_root / "unicode.json").write_text(
        json.dumps({"text": "clean — separator · kept"}, ensure_ascii=False),
        encoding="utf-8",
    )

    class UnicodeFixtureTool(FixtureBackedTool):
        fixture_name = "unicode.json"

        def fixture_path(self) -> Path:
            return tools_root / self.fixture_name

    settings = Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
    )

    assert UnicodeFixtureTool(settings).load_fixture() == {"text": "clean — separator · kept"}


def _assert_no_mojibake(value: Any, path: str = "$") -> None:
    if isinstance(value, str):
        assert not any(
            marker in value for marker in MOJIBAKE_MARKERS
        ), f"{path} contains UTF-8-as-Latin-1 mojibake: {value!r}"
        assert not any(
            ord(character) in CONTROL_MOJIBAKE_RANGE for character in value
        ), f"{path} contains C1 control mojibake: {value!r}"
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_no_mojibake(item, f"{path}[{index}]")
        return

    if isinstance(value, dict):
        for key, item in value.items():
            _assert_no_mojibake(item, f"{path}.{key}")
