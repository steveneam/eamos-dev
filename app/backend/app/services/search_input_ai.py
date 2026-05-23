from __future__ import annotations

import re
from dataclasses import dataclass

from app.agents.client import build_search_input_ai_chain
from app.schemas.lookup import SearchInputAiExtraction, SearchInputConfidence
from app.services.search_input_reference import (
    SearchInputReference,
    default_search_input_reference,
)


@dataclass(frozen=True)
class SearchInputAiResult:
    extraction: SearchInputAiExtraction | None = None
    warnings: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()


class SearchInputAiExtractor:
    """Optional plain-language extractor for search-input candidate intent.

    The extractor never finalizes an allele. It proposes structured intent that
    SearchInputInterpreter validates through deterministic parsing and
    source-backed candidate resolution.
    """

    def __init__(
        self,
        settings=None,
        chain=None,
        reference: SearchInputReference | None = None,
    ) -> None:
        self.settings = settings
        self.chain = chain
        self.reference = reference or default_search_input_reference()

    def extract(self, search_text: str, *, allow_ai: bool = True) -> SearchInputAiResult:
        if not allow_ai or not _ai_enabled(self.settings):
            return SearchInputAiResult()

        guardrail_warnings = _guardrail_warnings(search_text)
        if guardrail_warnings and not _has_variant_signal(search_text, self.reference):
            return SearchInputAiResult(
                warnings=guardrail_warnings,
                provenance=("search_input_ai_guardrail",),
            )

        if _use_mock(self.settings):
            return self._mock_extract(search_text, extra_warnings=guardrail_warnings)

        chain = self.chain or build_search_input_ai_chain(self.settings)
        if chain is None:
            return SearchInputAiResult(
                warnings=(*guardrail_warnings, "search_input_ai_unavailable"),
                provenance=("search_input_ai_extractor",),
            )

        try:
            payload = {
                "search_text": search_text,
                "reference_context": self.reference_context_json(),
            }
            extraction = SearchInputAiExtraction.model_validate(chain.invoke(payload))
        except Exception as exc:
            return SearchInputAiResult(
                warnings=(*guardrail_warnings, f"search_input_ai_failed:{type(exc).__name__}"),
                provenance=("live_search_input_ai_extractor",),
            )

        extraction_warnings = [*guardrail_warnings, *extraction.warnings]
        if extraction_warnings != extraction.warnings:
            extraction = extraction.model_copy(update={"warnings": extraction_warnings})
        return SearchInputAiResult(
            extraction=extraction,
            warnings=tuple(extraction_warnings),
            provenance=("live_search_input_ai_extractor", "curated_search_input_lexicon"),
        )

    def _mock_extract(
        self,
        search_text: str,
        *,
        extra_warnings: tuple[str, ...] = (),
    ) -> SearchInputAiResult:
        text = search_text.strip()
        warnings = list(extra_warnings)

        (
            gene,
            gene_alias,
            disease_context,
            gene_assumptions,
            gene_warnings,
        ) = _extract_gene_hint(
            text,
            self.reference,
        )
        warnings.extend(gene_warnings)
        cdna = _extract_cdna_hint(text)
        genomic_hint = _extract_genomic_hint(text)
        protein_change, variant_class, protein_assumptions = _extract_protein_hint(
            text,
            self.reference,
        )

        if not any((gene, cdna, genomic_hint, protein_change, disease_context)):
            return SearchInputAiResult(
                warnings=tuple(warnings),
                provenance=("mock_search_input_ai_extractor",),
            )

        assumptions = [*gene_assumptions, *protein_assumptions]
        if gene and not any((cdna, genomic_hint, protein_change)):
            warnings.append("variant_detail_missing")

        extraction = SearchInputAiExtraction(
            gene=gene,
            gene_alias=gene_alias,
            cdna=cdna,
            protein_change=protein_change,
            genomic_hint=genomic_hint,
            variant_class=variant_class,
            disease_context=disease_context,
            confidence=_confidence(
                gene=gene, cdna=cdna, genomic_hint=genomic_hint, protein=protein_change
            ),
            assumptions=assumptions,
            warnings=warnings,
        )
        provenance = ["mock_search_input_ai_extractor"]
        if gene_alias or protein_assumptions:
            provenance.append("curated_search_input_lexicon")
        return SearchInputAiResult(
            extraction=extraction,
            warnings=tuple(warnings),
            provenance=tuple(provenance),
        )

    def reference_context_json(self) -> str:
        import json

        return json.dumps(self.reference.reference_context(), sort_keys=True)


def _ai_enabled(settings) -> bool:
    return bool(settings is not None and getattr(settings, "search_input_ai_enabled", False))


def _use_mock(settings) -> bool:
    return bool(settings is None or getattr(settings, "llm_provider", "mock") == "mock")


def _guardrail_warnings(search_text: str) -> tuple[str, ...]:
    lowered = search_text.lower()
    if any(
        phrase in lowered
        for phrase in (
            "ignore previous instructions",
            "ignore your previous instructions",
            "forget previous instructions",
            "change your role",
            "reveal your prompt",
            "system prompt",
        )
    ):
        return ("prompt_injection_phrase_ignored",)
    return ()


def _has_variant_signal(text: str, reference: SearchInputReference) -> bool:
    if _extract_cdna_hint(text) or _extract_genomic_hint(text):
        return True
    if _extract_protein_hint(text, reference)[0]:
        return True
    gene, _alias, disease_context, _assumptions, _warnings = _extract_gene_hint(
        text,
        reference,
    )
    return bool(gene or disease_context)


