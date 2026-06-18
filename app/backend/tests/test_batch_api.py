from __future__ import annotations

from pathlib import Path
import time

import pytest

from app.schemas.batch import BatchCreateRequest, ParsedVariant
from app.schemas.lookup import LookupResponse
from app.schemas.run import (
    AcmgWorksheetLedger,
    ComputationalDeepDiveSection,
    ComputationalPredictorRow,
    EvidenceSourceSummary,
    PopulationFrequencyDetail,
    ReportPayload,
    VariantReportHeader,
    VariantReportProfile,
    VariantSummaryRow,
)
from app.services.compact_coordinate_index import CompactCoordinateIndex
from app.services.batch import BatchService
from app.services.panels import PanelService
from app.services.search_input_resolver import build_runtime_coordinate_resolver
from app.services.vcf_ingest import read_vcf_upload_file

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures"
COMPACT_INDEX_FIXTURE = FIXTURES_DIR / "coordinate_index" / "eamos_coordinate_index_tiny.jsonl"
PROJECT_100_VCF = FIXTURES_DIR / "hardening" / "project_100_mock_stack.vcf"


def test_batch_inline_job_dedupes_and_paginates_results(client) -> None:
    response = client.post(
        "/api/v1/batch",
        json={
            "variants": [
                {
                    "query": "1-10-A-C",
                    "chrom": "1",
                    "pos": 10,
                    "ref": "A",
                    "alt": "C",
                    "gene": "BRCA1",
                    "variant": "c.1A>C",
                    "filter": "PASS",
                },
                {
                    "query": "1-10-A-C",
                    "chrom": "1",
                    "pos": 10,
                    "ref": "A",
                    "alt": "C",
                    "gene": "BRCA1",
                    "variant": "c.1A>C",
                    "filter": "PASS",
                },
            ],
            "filters": {"panel_slug": "hereditary-cancer"},
        },
    )

    assert response.status_code == 200
    created = response.json()
    assert created["n_input"] == 2
    assert created["n_to_lookup"] == 1

    job = _wait_for_http_job(client, created["job_id"], limit=1)
    assert job["status"] == "completed"
    assert job["done"] == 1
    assert job["page"] == {"limit": 1, "next_cursor": None, "total": 1}
    assert job["results"][0]["variant_key"] == "1-10-A-C"
    assert job["results"][0]["gene"] == "BRCA1"
    assert "deduplicated_variants:1" in job["warnings"]


def test_batch_inline_job_uses_compact_coordinate_index_for_cdna_rows(
    client,
    tmp_path: Path,
) -> None:
    settings = client.app.state.settings.model_copy(
        update={"coordinate_resolver_compact_index_path": COMPACT_INDEX_FIXTURE}
    )
    client.app.state.batch_service = BatchService(
        upload_dir=tmp_path,
        panel_service=PanelService(),
        coordinate_resolver=build_runtime_coordinate_resolver(settings),
    )

    response = client.post(
        "/api/v1/batch",
        json={
            "variants": [
                {
                    "query": "RPE65:c.260A>G",
                    "gene": "RPE65",
                    "variant": "c.260A>G",
                    "filter": "PASS",
                }
            ],
            "filters": {"pass_only": True},
        },
    )

    assert response.status_code == 200
    created = response.json()
    job = _wait_for_http_job(client, created["job_id"])

    assert job["results"][0]["variant_key"] == "1-68444869-T-C"
    assert "compact_coordinate_index_batch_resolution" in job["results"][0]["warnings"]


def test_batch_upload_requires_authentication(client) -> None:
    upload = client.post(
        "/api/v1/batch/uploads",
        files={"file": ("sample.vcf", _valid_vcf(), "text/plain")},
    )

    assert upload.status_code == 401


