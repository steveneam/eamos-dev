from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.core.paths import find_project_root, repo_relative_path
from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry

MONDO_SOURCE_ID = "mondo_disease_ontology"
HPO_SOURCE_ID = "human_phenotype_ontology"
CLINGEN_GENE_VALIDITY_SOURCE_ID = "clingen_gene_validity"
GENCC_SOURCE_ID = "gencc_download"
DEFAULT_CLINICAL_SOURCE_FIXTURE_DIR = (
    Path(__file__).resolve().parents[1] / "fixtures" / "source_tables"
)
DEFAULT_CLINICAL_SOURCE_ASSET_ROOT = Path(__file__).resolve().parents[2] / "data" / "source_assets"


class ClinicalSourceTableError(ValueError):
    """Structured error for malformed local clinical source table fixtures."""

    def __init__(
        self,
        code: str,
        message: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


@dataclass(frozen=True)
class ClinicalTableProvenance:
    source_id: str
    source_version: str | None
    checksum_algorithm: str
    checksum: str
    relative_path: str


@dataclass(frozen=True)
class ClinicalSourceFixturePaths:
    mondo_json: Path
    phenotype_hpoa: Path
    genes_to_phenotype: Path
    clingen_gene_validity_csv: Path
    gencc_download_csv: Path
    hpo_terms_tsv: Path | None = None
    hpo_terms_json: Path | None = None

    def __post_init__(self) -> None:
        if (self.hpo_terms_tsv is None) == (self.hpo_terms_json is None):
            raise ValueError("exactly one HPO term source must be configured")

    @classmethod
    def from_dir(cls, fixture_dir: Path) -> ClinicalSourceFixturePaths:
        return cls(
            mondo_json=fixture_dir / "mondo_tiny.json",
            phenotype_hpoa=fixture_dir / "phenotype_tiny.hpoa",
            genes_to_phenotype=fixture_dir / "genes_to_phenotype_tiny.txt",
            clingen_gene_validity_csv=fixture_dir / "clingen_gene_validity_tiny.csv",
            gencc_download_csv=fixture_dir / "gencc_download_tiny.csv",
            hpo_terms_tsv=fixture_dir / "hpo_terms_tiny.tsv",
        )

    @classmethod
    def from_source_asset_root(cls, source_asset_root: Path) -> ClinicalSourceFixturePaths:
        return cls(
            mondo_json=source_asset_root / MONDO_SOURCE_ID / "mondo.json",
            phenotype_hpoa=source_asset_root / HPO_SOURCE_ID / "phenotype.hpoa",
            genes_to_phenotype=source_asset_root / HPO_SOURCE_ID / "genes_to_phenotype.txt",
            clingen_gene_validity_csv=(
                source_asset_root / CLINGEN_GENE_VALIDITY_SOURCE_ID / "clingen_gene_validity.csv"
            ),
            gencc_download_csv=source_asset_root / GENCC_SOURCE_ID / "gencc-download.csv",
            hpo_terms_json=source_asset_root / HPO_SOURCE_ID / "hp.json",
        )


@dataclass(frozen=True)
class MondoDisease:
    mondo_id: str
    name: str
    xrefs: tuple[str, ...]
    definition: str | None
    provenance: ClinicalTableProvenance


@dataclass(frozen=True)
class HpoDiseasePhenotype:
    disease_id: str
    disease_name: str
    hpo_id: str
    hpo_label: str
    evidence: str | None
    frequency: str | None
    provenance: ClinicalTableProvenance


@dataclass(frozen=True)
class HpoGenePhenotype:
    gene_symbol: str
    gene_id: str | None
    hpo_id: str
    hpo_label: str
    provenance: ClinicalTableProvenance


@dataclass(frozen=True)
class HpoPhenotypeLink:
    disease_id: str
    disease_name: str
    gene_symbol: str
    hpo_id: str
    hpo_label: str
    disease_evidence: str | None
    disease_frequency: str | None
    provenance: tuple[ClinicalTableProvenance, ...]


@dataclass(frozen=True)
class ClinGenGeneValidityRecord:
    gene_symbol: str
    gene_hgnc_id: str | None
    disease_label: str
    disease_id: str
    mode_of_inheritance: str | None
    classification: str
    source_date: str
    report_url: str | None
    provenance: ClinicalTableProvenance


@dataclass(frozen=True)
class GenCcAssertionRecord:
    gene_symbol: str
    gene_curie: str | None
    disease_title: str
    disease_curie: str
    assertion: str
    submitter: str
    source_date: str
    report_url: str | None
    provenance: ClinicalTableProvenance


class ClinicalSourceTableStore:
    """Fixture-first parsers for small clinical source tables."""

    def __init__(
        self,
        fixture_dir: Path | None = None,
        paths: ClinicalSourceFixturePaths | None = None,
        registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
        source_version_overrides: Mapping[str, str] | None = None,
    ) -> None:
        if fixture_dir is not None and paths is not None:
            raise ValueError("fixture_dir and paths are mutually exclusive")
        self._fixture_dir = fixture_dir or DEFAULT_CLINICAL_SOURCE_FIXTURE_DIR
        self._paths = paths or ClinicalSourceFixturePaths.from_dir(self._fixture_dir)
        self._provenance_by_path = _build_provenance_by_path(
            self._paths,
            registry,
            source_version_overrides=source_version_overrides,
        )
        self._mondo_records = tuple(
            parse_mondo_json(
                self._paths.mondo_json,
                provenance=self._provenance_by_path[self._paths.mondo_json],
            )
        )
        self._hpo_terms = _parse_hpo_terms(self._paths)
        self._hpo_disease_records = tuple(
            parse_phenotype_hpoa(
                self._paths.phenotype_hpoa,
                hpo_terms=self._hpo_terms,
                provenance=self._provenance_by_path[self._paths.phenotype_hpoa],
            )
        )
        self._hpo_gene_records = tuple(
            parse_genes_to_phenotype(
                self._paths.genes_to_phenotype,
                provenance=self._provenance_by_path[self._paths.genes_to_phenotype],
            )
        )
        self._clingen_records = tuple(
            parse_clingen_gene_validity_csv(
                self._paths.clingen_gene_validity_csv,
                provenance=self._provenance_by_path[self._paths.clingen_gene_validity_csv],
            )
        )
        self._gencc_records = tuple(
            parse_gencc_download_csv(
                self._paths.gencc_download_csv,
                provenance=self._provenance_by_path[self._paths.gencc_download_csv],
            )
        )
        self._mondo_by_id = {record.mondo_id: record for record in self._mondo_records}
        self._mondo_by_xref = {
            xref.upper(): record for record in self._mondo_records for xref in record.xrefs
        }

    def provenance(self) -> tuple[ClinicalTableProvenance, ...]:
        return tuple(self._provenance_by_path.values())

    def mondo_records(self) -> tuple[MondoDisease, ...]:
        return self._mondo_records

    def hpo_terms(self) -> Mapping[str, str]:
        return dict(self._hpo_terms)

    def hpo_disease_records(self) -> tuple[HpoDiseasePhenotype, ...]:
        return self._hpo_disease_records

    def hpo_gene_records(self) -> tuple[HpoGenePhenotype, ...]:
        return self._hpo_gene_records

    def clingen_records(self) -> tuple[ClinGenGeneValidityRecord, ...]:
        return self._clingen_records

    def gencc_records(self) -> tuple[GenCcAssertionRecord, ...]:
        return self._gencc_records

    def mondo_by_id(self, mondo_id: str) -> MondoDisease | None:
        return self._mondo_by_id.get(_normalize_curie(mondo_id))

    def mondo_by_xref(self, xref: str) -> MondoDisease | None:
        return self._mondo_by_xref.get(_normalize_curie(xref).upper())

    def hpo_links(self, *, gene: str, disease_id: str) -> tuple[HpoPhenotypeLink, ...]:
        normalized_gene = gene.strip().upper()
        normalized_disease_id = _normalize_curie(disease_id)
        disease_rows = [
            row for row in self._hpo_disease_records if row.disease_id == normalized_disease_id
        ]
        gene_rows = [row for row in self._hpo_gene_records if row.gene_symbol == normalized_gene]
        gene_by_hpo = {row.hpo_id: row for row in gene_rows}
        return tuple(
            HpoPhenotypeLink(
                disease_id=row.disease_id,
                disease_name=row.disease_name,
                gene_symbol=gene_by_hpo[row.hpo_id].gene_symbol,
                hpo_id=row.hpo_id,
                hpo_label=row.hpo_label,
                disease_evidence=row.evidence,
                disease_frequency=row.frequency,
                provenance=(row.provenance, gene_by_hpo[row.hpo_id].provenance),
            )
            for row in disease_rows
            if row.hpo_id in gene_by_hpo
        )

    def clingen_validity(
        self,
        *,
        gene: str,
        disease_id: str | None = None,
    ) -> tuple[ClinGenGeneValidityRecord, ...]:
        normalized_gene = gene.strip().upper()
        normalized_disease_id = _normalize_curie(disease_id) if disease_id else None
        return tuple(
            record
            for record in self._clingen_records
            if record.gene_symbol == normalized_gene
            and (normalized_disease_id is None or record.disease_id == normalized_disease_id)
        )

    def gencc_assertions(
        self,
        *,
        gene: str,
        disease_id: str | None = None,
    ) -> tuple[GenCcAssertionRecord, ...]:
        normalized_gene = gene.strip().upper()
        normalized_disease_id = _normalize_curie(disease_id) if disease_id else None
        return tuple(
            record
            for record in self._gencc_records
            if record.gene_symbol == normalized_gene
            and (normalized_disease_id is None or record.disease_curie == normalized_disease_id)
        )


def parse_mondo_json(
    path: Path,
    *,
    provenance: ClinicalTableProvenance,
) -> tuple[MondoDisease, ...]:
    payload = _load_json(path)
    graphs = _required_list(payload.get("graphs"), "graphs", code="malformed_mondo_fixture")
    records: list[MondoDisease] = []
    for graph in graphs:
        nodes = _required_list(
            _required_mapping(graph, "graphs[]", code="malformed_mondo_fixture").get("nodes"),
            "graphs[].nodes",
            code="malformed_mondo_fixture",
        )
        for node in nodes:
            node_payload = _required_mapping(node, "graphs[].nodes[]", code="malformed_mondo_node")
            mondo_id = _mondo_id_from_iri(
                _required_string(node_payload.get("id"), "node.id", code="malformed_mondo_node")
            )
            if mondo_id is None:
                continue
            metadata = _optional_mapping(node_payload.get("meta"))
            definition = None
            xrefs: tuple[str, ...] = ()
            if metadata is not None:
                definition = _definition_from_metadata(metadata)
                xrefs = _xrefs_from_metadata(metadata)
            label = _row_text(node_payload.get("lbl"))
            if label is None and _is_deprecated(metadata):
                continue
            records.append(
                MondoDisease(
                    mondo_id=mondo_id,
                    name=_required_string(
                        label,
                        "node.lbl",
                        code="malformed_mondo_node",
                        details={"mondo_id": mondo_id},
                    ),
                    xrefs=xrefs,
                    definition=definition,
                    provenance=provenance,
                )
            )
    if not records:
        raise ClinicalSourceTableError(
            "empty_mondo_fixture",
            "MONDO fixture must contain at least one MONDO node",
            {"path": str(path)},
        )
    return tuple(records)


def parse_hpo_terms_tsv(path: Path) -> Mapping[str, str]:
    terms: dict[str, str] = {}
    for row_number, row in enumerate(_dict_rows(path, delimiter="\t"), start=2):
        hpo_id = _normalize_curie(
            _required_row_value(row, "id", code="malformed_hpo_terms_row", row_number=row_number)
        )
        label = _required_row_value(
            row,
            "label",
            code="malformed_hpo_terms_row",
            row_number=row_number,
        )
        terms[hpo_id] = label
    if not terms:
        raise ClinicalSourceTableError(
            "empty_hpo_terms_fixture",
            "HPO term fixture must contain at least one term",
            {"path": str(path)},
        )
    return terms


def parse_hpo_terms_json(path: Path) -> Mapping[str, str]:
    payload = _load_json(path)
    graphs = _required_list(payload.get("graphs"), "graphs", code="malformed_hpo_terms_json")
    terms: dict[str, str] = {}
    for graph in graphs:
        nodes = _required_list(
            _required_mapping(graph, "graphs[]", code="malformed_hpo_terms_json").get("nodes"),
            "graphs[].nodes",
            code="malformed_hpo_terms_json",
        )
        for node in nodes:
            node_payload = _required_mapping(node, "graphs[].nodes[]", code="malformed_hpo_node")
            raw_id = _required_string(node_payload.get("id"), "node.id", code="malformed_hpo_node")
            hpo_id = _hpo_id_from_iri(raw_id)
            if hpo_id is None:
                continue
            terms[hpo_id] = _required_string(
                node_payload.get("lbl"),
                "node.lbl",
                code="malformed_hpo_node",
                details={"hpo_id": hpo_id},
            )
    if not terms:
        raise ClinicalSourceTableError(
            "empty_hpo_terms_json",
            "HPO ontology JSON must contain at least one HP node",
            {"path": str(path)},
        )
    return terms


def parse_phenotype_hpoa(
    path: Path,
    *,
    hpo_terms: Mapping[str, str],
    provenance: ClinicalTableProvenance,
) -> tuple[HpoDiseasePhenotype, ...]:
    records: list[HpoDiseasePhenotype] = []
    for row_number, row in enumerate(_dict_rows(path, delimiter="\t"), start=2):
        qualifier = _row_value_any(row, ("Qualifier", "qualifier"))
        if qualifier and qualifier.upper() == "NOT":
            continue
        hpo_id = _normalize_curie(
            _required_any_row_value(
                row,
                ("HPO_ID", "hpo_id"),
                code="malformed_hpoa_row",
                row_number=row_number,
            )
        )
        hpo_label = hpo_terms.get(hpo_id)
        if hpo_label is None:
            raise ClinicalSourceTableError(
                "unknown_hpo_term",
                "HPOA row references an HPO ID absent from the term fixture",
                {"row": row_number, "hpo_id": hpo_id},
            )
        records.append(
            HpoDiseasePhenotype(
                disease_id=_normalize_curie(
                    _required_any_row_value(
                        row,
                        ("DatabaseID", "database_id"),
                        code="malformed_hpoa_row",
                        row_number=row_number,
                    )
                ),
                disease_name=_required_any_row_value(
                    row,
                    ("DiseaseName", "disease_name"),
                    code="malformed_hpoa_row",
                    row_number=row_number,
                ),
                hpo_id=hpo_id,
                hpo_label=hpo_label,
                evidence=_row_value_any(row, ("Evidence", "evidence")),
                frequency=_row_value_any(row, ("Frequency", "frequency")),
                provenance=provenance,
            )
        )
    if not records:
        raise ClinicalSourceTableError(
            "empty_hpoa_fixture",
            "HPOA fixture must contain at least one positive phenotype row",
            {"path": str(path)},
        )
    return tuple(records)


def parse_genes_to_phenotype(
    path: Path,
    *,
    provenance: ClinicalTableProvenance,
) -> tuple[HpoGenePhenotype, ...]:
    records: list[HpoGenePhenotype] = []
    for row_number, row in enumerate(_dict_rows(path, delimiter="\t"), start=2):
        records.append(
            HpoGenePhenotype(
                gene_symbol=_required_any_row_value(
                    row,
                    ("gene_symbol", "gene symbol", "Gene Symbol"),
                    code="malformed_hpo_gene_row",
                    row_number=row_number,
                ).upper(),
                gene_id=_row_value_any(row, ("ncbi_gene_id", "gene_id", "Gene ID")),
                hpo_id=_normalize_curie(
                    _required_any_row_value(
                        row,
                        ("hpo_id", "HPO_ID", "hpo id"),
                        code="malformed_hpo_gene_row",
                        row_number=row_number,
                    )
                ),
                hpo_label=_required_any_row_value(
                    row,
                    ("hpo_name", "hpo_label", "HPO term name"),
                    code="malformed_hpo_gene_row",
                    row_number=row_number,
                ),
                provenance=provenance,
            )
        )
    if not records:
        raise ClinicalSourceTableError(
            "empty_hpo_gene_fixture",
            "HPO gene-phenotype fixture must contain at least one row",
            {"path": str(path)},
        )
    return tuple(records)


def parse_clingen_gene_validity_csv(
    path: Path,
    *,
    provenance: ClinicalTableProvenance,
) -> tuple[ClinGenGeneValidityRecord, ...]:
    records: list[ClinGenGeneValidityRecord] = []
    for row_number, row in enumerate(
        _dict_rows(
            path,
            delimiter=",",
            header_contains=("GENE SYMBOL", "DISEASE LABEL", "CLASSIFICATION"),
        ),
        start=2,
    ):
        records.append(
            ClinGenGeneValidityRecord(
                gene_symbol=_required_any_row_value(
                    row,
                    ("GENE SYMBOL", "Gene Symbol", "gene_symbol"),
                    code="malformed_clingen_gene_validity_row",
                    row_number=row_number,
                ).upper(),
                gene_hgnc_id=_row_value_any(row, ("GENE ID (HGNC)", "HGNC ID", "gene_hgnc_id")),
                disease_label=_required_any_row_value(
                    row,
                    ("DISEASE LABEL", "Disease Label", "disease_label"),
                    code="malformed_clingen_gene_validity_row",
                    row_number=row_number,
                ),
                disease_id=_normalize_curie(
                    _required_any_row_value(
                        row,
                        ("DISEASE ID (MONDO)", "Disease ID", "disease_id"),
                        code="malformed_clingen_gene_validity_row",
                        row_number=row_number,
                    )
                ),
                mode_of_inheritance=_row_value_any(row, ("MOI", "Mode Of Inheritance")),
                classification=_required_any_row_value(
                    row,
                    ("CLASSIFICATION", "Classification", "classification"),
                    code="malformed_clingen_gene_validity_row",
                    row_number=row_number,
                ),
                source_date=_required_any_row_value(
                    row,
                    ("CLASSIFICATION DATE", "Report Date", "source_date"),
                    code="malformed_clingen_gene_validity_row",
                    row_number=row_number,
                ),
                report_url=_row_value_any(row, ("ONLINE REPORT", "Report URL", "report_url")),
                provenance=provenance,
            )
        )
    if not records:
        raise ClinicalSourceTableError(
            "empty_clingen_gene_validity_fixture",
            "ClinGen gene-validity fixture must contain at least one row",
            {"path": str(path)},
        )
    return tuple(records)


def parse_gencc_download_csv(
    path: Path,
    *,
    provenance: ClinicalTableProvenance,
) -> tuple[GenCcAssertionRecord, ...]:
    records: list[GenCcAssertionRecord] = []
    for row_number, row in enumerate(_dict_rows(path, delimiter=","), start=2):
        records.append(
            GenCcAssertionRecord(
                gene_symbol=_required_any_row_value(
                    row,
                    ("gene_symbol", "Gene Symbol", "submitted_as_symbol"),
                    code="malformed_gencc_row",
                    row_number=row_number,
                ).upper(),
                gene_curie=_row_value_any(row, ("gene_curie", "submitted_as_hgnc_id")),
                disease_title=_required_any_row_value(
                    row,
                    ("disease_title", "Disease Title", "submitted_as_disease_name"),
                    code="malformed_gencc_row",
                    row_number=row_number,
                ),
                disease_curie=_normalize_curie(
                    _required_any_row_value(
                        row,
                        ("disease_curie", "submitted_as_mondo_id", "Disease ID"),
                        code="malformed_gencc_row",
                        row_number=row_number,
                    )
                ),
                assertion=_required_any_row_value(
                    row,
                    ("classification_title", "Assertion", "assertion"),
                    code="malformed_gencc_row",
                    row_number=row_number,
                ),
                submitter=_required_any_row_value(
                    row,
                    ("submitter_title", "Submitter", "submitter"),
                    code="malformed_gencc_row",
                    row_number=row_number,
                ),
                source_date=_required_any_row_value(
                    row,
                    ("submitted_as_date", "submitted_at", "source_date"),
                    code="malformed_gencc_row",
                    row_number=row_number,
                ),
                report_url=_row_value_any(
                    row,
                    ("submitted_as_public_report_url", "public_report_url", "report_url"),
                ),
                provenance=provenance,
            )
        )
    if not records:
        raise ClinicalSourceTableError(
            "empty_gencc_fixture",
            "GenCC fixture must contain at least one row",
            {"path": str(path)},
        )
    return tuple(records)


def _build_provenance_by_path(
    paths: ClinicalSourceFixturePaths,
    registry: DataSourceRegistry,
    *,
    source_version_overrides: Mapping[str, str] | None = None,
) -> dict[Path, ClinicalTableProvenance]:
    hpo_terms_path = _hpo_terms_path(paths)
    provenance = {
        paths.mondo_json: _provenance(paths.mondo_json, MONDO_SOURCE_ID, registry),
        paths.phenotype_hpoa: _provenance(paths.phenotype_hpoa, HPO_SOURCE_ID, registry),
        hpo_terms_path: _provenance(hpo_terms_path, HPO_SOURCE_ID, registry),
        paths.genes_to_phenotype: _provenance(paths.genes_to_phenotype, HPO_SOURCE_ID, registry),
        paths.clingen_gene_validity_csv: _provenance(
            paths.clingen_gene_validity_csv,
            CLINGEN_GENE_VALIDITY_SOURCE_ID,
            registry,
        ),
        paths.gencc_download_csv: _provenance(paths.gencc_download_csv, GENCC_SOURCE_ID, registry),
    }
    if not source_version_overrides:
        return provenance
    return {
        path: _replace_source_version(item, source_version_overrides.get(item.source_id))
        for path, item in provenance.items()
    }


def _parse_hpo_terms(paths: ClinicalSourceFixturePaths) -> Mapping[str, str]:
    if paths.hpo_terms_tsv is not None:
        return parse_hpo_terms_tsv(paths.hpo_terms_tsv)
    if paths.hpo_terms_json is not None:
        return parse_hpo_terms_json(paths.hpo_terms_json)
    raise ValueError("exactly one HPO term source must be configured")


def _hpo_terms_path(paths: ClinicalSourceFixturePaths) -> Path:
    return paths.hpo_terms_tsv or paths.hpo_terms_json or _missing_hpo_terms_path()


def _missing_hpo_terms_path() -> Path:
    raise ValueError("exactly one HPO term source must be configured")


def _replace_source_version(
    provenance: ClinicalTableProvenance,
    source_version: str | None,
) -> ClinicalTableProvenance:
    if not source_version:
        return provenance
    return ClinicalTableProvenance(
        source_id=provenance.source_id,
        source_version=source_version,
        checksum_algorithm=provenance.checksum_algorithm,
        checksum=provenance.checksum,
        relative_path=provenance.relative_path,
    )


def _provenance(
    path: Path,
    source_id: str,
    registry: DataSourceRegistry,
) -> ClinicalTableProvenance:
    record = registry.get(source_id)
    return ClinicalTableProvenance(
        source_id=source_id,
        source_version=record.source_version,
        checksum_algorithm="sha256",
        checksum=_sha256_file(path),
        relative_path=_repo_relative_path(path),
    )


@lru_cache(maxsize=8)
def _load_json(path: Path) -> Mapping[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ClinicalSourceTableError(
            "fixture_unavailable",
            "clinical source table fixture is unavailable",
            {"path": str(path)},
        ) from exc
    except ValueError as exc:
        raise ClinicalSourceTableError(
            "fixture_malformed_json",
            "clinical source table fixture is not valid JSON",
            {"path": str(path)},
        ) from exc


def _dict_rows(
    path: Path,
    *,
    delimiter: str,
    header_contains: tuple[str, ...] = (),
) -> Iterable[Mapping[str, str]]:
    try:
        file = path.open("r", encoding="utf-8", errors="replace", newline="")
    except OSError as exc:
        raise ClinicalSourceTableError(
            "fixture_unavailable",
            "clinical source table fixture is unavailable",
            {"path": str(path)},
        ) from exc
    header: list[str] | None = None
    with file:
        reader = csv.reader(file, delimiter=delimiter)
        for row_number, values in enumerate(reader, start=1):
            if not values or not any(value.strip() for value in values):
                continue
            if values[0].startswith("#"):
                candidate_header = [values[0][1:], *values[1:]]
                if len(candidate_header) > 1 and (
                    not header_contains or _header_matches(candidate_header, header_contains)
                ):
                    header = candidate_header
                continue
            if _is_divider_row(values):
                continue
            if header is None:
                if header_contains:
                    if _header_matches(values, header_contains):
                        header = values
                    continue
                header = values
                continue
            if len(values) != len(header):
                raise ClinicalSourceTableError(
                    "malformed_table_row",
                    "clinical source table row field count does not match header",
                    {
                        "path": str(path),
                        "row": row_number,
                        "field_count": len(values),
                        "header_count": len(header),
                    },
                )
            yield dict(zip(header, values, strict=True))
    if header is None:
        raise ClinicalSourceTableError(
            "fixture_missing_header",
            "clinical source table fixture must include a header row",
            {"path": str(path)},
        )


def _header_matches(header: Iterable[str], required_columns: tuple[str, ...]) -> bool:
    normalized = {value.strip().lower() for value in header}
    return all(column.strip().lower() in normalized for column in required_columns)


def _is_divider_row(values: Iterable[str]) -> bool:
    non_empty = [value.strip() for value in values if value.strip()]
    return bool(non_empty) and all(set(value) <= {"+"} for value in non_empty)


def _required_mapping(
    value: object,
    field_name: str,
    *,
    code: str,
    details: Mapping[str, object] | None = None,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ClinicalSourceTableError(
            code,
            f"{field_name} must be an object",
            {"field": field_name, **dict(details or {})},
        )
    return value


def _optional_mapping(value: object) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _required_list(value: object, field_name: str, *, code: str) -> list[Any]:
    if not isinstance(value, list):
        raise ClinicalSourceTableError(
            code,
            f"{field_name} must be a list",
            {"field": field_name},
        )
    return value


def _required_string(
    value: object,
    field_name: str,
    *,
    code: str,
    details: Mapping[str, object] | None = None,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClinicalSourceTableError(
            code,
            f"{field_name} must be a non-empty string",
            {"field": field_name, **dict(details or {})},
        )
    return value.strip()


def _required_row_value(
    row: Mapping[str, str],
    field_name: str,
    *,
    code: str,
    row_number: int,
) -> str:
    value = _row_value(row, field_name)
    if value is None:
        raise ClinicalSourceTableError(
            code,
            f"{field_name} is required",
            {"row": row_number, "field": field_name},
        )
    return value


def _required_any_row_value(
    row: Mapping[str, str],
    field_names: tuple[str, ...],
    *,
    code: str,
    row_number: int,
) -> str:
    value = _row_value_any(row, field_names)
    if value is None:
        raise ClinicalSourceTableError(
            code,
            "one of the required source columns is missing",
            {"row": row_number, "fields": field_names},
        )
    return value


def _row_value(row: Mapping[str, str], field_name: str) -> str | None:
    value = row.get(field_name)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _row_value_any(row: Mapping[str, str], field_names: tuple[str, ...]) -> str | None:
    for field_name in field_names:
        value = _row_value(row, field_name)
        if value is not None:
            return value
    return None


def _mondo_id_from_iri(value: str) -> str | None:
    if value.startswith("MONDO:"):
        return _normalize_curie(value)
    suffix = value.rsplit("/", 1)[-1]
    if not suffix.startswith("MONDO_"):
        return None
    return suffix.replace("_", ":", 1)


def _hpo_id_from_iri(value: str) -> str | None:
    if value.startswith("HP:"):
        return _normalize_curie(value)
    suffix = value.rsplit("/", 1)[-1]
    if not suffix.startswith("HP_"):
        return None
    return suffix.replace("_", ":", 1)


def _xrefs_from_metadata(metadata: Mapping[str, Any]) -> tuple[str, ...]:
    raw_xrefs = metadata.get("xrefs")
    if not isinstance(raw_xrefs, list):
        return ()
    values: list[str] = []
    for raw_xref in raw_xrefs:
        if isinstance(raw_xref, Mapping):
            value = _row_text(raw_xref.get("val"))
        else:
            value = _row_text(raw_xref)
        if value:
            values.append(_normalize_curie(value))
    return tuple(dict.fromkeys(values))


def _definition_from_metadata(metadata: Mapping[str, Any]) -> str | None:
    raw_definition = metadata.get("definition")
    if isinstance(raw_definition, Mapping):
        return _row_text(raw_definition.get("val"))
    return _row_text(raw_definition)


def _is_deprecated(metadata: Mapping[str, Any] | None) -> bool:
    return bool(metadata and metadata.get("deprecated") is True)


def _row_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_curie(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if ":" not in text and "_" in text:
        prefix, suffix = text.split("_", 1)
        return f"{prefix.upper()}:{suffix}"
    prefix, suffix = text.split(":", 1) if ":" in text else ("", text)
    if not prefix:
        return suffix
    return f"{prefix.upper()}:{suffix}"


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _repo_relative_path(path: Path) -> str:
    return repo_relative_path(path, anchor=__file__)


def _repo_root() -> Path:
    return find_project_root(__file__)