def _extract_gene_hint(
    text: str,
    reference: SearchInputReference,
) -> tuple[str | None, str | None, str | None, list[str], list[str]]:
    for match in re.finditer(r"\b[A-Z][A-Z0-9-]{2,}\b", text):
        symbol = match.group(0).upper()
        if symbol in reference.known_gene_symbols:
            return symbol, None, None, [], []

    hint = reference.match_gene_hint(text)
    if hint is not None:
        return hint.gene, hint.phrase, hint.phrase, [hint.assumption], []

    disease_hint = reference.match_disease_gene_hint(text)
    if disease_hint is not None:
        if disease_hint.is_ambiguous:
            return (
                None,
                disease_hint.phrase,
                disease_hint.phrase,
                [disease_hint.assumption],
                [f"ambiguous_gene_hint:{disease_hint.phrase}"],
            )
        return (
            disease_hint.genes[0],
            disease_hint.phrase,
            disease_hint.phrase,
            [disease_hint.assumption],
            [],
        )

    return None, None, None, [], []


def _extract_cdna_hint(text: str) -> str | None:
    hgvs_match = re.search(r"\bc\.\s*\d+[A-Za-z0-9_+*\->]+", text, flags=re.IGNORECASE)
    if hgvs_match is not None:
        return re.sub(r"\s+", "", hgvs_match.group(0))

    spoken_snv = re.search(
        r"\bc\.?\s*(?P<pos>\d+)\s*(?P<ref>[ACGT])\s*(?:>|to)\s*(?P<alt>[ACGT])\b",
        text,
        flags=re.IGNORECASE,
    )
    if spoken_snv is None:
        return None
    return (
        f"c.{spoken_snv.group('pos')}"
        f"{spoken_snv.group('ref').upper()}>{spoken_snv.group('alt').upper()}"
    )


def _extract_genomic_hint(text: str) -> str | None:
    match = re.search(
        r"\b(?:chr)?(?:\d+|X|Y|M|MT)[-:]\d+[-:][ACGT]+[-:][ACGT]+\b",
        text,
        flags=re.IGNORECASE,
    )
    if match is not None:
        return match.group(0)

    refseq = re.search(
        r"\bNC_\d{6}\.\d+:g\.[A-Za-z0-9_+*\->]+\b",
        text,
        flags=re.IGNORECASE,
    )
    return refseq.group(0) if refseq is not None else None


def _extract_protein_hint(
    text: str,
    reference: SearchInputReference,
) -> tuple[str | None, str, list[str]]:
    explicit = re.search(
        r"\bp\.?\(?(?P<ref>[A-Za-z]{1,3})(?P<pos>\d+)(?P<alt>[A-Za-z*]{1,3}|fs|del|dup)?\)?",
        text,
        flags=re.IGNORECASE,
    )
    if explicit is not None:
        ref = _normalize_amino_acid_token(explicit.group("ref"), reference)
        alt = explicit.group("alt") or ""
        variant_class = _variant_class_from_suffix(alt)
        suffix = _normalize_protein_suffix(alt)
        return f"p.{ref}{explicit.group('pos')}{suffix}", variant_class, []

    lowered = text.lower()
    matched_consequence = reference.consequence(lowered)
    for name in sorted(reference.amino_acid_names(), key=len, reverse=True):
        name_pattern = re.escape(name.lower())
        match = re.search(rf"\b{name_pattern}\s*(?P<pos>\d+)\b", lowered)
        if match is None:
            continue
        if matched_consequence is None:
            return None, "unknown", []
        amino = reference.amino_acid(name)
        if amino is None:
            return None, "unknown", []
        three_letter = amino.three_letter
        suffix = matched_consequence.suffix
        variant_class = matched_consequence.variant_class
        assumption = (
            f"Converted amino-acid name {name} to HGVS protein code {three_letter} "
            "using curated search-input lexicon."
        )
        return f"p.{three_letter}{match.group('pos')}{suffix}", variant_class, [assumption]

    return None, "unknown", []


def _normalize_amino_acid_token(token: str, reference: SearchInputReference) -> str:
    amino = reference.amino_acid(token)
    if amino is not None:
        return amino.three_letter
    return token[:1].upper() + token[1:].lower()


def _normalize_protein_suffix(suffix: str) -> str:
    if not suffix:
        return ""
    lowered = suffix.lower()
    if lowered == "ter":
        return "Ter"
    if lowered in {"fs", "del", "dup"}:
        return lowered
    if suffix == "*":
        return "Ter"
    return suffix[:1].upper() + suffix[1:].lower()


def _variant_class_from_suffix(suffix: str) -> str:
    lowered = suffix.lower()
    if lowered == "fs":
        return "frameshift"
    if lowered == "del":
        return "deletion"
    if lowered == "dup":
        return "duplication"
    if lowered in {"*", "ter"}:
        return "nonsense"
    return "unknown"


def _confidence(
    *,
    gene: str | None,
    cdna: str | None,
    genomic_hint: str | None,
    protein: str | None,
) -> SearchInputConfidence:
    if gene and any((cdna, genomic_hint, protein)):
        return "high"
    if gene or any((cdna, genomic_hint, protein)):
        return "medium"
    return "low"
