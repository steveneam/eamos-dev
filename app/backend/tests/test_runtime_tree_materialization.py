from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

import pytest

from app.cli import eamos_runtime_tree_materialize as runtime_tree_cli
from app.core.config import Settings
from app.services.runtime_tree_materialization import (
    RuntimeTreeMaterializationError,
    load_runtime_tree_manifest,
    materialize_runtime_tree,
)

FROZEN_MANIFEST = Path(__file__).resolve().parents[1] / "app" / "runtime-tree-manifest-syd2.json"
FROZEN_TREE_MANIFEST = (
    Path(__file__).resolve().parents[1] / "app" / "runtime-tree-manifest-syd2.txt"
)


class FakeS3Client:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects
        self.head_calls: list[str] = []
        self.download_calls: list[str] = []

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, int]:
        assert Bucket == "test-bucket"
        self.head_calls.append(Key)
        return {"ContentLength": len(self.objects[Key])}

    def download_fileobj(self, bucket: str, key: str, destination, **_kwargs) -> None:
        assert bucket == "test-bucket"
        self.download_calls.append(key)
        destination.write(self.objects[key])


def test_frozen_manifest_classifies_all_source_objects_and_exact_runtime_tree() -> None:
    manifest = load_runtime_tree_manifest(FROZEN_MANIFEST)

    assert manifest.item_count == 23
    assert manifest.total_bytes == 47_943_536_945
    assert manifest.source_object_count == 45
    assert manifest.source_total_bytes == 48_562_226_185
    assert len(manifest.excluded_source_objects) == 22
    assert sum(item.byte_size for item in manifest.excluded_source_objects) == 618_689_240
    assert manifest.reference_tree_manifest_sha256 == (
        "c907fa2aab78eb31a5ae30dcbc3e914ed89d90584d5aea845f360cdc25c20cbb"
    )
    assert Counter(item.landing_set for item in manifest.items) == {
        "A_seed_manifest": 7,
        "B_preserved_runtime": 10,
        "C_runtime_required": 6,
    }
    predictor_items = [
        item
        for item in manifest.items
        if item.source_id in {"google_deepmind_alphamissense_hg38", "hmmer_pfam_a"}
    ]
    assert len(predictor_items) == 9
    assert all(item.license_status == "commercial_allowed" for item in predictor_items)
    assert all(item.approval_status == "approved" for item in predictor_items)
    canonical_tree_manifest = "".join(
        f"{item.sha256}  {item.byte_size}  {item.destination_relpath.as_posix()}\n"
        for item in sorted(
            manifest.items,
            key=lambda item: item.destination_relpath.as_posix(),
        )
    )
    assert FROZEN_TREE_MANIFEST.read_text(encoding="utf-8") == canonical_tree_manifest
    assert sha256(canonical_tree_manifest.encode("utf-8")).hexdigest() == (
        manifest.reference_tree_manifest_sha256
    )


def test_empty_target_materializes_only_after_all_source_heads_pass(tmp_path: Path) -> None:
    objects = {"source/a": b"alpha", "source/b": b"beta"}
    manifest_path = _write_manifest(tmp_path, objects)
    target = tmp_path / "target"
    target.mkdir()
    client = FakeS3Client(objects)

    report = materialize_runtime_tree(
        _settings(),
        manifest_path=manifest_path,
        target_root=target,
        minimum_free_after_bytes=0,
        s3_client=client,
    )

    assert report["ready"] is True
    assert report["status"] == "ready"
    assert client.head_calls == ["source/a", "source/b"]
    assert client.download_calls == ["source/a", "source/b"]
    assert (target / "one" / "a.bin").read_bytes() == b"alpha"
    assert (target / "two" / "b.bin").read_bytes() == b"beta"
    assert (target / "one" / "a.bin").stat().st_mode & 0o777 == 0o600
    encoded = json.dumps(report)
    assert "source/a" not in encoded
    assert str(target) not in encoded


