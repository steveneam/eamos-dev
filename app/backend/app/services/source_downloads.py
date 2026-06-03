from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import md5, sha256
import json
import os
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

import httpx

from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY
from app.data_sources.registry import DataSourceRegistry
from app.data_sources.source_manifest import POST_REFERENCE_DAY1_SOURCE_IDS


class SourceDownloadStatus(str, Enum):
    PLANNED = "planned"
    SKIPPED_LARGE_ASSET = "skipped_large_asset"
    PARTIAL_DOWNLOAD = "partial_download"
    PRESENT = "present"
    DOWNLOADED = "downloaded"
    SIZE_MISMATCH = "size_mismatch"


@dataclass(frozen=True)
class SourceDownloadFileSpec:
    source_id: str
    asset_id: str
    url: str
    file_name: str
    large_asset: bool = False
    expected_size_bytes: int | None = None
    role: str = "source_asset"


@dataclass(frozen=True)
class SourceDownloadItem:
    source_id: str
    display_name: str
    asset_id: str
    url: str
    destination: Path
    large_asset: bool
    expected_size_bytes: int | None
    role: str
    download_allowed: bool
    status: SourceDownloadStatus
    actual_size_bytes: int | None = None
    md5: str | None = None
    sha256: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class SourceDownloadResult:
    items: tuple[SourceDownloadItem, ...]
    downloaded_count: int
    present_count: int
    skipped_large_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "items": [
                asdict(item) | {"destination": str(item.destination), "status": item.status.value}
                for item in self.items
            ],
            "downloaded_count": self.downloaded_count,
            "present_count": self.present_count,
            "skipped_large_count": self.skipped_large_count,
        }


DEFAULT_SMALL_STAGING_ROOT = Path(__file__).resolve().parents[2] / "data" / "source_assets"
DEFAULT_LARGE_STAGING_ROOT = (
    Path("C:/EamosDataStaging/source_assets")
    if os.name == "nt"
    else Path(__file__).resolve().parents[2] / "data" / "source_assets_large"
)


