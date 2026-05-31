from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import csv
import gzip
import importlib.util
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY
from app.data_sources.registry import DataSourceRegistry
from app.data_sources.source_manifest import POST_REFERENCE_DAY1_SOURCE_IDS
from app.services.clinical_source_tables import (
    ClinicalTableProvenance,
    parse_clingen_gene_validity_csv,
    parse_gencc_download_csv,
    parse_hpo_terms_json,
    parse_mondo_json,
    parse_phenotype_hpoa,
)
from app.services.indexed_sources import RepeatMaskerIndexedTable
from app.services.source_downloads import (
    DEFAULT_LARGE_STAGING_ROOT,
    DEFAULT_SMALL_STAGING_ROOT,
    SourceDownloadItem,
    build_source_download_items,
)


class SourceReaderProofStatus(str, Enum):
    PROVEN = "proven"
    FORMAT_SMOKE_NATIVE_PENDING = "format_smoke_passed_native_reader_pending"
    PARTIAL_DOWNLOAD = "partial_download"
    MISSING_LOCAL_FILE = "missing_local_file"
    FAILED = "failed"


@dataclass(frozen=True)
class SourceReaderProofItem:
    source_id: str
    display_name: str
    status: SourceReaderProofStatus
    local_paths: tuple[Path, ...]
    format_smoke_passed: bool
    native_reader_required: str | None = None
    native_reader_available: bool | None = None
    message: str | None = None
    evidence: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {
            "status": self.status.value,
            "local_paths": [str(path) for path in self.local_paths],
            "evidence": dict(self.evidence or {}),
        }


@dataclass(frozen=True)
class SourceReaderProofResult:
    items: tuple[SourceReaderProofItem, ...]

    @property
    def proven_count(self) -> int:
        return sum(1 for item in self.items if item.status is SourceReaderProofStatus.PROVEN)

    @property
    def native_pending_count(self) -> int:
        return sum(
            1
            for item in self.items
            if item.status is SourceReaderProofStatus.FORMAT_SMOKE_NATIVE_PENDING
        )

    @property
    def partial_count(self) -> int:
        return sum(
            1 for item in self.items if item.status is SourceReaderProofStatus.PARTIAL_DOWNLOAD
        )

    @property
    def missing_count(self) -> int:
        return sum(
            1 for item in self.items if item.status is SourceReaderProofStatus.MISSING_LOCAL_FILE
        )

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.items if item.status is SourceReaderProofStatus.FAILED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "proven_count": self.proven_count,
            "native_pending_count": self.native_pending_count,
            "partial_count": self.partial_count,
            "missing_count": self.missing_count,
            "failed_count": self.failed_count,
        }


def execute_source_reader_proofs(
    *,
    source_ids: Iterable[str] = POST_REFERENCE_DAY1_SOURCE_IDS,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    small_staging_root: Path = DEFAULT_SMALL_STAGING_ROOT,
    large_staging_root: Path = DEFAULT_LARGE_STAGING_ROOT,
) -> SourceReaderProofResult:
    download_items = build_source_download_items(
        source_ids=source_ids,
        registry=registry,
        small_staging_root=small_staging_root,
        large_staging_root=large_staging_root,
        include_large=True,
    )
    by_source: dict[str, tuple[SourceDownloadItem, ...]] = {}
    for item in download_items:
        by_source.setdefault(item.source_id, ())
        by_source[item.source_id] = (*by_source[item.source_id], item)

    proof_items = tuple(
        _execute_source_proof(source_id, registry=registry, assets=by_source.get(source_id, ()))
        for source_id in source_ids
    )
    return SourceReaderProofResult(items=proof_items)


