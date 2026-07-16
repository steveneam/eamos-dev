from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

import pytest

from app.services.migration_asset_manifest import (
    AssetManifestRow,
    MigrationAssetManifestError,
    SourceChecksumOverride,
    build_source_bucket_manifest,
    build_tree_manifest,
    compare_manifest_content,
    format_asset_manifest,
    load_source_checksum_overrides,
    parse_asset_manifest,
)


class _ReadOnlyS3Client:
    def __init__(self, objects: dict[str, bytes], reported_sizes: dict[str, int] | None = None):
        self.objects = objects
        self.reported_sizes = reported_sizes or {}
        self.calls: list[tuple[str, str]] = []

    def list_objects_v2(self, **_kwargs):
        self.calls.append(("list", ""))
        return {
            "Contents": [
                {"Key": key, "Size": self.reported_sizes.get(key, len(content))}
                for key, content in sorted(self.objects.items())
            ],
            "IsTruncated": False,
        }

    def head_object(self, *, Bucket: str, Key: str):  # noqa: N803
        assert Bucket == "private-assets"
        self.calls.append(("head", Key))
        return {"ContentLength": self.reported_sizes.get(Key, len(self.objects[Key]))}

    def get_object(self, *, Bucket: str, Key: str):  # noqa: N803
        assert Bucket == "private-assets"
        self.calls.append(("get", Key))
        return {"Body": BytesIO(self.objects[Key])}


def test_source_bucket_manifest_uses_only_read_operations_and_checksum_authorities() -> None:
    direct_checksum = "1" * 64
    nested_checksum = "2" * 64
    legacy_checksum = "3" * 64
    direct_key = f"source/asset/sha256-{direct_checksum}/large.bin"
    direct_sidecar_key = f"{direct_key}.manifest.json"
    nested_key = "genomes/hg38/hg38.2bit"
    nested_sidecar_key = f"{nested_key}.manifest.json"
    legacy_key = "legacy/pfam/md5-value/Pfam-A.hmm.gz"
    small_key = "source/checksum/md5sum.txt"
    objects = {
        direct_key: b"placeholder",
        direct_sidecar_key: json.dumps(
            {"byte_size": 5_000_000, "sha256": direct_checksum}
        ).encode(),
        nested_key: b"placeholder",
        nested_sidecar_key: json.dumps(
            {"byte_size": 6_000_000, "checksums": {"sha256": nested_checksum}}
        ).encode(),
        legacy_key: b"placeholder",
        small_key: b"checksum metadata\n",
    }
    sizes = {
        direct_key: 5_000_000,
        nested_key: 6_000_000,
        legacy_key: 7_000_000,
    }
    client = _ReadOnlyS3Client(objects, sizes)

    result = build_source_bucket_manifest(
        client,
        bucket_id="private-assets",
        overrides={
            legacy_key: SourceChecksumOverride(
                object_path=legacy_key,
                byte_size=7_000_000,
                sha256=legacy_checksum,
            )
        },
    )

    assert result.issues == ()
    by_path = {row.relpath: row for row in result.rows}
    assert by_path[direct_key].sha256 == direct_checksum
    assert by_path[nested_key].sha256 == nested_checksum
    assert by_path[legacy_key].sha256 == legacy_checksum
    assert by_path[small_key].sha256 == sha256(objects[small_key]).hexdigest()
    assert {operation for operation, _ in client.calls} == {"list", "head", "get"}
    assert ("get", direct_key) not in client.calls
    assert ("get", nested_key) not in client.calls
    assert ("get", legacy_key) not in client.calls


def test_source_bucket_manifest_fails_when_sidecar_and_content_address_disagree() -> None:
    object_path = f"source/asset/sha256-{'1' * 64}/large.bin"
    sidecar_path = f"{object_path}.manifest.json"
    client = _ReadOnlyS3Client(
        {
            object_path: b"placeholder",
            sidecar_path: json.dumps({"byte_size": 5_000_000, "sha256": "2" * 64}).encode(),
        },
        {object_path: 5_000_000},
    )

    result = build_source_bucket_manifest(client, bucket_id="private-assets")

    assert [(issue.code, issue.object_path) for issue in result.issues] == [
        ("sha256_authorities_disagree", object_path)
    ]


def test_source_bucket_manifest_checks_small_object_content_against_sidecar() -> None:
    object_path = "source/index/small.tbi"
    sidecar_path = f"{object_path}.manifest.json"
    client = _ReadOnlyS3Client(
        {
            object_path: b"actual-small-index",
            sidecar_path: json.dumps({"byte_size": 18, "sha256": "4" * 64}).encode(),
        }
    )

    result = build_source_bucket_manifest(client, bucket_id="private-assets")

    assert [(issue.code, issue.object_path) for issue in result.issues] == [
        ("sha256_authorities_disagree", object_path)
    ]


def test_source_checksum_overrides_require_version_and_review_metadata(tmp_path: Path) -> None:
    override_path = tmp_path / "overrides.json"
    override_path.write_text(
        json.dumps(
            {
                "schema_version": "unsupported",
                "objects": [
                    {
                        "object_path": "legacy.bin",
                        "byte_size": 10,
                        "sha256": "5" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(MigrationAssetManifestError, match="schema version"):
        load_source_checksum_overrides(override_path)

    override_path.write_text(
        json.dumps(
            {
                "schema_version": "eamos.migration_source_overrides.v1",
                "objects": [
                    {
                        "object_path": "legacy.bin",
                        "byte_size": 10,
                        "sha256": "5" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(MigrationAssetManifestError, match="reason"):
        load_source_checksum_overrides(override_path)


def test_content_comparison_flags_render_only_derivatives() -> None:
    shared = AssetManifestRow("1" * 64, 10, "bucket/shared.bin")
    source_only = AssetManifestRow("2" * 64, 20, "bucket/offline-input.bin")
    runtime_shared = AssetManifestRow("1" * 64, 10, "runtime/shared.bin")
    runtime_derived = AssetManifestRow("3" * 64, 30, "runtime/Pfam-A.hmm.h3f")

    comparison = compare_manifest_content(
        (shared, source_only),
        (runtime_shared, runtime_derived),
    )

    assert comparison.matched_count == 1
    assert comparison.render_only == (runtime_derived,)
    assert comparison.source_identity_count == 2
    assert comparison.source_only_identity_count == 1


def test_tree_manifest_is_deterministic_and_round_trips(tmp_path: Path) -> None:
    (tmp_path / "z.txt").write_text("zeta\n", encoding="utf-8")
    nested = tmp_path / "a"
    nested.mkdir()
    (nested / "b.bin").write_bytes(b"beta")
    (tmp_path / "link").symlink_to(tmp_path / "z.txt")

    first = build_tree_manifest(tmp_path)
    second = build_tree_manifest(tmp_path)
    rendered = format_asset_manifest(first)

    assert first == second
    assert [row.relpath for row in first] == ["a/b.bin", "z.txt"]
    assert parse_asset_manifest(rendered) == first
