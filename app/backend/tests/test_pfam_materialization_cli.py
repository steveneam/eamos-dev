from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import httpx

from app.cli.eamos_pfam_runtime_materialize import main
from app.core.config import Settings
from app.services.pfam_materialization import materialize_pfam_hmm_gz_from_private_storage


def test_materialize_pfam_downloads_private_object_and_sanitizes_result(tmp_path: Path) -> None:
    payload = b"HMMER3/f [test]\nNAME PFTEST\n//\n"
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=payload)

    destination = tmp_path / "downloads" / "Pfam-A.hmm.gz"
    settings = Settings(
        jwt_secret="test-secret",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role-secret",
        protein_annotation_pfam_hmm_gz_path=destination,
    )
    result = materialize_pfam_hmm_gz_from_private_storage(
        settings,
        source_object_uri="supabase://eamos-source-assets/protein/Pfam-A.hmm.gz",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        expected_size_bytes=len(payload),
        expected_md5=hashlib.md5(payload).hexdigest(),
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )

    assert result.ready is True
    assert result.status == "ready"
    assert result.downloaded is True
    assert destination.read_bytes() == payload
    assert requests[0].headers["authorization"] == "Bearer service-role-secret"
    assert "service-role-secret" not in json.dumps(asdict(result))
    assert str(destination) not in json.dumps(asdict(result))


def test_materialize_pfam_rejects_checksum_mismatch_without_destination(
    tmp_path: Path,
) -> None:
    payload = b"wrong-pfam"

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload)

    destination = tmp_path / "downloads" / "Pfam-A.hmm.gz"
    settings = Settings(
        jwt_secret="test-secret",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role-secret",
        protein_annotation_pfam_hmm_gz_path=destination,
    )
    result = materialize_pfam_hmm_gz_from_private_storage(
        settings,
        source_object_uri="supabase://eamos-source-assets/protein/Pfam-A.hmm.gz",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        expected_size_bytes=len(payload),
        expected_md5="0" * 32,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )

    assert result.ready is False
    assert result.status == "md5_mismatch"
    assert result.downloaded is True
    assert not destination.exists()


def test_pfam_materialize_cli_fails_closed_without_storage_credentials(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    exit_code = main(
        [
            "--source-object-uri",
            "supabase://eamos-source-assets/protein/Pfam-A.hmm.gz",
            "--pfam-hmm-gz-path",
            str(tmp_path / "missing" / "Pfam-A.hmm.gz"),
            "--compact",
            "--require-ready",
        ]
    )

    assert exit_code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "pfam_runtime_materialize"
    assert output["guardrails"]["secrets_in_output"] == "blocked"
    assert output["materialization"]["status"] == "supabase_storage_credentials_missing"
    assert "Pfam-A.hmm.gz" not in json.dumps(output)
    assert "service_role" not in json.dumps(output).lower()
