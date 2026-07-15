from __future__ import annotations

import re
from typing import Any

from app.schemas.run import SourceProvenance
from app.services.report_provenance import provenance_for_source


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [text for text in (_optional_text(item) for item in value) if text]
    text = _optional_text(value)
    return [text] if text else []


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _dedupe_text(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = item.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _first_prefixed(items: list[str], prefix: str) -> str | None:
    prefix_upper = prefix.upper()
    return next((item for item in items if item.upper().startswith(prefix_upper)), None)


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    match = re.search(r"\d+", text)
    if match is None:
        return None
    return int(match.group(0))


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _chromosome(genomic_hg38: str | None) -> str | None:
    if not genomic_hg38 or "-" not in genomic_hg38:
        return None
    return genomic_hg38.split("-", 1)[0]


def _chromosome_from_variant_validator(summary: dict[str, Any]) -> str | None:
    vcf = _dict_or_empty(summary.get("vcf"))
    return _optional_text(vcf.get("chr"))


def _strand_from_sequence_context(summary: dict[str, Any]) -> str | None:
    strand = _optional_text(summary.get("strand"))
    return strand if strand in {"+", "-"} else None


def _strand_from_vep(summary: dict[str, Any]) -> str | None:
    strand = summary.get("strand")
    if strand in {"+", "-"}:
        return strand
    if strand in {1, "1", "+1"}:
        return "+"
    if strand in {-1, "-1"}:
        return "-"
    return None


def _strand_from_coords(coords: str) -> str | None:
    if "(+)" in coords:
        return "+"
    if "(-)" in coords:
        return "-"
    return None


def _exon_from_variant_validator(summary: dict[str, Any]) -> str | None:
    return _optional_text(summary.get("exon"))


def _exon_from_vep(summary: dict[str, Any]) -> str | None:
    exon = _optional_text(summary.get("exon"))
    if exon and "/" in exon:
        return exon.split("/", 1)[0]
    return exon


def _exon_from_coords(coords: str) -> str | None:
    match = re.search(r"\bexon\s+(\d+)\b", coords, flags=re.I)
    if match is None:
        return None
    return match.group(1)


def _codon_change(query_codon) -> str | None:
    if query_codon is None:
        return None
    if not query_codon.aa_alt:
        return f"{query_codon.aa_ref}{query_codon.codon_number}"
    return f"{query_codon.aa_ref}{query_codon.codon_number}{query_codon.aa_alt}"


def _codon_change_from_sequence_context(summary: dict[str, Any]) -> str | None:
    ref = _optional_text(summary.get("codon_ref"))
    alt = _optional_text(summary.get("codon_alt"))
    if ref and alt:
        return f"{ref}>{alt}"
    number = _optional_text(summary.get("codon_number"))
    return f"codon {number}" if number else None


def _codon_change_from_vep(summary: dict[str, Any]) -> str | None:
    codons = _optional_text(summary.get("codons"))
    if not codons:
        return None
    parts = [part.upper() for part in re.split(r"[/|]", codons) if part]
    if len(parts) >= 2:
        return f"{parts[0]}>{parts[1]}"
    return codons


def _protein_position_from_vep(summary: dict[str, Any]) -> str | None:
    return _optional_text(summary.get("protein_position"))


def _protein_position(protein_change: str | None) -> str | None:
    if not protein_change:
        return None
    match = re.search(r"(\d+)", protein_change)
    return match.group(1) if match else None


def _filter_provenance(
    provenance: list[SourceProvenance],
    sources: set[str],
) -> list[SourceProvenance]:
    return [item for item in provenance if item.source in sources]


def _sequence_context_provenance(summary: dict[str, Any]) -> list[SourceProvenance]:
    if not summary:
        return []
    source = _optional_text(summary.get("source"))
    status = "fixture" if source == "fixture" else "live" if source == "resolver" else "missing"
    metadata = _dict_or_empty(summary.get("source_metadata"))
    query = {
        "gene": summary.get("gene"),
        "cdna": summary.get("cdna"),
        "transcript": summary.get("transcript"),
        "genomic_hg38": summary.get("genomic_hg38"),
    }
    source_url = _optional_text(
        metadata.get("ensembl_sequence_url") or metadata.get("variant_validator_url")
    )
    version = _optional_text(metadata.get("fixture") or metadata.get("coordinate_source"))
    return [
        provenance_for_source(
            "sequence_context",
            status=status,
            query=query,
            source_url=source_url,
            version=version,
            warnings=_string_list(summary.get("warnings")),
        )
    ]


def _molecular_context_provenance(
    summary: dict[str, Any],
    *,
    status: str,
) -> list[SourceProvenance]:
    raw = summary.get("provenance")
    provenance: list[SourceProvenance] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                provenance.append(SourceProvenance.model_validate(item))
            except Exception:
                continue
    if provenance:
        return provenance
    gene = _optional_text(summary.get("gene"))
    return [
        provenance_for_source(
            "molecular_context",
            status=status,
            query={"gene": gene} if gene else {},
            warnings=_string_list(summary.get("warnings")),
        )
    ]


def _dedupe_provenance(items: list[SourceProvenance]) -> list[SourceProvenance]:
    seen: set[tuple[str, str | None, str | None, tuple[tuple[str, str], ...]]] = set()
    result: list[SourceProvenance] = []
    for item in items:
        key = (
            item.source,
            item.source_url,
            item.version,
            tuple(sorted(item.query.items())),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _classification_text(value: Any) -> str | None:
    text = _optional_text(value)
    if text is None or text.lower() in {"unavailable", "not found", "none"}:
        return None
    return text


def _clinical_consensus(evidence_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    value = evidence_map.get("clinical_consensus")
    return value if isinstance(value, dict) else {}
