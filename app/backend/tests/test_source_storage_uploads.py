from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import httpx

from app.cli import eamos_source_storage_upload
from app.services.source_storage_uploads import (
    SourceStorageUploadMode,
    SourceStorageUploadStatus,
    build_source_storage_upload_items,
    execute_source_storage_uploads,
)


class FakeS3Client:
    def __init__(self) -> None:
        self.uploads: list[dict[str, object]] = []

    def upload_file(
        self,
        filename: str,
        bucket: str,
        key: str,
        *,
        ExtraArgs: dict[str, str],
        Config: object | None = None,
    ) -> None:
        self.uploads.append(
            {
                "filename": filename,
                "bucket": bucket,
                "key": key,
                "extra_args": ExtraArgs,
                "config": Config,
            }
        )


def test_storage_upload_plan_requires_local_file_and_manifest(tmp_path: Path) -> None:
    root = tmp_path / "source_assets"
    asset = root / "ncbi_clinvar_vcf" / "clinvar.vcf.gz"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"vcf")
    asset.with_suffix(asset.suffix + ".manifest.json").write_text(
        json.dumps({"md5": "a" * 32, "sha256": "b" * 64}),
        encoding="utf-8",
    )

    items = build_source_storage_upload_items(
        source_ids=("ncbi_clinvar_vcf",),
        small_staging_root=root,
        bucket_file_size_limit=10,
    )

    by_asset = {item.asset_id: item for item in items}
    assert by_asset["clinvar_grch38_vcf_gz"].status is SourceStorageUploadStatus.PLANNED
    assert by_asset["clinvar_grch38_vcf_gz"].object_path == (
        "ncbi_clinvar_vcf/clinvar_grch38_vcf_gz/" f"sha256-{'b' * 64}/clinvar.vcf.gz"
    )
    assert by_asset["clinvar_grch38_vcf_tbi"].status is (
        SourceStorageUploadStatus.MISSING_LOCAL_FILE
    )


def test_storage_upload_plan_blocks_bucket_limit(tmp_path: Path) -> None:
    root = tmp_path / "source_assets"
    asset = root / "repeatmasker_rmsk_bb" / "rmsk.txt.gz"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"too-large")
    asset.with_suffix(asset.suffix + ".manifest.json").write_text(
        json.dumps({"md5": "a" * 32, "sha256": "c" * 64}),
        encoding="utf-8",
    )

    [item] = build_source_storage_upload_items(
        source_ids=("repeatmasker_rmsk_bb",),
        small_staging_root=root,
        bucket_file_size_limit=4,
    )

    assert item.status is SourceStorageUploadStatus.EXCEEDS_BUCKET_LIMIT
    assert item.message == "asset exceeds current private bucket file-size limit"


def test_storage_upload_requires_credentials_without_network(tmp_path: Path) -> None:
    root = tmp_path / "source_assets"
    asset = root / "gencc_download" / "gencc-download.csv"
    asset.parent.mkdir(parents=True)
    asset.write_text("uuid,gene_symbol\n", encoding="utf-8")
    asset.with_suffix(asset.suffix + ".manifest.json").write_text(
        json.dumps({"md5": "a" * 32, "sha256": "d" * 64}),
        encoding="utf-8",
    )
    [item] = build_source_storage_upload_items(
        source_ids=("gencc_download",),
        small_staging_root=root,
    )

    result = execute_source_storage_uploads([item], upload=True)

    assert result.uploaded_count == 0
    assert result.blocked_count == 1
    assert result.items[0].status is SourceStorageUploadStatus.CREDENTIALS_MISSING


