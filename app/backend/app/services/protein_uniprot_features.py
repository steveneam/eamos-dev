from __future__ import annotations

from collections.abc import Iterator
import gzip
import json
from pathlib import Path
import re
import time
from typing import Any

from app.schemas.protein_annotation import ProteinDomainTrackFeature

UNIPROT_FEATURE_SOURCE = "UniProtKB/Swiss-Prot feature table"
_UNIPROT_FEATURE_KIND_MAP = {
    "CHAIN": "region",
    "INIT_MET": "site",
    "PEPTIDE": "region",
    "PROPEP": "region",
    "DOMAIN": "domain",
    "DNA_BIND": "domain",
    "ZN_FING": "domain",
    "NP_BIND": "region",
    "CA_BIND": "site",
    "REGION": "region",
    "MOTIF": "motif",
    "REPEAT": "repeat",
    "SITE": "site",
    "ACT_SITE": "site",
    "BINDING": "site",
    "METAL": "site",
    "MOD_RES": "site",
    "CARBOHYD": "site",
    "LIPID": "site",
    "DISULFID": "site",
    "CROSSLNK": "site",
    "NON_STD": "site",
    "COILED": "coiled_coil",
    "COMPBIAS": "low_complexity",
    "SIGNAL": "signal_peptide",
    "TRANSIT": "region",
    "TRANSMEM": "transmembrane",
    "INTRAMEM": "transmembrane",
    "TOPO_DOM": "topological_domain",
    "HELIX": "region",
    "STRAND": "region",
    "TURN": "region",
}


def parse_uniprot_flatfile_features(
    entry_text: str,
    *,
    protein_length: int,
    source_release: str | None,
    source_checksum_sha256: str | None,
) -> list[ProteinDomainTrackFeature]:
    accession = _primary_uniprot_accession(entry_text)
    features: list[ProteinDomainTrackFeature] = []
    for current in _uniprot_feature_records(entry_text):
        feature = _uniprot_feature_from_current(
            current,
            accession=accession,
            protein_length=protein_length,
            source_release=source_release,
            source_checksum_sha256=source_checksum_sha256,
            ordinal=len(features) + 1,
        )
        if feature is not None:
            features.append(feature)
    return sorted(
        _dedupe_features(features),
        key=lambda item: (item.aa_start, item.aa_end, item.source, item.label),
    )


def _find_uniprot_entry(
    *,
    path: Path,
    gene_symbol: str | None,
    protein_accession: str | None,
    timeout_seconds: float,
    started_at: float,
) -> str | None:
    requested_gene = (gene_symbol or "").upper()
    requested_accession = (protein_accession or "").upper()
    entry_lines: list[str] = []
    with _open_uniprot_text(path) as handle:
        for line in handle:
            if time.monotonic() - started_at > timeout_seconds:
                raise TimeoutError("uniprot_flatfile_scan_timeout")
            entry_lines.append(line)
            if not line.startswith("//"):
                continue
            entry = "".join(entry_lines)
            if _uniprot_entry_matches(
                entry,
                gene_symbol=requested_gene,
                protein_accession=requested_accession,
            ):
                return entry
            entry_lines = []
    return None


def _find_uniprot_feature_index_record(
    *,
    path: Path,
    gene_symbol: str | None,
    protein_accession: str | None,
    timeout_seconds: float,
    started_at: float,
) -> dict[str, Any] | None:
    requested_gene = (gene_symbol or "").upper()
    requested_accession = (protein_accession or "").upper()
    with path.open("rt", encoding="utf-8") as handle:
        for raw_line in handle:
            if time.monotonic() - started_at > timeout_seconds:
                raise TimeoutError("uniprot_feature_index_scan_timeout")
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            accessions = {
                str(accession).upper()
                for accession in record.get("accessions", [])
                if str(accession).strip()
            }
            genes = {str(gene).upper() for gene in record.get("genes", []) if str(gene).strip()}
            if requested_accession and requested_accession in accessions:
                return record
            if requested_gene and requested_gene in genes:
                return record
    return None


def _features_from_uniprot_feature_index_record(
    record: dict[str, Any],
    *,
    protein_length: int,
    source_release: str | None,
    source_checksum_sha256: str | None,
) -> list[ProteinDomainTrackFeature]:
    accession = str(record.get("primary_accession") or "").strip() or None
    features: list[ProteinDomainTrackFeature] = []
    for raw_feature in record.get("features", []):
        if not isinstance(raw_feature, dict):
            continue
        current: dict[str, object] = {
            "feature_key": str(raw_feature.get("feature_key") or ""),
            "location": str(raw_feature.get("location") or ""),
        }
        qualifiers = raw_feature.get("qualifiers")
        if isinstance(qualifiers, dict):
            for key in ("note", "id", "ligand", "ligand_id"):
                value = qualifiers.get(key)
                if value:
                    current[key] = str(value)
        feature = _uniprot_feature_from_current(
            current,
            accession=accession,
            protein_length=protein_length,
            source_release=source_release,
            source_checksum_sha256=source_checksum_sha256,
            ordinal=len(features) + 1,
        )
        if feature is not None:
            features.append(feature)
    return sorted(
        _dedupe_features(features),
        key=lambda item: (item.aa_start, item.aa_end, item.source, item.label),
    )


