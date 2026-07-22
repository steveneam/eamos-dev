from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace
import time

import pytest

from app.schemas.batch import BatchAlleleIdentityV2, BatchCreateRequest
from app.schemas.capabilities import CapabilityExecutionDisclosureV2
from app.schemas.report import ReportExecutionStateV2, ReportSectionExecutionV2
from app.schemas.run import (
    AcmgWorksheetLedger,
    ComputationalDeepDiveSection,
    ComputationalPredictorRow,
    PopulationFrequencyDetail,
    ReportPayload,
    VariantReportHeader,
    VariantReportProfile,
    VariantSummaryRow,
)
from app.schemas.workflow import CanonicalVariantRefV1
from app.services.batch import BatchService
from app.services.panels import PanelService


def test_v2_upload_is_single_use_and_fails_closed_without_normalization(
    tmp_path: Path,
) -> None:
    service = BatchService(upload_dir=tmp_path, panel_service=PanelService())
    upload_ref = service.store_upload_file(
        BytesIO(_one_row_vcf()),
        filename="secret-sample.vcf",
        owner_user_id="owner",
        owner_provider="eamos",
    )
    upload = service._uploads[upload_ref]
    staged_path = upload.staged_vcf.path
    receipt = service.upload_response(
        upload_ref,
        owner_user_id="owner",
        owner_provider="eamos",
    )

    created = service.create_job(
        BatchCreateRequest(upload_ref=upload_ref),
        owner_user_id="owner",
        owner_provider="eamos",
    )
    job = service.get_job(
        created.job_id,
        limit=100,
        owner_user_id="owner",
        owner_provider="eamos",
    )

    assert receipt.single_use is True
    assert receipt.expires_at is not None
    assert receipt.input_envelope_v2.raw_record_count == 1
    assert created.input_envelope_v2 == receipt.input_envelope_v2
    assert created.n_to_lookup == 0
    assert job is not None and job.status == "failed"
    assert job.results == []
    assert any("normalization_unavailable" in item for item in job.warnings)
    assert "SECRET_PATIENT_NAME" not in job.model_dump_json()
    assert not staged_path.exists()


def test_v2_completed_row_equals_direct_report_and_carries_every_field_state(
    tmp_path: Path,
) -> None:
    lookup = _V2LookupService()
    service = BatchService(
        upload_dir=tmp_path,
        panel_service=PanelService(),
        lookup_service=lookup,
        normalizer=_PassThroughNormalizer(),
        max_lookup_workers=1,
        cursor_secret=b"c" * 32,
    )
    upload_ref = service.store_upload_file(
        BytesIO(_one_row_vcf()),
        filename="wes.vcf",
        owner_user_id="owner",
        owner_provider="eamos",
    )
    created = service.create_job(
        BatchCreateRequest(upload_ref=upload_ref),
        owner_user_id="owner",
        owner_provider="eamos",
    )
    job = _wait_for_job(service, created.job_id)

    assert created.n_input == 1
    assert created.n_to_lookup == 1
    assert job.status == "completed"
    assert job.n_after_filters == 1
    assert len(lookup.calls) == 1
    row = job.results[0]
    assert row.variant_key == "1-10-A-C"
    assert row.gene == "RPE65"
    assert row.hgvs_c == "c.1A>C"
    assert row.hgvs_p == "p.Arg1Gly"
    assert row.clinvar_verdict == "Likely pathogenic"
    assert row.gnomad_af == 0.00012
    assert row.acmg_classification == "Likely pathogenic"
    assert set(item.field_name for item in row.field_executions_v2) == {
        "gene",
        "hgvs_c",
        "hgvs_p",
        "clinvar_verdict",
        "gnomad_af",
        "predictor_ensemble",
        "acmg_classification",
    }
    assert all(item.value_status == "executed" for item in row.field_executions_v2)
    assert row.source_snapshot_id == job.source_snapshot_v2.snapshot_id
    assert "direct_report_source_snapshot:report-snapshot-v2" in row.warnings
    assert row.sample_provenance_v2[0].sample_key.startswith("sample-")
    assert "SECRET_PATIENT_NAME" not in row.model_dump_json()


def test_annotation_cap_is_applied_after_normalized_duplicate_collapse(tmp_path: Path) -> None:
    service = BatchService(
        upload_dir=tmp_path,
        panel_service=PanelService(),
        lookup_service=_V2LookupService(),
        normalizer=_CollapsingNormalizer(),
        max_lookup_workers=1,
    )
    upload_ref = service.store_upload_file(
        BytesIO(_multirow_vcf(5)),
        filename="duplicates.vcf",
        owner_user_id="owner",
        owner_provider="eamos",
        post_filter_variant_cap=2,
    )
    created = service.create_job(
        BatchCreateRequest(upload_ref=upload_ref),
        owner_user_id="owner",
        owner_provider="eamos",
    )
    job = _wait_for_job(service, created.job_id)

    assert created.n_input == 5
    assert created.n_to_lookup == 2
    assert job.total == 2
    assert {item.variant_key for item in job.results} == {"1-4-A-C", "1-10-A-C"}
    assert "normalized_duplicates:2" in job.warnings
    assert "post_filter_annotation_cap_excluded:1" in job.warnings


