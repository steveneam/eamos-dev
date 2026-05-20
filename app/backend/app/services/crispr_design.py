from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.schemas.workbench import CrisprGuide, CrisprRequest, CrisprResponse, HdrSsodn
from app.services.sequence_context import SequenceContext, unsupported_input_warning

CRISPR_PROVIDER_LOCAL_DETERMINISTIC = "local_deterministic"
SPCAS9_SPACER_LENGTH = 20
SPCAS9_PAM_LENGTH = 3
SPCAS9_TARGET_LENGTH = SPCAS9_SPACER_LENGTH + SPCAS9_PAM_LENGTH
HSU_DISTANCE_PENALTY_CONSTANT = 4.0
MAX_RETURNED_GUIDES = 6

# MIT/Hsu 2013 position penalties, indexed from PAM-distal to PAM-proximal.
HSU_MISMATCH_PENALTIES: tuple[float, ...] = (
    0.000,
    0.000,
    0.014,
    0.000,
    0.000,
    0.395,
    0.317,
    0.000,
    0.389,
    0.079,
    0.445,
    0.508,
    0.613,
    0.851,
    0.732,
    0.828,
    0.615,
    0.804,
    0.685,
    0.583,
)

Strand = Literal["+", "-"]


class CrisprDesignInputError(Exception):
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


@dataclass(frozen=True)
class SpCas9PamSite:
    spacer: str
    pam: str
    strand: Strand
    spacer_start: int
    spacer_end: int
    pam_start: int
    pam_end: int
    cut_position: int
    deep_hf_context: str


@dataclass(frozen=True)
class HsuOffTarget:
    site: SpCas9PamSite
    mismatches: tuple[int, ...]
    cutting_score: float


_COMPLEMENT = str.maketrans("ACGTN", "TGCAN")


def clean_dna(sequence: str) -> str:
    return "".join(base if base in "ACGTN" else "N" for base in sequence.upper())


def reverse_complement(sequence: str) -> str:
    return clean_dna(sequence).translate(_COMPLEMENT)[::-1]


def is_spcas9_pam(pam: str) -> bool:
    pam = clean_dna(pam)
    return len(pam) == SPCAS9_PAM_LENGTH and pam[0] in "ACGT" and pam[1:] == "GG"


def discover_spcas9_pam_sites(
    sequence: str,
    *,
    strand_filter: Literal["both", "plus", "minus"] = "both",
) -> tuple[SpCas9PamSite, ...]:
    template = clean_dna(sequence)
    sites: list[SpCas9PamSite] = []
    if strand_filter in {"both", "plus"}:
        sites.extend(_plus_spcas9_sites(template))
    if strand_filter in {"both", "minus"}:
        sites.extend(_minus_spcas9_sites(template))
    return tuple(
        sorted(sites, key=lambda site: (site.cut_position, site.strand, site.spacer_start))
    )


def _plus_spcas9_sites(sequence: str) -> tuple[SpCas9PamSite, ...]:
    sites: list[SpCas9PamSite] = []
    for spacer_start in range(0, len(sequence) - SPCAS9_TARGET_LENGTH + 1):
        spacer_end = spacer_start + SPCAS9_SPACER_LENGTH
        pam_end = spacer_end + SPCAS9_PAM_LENGTH
        spacer = sequence[spacer_start:spacer_end]
        pam = sequence[spacer_end:pam_end]
        if "N" in spacer or "N" in pam or not is_spcas9_pam(pam):
            continue
        sites.append(
            SpCas9PamSite(
                spacer=spacer,
                pam=pam,
                strand="+",
                spacer_start=spacer_start,
                spacer_end=spacer_end,
                pam_start=spacer_end,
                pam_end=pam_end,
                cut_position=spacer_start + 17,
                deep_hf_context=spacer + pam[0],
            )
        )
    return tuple(sites)