def test_batch_upload_is_rate_limited(auth_client) -> None:
    auth_client.app.state.settings.rate_limit_batch_upload_max_requests = 1

    first = auth_client.post(
        "/api/v1/batch/uploads",
        files={"file": ("sample.vcf", _valid_vcf(), "text/plain")},
    )
    second = auth_client.post(
        "/api/v1/batch/uploads",
        files={"file": ("sample.vcf", _valid_vcf(), "text/plain")},
    )

    assert first.status_code == 200
    assert second.status_code == 429


def test_batch_upload_rejects_oversized_file(auth_client) -> None:
    auth_client.app.state.settings.max_upload_mb = 1
    oversized = b"##fileformat=VCFv4.2\n" + b"#" * (1024 * 1024)

    upload = auth_client.post(
        "/api/v1/batch/uploads",
        files={"file": ("oversized.vcf", oversized, "text/plain")},
    )

    assert upload.status_code == 413


def test_batch_upload_rejects_hg19_vcf_with_clear_422(auth_client) -> None:
    hg19_vcf = (
        "##fileformat=VCFv4.2\n"
        "##reference=GRCh37\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "1\t10\t.\tA\tC\t.\tPASS\tGENE=BRCA1\n"
    )

    upload = auth_client.post(
        "/api/v1/batch/uploads",
        files={"file": ("hg19.vcf", hg19_vcf, "text/plain")},
    )

    assert upload.status_code == 422
    assert "hg19/GRCh37" in upload.json()["detail"]


def test_batch_upload_vcf_cleans_rows_and_filters_before_lookup(auth_client) -> None:
    messy_vcf = (
        "##fileformat=VCFv4.2\n"
        "#CHROM POS ID REF ALT QUAL FILTER INFO FORMAT proband\n"
        "chr17  43092673 . c a . PASS GENE=BRCA1;HGVS_C=c.2858G>T;HGVS_P=p.Cys953Phe;AF=0.01 GT 0/1\n"
        "chr7 117509068 . c t . q10 GENE=CFTR;HGVS_C=c.199C>T;AF=0.01 GT 0/1\n"
        "chr17 43094577 . a c . PASS GENE=BRCA1;HGVS_C=c.954T>G;AF=0.2 GT 0/1\n"
    )
    upload = auth_client.post(
        "/api/v1/batch/uploads",
        files={"file": ("messy.vcf", messy_vcf, "text/plain")},
    )
    assert upload.status_code == 200
    upload_ref = upload.json()["upload_ref"]

    created = auth_client.post(
        "/api/v1/batch",
        json={
            "upload_ref": upload_ref,
            "filters": {
                "panel_slug": "hereditary-cancer",
                "pass_only": True,
                "max_af": 0.05,
            },
        },
    )

    assert created.status_code == 200
    payload = created.json()
    assert payload["n_input"] == 3
    assert payload["n_to_lookup"] == 1

    job = _wait_for_http_job(auth_client, payload["job_id"])
    assert job["n_after_filters"] == 1
    assert job["results"][0]["variant_key"] == "17-43092673-C-A"
    assert job["results"][0]["hgvs_c"] == "c.2858G>T"
    assert job["results"][0]["hgvs_p"] == "p.Cys953Phe"
    assert "whitespace_delimited_vcf_row_recovered" in job["results"][0]["warnings"]


def test_batch_service_runs_lookup_in_background_and_maps_summary(tmp_path: Path) -> None:
    lookup = _FakeLookupService(delay_seconds=0.05)
    service = BatchService(
        upload_dir=tmp_path,
        panel_service=PanelService(),
        lookup_service=lookup,
        max_lookup_workers=1,
    )

    created = service.create_job(
        BatchCreateRequest(
            variants=[
                _parsed_variant("RPE65:c.260A>G", gene="RPE65", variant="c.260A>G", pos=10),
                _parsed_variant("BRCA1:c.1A>C", gene="BRCA1", variant="c.1A>C", pos=11),
            ]
        )
    )

    queued = service.get_job(created.job_id, limit=100)
    assert queued is not None
    assert queued.status in {"queued", "running", "completed"}
    assert queued.total == 2

    job = _wait_for_service_job(service, created.job_id)
    assert job.status == "completed"
    assert job.done == 2
    assert job.results[0].clinvar_verdict == "Likely pathogenic"
    assert job.results[0].gnomad_af == 0.00012
    assert job.results[0].predictor_ensemble["AlphaMissense"]["interpretation"] == "damaging"
    assert job.results[0].acmg_classification == "Likely pathogenic"
    assert len(lookup.calls) == 2

    cached = service.create_job(
        BatchCreateRequest(
            variants=[_parsed_variant("RPE65:c.260A>G", gene="RPE65", variant="c.260A>G", pos=10)]
        )
    )
    _wait_for_service_job(service, cached.job_id)
    assert len(lookup.calls) == 2


