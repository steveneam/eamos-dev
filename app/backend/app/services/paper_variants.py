"""Paper → variants: extract variant mentions from publication text, then resolve
each candidate.

Reuses Eamos assets rather than rebuilding:
- the gateway structured validate+repair substrate (`build_gateway_paper_variants_chain`
  → `extract_structured`) for live extraction;
- the curated search-input lexicon (`SearchInputReference`) for amino-acid
  normalization (1-/3-letter/full name) and known-gene validation — no hardcoded
  amino-acid table here;
- `EamosSearchInputResolver` as the cDNA/genomic identity gate;
- `SearchCandidateResolver` as the protein/source-backed candidate gate.

Protein-only mentions resolve only when a source-backed candidate exists. Protein
constructs without a source-backed allele remain explicit experimental constructs,
not coordinate-validated clinical variants. Mock-first; inert unless
`llm_provider == "gateway"`.
"""

from __future__ import annotations

import logging
import re
from collections import Counter

from app.agents.client import build_gateway_paper_variants_chain
from app.schemas.lookup import SearchInputCandidate, SearchInputSourceInputs
from app.schemas.paper_variants import (
    PaperVariantCandidate,
    PaperVariantsExtraction,
    PaperVariantsResult,
    ValidatedPaperVariant,
)
from app.services.search_candidate_resolver import SearchCandidateResolver
from app.services.search_input_reference import default_search_input_reference
from app.services.search_input_resolver import EamosSearchInputResolver, SearchInputResolution

logger = logging.getLogger(__name__)