def iter_uniprot_feature_index_records(path: Path) -> Iterator[dict[str, Any]]:
    entry_lines: list[str] = []
    with _open_uniprot_text(path) as handle:
        for line in handle:
            entry_lines.append(line)
            if not line.startswith("//"):
                continue
            entry = "".join(entry_lines)
            record = _uniprot_feature_index_record(entry)
            if record is not None:
                yield record
            entry_lines = []


def write_uniprot_feature_index(dat_path: Path, output_path: Path) -> dict[str, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    record_count = 0
    feature_count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in iter_uniprot_feature_index_records(dat_path):
            record_count += 1
            feature_count += len(record.get("features", []))
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    return {"records": record_count, "features": feature_count}


def _uniprot_feature_index_record(entry_text: str) -> dict[str, Any] | None:
    accessions = _uniprot_accessions(entry_text)
    genes = _uniprot_gene_symbols(entry_text)
    features = [
        _uniprot_feature_index_feature(record) for record in _uniprot_feature_records(entry_text)
    ]
    features = [feature for feature in features if feature is not None]
    if not accessions or not features:
        return None
    return {
        "primary_accession": accessions[0],
        "accessions": accessions,
        "genes": genes,
        "features": features,
    }


def _uniprot_feature_index_feature(record: dict[str, object]) -> dict[str, Any] | None:
    feature_key = str(record.get("feature_key") or "")
    location = str(record.get("location") or "")
    if not feature_key or not location:
        return None
    qualifiers: dict[str, str] = {}
    for key in ("note", "id", "ligand", "ligand_id"):
        value = str(record.get(key) or "").strip()
        if value:
            qualifiers[key] = value
    return {
        "feature_key": feature_key,
        "location": location,
        "qualifiers": qualifiers,
    }


def _uniprot_feature_records(entry_text: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for raw_line in entry_text.splitlines():
        if not raw_line.startswith("FT"):
            continue
        payload = raw_line[5:].rstrip() if len(raw_line) > 5 else ""
        if not payload.strip():
            continue
        if payload[0].isspace():
            if current is not None:
                _apply_uniprot_feature_qualifier(current, payload.strip())
            continue

        if current is not None:
            records.append(current)
        parts = payload.split(None, 1)
        current = {"feature_key": parts[0], "location": parts[1] if len(parts) > 1 else ""}

    if current is not None:
        records.append(current)
    return records


def _open_uniprot_text(path: Path):
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("rt", encoding="utf-8", errors="replace")


def _uniprot_entry_matches(
    entry: str,
    *,
    gene_symbol: str,
    protein_accession: str,
) -> bool:
    accessions = {accession.upper() for accession in _uniprot_accessions(entry)}
    genes = {gene.upper() for gene in _uniprot_gene_symbols(entry)}
    if protein_accession and protein_accession in accessions:
        return True
    return bool(gene_symbol and gene_symbol in genes)


def _uniprot_accessions(entry: str) -> list[str]:
    accessions: list[str] = []
    for line in entry.splitlines():
        if not line.startswith("AC"):
            continue
        values = line[5:].replace(";", " ").split()
        accessions.extend(value.strip() for value in values if value.strip())
    return accessions


def _primary_uniprot_accession(entry: str) -> str | None:
    accessions = _uniprot_accessions(entry)
    return accessions[0] if accessions else None


def _uniprot_gene_symbols(entry: str) -> list[str]:
    genes: list[str] = []
    for line in entry.splitlines():
        if not line.startswith("GN"):
            continue
        payload = line[5:]
        for key in ("Name", "Synonyms", "OrderedLocusNames", "ORFNames"):
            for match in re.finditer(rf"{key}=([^;]+)", payload):
                genes.extend(
                    item.strip() for item in re.split(r"[, ]+", match.group(1)) if item.strip()
                )
    return genes


def _apply_uniprot_feature_qualifier(current: dict[str, object], qualifier: str) -> None:
    if not qualifier.startswith("/"):
        return
    key, _, raw_value = qualifier[1:].partition("=")
    value = raw_value.strip().strip('"')
    if key in {"note", "id", "ligand", "ligand_id"} and value:
        current[str(key)] = value


def _uniprot_feature_from_current(
    current: dict[str, object],
    *,
    accession: str | None,
    protein_length: int,
    source_release: str | None,
    source_checksum_sha256: str | None,
    ordinal: int,
) -> ProteinDomainTrackFeature | None:
    feature_key = str(current.get("feature_key") or "")
    kind = _UNIPROT_FEATURE_KIND_MAP.get(feature_key)
    if kind is None:
        return None
    aa_range = _uniprot_location_range(str(current.get("location") or ""))
    if aa_range is None:
        return None
    aa_start, aa_end = aa_range
    if aa_start > protein_length or aa_end < 1:
        return None
    aa_start = max(1, aa_start)
    aa_end = min(protein_length, aa_end)
    label = _uniprot_feature_label(feature_key, current)
    if not label:
        return None
    source_accession = accession or "UniProtKB"
    return ProteinDomainTrackFeature(
        feature_id=f"uniprot:{source_accession}:{feature_key}:{aa_start}-{aa_end}:{ordinal}",
        kind=kind,
        label=label,
        short_label=_short_uniprot_feature_label(label),
        aa_start=aa_start,
        aa_end=aa_end,
        accession=accession,
        source=UNIPROT_FEATURE_SOURCE,
        source_accession=source_accession,
        source_release=source_release,
        source_checksum_sha256=source_checksum_sha256,
        description=_uniprot_feature_description(label),
        lane=_uniprot_feature_lane(kind),
    )


def _uniprot_location_range(location: str) -> tuple[int, int] | None:
    digits = [int(value) for value in re.findall(r"\d+", location)]
    if not digits:
        return None
    return min(digits), max(digits)


def _uniprot_feature_label(feature_key: str, current: dict[str, object]) -> str:
    for key in ("note", "id", "ligand"):
        value = str(current.get(key) or "").strip()
        if value:
            return value
    default_labels = {
        "SIGNAL": "Signal peptide",
        "TRANSMEM": "Transmembrane helix",
        "TOPO_DOM": "Topological domain",
        "COMPBIAS": "Compositional bias",
    }
    if feature_key in default_labels:
        return default_labels[feature_key]
    return feature_key.replace("_", " ").title()


def _short_uniprot_feature_label(label: str) -> str:
    normalized = label.lower()
    if normalized == "fz":
        return "CRD"
    transmembrane_match = re.search(r"transmembrane helix\s*(\d+)", normalized)
    if transmembrane_match:
        return f"TM{transmembrane_match.group(1)}"
    transmembrane_name_match = re.search(r"name\s*=\s*(\d+)", normalized)
    if transmembrane_name_match:
        return f"TM{transmembrane_name_match.group(1)}"
    short_labels = (
        ("dynamin-type g", "GTPase"),
        ("rpe65 catalytic", "RPE65 cat."),
        ("carotenoid oxygenase", "RPE65 cat."),
        ("frizzled cysteine-rich", "CRD"),
        ("frizzled domain", "Fz"),
        ("wnt-binding", "CRD"),
        ("wnt binding", "CRD"),
        ("transmembrane helix", "TM"),
        ("signal peptide", "SP"),
        ("extracellular", "Extra"),
        ("cytoplasmic", "Cyto"),
        ("iron-binding", "Fe"),
        ("palmitoyl", "Palm"),
        ("membrane contact", "Mem"),
        ("pleckstrin homology", "PH"),
        ("gtpase effector", "GED"),
        ("proline-rich", "PRD"),
        ("proline rich", "PRD"),
        ("nuclear localization signal", "NLS"),
        ("gtpase", "GTPase"),
        ("middle/stalk", "Middle"),
        ("middle domain", "Middle"),
        ("laminin egf", "LamEGF"),
        ("laminin g", "LamG"),
        ("laminin n", "LamNT"),
        ("fibronectin type-iii", "FN3"),
        ("fibronectin type iii", "FN3"),
        ("coiled-coil", "CC"),
        ("helical", "TM"),
        ("carotenoid oxygenase", "COX"),
    )
    for needle, abbreviation in short_labels:
        if needle in normalized:
            return abbreviation
    if len(label) <= 12:
        return label
    words = re.findall(r"[A-Za-z0-9]+", label)
    if 1 < len(words) <= 4:
        acronym = "".join(word[0].upper() for word in words if word)
        if 2 <= len(acronym) <= 6:
            return acronym
    return label[:12].rstrip()


def _uniprot_feature_description(label: str) -> str:
    normalized = label.lower()
    if normalized == "fz" or "frizzled cysteine-rich" in normalized:
        return "WNT-binding Frizzled cysteine-rich domain"
    if "rpe65" in normalized and "carotenoid oxygenase" in normalized:
        return "Carotenoid oxygenase/RPE65 catalytic family domain"
    return label


def _uniprot_feature_lane(kind: str) -> str:
    if kind in {"signal_peptide", "transmembrane", "topological_domain"}:
        return "topology"
    if kind in {"site", "epitope"}:
        return "sites"
    if kind in {"motif", "coiled_coil", "low_complexity"}:
        return "motifs"
    return "domains"


def _dedupe_features(
    features: list[ProteinDomainTrackFeature],
) -> list[ProteinDomainTrackFeature]:
    seen: set[tuple[str, int, int, str]] = set()
    deduped: list[ProteinDomainTrackFeature] = []
    for feature in features:
        key = (feature.source, feature.aa_start, feature.aa_end, feature.label)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(feature)
    return deduped
