from __future__ import annotations

from dataclasses import replace

from app.schemas.lookup import (
    SearchInputAiExtraction,
    SearchInputCandidate,
    SearchInputInterpretation,
    SearchInputSourceInputs,
)
from app.services.search_input_ai import SearchInputAiExtractor
from app.services.search_candidate_resolver import SearchCandidateResolver
from app.services.search_input_resolver import (
    EamosSearchInputResolver,
    SearchInputResolution,
    SourceSpecificInputs,
)


class SearchInputInterpreter:
    """Turn raw search text into an auditable backend interpretation."""

    def __init__(
        self,
        settings=None,
        *,
        candidate_resolver: SearchCandidateResolver | None = None,
        ai_extractor: SearchInputAiExtractor | None = None,
    ) -> None:
        self.settings = settings
        self.candidate_resolver = candidate_resolver or SearchCandidateResolver()
        self.ai_extractor = ai_extractor or SearchInputAiExtractor(settings=settings)
        self.resolver = EamosSearchInputResolver(settings=settings)

    def interpret(
        self,
        search_text: str,
        *,
        species: str = "human",
        allow_ai: bool = True,
        resolve_coordinates: bool = False,
    ) -> SearchInputInterpretation:
        text = search_text.strip()
        resolver = self._resolver(resolve_coordinates=resolve_coordinates)
        resolution = resolver.resolve_text(text)

        if species.lower() != "human":
            return self._suggestions(
                submitted_text=text,
                resolution=resolution,
                ui_prompt="Use a human GRCh38 variant for the Variant Evidence Report.",
                warnings=["species_not_supported_for_search_input"],
            )

        if resolution.kind == "unknown":
            ai_interpretation, ai_warnings = self._interpret_with_ai(
                text,
                species=species,
                allow_ai=allow_ai,
                resolve_coordinates=resolve_coordinates,
                current_resolution=resolution,
            )
            if ai_interpretation is not None:
                return ai_interpretation
            return self._suggestions(
                submitted_text=text,
                resolution=resolution,
                ui_prompt=(
                    "Add a gene symbol plus HGVS, protein, rsID, or genomic coordinate "
                    "so Eamos can show matching variants."
                ),
                warnings=ai_warnings,
            )

        if resolution.kind == "protein":
            if not resolution.gene:
                ai_interpretation, _ai_warnings = self._interpret_with_ai(
                    text,
                    species=species,
                    allow_ai=allow_ai,
                    resolve_coordinates=resolve_coordinates,
                    current_resolution=resolution,
                )
                if ai_interpretation is not None:
                    return ai_interpretation
            candidates = self.candidate_resolver.resolve_candidates(resolution)
            has_high_confidence = any(candidate.confidence == "high" for candidate in candidates)
            return self._candidate_interpretation(
                submitted_text=text,
                resolution=resolution,
                candidates=candidates,
                no_candidate_prompt=(
                    "Add the cDNA/genomic allele or choose from reported variants with "
                    "the same protein position when available."
                ),
                suggestions_mode=bool(candidates)
                and not has_high_confidence
                and len(candidates) == 1,
            )

        if resolution.kind in {"cdna", "genomic"}:
            exact_candidate = self.candidate_resolver.exact_candidate(resolution)
            if exact_candidate is not None and not resolution.gene:
                return self._auto_resolved(
                    submitted_text=text,
                    resolution=_resolution_from_candidate(resolution, exact_candidate),
                    candidate=exact_candidate,
                    assumptions=["Gene inferred from a reported source-backed candidate."],
                )
            if exact_candidate is None:
                candidates = self.candidate_resolver.resolve_candidates(resolution)
                if candidates:
                    return self._candidate_interpretation(
                        submitted_text=text,
                        resolution=resolution,
                        candidates=candidates,
                        no_candidate_prompt=(
                            "Choose the closest reported variant or adjust the submitted HGVS."
                        ),
                        suggestions_mode=True,
                    )

        return self._deterministic(submitted_text=text, resolution=resolution)

    def _interpret_with_ai(
        self,
        submitted_text: str,
        *,
        species: str,
        allow_ai: bool,
        resolve_coordinates: bool,
        current_resolution: SearchInputResolution,
    ) -> tuple[SearchInputInterpretation | None, list[str]]:
        if species.lower() != "human":
            return None, []

        ai_result = self.ai_extractor.extract(submitted_text, allow_ai=allow_ai)
        warnings = list(ai_result.warnings)
        extraction = ai_result.extraction
        if extraction is None:
            return None, warnings

        if _extraction_matches_current_resolution(extraction, current_resolution):
            return None, warnings

        if not any((extraction.cdna, extraction.genomic_hint, extraction.protein_change)):
            return (
                self._ai_suggestions(
                    submitted_text=submitted_text,
                    extraction=extraction,
                    warnings=warnings,
                    provenance=list(ai_result.provenance),
                ),
                [],
            )

        resolver = self._resolver(resolve_coordinates=resolve_coordinates)
        variant_text = extraction.cdna or extraction.genomic_hint or extraction.protein_change or ""
        resolution = resolver.resolve(
            gene=extraction.gene or "",
            cdna=variant_text,
            transcript=extraction.transcript,
            protein_change=extraction.protein_change,
        )
        resolution = _resolution_with_ai_context(
            resolution,
            warnings=warnings,
            provenance=list(ai_result.provenance),
        )

        if resolution.kind == "protein":
            candidates = self.candidate_resolver.resolve_candidates(resolution)
            has_high_confidence = any(candidate.confidence == "high" for candidate in candidates)
            return (
                self._candidate_interpretation(
                    submitted_text=submitted_text,
                    resolution=resolution,
                    candidates=candidates,
                    no_candidate_prompt=(
                        "Add the cDNA/genomic allele or choose from reported variants with "
                        "the same protein position when available."
                    ),
                    suggestions_mode=bool(candidates)
                    and not has_high_confidence
                    and len(candidates) == 1,
                    assumptions=list(extraction.assumptions),
                    confidence=extraction.confidence,
                ),
                [],
            )

        if resolution.kind in {"cdna", "genomic"}:
            exact_candidate = self.candidate_resolver.exact_candidate(resolution)
            if exact_candidate is not None and not resolution.gene:
                return (
                    self._auto_resolved(
                        submitted_text=submitted_text,
                        resolution=_resolution_from_candidate(resolution, exact_candidate),
                        candidate=exact_candidate,
                        assumptions=[
                            *extraction.assumptions,
                            "Gene inferred from a reported source-backed candidate.",
                        ],
                    ),
                    [],
                )
            if exact_candidate is None:
                candidates = self.candidate_resolver.resolve_candidates(resolution)
                if candidates:
                    return (
                        self._candidate_interpretation(
                            submitted_text=submitted_text,
                            resolution=resolution,
                            candidates=candidates,
                            no_candidate_prompt=(
                                "Choose the closest reported variant or adjust the submitted HGVS."
                            ),
                            suggestions_mode=True,
                            assumptions=list(extraction.assumptions),
                            confidence=extraction.confidence,
                        ),
                        [],
                    )
            return (
                self._ai_assisted(
                    submitted_text=submitted_text,
                    resolution=resolution,
                    extraction=extraction,
                ),
                [],
            )

        return (
            self._ai_suggestions(
                submitted_text=submitted_text,
                extraction=extraction,
                warnings=warnings,
                provenance=list(ai_result.provenance),
            ),
            [],
        )

    def from_selected_candidate(self, candidate_id: str) -> SearchInputInterpretation:
        candidate = self.candidate_resolver.get_candidate(candidate_id)
        if candidate is None:
            return SearchInputInterpretation(
                submitted_text=candidate_id,
                mode="suggestions",
                confidence="low",
                requires_confirmation=True,
                exact_variant_available=False,
                ui_prompt="Choose one of the current candidate options or resubmit the variant.",
                warnings=["selected_candidate_unavailable"],
                provenance=["search_candidate_resolver"],
            )

        resolution = self.resolver.resolve(
            gene=candidate.gene,
            cdna=candidate.cdna or candidate.genomic_hgvs or candidate.genomic_hg38 or "",
            transcript=candidate.transcript,
            protein_change=candidate.protein_change,
        )
        return self._auto_resolved(
            submitted_text=candidate_id,
            resolution=resolution,
            candidate=candidate,
            assumptions=["User selected a source-backed candidate."],
        )

    def _resolver(self, *, resolve_coordinates: bool) -> EamosSearchInputResolver:
        if not resolve_coordinates:
            return self.resolver
        return EamosSearchInputResolver(
            settings=self.settings,
            resolve_coordinates=True,
        )

    def _deterministic(
        self,
        *,
        submitted_text: str,
        resolution: SearchInputResolution,
    ) -> SearchInputInterpretation:
        return SearchInputInterpretation(
            submitted_text=submitted_text,
            mode="deterministic",
            confidence="high",
            gene=resolution.gene or None,
            cdna=resolution.hgvs,
            transcript=resolution.transcript,
            protein_change=resolution.protein_change,
            normalized_query=_normalized_query(resolution),
            query_kind=resolution.kind,
            genomic_hg38=resolution.genomic_hg38,
            genomic_hgvs=resolution.genomic_hgvs,
            source_inputs=_source_inputs_schema(resolution.source_inputs),
            warnings=list(resolution.warnings),
            provenance=["deterministic_parser", *resolution.provenance],
        )

    def _auto_resolved(
        self,
        *,
        submitted_text: str,
        resolution: SearchInputResolution,
        candidate: SearchInputCandidate,
        assumptions: list[str] | None = None,
    ) -> SearchInputInterpretation:
        return SearchInputInterpretation(
            submitted_text=submitted_text,
            mode="auto_resolved",
            confidence="high",
            gene=candidate.gene,
            cdna=candidate.cdna,
            transcript=candidate.transcript,
            protein_change=candidate.protein_change,
            normalized_query=_normalized_query(resolution),
            query_kind=resolution.kind,
            genomic_hg38=candidate.genomic_hg38 or resolution.genomic_hg38,
            genomic_hgvs=candidate.genomic_hgvs or resolution.genomic_hgvs,
            source_inputs=_source_inputs_schema(resolution.source_inputs),
            exact_variant_available=True,
            auto_selected_candidate_id=candidate.candidate_id,
            candidates=[candidate],
            assumptions=assumptions or [],
            warnings=list(resolution.warnings),
            provenance=[
                "deterministic_parser",
                "search_candidate_resolver",
                *resolution.provenance,
            ],
        )

    def _ai_assisted(
        self,
        *,
        submitted_text: str,
        resolution: SearchInputResolution,
        extraction: SearchInputAiExtraction,
    ) -> SearchInputInterpretation:
        return SearchInputInterpretation(
            submitted_text=submitted_text,
            mode="ai_assisted",
            confidence=extraction.confidence,
            gene=resolution.gene or None,
            cdna=resolution.hgvs,
            transcript=resolution.transcript,
            protein_change=resolution.protein_change,
            normalized_query=_normalized_query(resolution),
            query_kind=resolution.kind,
            genomic_hg38=resolution.genomic_hg38,
            genomic_hgvs=resolution.genomic_hgvs,
            source_inputs=_source_inputs_schema(resolution.source_inputs),
            warnings=list(resolution.warnings),
            assumptions=list(extraction.assumptions),
            provenance=[
                "ai_extractor",
                "deterministic_validation",
                *resolution.provenance,
            ],
        )

    def _candidate_interpretation(
        self,
        *,
        submitted_text: str,
        resolution: SearchInputResolution,
        candidates: list[SearchInputCandidate],
        no_candidate_prompt: str,
        suggestions_mode: bool = False,
        assumptions: list[str] | None = None,
        confidence: str = "medium",
    ) -> SearchInputInterpretation:
        high_confidence = [candidate for candidate in candidates if candidate.confidence == "high"]
        if len(high_confidence) == 1 and len(candidates) == 1 and not suggestions_mode:
            candidate = high_confidence[0]
            return self._auto_resolved(
                submitted_text=submitted_text,
                resolution=_resolution_from_candidate(resolution, candidate),
                candidate=candidate,
                assumptions=[
                    *(assumptions or []),
                    "One reported source-backed candidate matched the submitted intent.",
                ],
            )

        if candidates:
            mode = "suggestions" if suggestions_mode else "needs_selection"
            prompt = (
                "Choose one of the ranked reported variants to continue."
                if mode == "needs_selection"
                else "Review the closest reported variants before running a report."
            )
            return SearchInputInterpretation(
                submitted_text=submitted_text,
                mode=mode,
                confidence=confidence if confidence in {"high", "medium", "low"} else "medium",
                gene=resolution.gene or None,
                cdna=resolution.hgvs if resolution.kind != "protein" else None,
                transcript=resolution.transcript,
                protein_change=resolution.hgvs if resolution.kind == "protein" else None,
                normalized_query=_normalized_query(resolution),
                query_kind=resolution.kind,
                genomic_hg38=resolution.genomic_hg38,
                genomic_hgvs=resolution.genomic_hgvs,
                source_inputs=_source_inputs_schema(resolution.source_inputs),
                requires_confirmation=True,
                exact_variant_available=False,
                candidates=candidates,
                ui_prompt=prompt,
                assumptions=assumptions or [],
                warnings=list(resolution.warnings),
                provenance=[
                    "deterministic_parser",
                    "search_candidate_resolver",
                    *resolution.provenance,
                ],
            )

        return self._suggestions(
            submitted_text=submitted_text,
            resolution=resolution,
            ui_prompt=no_candidate_prompt,
            assumptions=assumptions,
        )

    def _ai_suggestions(
        self,
        *,
        submitted_text: str,
        extraction: SearchInputAiExtraction,
        warnings: list[str],
        provenance: list[str],
    ) -> SearchInputInterpretation:
        prompt = (
            "Add a protein, cDNA, rsID, or genomic coordinate for the gene hint to continue."
            if extraction.gene
            else (
                "Add a gene symbol plus HGVS, protein, rsID, or genomic coordinate "
                "so Eamos can show matching variants."
            )
        )
        return SearchInputInterpretation(
            submitted_text=submitted_text,
            mode="suggestions",
            confidence=extraction.confidence,
            gene=extraction.gene,
            cdna=extraction.cdna,
            transcript=extraction.transcript,
            protein_change=extraction.protein_change,
            normalized_query=(
                f"{extraction.gene}:{extraction.cdna or extraction.protein_change}"
                if extraction.gene and (extraction.cdna or extraction.protein_change)
                else extraction.gene
            ),
            query_kind="plain_language",
            requires_confirmation=True,
            exact_variant_available=False,
            ui_prompt=prompt,
            assumptions=list(extraction.assumptions),
            warnings=warnings,
            provenance=["ai_extractor", *provenance],
        )

    def _suggestions(
        self,
        *,
        submitted_text: str,
        resolution: SearchInputResolution,
        ui_prompt: str,
        warnings: list[str] | None = None,
        assumptions: list[str] | None = None,
    ) -> SearchInputInterpretation:
        return SearchInputInterpretation(
            submitted_text=submitted_text,
            mode="suggestions",
            confidence="low",
            gene=resolution.gene or None,
            cdna=resolution.hgvs if resolution.kind not in {"unknown", "protein"} else None,
            transcript=resolution.transcript,
            protein_change=resolution.hgvs if resolution.kind == "protein" else None,
            normalized_query=_normalized_query(resolution),
            query_kind=resolution.kind,
            genomic_hg38=resolution.genomic_hg38,
            genomic_hgvs=resolution.genomic_hgvs,
            source_inputs=_source_inputs_schema(resolution.source_inputs),
            requires_confirmation=True,
            exact_variant_available=False,
            ui_prompt=ui_prompt,
            assumptions=assumptions or [],
            warnings=[*resolution.warnings, *(warnings or [])],
            provenance=["deterministic_parser", *resolution.provenance],
        )