_CDNA_RE = re.compile(r"c\.\d+[A-Za-z0-9>_+*\-]+")
_GENE_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}\b")
_PROTEIN_RE = re.compile(r"p\.[A-Za-z0-9*]+")
# Residue substitutions in single-letter (H241A) and three-letter (His241Ala)
# forms. Loose by design: SearchInputReference.amino_acid() validates each token,
# so non-amino-acid hits are dropped.
_PROTEIN_SUB1_RE = re.compile(r"\b([A-Z])(\d{2,4})([A-Z*])\b")
_PROTEIN_SUB3_RE = re.compile(r"\b([A-Za-z]{3})(\d{1,4})([A-Za-z]{3}|\*)\b")
_PROTEIN_LIKE_TOKEN_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY]\d{1,5}[ACDEFGHIKLMNPQRSTVWY*]?$")
_CONSTRUCT_HINTS = (
    "site-directed",
    "site directed",
    "mutagenesis",
    "we mutated",
    "substitut",
    "engineered",
    "replaced with",
    "alanine scan",
    "mutant",
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
    def __init__(
        self,
        settings,
        chain=None,
        validator=None,
        reference=None,
        input_resolver: EamosSearchInputResolver | None = None,
        candidate_resolver: SearchCandidateResolver | None = None,
    ) -> None:
        self.settings = settings
        self.chain = chain
        # Compatibility seam for older tests/callers. Phase 3 resolves through
        # EamosSearchInputResolver rather than calling VariantValidator here.
        self.validator = validator
        self.reference = reference or default_search_input_reference()
        self.input_resolver = input_resolver
        self.candidate_resolver = candidate_resolver or SearchCandidateResolver(settings=settings)

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
        tokens = [
            token
            for token in _GENE_RE.findall(text[max(0, pos - 120) : pos])
            if not _looks_like_protein_or_catalog_token(token)
        ]
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
        if candidate.transcript_hgvs:
            return self._resolve_cdna_or_genomic_candidate(candidate)
        if candidate.protein_change or candidate.protein_hgvs:
            return self._resolve_protein_candidate(candidate)
        return _ungated(candidate, status="missing")

    def _resolve_cdna_or_genomic_candidate(
        self,
        candidate: PaperVariantCandidate,
    ) -> ValidatedPaperVariant:
        try:
            resolution = self._search_input_resolver().resolve_text(
                candidate.transcript_hgvs or "",
                gene=candidate.gene,
                protein_change=candidate.protein_hgvs or candidate.protein_change,
            )
        except Exception as exc:  # resolver boundary - unvalidated, never crash
            logger.warning("paper variant search-input resolution failed", exc_info=True)
            return _ungated(candidate, status=f"resolver_failed:{type(exc).__name__}")

        exact_candidate = self.candidate_resolver.exact_candidate(resolution)
        if exact_candidate is not None:
            return _resolved_from_candidate(
                candidate,
                resolution=resolution,
                resolved=exact_candidate,
                status="resolved",
            )

        if resolution.genomic_hg38 or resolution.genomic_hgvs:
            return _resolved(
                candidate,
                validated=True,
                status="resolved",
                variant_id=resolution.genomic_hg38,
                genomic_hgvs=resolution.genomic_hgvs,
                source_inputs=_source_inputs_schema(resolution),
                resolver_warnings=list(resolution.warnings),
                resolver_provenance=["eamos_search_input_resolver", *resolution.provenance],
            )

        candidates = self.candidate_resolver.resolve_candidates(resolution)
        if candidates:
            return _ungated(
                candidate,
                status="candidates",
                source_inputs=_source_inputs_schema(resolution),
                candidates=candidates,
                resolver_warnings=list(resolution.warnings),
                resolver_provenance=["eamos_search_input_resolver", *resolution.provenance],
            )

        return _ungated(
            candidate,
            status="missing",
            source_inputs=_source_inputs_schema(resolution),
            resolver_warnings=list(resolution.warnings),
            resolver_provenance=["eamos_search_input_resolver", *resolution.provenance],
        )

    def _resolve_protein_candidate(
        self,
        candidate: PaperVariantCandidate,
    ) -> ValidatedPaperVariant:
        protein_hgvs = candidate.protein_hgvs or candidate.protein_change or ""
        try:
            resolution = self._search_input_resolver().resolve(
                gene=candidate.gene or "",
                cdna=protein_hgvs,
                protein_change=protein_hgvs,
            )
        except Exception as exc:  # resolver boundary - unvalidated, never crash
            logger.warning("paper protein search-input resolution failed", exc_info=True)
            return _ungated(candidate, status=f"resolver_failed:{type(exc).__name__}")

        candidates = self.candidate_resolver.resolve_candidates(resolution)
        high_confidence = [item for item in candidates if item.confidence == "high"]
        if (
            candidate.context != "experimental_construct"
            and len(candidates) == 1
            and len(high_confidence) == 1
        ):
            return _resolved_from_candidate(
                candidate,
                resolution=resolution,
                resolved=high_confidence[0],
                status="resolved",
            )

        status = "protein_only_unresolved"
        if candidates:
            status = "candidates"
        elif candidate.context == "experimental_construct":
            status = "experimental_construct"

        return _ungated(
            candidate,
            status=status,
            source_inputs=_source_inputs_schema(resolution),
            candidates=candidates,
            resolver_warnings=list(resolution.warnings),
            resolver_provenance=["eamos_search_input_resolver", "search_candidate_resolver"],
        )

    def _search_input_resolver(self) -> EamosSearchInputResolver:
        if self.input_resolver is None:
            self.input_resolver = EamosSearchInputResolver(
                settings=self.settings,
                resolve_coordinates=bool(getattr(self.settings, "use_real_apis", False)),
            )
        return self.input_resolver


def _resolved(
    candidate: PaperVariantCandidate,
    *,
    validated: bool,
    status: str,
    variant_id: str | None,
    genomic_hgvs: str | None,
    resolved_candidate_id: str | None = None,
    source_support: list[str] | None = None,
    source_inputs: SearchInputSourceInputs | None = None,
    candidates: list[SearchInputCandidate] | None = None,
    resolver_warnings: list[str] | None = None,
    resolver_provenance: list[str] | None = None,
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
        resolved_candidate_id=resolved_candidate_id,
        source_support=source_support or [],
        source_inputs=source_inputs,
        candidates=candidates or [],
        resolver_warnings=resolver_warnings or [],
        resolver_provenance=resolver_provenance or [],
    )


def _resolved_from_candidate(
    candidate: PaperVariantCandidate,
    *,
    resolution: SearchInputResolution,
    resolved: SearchInputCandidate,
    status: str,
) -> ValidatedPaperVariant:
    return _resolved(
        candidate,
        validated=True,
        status=status,
        variant_id=resolved.genomic_hg38 or resolved.candidate_id,
        genomic_hgvs=resolved.genomic_hgvs or resolution.genomic_hgvs,
        resolved_candidate_id=resolved.candidate_id,
        source_support=list(resolved.source_support),
        source_inputs=_source_inputs_schema(resolution),
        candidates=[resolved],
        resolver_warnings=list(resolution.warnings),
        resolver_provenance=[
            "eamos_search_input_resolver",
            "search_candidate_resolver",
            *resolution.provenance,
        ],
    )


def _ungated(
    candidate: PaperVariantCandidate,
    *,
    status: str = "not_validated",
    source_inputs: SearchInputSourceInputs | None = None,
    candidates: list[SearchInputCandidate] | None = None,
    resolver_warnings: list[str] | None = None,
    resolver_provenance: list[str] | None = None,
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
        source_inputs=source_inputs,
        candidates=candidates or [],
        resolver_warnings=resolver_warnings or [],
        resolver_provenance=resolver_provenance or [],
    )


def _source_inputs_schema(resolution: SearchInputResolution) -> SearchInputSourceInputs:
    source_inputs = resolution.source_inputs
    return SearchInputSourceInputs(
        variant_validator=source_inputs.variant_validator,
        ensembl_vep=source_inputs.ensembl_vep,
        gnomad=source_inputs.gnomad,
        spliceai=source_inputs.spliceai,
        clinvar=source_inputs.clinvar,
        literature_terms=list(source_inputs.literature_terms),
    )


def _looks_like_protein_or_catalog_token(token: str) -> bool:
    if _PROTEIN_LIKE_TOKEN_RE.match(token):
        return True
    digits = sum(1 for char in token if char.isdigit())
    return digits >= 3 and token[0] in "ACDEFGHIKLMNPQRSTVWY"
