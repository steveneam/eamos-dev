from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from app.schemas.lookup import SearchInputCandidate, SearchInputConfidence
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

    def __init__(self, records: Iterable[CandidateRecord] | None = None) -> None:
        self.records = tuple(records) if records is not None else _candidate_records()

    def get_candidate(self, candidate_id: str) -> SearchInputCandidate | None:
        record = self._record_by_id(candidate_id)
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
        ranked: list[tuple[int, SearchInputCandidate]] = []
        for record in self.records:
            if resolution.gene and record.gene.upper() != resolution.gene.upper():
                continue
            record_position = _protein_position(record.protein_change)
            if requested is not None and record_position != requested:
                continue
            record_kind = _protein_kind(record.protein_change)
            score = 100
            reasons = ["same protein position"]
            if resolution.gene and record.gene.upper() == resolution.gene.upper():
                score += 50
                reasons.append("same gene")
            if requested_kind and requested_kind == record_kind:
                score += 30
                reasons.append(f"{requested_kind} consequence")
            confidence = "high" if score >= 180 else "medium"
            ranked.append(
                (
                    -score,
                    self._to_candidate(
                        record,
                        match_reason=", ".join(reasons).capitalize() + ".",
                        confidence=confidence,
                    ),
                )
            )
        return [candidate for _, candidate in sorted(ranked, key=lambda item: item[0])]

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


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", "", value or "").upper()


def _same_gene_or_empty(candidate_gene: str, requested_gene: str) -> bool:
    return not requested_gene or candidate_gene.upper() == requested_gene.upper()


def _protein_position(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"p\.?[A-Za-z*()]*?(\d+)", value)
    return int(match.group(1)) if match else None


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
