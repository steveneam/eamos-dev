from __future__ import annotations

import json

from app.core.config import get_settings
from app.cli.search_input_ai_smoke import main


def test_search_input_ai_smoke_cli_runs_mock_cftr_prompt(capsys) -> None:
    exit_code = main(
        [
            "--mock",
            "--expect-gene",
            "CFTR",
            "--expect-protein",
            "p.Leu441fs",
            "--expect-mode",
            "suggestions",
            "--expect-candidate-id",
            "source:CFTR_c.1321_1323del",
            "--compact",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "passed"
    assert output["mode"] == "mock"
    assert output["report_allowed"] is False
    assert output["interpretation"]["gene"] == "CFTR"
    assert output["interpretation"]["protein_change"] == "p.Leu441fs"


def test_search_input_ai_smoke_cli_can_skip_unconfigured_live_provider(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    exit_code = main(["--skip-if-unconfigured", "--compact"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "skipped"
    assert output["mode"] == "live"
    assert any("LLM_PROVIDER is mock" in reason for reason in output["reasons"])
    get_settings.cache_clear()
