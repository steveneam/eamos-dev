from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

from app.schemas.workbench import (
    CrisprOffTargetRequest,
    CrisprOffTargetResponse,
    CrisprOffTargetSite,
    CrisprScreeningPrimerRequest,
    CrisprScreeningPrimerTarget,
    CrisprScreeningRegion,
    PrimerPair,
    PrimerRequest,
    PrimerResponse,
    ScreeningPrimer,
    SourceDisclosure,
)
from app.services.crispr_design import (
    hsu_mismatch_positions,
    hsu_off_target_cutting_score,
)
from app.services.crispr_offtarget_index import (
    CrisprOffTargetIndexUnavailable,
    CrisprOffTargetIndexUnsupported,
    inspect_crispr_offtarget_index,
    query_spcas9_offtarget_index,
)
from app.services.sequence_context import SequenceContext, unsupported_input_warning

SCREENING_REFERENCE_WINDOW_UNAVAILABLE_WARNING = "crispr_screening_reference_window_unavailable"
CRISPR_OFFTARGET_PROVIDER_AUTO = "auto"
CRISPR_OFFTARGET_PROVIDER_INDEXED_SQLITE = "indexed_sqlite"
CRISPR_OFFTARGET_PROVIDER_MOCK = "mock"


class CrisprOffTargetScreeningInputError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        warnings: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.warnings = warnings if warnings is not None else [code]


