from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import Settings
from app.core.db import build_session_factory, initialize_database
from app.repos.protein_annotation_cache_repo import ProteinAnnotationCacheRepo
from app.repos.source_cache_repo import SourceCacheRepo
from app.repos.supabase_local_model_cache_repo import (
    HybridProteinAnnotationCacheRepo,
    HybridSourceCacheRepo,
    HybridVariantCacheRepo,
    LocalModelCacheEntry,
    SupabaseLocalModelCacheError,
    SupabaseProteinAnnotationCacheRepo,
    SupabaseSourceCacheRepo,
    SupabaseVariantCacheRepo,
)
from app.repos.variant_cache_repo import VariantCacheRepo
from app.schemas.protein_annotation import (
    ProteinDomainTrack,
    ProteinDomainTrackFeature,
    ProteinTrackProvenance,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


class FakeLocalModelCacheStore:
    def __init__(self) -> None:
        self.entries: dict[tuple[str, str, str], LocalModelCacheEntry] = {}
        self.source_versions: list[dict] = []
        self.jobs: list[dict] = []
        self.fail_read = False
        self.fail_write = False

    def get_entry(
        self,
        *,
        cache_family: str,
        source_id: str,
        cache_key: str,
    ) -> LocalModelCacheEntry | None:
        if self.fail_read:
            raise SupabaseLocalModelCacheError("read failed")
        return self.entries.get((cache_family, source_id, cache_key))

    def upsert_entry(self, entry: LocalModelCacheEntry) -> None:
        if self.fail_write:
            raise SupabaseLocalModelCacheError("write failed")
        self.entries[(entry.cache_family, entry.source_id, entry.cache_key)] = entry

    def record_source_version(self, **kwargs) -> None:
        if self.fail_write:
            raise SupabaseLocalModelCacheError("source version write failed")
        self.source_versions.append(kwargs)

    def record_job(self, **kwargs) -> None:
        if self.fail_write:
            raise SupabaseLocalModelCacheError("job write failed")
        self.jobs.append(kwargs)

    def smoke_test(self) -> None:
        entry = LocalModelCacheEntry(
            cache_family="supabase_cache_smoke",
            source_id="warm_source_cache",
            cache_key="smoke:test",
            status="smoke",
            payload={"ok": True},
        )
        self.upsert_entry(entry)
        assert self.get_entry(
            cache_family=entry.cache_family,
            source_id=entry.source_id,
            cache_key=entry.cache_key,
        )
        del self.entries[(entry.cache_family, entry.source_id, entry.cache_key)]


def _session_factory(tmp_path: Path):
    session_factory = build_session_factory(
        f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}"
    )
    initialize_database(session_factory)
    return session_factory


def test_variant_cache_reads_supabase_dev_cache_on_local_miss(tmp_path: Path) -> None:
    local_repo = VariantCacheRepo(_session_factory(tmp_path))
    store = FakeLocalModelCacheStore()
    remote_repo = SupabaseVariantCacheRepo(store)
    hybrid = HybridVariantCacheRepo(local_repo=local_repo, remote_repo=remote_repo)

    remote_repo.upsert(
        "RPE65:c.260A>G",
        litvar_id="litvar-rpe65-c260ag",
        total_publications=3,
        publication_data={"ep_vlex": {"total_count": 3}},
        strict_genomic_cache={"variant": {"genomic_hg38": "1-68444869-T-C"}},
    )

    hit = hybrid.get_fresh("RPE65:c.260A>G", ttl_days=30)

    assert hit is not None
    assert hit["litvar_id"] == "litvar-rpe65-c260ag"
    assert hit["publication_data"]["ep_vlex"]["total_count"] == 3
    assert hit["strict_genomic_cache"]["variant"]["genomic_hg38"] == "1-68444869-T-C"


def test_variant_cache_write_through_keeps_local_cache_when_supabase_fails(
    tmp_path: Path,
    caplog,
) -> None:
    caplog.set_level(logging.WARNING, logger="app.repos.supabase_local_model_cache_repo")
    local_repo = VariantCacheRepo(_session_factory(tmp_path))
    store = FakeLocalModelCacheStore()
    store.fail_write = True
    hybrid = HybridVariantCacheRepo(
        local_repo=local_repo,
        remote_repo=SupabaseVariantCacheRepo(store),
    )

    hybrid.upsert(
        "USH2A:c.2276G>T",
        litvar_id=None,
        total_publications=1,
        publication_data={"summary": {"total_publications": 1}},
        strict_genomic_cache={"variant": {"genomic_hg38": "1-216247118-C-A"}},
    )

    hit = local_repo.get_fresh("USH2A:c.2276G>T", ttl_days=30)
    assert hit is not None
    assert hit["strict_genomic_cache"]["variant"]["genomic_hg38"] == "1-216247118-C-A"
    assert store.entries == {}
    assert "Supabase local model cache write failed; using local fallback" in caplog.text
    assert "cache_family=variant_report" in caplog.text
    assert "USH2A:c.2276G>T" not in caplog.text


