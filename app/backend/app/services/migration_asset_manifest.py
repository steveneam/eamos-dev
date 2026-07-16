from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

_MANIFEST_LINE = re.compile(r"^([0-9a-f]{64})  ([0-9]+)  (.+)$")
_SHA256_SEGMENT = re.compile(r"(?:^|/)sha256-([0-9a-f]{64})(?:/|$)")
_SHA256_VALUE = re.compile(r"^[0-9a-f]{64}$")
_SMALL_OBJECT_HASH_LIMIT = 1024 * 1024
_SOURCE_OVERRIDE_SCHEMA_VERSION = "eamos.migration_source_overrides.v1"


class MigrationAssetManifestError(ValueError):
    pass


@dataclass(frozen=True)
class AssetManifestRow:
    sha256: str
    byte_size: int
    relpath: str

    def render(self) -> str:
        return f"{self.sha256}  {self.byte_size}  {self.relpath}"


@dataclass(frozen=True)
class SourceChecksumOverride:
    object_path: str
    byte_size: int
    sha256: str


@dataclass(frozen=True)
class SourceManifestIssue:
    code: str
    object_path: str


@dataclass(frozen=True)
class SourceBucketManifest:
    rows: tuple[AssetManifestRow, ...]
    issues: tuple[SourceManifestIssue, ...]
    object_count: int
    object_bytes: int
    small_object_bytes_downloaded: int


@dataclass(frozen=True)
class ContentComparison:
    matched_count: int
    render_only: tuple[AssetManifestRow, ...]
    source_identity_count: int
    source_only_identity_count: int


def load_source_checksum_overrides(path: Path) -> dict[str, SourceChecksumOverride]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationAssetManifestError("checksum override file is unreadable") from exc
    if not isinstance(payload, dict):
        raise MigrationAssetManifestError("checksum override file must be an object")
    if payload.get("schema_version") != _SOURCE_OVERRIDE_SCHEMA_VERSION:
        raise MigrationAssetManifestError("checksum override schema version is unsupported")
    if not isinstance(payload.get("objects"), list):
        raise MigrationAssetManifestError("checksum override file requires an objects array")

    overrides: dict[str, SourceChecksumOverride] = {}
    for raw in payload["objects"]:
        if not isinstance(raw, dict):
            raise MigrationAssetManifestError("checksum override entries must be objects")
        object_path = _required_text(raw, "object_path")
        checksum = _required_sha256(raw, "sha256")
        byte_size = _required_size(raw, "byte_size")
        _required_text(raw, "reason")
        _required_text(raw, "evidence")
        if object_path in overrides:
            raise MigrationAssetManifestError("checksum override object paths must be unique")
        overrides[object_path] = SourceChecksumOverride(
            object_path=object_path,
            byte_size=byte_size,
            sha256=checksum,
        )
    return overrides


