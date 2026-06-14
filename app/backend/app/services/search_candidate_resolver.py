from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from app.schemas.lookup import SearchInputCandidate, SearchInputConfidence
from app.services.clingen_local import ClinGenLocalStore
from app.services.search_input_resolver import SearchInputResolution


@dataclass(frozen=True)
class CandidateRecord:
    candidate_id: str
    display_label: str
    gene: str
    cdna: str | None = None
    transcript: str | None = None
    protein_change: str | None = None
    genomic_hg38: str | None = None
    genomic_hgvs: str | None = None
    source_support: tuple[str, ...] = ()
    source_url: str | None = None


class SearchCandidateResolver:
    """First-slice reported-variant resolver for protein and near-miss inputs.

    The fixture is intentionally small and source-labeled. It is a replaceable
    provider boundary for ClinVar/MyVariant/local-index candidate records.
    """

    def __init__(
        self,
        records: Iterable[CandidateRecord] | None = None,
        *,
        settings=None,
    ) -> None:
        self.settings = settings
        self.records = tuple(records) if records is not None else _candidate_records()

    def get_candidate(self, candidate_id: str) -> SearchInputCandidate | None:
        record = self._record_by_id(candidate_id) or self._clingen_local_record_by_candidate_id(
            candidate_id
        )
        if record is None:
            return None
        return self._to_candidate(
            record,
            match_reason="Selected reported candidate.",
            confidence="high",
        )

    def resolve_candidates(self, resolution: SearchInputResolution) -> list[SearchInputCandidate]:
        if resolution.kind == "protein":
            return self._protein_candidates(resolution)
        if resolution.kind in {"cdna", "genomic"}:
            exact = self.exact_candidate(resolution)
            if exact is not None:
                return [exact]
            return self._near_miss_candidates(resolution)
        return []

    def exact_candidate(self, resolution: SearchInputResolution) -> SearchInputCandidate | None:
        for record in self.records:
            if not _same_gene_or_empty(record.gene, resolution.gene):
                continue
            if resolution.kind == "cdna" and _norm(record.cdna) == _norm(resolution.hgvs):
                return self._to_candidate(
                    record,
                    match_reason="Exact reported cDNA match.",
                    confidence="high",
                )
            if resolution.kind == "genomic" and _norm(record.genomic_hg38) == _norm(
                resolution.genomic_hg38 or resolution.hgvs
            ):
                return self._to_candidate(
                    record,
                    match_reason="Exact reported genomic match.",
                    confidence="high",
                )
            if resolution.kind == "genomic" and _norm(record.genomic_hgvs) == _norm(
                resolution.genomic_hgvs or resolution.hgvs
            ):
                return self._to_candidate(
                    record,
                    match_reason="Exact reported genomic HGVS match.",
                    confidence="high",
                )
        return None

    def _protein_candidates(self, resolution: SearchInputResolution) -> list[SearchInputCandidate]:
        requested = _protein_position(resolution.hgvs)
        requested_kind = _protein_kind(resolution.hgvs)
        ranked: list[tuple[int, bool, SearchInputCandidate]] = []
        for record in (*self.records, *self._clingen_local_records(resolution)):
            if resolution.gene and record.gene.upper() != resolution.gene.upper():
                continue
            record_position = _protein_position(record.protein_change)
            if requested is not None and record_position != requested:
                continue
            exact_change = _same_protein_change(record.protein_change, resolution.hgvs)
            record_kind = _protein_kind(record.protein_change)
            score = 100
            reasons = ["same protein position"]
            if resolution.gene and record.gene.upper() == resolution.gene.upper():
                score += 50
                reasons.append("same gene")
            if exact_change:
                score += 60
                reasons.append("same protein change")
            elif requested_kind and requested_kind == record_kind:
                score += 15
                reasons.append(f"{requested_kind} consequence")
            confidence = (
                "high"
                if exact_change
                and resolution.gene
                and record.gene.upper() == resolution.gene.upper()
                else "medium"
            )
            ranked.append(
                (
                    -score,
                    exact_change,
                    self._to_candidate(
                        record,
                        match_reason=", ".join(reasons).capitalize() + ".",
                        confidence=confidence,
                    ),
                )
            )
        matches = _dedupe_ranked_candidates(sorted(ranked, key=lambda item: item[0]))
        exact_matches = [match for match in matches if match[1]]
        if exact_matches:
            return [candidate for _, _, candidate in exact_matches]
        return [candidate for _, _, candidate in matches]

    def _clingen_local_records(
        self, resolution: SearchInputResolution
    ) -> tuple[CandidateRecord, ...]:
        if not resolution.gene:
            return ()
        db_path, manifest_path = self._clingen_local_paths()
        if db_path is None:
            return ()
        terms = _protein_query_terms(resolution.hgvs)
        if not terms:
            return ()
        try:
            store = ClinGenLocalStore(
                db_path,
                manifest_path=manifest_path,
                enabled=True,
            )
            rows, inspection, _needs_live_fallback = store.search_records_by_raw_text(
                gene=resolution.gene,
                terms=terms,
                limit=int(getattr(self.settings, "clingen_local_max_results", 25) or 25),
                verify_checksum=False,
            )
        except Exception:
            return ()
        if not inspection.ready:
            return ()
        return tuple(
            record
            for record in (_candidate_from_clingen_record(item) for item in rows)
            if record is not None
        )

    def _clingen_local_record_by_candidate_id(self, candidate_id: str) -> CandidateRecord | None:
        db_path, manifest_path = self._clingen_local_paths()
        if db_path is None:
            return None
        terms = _candidate_id_terms(candidate_id)
        if not terms:
            return None
        try:
            store = ClinGenLocalStore(
                db_path,
                manifest_path=manifest_path,
                enabled=True,
            )
            rows, inspection, _needs_live_fallback = store.search_records_by_terms(
                terms=terms,
                limit=int(getattr(self.settings, "clingen_local_max_results", 25) or 25),
                verify_checksum=False,
            )
        except Exception:
            return None
        if not inspection.ready:
            return None
        for record in (_candidate_from_clingen_record(item) for item in rows):
            if record is not None and record.candidate_id == candidate_id:
                return record
        return None

    def _clingen_local_paths(self) -> tuple[Path | None, Path | None]:
        if self.settings is None or not getattr(self.settings, "clingen_local_enabled", False):
            return None, None
        db_path = _settings_path(
            self.settings, getattr(self.settings, "clingen_local_sqlite_path", None)
        )
        if db_path is None or not db_path.is_file():
            return None, None
        manifest_path = _settings_path(
            self.settings,
            getattr(self.settings, "clingen_local_manifest_path", None),
        )
        return db_path, manifest_path

    def _near_miss_candidates(
        self,
        resolution: SearchInputResolution,
    ) -> list[SearchInputCandidate]:
        requested_pos = _cdna_position(resolution.hgvs)
        if requested_pos is None:
            return []

        ranked: list[tuple[int, SearchInputCandidate]] = []
        for record in self.records:
            if resolution.gene and record.gene.upper() != resolution.gene.upper():
                continue
            record_pos = _cdna_position(record.cdna)
            if record_pos is None:
                continue
            distance = abs(record_pos - requested_pos)
            if distance > 6:
                continue
            same_codon = _codon_number(record_pos) == _codon_number(requested_pos)
            score = 90 - distance
            if same_codon:
                score += 20
            ranked.append(
                (
                    -score,
                    self._to_candidate(
                        record,
                        match_reason=(
                            "Closest reported same-codon variant."
                            if same_codon
                            else "Nearby reported same-gene variant."
                        ),
                        confidence="medium",
                        distance=f"{distance} cDNA base{'s' if distance != 1 else ''}",
                    ),
                )
            )
        return [candidate for _, candidate in sorted(ranked, key=lambda item: item[0])]

    def _record_by_id(self, candidate_id: str) -> CandidateRecord | None:
        for record in self.records:
            if record.candidate_id == candidate_id:
                return record
        return None

    def _to_candidate(
        self,
        record: CandidateRecord,
        *,
        match_reason: str,
        confidence: SearchInputConfidence,
        distance: str | None = None,
    ) -> SearchInputCandidate:
        return SearchInputCandidate(
            candidate_id=record.candidate_id,
            display_label=record.display_label,
            gene=record.gene,
            cdna=record.cdna,
            transcript=record.transcript,
            protein_change=record.protein_change,
            genomic_hg38=record.genomic_hg38,
            genomic_hgvs=record.genomic_hgvs,
            match_reason=match_reason,
            source_support=list(record.source_support),
            source_count=len(record.source_support),
            distance=distance,
            confidence=confidence,
        )


