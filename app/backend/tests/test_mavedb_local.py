from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from app.cli import eamos_mavedb_local_materialize
from app.core.config import Settings
from app.services.build_ledger import build_backend_build_ledger
from app.services.mavedb_local import (
    MaveDbLocalStore,
    inspect_mavedb_local_store,
    materialize_mavedb_local_store,
)


def test_mavedb_local_materialization_filters_to_cc0_public_scores(tmp_path: Path) -> None:
    source = tmp_path / "mavedb.jsonl"
    source.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {
                    "score_set_id": "urn:mavedb:0001",
                    "gene": "RPE65",
                    "variant": "NM_000329.3:c.1301C>T",
                    "score": 0.12,
                    "license": "CC0-1.0",
                    "url": "https://www.mavedb.org/score-sets/urn:mavedb:0001",
                },
                {
                    "score_set_id": "urn:mavedb:0002",
                    "gene": "RPE65",
                    "variant": "NM_000329.3:c.11+5G>A",
                    "score": 0.8,
                    "license": "CC BY 4.0",
                },
                {
                    "score_set_id": "urn:mavedb:0003",
                    "gene": "RPE65",
                    "variant": "NM_000329.3:c.260A>G",
                    "license": "CC0",
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "mavedb-local.sqlite"
    manifest_path = tmp_path / "mavedb-local.manifest.json"
    settings = Settings(
        jwt_secret="test-secret",
        mavedb_local_sqlite_path=db_path,
        mavedb_local_manifest_path=manifest_path,
    )

    result = materialize_mavedb_local_store(
        settings,
        jsonl_files=[source],
        source_version="mavedb-test-v1",
    )

    assert result.ready is True
    assert result.accepted_count == 1
    assert result.rejected_count == 2
    assert result.warnings == (
        "mavedb_non_cc0_rejected:urn:mavedb:0002",
        "mavedb_missing_score_rejected:urn:mavedb:0003",
    )
    inspection = inspect_mavedb_local_store(settings, verify_checksum=True)
    assert inspection.ready is True
    assert inspection.checksum_verified is True
    assert inspection.source_version == "mavedb-test-v1"
    assert manifest_path.is_file()
    encoded = json.dumps(inspection.to_sanitized_dict()).lower()
    assert str(tmp_path).lower() not in encoded
    assert "nm_000329" not in encoded

    records, request_inspection = MaveDbLocalStore(db_path).search_records(
        SimpleNamespace(
            gene="RPE65",
            transcript_hgvs="NM_000329.3:c.1301C>T",
            protein_change="p.Ala434Val",
            genomic_hg38="",
            genomic_hgvs="",
            dbsnp_rsid="",
        ),
        limit=10,
    )

    assert request_inspection.ready is True
    assert [record.score_set_id for record in records] == ["urn:mavedb:0001"]

    ledger_items = {item["item_id"]: item for item in build_backend_build_ledger(settings)["items"]}
    assert ledger_items["mavedb"]["status"] == "ready"
    assert ledger_items["mavedb"]["public_serialization_allowed"] is True
    assert ledger_items["mavedb"]["blockers"] == []


def test_mavedb_local_materialize_cli_emits_sanitized_guardrails(
    tmp_path: Path,
    capsys,
) -> None:
    source = tmp_path / "mavedb.jsonl"
    source.write_text(
        json.dumps(
            {
                "score_set_id": "urn:mavedb:0001",
                "gene": "RPE65",
                "variant": "NM_000329.3:c.1301C>T",
                "score": 0.12,
                "license": "CC0",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "mavedb-local.sqlite"
    manifest_path = tmp_path / "mavedb-local.manifest.json"

    exit_code = eamos_mavedb_local_materialize.main(
        [
            "--input-jsonl",
            str(source),
            "--output",
            str(db_path),
            "--manifest-path",
            str(manifest_path),
            "--source-version",
            "mavedb-test-v1",
            "--require-ready",
            "--compact",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "eamos_mavedb_local_materialize"
    assert payload["guardrails"] == {
        "network": "not_used",
        "provider_flips": "not_used",
        "render": "not_used",
        "startup_downloads": "not_used",
        "supabase": "not_used",
    }
    assert payload["materialization"]["ready"] is True
    encoded = json.dumps(payload).lower()
    assert str(tmp_path).lower() not in encoded
    assert "nm_000329" not in encoded
