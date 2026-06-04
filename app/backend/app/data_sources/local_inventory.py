from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5
from pathlib import Path

from app.core.paths import find_project_root
from app.data_sources.registry import (
    DEFAULT_DATA_SOURCE_REGISTRY,
    DataSourceRecord,
    DataSourceRegistry,
)

LOCAL_HG38_2BIT_SOURCE_ID = "ucsc_hg38_2bit"


class LocalAssetInventoryError(RuntimeError):
    """Raised when registry metadata is not enough to prove a local asset."""


@dataclass(frozen=True)
class LocalAssetInventory:
    source_id: str
    source_url: str | None
    relative_path: str
    path: Path
    expected_size_bytes: int
    actual_size_bytes: int
    expected_md5: str
    actual_md5: str
    md5sum_path: Path
    md5sum_md5: str | None

    @property
    def size_matches(self) -> bool:
        return self.actual_size_bytes == self.expected_size_bytes

    @property
    def md5_matches(self) -> bool:
        return self.actual_md5.lower() == self.expected_md5.lower()

    @property
    def md5sum_matches(self) -> bool:
        return self.md5sum_md5 is not None and self.actual_md5.lower() == self.md5sum_md5.lower()


def inventory_local_hg38_2bit(
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
) -> LocalAssetInventory:
    return inventory_local_asset(registry.get(LOCAL_HG38_2BIT_SOURCE_ID))


def inventory_local_asset(record: DataSourceRecord) -> LocalAssetInventory:
    path = resolve_local_asset_path(record)
    expected_size = _required_int(record.actual_size_bytes_local, "actual_size_bytes_local")
    expected_md5 = _required_string(record.current_local_md5, "current_local_md5")
    relative_path = _required_string(record.current_local_path, "current_local_path")

    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise LocalAssetInventoryError(f"{record.source_id}: local path is not a file: {path}")

    md5sum_path = path.with_name("md5sum.txt")
    return LocalAssetInventory(
        source_id=record.source_id,
        source_url=record.source_url,
        relative_path=relative_path,
        path=path,
        expected_size_bytes=expected_size,
        actual_size_bytes=path.stat().st_size,
        expected_md5=expected_md5,
        actual_md5=compute_md5(path),
        md5sum_path=md5sum_path,
        md5sum_md5=read_md5sum_entry(md5sum_path, path.name),
    )


def resolve_local_asset_path(record: DataSourceRecord) -> Path:
    relative_path = _required_string(record.current_local_path, "current_local_path")
    path = Path(relative_path)
    if path.is_absolute():
        return path
    return _repo_root() / path


def read_md5sum_entry(md5sum_path: Path, filename: str) -> str | None:
    if not md5sum_path.exists():
        return None
    for line in md5sum_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == filename:
            return parts[0].lower()
    return None


def compute_md5(path: Path) -> str:
    digest = md5()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_root() -> Path:
    return find_project_root(__file__)


def _required_string(value: str | None, field_name: str) -> str:
    if not value:
        raise LocalAssetInventoryError(f"{field_name} is required")
    return value


def _required_int(value: int | None, field_name: str) -> int:
    if value is None or value <= 0:
        raise LocalAssetInventoryError(f"{field_name} is required")
    return value