@lru_cache(maxsize=1)
def _candidate_records() -> tuple[CandidateRecord, ...]:
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "search_candidate_records.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return tuple(
        CandidateRecord(
            candidate_id=str(item["candidate_id"]),
            display_label=str(item["display_label"]),
            gene=str(item["gene"]).upper(),
            cdna=item.get("cdna"),
            transcript=item.get("transcript"),
            protein_change=item.get("protein_change"),
            genomic_hg38=item.get("genomic_hg38"),
            genomic_hgvs=item.get("genomic_hgvs"),
            source_support=tuple(item.get("source_support") or ()),
            source_url=item.get("source_url"),
        )
        for item in payload
    )


def _candidate_from_clingen_record(record: dict[str, Any]) -> CandidateRecord | None:
    gene = _record_text(record, "gene", "geneSymbol").upper()
    if not gene:
        return None
    title = _record_text(record, "preferredVarTitle", "variantTitle")
    values = [title, *_record_string_values(record.get("hgvs"))]
    parsed = next(
        (
            item
            for item in (_parse_transcript_cdna_protein(value) for value in values)
            if item is not None
        ),
        None,
    )
    if parsed is None:
        return None
    transcript, cdna, protein = parsed
    genomic_hgvs = next(
        (value for value in _record_string_values(record.get("hgvs")) if value.startswith("NC_")),
        None,
    )
    clinvar_id = _clinvar_variation_id(record)
    candidate_id = (
        f"clinvar:VCV{int(clinvar_id):09d}"
        if clinvar_id and clinvar_id.isdigit()
        else f"clingen:{_record_text(record, 'uuid', '_id', '_key', 'caId')}"
    )
    if candidate_id.endswith(":"):
        return None
    source_support = _dedupe(
        [
            f"ClinVar VCV{int(clinvar_id):09d}" if clinvar_id and clinvar_id.isdigit() else "",
            f"ClinGen eRepo {_record_text(record, 'classification')}".strip(),
        ]
    )
    label = title or f"{transcript}:{cdna}"
    if not label.upper().startswith(gene):
        label = f"{gene} {label}"
    return CandidateRecord(
        candidate_id=candidate_id,
        display_label=label,
        gene=gene,
        cdna=cdna,
        transcript=transcript,
        protein_change=protein,
        genomic_hg38=_genomic_hg38_from_hgvs(genomic_hgvs),
        genomic_hgvs=genomic_hgvs,
        source_support=tuple(source_support),
        source_url=_candidate_source_url(record, clinvar_id),
    )


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", "", value or "").upper()


