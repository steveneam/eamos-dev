from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas.batch import BatchCreateRequest, ParsedVariant
from app.services.batch import BatchService
from app.services.panels import PanelService
from app.services.search_input_resolver import build_runtime_coordinate_resolver

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures"
COMPACT_INDEX_FIXTURE = FIXTURES_DIR / "coordinate_index" / "eamos_coordinate_index_tiny.jsonl"


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

    job_response = client.get(f"/api/v1/batch/{created['job_id']}?limit=1")
    assert job_response.status_code == 200
    job = job_response.json()
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
    job = client.get(f"/api/v1/batch/{created['job_id']}").json()

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

    job = auth_client.get(f"/api/v1/batch/{payload['job_id']}").json()
    assert job["n_after_filters"] == 1
    assert job["results"][0]["variant_key"] == "17-43092673-C-A"
    assert job["results"][0]["hgvs_c"] == "c.2858G>T"
    assert job["results"][0]["hgvs_p"] == "p.Cys953Phe"
    assert job["results"][0]["gnomad_af"] == 0.01
    assert "whitespace_delimited_vcf_row_recovered" in job["results"][0]["warnings"]


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


def _parsed_variant(query: str, *, pos: int = 10) -> ParsedVariant:
    return ParsedVariant(
        query=query,
        chrom="1",
        pos=pos,
        ref="A",
        alt="C",
        gene="BRCA1",
        variant="c.1A>C",
        filter="PASS",
    )
