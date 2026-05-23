from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GeneHint:
    gene: str
    phrase: str
    confidence: str
    source: str

    @property
    def assumption(self) -> str:
        return f"Mapped '{self.phrase}' to {self.gene} from curated search-input lexicon."


@dataclass(frozen=True)
class DiseaseGeneHint:
    phrase: str
    genes: tuple[str, ...]
    confidence: str
    source: str

    @property
    def is_ambiguous(self) -> bool:
        return len(self.genes) != 1

    @property
    def assumption(self) -> str:
        if self.is_ambiguous:
            choices = ", ".join(self.genes)
            return (
                f"Mapped '{self.phrase}' to multiple possible genes ({choices}) "
                "from curated search-input lexicon."
            )
        return f"Mapped '{self.phrase}' to {self.genes[0]} from curated search-input lexicon."


@dataclass(frozen=True)
class AminoAcidHint:
    name: str
    three_letter: str
    one_letter: str


@dataclass(frozen=True)
class ConsequenceHint:
    term: str
    suffix: str
    variant_class: str


@dataclass(frozen=True)
class TranscriptHint:
    gene: str
    transcript: str
    phrase: str
    source: str

    @property
    def assumption(self) -> str:
        return (
            f"Mapped '{self.phrase}' to {self.gene} transcript {self.transcript} "
            "from curated search-input lexicon."
        )


@dataclass(frozen=True)
class DisplayTerm:
    key: str
    display: str
    group: str | None = None
    description: str | None = None