def build_source_bucket_manifest(
    client: Any,
    *,
    bucket_id: str,
    overrides: Mapping[str, SourceChecksumOverride] | None = None,
) -> SourceBucketManifest:
    """Build a checksum manifest with S3 List/Head/Get operations only.

    Large source blobs are never downloaded. Their SHA-256 comes from an
    adjacent checksum sidecar, a content-addressed object path, or an explicit
    reviewed override for a legacy object. Objects up to one MiB are hashed
    directly so sidecars and checksum files are independently covered.
    """

    resolved_overrides = dict(overrides or {})
    objects = _list_objects(client, bucket_id=bucket_id)
    object_sizes = {key: size for key, size in objects}
    issues: list[SourceManifestIssue] = []
    rows: list[AssetManifestRow] = []
    downloaded_cache: dict[str, bytes] = {}
    small_object_bytes_downloaded = 0

    for object_path, listed_size in objects:
        try:
            head = client.head_object(Bucket=bucket_id, Key=object_path)
            head_size = int(head.get("ContentLength"))
        except Exception:
            issues.append(SourceManifestIssue("head_failed", object_path))
            continue
        if head_size != listed_size:
            issues.append(SourceManifestIssue("list_head_size_mismatch", object_path))
            continue

        candidate_checksums: list[str] = []
        expected_sizes: list[int] = [listed_size]
        embedded_checksum = (
            None
            if object_path.endswith(".manifest.json")
            else _checksum_from_object_path(object_path)
        )
        if embedded_checksum:
            candidate_checksums.append(embedded_checksum)

        sidecar_path = f"{object_path}.manifest.json"
        if sidecar_path in object_sizes:
            sidecar_was_cached = sidecar_path in downloaded_cache
            try:
                sidecar_content = _get_object_bytes(
                    client,
                    bucket_id=bucket_id,
                    object_path=sidecar_path,
                    cache=downloaded_cache,
                )
                sidecar = json.loads(sidecar_content)
            except Exception:
                issues.append(SourceManifestIssue("sidecar_unreadable", object_path))
                continue
            if not sidecar_was_cached:
                small_object_bytes_downloaded += len(sidecar_content)
            sidecar_checksum = _checksum_from_sidecar(sidecar)
            sidecar_size = _size_from_sidecar(sidecar)
            if sidecar_checksum:
                candidate_checksums.append(sidecar_checksum)
            if sidecar_size is not None:
                expected_sizes.append(sidecar_size)

        override = resolved_overrides.get(object_path)
        if override:
            candidate_checksums.append(override.sha256)
            expected_sizes.append(override.byte_size)

        if listed_size <= _SMALL_OBJECT_HASH_LIMIT:
            object_was_cached = object_path in downloaded_cache
            try:
                content = _get_object_bytes(
                    client,
                    bucket_id=bucket_id,
                    object_path=object_path,
                    cache=downloaded_cache,
                )
            except Exception:
                issues.append(SourceManifestIssue("small_object_get_failed", object_path))
                continue
            if not object_was_cached:
                small_object_bytes_downloaded += len(content)
            if len(content) != listed_size:
                issues.append(SourceManifestIssue("downloaded_size_mismatch", object_path))
                continue
            candidate_checksums.append(sha256(content).hexdigest())

        if not candidate_checksums:
            issues.append(SourceManifestIssue("sha256_unavailable", object_path))
            continue
        if len(set(candidate_checksums)) != 1:
            issues.append(SourceManifestIssue("sha256_authorities_disagree", object_path))
            continue
        checksum = candidate_checksums[0]

        if len(set(expected_sizes)) != 1:
            issues.append(SourceManifestIssue("size_authorities_disagree", object_path))
            continue
        rows.append(
            AssetManifestRow(
                sha256=checksum,
                byte_size=listed_size,
                relpath=object_path,
            )
        )

    for object_path in sorted(set(resolved_overrides) - set(object_sizes)):
        issues.append(SourceManifestIssue("override_object_missing", object_path))

    return SourceBucketManifest(
        rows=tuple(sorted(rows, key=lambda row: row.relpath)),
        issues=tuple(sorted(issues, key=lambda issue: (issue.object_path, issue.code))),
        object_count=len(objects),
        object_bytes=sum(size for _, size in objects),
        small_object_bytes_downloaded=small_object_bytes_downloaded,
    )


def build_tree_manifest(root: Path) -> tuple[AssetManifestRow, ...]:
    if not root.is_dir():
        raise MigrationAssetManifestError("tree manifest root is not a directory")
    rows: list[AssetManifestRow] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink() or not path.is_file():
            continue
        relpath = path.relative_to(root).as_posix()
        if "\n" in relpath:
            raise MigrationAssetManifestError("manifest paths cannot contain newlines")
        rows.append(
            AssetManifestRow(
                sha256=_hash_file(path),
                byte_size=path.stat().st_size,
                relpath=relpath,
            )
        )
    return tuple(rows)


def format_asset_manifest(rows: Iterable[AssetManifestRow]) -> str:
    rendered = [row.render() for row in sorted(rows, key=lambda row: row.relpath)]
    return "\n".join(rendered) + ("\n" if rendered else "")