def test_source_cache_remote_round_trip_preserves_freshness_and_warnings() -> None:
    remote_repo = SupabaseSourceCacheRepo(FakeLocalModelCacheStore())

    remote_repo.upsert(
        "clingen",
        "clinvar:VCV001421454",
        normalized_identity={"gene": "RPE65", "clinvar_accession": "VCV001421454"},
        request_identity={"cache_key": "clinvar:VCV001421454"},
        status="live",
        summary={"expert_panel": {"final_classification": "likely_pathogenic"}},
        raw={"cached": True},
        warnings=["cached_warning"],
        source_url="https://erepo.clinicalgenome.org/evrepo/api/classifications/CA189146",
        ttl_days=-1,
        source_version="ClinGen Evidence Repository cached",
    )

    assert remote_repo.get_fresh("clingen", "clinvar:VCV001421454") is None
    stale = remote_repo.get_stale("clingen", "clinvar:VCV001421454")

    assert stale is not None
    assert stale.source_version == "ClinGen Evidence Repository cached"
    assert stale.summary["expert_panel"]["final_classification"] == "likely_pathogenic"
    assert stale.warnings == ["cached_warning"]
    result = stale.to_tool_result(
        status="stale",
        cache_status="stale_on_failure",
        extra_warnings=["source_cache_stale_on_failure:clingen"],
    )
    assert result.cache_status == "stale_on_failure"
    assert "source_cache_stale_on_failure:clingen" in result.warnings


def test_hybrid_source_cache_falls_back_to_supabase_for_fresh_remote_hit(
    tmp_path: Path,
) -> None:
    local_repo = SourceCacheRepo(_session_factory(tmp_path))
    store = FakeLocalModelCacheStore()
    remote_repo = SupabaseSourceCacheRepo(store)
    remote_repo.upsert(
        "gnomad",
        "gnomad:gnomad_r4:1-68444869-t-c",
        normalized_identity={"gene": "RPE65"},
        request_identity={"variant_id": "1-68444869-T-C"},
        status="live",
        summary={"allele_frequency": 0.00001},
        raw={"cached": True},
        warnings=[],
        source_url="https://gnomad.broadinstitute.org/",
        ttl_days=30,
        source_version="gnomAD v4.1.1",
    )
    hybrid = HybridSourceCacheRepo(local_repo=local_repo, remote_repo=remote_repo)

    hit = hybrid.get_fresh("gnomad", "gnomad:gnomad_r4:1-68444869-t-c")

    assert hit is not None
    assert hit.status == "live"
    assert hit.summary["allele_frequency"] == 0.00001
    assert hit.source_version == "gnomAD v4.1.1"


def test_protein_annotation_supabase_cache_round_trip_records_provenance_and_job() -> None:
    store = FakeLocalModelCacheStore()
    remote_repo = SupabaseProteinAnnotationCacheRepo(store)
    track = ProteinDomainTrack(
        status="available",
        sequence_label="FZD5",
        gene_symbol="FZD5",
        protein_accession="Q13467",
        protein_sequence_hash="a" * 64,
        protein_length=585,
        translated_from="protein",
        cache_key=(
            "protein_annotation:sha256:"
            + "a" * 64
            + ":pfam:Pfam 37.0:hmmer:HMMER 3.4:uniprot:UniProtKB 2026_02"
        ),
        cache_status="stored",
        pfam_release="Pfam 37.0",
        hmmer_release="HMMER 3.4",
        uniprot_release="UniProtKB 2026_02",
        features=[
            ProteinDomainTrackFeature(
                feature_id="uniprot:Q13467:SIGNAL:1-31:1",
                kind="signal_peptide",
                label="Signal peptide",
                short_label="SP",
                aa_start=1,
                aa_end=31,
                source="UniProtKB/Swiss-Prot feature table",
                source_accession="Q13467",
                source_release="UniProtKB 2026_02",
                source_checksum_sha256="b" * 64,
                description="Signal peptide",
                lane="topology",
            )
        ],
        provenance=[
            ProteinTrackProvenance(
                source_id="uniprotkb_reviewed_swissprot",
                source_name="UniProtKB reviewed Swiss-Prot",
                source_url="https://www.uniprot.org/",
                source_release="UniProtKB 2026_02",
                checksum_sha256="b" * 64,
                license_status="cc_by_4_0",
            )
        ],
        warnings=["protein_annotation_no_live_api_fallback"],
    )

    remote_repo.upsert(track)
    cached = remote_repo.get(
        sequence_hash="a" * 64,
        pfam_release="Pfam 37.0",
        hmmer_release="HMMER 3.4",
        uniprot_release="UniProtKB 2026_02",
    )

    assert cached is not None
    assert cached.gene_symbol == "FZD5"
    assert cached.features[0].short_label == "SP"
    assert cached.features[0].source_checksum_sha256 == "b" * 64
    assert store.source_versions[0]["source_id"] == "uniprotkb_reviewed_swissprot"
    assert store.source_versions[0]["checksum_sha256"] == "b" * 64
    assert store.jobs[0]["job_type"] == "protein_annotation_cache_store"
    assert store.jobs[0]["status"] == "available"


