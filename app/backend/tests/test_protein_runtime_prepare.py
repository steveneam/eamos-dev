from __future__ import annotations

import gzip
import json
import os
import stat
from pathlib import Path

from app.cli.eamos_protein_runtime_prepare import main as protein_runtime_prepare_main
from app.core.config import Settings
from app.services.protein_runtime import prepare_protein_annotation_runtime


def test_prepare_protein_runtime_extracts_pfam_and_runs_hmmpress(tmp_path: Path) -> None:
    hmmscan = _fake_executable(tmp_path, "hmmscan", _no_op_script())
    hmmpress = _fake_executable(tmp_path, "hmmpress", _hmmpress_script())
    source_gz = tmp_path / "downloads" / "Pfam-A.hmm.gz"
    runtime_hmm = tmp_path / "runtime" / "Pfam-A.hmm"
    source_gz.parent.mkdir()
    with gzip.open(source_gz, "wb") as handle:
        handle.write(b"HMMER3/f [test]\nNAME  PFTEST\n//\n")
    settings = Settings(
        jwt_secret="test-secret",
        protein_annotation_enabled=True,
        protein_annotation_hmmscan_path=hmmscan,
        protein_annotation_hmmpress_path=hmmpress,
        protein_annotation_pfam_hmm_path=runtime_hmm,
        protein_annotation_pfam_hmm_gz_path=source_gz,
    )

    result = prepare_protein_annotation_runtime(settings)

    assert result.ready is True
    assert result.status == "ready"
    assert result.hmmscan_available is True
    assert result.hmmpress_available is True
    assert result.pfam_hmm_extracted is True
    assert result.hmmpress_ran is True
    assert result.missing_index_count == 0
    assert runtime_hmm.read_bytes() == b"HMMER3/f [test]\nNAME  PFTEST\n//\n"
    for suffix in (".h3f", ".h3i", ".h3m", ".h3p"):
        assert runtime_hmm.with_suffix(runtime_hmm.suffix + suffix).is_file()


def test_prepare_protein_runtime_fails_closed_without_hmmpress(tmp_path: Path) -> None:
    hmmscan = _fake_executable(tmp_path, "hmmscan", _no_op_script())
    source_gz = tmp_path / "downloads" / "Pfam-A.hmm.gz"
    runtime_hmm = tmp_path / "runtime" / "Pfam-A.hmm"
    source_gz.parent.mkdir()
    with gzip.open(source_gz, "wb") as handle:
        handle.write(b"HMMER3/f [test]\n//\n")
    settings = Settings(
        jwt_secret="test-secret",
        protein_annotation_enabled=True,
        protein_annotation_hmmscan_path=hmmscan,
        protein_annotation_hmmpress_path=tmp_path / "missing-hmmpress",
        protein_annotation_pfam_hmm_path=runtime_hmm,
        protein_annotation_pfam_hmm_gz_path=source_gz,
    )

    result = prepare_protein_annotation_runtime(settings)

    assert result.ready is False
    assert result.status == "hmmpress_executable_missing"
    assert result.hmmscan_available is True
    assert result.hmmpress_available is False
    assert runtime_hmm.exists() is False


def test_protein_runtime_prepare_cli_emits_sanitized_ready_report(
    tmp_path: Path,
    capsys,
) -> None:
    hmmscan = _fake_executable(tmp_path, "hmmscan", _no_op_script())
    hmmpress = _fake_executable(tmp_path, "hmmpress", _hmmpress_script())
    source_gz = tmp_path / "downloads" / "Pfam-A.hmm.gz"
    runtime_hmm = tmp_path / "runtime" / "Pfam-A.hmm"
    source_gz.parent.mkdir()
    with gzip.open(source_gz, "wb") as handle:
        handle.write(b"HMMER3/f [test]\n//\n")

    exit_code = protein_runtime_prepare_main(
        [
            "--compact",
            "--require-ready",
            "--hmmscan-path",
            str(hmmscan),
            "--hmmpress-path",
            str(hmmpress),
            "--pfam-hmm-path",
            str(runtime_hmm),
            "--pfam-hmm-gz-path",
            str(source_gz),
        ]
    )

    captured = capsys.readouterr()
    body = json.loads(captured.out)
    assert exit_code == 0
    assert body["runtime"]["ready"] is True
    assert body["runtime"]["status"] == "ready"
    assert str(tmp_path).lower() not in captured.out.lower()
    assert body["guardrails"]["downloads"] == "not_used"
    assert body["guardrails"]["storage_buckets"] == "not_used"


def _fake_executable(tmp_path: Path, name: str, script: str) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    path = tmp_path / f"{name}{suffix}"
    path.write_text(script, encoding="utf-8")
    if os.name != "nt":
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _no_op_script() -> str:
    if os.name == "nt":
        return "@echo off\r\nexit /b 0\r\n"
    return "#!/bin/sh\nexit 0\n"


def _hmmpress_script() -> str:
    if os.name == "nt":
        return (
            "@echo off\r\n"
            'set "db=%~2"\r\n'
            'if "%db%"=="" set "db=%~1"\r\n'
            'type NUL > "%db%.h3f"\r\n'
            'type NUL > "%db%.h3i"\r\n'
            'type NUL > "%db%.h3m"\r\n'
            'type NUL > "%db%.h3p"\r\n'
            "exit /b 0\r\n"
        )
    return (
        "#!/bin/sh\n"
        'db="$2"\n'
        'if [ -z "$db" ]; then db="$1"; fi\n'
        ': > "$db.h3f"\n'
        ': > "$db.h3i"\n'
        ': > "$db.h3m"\n'
        ': > "$db.h3p"\n'
        "exit 0\n"
    )