def test_nonempty_target_is_rejected_before_any_source_request(tmp_path: Path) -> None:
    objects = {"source/a": b"alpha"}
    manifest_path = _write_manifest(tmp_path, objects)
    target = tmp_path / "target"
    target.mkdir()
    (target / "unexpected").write_text("blocked", encoding="utf-8")
    client = FakeS3Client(objects)

    with pytest.raises(RuntimeTreeMaterializationError) as exc_info:
        materialize_runtime_tree(
            _settings(),
            manifest_path=manifest_path,
            target_root=target,
            minimum_free_after_bytes=0,
            s3_client=client,
        )

    assert exc_info.value.code == "target_root_not_empty"
    assert client.head_calls == []
    assert client.download_calls == []


def test_preflight_only_heads_every_source_and_writes_nothing(tmp_path: Path) -> None:
    objects = {"source/a": b"alpha", "source/b": b"beta"}
    manifest_path = _write_manifest(tmp_path, objects)
    target = tmp_path / "target"
    target.mkdir()
    client = FakeS3Client(objects)

    report = materialize_runtime_tree(
        _settings(),
        manifest_path=manifest_path,
        target_root=target,
        preflight_only=True,
        minimum_free_after_bytes=0,
        s3_client=client,
    )

    assert report["status"] == "preflight_ready"
    assert len(report["items"]) == 2
    assert report["items"][0]["license_status"] == "test"
    assert report["items"][0]["approval_status"] == "approved"
    assert report["items"][0]["launch_gate"] is None
    assert report["items"][0]["sha256_verified"] is False
    assert client.head_calls == ["source/a", "source/b"]
    assert client.download_calls == []
    assert list(target.iterdir()) == []


def test_source_head_mismatch_blocks_every_download(tmp_path: Path) -> None:
    objects = {"source/a": b"alpha", "source/b": b"beta"}
    manifest_path = _write_manifest(tmp_path, objects)
    target = tmp_path / "target"
    target.mkdir()
    client = FakeS3Client(objects)
    client.objects["source/b"] = b"wrong-size"

    with pytest.raises(RuntimeTreeMaterializationError) as exc_info:
        materialize_runtime_tree(
            _settings(),
            manifest_path=manifest_path,
            target_root=target,
            minimum_free_after_bytes=0,
            s3_client=client,
        )

    assert exc_info.value.code == "source_size_mismatch"
    assert client.download_calls == []
    assert list(target.iterdir()) == []


def test_download_checksum_mismatch_removes_temp_and_never_commits(tmp_path: Path) -> None:
    expected = {"source/a": b"alpha"}
    manifest_path = _write_manifest(tmp_path, expected)
    target = tmp_path / "target"
    target.mkdir()
    client = FakeS3Client({"source/a": b"omega"})

    with pytest.raises(RuntimeTreeMaterializationError) as exc_info:
        materialize_runtime_tree(
            _settings(),
            manifest_path=manifest_path,
            target_root=target,
            minimum_free_after_bytes=0,
            s3_client=client,
        )

    assert exc_info.value.code == "download_identity_mismatch"
    assert list(target.rglob("*.bin")) == []
    assert list(target.rglob("*.tmp")) == []


def test_atomic_commit_never_overwrites_a_racing_destination(tmp_path: Path) -> None:
    objects = {"source/a": b"alpha"}
    manifest_path = _write_manifest(tmp_path, objects)
    target = tmp_path / "target"
    target.mkdir()

    class RacingS3Client(FakeS3Client):
        def download_fileobj(self, bucket: str, key: str, destination, **kwargs) -> None:
            super().download_fileobj(bucket, key, destination, **kwargs)
            (Path(destination.name).parent / "a.bin").write_bytes(b"do-not-overwrite")

    with pytest.raises(RuntimeTreeMaterializationError) as exc_info:
        materialize_runtime_tree(
            _settings(),
            manifest_path=manifest_path,
            target_root=target,
            minimum_free_after_bytes=0,
            s3_client=RacingS3Client(objects),
        )

    assert exc_info.value.code == "destination_already_exists"
    assert (target / "one" / "a.bin").read_bytes() == b"do-not-overwrite"
    assert list(target.rglob("*.tmp")) == []


