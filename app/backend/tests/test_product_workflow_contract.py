from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.workflow import (
    CanonicalVariantRefV1,
    CuratedVariantPageV1,
    ProcessingDisclosureV1,
    RelatedVariantGroupV1,
    RelatedVariantItemV1,
    SelectionRangeV1,
    WorkflowArtifactV1,
    WorkflowContextV1,
    WorkflowRunV1,
    build_compare_href_v1,
    build_paper_href_v1,
    build_report_href_v1,
    build_workbench_href_v1,
)
from app.schemas.workbench import SourceDisclosure

NOW = datetime(2026, 7, 19, 10, 0, tzinfo=UTC)
SHA_A = "a" * 64
SHA_B = "b" * 64


def _variant(**overrides) -> CanonicalVariantRefV1:
    payload = {
        "schema_version": "canonical_variant_ref.v1",
        "gene": "rpe65",
        "cdna": "c.260A>G",
        "transcript": "NM_000329.3",
        "protein_hgvs": "p.Asp87Gly",
        "genomic_hg38": "NC_000001.11:g.68444869T>C",
        "variant_key": "1-68444869-T-C",
        "species": "human",
        "genome_build": "GRCh38",
        "resolution_status": "resolved",
        "source_support": ["variantvalidator", "clinvar"],
        "warnings": [],
    }
    payload.update(overrides)
    return CanonicalVariantRefV1.model_validate(payload)


def _selection(**overrides) -> SelectionRangeV1:
    payload = {
        "schema_version": "selection_range.v1",
        "variant_key": "1-68444869-T-C",
        "transcript": "NM_000329.3",
        "genome_build": "GRCh38",
        "chrom": "chr1",
        "genomic_start": 68_444_849,
        "genomic_end": 68_444_889,
        "strand": "+",
        "orientation": "transcript",
        "sequence_basis": "variant",
        "edit_revision": 0,
        "sequence_sha256": SHA_A.upper(),
        "cdna_start": 240,
        "cdna_end": 280,
        "cds_start": 240,
        "cds_end": 280,
        "protein_start": 80,
        "protein_end": 94,
        "overlaps": ["cds", "exon"],
    }
    payload.update(overrides)
    return SelectionRangeV1.model_validate(payload)


def _source_disclosure() -> SourceDisclosure:
    return SourceDisclosure(
        source_status="source_backed",
        provider_id="ncbi_clinvar",
        provider_label="NCBI ClinVar",
        source_version="2026-07-12",
        cache_status="fresh",
        warnings=[],
        requirements=[],
    )


def _processing(**overrides) -> ProcessingDisclosureV1:
    payload = {
        "execution": "eamos_backend",
        "provider_id": "eamos_local",
        "provider_label": "Eamos backend",
        "input_classes": ["variant_id", "vcf"],
        "raw_input_persisted": False,
        "retention": "request_lifetime",
        "expires_at": None,
        "user_deletable": False,
        "consent_required": False,
        "warnings": [],
    }
    payload.update(overrides)
    return ProcessingDisclosureV1.model_validate(payload)


def _artifact(**overrides) -> WorkflowArtifactV1:
    payload = {
        "artifact_id": "artifact_batch_tsv_01",
        "kind": "batch_tsv",
        "filename": "rpe65_batch.tsv",
        "media_type": "text/tab-separated-values",
        "generated_at": NOW,
        "source_run_id": "batch_run_01",
        "context_digest": "ctxdigest-rpe65-01",
        "sha256": SHA_B,
        "download_state": "ready",
    }
    payload.update(overrides)
    return WorkflowArtifactV1.model_validate(payload)


