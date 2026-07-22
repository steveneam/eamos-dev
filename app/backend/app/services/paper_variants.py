"""Deterministic Paper → Variants extraction followed by a separate resolver gate.

L1-L3 mention extraction is always local and input-bound. A configured gateway
or injected chain cannot replace, delete, or canonically resolve deterministic
evidence; optional L4 adjudication remains a separately consented future path.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache

from app.schemas.capabilities import CapabilityExecutionDisclosureV2
from app.schemas.lookup import SearchInputCandidate, SearchInputSourceInputs
from app.schemas.paper_variants import (
    PaperDocumentExtractionV2,
    PaperMentionResolutionV2,
    PaperSourceMetadata,
    PaperVariantCandidate,
    PaperVariantsResult,
    ValidatedPaperVariant,
)
from app.schemas.workflow import CanonicalVariantRefV1
from app.services.paper_extract.document import PaperInputDocument, text_document
from app.services.paper_extract.grammar import DetectedMention
from app.services.paper_extract.metadata import legacy_source_metadata
from app.services.paper_extract.pipeline import build_extraction_draft
from app.services.search_candidate_resolver import SearchCandidateResolver
from app.services.search_input_reference import default_search_input_reference
from app.services.search_input_resolver import EamosSearchInputResolver, SearchInputResolution

logger = logging.getLogger(__name__)

_NON_ACTIONABLE_CONTEXTS = {
    "ambiguous",
    "experimental_construct",
    "engineered_rescue",
    "comparator_or_background",
}


@dataclass(frozen=True, slots=True)
class PaperDocumentRunResult:
    result: PaperVariantsResult
    document_extraction: PaperDocumentExtractionV2
    source_metadata: PaperSourceMetadata | None


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
        self.last_document_run: PaperDocumentRunResult | None = None

    def extract(
        self,
        paper_text: str | PaperInputDocument,
        *,
        validate: bool = True,
    ) -> PaperVariantsResult:
        document = (
            paper_text if isinstance(paper_text, PaperInputDocument) else text_document(paper_text)
        )
        run = self.extract_document(document, validate=validate)
        self.last_document_run = run
        return run.result

    def extract_document(
        self,
        document: PaperInputDocument,
        *,
        supplements: tuple[PaperInputDocument, ...] = (),
        validate: bool = True,
    ) -> PaperDocumentRunResult:
        draft = build_extraction_draft((document, *supplements))
        variants: list[ValidatedPaperVariant] = []
        resolutions: list[PaperMentionResolutionV2] = []
        for record in draft.records:
            candidate = self._candidate_from_record(record)
            if record.mention.biological_context == "bibliography_only":
                variant = _ungated(candidate, status="bibliography_only_excluded")
            elif validate:
                variant = self._gate(candidate)
            else:
                variant = _ungated(candidate)
            variants.append(variant)
            resolutions.append(_resolution_for_record(record, variant=variant, validate=validate))

        result = PaperVariantsResult(
            variants=variants,
            warnings=list(draft.warnings),
            provenance=["eamos_paper_extract_l1_l3"],
        )
        extraction = draft.finalize(resolutions)
        main_metadata = next(
            (
                row.bibliographic_metadata
                for row in extraction.bundle.documents
                if row.role == "main"
            ),
            None,
        )
        return PaperDocumentRunResult(
            result=result,
            document_extraction=extraction,
            source_metadata=legacy_source_metadata(main_metadata),
        )

    # -- candidate extraction ---------------------------------------------

    def _candidate_from_record(self, record: DetectedMention) -> PaperVariantCandidate:
        mention = record.mention
        gene = mention.gene_evidence[0] if mention.gene_evidence else None
        notation = record.canonical_notation
        protein_hgvs: str | None = None
        transcript_hgvs: str | None = None
        if mention.notation_type == "protein":
            protein_hgvs = notation
        elif mention.notation_type == "legacy" and not notation.upper().startswith("IVS"):
            legacy = re.fullmatch(r"([A-Za-z]{1,3})([0-9]{1,5})([A-Za-z*]{1,3})", notation)
            if legacy:
                protein_hgvs = self._normalize_residue(*legacy.groups())
        else:
            transcript_hgvs = notation
        return PaperVariantCandidate(
            gene=gene,
            transcript_hgvs=transcript_hgvs,
            protein_change=protein_hgvs,
            protein_hgvs=protein_hgvs,
            level=mention.notation_type,
            context=mention.biological_context,
            # The V2 evidence graph owns the bounded quote. The compatibility
            # row deliberately carries no publication text.
            evidence_quote=None,
        )

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

    # -- resolution gate --------------------------------------------------

    def _gate(self, candidate: PaperVariantCandidate) -> ValidatedPaperVariant:
        if candidate.context == "bibliography_only":
            return _ungated(candidate, status="bibliography_only_excluded")
        if candidate.transcript_hgvs:
            resolved = self._resolve_cdna_or_genomic_candidate(candidate)
        elif candidate.protein_change or candidate.protein_hgvs:
            resolved = self._resolve_protein_candidate(candidate)
        else:
            return _ungated(candidate, status="missing")
        if candidate.context in _NON_ACTIONABLE_CONTEXTS:
            status = f"{candidate.context}_non_actionable"
            if "fixture_source_unavailable" in resolved.validation_status:
                status = f"{candidate.context}_fixture_source_unavailable"
            return resolved.model_copy(
                update={
                    "validated": False,
                    "validation_status": status,
                    "variant_id": None,
                    "genomic_hgvs": None,
                    "resolved_candidate_id": None,
                    "source_support": [],
                }
            )
        return resolved

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
            logger.warning(
                "paper variant search-input resolution failed (error_type=%s)",
                type(exc).__name__,
            )
            return _ungated(candidate, status=f"resolver_failed:{type(exc).__name__}")

        exact_candidate = self.candidate_resolver.exact_candidate(resolution)
        if exact_candidate is not None:
            if self._is_fixture_candidate(exact_candidate):
                if not _coordinate_source_support(resolution):
                    return _ungated(
                        candidate,
                        status="fixture_source_unavailable",
                        resolver_warnings=["fixture_candidate_blocked"],
                        resolver_provenance=[
                            "eamos_search_input_resolver",
                            "fixture_candidate_blocked",
                        ],
                    )
            else:
                if not _candidate_has_source_support(exact_candidate):
                    return _ungated(
                        candidate,
                        status="source_verification_required",
                        source_inputs=_source_inputs_schema(resolution),
                        resolver_warnings=list(resolution.warnings),
                        resolver_provenance=[
                            "eamos_search_input_resolver",
                            "candidate_source_support_missing",
                            *resolution.provenance,
                        ],
                    )
                return _resolved_from_candidate(
                    candidate,
                    resolution=resolution,
                    resolved=exact_candidate,
                    status="resolved",
                )

        if resolution.genomic_hg38 or resolution.genomic_hgvs:
            source_support = _coordinate_source_support(resolution)
            if not source_support:
                return _ungated(
                    candidate,
                    status="source_verification_required",
                    source_inputs=_source_inputs_schema(resolution),
                    resolver_warnings=list(resolution.warnings),
                    resolver_provenance=[
                        "eamos_search_input_resolver",
                        *resolution.provenance,
                    ],
                )
            return _resolved(
                candidate,
                validated=True,
                status="resolved",
                variant_id=resolution.genomic_hg38,
                genomic_hgvs=resolution.genomic_hgvs,
                resolved_candidate_id=f"coordinate:{resolution.genomic_hg38 or resolution.genomic_hgvs}",
                source_support=source_support,
                source_inputs=_source_inputs_schema(resolution),
                resolver_warnings=list(resolution.warnings),
                resolver_provenance=["eamos_search_input_resolver", *resolution.provenance],
            )

        candidates = [
            item
            for item in self.candidate_resolver.resolve_candidates(resolution)
            if not self._is_fixture_candidate(item)
        ]
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
            logger.warning(
                "paper protein search-input resolution failed (error_type=%s)",
                type(exc).__name__,
            )
            return _ungated(candidate, status=f"resolver_failed:{type(exc).__name__}")

        all_candidates = self.candidate_resolver.resolve_candidates(resolution)
        candidates = [item for item in all_candidates if not self._is_fixture_candidate(item)]
        high_confidence = [
            item
            for item in candidates
            if item.confidence == "high" and _candidate_has_source_support(item)
        ]
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
        if (
            len(candidates) == 1
            and candidates[0].confidence == "high"
            and not _candidate_has_source_support(candidates[0])
        ):
            status = "source_verification_required"
        elif candidates:
            status = "candidates"
        elif all_candidates and not candidates:
            status = "fixture_source_unavailable"
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

    def _is_fixture_candidate(self, candidate: SearchInputCandidate) -> bool:
        return candidate.candidate_id in _default_fixture_candidate_ids()

    def _search_input_resolver(self) -> EamosSearchInputResolver:
        if self.input_resolver is None:
            self.input_resolver = EamosSearchInputResolver(
                # Paper L1-L3 is an offline capability. Composition may inject an
                # approved source-backed/local resolver, but generic runtime API
                # flags must never silently transmit publication-derived input.
                settings=None,
                resolve_coordinates=False,
            )
        return self.input_resolver


def _resolution_for_record(
    record: DetectedMention,
    *,
    variant: ValidatedPaperVariant,
    validate: bool,
) -> PaperMentionResolutionV2:
    mention = record.mention
    if mention.biological_context == "bibliography_only":
        disclosure = CapabilityExecutionDisclosureV2(
            capability_id="paper_allele_resolution",
            claim="Resolve one deterministic publication mention to a source-backed allele.",
            execution="unavailable",
            input_scope=f"mention:{mention.mention_id}",
            source_status="not_applicable",
            applicability="not_applicable",
            validation_status="not_applicable",
            retention="request_lifetime",
            consent_required=False,
            warnings=["bibliography_only_mentions_are_not_actionable"],
            requirements=[],
        )
        return PaperMentionResolutionV2(
            mention_id=mention.mention_id,
            status="excluded",
            canonical_variant=None,
            candidate_ids=[],
            execution_disclosure=disclosure,
            warnings=["Bibliography-only mention excluded from candidate resolution."],
        )

    candidate_ids = _opaque_candidate_ids(variant)
    canonical = _canonical_variant(record, variant)
    if variant.validated and canonical is not None:
        source_ids = _opaque_source_ids(variant)
        disclosure = _resolution_disclosure(
            mention_id=mention.mention_id,
            source_status="source_backed",
            source_record_ids=source_ids,
            validation_status="validated",
        )
        resolved_id = _opaque_id(
            variant.resolved_candidate_id or variant.variant_id or mention.mention_id
        )
        return PaperMentionResolutionV2(
            mention_id=mention.mention_id,
            status="resolved",
            canonical_variant=canonical,
            candidate_ids=[resolved_id],
            execution_disclosure=disclosure,
            warnings=[],
        )

    if (
        "fixture_source_unavailable" in variant.validation_status
        or variant.validation_status == "source_verification_required"
    ):
        disclosure = CapabilityExecutionDisclosureV2(
            capability_id="paper_allele_resolution",
            claim="Resolve one deterministic publication mention to a source-backed allele.",
            execution="unavailable",
            input_scope=f"mention:{mention.mention_id}",
            source_status="unavailable",
            applicability="applicable",
            validation_status="unvalidated",
            retention="request_lifetime",
            consent_required=False,
            warnings=[variant.validation_status],
            requirements=["source_backed_allele_resolver_or_mounted_artifact"],
        )
        return PaperMentionResolutionV2(
            mention_id=mention.mention_id,
            status="unresolved",
            canonical_variant=None,
            candidate_ids=[],
            execution_disclosure=disclosure,
            warnings=["Illustrative or unverified resolver data cannot enable actions."],
        )

    if not validate:
        disclosure = CapabilityExecutionDisclosureV2(
            capability_id="paper_allele_resolution",
            claim="Resolve one deterministic publication mention to a source-backed allele.",
            execution="unavailable",
            input_scope=f"mention:{mention.mention_id}",
            source_status="unavailable",
            applicability="applicable",
            validation_status="unvalidated",
            retention="request_lifetime",
            consent_required=False,
            warnings=[],
            requirements=["enable_source_backed_allele_resolution"],
        )
        status = "ambiguous" if candidate_ids else "unresolved"
    else:
        failed = variant.validation_status.startswith("resolver_failed:")
        disclosure = _resolution_disclosure(
            mention_id=mention.mention_id,
            source_status=(
                "unavailable" if failed else ("source_backed" if candidate_ids else "not_found")
            ),
            source_record_ids=candidate_ids,
            validation_status="failed" if failed else "unvalidated",
            warnings=[variant.validation_status] if failed else [],
        )
        status = "ambiguous" if candidate_ids else "unresolved"
    context_warning = (
        [f"{mention.biological_context}_mention_is_not_a_clinical_allele"]
        if mention.biological_context in _NON_ACTIONABLE_CONTEXTS
        else []
    )
    return PaperMentionResolutionV2(
        mention_id=mention.mention_id,
        status=status,
        canonical_variant=None,
        candidate_ids=candidate_ids,
        execution_disclosure=disclosure,
        warnings=context_warning,
    )


def _resolution_disclosure(
    *,
    mention_id: str,
    source_status: str,
    source_record_ids: list[str],
    validation_status: str,
    warnings: list[str] | None = None,
) -> CapabilityExecutionDisclosureV2:
    return CapabilityExecutionDisclosureV2(
        capability_id="paper_allele_resolution",
        claim="Resolve one deterministic publication mention to a source-backed allele.",
        execution="eamos_local",
        algorithm_id="eamos_search_input_resolver",
        algorithm_version="2.0.0",
        input_scope=f"mention:{mention_id}",
        source_status=source_status,
        source_record_ids=source_record_ids,
        applicability="applicable",
        validation_status=validation_status,
        validation_matrix_id="paper-resolution-v2",
        retention="request_lifetime",
        consent_required=False,
        warnings=warnings or [],
        requirements=[],
    )


def _canonical_variant(
    record: DetectedMention,
    variant: ValidatedPaperVariant,
) -> CanonicalVariantRefV1 | None:
    selected = variant.candidates[0] if len(variant.candidates) == 1 else None
    gene = (selected.gene if selected else None) or variant.gene
    cdna = (selected.cdna if selected else None) or variant.transcript_hgvs
    transcript = (selected.transcript if selected else None) or (
        record.mention.transcript_evidence[0] if record.mention.transcript_evidence else None
    )
    if cdna and ":" in cdna:
        prefix, cdna = cdna.split(":", 1)
        transcript = transcript or re.sub(r"\([A-Z][A-Z0-9-]{1,14}\)$", "", prefix)
    if not gene or not cdna or not variant.variant_id or not variant.source_support:
        return None
    protein = (selected.protein_change if selected else None) or variant.protein_hgvs
    genomic_hg38 = (selected.genomic_hg38 if selected else None) or variant.variant_id
    return CanonicalVariantRefV1(
        schema_version="canonical_variant_ref.v1",
        gene=gene,
        cdna=cdna,
        transcript=transcript,
        protein_hgvs=protein,
        genomic_hg38=genomic_hg38,
        variant_key=variant.variant_id,
        species="human",
        genome_build="GRCh38",
        resolution_status="resolved",
        source_support=list(dict.fromkeys(variant.source_support)),
        warnings=[],
    )


def _opaque_candidate_ids(variant: ValidatedPaperVariant) -> list[str]:
    values = [candidate.candidate_id for candidate in variant.candidates]
    if variant.resolved_candidate_id:
        values.append(variant.resolved_candidate_id)
    return list(dict.fromkeys(_opaque_id(value) for value in values))[:32]


def _opaque_source_ids(variant: ValidatedPaperVariant) -> list[str]:
    values = [*variant.source_support]
    if variant.resolved_candidate_id:
        values.append(variant.resolved_candidate_id)
    if variant.variant_id:
        values.append(variant.variant_id)
    return list(dict.fromkeys(_opaque_id(value, prefix="source") for value in values))[:128]


def _opaque_id(value: str, *, prefix: str = "candidate") -> str:
    import hashlib

    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


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


def _coordinate_source_support(resolution: SearchInputResolution) -> list[str]:
    support: list[str] = []
    if "eamos_local_coordinate_resolver" in resolution.provenance:
        support.append("Eamos local transcript-coordinate resolver")
    if "variant_validator_grch38_vcf" in resolution.provenance:
        support.append("VariantValidator GRCh38 coordinate response")
    return support


def _candidate_has_source_support(candidate: SearchInputCandidate) -> bool:
    return bool(candidate.source_support) and candidate.source_count > 0


@lru_cache(maxsize=1)
def _default_fixture_candidate_ids() -> frozenset[str]:
    return frozenset(
        record.candidate_id for record in SearchCandidateResolver(settings=None).records
    )
