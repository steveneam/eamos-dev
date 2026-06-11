from __future__ import annotations

import json
from pathlib import Path

from app.cli.eamos_crispr_tide import main

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures" / "workbench"


def test_crispr_tide_cli_reports_source_backed_observed_result(capsys) -> None:
    trace_path = FIXTURES_DIR / "rpe65_vus1.ab1"

    exit_code = main(
        [
            "--control",
            str(trace_path),
            "--edited",
            str(trace_path),
            "--cut-site-index",
            "100",
            "--compact",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "local_observed_tide"
    assert output["guardrails"]["network"] == "not_used"
    assert output["guardrails"]["prediction"] == "not_used"
    assert output["inputs"]["control"]["name"] == "rpe65_vus1.ab1"
    assert output["inputs"]["control_base_calls"] > 100
    assert output["result"]["source_backed"] is True
    assert output["result"]["analysis_kind"] == "tide"
    assert output["result"]["predicted_available"] is False
    assert output["result"]["spectrum"][0]["size"] == 0


def test_crispr_tide_cli_returns_structured_error_for_bad_trace(
    tmp_path: Path,
    capsys,
) -> None:
    control_path = tmp_path / "control.ab1"
    edited_path = FIXTURES_DIR / "rpe65_vus1.ab1"
    control_path.write_bytes(b"not-an-ab1")

    exit_code = main(
        [
            "--control",
            str(control_path),
            "--edited",
            str(edited_path),
            "--cut-site-index",
            "100",
            "--compact",
        ]
    )

    assert exit_code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "error"
    assert output["error"]["code"] == "trace_unsupported_format"
    assert output["error"]["warnings"] == ["trace_unsupported_format"]