def test_batch_paper_selection_and_artifact_examples_round_trip_as_json() -> None:
    variant = _variant()
    selection = _selection()
    batch_context = WorkflowContextV1(
        schema_version="workflow_context.v1",
        context_id="ctx_batch_01",
        variant=variant,
        origin_surface="batch",
        return_to="/compare?run_id=batch_run_01&view=cohort",
        batch_run_id="batch_run_01",
        paper_run_id=None,
        workspace_id=None,
        active_tool=None,
        selection=None,
        created_at=NOW,
        expires_at=NOW + timedelta(hours=1),
    )
    paper_context = WorkflowContextV1(
        schema_version="workflow_context.v1",
        context_id="ctx_paper_01",
        variant=variant,
        origin_surface="paper",
        return_to="/paper?run_id=paper_run_01",
        batch_run_id=None,
        paper_run_id="paper_run_01",
        workspace_id=None,
        active_tool=None,
        selection=None,
        created_at=NOW,
        expires_at=None,
    )
    workbench_context = WorkflowContextV1(
        schema_version="workflow_context.v1",
        context_id="ctx_workbench_01",
        variant=variant,
        origin_surface="workbench",
        return_to="/report?gene=RPE65&cdna=c.260A%3EG&from=workbench",
        batch_run_id=None,
        paper_run_id=None,
        workspace_id="workspace_01",
        active_tool="primer",
        selection=selection,
        created_at=NOW,
        expires_at=None,
    )
    artifact = _artifact()
    run = WorkflowRunV1(
        schema_version="workflow_run.v1",
        run_id="batch_run_01",
        kind="batch",
        status="completed",
        owner_scope="account",
        context=batch_context,
        done=1,
        total=1,
        created_at=NOW,
        updated_at=NOW + timedelta(minutes=1),
        expires_at=NOW + timedelta(days=7),
        warnings=[],
        source_disclosures=[_source_disclosure()],
        processing_disclosure=_processing(),
        artifacts=[artifact],
    )

    assert variant.gene == "RPE65"
    assert selection.sequence_sha256 == SHA_A
    assert paper_context.model_dump(mode="json")["paper_run_id"] == "paper_run_01"
    assert workbench_context.model_dump(mode="json")["selection"]["overlaps"] == [
        "cds",
        "exon",
    ]

    encoded = run.model_dump(mode="json")
    assert encoded["schema_version"] == "workflow_run.v1"
    assert encoded["context"]["variant"]["transcript"] == "NM_000329.3"
    assert encoded["context"]["selection"] is None
    assert encoded["processing_disclosure"]["expires_at"] is None
    assert encoded["artifacts"][0]["filename"] == "rpe65_batch.tsv"
    assert encoded["created_at"].endswith("Z")
    assert WorkflowRunV1.model_validate_json(run.model_dump_json()) == run


def test_context_rejects_unsafe_return_paths_and_sensitive_query_fields() -> None:
    base = {
        "schema_version": "workflow_context.v1",
        "context_id": None,
        "variant": _variant(),
        "origin_surface": "report",
        "batch_run_id": None,
        "paper_run_id": None,
        "workspace_id": None,
        "active_tool": None,
        "selection": None,
        "created_at": NOW,
        "expires_at": None,
    }

    for unsafe in (
        "https://evil.example/report?gene=RPE65",
        "//evil.example/report?gene=RPE65",
        "/report?paper_text=private",
        "/workbench?notes=private",
        "/lookup?query=RPE65",
        "/report?gene=RPE65#fragment",
        "/report?gene=RPE65%0Ainjected&cdna=c.260A%3EG",
    ):
        with pytest.raises(ValidationError, match="return_to"):
            WorkflowContextV1(return_to=unsafe, **base)


def test_context_binds_selection_and_design_tools_to_a_resolved_variant() -> None:
    base = {
        "schema_version": "workflow_context.v1",
        "context_id": None,
        "origin_surface": "workbench",
        "return_to": None,
        "batch_run_id": None,
        "paper_run_id": None,
        "workspace_id": None,
        "created_at": NOW,
        "expires_at": None,
    }

    with pytest.raises(ValidationError, match="variant_key"):
        WorkflowContextV1(
            variant=_variant(variant_key="different-key"),
            active_tool="viewer",
            selection=_selection(),
            **base,
        )

    with pytest.raises(ValidationError, match="resolved"):
        WorkflowContextV1(
            variant=_variant(resolution_status="ambiguous"),
            active_tool="primer",
            selection=None,
            **base,
        )


def test_selection_rejects_ambiguous_or_internally_inconsistent_intervals() -> None:
    with pytest.raises(ValidationError, match="genomic_start"):
        _selection(genomic_start=20, genomic_end=10)

    with pytest.raises(ValidationError, match="cdna_start"):
        _selection(cdna_start=240, cdna_end=None)

    with pytest.raises(ValidationError, match="edit_revision"):
        _selection(sequence_basis="edited", edit_revision=0)

    with pytest.raises(ValidationError, match="sequence_sha256"):
        _selection(sequence_sha256="not-a-sha256")

    with pytest.raises(ValidationError, match="overlaps"):
        _selection(overlaps=["exon", "exon"])


def test_disclosure_requires_external_consent_and_ttl_expiry() -> None:
    with pytest.raises(ValidationError, match="consent_required"):
        _processing(
            execution="external_provider",
            provider_id="external_gateway",
            provider_label="External gateway",
            input_classes=["paper_text"],
            consent_required=False,
        )

    with pytest.raises(ValidationError, match="expires_at"):
        _processing(retention="ttl", expires_at=None)


