from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import md5, sha256
from pathlib import Path
from typing import Iterable

from app.core.paths import find_project_root
from app.data_sources.local_inventory import resolve_local_asset_path
from app.data_sources.registry import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry


class ProteinAssetStatus(str, Enum):
    READY = "ready"
    PRESENT_UNVERIFIED = "present_unverified"
    MISSING = "missing"
    NOT_FILE = "not_file"
    SIZE_MISMATCH = "size_mismatch"
    MD5_MISMATCH = "md5_mismatch"
    SHA256_MISMATCH = "sha256_mismatch"
    REGISTRY_ERROR = "registry_error"


@dataclass(frozen=True)
class ProteinAssetSpec:
    asset_id: str
    source_ids: tuple[str, ...]
    relative_path: str
    expected_size_bytes: int
    expected_md5: str
    expected_sha256: str
    role: str


@dataclass(frozen=True)
class ProteinAssetInspection:
    asset_id: str
    source_ids: tuple[str, ...]
    role: str
    path: Path
    status: ProteinAssetStatus
    expected_size_bytes: int
    actual_size_bytes: int | None
    expected_md5: str
    actual_md5: str | None
    expected_sha256: str
    actual_sha256: str | None
    checksum_verified: bool
    message: str

    @property
    def present(self) -> bool:
        return self.status not in {
            ProteinAssetStatus.MISSING,
            ProteinAssetStatus.NOT_FILE,
            ProteinAssetStatus.REGISTRY_ERROR,
        }

    @property
    def ready(self) -> bool:
        return self.status is ProteinAssetStatus.READY


PROTEIN_ANNOTATION_SOURCE_IDS: tuple[str, ...] = (
    "uniprotkb_reviewed_swissprot",
    "interpro_pfam_protein_matches",
    "interproscan_standalone",
    "hmmer_pfam_a",
)

PROTEIN_ANNOTATION_ASSETS: tuple[ProteinAssetSpec, ...] = (
    ProteinAssetSpec(
        asset_id="uniprot_sprot_dat_gz",
        source_ids=("uniprotkb_reviewed_swissprot",),
        relative_path="app/backend/data/bio_assets/protein_annotation/downloads/uniprot_sprot.dat.gz",
        expected_size_bytes=692_563_345,
        expected_md5="d6bd6e9435cd819b64cd888068530a45",
        expected_sha256="bb3815e7b6445566ad9c8479f659033aa2115ed3cf2b06e61ae37c1dabc60438",
        role="reviewed_swissprot_feature_source",
    ),
    ProteinAssetSpec(
        asset_id="pfam_a_hmm_gz",
        source_ids=("interpro_pfam_protein_matches", "hmmer_pfam_a"),
        relative_path="app/backend/data/bio_assets/protein_annotation/downloads/Pfam-A.hmm.gz",
        expected_size_bytes=384_357_362,
        expected_md5="dc814cc181ece09102c09c4e6c19f2fd",
        expected_sha256="d3d30c8e6801bfedecf783408ecc98916f8f1dda8974c6e51036fcbdd765f591",
        role="pfam_hmm_profile_database",
    ),
    ProteinAssetSpec(
        asset_id="pfam_a_hmm_dat_gz",
        source_ids=("interpro_pfam_protein_matches",),
        relative_path="app/backend/data/bio_assets/protein_annotation/downloads/Pfam-A.hmm.dat.gz",
        expected_size_bytes=718_721,
        expected_md5="41a8fb4c9391e814795587fcdc8baa33",
        expected_sha256="4da981816a630fd77171cc5d369716bbe16e58dae8be8047ac1118e0bd64ebe4",
        role="pfam_release_metadata_sidecar",
    ),
    ProteinAssetSpec(
        asset_id="hmmer_tar_gz",
        source_ids=("hmmer_pfam_a",),
        relative_path="app/backend/data/bio_assets/protein_annotation/downloads/hmmer.tar.gz",
        expected_size_bytes=19_669_667,
        expected_md5="b1ed21ceea33930222c84f8c4d9f4240",
        expected_sha256="ca70d94fd0cf271bd7063423aabb116d42de533117343a9b27a65c17ff06fbf3",
        role="hmmer_source_bundle",
    ),
    ProteinAssetSpec(
        asset_id="interproscan6_main_zip",
        source_ids=("interproscan_standalone",),
        relative_path="app/backend/data/bio_assets/protein_annotation/downloads/interproscan6-main.zip",
        expected_size_bytes=58_031_205,
        expected_md5="97d76552a7886ebe6ac944786fae4363",
        expected_sha256="80ed03963f9f313c1e717b53fae54f063938e30bfaf415801599df18cab670e5",
        role="interproscan_source_bundle",
    ),
)


