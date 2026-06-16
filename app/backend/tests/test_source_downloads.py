from __future__ import annotations

import json
from pathlib import Path

import httpx

from app.cli.eamos_source_download import main
from app.data_sources.source_manifest import POST_REFERENCE_DAY1_SOURCE_IDS
from app.services.source_downloads import (
    SourceDownloadItem,
    SourceDownloadStatus,
    build_source_download_items,
    execute_source_downloads,
)


def test_source_download_plan_covers_post_reference_sources_with_large_guard(
    tmp_path: Path,
) -> None:
    items = build_source_download_items(
        source_ids=POST_REFERENCE_DAY1_SOURCE_IDS,
        small_staging_root=tmp_path / "small",
        large_staging_root=tmp_path / "large",
        include_large=False,
    )

    assert {item.source_id for item in items} == set(POST_REFERENCE_DAY1_SOURCE_IDS)
    by_asset = {item.asset_id: item for item in items}
    assert by_asset["clinvar_grch38_vcf_gz"].download_allowed is True
    assert by_asset["dbsnp_grch38_vcf_gz"].download_allowed is False
    assert by_asset["dbsnp_grch38_vcf_gz"].status is SourceDownloadStatus.SKIPPED_LARGE_ASSET
    assert by_asset["ucsc_hg38_phylop100way_bw"].destination.is_relative_to(tmp_path / "large")

    large_items = build_source_download_items(
        source_ids=("ncbi_dbsnp_gcf_000001405_40",),
        small_staging_root=tmp_path / "small",
        large_staging_root=tmp_path / "large",
        include_large=True,
    )
    assert all(item.download_allowed for item in large_items)
    assert {item.asset_id for item in large_items} == {
        "dbsnp_grch38_vcf_gz",
        "dbsnp_grch38_vcf_tbi",
        "dbsnp_grch38_vcf_md5",
    }


def test_source_download_cli_plans_without_network(
    tmp_path: Path,
    capsys,
) -> None:
    exit_code = main(
        [
            "--source",
            "ncbi_clinvar_vcf",
            "--small-staging-root",
            str(tmp_path / "small"),
            "--large-staging-root",
            str(tmp_path / "large"),
            "--compact",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "eamos_source_download"
    assert output["status"] == "planned"
    assert output["download_performed"] is False
    assert output["guardrails"]["supabase_mutation"] == "not_used"
    assert len(output["result"]["items"]) == 3
    assert {item["status"] for item in output["result"]["items"]} == {"planned"}


def test_alphamissense_download_plan_uses_approved_runtime_path(
    tmp_path: Path,
) -> None:
    [item] = build_source_download_items(
        source_ids=("google_deepmind_alphamissense_hg38",),
        small_staging_root=tmp_path / "small",
        large_staging_root=tmp_path / "large",
    )

    assert item.source_id == "google_deepmind_alphamissense_hg38"
    assert item.asset_id == "alphamissense_hg38_tsv_gz"
    assert item.download_allowed is True
    assert item.large_asset is False
    assert item.destination == (
        tmp_path / "small" / "google_deepmind_alphamissense_hg38" / "AlphaMissense_hg38.tsv.gz"
    )


def test_source_download_execute_writes_manifest_with_sanitized_final_url(
    tmp_path: Path,
) -> None:
    payload = b"source-data"
    destination = tmp_path / "source.bin"
    item = SourceDownloadItem(
        source_id="test_source",
        display_name="Test Source",
        asset_id="test_asset",
        url="https://example.test/source.bin",
        destination=destination,
        large_asset=False,
        expected_size_bytes=len(payload),
        role="test_role",
        download_allowed=True,
        status=SourceDownloadStatus.PLANNED,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://example.test/source.bin"
        return httpx.Response(
            200,
            content=payload,
            request=request,
            headers={"Location": "https://example.test/source.bin?token=secret"},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    )
    result = execute_source_downloads((item,), download=True, client=client)

    assert result.downloaded_count == 1
    downloaded = result.items[0]
    assert downloaded.status is SourceDownloadStatus.DOWNLOADED
    assert destination.read_bytes() == payload
    manifest = json.loads(destination.with_suffix(".bin.manifest.json").read_text())
    assert manifest["source_id"] == "test_source"
    assert manifest["actual_size_bytes"] == len(payload)
    assert "token" not in manifest["final_url_sanitized"]


def test_source_download_default_client_uses_finite_streaming_timeout(
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class DummyClient:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

        def close(self) -> None:
            captured["closed"] = True

    item = SourceDownloadItem(
        source_id="test_source",
        display_name="Test Source",
        asset_id="test_asset",
        url="https://example.test/source.bin",
        destination=tmp_path / "source.bin",
        large_asset=False,
        expected_size_bytes=None,
        role="test_role",
        download_allowed=True,
        status=SourceDownloadStatus.PLANNED,
    )

    monkeypatch.setattr("app.services.source_downloads.httpx.Client", DummyClient)

    execute_source_downloads((item,), download=False)

    timeout = captured["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect is not None
    assert timeout.read is not None
    assert timeout.write is not None
    assert timeout.pool is not None
    assert captured["closed"] is True


def test_source_download_execute_resumes_existing_part_file(tmp_path: Path) -> None:
    destination = tmp_path / "source.bin"
    temp_path = destination.with_name(".source.bin.part")
    temp_path.write_bytes(b"abc")
    item = SourceDownloadItem(
        source_id="test_source",
        display_name="Test Source",
        asset_id="test_asset",
        url="https://example.test/source.bin",
        destination=destination,
        large_asset=False,
        expected_size_bytes=6,
        role="test_role",
        download_allowed=True,
        status=SourceDownloadStatus.PLANNED,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["range"] == "bytes=3-"
        return httpx.Response(
            206,
            content=b"def",
            request=request,
            headers={"Content-Range": "bytes 3-5/6"},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = execute_source_downloads((item,), download=True, client=client)

    assert result.downloaded_count == 1
    assert destination.read_bytes() == b"abcdef"
    assert result.items[0].actual_size_bytes == 6


def test_source_download_plan_reports_partial_download(tmp_path: Path) -> None:
    root = tmp_path / "source_assets"
    destination = root / "gencc_download" / "gencc-download.csv"
    destination.parent.mkdir(parents=True)
    destination.with_name(".gencc-download.csv.part").write_bytes(b"partial")
    [item] = build_source_download_items(
        source_ids=("gencc_download",),
        small_staging_root=root,
    )

    result = execute_source_downloads((item,), download=False)

    assert result.items[0].status is SourceDownloadStatus.PARTIAL_DOWNLOAD
    assert result.items[0].actual_size_bytes == len(b"partial")
