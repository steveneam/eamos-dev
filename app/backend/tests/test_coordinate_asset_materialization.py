from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.services.coordinate_asset_materialization import (
    materialize_coordinate_resolver_assets,
)


def test_materialize_coordinate_assets_downloads_verified_objects(tmp_path: Path) -> None:
    assets = _asset_fixture(tmp_path)
    client = _storage_client(assets)
    settings = _settings(tmp_path, assets=assets)

    result = materialize_coordinate_resolver_assets(settings, http_client=client)

    assert result.ready is True
    assert {item.status for item in result.items} == {"ready"}
    assert all(item.downloaded for item in result.items)
    for asset in assets:
        assert asset["destination"].read_bytes() == asset["content"]


def test_materialize_coordinate_assets_skips_existing_verified_files(tmp_path: Path) -> None:
    assets = _asset_fixture(tmp_path)
    for asset in assets:
        asset["destination"].parent.mkdir(parents=True, exist_ok=True)
        asset["destination"].write_bytes(asset["content"])
    seen_asset_requests: list[str] = []
    client = _storage_client(assets, seen_asset_requests=seen_asset_requests)
    settings = _settings(tmp_path, assets=assets)

    result = materialize_coordinate_resolver_assets(settings, http_client=client)

    assert result.ready is True
    assert {item.status for item in result.items} == {"ready"}
    assert all(not item.downloaded for item in result.items)
    assert seen_asset_requests == []


def test_materialize_coordinate_assets_rejects_checksum_mismatch(tmp_path: Path) -> None:
    assets = _asset_fixture(tmp_path)
    broken = dict(assets[0])
    broken["content"] = b"wrong-bytes"
    broken_assets = (broken, *assets[1:])
    client = _storage_client(broken_assets, manifest_assets=assets)
    settings = _settings(tmp_path, assets=assets)

    result = materialize_coordinate_resolver_assets(settings, http_client=client)

    assert result.ready is False
    first = result.items[0]
    assert first.ready is False
    assert first.status == "size_mismatch"
    assert not assets[0]["destination"].exists()
    assert all(item.ready for item in result.items[1:])


def _settings(tmp_path: Path, *, assets: tuple[dict[str, object], ...]) -> Settings:
    return Settings(
        jwt_secret="test-secret",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role-test",
        coordinate_resolver_asset_materialization_enabled=True,
        coordinate_resolver_mane_gff_path=assets[0]["destination"],
        coordinate_resolver_refseq_gff_path=assets[1]["destination"],
        hg38_2bit_runtime_asset_path=assets[2]["destination"],
        coordinate_resolver_mane_gff_object_path=assets[0]["object_path"],
        coordinate_resolver_refseq_gff_object_path=assets[1]["object_path"],
        coordinate_resolver_hg38_2bit_object_path=assets[2]["object_path"],
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "reports",
    )


def _asset_fixture(tmp_path: Path) -> tuple[dict[str, object], ...]:
    return (
        {
            "object_path": "transcripts/mane_refseq_gff/MANE.test.gff.gz",
            "destination": tmp_path / "bio_assets" / "transcripts" / "MANE.test.gff.gz",
            "content": b"mane-content",
        },
        {
            "object_path": "transcripts/refseq_grch38_p14_gff/refseq.test.gff.gz",
            "destination": tmp_path / "bio_assets" / "transcripts" / "refseq.test.gff.gz",
            "content": b"refseq-content",
        },
        {
            "object_path": "genomes/ucsc_hg38_2bit/hg38.2bit",
            "destination": tmp_path / "bio_assets" / "genomes" / "hg38.2bit",
            "content": b"hg38-content",
        },
    )


def _storage_client(
    assets: tuple[dict[str, object], ...],
    *,
    manifest_assets: tuple[dict[str, object], ...] | None = None,
    seen_asset_requests: list[str] | None = None,
) -> httpx.Client:
    manifest_source = manifest_assets or assets
    payloads: dict[str, bytes] = {}
    for asset in assets:
        object_path = str(asset["object_path"])
        payloads[_encoded_storage_path(object_path)] = asset["content"]
    for asset in manifest_source:
        object_path = str(asset["object_path"])
        content = asset["content"]
        manifest = {
            "byte_size": len(content),
            "checksums": {
                "md5": hashlib.md5(content).hexdigest(),
                "sha256": hashlib.sha256(content).hexdigest(),
            },
            "storage": {
                "bucket_id": "eamos-source-assets",
                "object_path": object_path,
                "manifest_object_path": f"{object_path}.manifest.json",
            },
        }
        payloads[_encoded_storage_path(f"{object_path}.manifest.json")] = json.dumps(
            manifest
        ).encode("utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        prefix = "/storage/v1/object/eamos-source-assets/"
        assert path.startswith(prefix)
        encoded_path = path[len(prefix) :]
        payload = payloads.get(encoded_path)
        if payload is None:
            return httpx.Response(404)
        if not encoded_path.endswith(".manifest.json") and seen_asset_requests is not None:
            seen_asset_requests.append(encoded_path)
        return httpx.Response(200, content=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def _encoded_storage_path(object_path: str) -> str:
    return "/".join(quote(part, safe="") for part in object_path.split("/"))