class CrisprOffTargetScreeningProviderUnavailable(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class PrimerDesignProvider(Protocol):
    def design(self, payload: PrimerRequest, context: SequenceContext) -> PrimerResponse: ...


class ScreeningReferenceWindowProvider(Protocol):
    def get_sequence(
        self,
        chrom: str,
        start: int,
        end: int,
        build: str | None = None,
    ) -> Any: ...


class MockCasOffinderOffTargetProvider:
    """De-identified mock-first Cas-OFFinder boundary for site-level screening."""

    def enumerate(self, payload: CrisprOffTargetRequest) -> CrisprOffTargetResponse:
        if payload.enzyme != "SpCas9":
            code = unsupported_input_warning("enzyme")
            raise CrisprOffTargetScreeningInputError(
                code=code,
                message="CRISPR off-target screening currently supports SpCas9 NGG only.",
                warnings=[code],
            )

        on_target = payload.on_target_locus
        base_chromosome = _normalize_chromosome(
            on_target.chromosome if on_target is not None else "chr1"
        )
        base_position = on_target.position if on_target is not None else 68_444_869
        base_strand = on_target.strand if on_target is not None else "+"

        sites = [
            CrisprOffTargetSite(
                sequence=payload.guide,
                pam=_concrete_pam(payload.pam, 0),
                score=1.0,
                mismatches=0,
                gene="ON_TARGET",
                gene_id=None,
                biotype="protein_coding",
                chromosome=base_chromosome,
                strand=base_strand,
                position=base_position,
                on_target=True,
            )
        ]

        for index, row in enumerate(_MOCK_ROWS, start=1):
            mismatch_positions = row.mismatch_positions
            if len(mismatch_positions) > payload.max_mismatches:
                continue
            sequence = _mutate(payload.guide, mismatch_positions)
            sites.append(
                CrisprOffTargetSite(
                    sequence=sequence,
                    pam=_concrete_pam(payload.pam, index),
                    score=round(hsu_off_target_cutting_score(payload.guide, sequence) / 100.0, 6),
                    mismatches=len(hsu_mismatch_positions(payload.guide, sequence)),
                    gene=row.gene,
                    gene_id=row.gene_id,
                    biotype=row.biotype,
                    chromosome=row.chromosome,
                    strand=row.strand,
                    position=row.position,
                    on_target=False,
                )
            )

        sites = sorted(
            sites,
            key=lambda site: (
                not site.on_target,
                -site.score,
                site.mismatches,
                site.chromosome,
                site.position,
            ),
        )
        return CrisprOffTargetResponse(
            genome_build=payload.genome_build,
            sites=sites,
            source_disclosure=SourceDisclosure(
                source_status="fallback",
                provider_id="mock_cas_offinder",
                provider_label="Mock Cas-OFFinder fallback",
                warnings=["crispr_offtarget_mock_fallback"],
                requirements=["crispr_offtarget_index"],
            ),
        )


class UnavailableCrisprOffTargetProvider:
    """Fail-closed release seam used until a verified genome index is mounted."""

    def enumerate(self, payload: CrisprOffTargetRequest) -> CrisprOffTargetResponse:
        del payload
        raise CrisprOffTargetScreeningProviderUnavailable(
            code="crispr_offtarget_index_unavailable",
            message="The verified GRCh38 CRISPR off-target index is unavailable.",
        )


@dataclass(frozen=True)
class CrisprOffTargetArtifactIdentity:
    manifest_id: str
    sha256: str
    source_release: str


class IndexedSqliteCrisprOffTargetProvider:
    """Whole-genome SpCas9 off-target lookup against a local immutable SQLite index."""

    def __init__(
        self,
        index_path,
        *,
        max_results: int = 200,
        artifact_manifest_id: str | None = None,
        artifact_sha256: str | None = None,
        source_release: str | None = None,
    ) -> None:
        self.index_path = index_path
        self.max_results = max_results
        self.artifact_manifest_id = artifact_manifest_id
        self.artifact_sha256 = artifact_sha256
        self.source_release = source_release

    def available(self) -> bool:
        return inspect_crispr_offtarget_index(self.index_path).ready

    def execution_artifact(self) -> CrisprOffTargetArtifactIdentity | None:
        if not self.artifact_manifest_id or not self.artifact_sha256 or not self.source_release:
            return None
        if re.fullmatch(r"[0-9a-fA-F]{64}", self.artifact_sha256) is None:
            return None
        return CrisprOffTargetArtifactIdentity(
            manifest_id=self.artifact_manifest_id,
            sha256=self.artifact_sha256.lower(),
            source_release=self.source_release,
        )

    def enumerate(self, payload: CrisprOffTargetRequest) -> CrisprOffTargetResponse:
        try:
            response = query_spcas9_offtarget_index(
                self.index_path,
                payload,
                max_results=self.max_results,
            )
            return response.model_copy(
                update={
                    "source_disclosure": SourceDisclosure(
                        source_status="source_backed",
                        provider_id="indexed_sqlite_crispr_offtarget",
                        provider_label="Indexed GRCh38 SpCas9 off-target index",
                        cache_status="ready",
                    )
                }
            )
        except CrisprOffTargetIndexUnsupported as exc:
            raise CrisprOffTargetScreeningInputError(
                code=exc.code,
                message=exc.message,
                warnings=[exc.code],
            ) from exc
        except CrisprOffTargetIndexUnavailable as exc:
            raise CrisprOffTargetScreeningProviderUnavailable(
                code="crispr_offtarget_index_unavailable",
                message=exc.message,
            ) from exc


def design_screening_primers(
    payload: CrisprScreeningPrimerRequest,
    *,
    primer_provider: PrimerDesignProvider,
    reference_window_provider: ScreeningReferenceWindowProvider | None = None,
) -> tuple[list[ScreeningPrimer], list[str]]:
    primers: list[ScreeningPrimer] = []
    warnings: list[str] = []
    for target in payload.sites:
        context, region_label, point, template_source, target_warnings = _target_context(
            target,
            payload=payload,
            reference_window_provider=reference_window_provider,
        )
        warnings.extend(target_warnings)
        primer_payload = PrimerRequest(
            gene="CRISPR_SCREENING",
            cdna=f"site-{target.site_index}",
            mode=payload.mode,
            tm_min=payload.tm_min,
            tm_max=payload.tm_max,
            product_size_min=payload.product_size_min,
            product_size_max=payload.product_size_max,
            avoid_snps=payload.avoid_snps,
        )
        primer_response = primer_provider.design(primer_payload, context)
        pair = _recommended_pair(primer_response.pairs)
        if pair is None:
            warnings.append(f"crispr_screening_primer_unavailable:site_{target.site_index}")
            continue
        primers.append(
            _screening_primer(
                pair,
                target=target,
                point=point,
                region=region_label,
                naming_prefix=payload.naming_prefix,
                template_source=template_source,
            )
        )
    return primers, warnings


@dataclass(frozen=True)
class _MockOffTargetRow:
    mismatch_positions: tuple[int, ...]
    chromosome: str
    position: int
    strand: str
    gene: str | None
    gene_id: str | None
    biotype: str | None


_MOCK_ROWS: tuple[_MockOffTargetRow, ...] = (
    _MockOffTargetRow(
        (16,), "chr7", 117_509_068, "+", "OTSG1", "ENSG00000290001", "protein_coding"
    ),
    _MockOffTargetRow((10,), "chr3", 37_004_431, "-", "OTSG2", "ENSG00000290002", "protein_coding"),
    _MockOffTargetRow((4, 17), "chr12", 102_912_875, "+", None, None, None),
    _MockOffTargetRow((7, 12), "chr17", 43_092_673, "-", "OTSG3", "ENSG00000290003", "lncRNA"),
    _MockOffTargetRow(
        (2, 9, 18), "chr19", 11_100_274, "+", "OTSG4", "ENSG00000290004", "protein_coding"
    ),
    _MockOffTargetRow((1, 5, 14), "chr5", 112_780_910, "-", None, None, None),
)


_BASE_SWAP = {
    "A": "C",
    "C": "G",
    "G": "T",
    "T": "A",
}


def _mutate(guide: str, positions: tuple[int, ...]) -> str:
    bases = list(guide)
    for position in positions:
        bases[position] = _BASE_SWAP[bases[position]]
    return "".join(bases)


def _concrete_pam(pattern: str, index: int) -> str:
    replacements = "ACGT"
    return "".join(
        replacements[(index + offset) % len(replacements)] if base == "N" else base
        for offset, base in enumerate(pattern.upper())
    )


def _target_context(
    target: CrisprScreeningPrimerTarget,
    *,
    payload: CrisprScreeningPrimerRequest,
    reference_window_provider: ScreeningReferenceWindowProvider | None,
) -> tuple[SequenceContext, str, str, str, list[str]]:
    chrom, position = _target_locus(target)
    region = _target_region(
        target,
        chromosome=chrom,
        position=position,
        payload=payload,
    )
    target_offset = _target_offset(target, region=region, position=position)
    template, template_source, warnings = _template_sequence(
        target,
        region=region,
        target_offset=target_offset,
        reference_window_provider=reference_window_provider,
    )
    if target_offset >= len(template):
        code = unsupported_input_warning("screening_target")
        raise CrisprOffTargetScreeningInputError(
            code=code,
            message="Screening-primer target offset is outside the template sequence.",
            warnings=[code],
        )

    region_label = _region_label(region)
    point = f"{_normalize_chromosome(region.chromosome)}:{position}"
    context = SequenceContext(
        gene="CRISPR_SCREENING",
        cdna=f"site-{target.site_index}",
        transcript=None,
        transcript_hgvs=point,
        query_kind="genomic",
        species="human",
        genome_build=region.genome_build,
        genomic_hg38=f"{_normalize_chromosome(region.chromosome).removeprefix('chr')}-{position}-N-N",
        strand=target.strand,
        window_sequence=template,
        target_offset=target_offset,
        reference_base=None,
        alternate_base=None,
        source="fixture",
        source_metadata={
            "template_source": template_source,
            "region": region_label,
            "point": point,
        },
        warnings=warnings,
    )
    return context, region_label, point, template_source, warnings


def _target_locus(target: CrisprScreeningPrimerTarget) -> tuple[str, int]:
    point = _parse_point(target.point)
    chromosome = target.chromosome or (target.region.chromosome if target.region else None)
    position = target.position
    if point is not None:
        chromosome = chromosome or point[0]
        position = position or point[1]
    if chromosome is None or position is None:
        code = unsupported_input_warning("screening_locus")
        raise CrisprOffTargetScreeningInputError(
            code=code,
            message=(
                "Screening-primer targets require chromosome and position, "
                "or a point formatted as chrN:position."
            ),
            warnings=[code],
        )
    return _normalize_chromosome(chromosome), position


def _target_region(
    target: CrisprScreeningPrimerTarget,
    *,
    chromosome: str,
    position: int,
    payload: CrisprScreeningPrimerRequest,
) -> CrisprScreeningRegion:
    if target.region is not None:
        return target.region
    return CrisprScreeningRegion(
        chromosome=chromosome,
        start=max(1, position - payload.flank_bp),
        end=position + payload.flank_bp,
        genome_build=payload.genome_build,
        strand=target.strand,
    )


def _target_offset(
    target: CrisprScreeningPrimerTarget,
    *,
    region: CrisprScreeningRegion,
    position: int,
) -> int:
    if target.target_offset is not None:
        return target.target_offset
    return max(0, position - region.start)


def _template_sequence(
    target: CrisprScreeningPrimerTarget,
    *,
    region: CrisprScreeningRegion,
    target_offset: int,
    reference_window_provider: ScreeningReferenceWindowProvider | None,
) -> tuple[str, str, list[str]]:
    if target.template_sequence:
        if reference_window_provider is not None:
            try:
                window = reference_window_provider.get_sequence(
                    _normalize_chromosome(region.chromosome),
                    region.start,
                    region.end,
                    build=region.genome_build,
                )
                expected = _clean_reference_sequence(getattr(window, "sequence", ""))
            except Exception as exc:
                raise CrisprOffTargetScreeningProviderUnavailable(
                    code=SCREENING_REFERENCE_WINDOW_UNAVAILABLE_WARNING,
                    message="The source-backed screening reference window is unavailable.",
                ) from exc
            if not expected or expected != target.template_sequence:
                code = unsupported_input_warning("screening_template_mismatch")
                raise CrisprOffTargetScreeningInputError(
                    code=code,
                    message="The supplied screening template does not match the verified reference window.",
                    warnings=[code],
                )
        return target.template_sequence, "template_sequence", []

    if reference_window_provider is not None:
        try:
            window = reference_window_provider.get_sequence(
                _normalize_chromosome(region.chromosome),
                region.start,
                region.end,
                build=region.genome_build,
            )
            sequence = _clean_reference_sequence(getattr(window, "sequence", ""))
            if sequence and target_offset < len(sequence):
                return sequence, "reference_window", []
        except Exception as exc:
            raise CrisprOffTargetScreeningProviderUnavailable(
                code=SCREENING_REFERENCE_WINDOW_UNAVAILABLE_WARNING,
                message="The source-backed screening reference window is unavailable.",
            ) from exc
        raise CrisprOffTargetScreeningProviderUnavailable(
            code=SCREENING_REFERENCE_WINDOW_UNAVAILABLE_WARNING,
            message="The source-backed screening reference window is unavailable.",
        )

    raise CrisprOffTargetScreeningProviderUnavailable(
        code=SCREENING_REFERENCE_WINDOW_UNAVAILABLE_WARNING,
        message="A source-backed reference-window provider is required for screening primers.",
    )


def _clean_reference_sequence(sequence: str) -> str:
    return re.sub(r"[^ACGTN]", "N", sequence.upper())


def _parse_point(point: str | None) -> tuple[str, int] | None:
    if not point:
        return None
    match = re.fullmatch(r"(?P<chrom>chr)?(?P<id>\d+|X|Y|M|MT):(?P<pos>\d+)", point.strip())
    if match is None:
        return None
    chrom = match.group("id").upper()
    if chrom == "MT":
        chrom = "M"
    return f"chr{chrom}", int(match.group("pos"))


def _normalize_chromosome(chromosome: str) -> str:
    raw = chromosome.strip()
    if raw.lower().startswith("chr"):
        raw = raw[3:]
    raw = raw.upper()
    if raw == "MT":
        raw = "M"
    return f"chr{raw}"


def _region_label(region: CrisprScreeningRegion) -> str:
    return f"{_normalize_chromosome(region.chromosome)}:{region.start}-{region.end}"


def _recommended_pair(pairs: list[PrimerPair]) -> PrimerPair | None:
    return next((pair for pair in pairs if pair.recommended), pairs[0] if pairs else None)


def _screening_primer(
    pair: PrimerPair,
    *,
    target: CrisprScreeningPrimerTarget,
    point: str,
    region: str,
    naming_prefix: str,
    template_source: str,
) -> ScreeningPrimer:
    prefix = re.sub(r"[^A-Za-z0-9_.-]+", "_", naming_prefix.strip()).strip("_") or "OTS"
    return ScreeningPrimer(
        site_index=target.site_index,
        point=point,
        region=region,
        name_forward=f"{prefix}_{target.site_index}_F",
        name_reverse=f"{prefix}_{target.site_index}_R",
        forward=pair.forward,
        reverse=pair.reverse,
        tm_forward=pair.tm_forward,
        tm_reverse=pair.tm_reverse,
        gc_forward=pair.gc_forward,
        gc_reverse=pair.gc_reverse,
        product_size=pair.product_size,
        specificity_hits=pair.specificity_hits,
        other_products=_other_products(pair),
        secondary_structure_risk=pair.secondary_structure_risk,
        secondary_structure_notes=pair.secondary_structure_notes,
        recommended=pair.recommended,
        notes=pair.notes,
        template_source=template_source,
    )


def _other_products(pair: PrimerPair) -> str:
    if pair.specificity_hits <= 1:
        return "NONE"
    return f"{pair.specificity_hits - 1} other product(s); see notes"
