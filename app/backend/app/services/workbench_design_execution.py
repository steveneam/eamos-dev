from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TypeVar

from pydantic import BaseModel

from app.schemas.capabilities import CapabilityExecutionDisclosureV2
from app.schemas.workflow import WorkbenchResultBindingV2
from app.schemas.workbench import (
    CrisprGuide,
    CrisprGuideIdentityV2,
    CrisprOffTargetResponse,
    CrisprResponse,
    CrisprScoreV2,
    CrisprVerifiedLocusV2,
    build_crispr_guide_identity_digest_v2,
)
from app.services.crispr_design import discover_spcas9_pam_sites
from app.services.workbench_design_context import VerifiedWorkbenchContext

WorkbenchResponse = TypeVar("WorkbenchResponse", bound=BaseModel)

WORKBENCH_VALIDATION_MATRIX_V2 = "workbench_live_product_v2.synthetic"


def package_version(distribution: str, *, fallback: str = "unknown") -> str:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return fallback


def executed_disclosure(
    verified: VerifiedWorkbenchContext,
    *,
    capability_id: str,
    claim: str,
    algorithm_id: str,
    algorithm_version: str,
    input_scope: str = "verified_context_v2_selection",
    validation_status: str = "unvalidated",
    warnings: list[str] | None = None,
    requirements: list[str] | None = None,
) -> CapabilityExecutionDisclosureV2:
    disclosure_warnings = list(warnings or [])
    disclosure_requirements = list(requirements or [])
    if not verified.source_identity_verified:
        disclosure_warnings.append("workbench_reference_source_identity_metadata_unavailable")
        disclosure_requirements.append("versioned_reference_source_metadata")
    return CapabilityExecutionDisclosureV2(
        capability_id=capability_id,
        claim=claim,
        execution="eamos_local",
        algorithm_id=algorithm_id,
        algorithm_version=algorithm_version,
        provider_id="eamos",
        provider_version="2",
        input_scope=input_scope,
        source_status="source_backed",
        source_record_ids=[f"reference.{verified.context.reference.sequence_sha256[:24]}"],
        source_release=(
            verified.context.reference.source_release if verified.source_identity_verified else None
        ),
        applicability="applicable",
        validation_status=validation_status,
        validation_matrix_id=WORKBENCH_VALIDATION_MATRIX_V2,
        retention="request_lifetime",
        consent_required=False,
        warnings=disclosure_warnings,
        requirements=disclosure_requirements,
    )


def unavailable_disclosure(
    *,
    capability_id: str,
    claim: str,
    input_scope: str,
    requirements: list[str],
    warnings: list[str] | None = None,
) -> CapabilityExecutionDisclosureV2:
    return CapabilityExecutionDisclosureV2(
        capability_id=capability_id,
        claim=claim,
        execution="unavailable",
        input_scope=input_scope,
        source_status="unavailable",
        applicability="applicable",
        validation_status="unvalidated",
        retention="request_lifetime",
        consent_required=False,
        warnings=list(warnings or []),
        requirements=requirements,
    )


def mounted_artifact_disclosure(
    verified: VerifiedWorkbenchContext,
    *,
    capability_id: str,
    claim: str,
    algorithm_id: str,
    algorithm_version: str,
    input_scope: str,
    artifact_manifest_id: str,
    artifact_sha256: str,
    source_release: str,
    warnings: list[str] | None = None,
    requirements: list[str] | None = None,
) -> CapabilityExecutionDisclosureV2:
    disclosure_warnings = list(warnings or [])
    disclosure_requirements = list(requirements or [])
    if not verified.source_identity_verified:
        disclosure_warnings.append("workbench_reference_source_identity_metadata_unavailable")
        disclosure_requirements.append("versioned_reference_source_metadata")
    return CapabilityExecutionDisclosureV2(
        capability_id=capability_id,
        claim=claim,
        execution="mounted_artifact",
        algorithm_id=algorithm_id,
        algorithm_version=algorithm_version,
        provider_id="eamos",
        provider_version="2",
        input_scope=input_scope,
        source_status="source_backed",
        source_record_ids=[f"reference.{verified.context.reference.sequence_sha256[:24]}"],
        source_release=source_release,
        artifact_manifest_id=artifact_manifest_id,
        artifact_sha256=artifact_sha256,
        applicability="applicable",
        validation_status="unvalidated",
        validation_matrix_id=WORKBENCH_VALIDATION_MATRIX_V2,
        retention="request_lifetime",
        consent_required=False,
        warnings=disclosure_warnings,
        requirements=disclosure_requirements,
    )


