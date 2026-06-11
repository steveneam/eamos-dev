from __future__ import annotations

import json
from pathlib import Path

from app.services.crispr_offtarget_index import (
    build_spcas9_offtarget_index_from_sequences,
    cli_main,
)


def test_offtarget_index_estimate_cli_reports_sanitized_capacity(
    tmp_path: Path,
    capsys,
) -> None:
    guide = "GAGTCCGAGCAGAAGAAGAT"
    fasta_path = tmp_path / "tiny.fa"
    fasta_path.write_text(f">chr1\n{guide}AGG{'N' * 20}\n", encoding="utf-8")

    exit_code = cli_main(
        [
            "estimate",
            "--fasta",
            str(fasta_path),
            "--genome-build",
            "GRCh38",
            "--source-version",
            "pytest-mini",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["schema_version"] == "eamos.crispr_spcas9_offtargets.v1"
    assert payload["genome_build"] == "GRCh38"
    assert payload["target_count"] >= 1
    assert payload["estimated_sqlite_bytes"] >= 65_536
    assert payload["local_path_values_emitted"] is False
    assert str(tmp_path).lower() not in json.dumps(payload).lower()


def test_offtarget_index_verify_and_manifest_cli_are_sanitized(
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

    verify_code = cli_main(
        [
            "verify",
            "--index",
            str(index_path),
            "--genome-build",
            "GRCh38",
            "--min-target-count",
            "1",
        ]
    )
    verify_payload = json.loads(capsys.readouterr().out)

    manifest_code = cli_main(
        [
            "manifest",
            "--index",
            str(index_path),
            "--artifact-uri",
            "supabase://bucket/crispr/spcas9.sqlite",
            "--source-version",
            "pytest-mini",
        ]
    )
    manifest_payload = json.loads(capsys.readouterr().out)

    assert verify_code == 0
    assert verify_payload["verification_ready"] is True
    assert verify_payload["genome_build_matches"] is True
    assert verify_payload["target_count_meets_min"] is True
    assert verify_payload["local_path_values_emitted"] is False
    assert manifest_code == 0
    assert manifest_payload["ready"] is True
    assert manifest_payload["actual_sha256"]
    assert len(manifest_payload["actual_sha256"]) == 64
    assert manifest_payload["artifact_uri"] == "supabase://bucket/crispr/spcas9.sqlite"
    assert manifest_payload["local_path_values_emitted"] is False
    encoded = json.dumps({"verify": verify_payload, "manifest": manifest_payload}).lower()
    assert str(tmp_path).lower() not in encoded