def _execute_source_proof(
    source_id: str,
    *,
    registry: DataSourceRegistry,
    assets: tuple[SourceDownloadItem, ...],
) -> SourceReaderProofItem:
    record = registry.get(source_id)
    paths = tuple(item.destination for item in assets)
    try:
        if source_id == "ncbi_dbsnp_gcf_000001405_40":
            return _prove_indexed_vcf(
                source_id=source_id,
                display_name=record.display_name,
                assets=assets,
                native_reader="pysam",
                id_prefix="rs",
            )
        if source_id == "ncbi_clinvar_vcf":
            return _prove_indexed_vcf(
                source_id=source_id,
                display_name=record.display_name,
                assets=assets,
                native_reader="pysam",
                id_prefix=None,
            )
        if source_id == "repeatmasker_rmsk_bb":
            return _prove_repeatmasker(record.display_name, assets)
        if source_id == "ucsc_phylop100way_hg38":
            return _prove_phylop(record.display_name, assets)
        if source_id == "ncbi_mane_grch38_v1_4_select_ensembl":
            return _prove_gtf(
                source_id=source_id,
                display_name=record.display_name,
                path=_asset_path(assets, "mane_grch38_v1_4_ensembl_gtf_gz"),
                require_text="MANE_Select",
            )
        if source_id == "gencode_v45_annotation":
            return _prove_gtf(
                source_id=source_id,
                display_name=record.display_name,
                path=_asset_path(assets, "gencode_v45_annotation_gtf_gz"),
            )
        if source_id == "mondo_disease_ontology":
            return _prove_mondo(record.display_name, assets)
        if source_id == "human_phenotype_ontology":
            return _prove_hpo(record.display_name, assets)
        if source_id == "clingen_gene_validity":
            return _prove_clingen(record.display_name, assets)
        if source_id == "gencc_download":
            return _prove_gencc(record.display_name, assets)
    except Exception as exc:  # noqa: BLE001 - proof reports must fail closed with context.
        return SourceReaderProofItem(
            source_id=source_id,
            display_name=record.display_name,
            status=SourceReaderProofStatus.FAILED,
            local_paths=paths,
            format_smoke_passed=False,
            message=f"{type(exc).__name__}: {exc}",
        )
    return SourceReaderProofItem(
        source_id=source_id,
        display_name=record.display_name,
        status=SourceReaderProofStatus.FAILED,
        local_paths=paths,
        format_smoke_passed=False,
        message="no reader proof implementation is registered for this source",
    )


def _prove_indexed_vcf(
    *,
    source_id: str,
    display_name: str,
    assets: tuple[SourceDownloadItem, ...],
    native_reader: str,
    id_prefix: str | None,
) -> SourceReaderProofItem:
    vcf_path = _first_existing_asset_path(assets, role_suffix="bgzip_vcf")
    paths = tuple(item.destination for item in assets)
    partial = vcf_path.with_name(f".{vcf_path.name}.part") if vcf_path is not None else None
    if vcf_path is None:
        if partial is not None and partial.is_file():
            return _partial_item(source_id, display_name, paths, partial)
        return _missing_item(source_id, display_name, paths, "indexed VCF is not staged")
    partial = vcf_path.with_name(f".{vcf_path.name}.part")
    if partial.is_file():
        return _partial_item(source_id, display_name, paths, partial)
    if not vcf_path.is_file():
        return _missing_item(source_id, display_name, paths, "indexed VCF is not staged")

    evidence = _vcf_gzip_smoke(vcf_path, id_prefix=id_prefix)
    native_available = _module_available(native_reader)
    if not native_available:
        return SourceReaderProofItem(
            source_id=source_id,
            display_name=display_name,
            status=SourceReaderProofStatus.FORMAT_SMOKE_NATIVE_PENDING,
            local_paths=paths,
            format_smoke_passed=True,
            native_reader_required=native_reader,
            native_reader_available=False,
            message=f"{native_reader} is not installed in this runtime",
            evidence=evidence,
        )
    index_path = _first_existing_asset_path(assets, role_suffix="tabix_index")
    if index_path is None or not index_path.is_file():
        return _missing_item(source_id, display_name, paths, "tabix index is not staged")
    native_evidence = _indexed_vcf_native_smoke(vcf_path, evidence=evidence)
    return SourceReaderProofItem(
        source_id=source_id,
        display_name=display_name,
        status=SourceReaderProofStatus.PROVEN,
        local_paths=paths,
        format_smoke_passed=True,
        native_reader_required=native_reader,
        native_reader_available=True,
        message="indexed VCF gzip smoke passed and native reader query returned a record",
        evidence=evidence | {"native_query": native_evidence},
    )


