"""Paper → variants: extract variant mentions from publication text, then resolve
each candidate.

Reuses Eamos assets rather than rebuilding:
- the gateway structured validate+repair substrate (`build_gateway_paper_variants_chain`
  → `extract_structured`) for live extraction;
- the curated search-input lexicon (`SearchInputReference`) for amino-acid
  normalization (1-/3-letter/full name) and known-gene validation — no hardcoded
  amino-acid table here;
- `VariantValidatorTool` as the cDNA/genomic coordinate gate (fixture-backed
  offline, REST when `use_real_apis`).

Protein-only mentions are surfaced as `protein_only_unresolved` here; Phase 3
routes them through source-backed candidate resolution (see
docs/ai-gateway-paper-variants/spec.md). Mock-first; inert unless
`llm_provider == "gateway"`.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from types import SimpleNamespace

from app.agents.client import build_gateway_paper_variants_chain
from app.schemas.paper_variants import (
    PaperVariantCandidate,
    PaperVariantsExtraction,
    PaperVariantsResult,
    ValidatedPaperVariant,
)
from app.services.search_input_reference import default_search_input_reference
from app.tools.variant_validator import VariantValidatorTool

logger = logging.getLogger(__name__)

_VALIDATED_STATUSES = {"fixture", "live"}
_CDNA_RE = re.compile(r"c\.\d+[A-Za-z0-9>_+*\-]+")
_GENE_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}\b")
_PROTEIN_RE = re.compile(r"p\.[A-Za-z0-9*]+")
# Residue substitutions in single-letter (H241A) and three-letter (His241Ala)
# forms. Loose by design: SearchInputReference.amino_acid() validates each token,
# so non-amino-acid hits are dropped.
_PROTEIN_SUB1_RE = re.compile(r"\b([A-Z])(\d{2,4})([A-Z*])\b")
_PROTEIN_SUB3_RE = re.compile(r"\b([A-Za-z]{3})(\d{1,4})([A-Za-z]{3}|\*)\b")
_CONSTRUCT_HINTS = (
    "site-directed",
    "site directed",
    "mutagenesis",
    "we mutated",
    "substitut",
    "engineered",
    "replaced with",
    "alanine scan",
)
_CLINICAL_HINTS = (
    "patient",
    "proband",
    "carrier",
    "homozygous",
    "compound heterozygous",
    "diagnosed",
    "family",
)


class PaperVariantsService:
    def __init__(self, settings, chain=None, validator=None, reference=None) -> None:
        self.settings = settings
        self.chain = chain
        self.validator = validator
        self.reference = reference or default_search_input_reference()

    def extract(self, paper_text: str, *, validate: bool = True) -> PaperVariantsResult:
        extraction, warnings, provenance = self._candidates(paper_text)
        variants = [
            self._gate(candidate) if validate else _ungated(candidate)
            for candidate in extraction.variants
        ]
        return PaperVariantsResult(
            variants=variants, warnings=warnings, provenance=list(provenance)
        )

    # -- candidate extraction ---------------------------------------------

    def _candidates(
        self, paper_text: str
    ) -> tuple[PaperVariantsExtraction, list[str], tuple[str, ...]]:
        if getattr(self.settings, "llm_provider", "mock") == "mock":
            return self._mock_extract(paper_text), [], ("mock_paper_variants_extractor",)

        chain = self.chain or build_gateway_paper_variants_chain(self.settings)
        if chain is None:
            return (
                PaperVariantsExtraction(),
                ["paper_variants_unavailable"],
                ("paper_variants_extractor",),
            )
        try:
            extraction = PaperVariantsExtraction.model_validate(
                chain.invoke({"paper_text": paper_text})
            )
        except Exception as exc:  # provider/parse boundary — never crash a request
            logger.warning("paper variants extraction failed", exc_info=True)
            return (
                PaperVariantsExtraction(),
                [f"paper_variants_failed:{type(exc).__name__}"],
                ("live_paper_variants_extractor",),
            )
        return extraction, [], ("live_paper_variants_extractor",)

    def _mock_extract(self, paper_text: str) -> PaperVariantsExtraction:
        """Deterministic offline extractor: cDNA mentions plus single-/three-letter
        protein substitutions, normalized + validated via the curated lexicon, each
        tied to the nearest known gene. Best-effort for dev/tests — the gateway LLM is
        the production extractor."""
        context = self._context_hint(paper_text)
        dominant = self._dominant_gene(paper_text)
        candidates: list[PaperVariantCandidate] = []
        seen_protein: set[str] = set()

        for match in _CDNA_RE.finditer(paper_text):
            window = paper_text[match.start() : match.start() + 80]
            protein = _PROTEIN_RE.search(window)
            protein_hgvs = protein.group(0) if protein else None
            candidates.append(
                PaperVariantCandidate(
                    gene=self._gene_near(paper_text, match.start(), dominant),
                    transcript_hgvs=match.group(0),
                    protein_change=protein_hgvs,
                    protein_hgvs=protein_hgvs,
                    level="cdna",
                    context=context,
                )
            )
            if protein_hgvs:
                seen_protein.add(protein_hgvs)

        for regex in (_PROTEIN_SUB1_RE, _PROTEIN_SUB3_RE):
            for match in regex.finditer(paper_text):
                normalized = self._normalize_residue(*match.groups())
                if normalized is None or normalized in seen_protein:
                    continue
                seen_protein.add(normalized)
                candidates.append(
                    PaperVariantCandidate(
                        gene=self._gene_near(paper_text, match.start(), dominant),
                        protein_change=match.group(0),
                        protein_hgvs=normalized,
                        level="protein",
                        context=context,
                    )
                )
        return PaperVariantsExtraction(variants=candidates)

    def _normalize_residue(self, ref: str, pos: str, alt: str) -> str | None:
        """Normalize a residue substitution to HGVS p. form via the curated lexicon.
        Returns None when either token is not a known amino acid (drops false hits)."""
        ref_aa = self.reference.amino_acid(ref)
        if ref_aa is None:
            return None
        if alt in ("*", "Ter", "ter"):
            alt3: str | None = "Ter"
        else:
            alt_aa = self.reference.amino_acid(alt)
            alt3 = alt_aa.three_letter if alt_aa else None
        if alt3 is None:
            return None
        return f"p.{ref_aa.three_letter}{pos}{alt3}"

    @staticmethod
    def _gene_near(text: str, pos: int, fallback: str | None) -> str | None:
        # Gene-agnostic: nearest preceding gene-like symbol, no curated allowlist.
        # Downstream coordinate/candidate resolution is MANE/RefSeq-backed and works
        # for any gene, so the extractor must not be limited to a fixed gene set.
        tokens = _GENE_RE.findall(text[max(0, pos - 120) : pos])
        return tokens[-1] if tokens else fallback

    @staticmethod
    def _dominant_gene(text: str) -> str | None:
        tokens = _GENE_RE.findall(text)
        return Counter(tokens).most_common(1)[0][0] if tokens else None

    @staticmethod
    def _context_hint(text: str) -> str:
        low = text.lower()
        if any(hint in low for hint in _CONSTRUCT_HINTS):
            return "experimental_construct"
        if any(hint in low for hint in _CLINICAL_HINTS):
            return "clinical_allele"
        return "unknown"

    # -- resolution gate --------------------------------------------------

    def _gate(self, candidate: PaperVariantCandidate) -> ValidatedPaperVariant:
        # cDNA/genomic candidates: coordinate-validate via VariantValidator. (The
        # tiered resolver-stack gate is Phase 3 — docs/ai-gateway-paper-variants.)
        if candidate.gene and candidate.transcript_hgvs:
            validator = self.validator or VariantValidatorTool(self.settings)
            probe = SimpleNamespace(gene=candidate.gene, transcript_hgvs=candidate.transcript_hgvs)
            try:
                result = validator.get_evidence(probe)
            except Exception as exc:  # tool boundary — unvalidated, never crash
                logger.warning("variant validator gate failed", exc_info=True)
                return _ungated(candidate, status=f"validator_failed:{type(exc).__name__}")
            summary = result.summary or {}
            variant_id = summary.get("variant_id")
            validated = result.status in _VALIDATED_STATUSES and bool(variant_id)
            return _resolved(
                candidate,
                validated=validated,
                status=result.status,
                variant_id=variant_id if validated else None,
                genomic_hgvs=summary.get("hgvs_genomic_description") if validated else None,
            )
        # protein-only mentions can't be coordinate-validated here; Phase 3 routes
        # them through source-backed candidate resolution.
        if candidate.protein_change or candidate.protein_hgvs:
            return _ungated(candidate, status="protein_only_unresolved")
        return _ungated(candidate, status="insufficient_identity")


def _resolved(
    candidate: PaperVariantCandidate,
    *,
    validated: bool,
    status: str,
    variant_id: str | None,
    genomic_hgvs: str | None,
) -> ValidatedPaperVariant:
    return ValidatedPaperVariant(
        gene=candidate.gene,
        transcript_hgvs=candidate.transcript_hgvs,
        protein_change=candidate.protein_change,
        protein_hgvs=candidate.protein_hgvs,
        level=candidate.level,
        context=candidate.context,
        evidence_quote=candidate.evidence_quote,
        validated=validated,
        validation_status=status,
        variant_id=variant_id,
        genomic_hgvs=genomic_hgvs,
    )


def _ungated(
    candidate: PaperVariantCandidate, *, status: str = "not_validated"
) -> ValidatedPaperVariant:
    return ValidatedPaperVariant(
        gene=candidate.gene,
        transcript_hgvs=candidate.transcript_hgvs,
        protein_change=candidate.protein_change,
        protein_hgvs=candidate.protein_hgvs,
        level=candidate.level,
        context=candidate.context,
        evidence_quote=candidate.evidence_quote,
        validated=False,
        validation_status=status,
    )