def test_batch_lookup_cache_preserves_richer_variant_metadata(tmp_path: Path) -> None:
    lookup = _CoordinateOnlyLookupService()
    service = BatchService(
        upload_dir=tmp_path,
        panel_service=PanelService(),
        lookup_service=lookup,
        max_lookup_workers=1,
    )

    coordinate_only = service.create_job(
        BatchCreateRequest(
            variants=[
                ParsedVariant(
                    query="1-94014568-A-T",
                    chrom="1",
                    pos=94014568,
                    ref="A",
                    alt="T",
                    filter="PASS",
                )
            ]
        )
    )
    first_job = _wait_for_service_job(service, coordinate_only.job_id)
    assert first_job.results[0].gene is None
    assert first_job.results[0].hgvs_c is None
    assert len(lookup.calls) == 1

    with_vcf_metadata = service.create_job(
        BatchCreateRequest(
            variants=[
                ParsedVariant(
                    raw=(
                        "1\t94014568\t.\tA\tT\t.\tPASS\t"
                        "GENE=ABCA4;HGVS_C=c.5435T>A;HGVS_P=p.Leu1812Ter;AF=0.00042"
                    ),
                    query="1-94014568-A-T",
                    gene="ABCA4",
                    variant="c.5435T>A",
                    chrom="1",
                    pos=94014568,
                    ref="A",
                    alt="T",
                    filter="PASS",
                    info_af=0.00042,
                )
            ]
        )
    )
    second_job = _wait_for_service_job(service, with_vcf_metadata.job_id)

    assert len(lookup.calls) == 1
    assert second_job.results[0].gene == "ABCA4"
    assert second_job.results[0].hgvs_c == "c.5435T>A"
    assert second_job.results[0].hgvs_p == "p.Leu1812Ter"
    assert second_job.results[0].gnomad_af == 0.00042
    assert second_job.results[0].report_href == "/lookup?query=ABCA4%3Ac.5435T%3EA"


def test_batch_panel_filter_uses_interval_for_no_info_gene_vcf(tmp_path: Path) -> None:
    service = BatchService(
        upload_dir=tmp_path,
        panel_service=PanelService(),
        panel_interval_index=CompactCoordinateIndex(COMPACT_INDEX_FIXTURE),
    )

    created = service.create_job(
        BatchCreateRequest(
            variants=[
                ParsedVariant(
                    query="1-68444869-T-C",
                    chrom="1",
                    pos=68444869,
                    ref="T",
                    alt="C",
                    filter="PASS",
                ),
                ParsedVariant(
                    query="7-117509068-C-T",
                    chrom="7",
                    pos=117509068,
                    ref="C",
                    alt="T",
                    filter="PASS",
                ),
            ],
            filters={"panel_slug": "inherited-retinal-disease"},
        )
    )
    job = service.get_job(created.job_id, limit=100)

    assert job is not None
    assert job.status == "completed"
    assert job.n_to_lookup == 1
    assert job.results[0].variant_key == "1-68444869-T-C"
    assert "panel_filter_interval_match" in job.results[0].warnings