def bind_workbench_response_v2(
    response: WorkbenchResponse,
    *,
    verified: VerifiedWorkbenchContext,
    disclosure: CapabilityExecutionDisclosureV2,
) -> WorkbenchResponse:
    binding = WorkbenchResultBindingV2(
        result_context_digest=verified.context.context_digest,
        current_context_digest=verified.context.context_digest,
        state="current",
    )
    payload = response.model_dump(mode="python")
    payload.update(
        {
            "execution_disclosure": disclosure,
            "verified_context": verified.context,
            "context_binding": binding,
        }
    )
    return type(response).model_validate(payload)


def bind_crispr_design_v2(
    response: CrisprResponse,
    *,
    verified: VerifiedWorkbenchContext,
) -> CrisprResponse:
    matched_sites = {
        (site.spacer, site.pam, site.strand, site.cut_position): site
        for site in discover_spcas9_pam_sites(
            verified.selected_sequence,
            strand_filter="both",
        )
    }
    guides: list[CrisprGuide] = []
    omitted = 0
    for guide in response.guides:
        site = matched_sites.get((guide.guide, guide.pam, guide.strand, guide.cut_position))
        if site is None:
            omitted += 1
            continue
        protospacer = verified.genomic_interval(site.spacer_start, site.spacer_end)
        pam = verified.genomic_interval(site.pam_start, site.pam_end)
        cut_position = verified.genomic_coordinate(site.cut_position)
        if protospacer is None or pam is None or cut_position is None:
            omitted += 1
            continue
        strand = verified.genomic_strand(site.strand)
        locus = CrisprVerifiedLocusV2(
            genome_build="GRCh38",
            chromosome=verified.context.reference.chrom,
            protospacer_start=protospacer[0],
            protospacer_end=protospacer[1],
            pam_start=pam[0],
            pam_end=pam[1],
            cut_position=cut_position,
            strand=strand,
        )
        identity_digest = build_crispr_guide_identity_digest_v2(
            guide=guide.guide,
            pam=guide.pam,
            enzyme=response.cas,
            locus=locus,
            context_digest=verified.context.context_digest,
        )
        identity = CrisprGuideIdentityV2(
            guide_id=f"guide-{guide.index}-{identity_digest[:16]}",
            guide=guide.guide,
            pam=guide.pam,
            enzyme=response.cas,
            locus=locus,
            context_digest=verified.context.context_digest,
            identity_sha256=identity_digest,
        )
        guide_disclosure = executed_disclosure(
            verified,
            capability_id="crispr_guide_discovery",
            claim="Scanned the verified selection for SpCas9 NGG protospacers",
            algorithm_id="spcas9_ngg_scan",
            algorithm_version="2.0.0",
            warnings=[
                "advanced_on_target_model_unavailable",
                "genome_wide_off_target_enumeration_not_run",
            ],
            requirements=["rs3_model_runtime", "grch38_crispr_offtarget_index"],
        )
        scores = [
            _score(
                verified,
                identity=identity,
                score_id="on-target-descriptive",
                family="on_target",
                algorithm_id="eamos_gc_poly_t_heuristic",
                algorithm_version="1.0.0",
                value=guide.on_target_score,
                scale_min=0.0,
                scale_max=100.0,
                direction="descriptive",
                claim="Computed a descriptive GC/poly-T guide ranking heuristic",
                input_scope="verified_selection_only_not_ruleset3",
                warnings=["not_ruleset3", "not_an_efficiency_probability"],
            ),
            _score(
                verified,
                identity=identity,
                score_id="off-target-context-risk",
                family="off_target",
                algorithm_id="hsu_mit_in_context_risk",
                algorithm_version="1.0.0",
                value=guide.off_target_score,
                scale_min=0.0,
                scale_max=100.0,
                direction="lower_is_better",
                claim="Computed Hsu/MIT risk over candidates in the verified selection only",
                input_scope="verified_selection_only_not_genome_wide",
                warnings=["not_genome_wide"],
            ),
        ]
        guides.append(
            guide.model_copy(
                update={
                    "strand": strand,
                    "identity": identity,
                    "scores": scores,
                    "execution_disclosure": guide_disclosure,
                }
            )
        )

    warnings = [
        "advanced_on_target_model_unavailable",
        "genome_wide_off_target_enumeration_not_run",
    ]
    if omitted:
        warnings.append("crispr_guides_without_contiguous_genomic_identity_omitted")
    outer = executed_disclosure(
        verified,
        capability_id="crispr_guide_discovery",
        claim="Scanned the verified selection for SpCas9 NGG protospacers",
        algorithm_id="spcas9_ngg_scan",
        algorithm_version="2.0.0",
        warnings=warnings,
        requirements=["rs3_model_runtime", "grch38_crispr_offtarget_index"],
    )
    bound = response.model_copy(update={"guides": guides, "ssodn": None})
    return bind_workbench_response_v2(bound, verified=verified, disclosure=outer)