@pytest.mark.parametrize(
    "batch_request",
    [
        BatchCreateRequest(
            upload_ref="placeholder",
            filter_plan_v2={
                "interval_scope": "capture_bed",
                "interval_snapshot_id": "capture-not-mounted",
            },
        ),
        BatchCreateRequest(
            upload_ref="placeholder",
            filters={"panel_slug": "inherited-retinal-disease"},
            filter_plan_v2={
                "interval_scope": "whole_gene",
                "interval_snapshot_id": "mane-not-mounted",
                "panel_snapshot_id": "panel-custom-not-ready",
            },
        ),
    ],
)
def test_unmounted_capture_and_panel_interval_authorities_fail_closed(
    tmp_path: Path,
    batch_request: BatchCreateRequest,
) -> None:
    service = BatchService(
        upload_dir=tmp_path,
        panel_service=PanelService(),
        lookup_service=_V2LookupService(),
        normalizer=_PassThroughNormalizer(),
    )
    upload_ref = service.store_upload_file(
        BytesIO(_one_row_vcf()),
        filename="scope.vcf",
        owner_user_id="owner",
        owner_provider="eamos",
    )
    created = service.create_job(
        batch_request.model_copy(update={"upload_ref": upload_ref}),
        owner_user_id="owner",
        owner_provider="eamos",
    )
    job = service.get_job(
        created.job_id,
        limit=100,
        owner_user_id="owner",
        owner_provider="eamos",
    )

    assert created.n_to_lookup == 0
    assert job is not None and job.status == "failed"
    assert job.results == []
    assert any("filter_unavailable" in warning for warning in job.warnings)
    assert job.filter_dispositions_v2[0].outcome == "deferred"
    assert job.filter_dispositions_v2[0].reason == "source_unavailable"


def test_terminal_v2_exports_are_streamed_digested_and_snapshot_bound(
    auth_client,
    tmp_path: Path,
) -> None:
    service = BatchService(
        upload_dir=tmp_path / "batch-runtime",
        panel_service=PanelService(),
        lookup_service=_V2LookupService(),
        normalizer=_PassThroughNormalizer(),
        workflow_service=auth_client.app.state.product_workflow_service,
        cursor_secret=b"export-cursor-secret" * 2,
    )
    auth_client.app.state.batch_service = service
    upload = auth_client.post(
        "/api/v1/batch/uploads",
        files={"file": ("wes.vcf", _one_row_vcf(), "text/vcf")},
    )
    assert upload.status_code == 200
    created = auth_client.post(
        "/api/v1/batch",
        json={"upload_ref": upload.json()["upload_ref"]},
    )
    assert created.status_code == 200
    job = _wait_for_http_job(auth_client, created.json()["job_id"])
    snapshot_id = job["source_snapshot_v2"]["snapshot_id"]

    responses = {
        export_format: auth_client.get(
            f"/api/v1/batch/{job['job_id']}/export",
            params={"format": export_format},
        )
        for export_format in ("tsv", "csv", "jsonl", "vcf")
    }
    for response in responses.values():
        assert response.status_code == 200
        assert response.headers["X-Source-Snapshot-ID"] == snapshot_id
        assert response.headers["X-Row-Count"] == "1"
        assert response.headers["X-Content-SHA256"] == sha256(response.content).hexdigest()
        assert response.headers["Cache-Control"] == "private, no-store"
        assert "SECRET_PATIENT_NAME" not in response.text

    assert responses["tsv"].text.startswith("variant_key\tstate\tgene")
    assert responses["csv"].text.startswith("variant_key,state,gene")
    jsonl = json.loads(responses["jsonl"].text)
    assert jsonl["variant_key"] == "1-10-A-C"
    assert jsonl["source_snapshot_id"] == snapshot_id
    assert jsonl["sample_provenance_v2"][0]["sample_key"].startswith("sample-")
    assert "\tGT" not in responses["vcf"].text
    assert "SOURCE_SNAPSHOT=" in responses["vcf"].text

    manifest = auth_client.get(
        f"/api/v1/batch/{job['job_id']}/export",
        params={"format": "manifest"},
    )
    assert manifest.status_code == 200
    body = manifest.json()
    assert body["schema_version"] == "batch_export_manifest.v2"
    assert body["raw_input_included"] is False
    assert body["source_snapshot_v2"]["snapshot_id"] == snapshot_id
    receipts = {item["format"]: item for item in body["exports"]}
    assert set(receipts) == {"tsv", "csv", "jsonl", "vcf"}
    for export_format, response in responses.items():
        assert receipts[export_format]["state"] == "ready"
        assert receipts[export_format]["row_count"] == 1
        assert receipts[export_format]["sha256"] == response.headers["X-Content-SHA256"]


