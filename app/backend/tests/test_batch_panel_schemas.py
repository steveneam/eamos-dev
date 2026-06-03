from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import (
    BatchCreateRequest,
    BatchCreateResponse,
    BatchJob,
    BatchJobQuery,
    BatchPage,
    BatchResult,
    Panel,
    PanelGene,
    PanelListResponse,
    PanelResolveRequest,
    PanelSummary,
    ParsedVariant,
)


def test_batch_create_response_uses_pre_lookup_count_contract() -> None:
    fields = set(BatchCreateResponse.model_fields)

    assert {"job_id", "n_input", "n_to_lookup", "est_seconds"} <= fields
    assert "n_after_filters" not in fields


def test_batch_job_carries_nullable_final_count_and_page_envelope() -> None:
    job = BatchJob(
        job_id="batch_1",
        status="running",
        n_input=10,
        n_to_lookup=4,
        n_after_filters=None,
        est_seconds=36.0,
        done=1,
        total=4,
        results=[
            BatchResult(
                variant_key="1-216247118-C-A",
                gene="ush2a",
                hgvs_c="c.2276G>T",
                hgvs_p="p.Cys759Phe",
                clinvar_verdict="Likely pathogenic",
                gnomad_af=0.0018,
                predictor_ensemble={"consensus": "damaging"},
                acmg_classification="Likely pathogenic",
                report_href="/report?gene=USH2A&variant=c.2276G%3ET",
            )
        ],
        page=BatchPage(limit=100, next_cursor="cursor-2", total=1),
    )

    assert job.n_after_filters is None
    assert job.page.model_dump() == {"limit": 100, "next_cursor": "cursor-2", "total": 1}
    assert job.results[0].gene == "USH2A"


def test_batch_create_request_requires_inline_variants_or_upload_ref_not_both() -> None:
    variant = ParsedVariant(raw="USH2A c.2276G>T", query="USH2A c.2276G>T", gene="ush2a")

    inline = BatchCreateRequest(variants=[variant])
    assert inline.upload_ref is None
    assert inline.filters.pass_only is True
    assert inline.variants and inline.variants[0].gene == "USH2A"

    upload = BatchCreateRequest(upload_ref="  batch-upload-1  ")
    assert upload.upload_ref == "batch-upload-1"
    assert upload.variants is None

    with pytest.raises(ValidationError, match="exactly one"):
        BatchCreateRequest()

    with pytest.raises(ValidationError, match="exactly one"):
        BatchCreateRequest(variants=[variant], upload_ref="batch-upload-1")


def test_batch_query_and_page_bounds_are_explicit_for_frontend_mirror() -> None:
    query = BatchJobQuery(limit=50, cursor="  abc  ")
    assert query.model_dump() == {"limit": 50, "cursor": "abc"}

    with pytest.raises(ValidationError):
        BatchJobQuery(limit=0)

    with pytest.raises(ValidationError):
        BatchPage(limit=501, total=0)


def test_panel_resolve_request_accepts_exactly_one_resolution_source() -> None:
    by_symbols = PanelResolveRequest(symbols=[" rpe65 ", "USH2A", "rpe65", " "])
    assert by_symbols.symbols == ["RPE65", "USH2A"]
    assert by_symbols.min_validity == "strong"

    by_disease = PanelResolveRequest(disease_mondo=" MONDO:0019200 ", min_validity="definitive")
    assert by_disease.disease_mondo == "MONDO:0019200"

    by_upload = PanelResolveRequest(upload_ref=" panel-upload-1 ")
    assert by_upload.upload_ref == "panel-upload-1"

    with pytest.raises(ValidationError, match="exactly one"):
        PanelResolveRequest()

    with pytest.raises(ValidationError, match="exactly one"):
        PanelResolveRequest(disease_mondo="MONDO:0019200", symbols=["RPE65"])


def test_panel_summary_and_full_panel_contracts_are_backend_first() -> None:
    summary = PanelSummary(
        id="ird-core",
        name="Inherited retinal disease core",
        slug="ird-core",
        source="clingen-gencc",
        version="local-2026-06-04",
        gene_count=2,
    )
    panel = Panel(
        id=summary.id,
        name=summary.name,
        slug=summary.slug,
        source=summary.source,
        version=summary.version,
        provenance_url=summary.provenance_url,
        genes=[
            PanelGene(
                symbol=" rpe65 ",
                hgnc_id="HGNC:10294",
                confidence=None,
                moi="AR",
                disease="Leber congenital amaurosis",
                mondo_id="MONDO:0019200",
                validity="definitive",
                provenance=["clingen_gene_validity"],
            )
        ],
    )
    response = PanelListResponse(panels=[summary])

    assert summary.intervals_ref == "hg38"
    assert panel.intervals_ref == "hg38"
    assert panel.genes[0].symbol == "RPE65"
    assert response.panels[0].slug == "ird-core"

    with pytest.raises(ValidationError):
        PanelGene(symbol=" ")