def test_resume_verifies_completed_file_then_fetches_only_missing(tmp_path: Path) -> None:
    objects = {"source/a": b"alpha", "source/b": b"beta"}
    manifest_path = _write_manifest(tmp_path, objects)
    target = tmp_path / "target"
    (target / "one").mkdir(parents=True)
    (target / "one" / "a.bin").write_bytes(b"alpha")
    client = FakeS3Client(objects)

    report = materialize_runtime_tree(
        _settings(),
        manifest_path=manifest_path,
        target_root=target,
        resume=True,
        minimum_free_after_bytes=0,
        s3_client=client,
    )

    assert report["ready"] is True
    assert client.download_calls == ["source/b"]
    statuses = {item["item_id"]: item["status"] for item in report["items"]}
    assert statuses == {"item-1": "verified_existing", "item-2": "ready"}


def test_resume_refuses_mismatched_or_unexpected_content(tmp_path: Path) -> None:
    objects = {"source/a": b"alpha"}
    manifest_path = _write_manifest(tmp_path, objects)
    target = tmp_path / "target"
    (target / "one").mkdir(parents=True)
    (target / "one" / "a.bin").write_bytes(b"wrong")

    with pytest.raises(RuntimeTreeMaterializationError) as exc_info:
        materialize_runtime_tree(
            _settings(),
            manifest_path=manifest_path,
            target_root=target,
            resume=True,
            minimum_free_after_bytes=0,
            s3_client=FakeS3Client(objects),
        )

    assert exc_info.value.code == "existing_file_mismatch"


def test_manifest_blocks_destination_traversal(tmp_path: Path) -> None:
    objects = {"source/a": b"alpha"}
    manifest_path = _write_manifest(tmp_path, objects)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["items"][0]["destination_relpath"] = "../escape.bin"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeTreeMaterializationError) as exc_info:
        load_runtime_tree_manifest(manifest_path)

    assert exc_info.value.code == "manifest_destination_path_invalid"


def test_cli_sanitizes_unexpected_errors(monkeypatch, capsys) -> None:
    secret_path = "/private/operator/credentials.env"

    def fail_materialization(*_args, **_kwargs):
        raise OSError(secret_path)

    monkeypatch.setattr(
        runtime_tree_cli,
        "materialize_runtime_tree",
        fail_materialization,
    )

    return_code = runtime_tree_cli.main(["--compact", "--require-ready"])
    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert return_code == 2
    assert report["ready"] is False
    assert report["status"] == "unexpected_error"
    assert report["details"] == {}
    assert secret_path not in captured.out
    assert captured.err == ""


def _settings() -> Settings:
    return Settings(jwt_secret="runtime-tree-test-secret-value")


def _write_manifest(tmp_path: Path, objects: dict[str, bytes]) -> Path:
    items = []
    for index, (object_path, content) in enumerate(objects.items(), start=1):
        items.append(
            {
                "item_id": f"item-{index}",
                "source_id": "test-source",
                "asset_id": f"asset-{index}",
                "role": "test-runtime-file",
                "landing_set": "test",
                "object_path": object_path,
                "destination_relpath": f"{'one' if index == 1 else 'two'}/{chr(96 + index)}.bin",
                "byte_size": len(content),
                "sha256": sha256(content).hexdigest(),
                "license_status": "test",
                "approval_status": "approved",
                "launch_gate": None,
            }
        )
    canonical = "".join(
        f"{item['sha256']}  {item['byte_size']}  {item['destination_relpath']}\n"
        for item in sorted(items, key=lambda item: item["destination_relpath"])
    )
    payload = {
        "schema_version": "eamos.runtime_tree_manifest.v1",
        "manifest_id": "test-runtime-tree",
        "bucket_id": "test-bucket",
        "reference_tree_manifest_sha256": sha256(canonical.encode("utf-8")).hexdigest(),
        "item_count": len(items),
        "total_bytes": sum(item["byte_size"] for item in items),
        "source_object_count": len(items),
        "source_total_bytes": sum(item["byte_size"] for item in items),
        "items": items,
        "excluded_source_objects": [],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