def _prove_repeatmasker(
    display_name: str,
    assets: tuple[SourceDownloadItem, ...],
) -> SourceReaderProofItem:
    source_id = "repeatmasker_rmsk_bb"
    path = _asset_path(assets, "ucsc_hg38_rmsk_txt_gz")
    paths = (path,)
    if not path.is_file():
        return _missing_item(
            source_id, display_name, paths, "RepeatMasker rmsk.txt.gz is not staged"
        )
    rows = tuple(_read_gzip_nonempty_lines(path, limit=256))
    table = RepeatMaskerIndexedTable.from_ucsc_rmsk_rows(rows)
    first = table.query("chr1", 10000, 10001)[0]
    return SourceReaderProofItem(
        source_id=source_id,
        display_name=display_name,
        status=SourceReaderProofStatus.PROVEN,
        local_paths=paths,
        format_smoke_passed=True,
        message="real UCSC rmsk.txt.gz rows parsed into the indexed interval table",
        evidence={
            "rows_sampled": len(rows),
            "first_interval": {
                "chrom": first.chrom,
                "start": first.start,
                "end": first.end,
                "name": first.name,
                "repeat_class": first.repeat_class,
            },
        },
    )


def _prove_phylop(
    display_name: str,
    assets: tuple[SourceDownloadItem, ...],
) -> SourceReaderProofItem:
    source_id = "ucsc_phylop100way_hg38"
    path = _asset_path(assets, "ucsc_hg38_phylop100way_bw")
    paths = tuple(item.destination for item in assets)
    partial = path.with_name(f".{path.name}.part")
    if partial.is_file():
        return _partial_item(source_id, display_name, paths, partial)
    if not path.is_file():
        return _missing_item(source_id, display_name, paths, "phyloP bigWig is not staged")
    native_available = _module_available("pyBigWig")
    if not native_available:
        return SourceReaderProofItem(
            source_id=source_id,
            display_name=display_name,
            status=SourceReaderProofStatus.FORMAT_SMOKE_NATIVE_PENDING,
            local_paths=paths,
            format_smoke_passed=False,
            native_reader_required="pyBigWig",
            native_reader_available=False,
            message="pyBigWig is not installed in this runtime",
            evidence={"byte_size": path.stat().st_size},
        )
    native_evidence = _bigwig_native_smoke(path)
    return SourceReaderProofItem(
        source_id=source_id,
        display_name=display_name,
        status=SourceReaderProofStatus.PROVEN,
        local_paths=paths,
        format_smoke_passed=True,
        native_reader_required="pyBigWig",
        native_reader_available=True,
        message="bigWig file is staged and native reader query returned values",
        evidence={"byte_size": path.stat().st_size, "native_query": native_evidence},
    )


def _prove_gtf(
    *,
    source_id: str,
    display_name: str,
    path: Path,
    require_text: str | None = None,
) -> SourceReaderProofItem:
    if not path.is_file():
        return _missing_item(source_id, display_name, (path,), "GTF gzip is not staged")
    evidence = _gtf_gzip_smoke(path, require_text=require_text)
    return SourceReaderProofItem(
        source_id=source_id,
        display_name=display_name,
        status=SourceReaderProofStatus.PROVEN,
        local_paths=(path,),
        format_smoke_passed=True,
        message="real GTF gzip rows match the expected 9-column GTF shape",
        evidence=evidence,
    )