def _same_gene_or_empty(candidate_gene: str, requested_gene: str) -> bool:
    return not requested_gene or candidate_gene.upper() == requested_gene.upper()


def _protein_position(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"p\.?[A-Za-z*()]*?(\d+)", value)
    return int(match.group(1)) if match else None


def _protein_query_terms(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    compact = re.sub(r"\s+", "", value)
    match = re.search(r"p\.?([A-Za-z*]+)(\d+)", compact)
    if match is None:
        return (compact,)
    residue_prefix = f"p.{match.group(1)}{match.group(2)}"
    return tuple(_dedupe([residue_prefix, residue_prefix.removeprefix("p."), compact]))


def _same_protein_change(left: str | None, right: str | None) -> bool:
    return bool(left and right and _norm(left) == _norm(right))


def _protein_kind(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.lower()
    if "fs" in lowered or "frameshift" in lowered:
        return "frameshift"
    if "del" in lowered or "deletion" in lowered:
        return "deletion"
    if "*" in lowered or "ter" in lowered:
        return "nonsense"
    return "protein"


def _cdna_position(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"c\.(\d+)", value)
    return int(match.group(1)) if match else None


def _codon_number(cdna_position: int) -> int:
    return (cdna_position + 2) // 3


def _settings_path(settings, path) -> Path | None:
    if path is None:
        return None
    resolved = path if isinstance(path, Path) else Path(path)
    if resolved.is_absolute():
        return resolved
    backend_root = getattr(settings, "backend_root", None)
    if backend_root is None:
        return resolved
    return Path(backend_root) / resolved


def _dedupe_ranked_candidates(
    values: list[tuple[int, bool, SearchInputCandidate]],
) -> list[tuple[int, bool, SearchInputCandidate]]:
    seen: set[str] = set()
    result: list[tuple[int, bool, SearchInputCandidate]] = []
    for item in values:
        candidate_id = item[2].candidate_id
        if candidate_id in seen:
            continue
        seen.add(candidate_id)
        result.append(item)
    return result


def _parse_transcript_cdna_protein(value: str | None) -> tuple[str, str, str | None] | None:
    if not value:
        return None
    match = re.search(
        r"(?P<transcript>[A-Z]{2}_\d+(?:\.\d+)?)(?:\([^)]+\))?:"
        r"(?P<cdna>c\.[^\s(]+)(?:\s+\((?P<protein>p\.[^)]+)\))?",
        value,
    )
    if match is None:
        return None
    return match.group("transcript"), match.group("cdna"), match.group("protein")


def _genomic_hg38_from_hgvs(value: str | None) -> str | None:
    if not value:
        return None
    match = re.fullmatch(r"NC_0*(\d+)\.\d+:g\.(\d+)([ACGT]+)>([ACGT]+)", value)
    if match is None:
        return None
    raw_chrom, position, ref, alt = match.groups()
    chrom_number = int(raw_chrom)
    if 1 <= chrom_number <= 22:
        chrom = str(chrom_number)
    elif chrom_number == 23:
        chrom = "X"
    elif chrom_number == 24:
        chrom = "Y"
    else:
        return None
    return f"{chrom}-{position}-{ref}-{alt}"


def _record_text(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _record_string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _clinvar_variation_id(record: dict[str, Any]) -> str | None:
    for key in ("cvId", "clinvarVariationId", "variation_id", "variationId"):
        value = _record_text(record, key)
        if value:
            value = value.upper().removeprefix("VCV").lstrip("0") or "0"
            return value if value.isdigit() else None
    return None


def _candidate_source_url(record: dict[str, Any], clinvar_id: str | None) -> str | None:
    if clinvar_id and clinvar_id.isdigit():
        return f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{int(clinvar_id)}/"
    return _record_text(record, "sourceUrl", "url", "iri") or None


def _candidate_id_terms(candidate_id: str) -> tuple[str, ...]:
    if not candidate_id:
        return ()
    if candidate_id.startswith("clinvar:VCV"):
        accession = candidate_id.split(":", 1)[1]
        digits = accession.removeprefix("VCV").lstrip("0")
        return tuple(_dedupe([accession, digits]))
    if candidate_id.startswith("clingen:"):
        return (candidate_id.split(":", 1)[1],)
    return (candidate_id,)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