def parse_asset_manifest(text: str) -> tuple[AssetManifestRow, ...]:
    rows: list[AssetManifestRow] = []
    seen_paths: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = _MANIFEST_LINE.fullmatch(line)
        if not match:
            raise MigrationAssetManifestError(f"invalid asset manifest line {line_number}")
        checksum, raw_size, relpath = match.groups()
        if relpath in seen_paths:
            raise MigrationAssetManifestError(
                f"duplicate asset manifest path on line {line_number}"
            )
        seen_paths.add(relpath)
        rows.append(
            AssetManifestRow(
                sha256=checksum,
                byte_size=int(raw_size),
                relpath=relpath,
            )
        )
    return tuple(rows)


def compare_manifest_content(
    source_rows: Iterable[AssetManifestRow],
    render_rows: Iterable[AssetManifestRow],
) -> ContentComparison:
    source_identities = {(row.sha256, row.byte_size) for row in source_rows}
    render_rows_tuple = tuple(render_rows)
    render_identities = {(row.sha256, row.byte_size) for row in render_rows_tuple}
    render_only = tuple(
        sorted(
            (
                row
                for row in render_rows_tuple
                if (row.sha256, row.byte_size) not in source_identities
            ),
            key=lambda row: row.relpath,
        )
    )
    return ContentComparison(
        matched_count=len(render_rows_tuple) - len(render_only),
        render_only=render_only,
        source_identity_count=len(source_identities),
        source_only_identity_count=len(source_identities - render_identities),
    )


def _list_objects(client: Any, *, bucket_id: str) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    continuation_token: str | None = None
    while True:
        kwargs: dict[str, object] = {"Bucket": bucket_id, "MaxKeys": 1000}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        response = client.list_objects_v2(**kwargs)
        for raw in response.get("Contents", []):
            key = raw.get("Key")
            size = raw.get("Size")
            if not isinstance(key, str) or not key or "\n" in key:
                raise MigrationAssetManifestError(
                    "bucket inventory contains an invalid object path"
                )
            if not isinstance(size, int) or size < 0:
                raise MigrationAssetManifestError(
                    "bucket inventory contains an invalid object size"
                )
            rows.append((key, size))
        if not response.get("IsTruncated"):
            break
        continuation_token = response.get("NextContinuationToken")
        if not isinstance(continuation_token, str) or not continuation_token:
            raise MigrationAssetManifestError(
                "truncated bucket inventory lacks a continuation token"
            )
    return sorted(rows)


def _get_object_bytes(
    client: Any,
    *,
    bucket_id: str,
    object_path: str,
    cache: dict[str, bytes],
) -> bytes:
    if object_path in cache:
        return cache[object_path]
    response = client.get_object(Bucket=bucket_id, Key=object_path)
    body = response.get("Body")
    content = body.read() if hasattr(body, "read") else body
    if hasattr(body, "close"):
        body.close()
    if not isinstance(content, bytes):
        raise MigrationAssetManifestError("storage object body is not bytes")
    cache[object_path] = content
    return content


def _checksum_from_object_path(object_path: str) -> str | None:
    match = _SHA256_SEGMENT.search(object_path)
    return match.group(1) if match else None


def _checksum_from_sidecar(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    direct = payload.get("sha256")
    if isinstance(direct, str) and _SHA256_VALUE.fullmatch(direct.lower()):
        return direct.lower()
    checksums = payload.get("checksums")
    if isinstance(checksums, dict):
        nested = checksums.get("sha256")
        if isinstance(nested, str) and _SHA256_VALUE.fullmatch(nested.lower()):
            return nested.lower()
    return None


def _size_from_sidecar(payload: object) -> int | None:
    if not isinstance(payload, dict):
        return None
    for key in ("byte_size", "size_bytes", "content_length"):
        value = payload.get(key)
        if isinstance(value, int) and value >= 0:
            return value
    return None


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value or "\n" in value:
        raise MigrationAssetManifestError(f"checksum override {key} is invalid")
    return value


def _required_sha256(payload: Mapping[str, object], key: str) -> str:
    value = _required_text(payload, key).lower()
    if not _SHA256_VALUE.fullmatch(value):
        raise MigrationAssetManifestError(f"checksum override {key} is invalid")
    return value


def _required_size(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value <= 0:
        raise MigrationAssetManifestError(f"checksum override {key} is invalid")
    return value