def _prove_mondo(
    display_name: str,
    assets: tuple[SourceDownloadItem, ...],
) -> SourceReaderProofItem:
    source_id = "mondo_disease_ontology"
    path = _asset_path(assets, "mondo_json")
    if not path.is_file():
        return _missing_item(source_id, display_name, (path,), "MONDO JSON is not staged")
    records = parse_mondo_json(path, provenance=_provenance(source_id, path))
    return SourceReaderProofItem(
        source_id=source_id,
        display_name=display_name,
        status=SourceReaderProofStatus.PROVEN,
        local_paths=(path,),
        format_smoke_passed=True,
        message="real MONDO JSON parsed with the clinical source table parser",
        evidence={"record_count": len(records), "first_mondo_id": records[0].mondo_id},
    )


def _prove_hpo(
    display_name: str,
    assets: tuple[SourceDownloadItem, ...],
) -> SourceReaderProofItem:
    source_id = "human_phenotype_ontology"
    hp_json = _asset_path(assets, "hpo_ontology_json")
    hpoa = _asset_path(assets, "hpo_phenotype_hpoa")
    genes_to_phenotype = _asset_path(assets, "hpo_genes_to_phenotype")
    phenotype_to_genes = _asset_path(assets, "hpo_phenotype_to_genes")
    genes_to_disease = _asset_path(assets, "hpo_genes_to_disease")
    paths = (hp_json, hpoa, genes_to_phenotype, phenotype_to_genes, genes_to_disease)
    missing = [path for path in paths if not path.is_file()]
    if missing:
        return _missing_item(source_id, display_name, paths, "one or more HPO files are not staged")
    hpo_terms = parse_hpo_terms_json(hp_json)
    disease_rows = parse_phenotype_hpoa(
        hpoa,
        hpo_terms=hpo_terms,
        provenance=_provenance(source_id, hpoa),
    )
    gene_rows = _tabular_smoke(
        genes_to_phenotype,
        delimiter="\t",
        required_columns=("ncbi_gene_id", "gene_symbol", "hpo_id", "hpo_name"),
    )
    phenotype_rows = _tabular_smoke(
        phenotype_to_genes,
        delimiter="\t",
        required_columns=("hpo_id", "hpo_name", "ncbi_gene_id", "gene_symbol"),
    )
    disease_link_rows = _tabular_smoke(
        genes_to_disease,
        delimiter="\t",
        required_columns=("ncbi_gene_id", "gene_symbol", "association_type", "disease_id"),
    )
    return SourceReaderProofItem(
        source_id=source_id,
        display_name=display_name,
        status=SourceReaderProofStatus.PROVEN,
        local_paths=paths,
        format_smoke_passed=True,
        message="real HPO ontology and annotation tables parsed with real-source headers",
        evidence={
            "hpo_term_count": len(hpo_terms),
            "phenotype_hpoa_rows": len(disease_rows),
            "genes_to_phenotype_header": gene_rows["header"],
            "phenotype_to_genes_header": phenotype_rows["header"],
            "genes_to_disease_header": disease_link_rows["header"],
        },
    )


def _prove_clingen(
    display_name: str,
    assets: tuple[SourceDownloadItem, ...],
) -> SourceReaderProofItem:
    source_id = "clingen_gene_validity"
    path = _asset_path(assets, "clingen_gene_validity_csv")
    if not path.is_file():
        return _missing_item(source_id, display_name, (path,), "ClinGen CSV is not staged")
    rows = parse_clingen_gene_validity_csv(path, provenance=_provenance(source_id, path))
    return SourceReaderProofItem(
        source_id=source_id,
        display_name=display_name,
        status=SourceReaderProofStatus.PROVEN,
        local_paths=(path,),
        format_smoke_passed=True,
        message="real ClinGen CSV parsed after skipping export banner rows",
        evidence={"record_count": len(rows), "first_gene": rows[0].gene_symbol},
    )