def test_batch_dedupes_by_resolved_identity_and_preserves_metadata(tmp_path: Path) -> None:
    settings = _settings_with_compact_index()
    lookup = _CoordinateOnlyLookupService()
    service = BatchService(
        upload_dir=tmp_path,
        panel_service=PanelService(),
        coordinate_resolver=build_runtime_coordinate_resolver(settings),
        lookup_service=lookup,
        max_lookup_workers=1,
    )

    created = service.create_job(
        BatchCreateRequest(
            variants=[
                ParsedVariant(
                    query="1-68444869-T-C",
                    chrom="1",
                    pos=68444869,
                    ref="T",
                    alt="C",
                    filter="PASS",
                ),
                ParsedVariant(
                    query="RPE65:c.260A>G",
                    gene="RPE65",
                    variant="c.260A>G",
                    filter="PASS",
                ),
            ]
        )
    )
    job = _wait_for_service_job(service, created.job_id)

    assert created.n_input == 2
    assert created.n_to_lookup == 1
    assert "deduplicated_variants:1" in job.warnings
    assert len(lookup.calls) == 1
    assert lookup.calls[0].gene == "RPE65"
    assert lookup.calls[0].cdna == "c.260A>G"
    assert job.results[0].variant_key == "1-68444869-T-C"
    assert job.results[0].gene == "RPE65"
    assert job.results[0].hgvs_c == "c.260A>G"


def test_batch_project_100_mock_vcf_uses_lookup_summary_not_info_passthrough(
    tmp_path: Path,
) -> None:
    parsed = read_vcf_upload_file(PROJECT_100_VCF)
    lookup = _FakeLookupService()
    service = BatchService(
        upload_dir=tmp_path,
        panel_service=PanelService(),
        lookup_service=lookup,
        max_lookup_workers=3,
    )

    created = service.create_job(
        BatchCreateRequest(
            variants=parsed.variants,
            filters={"panel_slug": "project-100-hardening"},
        )
    )
    job = _wait_for_service_job(service, created.job_id)

    assert job.status == "completed"
    assert job.n_input == 100
    assert job.done == 90
    assert job.total == 90
    assert len(lookup.calls) == 90
    assert {result.acmg_classification for result in job.results} == {"Likely pathogenic"}
    assert all(result.predictor_ensemble for result in job.results)


def test_batch_unknown_upload_ref_returns_404(client) -> None:
    response = client.post(
        "/api/v1/batch",
        json={"upload_ref": "batch-upload-missing"},
    )

    assert response.status_code == 404


def test_batch_service_bounds_upload_and_job_registries(tmp_path: Path) -> None:
    service = BatchService(
        upload_dir=tmp_path,
        panel_service=PanelService(),
        max_upload_entries=1,
        max_job_entries=1,
    )

    first_upload = service.store_upload(_valid_vcf().encode("utf-8"), filename="first.vcf")
    second_upload = service.store_upload(_valid_vcf().encode("utf-8"), filename="second.vcf")

    with pytest.raises(KeyError):
        service.create_job(BatchCreateRequest(upload_ref=first_upload))

    created_from_upload = service.create_job(BatchCreateRequest(upload_ref=second_upload))
    first_job = service.create_job(
        BatchCreateRequest(variants=[_parsed_variant("first-job", pos=11)])
    ).job_id
    second_job = service.create_job(
        BatchCreateRequest(variants=[_parsed_variant("second-job", pos=12)])
    ).job_id

    assert service.get_job(created_from_upload.job_id, limit=100) is None
    assert service.get_job(first_job, limit=100) is None
    assert service.get_job(second_job, limit=100) is not None


def test_batch_service_expires_stale_uploads_and_jobs(tmp_path: Path) -> None:
    now = 0.0

    def clock() -> float:
        return now

    service = BatchService(
        upload_dir=tmp_path,
        panel_service=PanelService(),
        entry_ttl_seconds=60,
        clock=clock,
    )
    upload_ref = service.store_upload(_valid_vcf().encode("utf-8"), filename="stale.vcf")
    created = service.create_job(BatchCreateRequest(variants=[_parsed_variant("stale-job")]))

    now = 61.0

    with pytest.raises(KeyError):
        service.create_job(BatchCreateRequest(upload_ref=upload_ref))
    assert service.get_job(created.job_id, limit=100) is None