SOURCE_DOWNLOAD_FILE_SPECS: tuple[SourceDownloadFileSpec, ...] = (
    SourceDownloadFileSpec(
        source_id="ncbi_dbsnp_gcf_000001405_40",
        asset_id="dbsnp_grch38_vcf_gz",
        url="https://ftp.ncbi.nih.gov/snp/latest_release/VCF/GCF_000001405.40.gz",
        file_name="GCF_000001405.40.gz",
        large_asset=True,
        expected_size_bytes=29_552_227_779,
        role="dbsnp_bgzip_vcf",
    ),
    SourceDownloadFileSpec(
        source_id="ncbi_dbsnp_gcf_000001405_40",
        asset_id="dbsnp_grch38_vcf_tbi",
        url="https://ftp.ncbi.nih.gov/snp/latest_release/VCF/GCF_000001405.40.gz.tbi",
        file_name="GCF_000001405.40.gz.tbi",
        large_asset=True,
        expected_size_bytes=3_140_346,
        role="dbsnp_tabix_index",
    ),
    SourceDownloadFileSpec(
        source_id="ncbi_dbsnp_gcf_000001405_40",
        asset_id="dbsnp_grch38_vcf_md5",
        url="https://ftp.ncbi.nih.gov/snp/latest_release/VCF/GCF_000001405.40.gz.md5",
        file_name="GCF_000001405.40.gz.md5",
        large_asset=True,
        expected_size_bytes=54,
        role="upstream_checksum",
    ),
    SourceDownloadFileSpec(
        source_id="ncbi_clinvar_vcf",
        asset_id="clinvar_grch38_vcf_gz",
        url="https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz",
        file_name="clinvar.vcf.gz",
        expected_size_bytes=191_912_185,
        role="clinvar_bgzip_vcf",
    ),
    SourceDownloadFileSpec(
        source_id="ncbi_clinvar_vcf",
        asset_id="clinvar_grch38_vcf_tbi",
        url="https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz.tbi",
        file_name="clinvar.vcf.gz.tbi",
        expected_size_bytes=609_481,
        role="clinvar_tabix_index",
    ),
    SourceDownloadFileSpec(
        source_id="ncbi_clinvar_vcf",
        asset_id="clinvar_grch38_vcf_md5",
        url="https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz.md5",
        file_name="clinvar.vcf.gz.md5",
        expected_size_bytes=132,
        role="upstream_checksum",
    ),
    SourceDownloadFileSpec(
        source_id="repeatmasker_rmsk_bb",
        asset_id="ucsc_hg38_rmsk_txt_gz",
        url="https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/rmsk.txt.gz",
        file_name="rmsk.txt.gz",
        expected_size_bytes=155_633_856,
        role="repeatmasker_source_table",
    ),
    SourceDownloadFileSpec(
        source_id="ucsc_phylop100way_hg38",
        asset_id="ucsc_hg38_phylop100way_bw",
        url="https://hgdownload.soe.ucsc.edu/goldenPath/hg38/phyloP100way/hg38.phyloP100way.bw",
        file_name="hg38.phyloP100way.bw",
        large_asset=True,
        expected_size_bytes=9_870_053_206,
        role="phylop_bigwig",
    ),
    SourceDownloadFileSpec(
        source_id="ucsc_phylop100way_hg38",
        asset_id="ucsc_hg38_phylop100way_md5sum",
        url="https://hgdownload.soe.ucsc.edu/goldenPath/hg38/phyloP100way/md5sum.txt",
        file_name="md5sum.txt",
        large_asset=True,
        expected_size_bytes=156,
        role="upstream_checksum",
    ),
    SourceDownloadFileSpec(
        source_id="google_deepmind_alphamissense_hg38",
        asset_id="alphamissense_hg38_tsv_gz",
        url="https://zenodo.org/records/10813168/files/AlphaMissense_hg38.tsv.gz?download=1",
        file_name="AlphaMissense_hg38.tsv.gz",
        expected_size_bytes=None,
        role="alphamissense_bgzip_tsv",
    ),
    SourceDownloadFileSpec(
        source_id="ncbi_mane_grch38_v1_4_select_ensembl",
        asset_id="mane_grch38_v1_4_ensembl_gtf_gz",
        url=(
            "https://ftp.ncbi.nlm.nih.gov/refseq/MANE/MANE_human/release_1.4/"
            "MANE.GRCh38.v1.4.ensembl_genomic.gtf.gz"
        ),
        file_name="MANE.GRCh38.v1.4.ensembl_genomic.gtf.gz",
        expected_size_bytes=8_538_314,
        role="mane_gtf",
    ),
    SourceDownloadFileSpec(
        source_id="gencode_v45_annotation",
        asset_id="gencode_v45_annotation_gtf_gz",
        url=(
            "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_45/"
            "gencode.v45.annotation.gtf.gz"
        ),
        file_name="gencode.v45.annotation.gtf.gz",
        expected_size_bytes=49_770_653,
        role="gencode_gtf",
    ),
    SourceDownloadFileSpec(
        source_id="mondo_disease_ontology",
        asset_id="mondo_json",
        url="https://purl.obolibrary.org/obo/mondo.json",
        file_name="mondo.json",
        expected_size_bytes=103_231_823,
        role="mondo_json",
    ),
    SourceDownloadFileSpec(
        source_id="human_phenotype_ontology",
        asset_id="hpo_ontology_json",
        url="https://purl.obolibrary.org/obo/hp.json",
        file_name="hp.json",
        expected_size_bytes=22_063_007,
        role="hpo_ontology_terms",
    ),
    SourceDownloadFileSpec(
        source_id="human_phenotype_ontology",
        asset_id="hpo_phenotype_hpoa",
        url="https://purl.obolibrary.org/obo/hp/hpoa/phenotype.hpoa",
        file_name="phenotype.hpoa",
        expected_size_bytes=35_261_380,
        role="hpo_disease_phenotypes",
    ),
    SourceDownloadFileSpec(
        source_id="human_phenotype_ontology",
        asset_id="hpo_genes_to_phenotype",
        url="https://purl.obolibrary.org/obo/hp/hpoa/genes_to_phenotype.txt",
        file_name="genes_to_phenotype.txt",
        expected_size_bytes=20_533_481,
        role="hpo_gene_phenotypes",
    ),
    SourceDownloadFileSpec(
        source_id="human_phenotype_ontology",
        asset_id="hpo_phenotype_to_genes",
        url="https://purl.obolibrary.org/obo/hp/hpoa/phenotype_to_genes.txt",
        file_name="phenotype_to_genes.txt",
        expected_size_bytes=65_852_754,
        role="hpo_phenotype_gene_index",
    ),
    SourceDownloadFileSpec(
        source_id="human_phenotype_ontology",
        asset_id="hpo_genes_to_disease",
        url="https://purl.obolibrary.org/obo/hp/hpoa/genes_to_disease.txt",
        file_name="genes_to_disease.txt",
        expected_size_bytes=1_474_869,
        role="hpo_gene_disease_index",
    ),
    SourceDownloadFileSpec(
        source_id="clingen_gene_validity",
        asset_id="clingen_gene_validity_csv",
        url="https://search.clinicalgenome.org/kb/gene-validity/download",
        file_name="clingen_gene_validity.csv",
        expected_size_bytes=None,
        role="clingen_gene_validity_csv",
    ),
    SourceDownloadFileSpec(
        source_id="gencc_download",
        asset_id="gencc_submissions_csv",
        url="https://search.thegencc.org/download/action/submissions-export-csv",
        file_name="gencc-download.csv",
        expected_size_bytes=None,
        role="gencc_submissions_csv",
    ),
)