def _prove_gencc(
    display_name: str,
    assets: tuple[SourceDownloadItem, ...],
) -> SourceReaderProofItem:
    source_id = "gencc_download"
    path = _asset_path(assets, "gencc_submissions_csv")
    if not path.is_file():
        return _missing_item(source_id, display_name, (path,), "GenCC CSV is not staged")
    rows = parse_gencc_download_csv(path, provenance=_provenance(source_id, path))
    return SourceReaderProofItem(
        source_id=source_id,
        display_name=display_name,
        status=SourceReaderProofStatus.PROVEN,
        local_paths=(path,),
        format_smoke_passed=True,
        message="real GenCC CSV parsed with the clinical source table parser",
        evidence={"record_count": len(rows), "first_gene": rows[0].gene_symbol},
    )


def _asset_path(assets: tuple[SourceDownloadItem, ...], asset_id: str) -> Path:
    for item in assets:
        if item.asset_id == asset_id:
            return item.destination
    return Path("__missing_asset_spec__") / asset_id


def _first_existing_asset_path(
    assets: tuple[SourceDownloadItem, ...],
    *,
    role_suffix: str,
) -> Path | None:
    for item in assets:
        if item.role.endswith(role_suffix):
            return item.destination
    return None


def _partial_item(
    source_id: str,
    display_name: str,
    paths: tuple[Path, ...],
    partial_path: Path,
) -> SourceReaderProofItem:
    return SourceReaderProofItem(
        source_id=source_id,
        display_name=display_name,
        status=SourceReaderProofStatus.PARTIAL_DOWNLOAD,
        local_paths=paths,
        format_smoke_passed=False,
        message="partial download is still in progress",
        evidence={
            "partial_path": str(partial_path),
            "partial_size_bytes": partial_path.stat().st_size,
        },
    )


def _missing_item(
    source_id: str,
    display_name: str,
    paths: tuple[Path, ...],
    message: str,
) -> SourceReaderProofItem:
    return SourceReaderProofItem(
        source_id=source_id,
        display_name=display_name,
        status=SourceReaderProofStatus.MISSING_LOCAL_FILE,
        local_paths=paths,
        format_smoke_passed=False,
        message=message,
    )


def _vcf_gzip_smoke(path: Path, *, id_prefix: str | None) -> dict[str, Any]:
    header: list[str] | None = None
    first_row: list[str] | None = None
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("##"):
                continue
            if line.startswith("#CHROM"):
                header = line.lstrip("#").split("\t")
                continue
            if header is not None:
                first_row = line.split("\t")
                break
    if header is None or first_row is None:
        raise ValueError("VCF gzip must include #CHROM and at least one variant row")
    row = dict(zip(header, first_row, strict=True))
    position = int(row["POS"])
    if position < 1 or not row["CHROM"] or not row["REF"] or not row["ALT"]:
        raise ValueError("VCF first row has invalid coordinates or alleles")
    if id_prefix is not None and not row["ID"].startswith(id_prefix):
        raise ValueError(f"VCF first row ID does not start with {id_prefix}")
    return {
        "header_columns": header[:8],
        "first_record": {
            "chrom": row["CHROM"],
            "position": position,
            "id": row["ID"],
            "ref": row["REF"],
            "alt": row["ALT"].split(",")[:3],
        },
    }


def _indexed_vcf_native_smoke(path: Path, *, evidence: Mapping[str, Any]) -> dict[str, Any]:
    import pysam

    first_record = dict(evidence.get("first_record") or {})
    chrom = str(first_record.get("chrom") or "")
    position = int(first_record.get("position") or 0)
    if not chrom or position < 1:
        raise ValueError("VCF smoke evidence did not include a valid first record")

    with pysam.VariantFile(str(path)) as vcf:
        records = list(vcf.fetch(chrom, position - 1, position))
    if not records:
        raise ValueError("native VCF reader query returned no records for the first variant")
    record = records[0]
    return {
        "reader": "pysam",
        "queried_chrom": chrom,
        "queried_position": position,
        "record_id": record.id,
        "record_position": int(record.pos),
        "record_ref": record.ref,
        "record_alt": list(record.alts or ())[:3],
    }