def _valid_vcf() -> str:
    return (
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "1\t10\t.\tA\tC\t.\tPASS\tGENE=BRCA1\n"
    )


def _settings_with_compact_index():
    from app.core.config import Settings

    return Settings(
        jwt_secret="test-secret",
        coordinate_resolver_compact_index_path=COMPACT_INDEX_FIXTURE,
    )


def _parsed_variant(
    query: str,
    *,
    pos: int = 10,
    gene: str = "BRCA1",
    variant: str = "c.1A>C",
) -> ParsedVariant:
    return ParsedVariant(
        query=query,
        chrom="1",
        pos=pos,
        ref="A",
        alt="C",
        gene=gene,
        variant=variant,
        filter="PASS",
    )


def _wait_for_http_job(client, job_id: str, *, limit: int = 100) -> dict:
    deadline = time.monotonic() + 5
    last = None
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/batch/{job_id}?limit={limit}")
        assert response.status_code == 200
        last = response.json()
        if last["status"] in {"completed", "failed"}:
            return last
        time.sleep(0.02)
    raise AssertionError(f"batch job did not finish: {last}")


def _wait_for_service_job(service: BatchService, job_id: str):
    deadline = time.monotonic() + 5
    last = None
    while time.monotonic() < deadline:
        last = service.get_job(job_id, limit=500)
        if last is not None and last.status in {"completed", "failed"}:
            return last
        time.sleep(0.02)
    raise AssertionError(f"batch job did not finish: {last}")


class _FakeLookupService:
    def __init__(self, *, delay_seconds: float = 0.0) -> None:
        self.delay_seconds = delay_seconds
        self.calls = []

    def lookup(self, request, refresh: bool = False) -> LookupResponse:
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        self.calls.append(request)
        gene = request.gene or "BATCH"
        cdna = request.cdna or request.search_text or request.query or "c.1A>C"
        query = f"{gene}:{cdna}" if request.gene else str(cdna)
        variant_id = _variant_id_for_query(query)
        return LookupResponse(
            query=query,
            species="human",
            evidence=[
                EvidenceSourceSummary(
                    source="clinvar",
                    status="fixture",
                    summary={"classification": "Likely pathogenic"},
                ),
                EvidenceSourceSummary(
                    source="gnomad",
                    status="fixture",
                    summary={"allele_frequency": 0.00012},
                ),
            ],
            warnings=[],
            report_payload=ReportPayload(
                patient_id="batch-test",
                report_title=query,
                variant_summary_rows=[
                    VariantSummaryRow(
                        gene=gene,
                        transcript_hgvs=cdna,
                        protein_change="p.Arg1Gly",
                        genomic_hg38=variant_id,
                    )
                ],
                population_frequency_detail=PopulationFrequencyDetail(
                    dataset="gnomAD r4",
                    variant_id=variant_id,
                    allele_frequency=0.00012,
                ),
                report_profile=VariantReportProfile(
                    header=VariantReportHeader(
                        display_name=query,
                        gene=gene,
                        cdna=cdna,
                        protein_change="p.Arg1Gly",
                        genomic_hg38=variant_id,
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
            ),
        )


class _CoordinateOnlyLookupService:
    def __init__(self) -> None:
        self.calls = []

    def lookup(self, request, refresh: bool = False) -> LookupResponse:
        self.calls.append(request)
        return LookupResponse(
            query=str(request.search_text or request.query or request.cdna or "1-94014568-A-T"),
            species="human",
            evidence=[],
            warnings=[],
            report_payload=ReportPayload(
                patient_id="batch-cache-test",
                report_title="coordinate-only",
            ),
        )


def _variant_id_for_query(query: str) -> str:
    token = abs(hash(query)) % 100000
    return f"1-{token + 100}-A-C"