def build_source_download_items(
    *,
    source_ids: Iterable[str] = POST_REFERENCE_DAY1_SOURCE_IDS,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    small_staging_root: Path = DEFAULT_SMALL_STAGING_ROOT,
    large_staging_root: Path = DEFAULT_LARGE_STAGING_ROOT,
    include_large: bool = False,
) -> tuple[SourceDownloadItem, ...]:
    requested = set(source_ids)
    items: list[SourceDownloadItem] = []
    for spec in SOURCE_DOWNLOAD_FILE_SPECS:
        if spec.source_id not in requested:
            continue
        record = registry.get(spec.source_id)
        root = large_staging_root if spec.large_asset else small_staging_root
        destination = root / spec.source_id / spec.file_name
        download_allowed = bool(
            record.download_approved and (include_large or not spec.large_asset)
        )
        items.append(
            SourceDownloadItem(
                source_id=spec.source_id,
                display_name=record.display_name,
                asset_id=spec.asset_id,
                url=spec.url,
                destination=destination,
                large_asset=spec.large_asset,
                expected_size_bytes=spec.expected_size_bytes,
                role=spec.role,
                download_allowed=download_allowed,
                status=(
                    SourceDownloadStatus.PLANNED
                    if download_allowed
                    else SourceDownloadStatus.SKIPPED_LARGE_ASSET
                ),
                message=(
                    None
                    if download_allowed
                    else "large asset requires --include-large and download approval"
                ),
            )
        )
    return tuple(items)


def execute_source_downloads(
    items: Iterable[SourceDownloadItem],
    *,
    download: bool = False,
    force: bool = False,
    client: httpx.Client | None = None,
) -> SourceDownloadResult:
    owns_client = client is None
    if client is None:
        client = httpx.Client(
            follow_redirects=True,
            timeout=None,
            headers={"User-Agent": "Eamos-source-downloader/1.0"},
        )
    try:
        resolved = tuple(
            _execute_item(item, download=download, force=force, client=client) for item in items
        )
    finally:
        if owns_client:
            client.close()

    return SourceDownloadResult(
        items=resolved,
        downloaded_count=sum(
            1 for item in resolved if item.status is SourceDownloadStatus.DOWNLOADED
        ),
        present_count=sum(1 for item in resolved if item.status is SourceDownloadStatus.PRESENT),
        skipped_large_count=sum(
            1 for item in resolved if item.status is SourceDownloadStatus.SKIPPED_LARGE_ASSET
        ),
    )


