from __future__ import annotations

import json
from pathlib import Path

from app.cli.eamos_crispr_offtarget_preflight import cli_main
from app.services.crispr_offtarget_index import build_spcas9_offtarget_index_from_sequences


def test_crispr_offtarget_preflight_auto_missing_index_warns_without_failing(
    tmp_path: Path,
    capsys,
) -> None:
    exit_code = cli_main(
        [
            "--provider",
            "auto",
            "--index-path",
            str(tmp_path / "missing.sqlite"),
            "--compact",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload).lower()
    assert exit_code == 0
    assert payload["ready_to_flip"] is False
    assert payload["public_runtime_available"] is True
    assert payload["runtime_status"] == "auto_mock_fallback_not_ready_to_flip"
    assert payload["provider_policy"]["auto_mode_warns_and_uses_mock_fallback"] is True
    assert payload["provider_policy"]["forced_indexed_sqlite_fails_closed"] is False
    assert payload["indexed_sqlite"]["status"] == "missing"
    assert payload["guardrails"]["local_path_values_emitted"] is False
    assert str(tmp_path).lower() not in encoded


def test_crispr_offtarget_preflight_forced_index_missing_fails_closed(
    tmp_path: Path,
    capsys,
) -> None:
    exit_code = cli_main(
        [
            "--provider",
            "indexed_sqlite",
            "--index-path",
            str(tmp_path / "missing.sqlite"),
            "--require-ready",
            "--compact",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload).lower()
    assert exit_code == 2
    assert payload["ready_to_flip"] is False
    assert payload["public_runtime_available"] is False
    assert payload["runtime_status"] == "forced_indexed_sqlite_not_ready_fail_closed"
    assert payload["provider_policy"]["auto_mode_warns_and_uses_mock_fallback"] is False
    assert payload["provider_policy"]["forced_indexed_sqlite_fails_closed"] is True
    assert str(tmp_path).lower() not in encoded


def test_crispr_offtarget_preflight_ready_index_passes_require_ready(
    tmp_path: Path,
    capsys,
) -> None:
    guide = "GAGTCCGAGCAGAAGAAGAT"
    index_path = tmp_path / "spcas9_offtargets.sqlite"
    build_spcas9_offtarget_index_from_sequences(
        [("1", f"{guide}AGG{'N' * 20}")],
        index_path,
        genome_build="GRCh38",
        source_version="pytest-mini",
    )

    exit_code = cli_main(
        [
            "--provider",
            "indexed_sqlite",
            "--index-path",
            str(index_path),
            "--require-ready",
            "--compact",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload).lower()
    assert exit_code == 0
    assert payload["ready_to_flip"] is True
    assert payload["public_runtime_available"] is True
    assert payload["runtime_status"] == "indexed_ready"
    assert payload["indexed_sqlite"]["verification_ready"] is True
    assert payload["indexed_sqlite"]["target_count"] == 1
    assert str(tmp_path).lower() not in encoded
