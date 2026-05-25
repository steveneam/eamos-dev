from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Protocol

from app.schemas.gene_viewer import (
    AlleleMode,
    ProteinConsequenceKind,
    ProteinProductEffect,
    ProteinProductExonEffect,
)


class ProteinVariantLike(Protocol):
    hgvs_p: str | None
    cds_pos: int
    codon_number: int | None
    aa_ref: str | None
    aa_alt: str | None


class CdsExonLike(Protocol):
    number: int
    cds_start: int
    cds_end: int


@dataclass(frozen=True)
class ParsedProteinConsequence:
    kind: ProteinConsequenceKind
    aa_position: int | None = None
    aa_end_position: int | None = None
    aa_ref: str | None = None
    aa_alt: str | None = None
    stop_distance: int | None = None
    aa_delta: int = 0


class VariantAppliedModelGenerator:
    """Build Eamos' internal variant-applied product model for viewer display."""

    def build(
        self,
        *,
        variant: ProteinVariantLike,
        allele_mode: AlleleMode,
        reference_protein_length: int | None,
        exons: Iterable[CdsExonLike],
    ) -> ProteinProductEffect:
        parsed = parse_protein_consequence(variant)
        reference_length = _positive_int_or_none(reference_protein_length)
        if allele_mode == "reference":
            return ProteinProductEffect(
                allele_mode="reference",
                consequence="reference",
                label="Reference protein",
                description="Reference transcript product; no variant-applied protein change.",
                reference_protein_length=reference_length,
                effective_protein_length=reference_length,
                exon_effects=_exon_effects(
                    exons=exons,
                    variant_cds_pos=variant.cds_pos,
                    affected_cds_start=None,
                ),
            )

        affected_aa_start = parsed.aa_position or variant.codon_number
        stop_codon = _stop_codon(parsed)
        consequence = parsed.kind
        effective_length = _effective_length(
            parsed=parsed,
            reference_length=reference_length,
        )
        truncates = consequence in {"stop_gained", "frameshift"} and (
            effective_length is not None
            and reference_length is not None
            and effective_length < reference_length
        )
        affected_cds_start = _affected_cds_start(
            variant=variant,
            parsed=parsed,
            affected_aa_start=affected_aa_start,
        )
        return ProteinProductEffect(
            allele_mode="variant",
            consequence=consequence,
            label=_label(
                consequence=consequence,
                affected_aa_start=affected_aa_start,
                stop_codon=stop_codon,
            ),
            description=_description(
                consequence=consequence,
                affected_aa_start=affected_aa_start,
                stop_codon=stop_codon,
                effective_length=effective_length,
                reference_length=reference_length,
            ),
            reference_protein_length=reference_length,
            effective_protein_length=effective_length or reference_length,
            truncates_protein=truncates,
            stop_codon=stop_codon,
            affected_aa_start=affected_aa_start,
            lost_aa_count=max(
                0, (reference_length or 0) - (effective_length or reference_length or 0)
            ),
            nmd_risk=("possible" if consequence in {"stop_gained", "frameshift"} else None),
            exon_effects=_exon_effects(
                exons=exons,
                variant_cds_pos=variant.cds_pos,
                affected_cds_start=affected_cds_start if truncates else None,
            ),
        )


def build_protein_product_effect(
    *,
    variant: ProteinVariantLike,
    allele_mode: AlleleMode,
    reference_protein_length: int | None,
    exons: Iterable[CdsExonLike],
) -> ProteinProductEffect:
    return VariantAppliedModelGenerator().build(
        variant=variant,
        allele_mode=allele_mode,
        reference_protein_length=reference_protein_length,
        exons=exons,
    )