def test_hybrid_protein_cache_uses_local_first_and_ignores_remote_read_failure(
    tmp_path: Path,
) -> None:
    local_repo = ProteinAnnotationCacheRepo(_session_factory(tmp_path))
    store = FakeLocalModelCacheStore()
    store.fail_read = True
    hybrid = HybridProteinAnnotationCacheRepo(
        local_repo=local_repo,
        remote_repo=SupabaseProteinAnnotationCacheRepo(store),
    )

    assert (
        hybrid.get(
            sequence_hash="missing",
            pfam_release="Pfam 37.0",
            hmmer_release="HMMER 3.4",
        )
        is None
    )


def test_frontend_code_does_not_reference_private_cache_schema_or_service_role() -> None:
    frontend_roots = [REPO_ROOT / "app" / "web", REPO_ROOT / "app" / "frontend"]
    checked_files = 0
    extensions = {".ts", ".tsx", ".js", ".jsx", ".json", ".env", ".example"}
    for root in frontend_roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in extensions:
                continue
            if "node_modules" in path.parts or ".next" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            checked_files += 1
            assert "eamos_private" not in text, f"private schema leaked into {path}"
            assert (
                "NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY" not in text
            ), f"service role key exposed through public env in {path}"
            assert (
                "NEXT_PUBLIC_SERVICE_ROLE" not in text
            ), f"service role key exposed through public env in {path}"
    assert checked_files > 0


def test_landing_example_warmer_uses_supabase_hybrid_cache_when_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from app.cli import warm_source_cache

    store = FakeLocalModelCacheStore()
    monkeypatch.setattr(
        warm_source_cache,
        "build_supabase_local_model_cache_store",
        lambda settings: store,
    )
    settings = Settings(
        jwt_secret="test-secret",
        supabase_local_model_cache_enabled=True,
        supabase_local_model_cache_database_url="postgresql+psycopg://unused",
    )
    variant_repo, source_repo, supabase_store = warm_source_cache._build_cache_repos(
        settings,
        _session_factory(tmp_path),
    )

    assert supabase_store is store
    assert isinstance(variant_repo, HybridVariantCacheRepo)
    assert isinstance(source_repo, HybridSourceCacheRepo)

    source_repo.upsert(
        "pubmed",
        "RPE65:c.260A>G",
        normalized_identity={"gene": "RPE65", "cdna": "c.260A>G"},
        request_identity={"query": "RPE65 c.260A>G"},
        status="live",
        summary={"total": 1},
        raw={"cached": True},
        warnings=[],
        source_url="https://pubmed.ncbi.nlm.nih.gov/?term=RPE65+c.260A%3EG",
        ttl_days=30,
        source_version="PubMed cached",
    )
    variant_repo.upsert(
        "RPE65:c.260A>G",
        litvar_id="litvar-rpe65-c260ag",
        total_publications=1,
        publication_data={"summary": {"total_publications": 1}},
        strict_genomic_cache={"variant": {"genomic_hg38": "1-68444869-T-C"}},
    )

    assert ("source_cache", "pubmed", "RPE65:c.260A>G") in store.entries
    assert ("variant_report", "variant_cache", "RPE65:c.260A>G") in store.entries


def test_supabase_cache_store_smoke_test_round_trip_cleans_up() -> None:
    store = FakeLocalModelCacheStore()

    store.smoke_test()

    assert store.entries == {}