def _source_inputs_schema(source_inputs: SourceSpecificInputs) -> SearchInputSourceInputs:
    return SearchInputSourceInputs(
        variant_validator=source_inputs.variant_validator,
        ensembl_vep=source_inputs.ensembl_vep,
        gnomad=source_inputs.gnomad,
        spliceai=source_inputs.spliceai,
        clinvar=source_inputs.clinvar,
        literature_terms=list(source_inputs.literature_terms),
    )


def _normalized_query(resolution: SearchInputResolution) -> str:
    if resolution.gene:
        return f"{resolution.gene}:{resolution.hgvs}"
    return resolution.hgvs


def _resolution_from_candidate(
    resolution: SearchInputResolution,
    candidate: SearchInputCandidate,
) -> SearchInputResolution:
    return replace(
        resolution,
        gene=candidate.gene,
        hgvs=candidate.cdna or resolution.hgvs,
        transcript=candidate.transcript,
        protein_change=candidate.protein_change or resolution.protein_change,
        transcript_hgvs=(
            f"{candidate.transcript}:{candidate.cdna}"
            if candidate.transcript and candidate.cdna
            else candidate.cdna or resolution.transcript_hgvs
        ),
        resolver_transcript=candidate.transcript or resolution.resolver_transcript,
        resolver_transcript_hgvs=(
            f"{candidate.transcript}:{candidate.cdna}"
            if candidate.transcript and candidate.cdna
            else resolution.resolver_transcript_hgvs
        ),
        genomic_hg38=candidate.genomic_hg38 or resolution.genomic_hg38,
        genomic_hgvs=candidate.genomic_hgvs or resolution.genomic_hgvs,
    )


def _resolution_with_ai_context(
    resolution: SearchInputResolution,
    *,
    warnings: list[str],
    provenance: list[str],
) -> SearchInputResolution:
    return replace(
        resolution,
        warnings=(*resolution.warnings, *warnings),
        provenance=(
            "ai_extractor",
            *provenance,
            "deterministic_validation",
            *resolution.provenance,
        ),
    )


def _extraction_matches_current_resolution(
    extraction: SearchInputAiExtraction,
    resolution: SearchInputResolution,
) -> bool:
    if resolution.kind == "unknown":
        return False
    extracted_variant = extraction.cdna or extraction.genomic_hint or extraction.protein_change
    if extracted_variant is None:
        return False
    return (extraction.gene or "").upper() == (resolution.gene or "").upper() and _compact(
        extracted_variant
    ) == _compact(resolution.hgvs)


def _compact(value: str | None) -> str:
    return "".join((value or "").split()).upper()
