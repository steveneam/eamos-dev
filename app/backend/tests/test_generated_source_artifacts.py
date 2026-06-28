from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import httpx

from app.cli import eamos_generated_artifact_sync, eamos_generated_artifact_upload
from app.core.config import Settings
from app.services.ai_gateway.retrieval import LiteratureEmbeddingStore, LiteratureSourceRecord
from app.services.clingen_local import materialize_clingen_local_store
from app.services.clinvar_local import (
    DEFAULT_CLINVAR_VCF_FIXTURE_PATH,
    inspect_clinvar_gene_distribution_index,
    materialize_clinvar_gene_distribution_index,
)
from app.services.generated_source_artifacts import (
    GENERATED_SOURCE_ARTIFACT_IDS,
    build_generated_source_artifact_upload_items,
    execute_generated_source_artifact_uploads,
    materialize_generated_source_artifact,
)
from app.services.pubmed_local import inspect_pubmed_local_store, materialize_pubmed_local_store
from app.services.source_storage_uploads import SourceStorageUploadMode, SourceStorageUploadStatus

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures" / "tools"
PUBMED_XML = FIXTURES_DIR / "pubmed_local_sample.xml"


def test_generated_artifact_upload_plan_includes_tier1_sqlites_without_paths(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    _materialize_all_tier1(settings, tmp_path)

    items = build_generated_source_artifact_upload_items(
        settings,
        artifact_ids=GENERATED_SOURCE_ARTIFACT_IDS,
        bucket_id="eamos-source-assets",
        manifest_staging_root=tmp_path / "upload-manifests",
    )

    by_artifact = {item.artifact_id: item for item in items}
    assert set(by_artifact) == set(GENERATED_SOURCE_ARTIFACT_IDS)
    assert {item.status for item in items} == {SourceStorageUploadStatus.PLANNED}
    assert by_artifact["clingen_local"].source_id == "eamos_clingen_local"
    assert by_artifact["pubmed_local"].source_id == "eamos_pubmed_local"
    assert by_artifact["literature_embeddings"].source_id == "eamos_literature_embeddings"
    assert (
        by_artifact["clinvar_gene_distribution_index"].source_id
        == "eamos_clinvar_gene_distribution_index"
    )
    assert all(item.object_path.startswith("generated/") for item in items)
    assert all("/sha256-" in item.object_path for item in items)
    assert all(item.content_type == "application/octet-stream" for item in items)
    assert all(item.byte_size and item.byte_size > 0 for item in items)
    assert all(item.sha256 and len(item.sha256) == 64 for item in items)
    assert all(
        item.source_object_uri.startswith("supabase://eamos-source-assets/") for item in items
    )

    result = execute_generated_source_artifact_uploads(items, upload=False)
    encoded = json.dumps(result.to_sanitized_dict()).lower()
    assert str(tmp_path).lower() not in encoded
    assert "service_role" not in encoded
    assert result.planned_count == 4


def test_generated_artifact_upload_posts_asset_and_manifest(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _materialize_clingen(settings, tmp_path)
    [item] = build_generated_source_artifact_upload_items(
        settings,
        artifact_ids=("clingen_local",),
        bucket_id="eamos-source-assets",
        manifest_staging_root=tmp_path / "upload-manifests",
    )
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"Key": "ok"})

    result = execute_generated_source_artifact_uploads(
        [item],
        upload=True,
        supabase_url="https://project.supabase.co",
        service_role_key="service-role-secret",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.uploaded_count == 1
    assert result.items[0].status is SourceStorageUploadStatus.UPLOADED
    assert len(requests) == 2
    assert requests[0].headers["authorization"] == "Bearer service-role-secret"
    assert requests[0].url.path.endswith("/clingen-local.sqlite")
    assert requests[1].url.path.endswith("/clingen-local.sqlite.manifest.json")


def test_generated_artifact_s3_upload_failure_is_sanitized(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _materialize_clingen(settings, tmp_path)
    [item] = build_generated_source_artifact_upload_items(
        settings,
        artifact_ids=("clingen_local",),
        bucket_id="eamos-source-assets",
        manifest_staging_root=tmp_path / "upload-manifests",
    )

    class FailingS3Client:
        def upload_file(self, filename: str, *_args: object, **_kwargs: object) -> None:
            raise RuntimeError(f"failed local file {filename}")

    result = execute_generated_source_artifact_uploads(
        [item],
        upload=True,
        upload_mode=SourceStorageUploadMode.S3_MULTIPART,
        s3_client=FailingS3Client(),
    )

    assert result.failed_count == 1
    assert result.items[0].status is SourceStorageUploadStatus.FAILED
    assert result.items[0].message == "private S3 multipart upload failed"
    encoded = json.dumps(result.to_sanitized_dict()).lower()
    assert str(tmp_path).lower() not in encoded


def test_generated_artifact_sync_downloads_private_pubmed_object(
    tmp_path: Path,
) -> None:
    source_settings = _settings(tmp_path / "source")
    _materialize_pubmed(source_settings, tmp_path / "source")
    [item] = build_generated_source_artifact_upload_items(
        source_settings,
        artifact_ids=("pubmed_local",),
        bucket_id="eamos-source-assets",
        manifest_staging_root=tmp_path / "upload-manifests",
    )
    source_payload = source_settings.pubmed_local_sqlite_path.read_bytes()
    manifest_payload = item.manifest_path.read_bytes()
    payloads = {
        _encoded_storage_path(item.object_path): source_payload,
        _encoded_storage_path(item.manifest_object_path): manifest_payload,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.url.path.split("/storage/v1/object/eamos-source-assets/", 1)[-1]
        content = payloads.get(key)
        if content is None:
            return httpx.Response(404)
        return httpx.Response(200, content=content)

    runtime_settings = _settings(tmp_path / "runtime")
    runtime_settings.supabase_url = "https://project.supabase.co"
    runtime_settings.supabase_service_role_key = "service-role-secret"

    result = materialize_generated_source_artifact(
        runtime_settings,
        artifact_id="pubmed_local",
        source_object_uri=f"supabase://eamos-source-assets/{item.object_path}",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.ready is True
    assert result.status == "ready"
    assert result.downloaded is True
    assert result.copied is False
    assert result.manifest_written is True
    assert result.md5_verified is True
    assert result.sha256_verified is True
    assert runtime_settings.pubmed_local_sqlite_path.read_bytes() == source_payload
    assert inspect_pubmed_local_store(runtime_settings).ready is True
    encoded = json.dumps(result.to_sanitized_dict()).lower()
    assert item.object_path.lower() not in encoded
    assert "service-role-secret" not in encoded
    assert str(tmp_path).lower() not in encoded


def test_generated_artifact_sync_downloads_private_pubmed_object_from_s3(
    tmp_path: Path,
) -> None:
    source_settings = _settings(tmp_path / "source")
    _materialize_pubmed(source_settings, tmp_path / "source")
    [item] = build_generated_source_artifact_upload_items(
        source_settings,
        artifact_ids=("pubmed_local",),
        bucket_id="eamos-source-assets",
        manifest_staging_root=tmp_path / "upload-manifests",
    )
    source_payload = source_settings.pubmed_local_sqlite_path.read_bytes()
    manifest_payload = item.manifest_path.read_bytes()
    payloads = {
        item.object_path: source_payload,
        item.manifest_object_path: manifest_payload,
    }

    class Body:
        def __init__(self, payload: bytes) -> None:
            self.payload = payload

        def read(self) -> bytes:
            return self.payload

    class FakeS3Client:
        def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
            assert Bucket == "eamos-source-assets"
            return {"Body": Body(payloads[Key])}

        def download_fileobj(self, bucket: str, key: str, fileobj, **_kwargs: object) -> None:
            assert bucket == "eamos-source-assets"
            fileobj.write(payloads[key])

    runtime_settings = _settings(tmp_path / "runtime")

    result = materialize_generated_source_artifact(
        runtime_settings,
        artifact_id="pubmed_local",
        source_object_uri=f"supabase://eamos-source-assets/{item.object_path}",
        download_mode=SourceStorageUploadMode.S3_MULTIPART,
        s3_client=FakeS3Client(),
    )

    assert result.ready is True
    assert result.status == "ready"
    assert result.source_kind == "supabase_private_storage_s3"
    assert result.downloaded is True
    assert result.copied is False
    assert result.manifest_written is True
    assert result.md5_verified is True
    assert result.sha256_verified is True
    assert runtime_settings.pubmed_local_sqlite_path.read_bytes() == source_payload
    assert inspect_pubmed_local_store(runtime_settings).ready is True
    encoded = json.dumps(result.to_sanitized_dict()).lower()
    assert item.object_path.lower() not in encoded
    assert str(tmp_path).lower() not in encoded


def test_generated_artifact_sync_s3_requires_credentials_without_network(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path / "runtime")

    result = materialize_generated_source_artifact(
        settings,
        artifact_id="pubmed_local",
        source_object_uri="supabase://eamos-source-assets/generated/example.sqlite",
        download_mode=SourceStorageUploadMode.S3_MULTIPART,
    )

    assert result.ready is False
    assert result.status == "supabase_storage_s3_credentials_missing"
    assert result.source_kind == "supabase_private_storage_s3"
    encoded = json.dumps(result.to_sanitized_dict()).lower()
    assert "example.sqlite" not in encoded
    assert str(tmp_path).lower() not in encoded


def test_generated_artifact_sync_rejects_schema_invalid_local_artifact(
    tmp_path: Path,
) -> None:
    bad_source = tmp_path / "bad.sqlite"
    bad_source.write_bytes(b"not sqlite")
    settings = _settings(tmp_path / "runtime")

    result = materialize_generated_source_artifact(
        settings,
        artifact_id="literature_embeddings",
        source_artifact_path=bad_source,
    )

    assert result.ready is False
    assert result.status.startswith("schema_validation_failed:")
    assert not settings.rag_sqlite_path.exists()


def test_generated_artifact_sync_accepts_clinvar_gene_distribution_index(
    tmp_path: Path,
) -> None:
    source_settings = _settings(tmp_path / "source")
    _materialize_clinvar_gene_distribution(source_settings)
    runtime_settings = _settings(tmp_path / "runtime")

    result = materialize_generated_source_artifact(
        runtime_settings,
        artifact_id="clinvar_gene_distribution_index",
        source_artifact_path=source_settings.clinvar_gene_distribution_index_path,
    )

    assert result.ready is True
    assert result.status == "ready"
    assert result.copied is True
    assert result.manifest_written is True
    assert inspect_clinvar_gene_distribution_index(runtime_settings).ready is True
    manifest = json.loads(runtime_settings.clinvar_gene_distribution_manifest_path.read_text())
    assert manifest["artifact_id"] == "clinvar_gene_distribution_index"
    assert manifest["asset_id"] == "clinvar_gene_distribution_sqlite"
    assert manifest["upstream_source_id"] == "ncbi_clinvar_vcf"
    encoded = json.dumps(result.to_sanitized_dict()).lower()
    assert str(tmp_path).lower() not in encoded


def test_generated_artifact_upload_cli_plans_without_paths(capsys) -> None:
    exit_code = eamos_generated_artifact_upload.main(["--artifact", "clingen_local", "--compact"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "eamos_generated_artifact_upload"
    assert output["upload_performed"] is False
    assert output["guardrails"]["supabase_metadata_mutation"] == "not_used"
    encoded = json.dumps(output).lower()
    assert "service_role" not in encoded
    assert "app/backend/data" not in encoded


def test_generated_artifact_sync_cli_fails_closed_without_source(
    capsys,
    tmp_path: Path,
) -> None:
    exit_code = eamos_generated_artifact_sync.main(
        [
            "--artifact",
            "clingen_local",
            "--destination",
            str(tmp_path / "clingen-local.sqlite"),
            "--manifest-destination",
            str(tmp_path / "clingen-local.manifest.json"),
            "--require-ready",
            "--compact",
        ]
    )

    assert exit_code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "eamos_generated_artifact_sync"
    assert output["status"] == "source_unconfigured"
    assert output["guardrails"]["provider_flip"] == "not_used"
    assert str(tmp_path).lower() not in json.dumps(output).lower()


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        jwt_secret="test-secret",
        clingen_local_sqlite_path=tmp_path / "clingen" / "clingen-local.sqlite",
        clingen_local_manifest_path=tmp_path / "clingen" / "clingen-local.manifest.json",
        pubmed_local_sqlite_path=tmp_path / "pubmed" / "pubmed-local.sqlite",
        pubmed_local_manifest_path=tmp_path / "pubmed" / "pubmed-local.manifest.json",
        rag_sqlite_path=tmp_path / "literature" / "literature-embeddings.sqlite",
        rag_manifest_path=tmp_path / "literature" / "literature-embeddings.manifest.json",
        clinvar_gene_distribution_index_path=(
            tmp_path / "clinvar" / "clinvar-gene-distribution.sqlite"
        ),
        clinvar_gene_distribution_manifest_path=(
            tmp_path / "clinvar" / "clinvar-gene-distribution.manifest.json"
        ),
    )


def _materialize_all_tier1(settings: Settings, tmp_path: Path) -> None:
    _materialize_clingen(settings, tmp_path)
    _materialize_pubmed(settings, tmp_path)
    _materialize_literature(settings)
    _materialize_clinvar_gene_distribution(settings)


def _materialize_clingen(settings: Settings, tmp_path: Path) -> None:
    path = tmp_path / "clingen-erepo.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "uuid": "rpe65-1",
                "gene": "RPE65",
                "classification": "Pathogenic",
                "hgvs": ["NM_000329.3:c.260A>G"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = materialize_clingen_local_store(
        settings,
        erepo_jsonl_files=[path],
        source_version="clingen-test",
        force=True,
    )
    assert result.ready is True


def _materialize_pubmed(settings: Settings, tmp_path: Path) -> None:
    seed = tmp_path / "pubmed-seed.tsv"
    seed.parent.mkdir(parents=True, exist_ok=True)
    seed.write_text(
        "\n".join(
            [
                "gene\tcdna\ttranscript\tprotein_change\trsid\tgenomic_hg38\tscope",
                "RPE65\tc.260A>G\tNM_000329.3:c.260A>G\tp.Asp87Gly\trs1645931040\t1-68444869-T-C\tvariant",
            ]
        ),
        encoding="utf-8",
    )
    result = materialize_pubmed_local_store(
        settings,
        xml_files=[PUBMED_XML],
        query_file=seed,
        source_version="pubmed-test",
        force=True,
    )
    assert result.ready is True


def _materialize_literature(settings: Settings) -> None:
    settings.rag_sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    store = LiteratureEmbeddingStore(
        settings.rag_sqlite_path,
        manifest_path=settings.rag_manifest_path,
    )
    store.write(
        [
            (
                LiteratureSourceRecord(
                    pmid="111",
                    genes=["RPE65"],
                    title="RPE65 retinal study",
                    snippet="Licensed abstract snippet",
                    embed_text="RPE65 retinal study",
                    year=2022,
                    source_url="https://pubmed.ncbi.nlm.nih.gov/111/",
                    license_profile="cc_by",
                ),
                [1.0, 0.0, 0.0, 0.0],
            )
        ],
        embedding_model="test-embed",
        embedding_dim=4,
        source_version="literature-test",
    )


def _materialize_clinvar_gene_distribution(settings: Settings) -> None:
    result = materialize_clinvar_gene_distribution_index(
        vcf_path=DEFAULT_CLINVAR_VCF_FIXTURE_PATH,
        index_path=settings.clinvar_gene_distribution_index_path,
        manifest_path=settings.clinvar_gene_distribution_manifest_path,
        force=True,
    )
    assert result.ready is True


def _encoded_storage_path(object_path: str) -> str:
    return "/".join(quote(part, safe="") for part in object_path.split("/"))
