from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import quote

import httpx

from app.cli import eamos_local_evidence_runtime_seed
from app.core.config import Settings
from app.services.local_evidence_runtime_assets import inspect_local_evidence_runtime_assets
from app.services.local_evidence_runtime_seed import materialize_local_evidence_runtime_asset
from app.services.source_storage_uploads import SourceStorageUploadMode


def test_local_evidence_runtime_seed_copies_phylop_local_artifact_without_paths(
    tmp_path: Path,
) -> None:
    payload = b"tiny-bigwig-placeholder"
    source = tmp_path / "source" / "hg38.phyloP100way.bw"
    source.parent.mkdir(parents=True)
    source.write_bytes(payload)
    destination = tmp_path / "runtime" / "hg38.phyloP100way.bw"
    settings = Settings(jwt_secret="test-secret", phylop_runtime_bigwig_path=destination)

    result = materialize_local_evidence_runtime_asset(
        settings,
        role="phylop_bigwig",
        source_artifact_path=source,
        expected_size_bytes=len(payload),
        expected_md5=hashlib.md5(payload).hexdigest(),
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )

    assert result.ready is True
    assert result.status == "ready"
    assert result.item_id == "phylop_conservation_reader"
    assert result.source_kind == "local_file"
    assert result.copied is True
    assert result.downloaded is False
    assert result.md5_verified is True
    assert result.sha256_verified is True
    assert destination.read_bytes() == payload

    runtime = inspect_local_evidence_runtime_assets(settings)
    phylop = {source["item_id"]: source for source in runtime["sources"]}[
        "phylop_conservation_reader"
    ]
    assert phylop["status"] == "ready"
    assert phylop["ready_asset_count"] == 1

    encoded = json.dumps(result.to_sanitized_dict()).lower()
    assert str(tmp_path).lower() not in encoded
    assert "supabase://" not in encoded


def test_local_evidence_runtime_seed_downloads_phylop_private_object_rest(
    tmp_path: Path,
) -> None:
    payload = b"phylop-bigwig"
    object_path = "ucsc_phylop100way_hg38/hg38.phyloP100way.bw"
    manifest = _manifest(payload, source_id="ucsc_phylop100way_hg38", role="phylop_bigwig")
    payloads = {
        _encoded_storage_path(f"{object_path}.manifest.json"): json.dumps(manifest).encode("utf-8"),
        _encoded_storage_path(object_path): payload,
    }
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        key = request.url.path.split("/storage/v1/object/eamos-source-assets/", 1)[-1]
        content = payloads.get(key)
        if content is None:
            return httpx.Response(404)
        return httpx.Response(200, content=content)

    destination = tmp_path / "runtime" / "hg38.phyloP100way.bw"
    settings = Settings(
        jwt_secret="test-secret",
        supabase_url="https://project.supabase.co",
        supabase_service_role_key="service-role-secret",
        phylop_runtime_bigwig_path=destination,
    )

    result = materialize_local_evidence_runtime_asset(
        settings,
        role="phylop_bigwig",
        source_object_uri=f"supabase://eamos-source-assets/{object_path}",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.ready is True
    assert result.status == "ready"
    assert result.source_kind == "supabase_private_storage_rest"
    assert result.downloaded is True
    assert result.copied is False
    assert result.bucket_id == "eamos-source-assets"
    assert destination.read_bytes() == payload
    assert requests[0].headers["authorization"] == "Bearer service-role-secret"

    encoded = json.dumps(result.to_sanitized_dict()).lower()
    assert object_path.lower() not in encoded
    assert "service-role-secret" not in encoded
    assert str(tmp_path).lower() not in encoded


def test_local_evidence_runtime_seed_downloads_phylop_private_object_from_s3(
    tmp_path: Path,
) -> None:
    payload = b"phylop-bigwig-from-s3"
    object_path = "ucsc_phylop100way_hg38/hg38.phyloP100way.bw"
    payloads = {
        f"{object_path}.manifest.json": json.dumps(
            _manifest(payload, source_id="ucsc_phylop100way_hg38", role="phylop_bigwig")
        ).encode("utf-8"),
        object_path: payload,
    }

    class Body:
        def __init__(self, content: bytes) -> None:
            self._content = content

        def read(self) -> bytes:
            return self._content

    class FakeS3Client:
        def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
            assert Bucket == "eamos-source-assets"
            return {"Body": Body(payloads[Key])}

        def download_fileobj(self, bucket: str, key: str, fileobj, **_kwargs: object) -> None:
            assert bucket == "eamos-source-assets"
            fileobj.write(payloads[key])

    destination = tmp_path / "runtime" / "hg38.phyloP100way.bw"
    settings = Settings(jwt_secret="test-secret", phylop_runtime_bigwig_path=destination)

    result = materialize_local_evidence_runtime_asset(
        settings,
        role="phylop_bigwig",
        source_object_uri=f"supabase://eamos-source-assets/{object_path}",
        download_mode=SourceStorageUploadMode.S3_MULTIPART,
        s3_client=FakeS3Client(),
    )

    assert result.ready is True
    assert result.status == "ready"
    assert result.source_kind == "supabase_private_storage_s3"
    assert result.downloaded is True
    assert destination.read_bytes() == payload
    encoded = json.dumps(result.to_sanitized_dict()).lower()
    assert object_path.lower() not in encoded
    assert str(tmp_path).lower() not in encoded


def test_local_evidence_runtime_seed_rejects_checksum_mismatch_without_destination(
    tmp_path: Path,
) -> None:
    payload = b"wrong-content"
    source = tmp_path / "source" / "hg38.phyloP100way.bw"
    source.parent.mkdir(parents=True)
    source.write_bytes(payload)
    destination = tmp_path / "runtime" / "hg38.phyloP100way.bw"
    settings = Settings(jwt_secret="test-secret", phylop_runtime_bigwig_path=destination)

    result = materialize_local_evidence_runtime_asset(
        settings,
        role="phylop_bigwig",
        source_artifact_path=source,
        expected_size_bytes=len(payload),
        expected_md5="0" * 32,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )

    assert result.ready is False
    assert result.status == "md5_mismatch"
    assert result.copied is True
    assert result.warnings[-1] == "runtime_destination_not_modified"
    assert not destination.exists()


def test_local_evidence_runtime_seed_cli_fails_closed_without_source(
    capsys,
    tmp_path: Path,
) -> None:
    exit_code = eamos_local_evidence_runtime_seed.main(
        [
            "--role",
            "phylop_bigwig",
            "--destination",
            str(tmp_path / "runtime" / "hg38.phyloP100way.bw"),
            "--compact",
            "--require-ready",
        ]
    )

    assert exit_code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "eamos_local_evidence_runtime_seed"
    assert output["status"] == "source_unconfigured"
    assert output["guardrails"]["startup_download"] == "not_used"
    assert output["guardrails"]["provider_flip"] == "not_used"
    assert output["guardrails"]["local_evidence_enabled_flip"] == "not_used"
    assert output["materialization"]["role"] == "phylop_bigwig"
    encoded = json.dumps(output).lower()
    assert str(tmp_path).lower() not in encoded
    assert "supabase://" not in encoded


def _manifest(payload: bytes, *, source_id: str, role: str) -> dict[str, object]:
    return {
        "source_id": source_id,
        "role": role,
        "byte_size": len(payload),
        "checksums": {
            "md5": hashlib.md5(payload).hexdigest(),
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
    }


def _encoded_storage_path(object_path: str) -> str:
    return "/".join(quote(part, safe="") for part in object_path.split("/"))