def _minus_spcas9_sites(sequence: str) -> tuple[SpCas9PamSite, ...]:
    reverse_template = reverse_complement(sequence)
    sites: list[SpCas9PamSite] = []
    sequence_length = len(sequence)
    for rc_spacer_start in range(0, sequence_length - SPCAS9_TARGET_LENGTH + 1):
        rc_spacer_end = rc_spacer_start + SPCAS9_SPACER_LENGTH
        rc_pam_end = rc_spacer_end + SPCAS9_PAM_LENGTH
        spacer = reverse_template[rc_spacer_start:rc_spacer_end]
        pam = reverse_template[rc_spacer_end:rc_pam_end]
        if "N" in spacer or "N" in pam or not is_spcas9_pam(pam):
            continue
        pam_start = sequence_length - rc_pam_end
        pam_end = sequence_length - rc_spacer_end
        spacer_start = sequence_length - rc_spacer_end
        spacer_end = sequence_length - rc_spacer_start
        sites.append(
            SpCas9PamSite(
                spacer=spacer,
                pam=pam,
                strand="-",
                spacer_start=spacer_start,
                spacer_end=spacer_end,
                pam_start=pam_start,
                pam_end=pam_end,
                cut_position=pam_start + 5,
                deep_hf_context=spacer + pam[0],
            )
        )
    return tuple(sites)


def hsu_mismatch_positions(spacer: str, protospacer: str) -> tuple[int, ...]:
    spacer = clean_dna(spacer)
    protospacer = clean_dna(protospacer)
    if len(spacer) != SPCAS9_SPACER_LENGTH or len(protospacer) != SPCAS9_SPACER_LENGTH:
        raise ValueError("Hsu scoring requires 20 nt spacer and protospacer sequences.")
    return tuple(
        idx
        for idx, (spacer_base, protospacer_base) in enumerate(zip(spacer, protospacer))
        if spacer_base != protospacer_base
    )


def hsu_off_target_cutting_score(spacer: str, protospacer: str) -> float:
    mismatches = hsu_mismatch_positions(spacer, protospacer)
    if not mismatches:
        return 100.0

    position_factor = 1.0
    for position in mismatches:
        position_factor *= 1.0 - HSU_MISMATCH_PENALTIES[position]

    distance_factor = 1.0
    if len(mismatches) > 1:
        distances = [later - earlier for earlier, later in zip(mismatches, mismatches[1:])]
        average_distance = sum(distances) / len(distances)
        distance_factor = 1.0 / (
            (((SPCAS9_SPACER_LENGTH - 1) - average_distance) / (SPCAS9_SPACER_LENGTH - 1))
            * HSU_DISTANCE_PENALTY_CONSTANT
            + 1.0
        )

    mismatch_count_factor = 1.0 / (len(mismatches) ** 2)
    score = 100.0 * position_factor * distance_factor * mismatch_count_factor
    return round(max(0.0, min(100.0, score)), 6)


def hsu_specificity_score(off_target_cutting_scores: list[float]) -> float:
    if not off_target_cutting_scores:
        return 100.0
    return round(10000.0 / (100.0 + sum(off_target_cutting_scores)), 6)


class LocalDeterministicCrisprProvider:
    def design(self, payload: CrisprRequest, context: SequenceContext) -> CrisprResponse:
        if payload.cas != "SpCas9":
            code = unsupported_input_warning("cas")
            raise CrisprDesignInputError(
                code=code,
                message="Real-mode CRISPR design currently supports SpCas9 only.",
                warnings=[code],
            )

        sequence = clean_dna(context.window_sequence)
        if len(sequence) < SPCAS9_TARGET_LENGTH:
            code = unsupported_input_warning("sequence_too_short")
            raise CrisprDesignInputError(
                code=code,
                message="Sequence context is too short for SpCas9 NGG guide design.",
                warnings=[code],
            )

        selected_sites = discover_spcas9_pam_sites(
            sequence,
            strand_filter=payload.strand_filter,
        )
        all_sites = discover_spcas9_pam_sites(sequence, strand_filter="both")
        if not selected_sites:
            return CrisprResponse(cas=payload.cas, guides=[], ssodn=None)

        ranked = sorted(
            (
                self._guide_row(
                    site=site,
                    all_sites=all_sites,
                    payload=payload,
                    context=context,
                )
                for site in selected_sites
            ),
            key=lambda row: row["rank"],
        )[:MAX_RETURNED_GUIDES]

        guides = []
        for index, row in enumerate(ranked, start=1):
            guide = row["guide"]
            guides.append(guide.model_copy(update={"index": index}))

        return CrisprResponse(
            cas=payload.cas,
            guides=guides,
            ssodn=_build_hdr_ssodn(context, sequence) if guides else None,
        )

    def _guide_row(
        self,
        *,
        site: SpCas9PamSite,
        all_sites: tuple[SpCas9PamSite, ...],
        payload: CrisprRequest,
        context: SequenceContext,
    ) -> dict[str, object]:
        off_targets = _local_off_targets(
            site=site,
            all_sites=all_sites,
            mismatch_tolerance=max(0, payload.off_target_tolerance),
        )
        specificity = hsu_specificity_score(
            [off_target.cutting_score for off_target in off_targets]
        )
        on_target = heuristic_on_target_score(site.spacer)
        cut_distance = abs(site.cut_position - context.target_offset)
        guide = CrisprGuide(
            index=0,
            cut_position=site.cut_position,
            strand=site.strand,
            guide=site.spacer,
            pam=site.pam,
            on_target_score=round(on_target, 1),
            off_target_score=round(100.0 - specificity, 1),
            gc_percent=round(gc_percent(site.spacer), 1),
            notes=_guide_notes(
                site=site,
                context=context,
                off_target_count=len(off_targets),
                mismatch_tolerance=max(0, payload.off_target_tolerance),
                hsu_specificity=specificity,
            ),
        )
        return {
            "guide": guide,
            "rank": (
                cut_distance,
                guide.off_target_score,
                -guide.on_target_score,
                0 if guide.strand == "+" else 1,
                guide.cut_position,
            ),
        }