def _bigwig_native_smoke(path: Path) -> dict[str, Any]:
    import pyBigWig

    handle = pyBigWig.open(str(path))
    try:
        chroms = handle.chroms()
        if not chroms:
            raise ValueError("bigWig reader reported no chromosomes")
        chrom = "chr1" if "chr1" in chroms else next(iter(chroms))
        chrom_size = int(chroms[chrom])
        if chrom_size < 1:
            raise ValueError(f"bigWig chromosome {chrom} has invalid size")
        sampled_start: int | None = None
        sampled_value: float | None = None
        for candidate_start in (10_000, 100_000, 1_000_000, 10_000_000):
            if candidate_start + 1 > chrom_size:
                continue
            values = handle.values(chrom, candidate_start, candidate_start + 1)
            if values and values[0] is not None and math.isfinite(float(values[0])):
                sampled_start = candidate_start
                sampled_value = float(values[0])
                break
    finally:
        handle.close()
    if sampled_start is None or sampled_value is None:
        raise ValueError("native bigWig reader query did not return a finite value")
    return {
        "reader": "pyBigWig",
        "chrom_count": len(chroms),
        "queried_chrom": chrom,
        "queried_start_0_based": sampled_start,
        "values_sampled": 1,
        "first_value": sampled_value,
    }


def _gtf_gzip_smoke(path: Path, *, require_text: str | None = None) -> dict[str, Any]:
    first_record: dict[str, Any] | None = None
    required_text_seen = require_text is None
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()
            if not line:
                continue
            if require_text and require_text in line:
                required_text_seen = True
            if line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) != 9:
                raise ValueError("GTF row must have 9 tab-delimited fields")
            start = int(fields[3])
            end = int(fields[4])
            if start < 1 or end < start:
                raise ValueError("GTF row has invalid coordinates")
            if first_record is None:
                first_record = {
                    "line_number": line_number,
                    "chrom": fields[0],
                    "source": fields[1],
                    "feature": fields[2],
                    "start": start,
                    "end": end,
                    "strand": fields[6],
                }
            if first_record is not None and required_text_seen:
                break
    if first_record is None:
        raise ValueError("GTF gzip must contain at least one feature row")
    if not required_text_seen:
        raise ValueError(f"GTF gzip did not contain required text {require_text!r}")
    return {"first_record": first_record, "required_text_seen": required_text_seen}


def _tabular_smoke(
    path: Path,
    *,
    delimiter: str,
    required_columns: tuple[str, ...],
) -> dict[str, Any]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file:
        reader = csv.reader(file, delimiter=delimiter)
        for row in reader:
            if row and any(value.strip() for value in row):
                header = [value.strip() for value in row]
                break
        else:
            raise ValueError(f"{path} does not contain a header")
    normalized = {value.lower() for value in header}
    missing = [column for column in required_columns if column.lower() not in normalized]
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")
    return {"header": header}


def _read_gzip_nonempty_lines(path: Path, *, limit: int) -> Iterable[str]:
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as file:
        emitted = 0
        for raw_line in file:
            line = raw_line.strip()
            if not line:
                continue
            yield line
            emitted += 1
            if emitted >= limit:
                break


def _provenance(source_id: str, path: Path) -> ClinicalTableProvenance:
    return ClinicalTableProvenance(
        source_id=source_id,
        source_version=None,
        checksum_algorithm="sha256",
        checksum="reader-proof-not-checksum-validation",
        relative_path=str(path),
    )


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None