def parse_protein_consequence(variant: ProteinVariantLike) -> ParsedProteinConsequence:
    hgvs_p = _clean_hgvs_p(variant.hgvs_p)
    if not hgvs_p:
        if variant.aa_alt == "*":
            return ParsedProteinConsequence(
                kind="stop_gained",
                aa_position=variant.codon_number,
                aa_ref=variant.aa_ref,
                aa_alt="*",
            )
        return ParsedProteinConsequence(kind="unknown", aa_position=variant.codon_number)

    frameshift = re.fullmatch(
        r"p\.(?P<ref>[A-Z][a-z]{2}|[A-Z])(?P<pos>\d+)"
        r"(?:(?P<alt>[A-Z][a-z]{2}|[A-Z]))?fs"
        r"(?:(?:Ter|\*)(?P<stop>\d+))?",
        hgvs_p,
    )
    if frameshift is not None:
        return ParsedProteinConsequence(
            kind="frameshift",
            aa_position=int(frameshift.group("pos")),
            aa_ref=frameshift.group("ref"),
            aa_alt=frameshift.group("alt"),
            stop_distance=_int_or_none(frameshift.group("stop")),
        )

    stop_lost = re.fullmatch(
        r"p\.(?:Ter|\*)(?P<pos>\d+)(?P<alt>[A-Z][a-z]{2}|[A-Z])"
        r"ext(?:(?:Ter|\*)(?P<stop>\d+)|\*\?)?",
        hgvs_p,
    )
    if stop_lost is not None:
        return ParsedProteinConsequence(
            kind="stop_lost",
            aa_position=int(stop_lost.group("pos")),
            aa_alt=stop_lost.group("alt"),
            stop_distance=_int_or_none(stop_lost.group("stop")),
        )

    deletion = re.fullmatch(
        r"p\.(?P<ref>[A-Z][a-z]{2}|[A-Z])(?P<pos>\d+)"
        r"(?:_(?P<ref2>[A-Z][a-z]{2}|[A-Z])(?P<pos2>\d+))?del",
        hgvs_p,
    )
    if deletion is not None:
        start = int(deletion.group("pos"))
        end = int(deletion.group("pos2") or start)
        return ParsedProteinConsequence(
            kind="inframe_deletion",
            aa_position=start,
            aa_end_position=end,
            aa_ref=deletion.group("ref"),
            aa_delta=-max(1, end - start + 1),
        )

    duplication = re.fullmatch(
        r"p\.(?P<ref>[A-Z][a-z]{2}|[A-Z])(?P<pos>\d+)"
        r"(?:_(?P<ref2>[A-Z][a-z]{2}|[A-Z])(?P<pos2>\d+))?dup",
        hgvs_p,
    )
    if duplication is not None:
        start = int(duplication.group("pos"))
        end = int(duplication.group("pos2") or start)
        return ParsedProteinConsequence(
            kind="inframe_duplication",
            aa_position=start,
            aa_end_position=end,
            aa_ref=duplication.group("ref"),
            aa_delta=max(1, end - start + 1),
        )

    insertion = re.fullmatch(
        r"p\.(?P<ref>[A-Z][a-z]{2}|[A-Z])(?P<pos>\d+)_"
        r"(?P<ref2>[A-Z][a-z]{2}|[A-Z])(?P<pos2>\d+)ins(?P<alt>[A-Za-z]+)",
        hgvs_p,
    )
    if insertion is not None:
        return ParsedProteinConsequence(
            kind="inframe_insertion",
            aa_position=int(insertion.group("pos")),
            aa_end_position=int(insertion.group("pos2")),
            aa_ref=insertion.group("ref"),
            aa_alt=insertion.group("alt"),
            aa_delta=max(1, _aa_token_count(insertion.group("alt"))),
        )

    delins = re.fullmatch(
        r"p\.(?P<ref>[A-Z][a-z]{2}|[A-Z])(?P<pos>\d+)"
        r"(?:_(?P<ref2>[A-Z][a-z]{2}|[A-Z])(?P<pos2>\d+))?"
        r"delins(?P<alt>[A-Za-z]+)",
        hgvs_p,
    )
    if delins is not None:
        start = int(delins.group("pos"))
        end = int(delins.group("pos2") or start)
        deleted = max(1, end - start + 1)
        inserted = max(1, _aa_token_count(delins.group("alt")))
        return ParsedProteinConsequence(
            kind="delins",
            aa_position=start,
            aa_end_position=end,
            aa_ref=delins.group("ref"),
            aa_alt=delins.group("alt"),
            aa_delta=inserted - deleted,
        )

    simple = re.fullmatch(
        r"p\.(?P<ref>[A-Z][a-z]{2}|[A-Z])(?P<pos>\d+)" r"(?P<alt>[A-Z][a-z]{2}|Ter|[A-Z*]|=)",
        hgvs_p,
    )
    if simple is None:
        return ParsedProteinConsequence(kind="unknown", aa_position=variant.codon_number)

    alt = simple.group("alt")
    ref = simple.group("ref")
    position = int(simple.group("pos"))
    if alt in {"Ter", "*"}:
        return ParsedProteinConsequence(
            kind="stop_gained",
            aa_position=position,
            aa_ref=ref,
            aa_alt="*",
        )
    if alt == "=" or _aa_symbol(ref) == _aa_symbol(alt):
        return ParsedProteinConsequence(
            kind="synonymous",
            aa_position=position,
            aa_ref=ref,
            aa_alt=alt,
        )
    return ParsedProteinConsequence(
        kind="missense",
        aa_position=position,
        aa_ref=ref,
        aa_alt=alt,
    )


