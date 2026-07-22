from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import inf
from typing import get_args

import pytest
from pydantic import ValidationError

from app.schemas.batch import (
    BatchAlleleIdentityV2,
    BatchAlleleV2,
    BatchCreateResponse,
    BatchExportV2,
    BatchFieldExecutionV2,
    BatchFilterDispositionV2,
    BatchFilterPlanV2,
    BatchInputEnvelopeV2,
    BatchJob,
    BatchPage,
    BatchPagingV2,
    BatchResult,
    BatchSampleProvenanceV2,
    BatchSourceSnapshotV2,
    BatchUploadResponse,
)
from app.schemas.capabilities import CapabilityExecutionDisclosureV2
from app.schemas.panels import PanelSourceSnapshotV2
from app.schemas.panels import PanelSummary
from app.schemas.paper_variants import (
    PaperAiAdjudicationV2,
    PaperDocumentBundleRequestV2,
    PaperDocumentBundleV2,
    PaperDocumentExtractionV2,
    PaperDocumentMetadataV2,
    PaperDocumentUploadV2,
    PaperEvidenceSpanV2,
    PaperMentionResolutionV2,
    PaperPageExtractionQualityV2,
    PaperVariantMentionV2,
    PaperVariantsExtractResponse,
)
from app.schemas.report import (
    ReportExecutionStateV2,
    ReportPredictorExecutionV2,
    ReportSectionExecutionV2,
    ReportSectionIdV2,
)
from app.schemas.source_disclosure import SourceDisclosure
from app.schemas.workbench import (
    AlignReferenceResponse,
    AlignResponse,
    AlignTraceResponse,
    CrisprGuide,
    CrisprGuideIdentityV2,
    CrisprOffTargetResponse,
    CrisprOffTargetSite,
    CrisprResponse,
    CrisprScoreV2,
    CrisprScreeningPrimerResponse,
    CrisprSsodnResponse,
    CrisprTideResponse,
    CrisprVerifiedLocusV2,
    PrimerRequest,
    PrimerResponse,
    build_crispr_guide_identity_digest_v2,
)
from app.schemas.workflow import (
    CanonicalVariantRefV1,
    ProcessingDisclosureV1,
    SelectionRangeV1,
    WorkbenchDesignContextV1,
    WorkbenchDesignContextV2,
    WorkbenchReferenceBasisV2,
    WorkbenchResultBindingV2,
    WorkbenchSparseEditV2,
    build_workbench_design_context_digest_v1,
    build_workbench_design_context_digest_v2,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
NOW = datetime(2026, 7, 22, 17, 0, tzinfo=UTC)


def _assert_invalid(model_type, payload: dict, match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        model_type(**payload)


def _assert_invalid_update(instance, match: str, **updates) -> None:
    _assert_invalid(type(instance), {**instance.model_dump(), **updates}, match)


def _variant(*, resolved: bool = True, support: bool = True) -> CanonicalVariantRefV1:
    return CanonicalVariantRefV1(
        schema_version="canonical_variant_ref.v1",
        gene="RPE65",
        cdna="c.260A>G",
        transcript="NM_000329.3" if resolved else None,
        protein_hgvs="p.Asp87Gly" if resolved else None,
        genomic_hg38="1-68444869-T-C" if resolved else None,
        variant_key="RPE65:NM_000329.3:c.260A>G",
        species="human",
        genome_build="GRCh38",
        resolution_status="resolved" if resolved else "unresolved",
        source_support=["variantvalidator:record-1"] if support else [],
        warnings=[],
    )


def _selection(
    *,
    basis: str = "reference",
    revision: int = 0,
    strand: str = "+",
    orientation: str = "genomic_forward",
    sequence_sha256: str = SHA_B,
) -> SelectionRangeV1:
    return SelectionRangeV1(
        schema_version="selection_range.v1",
        variant_key="RPE65:NM_000329.3:c.260A>G",
        transcript="NM_000329.3",
        genome_build="GRCh38",
        chrom="chr1",
        genomic_start=110,
        genomic_end=150,
        strand=strand,
        orientation=orientation,
        sequence_basis=basis,
        edit_revision=revision,
        sequence_sha256=sequence_sha256,
        cdna_start=240,
        cdna_end=280,
        cds_start=200,
        cds_end=240,
        protein_start=80,
        protein_end=94,
        overlaps=["cds", "exon"],
    )


def _reference() -> WorkbenchReferenceBasisV2:
    return WorkbenchReferenceBasisV2(
        transcript="NM_000329.3",
        genome_build="GRCh38",
        chrom="chr1",
        genomic_start=100,
        genomic_end=199,
        strand="+",
        orientation="genomic_forward",
        source_id="ucsc_hg38",
        source_release="hg38-2026-06",
        source_record_id="chr1:100-199",
        sequence_length=100,
        sequence_sha256=SHA_A,
    )


def _capability(
    *,
    capability_id: str = "variant_resolution",
    algorithm_id: str = "eamos_resolver",
    algorithm_version: str = "2.0.0",
    execution: str = "eamos_local",
    source_status: str = "source_backed",
    applicability: str = "applicable",
    validation_status: str = "validated",
    requirements: list[str] | None = None,
    source_record_ids: list[str] | None = None,
    consent_required: bool = False,
    retention: str = "none",
    retention_expires_at: datetime | None = None,
    **extra,
) -> CapabilityExecutionDisclosureV2:
    payload = {
        "capability_id": capability_id,
        "claim": f"Executed {capability_id} on the declared input",
        "execution": execution,
        "algorithm_id": algorithm_id,
        "algorithm_version": algorithm_version,
        "provider_id": "eamos" if execution != "external_provider" else "provider_x",
        "provider_version": "2026-07",
        "input_scope": "declared_input",
        "source_status": source_status,
        "source_record_ids": source_record_ids or [],
        "source_release": "release-2026-07",
        "applicability": applicability,
        "validation_status": validation_status,
        "validation_matrix_id": "live-product-v2",
        "retention": retention,
        "retention_expires_at": retention_expires_at,
        "consent_required": consent_required,
        "warnings": [],
        "requirements": requirements or [],
    }
    payload.update(extra)
    return CapabilityExecutionDisclosureV2(**payload)


def _unavailable(
    *,
    capability_id: str,
    applicability: str = "applicable",
) -> CapabilityExecutionDisclosureV2:
    return _capability(
        capability_id=capability_id,
        execution="unavailable",
        source_status="not_applicable" if applicability == "not_applicable" else "unavailable",
        applicability=applicability,
        validation_status="not_applicable" if applicability == "not_applicable" else "unvalidated",
        requirements=[] if applicability == "not_applicable" else [f"configure_{capability_id}"],
        provider_id=None,
        provider_version=None,
        source_release=None,
    )


def _failed(*, capability_id: str) -> CapabilityExecutionDisclosureV2:
    return _capability(
        capability_id=capability_id,
        execution="unavailable",
        source_status="unavailable",
        validation_status="failed",
        requirements=[f"repair_{capability_id}"],
        provider_id=None,
        provider_version=None,
        source_release=None,
    )


def _native_context(
    selection: SelectionRangeV1,
    edits: list[WorkbenchSparseEditV2],
) -> WorkbenchDesignContextV2:
    payload = {
        "variant": _variant(),
        "reference": _reference(),
        "selection": selection,
        "edits": edits,
        "revision": selection.edit_revision,
    }
    return WorkbenchDesignContextV2(
        **payload,
        context_digest=build_workbench_design_context_digest_v2(**payload),
    )


def _edited_context() -> WorkbenchDesignContextV2:
    selection = _selection(basis="edited", revision=1)
    edit = WorkbenchSparseEditV2(
        edit_id="edit-1",
        operation="substitution",
        start_offset=20,
        end_offset=21,
        reference_bases="A",
        alternate_bases="G",
    )
    return _native_context(selection, [edit])


def _guide_identity(
    context: WorkbenchDesignContextV2,
    locus: CrisprVerifiedLocusV2,
    *,
    guide: str = "ACGTACGTACGTACGTACGT",
    pam: str = "AGG",
    guide_id: str = "guide-1",
) -> CrisprGuideIdentityV2:
    digest = build_crispr_guide_identity_digest_v2(
        guide=guide,
        pam=pam,
        enzyme="SpCas9",
        locus=locus,
        context_digest=context.context_digest,
    )
    return CrisprGuideIdentityV2(
        guide_id=guide_id,
        guide=guide,
        pam=pam,
        enzyme="SpCas9",
        locus=locus,
        context_digest=context.context_digest,
        identity_sha256=digest,
    )


def test_capability_disclosure_is_strict_fail_closed_and_privacy_safe() -> None:
    disclosure = _capability(source_record_ids=["vv-record-1"])
    assert disclosure.schema_version == "capability_execution.v2"
    assert disclosure.model_dump()["source_record_ids"] == ["vv-record-1"]

    with pytest.raises(ValidationError, match="extra_forbidden"):
        _capability(raw_sequence="ACGT")
    with pytest.raises(ValidationError, match="fixture source_status"):
        _capability(source_status="fixture")
    with pytest.raises(ValidationError, match="concrete requirement"):
        _capability(
            execution="unavailable", source_status="unavailable", validation_status="unvalidated"
        )
    with pytest.raises(ValidationError, match="cannot claim validated"):
        _capability(
            execution="unavailable",
            source_status="unavailable",
            requirements=["mount_asset"],
        )
    with pytest.raises(ValidationError, match="explicit consent"):
        _capability(execution="external_provider", consent_required=False)


def test_capability_v1_bridge_is_conservative_and_has_removal_seam() -> None:
    source = SourceDisclosure(
        source_status="fallback",
        provider_id="legacy_provider",
        provider_label="Legacy provider",
        requirements=[],
    )
    processing = ProcessingDisclosureV1(
        execution="eamos_backend",
        provider_id="eamos",
        provider_label="Eamos",
        input_classes=["variant_id"],
        raw_input_persisted=False,
        retention="none",
        expires_at=None,
        user_deletable=False,
        consent_required=False,
        warnings=[],
    )
    bridged = CapabilityExecutionDisclosureV2.from_legacy(
        capability_id="legacy_lookup",
        claim="Legacy lookup migration",
        algorithm_id="legacy_lookup",
        algorithm_version="1",
        input_scope="declared_input",
        source=source,
        processing=processing,
    )

    assert bridged.execution == "unavailable"
    assert bridged.requirements == ["replace_legacy_fallback_path"]
    assert "legacy_source_status:fallback" in bridged.warnings


def test_workbench_context_v2_binds_full_basis_edits_and_staleness() -> None:
    context = _edited_context()
    assert (
        PrimerRequest(
            gene="RPE65",
            cdna="c.260A>G",
            design_context_v2=context,
        ).design_context_v2
        == context
    )

    current = WorkbenchResultBindingV2(
        result_context_digest=context.context_digest,
        current_context_digest=context.context_digest,
        state="current",
    )
    stale = WorkbenchResultBindingV2(
        result_context_digest=context.context_digest,
        current_context_digest=SHA_C,
        state="stale",
        stale_reason="selection changed after execution",
    )
    assert current.stale_reason is None
    assert stale.state == "stale"

    with pytest.raises(ValidationError, match="strand"):
        WorkbenchDesignContextV2(
            **{
                **context.model_dump(),
                "selection": _selection(
                    basis="edited",
                    revision=1,
                    strand="-",
                    orientation="genomic_forward",
                ),
            }
        )
    with pytest.raises(ValidationError, match="deterministic"):
        edits = [
            WorkbenchSparseEditV2(
                edit_id="edit-2",
                operation="insertion",
                start_offset=30,
                end_offset=30,
                reference_bases="",
                alternate_bases="A",
            ),
            context.edits[0],
        ]
        _native_context(context.selection, edits)
    with pytest.raises(ValidationError, match="must not overlap"):
        edits = [
            WorkbenchSparseEditV2(
                edit_id="edit-a",
                operation="deletion",
                start_offset=20,
                end_offset=22,
                reference_bases="AA",
                alternate_bases="",
            ),
            WorkbenchSparseEditV2(
                edit_id="edit-b",
                operation="substitution",
                start_offset=21,
                end_offset=22,
                reference_bases="A",
                alternate_bases="G",
            ),
        ]
        _native_context(context.selection, edits)


def test_native_v2_reference_basis_is_exact_and_edit_free() -> None:
    with pytest.raises(ValidationError, match="must change"):
        WorkbenchSparseEditV2(
            edit_id="no-op",
            operation="substitution",
            start_offset=20,
            end_offset=21,
            reference_bases="A",
            alternate_bases="A",
        )
    selection = _selection(sequence_sha256=SHA_A)
    context = _native_context(selection, [])
    assert context.selection.sequence_sha256 == context.reference.sequence_sha256

    with pytest.raises(ValidationError, match="reference selection digest"):
        _native_context(_selection(sequence_sha256=SHA_B), [])

    with pytest.raises(ValidationError, match="cannot carry sparse edits"):
        _native_context(selection, _edited_context().edits)


@pytest.mark.parametrize(("basis", "revision"), [("variant", 0), ("edited", 1)])
def test_native_v2_non_reference_basis_requires_replayable_edits(
    basis: str,
    revision: int,
) -> None:
    with pytest.raises(ValidationError, match="require replayable sparse edits"):
        _native_context(_selection(basis=basis, revision=revision), [])


def test_workbench_context_v1_shim_preserves_legacy_digest_without_overclaiming_edits() -> None:
    variant = _variant()
    selection = _selection()
    legacy = WorkbenchDesignContextV1(
        schema_version="workbench_design_context.v1",
        variant=variant,
        selection=selection,
        context_digest=build_workbench_design_context_digest_v1(variant, selection),
    )
    migrated = WorkbenchDesignContextV2.from_v1(legacy, reference=_reference())

    assert migrated.compatibility_origin == "workbench_design_context.v1"
    assert migrated.legacy_context_digest == legacy.context_digest
    assert migrated.edits == []


def test_workbench_response_v2_envelope_is_atomic_and_digest_bound() -> None:
    response_models = (
        PrimerResponse,
        CrisprResponse,
        CrisprSsodnResponse,
        CrisprOffTargetResponse,
        CrisprScreeningPrimerResponse,
        CrisprTideResponse,
        AlignTraceResponse,
        AlignResponse,
        AlignReferenceResponse,
    )
    assert all(
        "_WorkbenchResponseV2Envelope" in {base.__name__ for base in model.__mro__}
        for model in response_models
    )
    context = _edited_context()
    binding = WorkbenchResultBindingV2(
        result_context_digest=context.context_digest,
        current_context_digest=context.context_digest,
        state="current",
    )
    response = PrimerResponse(
        mode="sanger",
        pairs=[],
        execution_disclosure=_capability(),
        verified_context=context,
        context_binding=binding,
    )
    assert response.context_binding.result_context_digest == context.context_digest
    with pytest.raises(ValidationError, match="supplied together"):
        PrimerResponse(mode="sanger", pairs=[], verified_context=context)
    with pytest.raises(ValidationError, match="verified context digest"):
        PrimerResponse(
            mode="sanger",
            pairs=[],
            execution_disclosure=_capability(),
            verified_context=context,
            context_binding=WorkbenchResultBindingV2(
                result_context_digest=SHA_C,
                current_context_digest=SHA_C,
                state="current",
            ),
        )


def test_crispr_score_is_algorithm_explicit_finite_and_guide_bound() -> None:
    context = _edited_context()
    locus = CrisprVerifiedLocusV2(
        genome_build="GRCh38",
        chromosome="chr1",
        protospacer_start=120,
        protospacer_end=139,
        pam_start=140,
        pam_end=142,
        cut_position=137,
        strand="+",
    )
    guide = "ACGTACGTACGTACGTACGT"
    identity = _guide_identity(context, locus)
    for locus_update, message in (
        ({"protospacer_end": locus.protospacer_end - 1}, "protospacer interval length"),
        ({"pam_end": locus.pam_end - 1}, "PAM interval length"),
    ):
        short_locus = CrisprVerifiedLocusV2(**{**locus.model_dump(), **locus_update})
        with pytest.raises(ValidationError, match=message):
            _guide_identity(context, short_locus, guide_id="bad-length")
    score_disclosure = _capability(
        capability_id="rs3",
        algorithm_id="rs3",
        algorithm_version="1.2.0",
        source_status="not_required",
    )
    score = CrisprScoreV2(
        score_id="rs3-on-target",
        family="on_target",
        algorithm_id="rs3",
        algorithm_version="1.2.0",
        value=72.5,
        scale_min=0,
        scale_max=100,
        direction="higher_is_better",
        context_digest=context.context_digest,
        guide_identity_sha256=identity.identity_sha256,
        execution_disclosure=score_disclosure,
    )
    row = CrisprGuide(
        index=1,
        cut_position=37,
        strand="+",
        guide=guide,
        pam="AGG",
        on_target_score=72.5,
        off_target_score=4.0,
        gc_percent=50,
        identity=identity,
        scores=[score],
    )
    assert row.scores[0].algorithm_id == "rs3"

    _assert_invalid_update(score, "finite number", value=inf)
    _assert_invalid_update(
        score,
        "executed capability",
        execution_disclosure=_unavailable(capability_id="rs3"),
    )
    _assert_invalid_update(
        row,
        "exact guide identity",
        scores=[{**score.model_dump(), "context_digest": SHA_C}],
    )
    second_guide = "TGCATGCATGCATGCATGCA"
    second_locus = CrisprVerifiedLocusV2(
        **{
            **locus.model_dump(),
            "protospacer_start": 150,
            "protospacer_end": 169,
            "pam_start": 170,
            "pam_end": 172,
            "cut_position": 167,
        }
    )
    second_identity = _guide_identity(
        context, second_locus, guide=second_guide, pam="TGG", guide_id="guide-2"
    )
    _assert_invalid_update(
        row,
        "exact guide identity",
        guide=second_guide,
        pam="TGG",
        identity=second_identity,
    )
    site = CrisprOffTargetSite(
        sequence=guide,
        pam="AGG",
        score=0.9,
        mismatches=0,
        chromosome="chr1",
        strand="+",
        position=120,
        on_target=True,
        scores=[score],
    )
    with pytest.raises(ValidationError, match="exact guide identity"):
        CrisprOffTargetResponse(
            genome_build="GRCh38",
            sites=[site],
            guide_identity=second_identity,
        )


def _paper_bundle() -> PaperDocumentBundleV2:
    return PaperDocumentBundleV2(
        bundle_id="paper-bundle-1",
        documents=[
            PaperDocumentMetadataV2(
                document_id="main-pdf",
                role="main",
                kind="pdf",
                filename="paper.pdf",
                media_type="application/pdf",
                size_bytes=1024,
                sha256=SHA_A,
                page_count=1,
                extraction_engine="pdfium",
                extraction_engine_version="133.0",
            )
        ],
        input_digest=SHA_B,
    )


def _paper_extraction() -> PaperDocumentExtractionV2:
    mention = PaperVariantMentionV2(
        mention_id="mention-1",
        notation_type="cdna",
        biological_context="clinical_allele",
        extraction_layer="l1_structured",
        confidence=0.99,
        span=PaperEvidenceSpanV2(
            document_id="main-pdf",
            page_number=1,
            section="Results",
            start_character=40,
            end_character=48,
            exact_text="c.260A>G",
            bounded_quote="The proband carried RPE65 c.260A>G.",
        ),
        gene_evidence=["RPE65"],
        transcript_evidence=["NM_000329.3"],
    )
    resolution = PaperMentionResolutionV2(
        mention_id="mention-1",
        status="resolved",
        canonical_variant=_variant(),
        candidate_ids=["candidate-1"],
        execution_disclosure=_capability(
            source_record_ids=["variantvalidator-record-1"],
        ),
    )
    return PaperDocumentExtractionV2(
        bundle=_paper_bundle(),
        deterministic_digest=SHA_C,
        page_quality=[
            PaperPageExtractionQualityV2(
                document_id="main-pdf",
                page_number=1,
                quality="good",
                extracted_character_count=1200,
                replacement_character_ratio=0,
            )
        ],
        mentions=[mention],
        resolutions=[resolution],
        execution_disclosure=_capability(
            capability_id="paper_l1_l3",
            algorithm_id="eamos_paper_extract",
            source_status="not_required",
        ),
    )


def test_paper_upload_handles_are_request_only_and_output_graph_is_source_bound() -> None:
    request = PaperDocumentBundleRequestV2(
        bundle_id="paper-bundle-1",
        input_digest=SHA_B,
        documents=[
            PaperDocumentUploadV2(
                document_id="main-pdf",
                role="main",
                kind="pdf",
                upload_ref="upload-owner-bound-1",
                filename="paper.pdf",
                media_type="application/pdf",
                size_bytes=1024,
                sha256=SHA_A,
            )
        ],
    )
    extraction = _paper_extraction()
    response = PaperVariantsExtractResponse(
        generated_at=NOW,
        llm_provider="legacy_local",
        candidate_count=1,
        validated_count=1,
        document_extraction=extraction,
        execution_disclosure=extraction.execution_disclosure,
    )

    assert request.documents[0].upload_ref == "upload-owner-bound-1"
    assert (
        "upload_ref"
        not in PaperDocumentBundleV2.model_json_schema()["$defs"]["PaperDocumentMetadataV2"][
            "properties"
        ]
    )
    assert "upload_ref" not in response.model_dump_json()
    assert response.document_extraction.resolutions[0].status == "resolved"

    for span_update, message in (
        ({"end_character": 49}, "span length"),
        ({"bounded_quote": "No matching notation here."}, "contain exact_text"),
    ):
        _assert_invalid_update(extraction.mentions[0].span, message, **span_update)
    _assert_invalid(
        PaperVariantsExtractResponse,
        response.model_dump(exclude={"execution_disclosure"}),
        "supplied together",
    )
    _assert_invalid_update(
        response,
        "must match document extraction",
        execution_disclosure=_capability(capability_id="other_extraction"),
    )
    for count_field, message in (
        ("candidate_count", "deterministic mention count"),
        ("validated_count", "resolved mention count"),
    ):
        _assert_invalid_update(response, message, **{count_field: 2})

    with pytest.raises(ValidationError, match="extra_forbidden"):
        PaperDocumentMetadataV2(
            **{
                **_paper_bundle().documents[0].model_dump(),
                "upload_ref": "must-not-echo",
            }
        )
    with pytest.raises(ValidationError, match="source-backed canonical support"):
        PaperMentionResolutionV2(
            mention_id="mention-1",
            status="resolved",
            canonical_variant=_variant(support=False),
            candidate_ids=["candidate-1"],
            execution_disclosure=_capability(source_record_ids=["record-1"]),
        )
    with pytest.raises(ValidationError, match="document in the bundle"):
        PaperDocumentExtractionV2(
            **{
                **extraction.model_dump(),
                "mentions": [
                    {
                        **extraction.mentions[0].model_dump(),
                        "span": {
                            **extraction.mentions[0].span.model_dump(),
                            "document_id": "foreign-document",
                        },
                    }
                ],
            }
        )


def test_paper_ai_adjudication_is_digest_bound_and_advisory_only() -> None:
    extraction = _paper_extraction()
    advisory = PaperAiAdjudicationV2(
        mention_id="mention-1",
        deterministic_digest=extraction.deterministic_digest,
        recommendation="needs_review",
        reason="The notation is split across a table boundary.",
        execution_disclosure=_capability(
            capability_id="paper_l4_verifier",
            execution="external_provider",
            source_status="not_required",
            consent_required=True,
            retention="request_lifetime",
        ),
    )
    with_advisory = PaperDocumentExtractionV2(
        **{**extraction.model_dump(), "ai_adjudications": [advisory]}
    )

    assert with_advisory.ai_adjudications[0].advisory_only is True
    assert "canonical_variant" not in PaperAiAdjudicationV2.model_fields
    with pytest.raises(ValidationError, match="deterministic evidence digest"):
        PaperDocumentExtractionV2(
            **{
                **extraction.model_dump(),
                "ai_adjudications": [{**advisory.model_dump(), "deterministic_digest": SHA_A}],
            }
        )


def _batch_envelope() -> BatchInputEnvelopeV2:
    return BatchInputEnvelopeV2(
        format="vcf_gz",
        analysis_scope="wes",
        cohort_model="proband",
        genome_build="GRCh38",
        source_sha256=SHA_A,
        compressed_bytes=1000,
        decompressed_bytes=5000,
        raw_record_count=75_000,
        sample_count=1,
        post_filter_variant_cap=5000,
        accepted_variant_classes=["snv", "short_indel"],
    )


def _batch_snapshot() -> BatchSourceSnapshotV2:
    return BatchSourceSnapshotV2(
        snapshot_id="batch-snapshot-1",
        created_at=NOW,
        genome_build="GRCh38",
        reference_release="GRCh38.p14",
        capabilities=[_capability(source_record_ids=["source-record-1"])],
    )


def _batch_field_states() -> list[BatchFieldExecutionV2]:
    executed = {
        "gene",
        "hgvs_c",
        "clinvar_verdict",
        "gnomad_af",
        "predictor_ensemble",
    }
    states: list[BatchFieldExecutionV2] = []
    for field_name in (
        "gene",
        "hgvs_c",
        "hgvs_p",
        "clinvar_verdict",
        "gnomad_af",
        "predictor_ensemble",
        "acmg_classification",
    ):
        states.append(
            BatchFieldExecutionV2(
                field_name=field_name,
                value_status="executed" if field_name in executed else "not_applicable",
                execution_disclosure=(
                    _capability(
                        capability_id=f"batch_{field_name}",
                        source_record_ids=[f"record-{field_name}"],
                    )
                    if field_name in executed
                    else _unavailable(
                        capability_id=f"batch_{field_name}", applicability="not_applicable"
                    )
                ),
            )
        )
    return states


def _batch_result() -> BatchResult:
    original = BatchAlleleV2(
        genome_build="GRCh38",
        chromosome="chr1",
        position=68444869,
        reference="T",
        alternate="C",
    )
    identity = BatchAlleleIdentityV2(
        original=original,
        normalized=original,
        status="normalized",
        source_record_index=42,
        normalization_algorithm_id="bcftools_norm",
        normalization_algorithm_version="1.22",
        reference_manifest_id="grch38-p14",
        reference_sha256=SHA_B,
    )
    return BatchResult(
        variant_key="1-68444869-T-C",
        gene="RPE65",
        hgvs_c="c.260A>G",
        hgvs_p=None,
        clinvar_verdict="Pathogenic",
        gnomad_af=0.0001,
        predictor_ensemble={"consensus": "damaging"},
        acmg_classification=None,
        allele_identity_v2=identity,
        source_snapshot_id="batch-snapshot-1",
        field_executions_v2=_batch_field_states(),
    )


def _batch_disposition(**updates) -> BatchFilterDispositionV2:
    payload = {
        "stage": "pre_annotation",
        "outcome": "excluded",
        "reason": "quality",
        "detail": "Bounded filter detail.",
        "source_snapshot_id": "batch-snapshot-1",
    }
    return BatchFilterDispositionV2(**{**payload, **updates})


def _batch_job(*, limit: int = 100, include_export: bool = False) -> BatchJob:
    paging = BatchPagingV2(
        snapshot_id="batch-snapshot-1",
        limit=limit,
        total=1,
        has_more=False,
    )
    exports = []
    if include_export:
        exports.append(
            BatchExportV2(
                export_id="export-1",
                format="jsonl",
                state="ready",
                source_snapshot_id="batch-snapshot-1",
                row_count=1,
                sha256=SHA_C,
                expires_at=NOW + timedelta(hours=1),
            )
        )
    return BatchJob(
        job_id="batch-1",
        status="completed",
        n_input=75_000,
        n_to_lookup=1,
        n_after_filters=1,
        est_seconds=10,
        done=1,
        total=1,
        results=[_batch_result()],
        page=BatchPage(limit=limit, total=1, paging_v2=paging),
        input_envelope_v2=_batch_envelope(),
        source_snapshot_v2=_batch_snapshot(),
        exports_v2=exports,
    )


def _report_section(*, state="ready", disclosures=None, **updates):
    payload = {
        "section_id": "computational_deep_dive",
        "state": state,
        "match_level": "exact_allele",
        "source_snapshot_id": "report-snapshot-1",
        "execution_disclosures": (
            [_capability(capability_id="lookup", source_record_ids=["record-1"])]
            if disclosures is None
            else disclosures
        ),
    }
    return ReportSectionExecutionV2(**{**payload, **updates})


def _report_state(*, coverage="partial", variant=None, sections=None, predictors=None):
    return ReportExecutionStateV2(
        coverage=coverage,
        canonical_variant=variant or _variant(),
        source_snapshot_id="report-snapshot-1",
        sections=[] if sections is None else sections,
        predictors=[] if predictors is None else predictors,
    )


def _report_predictor(*, state, applicability, disclosure):
    return ReportPredictorExecutionV2(
        predictor_id="spliceai",
        applicability=applicability,
        state=state,
        source_snapshot_id="report-snapshot-1",
        execution_disclosure=disclosure,
    )


def test_batch_v2_requires_source_backed_scope_and_coherent_snapshots() -> None:
    with pytest.raises(ValidationError, match="interval_snapshot_id"):
        BatchFilterPlanV2(
            interval_scope="capture_bed",
            pass_only=True,
        )
    plan = BatchFilterPlanV2(
        interval_scope="capture_bed",
        interval_snapshot_id="capture-bed-snapshot-1",
    )
    assert plan.interval_snapshot_id == "capture-bed-snapshot-1"

    job = _batch_job(include_export=True)
    result = job.results[0]
    paging = job.page.paging_v2
    assert paging is not None
    assert job.results[0].source_snapshot_id == job.source_snapshot_v2.snapshot_id

    with pytest.raises(ValidationError, match="value presence"):
        BatchResult(**{**result.model_dump(), "gene": None})
    with pytest.raises(ValidationError, match="job source snapshot"):
        BatchJob(
            **{
                **job.model_dump(),
                "page": {
                    "limit": 100,
                    "next_cursor": None,
                    "total": 1,
                    "paging_v2": {**paging.model_dump(), "snapshot_id": "other-snapshot"},
                },
            }
        )


def test_batch_v2_filter_upload_row_and_page_truth_fail_closed() -> None:
    for stage in ("pre_annotation", "post_annotation"):
        assert _batch_disposition(
            stage=stage,
            outcome="deferred",
            reason="source_unavailable",
        )
    for stage, outcome, reason, message in (
        ("pre_annotation", "excluded", "consequence", "processing stage"),
        ("post_annotation", "excluded", "quality", "processing stage"),
        ("pre_annotation", "excluded", "source_unavailable", "must agree"),
        ("pre_annotation", "deferred", "quality", "must agree"),
    ):
        with pytest.raises(ValidationError, match=message):
            _batch_disposition(stage=stage, outcome=outcome, reason=reason)

    envelope = _batch_envelope()
    upload = BatchUploadResponse(
        upload_ref="owner-bound-upload",
        expires_at=NOW + timedelta(minutes=30),
        single_use=True,
        input_envelope_v2=envelope,
    )
    assert upload.single_use is True
    for update, message in (
        ({"expires_at": None}, "require expires_at"),
        ({"expires_at": NOW.replace(tzinfo=None)}, "requires a timezone"),
        ({"single_use": False}, "single_use=true"),
    ):
        _assert_invalid_update(upload, message, **update)

    create = BatchCreateResponse(
        job_id="batch-1",
        n_input=75_000,
        n_to_lookup=1,
        est_seconds=10,
        input_envelope_v2=envelope,
        source_snapshot_v2=_batch_snapshot(),
    )
    _assert_invalid(
        BatchCreateResponse,
        create.model_dump(exclude={"source_snapshot_v2"}),
        "together",
    )

    result = _batch_result()
    for missing in ("allele_identity_v2", "field_executions_v2"):
        _assert_invalid(
            BatchResult,
            result.model_dump(exclude={missing}),
            "completed V2 rows",
        )
    bad_disposition = _batch_disposition(source_snapshot_id="other-snapshot")
    _assert_invalid_update(
        result,
        "row source snapshot",
        filter_dispositions_v2=[bad_disposition],
    )

    sample = BatchSampleProvenanceV2(
        sample_key="sample-1",
        source_sample_index=0,
        genotype="0/1",
        phased=False,
    )
    for duplicate in (
        {**sample.model_dump(), "source_sample_index": 1},
        {**sample.model_dump(), "sample_key": "sample-2"},
    ):
        _assert_invalid_update(
            result,
            "sample provenance",
            sample_provenance_v2=[sample, duplicate],
        )

    for value_status, disclosure in (
        (
            "unavailable",
            _unavailable(capability_id="gene", applicability="not_applicable"),
        ),
        ("not_applicable", _unavailable(capability_id="gene")),
    ):
        with pytest.raises(ValidationError, match="exactly match"):
            BatchFieldExecutionV2(
                field_name="gene",
                value_status=value_status,
                execution_disclosure=disclosure,
            )

    job = _batch_job(limit=1)
    paging = job.page.paging_v2
    assert paging is not None
    _assert_invalid_update(
        job,
        "post-filter variant cap",
        n_to_lookup=envelope.post_filter_variant_cap + 1,
    )
    _assert_invalid_update(
        job,
        "job source snapshot",
        filter_dispositions_v2=[bad_disposition],
    )
    _assert_invalid_update(
        job,
        "declared page",
        results=[result, result],
        done=2,
        total=2,
        page={
            **job.page.model_dump(),
            "total": 2,
            "paging_v2": {**paging.model_dump(), "total": 2},
        },
    )


def test_report_state_has_one_resolved_snapshot_and_predictor_truth() -> None:
    executed = _capability(capability_id="lookup_ok")
    unavailable = _unavailable(capability_id="lookup_missing")
    failed = _failed(capability_id="lookup_failed")
    not_applicable = _unavailable(capability_id="lookup_na", applicability="not_applicable")
    ready = _report_section()
    assert _report_section(state="empty").state == "empty"
    assert (
        _report_section(
            state="partial",
            disclosures=[executed, unavailable],
        ).state
        == "partial"
    )
    assert _report_section(state="unavailable", disclosures=[unavailable])
    assert _report_section(state="failed", disclosures=[failed])
    assert _report_section(
        state="stale",
        stale_on_failure=True,
        warnings=["Refresh failed; displaying prior source-backed evidence."],
    )
    assert _report_section(
        state="not_applicable",
        match_level="not_applicable",
        disclosures=[not_applicable],
    )

    invalid_sections = (
        ("ready", [executed, unavailable], {}, "cannot hide"),
        ("empty", [], {}, "executed lookup evidence"),
        ("partial", [executed], {}, "partial sections"),
        ("unavailable", [], {}, "unavailable sections"),
        ("unavailable", [failed], {}, "non-failed unavailable evidence"),
        ("failed", [unavailable], {}, "failed sections"),
        ("stale", None, {"stale_on_failure": True, "warnings": []}, "stale sections"),
        ("not_applicable", [not_applicable], {}, "state and match level"),
    )
    for section_state, disclosures, updates, message in invalid_sections:
        with pytest.raises(ValidationError, match=message):
            _report_section(state=section_state, disclosures=disclosures, **updates)

    predictor = _report_predictor(
        applicability="not_applicable",
        state="not_applicable",
        disclosure=_unavailable(
            capability_id="spliceai",
            applicability="not_applicable",
        ),
    )
    state = _report_state(sections=[ready], predictors=[predictor])
    assert state.predictors[0].state == "not_applicable"

    all_sections = [
        _report_section(section_id=section_id) for section_id in get_args(ReportSectionIdV2)
    ]
    complete = _report_state(coverage="complete", sections=all_sections)
    assert len(complete.sections) == len(get_args(ReportSectionIdV2))
    with pytest.raises(ValidationError, match="every report section"):
        _report_state(coverage="complete", sections=[ready])
    with pytest.raises(ValidationError, match="cannot contain the complete"):
        _report_state(sections=all_sections)
    with pytest.raises(ValidationError, match="source-backed support"):
        _report_state(variant=_variant(support=False), sections=[ready])

    with pytest.raises(ValidationError, match="resolved variant"):
        _report_state(variant=_variant(resolved=False))
    with pytest.raises(ValidationError, match="exactly match"):
        _report_predictor(
            applicability="not_applicable",
            state="unavailable",
            disclosure=_unavailable(capability_id="spliceai", applicability="not_applicable"),
        )
    with pytest.raises(ValidationError, match="failed validation state"):
        _report_predictor(
            applicability="applicable",
            state="failed",
            disclosure=_unavailable(capability_id="revel"),
        )
    assert (
        _report_predictor(
            applicability="applicable",
            state="failed",
            disclosure=_failed(capability_id="revel"),
        ).state
        == "failed"
    )
    with pytest.raises(ValidationError, match="stale predictors"):
        _report_predictor(
            applicability="applicable",
            state="stale",
            disclosure=_capability(capability_id="revel"),
        )


def test_panel_v2_provenance_url_is_http_only_and_ready_state_is_executed() -> None:
    disclosure = _capability(
        capability_id="panel_catalog",
        algorithm_id="panel_builder",
        execution="mounted_artifact",
        source_status="source_backed",
        artifact_manifest_id="panel-manifest-1",
        artifact_sha256=SHA_A,
        source_record_ids=["gencc-release-1"],
    )
    snapshot = PanelSourceSnapshotV2(
        snapshot_id="panel-snapshot-1",
        source="clingen-gencc",
        version="2026.07",
        release="2026-07-01",
        retrieved_at=NOW,
        launch_posture="ready",
        licence_id="CC0-1.0",
        provenance_url="https://search.thegencc.org/download",
        artifact_manifest_id="panel-manifest-1",
        artifact_sha256=SHA_A,
        execution_disclosure=disclosure,
    )
    assert snapshot.provenance_url.scheme == "https"
    summary = PanelSummary(
        id="panel-1",
        name="Inherited retinal disease",
        slug="ird",
        source=snapshot.source,
        version=snapshot.version,
        provenance_url=snapshot.provenance_url,
        gene_count=42,
        source_snapshot_v2=snapshot,
    )
    assert summary.source == snapshot.source

    for update, message in (
        ({"source": "custom"}, "source and version"),
        ({"version": "wrong-version"}, "source and version"),
        ({"provenance_url": "https://example.test/wrong"}, "provenance_url"),
    ):
        _assert_invalid_update(summary, message, **update)

    local_without_artifact = _capability(
        capability_id="panel_catalog",
        algorithm_id="panel_builder",
        source_status="source_backed",
        source_record_ids=["gencc-release-1"],
    )
    _assert_invalid_update(
        snapshot,
        "immutable artifact identity",
        artifact_manifest_id=None,
        artifact_sha256=None,
        execution_disclosure=local_without_artifact,
    )
    _assert_invalid_update(
        snapshot,
        "source-backed material",
        execution_disclosure=_capability(
            capability_id="panel_catalog",
            algorithm_id="panel_builder",
            execution="mounted_artifact",
            source_status="not_required",
            artifact_manifest_id="panel-manifest-1",
            artifact_sha256=SHA_A,
        ),
    )
    _assert_invalid_update(snapshot, "must match its execution disclosure", artifact_sha256=SHA_B)

    with pytest.raises(ValidationError):
        PanelSourceSnapshotV2(**{**snapshot.model_dump(), "provenance_url": "javascript:alert(1)"})


def test_v2_durable_contracts_exclude_client_identity_and_raw_payload_fields() -> None:
    forbidden = {
        "owner_id",
        "user_id",
        "tenant_id",
        "raw_sequence",
        "vcf_rows",
        "genotypes",
        "document_text",
        "pdf_bytes",
        "trace_bytes",
        "notes",
    }
    for model in (
        CapabilityExecutionDisclosureV2,
        PaperDocumentBundleV2,
        PaperDocumentExtractionV2,
        BatchInputEnvelopeV2,
        BatchSourceSnapshotV2,
        ReportExecutionStateV2,
    ):
        assert forbidden.isdisjoint(model.model_fields), model.__name__


def test_unset_v2_fields_preserve_legacy_serialization_shapes() -> None:
    primer_request = PrimerRequest(gene="RPE65", cdna="c.260A>G")
    primer_response = PrimerResponse(mode="sanger", pairs=[])
    batch_page = BatchPage(limit=100, next_cursor=None, total=0)
    panel = PanelSummary(
        id="custom-1",
        name="Custom panel",
        slug="custom-1",
        source="custom",
        version="1",
        gene_count=0,
    )

    assert "design_context_v2" not in primer_request.model_dump()
    assert "execution_disclosure" not in primer_response.model_dump()
    assert "paging_v2" not in batch_page.model_dump()
    assert "source_snapshot_v2" not in panel.model_dump()