def inspect_protein_annotation_assets(
    *,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    assets: Iterable[ProteinAssetSpec] = PROTEIN_ANNOTATION_ASSETS,
    verify_checksums: bool = False,
) -> tuple[ProteinAssetInspection, ...]:
    return tuple(
        inspect_protein_annotation_asset(
            asset,
            registry=registry,
            verify_checksums=verify_checksums,
        )
        for asset in assets
    )


def inspect_protein_annotation_asset(
    asset: ProteinAssetSpec,
    *,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    verify_checksums: bool = False,
) -> ProteinAssetInspection:
    try:
        path = _asset_path(asset, registry=registry)
    except Exception as exc:
        return ProteinAssetInspection(
            asset_id=asset.asset_id,
            source_ids=asset.source_ids,
            role=asset.role,
            path=Path(asset.relative_path),
            status=ProteinAssetStatus.REGISTRY_ERROR,
            expected_size_bytes=asset.expected_size_bytes,
            actual_size_bytes=None,
            expected_md5=asset.expected_md5,
            actual_md5=None,
            expected_sha256=asset.expected_sha256,
            actual_sha256=None,
            checksum_verified=False,
            message=f"protein asset registry/path error: {type(exc).__name__}",
        )

    if not path.exists():
        return _inspection(asset, path, ProteinAssetStatus.MISSING, "protein asset is missing")
    if not path.is_file():
        return _inspection(
            asset,
            path,
            ProteinAssetStatus.NOT_FILE,
            "protein asset path is not a file",
        )

    actual_size = path.stat().st_size
    if actual_size != asset.expected_size_bytes:
        return _inspection(
            asset,
            path,
            ProteinAssetStatus.SIZE_MISMATCH,
            "protein asset size does not match the staged manifest",
            actual_size_bytes=actual_size,
        )

    if not verify_checksums:
        return _inspection(
            asset,
            path,
            ProteinAssetStatus.PRESENT_UNVERIFIED,
            "protein asset is present with expected size; checksums were not computed",
            actual_size_bytes=actual_size,
        )

    actual_md5, actual_sha256 = _hash_file(path)
    if actual_md5.lower() != asset.expected_md5.lower():
        return _inspection(
            asset,
            path,
            ProteinAssetStatus.MD5_MISMATCH,
            "protein asset MD5 does not match the staged manifest",
            actual_size_bytes=actual_size,
            actual_md5=actual_md5,
            actual_sha256=actual_sha256,
            checksum_verified=True,
        )
    if actual_sha256.lower() != asset.expected_sha256.lower():
        return _inspection(
            asset,
            path,
            ProteinAssetStatus.SHA256_MISMATCH,
            "protein asset SHA256 does not match the staged manifest",
            actual_size_bytes=actual_size,
            actual_md5=actual_md5,
            actual_sha256=actual_sha256,
            checksum_verified=True,
        )

    return _inspection(
        asset,
        path,
        ProteinAssetStatus.READY,
        "protein asset size and checksums match the staged manifest",
        actual_size_bytes=actual_size,
        actual_md5=actual_md5,
        actual_sha256=actual_sha256,
        checksum_verified=True,
    )


def _asset_path(asset: ProteinAssetSpec, *, registry: DataSourceRegistry) -> Path:
    for source_id in asset.source_ids:
        record = registry.get(source_id)
        if record.current_local_path == asset.relative_path:
            return resolve_local_asset_path(record)
    path = Path(asset.relative_path)
    if path.is_absolute():
        return path
    return find_project_root(__file__) / path


def _inspection(
    asset: ProteinAssetSpec,
    path: Path,
    status: ProteinAssetStatus,
    message: str,
    *,
    actual_size_bytes: int | None = None,
    actual_md5: str | None = None,
    actual_sha256: str | None = None,
    checksum_verified: bool = False,
) -> ProteinAssetInspection:
    return ProteinAssetInspection(
        asset_id=asset.asset_id,
        source_ids=asset.source_ids,
        role=asset.role,
        path=path,
        status=status,
        expected_size_bytes=asset.expected_size_bytes,
        actual_size_bytes=actual_size_bytes,
        expected_md5=asset.expected_md5,
        actual_md5=actual_md5.lower() if actual_md5 else None,
        expected_sha256=asset.expected_sha256,
        actual_sha256=actual_sha256.lower() if actual_sha256 else None,
        checksum_verified=checksum_verified,
        message=message,
    )


def _hash_file(path: Path) -> tuple[str, str]:
    md5_digest = md5()
    sha256_digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            md5_digest.update(chunk)
            sha256_digest.update(chunk)
    return md5_digest.hexdigest(), sha256_digest.hexdigest()