def test_expired_worker_lease_recovers_v2_job_without_raw_upload(
    auth_client,
    monkeypatch,
    tmp_path: Path,
) -> None:
    token = auth_client.headers["Authorization"].removeprefix("Bearer ")
    owner_user_id = auth_client.app.state.auth_service.get_current_user(token).user_id
    workflow = auth_client.app.state.product_workflow_service
    runtime_dir = tmp_path / "restart-runtime"
    first_lookup = _V2LookupService()
    first = BatchService(
        upload_dir=runtime_dir,
        panel_service=PanelService(),
        lookup_service=first_lookup,
        normalizer=_PassThroughNormalizer(),
        workflow_service=workflow,
        lease_seconds=1,
    )
    monkeypatch.setattr(first, "_start_background_job", lambda *_args, **_kwargs: None)
    upload_ref = first.store_upload_file(
        BytesIO(_one_row_vcf()),
        filename="restart.vcf",
        owner_user_id=owner_user_id,
        owner_provider="eamos",
    )
    created = first.create_job(
        BatchCreateRequest(upload_ref=upload_ref),
        owner_user_id=owner_user_id,
        owner_provider="eamos",
    )
    lease = first._lease_store
    assert lease is not None
    assert lease.reserve(created.job_id) is True
    first_claim = lease.claim(created.job_id)
    assert first_claim is not None and first_claim.attempt == 1
    assert not list((runtime_dir / "batch" / "uploads").glob("*.upload"))

    time.sleep(1.05)
    recovered_lookup = _V2LookupService()
    recovered = BatchService(
        upload_dir=runtime_dir,
        panel_service=PanelService(),
        lookup_service=recovered_lookup,
        normalizer=_PassThroughNormalizer(),
        workflow_service=workflow,
        lease_seconds=1,
    )
    job = _wait_for_job(recovered, created.job_id, owner_user_id=owner_user_id)

    assert job.status == "completed"
    assert job.results[0].variant_key == "1-10-A-C"
    assert "batch_job_recovered_after_restart" in job.warnings
    assert len(first_lookup.calls) == 0
    assert len(recovered_lookup.calls) == 1
    final_lease = recovered._lease_store.get(created.job_id)
    assert final_lease is not None
    assert final_lease.state == "completed"
    assert final_lease.attempt == 2


class _PassThroughNormalizer:
    reference_release = "GRCh38.p14-test"

    def disclosure(self) -> CapabilityExecutionDisclosureV2:
        return _executed_disclosure("batch.variant_normalization")

    def normalize(self, allele, *, source_record_index: int) -> BatchAlleleIdentityV2:
        return BatchAlleleIdentityV2(
            original=allele,
            normalized=allele,
            status="normalized",
            source_record_index=source_record_index,
            normalization_algorithm_id="test_refchecked_normalizer",
            normalization_algorithm_version="1",
            reference_manifest_id="grch38-test-manifest",
            reference_sha256="a" * 64,
            warnings=[],
        )


class _CollapsingNormalizer(_PassThroughNormalizer):
    def normalize(self, allele, *, source_record_index: int) -> BatchAlleleIdentityV2:
        normalized = allele.model_copy(update={"position": 10}) if allele.position <= 3 else allele
        return BatchAlleleIdentityV2(
            original=allele,
            normalized=normalized,
            status="normalized",
            source_record_index=source_record_index,
            normalization_algorithm_id="test_collapsing_normalizer",
            normalization_algorithm_version="1",
            reference_manifest_id="grch38-test-manifest",
            reference_sha256="a" * 64,
            warnings=[],
        )


