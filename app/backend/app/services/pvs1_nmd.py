from __future__ import annotations

from dataclasses import dataclass


LOF_CONSEQUENCES = frozenset(
    {
        "stop_gained",
        "frameshift",
        "frameshift_variant",
        "splice_acceptor_variant",
        "splice_donor_variant",
        "start_lost",
    }
)


@dataclass(frozen=True)
class Pvs1NmdInput:
    consequence: str
    exon_number: int | None = None
    exon_count: int | None = None
    distance_to_last_exon_junction_bp: int | None = None
    critical_region: bool | None = None
    transcript: str | None = None


@dataclass(frozen=True)
class Pvs1NmdAssessment:
    applicable: bool
    pvs1_support: str
    nmd_predicted: bool | None
    reason: str
    warnings: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ("eamos_pure_code_pvs1_nmd_v1",)


def assess_pvs1_nmd(payload: Pvs1NmdInput) -> Pvs1NmdAssessment:
    consequence = payload.consequence.strip().lower()
    if consequence not in LOF_CONSEQUENCES:
        return Pvs1NmdAssessment(
            applicable=False,
            pvs1_support="not_applicable",
            nmd_predicted=None,
            reason="consequence_not_loss_of_function",
        )

    warnings: list[str] = []
    if payload.critical_region is False:
        warnings.append("critical_region_not_established")
        return Pvs1NmdAssessment(
            applicable=True,
            pvs1_support="uncertain",
            nmd_predicted=None,
            reason="loss_of_function_relevance_not_established",
            warnings=tuple(warnings),
        )

    if payload.exon_number is None or payload.exon_count is None:
        return Pvs1NmdAssessment(
            applicable=True,
            pvs1_support="uncertain",
            nmd_predicted=None,
            reason="missing_exon_context",
            warnings=("nmd_exon_context_missing",),
        )

    if payload.exon_count <= 1 or payload.exon_number >= payload.exon_count:
        return Pvs1NmdAssessment(
            applicable=True,
            pvs1_support="uncertain",
            nmd_predicted=False,
            reason="single_or_last_exon_nmd_escape_possible",
            warnings=("nmd_escape_possible",),
        )

    if payload.distance_to_last_exon_junction_bp is not None:
        if payload.distance_to_last_exon_junction_bp <= 50:
            return Pvs1NmdAssessment(
                applicable=True,
                pvs1_support="uncertain",
                nmd_predicted=False,
                reason="variant_within_50bp_of_last_exon_junction",
                warnings=("nmd_escape_possible",),
            )

    return Pvs1NmdAssessment(
        applicable=True,
        pvs1_support="possible",
        nmd_predicted=True,
        reason="premature_termination_before_final_exon_nmd_predicted",
        warnings=tuple(warnings),
    )