def _local_off_targets(
    *,
    site: SpCas9PamSite,
    all_sites: tuple[SpCas9PamSite, ...],
    mismatch_tolerance: int,
) -> list[HsuOffTarget]:
    off_targets: list[HsuOffTarget] = []
    for candidate in all_sites:
        if (
            candidate.strand == site.strand
            and candidate.spacer_start == site.spacer_start
            and candidate.pam_start == site.pam_start
        ):
            continue
        mismatches = hsu_mismatch_positions(site.spacer, candidate.spacer)
        if len(mismatches) <= mismatch_tolerance:
            off_targets.append(
                HsuOffTarget(
                    site=candidate,
                    mismatches=mismatches,
                    cutting_score=hsu_off_target_cutting_score(site.spacer, candidate.spacer),
                )
            )
    return off_targets


def gc_percent(sequence: str) -> float:
    sequence = clean_dna(sequence)
    if not sequence:
        return 0.0
    return 100.0 * sum(1 for base in sequence if base in {"G", "C"}) / len(sequence)


def heuristic_on_target_score(spacer: str) -> float:
    spacer = clean_dna(spacer)
    gc = gc_percent(spacer)
    score = 62.0
    score += max(0.0, 20.0 - abs(gc - 50.0))
    if "TTTT" in spacer:
        score -= 18.0
    if spacer[-1:] in {"G", "C"}:
        score += 4.0
    if spacer[:1] == "G":
        score += 2.0
    return max(0.0, min(100.0, score))


def _guide_notes(
    *,
    site: SpCas9PamSite,
    context: SequenceContext,
    off_target_count: int,
    mismatch_tolerance: int,
    hsu_specificity: float,
) -> str:
    target = context.genomic_hg38 or context.transcript_hgvs
    return (
        "Local deterministic SpCas9 NGG design. "
        "On-target score is a transparent GC/poly-T/PAM-proximal heuristic, not DeepHF. "
        f"In-context Hsu/MIT specificity scan found {off_target_count} candidate(s) "
        f"within {mismatch_tolerance} mismatch(es); Hsu specificity {hsu_specificity:.1f}/100. "
        f"Cut offset {site.cut_position}; template {context.genome_build} {target}. "
        "This is not a genome-wide Bowtie/BWA off-target screen."
    )


def _build_hdr_ssodn(context: SequenceContext, sequence: str) -> HdrSsodn | None:
    target_offset = context.target_offset
    reference = (context.reference_base or "").upper()
    alternate = (context.alternate_base or "").upper()
    if (
        target_offset < 0
        or target_offset >= len(sequence)
        or len(reference) != 1
        or len(alternate) != 1
        or reference not in "ACGT"
        or alternate not in "ACGT"
        or sequence[target_offset] != reference
    ):
        return None

    left_start = max(0, target_offset - 30)
    right_end = min(len(sequence), target_offset + 31)
    left_arm = sequence[left_start:target_offset]
    right_arm = sequence[target_offset + 1 : right_end]
    reference_arm = left_arm + reference + right_arm
    variant_arm = left_arm + alternate + right_arm
    return HdrSsodn(
        reference_arm=reference_arm,
        variant_arm=variant_arm,
        repair_template=variant_arm,
        edits_encoded=[context.cdna],
        arm_lengths={"left": len(left_arm), "right": len(right_arm)},
        estimated_hdr_efficiency=0.12,
    )