class _V2LookupService:
    def __init__(self) -> None:
        self.calls = []

    def lookup(self, request, refresh: bool = False):
        self.calls.append(request)
        payload = ReportPayload(
            patient_id="batch-v2-test",
            report_title="RPE65:c.1A>C",
            variant_summary_rows=[
                VariantSummaryRow(
                    gene="RPE65",
                    transcript_hgvs="c.1A>C",
                    protein_change="p.Arg1Gly",
                    genomic_hg38="1-10-A-C",
                )
            ],
            population_frequency_detail=PopulationFrequencyDetail(
                dataset="gnomAD r4",
                variant_id="1-10-A-C",
                allele_frequency=0.00012,
            ),
            report_profile=VariantReportProfile(
                header=VariantReportHeader(
                    display_name="RPE65:c.1A>C",
                    gene="RPE65",
                    cdna="c.1A>C",
                    protein_change="p.Arg1Gly",
                    genomic_hg38="1-10-A-C",
                    classification="Likely pathogenic",
                    classification_source="ClinVar",
                ),
                computational_deep_dive=ComputationalDeepDiveSection(
                    predictors=[
                        ComputationalPredictorRow(
                            name="AlphaMissense",
                            score=0.91,
                            threshold=0.56,
                            interpretation="damaging",
                            source="AlphaMissense",
                        )
                    ]
                ),
                acmg_worksheet=AcmgWorksheetLedger(
                    classification="Likely pathogenic",
                    classification_source="Eamos",
                ),
            ),
        )
        return SimpleNamespace(
            report_payload=payload,
            evidence=[],
            warnings=[],
            execution_state_v2=_report_execution_state(),
        )


def _report_execution_state() -> ReportExecutionStateV2:
    snapshot_id = "report-snapshot-v2"
    return ReportExecutionStateV2(
        coverage="partial",
        canonical_variant=CanonicalVariantRefV1(
            schema_version="canonical_variant_ref.v1",
            gene="RPE65",
            cdna="c.1A>C",
            transcript="NM_000329.3",
            protein_hgvs="p.Arg1Gly",
            genomic_hg38="1-10-A-C",
            variant_key="1-10-A-C",
            species="human",
            genome_build="GRCh38",
            resolution_status="resolved",
            source_support=["test-coordinate-source"],
            warnings=[],
        ),
        source_snapshot_id=snapshot_id,
        sections=[
            ReportSectionExecutionV2(
                section_id=section_id,
                state="ready",
                match_level="exact_allele",
                source_snapshot_id=snapshot_id,
                execution_disclosures=[_executed_disclosure(f"report.{section_id}")],
            )
            for section_id in (
                "header",
                "interpretation_summary",
                "population_frequency",
                "computational_deep_dive",
                "acmg_worksheet",
            )
        ],
        predictors=[],
    )


def _executed_disclosure(capability_id: str) -> CapabilityExecutionDisclosureV2:
    return CapabilityExecutionDisclosureV2(
        capability_id=capability_id,
        claim=f"Executed {capability_id}",
        execution="mounted_artifact",
        algorithm_id=capability_id,
        algorithm_version="1",
        input_scope="normalized_grch38_allele",
        source_status="source_backed",
        source_record_ids=[f"{capability_id}.record"],
        source_release="test-release",
        artifact_manifest_id=f"{capability_id}.manifest",
        artifact_sha256="a" * 64,
        applicability="applicable",
        validation_status="validated",
        validation_matrix_id="batch-direct-lookup-v2",
        retention="none",
        consent_required=False,
        warnings=[],
        requirements=[],
    )


def _one_row_vcf() -> bytes:
    return (
        "##fileformat=VCFv4.2\n"
        "##reference=GRCh38.p14\n"
        "##contig=<ID=1,length=248956422,assembly=GRCh38>\n"
        '##INFO=<ID=GENE,Number=1,Type=String,Description="Provenance only">\n'
        '##INFO=<ID=HGVS_C,Number=1,Type=String,Description="Provenance only">\n'
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n'
        '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read depth">\n'
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSECRET_PATIENT_NAME\n"
        "1\t10\t.\tA\tC\t60\tPASS\tGENE=RPE65;HGVS_C=c.1A%3EC\tGT:DP\t0/1:31\n"
    ).encode("utf-8")


def _multirow_vcf(row_count: int) -> bytes:
    header = (
        "##fileformat=VCFv4.2\n"
        "##reference=GRCh38.p14\n"
        "##contig=<ID=1,length=248956422,assembly=GRCh38>\n"
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n'
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tPROBAND\n"
    )
    rows = "".join(
        f"1\t{position}\t.\tA\tC\t60\tPASS\t.\tGT\t0/1\n" for position in range(1, row_count + 1)
    )
    return (header + rows).encode("utf-8")


def _wait_for_job(
    service: BatchService,
    job_id: str,
    *,
    owner_user_id: str = "owner",
):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        job = service.get_job(
            job_id,
            limit=100,
            owner_user_id=owner_user_id,
            owner_provider="eamos",
        )
        if job is not None and job.status in {"completed", "failed"}:
            return job
        time.sleep(0.01)
    raise AssertionError("batch V2 job did not finish")


def _wait_for_http_job(client, job_id: str) -> dict:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/batch/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] in {"completed", "failed", "cancelled"}:
            return job
        time.sleep(0.01)
    raise AssertionError("Batch export fixture did not reach a terminal state.")