class SearchInputReference:
    """Curated helper facts for search input parsing and AI extraction.

    This layer assists nomenclature handling. It is not a source of final
    variant identity and does not replace deterministic validation.
    """

    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.payload = payload or _search_input_lexicon()

    @property
    def known_gene_symbols(self) -> set[str]:
        return {str(item).upper() for item in self.payload.get("known_gene_symbols", [])}

    def match_gene_hint(self, text: str) -> GeneHint | None:
        lowered = text.lower()
        for entry in self.payload.get("gene_aliases", []):
            phrase = str(entry.get("phrase") or "").lower()
            gene = str(entry.get("gene") or "").upper()
            if not phrase or not gene or phrase not in lowered:
                continue
            return GeneHint(
                gene=gene,
                phrase=str(entry["phrase"]),
                confidence=str(entry.get("confidence") or "medium"),
                source=str(entry.get("source") or "curated_search_input_lexicon"),
            )
        return None

    def match_disease_gene_hint(self, text: str) -> DiseaseGeneHint | None:
        lowered = text.lower()
        for entry in self.payload.get("disease_gene_hints", []):
            phrase = str(entry.get("phrase") or "").lower()
            genes = tuple(str(gene).upper() for gene in entry.get("genes", []) if gene)
            if not phrase or phrase not in lowered or not genes:
                continue
            return DiseaseGeneHint(
                phrase=str(entry["phrase"]),
                genes=genes,
                confidence=str(entry.get("confidence") or "low"),
                source=str(entry.get("source") or "curated_search_input_lexicon"),
            )
        return None

    def amino_acid(self, token: str) -> AminoAcidHint | None:
        amino_acids = self.payload.get("amino_acids") or {}
        lowered = token.lower()
        if lowered in amino_acids:
            item = amino_acids[lowered]
            return AminoAcidHint(
                name=lowered,
                three_letter=str(item["three_letter"]),
                one_letter=str(item["one_letter"]),
            )

        for name, item in amino_acids.items():
            if (
                token.upper() == str(item.get("one_letter", "")).upper()
                or token.lower() == str(item.get("three_letter", "")).lower()
            ):
                return AminoAcidHint(
                    name=str(name),
                    three_letter=str(item["three_letter"]),
                    one_letter=str(item["one_letter"]),
                )
        return None

    def consequence(self, text: str) -> ConsequenceHint | None:
        lowered = text.lower()
        consequence_terms = self.payload.get("consequence_terms") or {}
        for term, item in sorted(
            consequence_terms.items(),
            key=lambda entry: len(str(entry[0])),
            reverse=True,
        ):
            if str(term).lower() not in lowered:
                continue
            return ConsequenceHint(
                term=str(term),
                suffix=str(item["suffix"]),
                variant_class=str(item["variant_class"]),
            )
        return None

    def normalize_chromosome(self, token: str) -> str | None:
        aliases = {
            str(alias).lower(): str(chromosome).upper()
            for alias, chromosome in (self.payload.get("chromosome_aliases") or {}).items()
        }
        cleaned = " ".join(token.strip().lower().split())
        if cleaned in aliases:
            return aliases[cleaned]
        cleaned = cleaned.removeprefix("chromosome ").removeprefix("chr")
        if cleaned in aliases:
            return aliases[cleaned]
        if cleaned in {"x", "y", "m", "mt"}:
            return "M" if cleaned == "mt" else cleaned.upper()
        if cleaned.isdigit() and 1 <= int(cleaned) <= 22:
            return cleaned
        return None

    def transcript_hint(self, gene: str, text: str = "") -> TranscriptHint | None:
        gene_key = gene.upper()
        entries = (self.payload.get("transcript_aliases") or {}).get(gene_key, [])
        lowered = text.lower()
        for entry in entries:
            phrases = [str(phrase).lower() for phrase in entry.get("phrases", [])]
            if lowered and phrases and not any(phrase in lowered for phrase in phrases):
                continue
            phrase = str((entry.get("phrases") or [gene_key])[0])
            return TranscriptHint(
                gene=gene_key,
                transcript=str(entry["transcript"]),
                phrase=phrase,
                source=str(entry.get("source") or "curated_search_input_lexicon"),
            )
        return None

    def clinical_significance(self, term: str) -> DisplayTerm | None:
        item = (self.payload.get("clinical_significance_terms") or {}).get(term.lower())
        if item is None:
            return None
        return DisplayTerm(
            key=term.lower(),
            display=str(item["display"]),
            group=str(item.get("group")) if item.get("group") else None,
            description=str(item.get("description")) if item.get("description") else None,
        )

    def acmg_criterion(self, code: str) -> DisplayTerm | None:
        normalized = code.upper()
        item = (self.payload.get("acmg_criteria") or {}).get(normalized)
        if item is None:
            return None
        return DisplayTerm(
            key=normalized,
            display=str(item.get("display") or normalized),
            group=str(item.get("group")) if item.get("group") else None,
            description=str(item.get("description")) if item.get("description") else None,
        )

    def amino_acid_names(self) -> list[str]:
        return sorted((self.payload.get("amino_acids") or {}).keys())

    def consequence_terms(self) -> list[str]:
        return sorted((self.payload.get("consequence_terms") or {}).keys())

    def reference_context(self) -> dict[str, Any]:
        return {
            "gene_aliases": self.payload.get("gene_aliases", []),
            "disease_gene_hints": self.payload.get("disease_gene_hints", []),
            "transcript_aliases": self.payload.get("transcript_aliases", {}),
            "chromosome_alias_examples": self.payload.get("chromosome_aliases", {}),
            "amino_acid_names": self.amino_acid_names(),
            "consequence_terms": self.consequence_terms(),
            "clinical_significance_terms": sorted(
                (self.payload.get("clinical_significance_terms") or {}).keys()
            ),
            "acmg_criteria": sorted((self.payload.get("acmg_criteria") or {}).keys()),
            "rules": [
                "Reference context supplies hints only.",
                "Do not infer final cDNA or genomic coordinates from protein-only text.",
                "Ambiguous or incomplete disease-only text should remain low confidence.",
                "Clinical significance and ACMG maps are display vocabulary, not classification logic.",
            ],
        }


@lru_cache(maxsize=1)
def _search_input_lexicon() -> dict[str, Any]:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "search_input_lexicon.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def default_search_input_reference() -> SearchInputReference:
    return SearchInputReference()