def bind_crispr_offtarget_v2(
    response: CrisprOffTargetResponse,
    *,
    verified: VerifiedWorkbenchContext,
    identity: CrisprGuideIdentityV2,
    disclosure: CapabilityExecutionDisclosureV2,
) -> CrisprOffTargetResponse:
    sites = []
    for index, site in enumerate(response.sites, start=1):
        score = _score(
            verified,
            identity=identity,
            score_id=f"mit-cutting-{index}",
            family="off_target",
            algorithm_id="hsu_mit_cutting_score",
            algorithm_version="1.0.0",
            value=round(site.score * 100.0, 6),
            scale_min=0.0,
            scale_max=100.0,
            direction="descriptive",
            claim="Computed Hsu/MIT cutting score for an indexed candidate",
            input_scope="verified_genome_wide_index_candidate",
            warnings=["cfd_score_unavailable"],
        )
        sites.append(site.model_copy(update={"scores": [score]}))
    enriched = response.model_copy(
        update={
            "sites": sites,
            "guide_identity": identity,
        }
    )
    return bind_workbench_response_v2(
        enriched,
        verified=verified,
        disclosure=disclosure,
    )


def _score(
    verified: VerifiedWorkbenchContext,
    *,
    identity: CrisprGuideIdentityV2,
    score_id: str,
    family: str,
    algorithm_id: str,
    algorithm_version: str,
    value: float,
    scale_min: float,
    scale_max: float,
    direction: str,
    claim: str,
    input_scope: str,
    warnings: list[str],
) -> CrisprScoreV2:
    disclosure = executed_disclosure(
        verified,
        capability_id=f"crispr_score.{algorithm_id}",
        claim=claim,
        algorithm_id=algorithm_id,
        algorithm_version=algorithm_version,
        input_scope=input_scope,
        validation_status="unvalidated",
        warnings=warnings,
        requirements=(
            ["rs3_model_runtime"] if family == "on_target" else ["grch38_crispr_offtarget_index"]
        ),
    )
    return CrisprScoreV2(
        score_id=score_id,
        family=family,
        algorithm_id=algorithm_id,
        algorithm_version=algorithm_version,
        value=value,
        scale_min=scale_min,
        scale_max=scale_max,
        direction=direction,
        context_digest=verified.context.context_digest,
        guide_identity_sha256=identity.identity_sha256,
        execution_disclosure=disclosure,
    )
