from __future__ import annotations

from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

import httpx

from app.cli.eamos_compact_index_materialize import main
from app.core.config import Settings
from app.services.compact_coordinate_index import inspect_compact_coordinate_index
from app.services.compact_coordinate_index_materialization import (
    materialize_compact_coordinate_index,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures"
COMPACT_INDEX_FIXTURE = FIXTURES_DIR / "coordinate_index" / "eamos_coordinate_index_tiny.jsonl"


def test_materialize_compact_index_copies_local_artifact_and_sanitizes_result(
    tmp_path: Path,
) -> None:
    payload = COMPACT_INDEX_FIXTURE.read_bytes()
    destination = tmp_path / "runtime" / "eamos-coordinate-index.latest.jsonl"
    settings = Settings(
        jwt_secret="test-secret",
        coordinate_resolver_compact_index_path=destination,
    )

    result = materialize_compact_coordinate_index(
        settings,
        source_artifact_path=COMPACT_INDEX_FIXTURE,
        expected_size_bytes=len(payload),
        expected_md5=hashlib.md5(payload).hexdigest(),
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )

    assert result.ready is True
    assert result.status == "ready"
    assert result.source_kind == "local_file"
    assert result.copied is True
    assert result.downloaded is False
    assert result.md5_verified is True
    assert result.sha256_verified is True
    assert result.schema_validated is True
    assert result.variant_count == 2
    assert result.transcript_count == 2
    assert destination.read_bytes() == payload
    assert inspect_compact_coordinate_index(settings).ready is True

    encoded = json.dumps(asdict(result)).lower()
    assert str(COMPACT_INDEX_FIXTURE).lower() not in encoded
    assert str(destination).lower() not in encoded


def test_materialize_compact_index_rejects_schema_invalid_local_artifact(
    tmp_path: Path,
) -> None:
    source = tmp_path / "bad-index.jsonl"
    source.write_text(
        json.dumps(
            {
                "record_type": "metadata",
                "schema_version": "wrong",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    payload = source.read_bytes()
    destination = tmp_path / "runtime" / "eamos-coordinate-index.latest.jsonl"
    settings = Settings(
        jwt_secret="test-secret",
        coordinate_resolver_compact_index_path=destination,
    )

    result = materialize_compact_coordinate_index(
        settings,
        source_artifact_path=source,
        expected_size_bytes=len(payload),
        expected_md5=hashlib.md5(payload).hexdigest(),
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )

    assert result.ready is False
    assert result.status == "schema_validation_failed"
    assert result.md5_verified is True
    assert result.sha256_verified is True
    assert result.schema_validated is False
    assert result.warnings[-1] == "compact_index_destination_not_modified"
    assert not destination.exists()


def test_materialize_compact_index_rejects_invalid_local_manifest(
    tmp_path: Path,
) -> None:
    source = tmp_path / "index.jsonl"
    source.write_bytes(COMPACT_INDEX_FIXTURE.read_bytes())
    source.with_suffix(source.suffix + ".manifest.json").write_text(
        "{not-json",
        encoding="utf-8",
    )
    destination = tmp_path / "runtime" / "eamos-coordinate-index.latest.jsonl"
    settings = Settings(
        jwt_secret="test-secret",
        coordinate_resolver_compact_index_path=destination,
    )

    result = materialize_compact_coordinate_index(
        settings,
        source_artifact_path=source,
    )

    assert result.ready is False
    assert result.status == "manifest_invalid_json"
    assert not destination.exists()


def test_materialize_compact_index_rejects_invalid_explicit_checksum(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "runtime" / "eamos-coordinate-index.latest.jsonl"
    settings = Settings(
        jwt_secret="test-secret",
        coordinate_resolver_compact_index_path=destination,
    )

    result = materialize_compact_coordinate_index(
        settings,
        source_artifact_path=COMPACT_INDEX_FIXTURE,
        expected_size_bytes=COMPACT_INDEX_FIXTURE.stat().st_size,
        expected_sha256="not-a-sha256",
    )

    assert result.ready is False
    assert result.status == "expected_identity_invalid"
    assert not destination.exists()


def test_materialize_compact_index_downloads_private_object_with_manifest(
    tmp_path: Path,
) -> None:
    payload = COMPACT_INDEX_FIXTURE.read_bytes()
    object_path = "coordinate/eamos-coordinate-index.latest.jsonl"
    manifest = {
        "byte_size": len(payload),
        "checksums": {
            "md5": hashlib.md5(payload).hexdigest(),
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
    }
    requests: list[httpx.Request] = []
    payloads = {
        _encoded_storage_path(f"{object_path}.manifest.json"): json.dumps(manifest).encode("utf-8"),
        _encoded_storage_path(object_path): payload,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        content = payloads.get(request.url.path.rsplit("/", 1)[-1])
        if content is None:
            key = request.url.path.split("/storage/v1/object/eamos-source-assets/", 1)[-1]
            content = payloads.get(key)
        return httpx.Response(200, content=content or b"")

    destination = tmp_path / "runtime" / "eamos-coordinate-index.latest.jsonl"
    settings = Settings(
        jwt_secret="test-secret",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role-secret",
        coordinate_resolver_compact_index_path=destination,
    )

    result = materialize_compact_coordinate_index(
        settings,
        source_object_uri=f"supabase://eamos-source-assets/{object_path}",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.ready is True
    assert result.status == "ready"
    assert result.source_kind == "supabase_private_storage"
    assert result.bucket_id == "eamos-source-assets"
    assert result.downloaded is True
    assert result.copied is False
    assert result.md5_verified is True
    assert result.sha256_verified is True
    assert destination.read_bytes() == payload
    assert requests[0].headers["authorization"] == "Bearer service-role-secret"

    encoded = json.dumps(asdict(result))
    assert "service-role-secret" not in encoded
    assert str(destination) not in encoded
    assert object_path not in encoded
    assert "supabase://" not in encoded


def test_materialize_compact_index_validates_gzip_private_object_with_temp_suffix(
    tmp_path: Path,
) -> None:
    payload = gzip.compress(COMPACT_INDEX_FIXTURE.read_bytes(), mtime=0)
    object_path = "coordinate/eamos-coordinate-index.latest.jsonl.gz"
    manifest = {
        "byte_size": len(payload),
        "checksums": {
            "md5": hashlib.md5(payload).hexdigest(),
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
    }
    payloads = {
        _encoded_storage_path(f"{object_path}.manifest.json"): json.dumps(manifest).encode("utf-8"),
        _encoded_storage_path(object_path): payload,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.url.path.split("/storage/v1/object/eamos-source-assets/", 1)[-1]
        return httpx.Response(200, content=payloads.get(key, b""))

    destination = tmp_path / "runtime" / "eamos-coordinate-index.latest.jsonl.gz"
    settings = Settings(
        jwt_secret="test-secret",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role-secret",
        coordinate_resolver_compact_index_path=destination,
    )

    result = materialize_compact_coordinate_index(
        settings,
        source_object_uri=f"supabase://eamos-source-assets/{object_path}",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.ready is True
    assert result.status == "ready"
    assert result.downloaded is True
    assert result.schema_validated is True
    assert result.transcript_count == 2
    assert destination.read_bytes() == payload


def test_compact_index_materialize_cli_fails_closed_without_source(
    capsys,
    tmp_path: Path,
) -> None:
    exit_code = main(
        [
            "--compact",
            "--require-ready",
            "--compact-index-path",
            str(tmp_path / "missing-index.jsonl"),
        ]
    )

    assert exit_code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "eamos_compact_index_materialize"
    assert output["guardrails"]["startup_downloads"] == "not_used"
    assert output["materialization"]["status"] == "source_unconfigured"
    assert output["materialization"]["source_configured"] is False
    assert str(tmp_path) not in json.dumps(output)


def _encoded_storage_path(object_path: str) -> str:
    return "/".join(quote(part, safe="") for part in object_path.split("/"))