def test_artifact_and_run_integrity_rejects_path_and_cross_run_confusion() -> None:
    for unsafe_name in ("../private.tsv", "nested/private.tsv", "private\\file.tsv"):
        with pytest.raises(ValidationError, match="filename"):
            _artifact(filename=unsafe_name)

    with pytest.raises(ValidationError, match="sha256"):
        _artifact(sha256="short")

    context = WorkflowContextV1(
        schema_version="workflow_context.v1",
        context_id=None,
        variant=_variant(),
        origin_surface="batch",
        return_to=None,
        batch_run_id="batch_run_01",
        paper_run_id=None,
        workspace_id=None,
        active_tool=None,
        selection=None,
        created_at=NOW,
        expires_at=None,
    )
    base = {
        "schema_version": "workflow_run.v1",
        "run_id": "batch_run_01",
        "kind": "batch",
        "status": "running",
        "owner_scope": "account",
        "context": context,
        "done": 1,
        "total": 2,
        "created_at": NOW,
        "updated_at": NOW,
        "expires_at": None,
        "warnings": [],
        "source_disclosures": [],
        "processing_disclosure": None,
        "artifacts": [],
    }

    with pytest.raises(ValidationError, match="done"):
        WorkflowRunV1(**{**base, "done": 3})

    with pytest.raises(ValidationError, match="completed"):
        WorkflowRunV1(**{**base, "status": "completed"})

    with pytest.raises(ValidationError, match="source_run_id"):
        WorkflowRunV1(
            **{
                **base,
                "artifacts": [_artifact(source_run_id="different_run")],
            }
        )

    duplicate = _artifact()
    with pytest.raises(ValidationError, match="artifact_id"):
        WorkflowRunV1(**{**base, "artifacts": [duplicate, duplicate]})


def test_related_and_curated_pages_are_backend_typed_and_deduplicated() -> None:
    variant = _variant()
    related = RelatedVariantItemV1(
        variant=variant,
        relationship="same_gene",
        distance_bp=42,
        classification="vus",
        evidence_axis_summary=None,
        source_disclosure=_source_disclosure(),
        report_href=build_report_href_v1(variant, from_surface="report"),
    )
    group = RelatedVariantGroupV1(items=[related], warnings=[])
    page = CuratedVariantPageV1(
        gene="rpe65",
        classification_filter="vus",
        consequence_filter="missense",
        items=[variant],
        next_cursor=None,
        total=1,
        source_disclosure=_source_disclosure(),
        warnings=[],
    )

    assert group.items[0].report_href.startswith("/report?")
    assert page.gene == "RPE65"

    with pytest.raises(ValidationError, match="deduplicated"):
        RelatedVariantGroupV1(items=[related, related], warnings=[])

    with pytest.raises(ValidationError, match="canonical gene"):
        RelatedVariantItemV1(
            **{
                **related.model_dump(),
                "report_href": "/report?gene=ABCA4&cdna=c.260A%3EG&transcript=NM_000329.3",
            }
        )

    with pytest.raises(ValidationError, match="deduplicated"):
        CuratedVariantPageV1(
            gene="RPE65",
            classification_filter=None,
            consequence_filter=None,
            items=[variant, variant],
            next_cursor=None,
            total=2,
            source_disclosure=_source_disclosure(),
            warnings=[],
        )

    with pytest.raises(ValidationError, match="page gene"):
        CuratedVariantPageV1(
            gene="ABCA4",
            classification_filter=None,
            consequence_filter=None,
            items=[variant],
            next_cursor=None,
            total=1,
            source_disclosure=_source_disclosure(),
            warnings=[],
        )


def test_canonical_url_builders_emit_only_the_frozen_public_grammar() -> None:
    variant = _variant()

    assert build_report_href_v1(variant, from_surface="paper") == (
        "/report?gene=RPE65&cdna=c.260A%3EG&transcript=NM_000329.3&from=paper"
    )
    assert build_workbench_href_v1(
        variant,
        tool="primer",
        view="locus",
        context_id="ctx_01",
    ) == (
        "/workbench?gene=RPE65&cdna=c.260A%3EG&transcript=NM_000329.3"
        "&tool=primer&view=locus&context_id=ctx_01"
    )
    assert build_compare_href_v1(run_id="batch_run_01", view="compare") == (
        "/compare?run_id=batch_run_01&view=compare"
    )
    assert build_paper_href_v1(context_id="ctx_01") == "/paper?context_id=ctx_01"

    with pytest.raises(ValueError, match="resolved"):
        build_workbench_href_v1(_variant(resolution_status="unresolved"), tool="crispr")

    with pytest.raises(ValueError, match="run_id or context_id"):
        build_compare_href_v1()


def test_contract_models_reject_unknown_fields_and_naive_timestamps() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        CanonicalVariantRefV1.model_validate(
            {**_variant().model_dump(), "client_supplied_owner_id": "attacker"}
        )

    with pytest.raises(ValidationError, match="extra_forbidden"):
        SourceDisclosure(
            source_status="source_backed",
            provider_id="clinvar",
            provider_label="ClinVar",
            warnings=[],
            requirements=[],
            client_supplied_owner_id="attacker",
        )

    with pytest.raises(ValidationError, match="timezone"):
        WorkflowArtifactV1(
            **{
                **_artifact().model_dump(),
                "generated_at": datetime(2026, 7, 19, 10, 0),
            }
        )