def _execute_item(
    item: SourceDownloadItem,
    *,
    download: bool,
    force: bool,
    client: httpx.Client,
) -> SourceDownloadItem:
    if not item.download_allowed:
        return item
    if item.destination.is_file() and not force:
        return _item_from_existing_file(item)
    temp_path = item.destination.with_name(f".{item.destination.name}.part")
    if temp_path.is_file() and not download:
        return _replace_item(
            item,
            status=SourceDownloadStatus.PARTIAL_DOWNLOAD,
            actual_size_bytes=temp_path.stat().st_size,
            message="partial download present; use --download to resume",
        )
    if not download:
        return item

    item.destination.parent.mkdir(parents=True, exist_ok=True)
    hash_md5 = md5()
    hash_sha256 = sha256()
    resume_from = temp_path.stat().st_size if temp_path.is_file() else 0
    total = resume_from
    final_url = item.url
    headers = {"Range": f"bytes={resume_from}-"} if resume_from else None

    if resume_from:
        _hash_existing_part(temp_path, hash_md5=hash_md5, hash_sha256=hash_sha256)

    with client.stream("GET", item.url, headers=headers) as response:
        response.raise_for_status()
        final_url = _sanitize_url(str(response.url))
        if resume_from and response.status_code != 206:
            hash_md5 = md5()
            hash_sha256 = sha256()
            total = 0
            file_mode = "wb"
        else:
            file_mode = "ab" if resume_from else "wb"
        with temp_path.open(file_mode) as file:
            for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                file.write(chunk)
                total += len(chunk)
                hash_md5.update(chunk)
                hash_sha256.update(chunk)

    if item.expected_size_bytes is not None and total != item.expected_size_bytes:
        temp_path.unlink(missing_ok=True)
        return _replace_item(
            item,
            status=SourceDownloadStatus.SIZE_MISMATCH,
            actual_size_bytes=total,
            md5=hash_md5.hexdigest(),
            sha256=hash_sha256.hexdigest(),
            message=(
                f"downloaded size {total} did not match expected " f"{item.expected_size_bytes}"
            ),
        )

    temp_path.replace(item.destination)
    manifest_path = item.destination.with_suffix(item.destination.suffix + ".manifest.json")
    manifest_path.write_text(
        _manifest_json(
            item=item,
            final_url=final_url,
            actual_size_bytes=total,
            md5_value=hash_md5.hexdigest(),
            sha256_value=hash_sha256.hexdigest(),
        ),
        encoding="utf-8",
    )
    return _replace_item(
        item,
        status=SourceDownloadStatus.DOWNLOADED,
        actual_size_bytes=total,
        md5=hash_md5.hexdigest(),
        sha256=hash_sha256.hexdigest(),
        message="downloaded and checksum manifest written",
    )


def _hash_existing_part(
    path: Path,
    *,
    hash_md5: object,
    hash_sha256: object,
) -> None:
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hash_md5.update(chunk)
            hash_sha256.update(chunk)


def _item_from_existing_file(item: SourceDownloadItem) -> SourceDownloadItem:
    actual_size = item.destination.stat().st_size
    if item.expected_size_bytes is not None and actual_size != item.expected_size_bytes:
        return _replace_item(
            item,
            status=SourceDownloadStatus.SIZE_MISMATCH,
            actual_size_bytes=actual_size,
            message="existing file size does not match expected download size",
        )
    return _replace_item(
        item,
        status=SourceDownloadStatus.PRESENT,
        actual_size_bytes=actual_size,
        message="existing file present; use --force to re-download",
    )


def _replace_item(
    item: SourceDownloadItem,
    *,
    status: SourceDownloadStatus,
    actual_size_bytes: int | None = None,
    md5: str | None = None,
    sha256: str | None = None,
    message: str | None = None,
) -> SourceDownloadItem:
    return SourceDownloadItem(
        source_id=item.source_id,
        display_name=item.display_name,
        asset_id=item.asset_id,
        url=item.url,
        destination=item.destination,
        large_asset=item.large_asset,
        expected_size_bytes=item.expected_size_bytes,
        role=item.role,
        download_allowed=item.download_allowed,
        status=status,
        actual_size_bytes=actual_size_bytes,
        md5=md5,
        sha256=sha256,
        message=message,
    )


def _manifest_json(
    *,
    item: SourceDownloadItem,
    final_url: str,
    actual_size_bytes: int,
    md5_value: str,
    sha256_value: str,
) -> str:
    return json.dumps(
        {
            "asset_id": item.asset_id,
            "source_id": item.source_id,
            "source_url": item.url,
            "final_url_sanitized": final_url,
            "role": item.role,
            "actual_size_bytes": actual_size_bytes,
            "expected_size_bytes": item.expected_size_bytes,
            "md5": md5_value,
            "sha256": sha256_value,
        },
        indent=2,
        sort_keys=True,
    )


def _sanitize_url(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