def test_storage_upload_s3_multipart_requires_credentials_without_network(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source_assets"
    asset = root / "gencc_download" / "gencc-download.csv"
    asset.parent.mkdir(parents=True)
    asset.write_text("uuid,gene_symbol\n", encoding="utf-8")
    asset.with_suffix(asset.suffix + ".manifest.json").write_text(
        json.dumps({"md5": "a" * 32, "sha256": "f" * 64}),
        encoding="utf-8",
    )
    [item] = build_source_storage_upload_items(
        source_ids=("gencc_download",),
        small_staging_root=root,
    )

    result = execute_source_storage_uploads(
        [item],
        upload=True,
        upload_mode=SourceStorageUploadMode.S3_MULTIPART,
    )

    assert result.uploaded_count == 0
    assert result.blocked_count == 1
    assert result.items[0].status is SourceStorageUploadStatus.CREDENTIALS_MISSING
    assert result.items[0].message == (
        "S3 multipart upload requires endpoint URL, access key id, and secret key"
    )


def test_storage_upload_posts_asset_and_manifest(tmp_path: Path) -> None:
    root = tmp_path / "source_assets"
    asset = root / "gencc_download" / "gencc-download.csv"
    asset.parent.mkdir(parents=True)
    asset.write_text("uuid,gene_symbol\n", encoding="utf-8")
    asset.with_suffix(asset.suffix + ".manifest.json").write_text(
        json.dumps({"md5": "a" * 32, "sha256": "e" * 64}),
        encoding="utf-8",
    )
    [item] = build_source_storage_upload_items(
        source_ids=("gencc_download",),
        small_staging_root=root,
    )
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"Key": "ok"})

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = execute_source_storage_uploads(
        [item],
        upload=True,
        supabase_url="https://project.supabase.co",
        service_role_key="service-role",
        client=client,
    )

    assert result.uploaded_count == 1
    assert result.items[0].status is SourceStorageUploadStatus.UPLOADED
    assert len(requests) == 2
    assert requests[0].url.path.endswith("/gencc-download.csv")
    assert requests[1].url.path.endswith("/gencc-download.csv.manifest.json")
    assert requests[0].headers["authorization"] == "Bearer service-role"
    assert requests[0].headers["content-type"] == "application/octet-stream"


def test_storage_upload_s3_multipart_uploads_asset_and_manifest(tmp_path: Path) -> None:
    root = tmp_path / "source_assets"
    asset = root / "gencc_download" / "gencc-download.csv"
    asset.parent.mkdir(parents=True)
    asset.write_text("uuid,gene_symbol\n", encoding="utf-8")
    asset.with_suffix(asset.suffix + ".manifest.json").write_text(
        json.dumps({"md5": "a" * 32, "sha256": "1" * 64}),
        encoding="utf-8",
    )
    [item] = build_source_storage_upload_items(
        source_ids=("gencc_download",),
        small_staging_root=root,
        bucket_id="eamos-source-assets",
    )
    s3_client = FakeS3Client()

    result = execute_source_storage_uploads(
        [item],
        upload=True,
        upload_mode=SourceStorageUploadMode.S3_MULTIPART,
        s3_client=s3_client,
    )

    assert result.uploaded_count == 1
    assert result.items[0].status is SourceStorageUploadStatus.UPLOADED
    assert len(s3_client.uploads) == 2
    assert s3_client.uploads[0]["bucket"] == "eamos-source-assets"
    assert s3_client.uploads[0]["key"].endswith("/gencc-download.csv")
    assert s3_client.uploads[1]["key"].endswith("/gencc-download.csv.manifest.json")
    assert s3_client.uploads[0]["extra_args"] == {
        "ContentType": "application/octet-stream",
        "CacheControl": "31536000",
    }
    assert "ACL" not in s3_client.uploads[0]["extra_args"]


def test_storage_upload_cli_plans_without_supabase_credentials(capsys) -> None:
    exit_code = eamos_source_storage_upload.main(["--source", "gencc_download", "--compact"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "eamos_source_storage_upload"
    assert output["upload_performed"] is False
    assert output["upload_mode"] == "rest"
    assert output["guardrails"]["public_bucket"] == "blocked"


def test_storage_upload_cli_reports_s3_multipart_mode(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        eamos_source_storage_upload,
        "Settings",
        lambda **_: SimpleNamespace(
            supabase_url=None,
            supabase_service_role_key=None,
            supabase_storage_s3_endpoint_url=None,
            supabase_storage_s3_region=None,
            supabase_storage_s3_access_key_id=None,
            supabase_storage_s3_secret_access_key=None,
        ),
    )

    exit_code = eamos_source_storage_upload.main(
        ["--source", "gencc_download", "--upload-mode", "s3_multipart", "--compact"]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["upload_performed"] is False
    assert output["upload_mode"] == "s3_multipart"
    assert output["s3_endpoint_configured"] is False
    assert output["s3_access_key_id_configured"] is False
    assert output["s3_secret_access_key_configured"] is False