def _clean_hgvs_p(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if ":" in stripped:
        stripped = stripped.split(":", 1)[1]
    return stripped.replace("p.(", "p.").removesuffix(")")


def _stop_codon(parsed: ParsedProteinConsequence) -> int | None:
    if parsed.kind == "stop_gained":
        return parsed.aa_position
    if parsed.kind == "frameshift" and parsed.aa_position and parsed.stop_distance:
        return parsed.aa_position + parsed.stop_distance
    return None


def _effective_length(
    *,
    parsed: ParsedProteinConsequence,
    reference_length: int | None,
) -> int | None:
    if parsed.kind == "stop_gained" and parsed.aa_position is not None:
        return max(0, parsed.aa_position - 1)
    if parsed.kind == "frameshift" and parsed.aa_position is not None:
        if parsed.stop_distance is not None:
            return max(0, parsed.aa_position + parsed.stop_distance - 1)
        return (
            min(reference_length, parsed.aa_position)
            if reference_length is not None
            else parsed.aa_position
        )
    if parsed.kind == "stop_lost":
        if reference_length is not None and parsed.stop_distance is not None:
            return reference_length + parsed.stop_distance
        return reference_length
    if parsed.kind in {"inframe_deletion", "inframe_insertion", "inframe_duplication", "delins"}:
        if reference_length is None:
            return None
        return max(0, reference_length + parsed.aa_delta)
    return reference_length


def _affected_cds_start(
    *,
    variant: ProteinVariantLike,
    parsed: ParsedProteinConsequence,
    affected_aa_start: int | None,
) -> int | None:
    if parsed.kind == "frameshift":
        return variant.cds_pos
    if parsed.kind == "stop_gained" and affected_aa_start is not None:
        return (affected_aa_start - 1) * 3 + 1
    return None


def _exon_effects(
    *,
    exons: Iterable[CdsExonLike],
    variant_cds_pos: int,
    affected_cds_start: int | None,
) -> list[ProteinProductExonEffect]:
    effects: list[ProteinProductExonEffect] = []
    for exon in sorted(exons, key=lambda item: item.cds_start):
        state = "retained"
        affected_start = None
        affected_end = None
        lost_bases = 0
        if affected_cds_start is None:
            if exon.cds_start <= variant_cds_pos <= exon.cds_end:
                state = "contains_variant"
        elif exon.cds_end >= affected_cds_start:
            affected_start = max(exon.cds_start, affected_cds_start)
            affected_end = exon.cds_end
            lost_bases = max(0, affected_end - affected_start + 1)
            if exon.cds_start <= variant_cds_pos <= exon.cds_end:
                state = "contains_variant"
            else:
                state = "downstream_truncated"
        effects.append(
            ProteinProductExonEffect(
                exon_number=exon.number,
                cds_start=exon.cds_start,
                cds_end=exon.cds_end,
                state=state,
                affected_cds_start=affected_start,
                affected_cds_end=affected_end,
                lost_cds_bases=lost_bases,
            )
        )
    return effects


def _label(
    *,
    consequence: ProteinConsequenceKind,
    affected_aa_start: int | None,
    stop_codon: int | None,
) -> str:
    if consequence == "stop_gained":
        return f"Stop gained at codon {stop_codon or affected_aa_start}"
    if consequence == "frameshift":
        if stop_codon is not None:
            return f"Frameshift, stop at codon {stop_codon}"
        return f"Frameshift from codon {affected_aa_start}"
    if consequence == "synonymous":
        return "Synonymous"
    if consequence == "missense":
        return f"Missense at codon {affected_aa_start}"
    if consequence == "stop_lost":
        return f"Stop lost at codon {affected_aa_start}"
    if consequence == "inframe_deletion":
        return f"In-frame deletion from codon {affected_aa_start}"
    if consequence == "inframe_insertion":
        return f"In-frame insertion after codon {affected_aa_start}"
    if consequence == "inframe_duplication":
        return f"In-frame duplication from codon {affected_aa_start}"
    if consequence == "delins":
        return f"Protein delins from codon {affected_aa_start}"
    return "Protein consequence unresolved"


def _description(
    *,
    consequence: ProteinConsequenceKind,
    affected_aa_start: int | None,
    stop_codon: int | None,
    effective_length: int | None,
    reference_length: int | None,
) -> str:
    if consequence == "stop_gained":
        return (
            f"Variant-applied translation stops at codon {stop_codon or affected_aa_start}; "
            f"the displayed protein product is {effective_length or 0} aa versus "
            f"{reference_length or 0} aa reference."
        )
    if consequence == "frameshift":
        stop_text = f" and reaches a stop at codon {stop_codon}" if stop_codon else ""
        return (
            f"Variant-applied translation changes frame from codon {affected_aa_start}"
            f"{stop_text}; downstream coding sequence is flagged as altered/truncated."
        )
    if consequence == "synonymous":
        return "Variant-applied translation preserves the reference amino-acid sequence."
    if consequence == "missense":
        return "Variant-applied translation changes one amino acid without changing product length."
    if consequence == "stop_lost":
        return "Variant-applied translation replaces the reference stop codon and may extend the protein product."
    if consequence == "inframe_deletion":
        return "Variant-applied translation removes amino acids while preserving the reading frame."
    if consequence == "inframe_insertion":
        return "Variant-applied translation inserts amino acids while preserving the reading frame."
    if consequence == "inframe_duplication":
        return (
            "Variant-applied translation duplicates amino acids while preserving the reading frame."
        )
    if consequence == "delins":
        return "Variant-applied translation replaces one amino-acid interval with another."
    return "Protein product impact is not resolved for this variant."


def _aa_symbol(value: str | None) -> str | None:
    if value is None:
        return None
    return value if len(value) == 1 else value[:3]


def _int_or_none(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _aa_token_count(value: str | None) -> int:
    if not value:
        return 0
    if re.fullmatch(r"(?:[A-Z][a-z]{2})+", value):
        return len(value) // 3
    return len(value)


def _positive_int_or_none(value: int | None) -> int | None:
    if value is None or value <= 0:
        return None
    return value
