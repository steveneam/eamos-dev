from __future__ import annotations

from hashlib import md5
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

import app.services.pubmed_local as pubmed_local_module
from app.cli import eamos_pubmed_local_materialize, eamos_pubmed_local_preflight
from app.core.config import Settings
from app.services.pubmed_local import (
    PubMedLocalStore,
    abstract_policy_for_license,
    classify_license_profile,
    inspect_pubmed_local_store,
    materialize_pubmed_local_store,
)
from app.services.publication_literature import EamosProprietaryVariantLiteratureExtractor
from app.tools.base import ToolResult
from app.tools.pubmed import PubmedTool

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures" / "tools"
PUBMED_XML = FIXTURES_DIR / "pubmed_local_sample.xml"


def _settings(tmp_path: Path, **overrides) -> Settings:
    return Settings(
        jwt_secret="test-secret",
        pubmed_local_sqlite_path=tmp_path / "pubmed-local.sqlite",
        pubmed_local_manifest_path=tmp_path / "pubmed-local.manifest.json",
        **overrides,
    )


def _seed_file(tmp_path: Path) -> Path:
    path = tmp_path / "pubmed-seed.tsv"
    path.write_text(
        "\n".join(
            [
                "gene\tcdna\ttranscript\tprotein_change\trsid\tgenomic_hg38\tscope",
                "RPE65\tc.260A>G\tNM_000329.3:c.260A>G\tp.Asp87Gly\trs1645931040\t1-68444869-T-C\tvariant",
                "RPE65\t\t\t\t\t\tgene",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _gene_seed_file(tmp_path: Path, gene: str) -> Path:
    path = tmp_path / f"{gene.lower()}-pubmed-seed.tsv"
    path.write_text(
        "\n".join(
            [
                "gene\tcdna\ttranscript\tprotein_change\trsid\tgenomic_hg38\tscope",
                f"{gene}\t\t\t\t\t\tgene",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _variant(**overrides):
    payload = {
        "gene": "RPE65",
        "transcript_hgvs": "NM_000329.3:c.260A>G",
        "protein_change": "p.Asp87Gly",
        "dbsnp_rsid": "rs1645931040",
        "genomic_hg38": "1-68444869-T-C",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_pubmed_local_policy_gates_abstract_storage() -> None:
    assert classify_license_profile("Creative Commons Attribution License") == "cc_by"
    assert classify_license_profile("CC BY-SA 4.0") == "cc_by_sa"
    assert classify_license_profile("cc-by") == "cc_by"
    assert classify_license_profile("cc-by-nc") == "noncommercial"
    assert classify_license_profile("U.S. Government work") == "us_government"
    assert classify_license_profile("Copyright 2024 Publisher") == "publisher_copyright"
    assert classify_license_profile("CC BY-NC") == "noncommercial"

    assert abstract_policy_for_license("cc_by", "abstract") == "licensed_text_persisted"
    assert (
        abstract_policy_for_license("publisher_copyright", "abstract")
        == "metadata_only_license_unverified"
    )
    assert abstract_policy_for_license("unknown", None) == "metadata_only_no_abstract"


def test_pubmed_local_materialization_filters_terms_and_sanitizes_text(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    result = materialize_pubmed_local_store(
        settings,
        xml_files=[PUBMED_XML],
        query_file=_seed_file(tmp_path),
        source_version="pubmed-local-test",
        force=True,
    )

    assert result.ready is True
    assert result.status == "ready"
    assert result.article_count == 2
    assert result.licensed_abstract_count == 1
    assert result.metadata_only_count == 1
    assert result.deleted_count == 1
    assert result.coverage_count >= 2
    assert result.checksum_value

    inspection = inspect_pubmed_local_store(settings)
    assert inspection.ready is True
    assert inspection.status == "ready"
    assert inspection.checksum_verified is True
    encoded = json.dumps(inspection.to_sanitized_dict()).lower()
    assert str(tmp_path).lower() not in encoded
    assert "asp87gly variant was observed" not in encoded

    with sqlite3.connect(settings.pubmed_local_sqlite_path) as conn:
        row = conn.execute(
            "select abstract_text, abstract_policy from pubmed_article where pmid = ?",
            ("37042101",),
        ).fetchone()
    assert row == (None, "metadata_only_license_unverified")


def test_pubmed_local_records_source_file_manifest_and_import_stats(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    xml_path = baseline_dir / "pubmed25n0001.xml"
    xml_path.write_bytes(PUBMED_XML.read_bytes())
    xml_path.with_name(f"{xml_path.name}.md5").write_text(
        f"{md5(xml_path.read_bytes(), usedforsecurity=False).hexdigest()}  {xml_path.name}\n",
        encoding="utf-8",
    )
    settings = _settings(tmp_path)

    result = materialize_pubmed_local_store(
        settings,
        xml_files=[xml_path],
        query_file=_seed_file(tmp_path),
        source_version="pubmed-local-test",
        verify_md5_sidecars=True,
        force=True,
    )

    assert result.ready is True
    assert result.source_file_count == 1
    assert result.source_kind_counts == {"pubmed_baseline": 1}
    assert result.import_stats_by_source["pubmed_baseline"] == {
        "source_file_count": 1,
        "records_seen_count": 3,
        "article_imported_count": 2,
        "deleted_imported_count": 1,
        "domain_filtered_count": 0,
        "seed_filtered_count": 0,
        "invalid_record_count": 0,
        "pmc_license_overlay_count": 0,
        "literature_edge_imported_count": 0,
        "literature_edge_orphan_skipped_count": 0,
        "licensed_abstract_count": 1,
        "metadata_only_count": 1,
    }

    inspection = inspect_pubmed_local_store(settings)
    assert inspection.source_kind_counts == {"pubmed_baseline": 1}
    assert inspection.import_stats_by_source == result.import_stats_by_source

    with sqlite3.connect(settings.pubmed_local_sqlite_path) as conn:
        source_row = conn.execute("""
            select load_order, source_kind, source_format, source_file_name, md5_status,
                   records_seen_count, article_imported_count, deleted_imported_count
            from pubmed_source_file
            """).fetchone()
        manifest_row = conn.execute("""
            select source_file_count, source_kind_counts_json, import_stats_by_source_json
            from pubmed_materialization_manifest
            where id = 1
            """).fetchone()
        provenance = conn.execute(
            "select provenance_json from pubmed_article where pmid = ?",
            ("38191234",),
        ).fetchone()[0]

    assert source_row == (
        1,
        "pubmed_baseline",
        "pubmed_xml",
        "pubmed25n0001.xml",
        "verified",
        3,
        2,
        1,
    )
    assert str(tmp_path) not in json.dumps(tuple(source_row))
    assert manifest_row[0] == 1
    assert json.loads(manifest_row[1]) == {"pubmed_baseline": 1}
    assert json.loads(manifest_row[2])["pubmed_baseline"]["article_imported_count"] == 2
    provenance_payload = json.loads(provenance)
    assert provenance_payload["source_file"] == {
        "file_name": "pubmed25n0001.xml",
        "load_order": 1,
        "source_format": "pubmed_xml",
        "source_kind": "pubmed_baseline",
    }


def test_pubmed_local_pmc_license_overlay_unlocks_permissive_abstract(
    tmp_path: Path,
) -> None:
    jsonl_path = tmp_path / "pubmed.jsonl"
    jsonl_path.write_text(
        json.dumps(
            {
                "pmid": "38000001",
                "pmcid": "PMC38000001",
                "title": "RPE65 c.260A>G variant biology",
                "abstract": "RPE65 c.260A>G has a measurable protein phenotype.",
                "journal": "Example Biology",
                "year": "2024",
                "language": "eng",
                "publication_types": ["Journal Article"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    license_path = tmp_path / "pmc-oa.tsv"
    license_path.write_text(
        "pmcid\tlicense_code\nPMC38000001\tcc-by\n",
        encoding="utf-8",
    )
    settings = _settings(tmp_path)

    result = materialize_pubmed_local_store(
        settings,
        jsonl_files=[jsonl_path],
        pmc_license_files=[license_path],
        query_file=_seed_file(tmp_path),
        source_version="pubmed-local-test",
        force=True,
    )

    assert result.ready is True
    assert result.licensed_abstract_count == 1
    assert result.pmc_license_overlay_count == 1
    with sqlite3.connect(settings.pubmed_local_sqlite_path) as conn:
        row = conn.execute(
            "select license_profile, abstract_policy, abstract_text, provenance_json "
            "from pubmed_article where pmid = ?",
            ("38000001",),
        ).fetchone()
    assert row[0] == "cc_by"
    assert row[1] == "licensed_text_persisted"
    assert "measurable protein phenotype" in row[2]
    assert "pmc_license_overlay" in row[3]


def test_pubmed_local_biomedical_filter_excludes_obvious_non_biomedical_rows(
    tmp_path: Path,
) -> None:
    jsonl_path = tmp_path / "mixed-domain.jsonl"
    rows = [
        {
            "pmid": "38000002",
            "title": "RPE65 variant biology in retinal disease",
            "abstract": "The RPE65 gene variant changes protein activity in cells.",
            "journal": "Example Biology",
            "year": "2024",
            "language": "eng",
            "publication_types": ["Journal Article"],
            "license_profile": "cc-by",
        },
        {
            "pmid": "38000003",
            "title": "Bridge engineering load model",
            "abstract": "A civil engineering construction study for bridge loading.",
            "journal": "Example Engineering",
            "year": "2024",
            "language": "eng",
            "publication_types": ["Journal Article"],
            "license_profile": "cc-by",
        },
        {
            "pmid": "38000006",
            "title": "Chemical engineering of retinal gene delivery biomaterials",
            "abstract": "A biomedical engineering study of biomaterials for retinal therapy.",
            "journal": "Example Bioengineering",
            "year": "2024",
            "language": "eng",
            "publication_types": ["Journal Article"],
            "license_profile": "cc-by",
        },
    ]
    jsonl_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    settings = _settings(tmp_path)

    result = materialize_pubmed_local_store(
        settings,
        jsonl_files=[jsonl_path],
        domain_filter="biomedical",
        source_version="pubmed-local-test",
        force=True,
    )

    assert result.ready is True
    assert result.article_count == 2
    assert result.domain_filtered_count == 1
    with sqlite3.connect(settings.pubmed_local_sqlite_path) as conn:
        pmids = [row[0] for row in conn.execute("select pmid from pubmed_article")]
    assert pmids == ["38000002", "38000006"]


def test_pubmed_local_short_gene_symbol_does_not_match_lowercase_prose(
    tmp_path: Path,
) -> None:
    jsonl_path = tmp_path / "was.jsonl"
    rows = [
        {
            "pmid": "38000004",
            "title": "WAS gene expression in immune disease",
            "abstract": "The WAS gene has an immune-cell phenotype.",
            "journal": "Example Immunology",
            "year": "2024",
            "language": "eng",
            "publication_types": ["Journal Article"],
        },
        {
            "pmid": "38000005",
            "title": "The model was fitted to bridge data",
            "abstract": "A finance and bridge engineering model was compared.",
            "journal": "Example Engineering",
            "year": "2024",
            "language": "eng",
            "publication_types": ["Journal Article"],
        },
    ]
    jsonl_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    settings = _settings(tmp_path)

    result = materialize_pubmed_local_store(
        settings,
        jsonl_files=[jsonl_path],
        query_file=_gene_seed_file(tmp_path, "WAS"),
        source_version="pubmed-local-test",
        force=True,
    )

    assert result.ready is True
    assert result.article_count == 1
    with sqlite3.connect(settings.pubmed_local_sqlite_path) as conn:
        pmids = [row[0] for row in conn.execute("select pmid from pubmed_article")]
    assert pmids == ["38000004"]


def test_pubmed_local_store_returns_local_tool_result(tmp_path: Path) -> None:
    settings = _settings(tmp_path, pubmed_local_enabled=True)
    materialize_pubmed_local_store(
        settings,
        xml_files=[PUBMED_XML],
        query_file=_seed_file(tmp_path),
        source_version="pubmed-local-test",
        force=True,
    )

    result, needs_live = PubMedLocalStore(
        settings.pubmed_local_sqlite_path,
        manifest_path=settings.pubmed_local_manifest_path,
        enabled=True,
    ).search_tool_result(_variant(), limit=10)

    assert needs_live is False
    assert result.status == "local"
    assert result.cache_status == "pubmed_local_materialized"
    assert result.source_version == "pubmed-local-test"
    assert result.summary["total"] == 1
    assert result.summary["articles"][0]["pmid"] == "38191234"
    assert "p.Asp87Gly" in result.summary["articles"][0]["abstract"]
    assert result.summary["gene_scope"]["total_count"] == 2


def test_pubmed_local_imports_pubtator_and_litvar_edges_for_variant_search(
    tmp_path: Path,
) -> None:
    jsonl_path = tmp_path / "neutral-pubmed.jsonl"
    jsonl_path.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {
                    "pmid": "39000001",
                    "title": "Retinal disease cohort study",
                    "abstract": "A hereditary eye disease cohort was evaluated.",
                    "journal": "Example Ophthalmology",
                    "year": "2025",
                    "language": "eng",
                    "publication_types": ["Journal Article"],
                    "license_profile": "cc-by",
                },
                {
                    "pmid": "39000002",
                    "title": "Independent retinal disease case series",
                    "abstract": "A second cohort was evaluated with sequencing.",
                    "journal": "Example Genetics",
                    "year": "2024",
                    "language": "eng",
                    "publication_types": ["Journal Article"],
                    "license_profile": "cc-by",
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )
    pubtator_edges = tmp_path / "pubtator-edges.jsonl"
    pubtator_edges.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {
                    "pmid": "39000001",
                    "source": "pubtator",
                    "entity_type": "gene",
                    "identifier": "RPE65",
                    "matched_text": "RPE65",
                    "section": "abstract",
                    "evidence_text": "The RPE65 c.260A>G variant was observed.",
                },
                {
                    "pmid": "39000001",
                    "source": "pubtator",
                    "entity_type": "variant",
                    "identifier": "c.260A>G",
                    "matched_text": "c.260A>G",
                    "section": "abstract",
                    "evidence_text": "The RPE65 c.260A>G variant was observed.",
                },
                {
                    "pmid": "99999999",
                    "source": "pubtator",
                    "entity_type": "variant",
                    "identifier": "c.260A>G",
                    "matched_text": "c.260A>G",
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )
    litvar_edges = tmp_path / "litvar-edges.jsonl"
    litvar_edges.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {
                    "pmid": "39000002",
                    "source": "litvar2",
                    "entity_type": "gene",
                    "matched_text": "RPE65",
                    "evidence_text": "LitVar links RPE65 to c.260A>G.",
                },
                {
                    "pmid": "39000002",
                    "source": "litvar2",
                    "entity_type": "variant",
                    "identifier": "c.260A>G",
                    "matched_text": "c.260A>G",
                    "evidence_text": "LitVar links RPE65 to c.260A>G.",
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )
    settings = _settings(tmp_path, pubmed_local_enabled=True)

    result = materialize_pubmed_local_store(
        settings,
        jsonl_files=[jsonl_path],
        pubtator_edge_files=[pubtator_edges],
        litvar_edge_files=[litvar_edges],
        query_file=_seed_file(tmp_path),
        source_version="pubmed-local-test",
        force=True,
    )

    assert result.ready is True
    assert result.article_count == 2
    assert result.literature_edge_count == 4
    assert result.source_kind_counts == {
        "import_jsonl": 1,
        "litvar_edges": 1,
        "pubtator_edges": 1,
    }
    assert result.import_stats_by_source["pubtator_edges"]["literature_edge_imported_count"] == 2
    assert (
        result.import_stats_by_source["pubtator_edges"]["literature_edge_orphan_skipped_count"] == 1
    )
    assert result.import_stats_by_source["litvar_edges"]["literature_edge_imported_count"] == 2

    tool_result, needs_live = PubMedLocalStore(
        settings.pubmed_local_sqlite_path,
        manifest_path=settings.pubmed_local_manifest_path,
        enabled=True,
    ).search_tool_result(_variant(), limit=10)

    assert needs_live is False
    articles_by_pmid = {article["pmid"]: article for article in tool_result.summary["articles"]}
    assert set(articles_by_pmid) == {"39000001", "39000002"}
    assert articles_by_pmid["39000001"]["pubtator"] == ["The RPE65 c.260A>G variant was observed."]
    assert articles_by_pmid["39000002"]["litvar2_snippet"] == ["LitVar links RPE65 to c.260A>G."]

    literature = EamosProprietaryVariantLiteratureExtractor().build_for_lookup(
        _variant(),
        {"pubmed": tool_result.summary},
        source_statuses={"pubmed": "local"},
        limit=10,
    )
    pubtator_article = next(
        article for article in literature.articles if article.pmid == "39000001"
    )
    litvar_article = next(article for article in literature.articles if article.pmid == "39000002")
    assert pubtator_article.snippet_status == "exact_variant_snippet"
    assert pubtator_article.snippets[0].source == "pubtator"
    assert litvar_article.snippet_status == "exact_variant_snippet"
    assert litvar_article.snippets[0].source == "litvar2"


def test_pubmed_tool_uses_local_without_live_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path, pubmed_local_enabled=True, use_real_apis=True)
    materialize_pubmed_local_store(
        settings,
        xml_files=[PUBMED_XML],
        query_file=_seed_file(tmp_path),
        source_version="pubmed-local-test",
        force=True,
    )

    def fail_live(*args, **kwargs):
        raise AssertionError("live PubMed should not be called for local hit")

    monkeypatch.setattr(PubmedTool, "_fetch_live", fail_live)

    result = PubmedTool(settings).get_evidence(_variant())

    assert result.status == "local"
    assert result.summary["articles"][0]["pmid"] == "38191234"


def test_pubmed_tool_local_request_path_skips_logical_checksum(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path, pubmed_local_enabled=True, use_real_apis=True)
    materialize_pubmed_local_store(
        settings,
        xml_files=[PUBMED_XML],
        query_file=_seed_file(tmp_path),
        source_version="pubmed-local-test",
        force=True,
    )

    def fail_checksum(*_args, **_kwargs):
        raise AssertionError("request-path PubMed lookup must not logical-checksum the corpus")

    monkeypatch.setattr(pubmed_local_module, "_logical_checksum", fail_checksum)

    result = PubmedTool(settings).get_evidence(_variant())

    assert result.status == "local"
    assert result.summary["articles"][0]["pmid"] == "38191234"


def test_pubmed_tool_refresh_bypasses_local(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path, pubmed_local_enabled=True, use_real_apis=True)
    materialize_pubmed_local_store(
        settings,
        xml_files=[PUBMED_XML],
        query_file=_seed_file(tmp_path),
        source_version="pubmed-local-test",
        force=True,
    )

    def fake_live(self, variant):
        return ToolResult(
            source="pubmed",
            status="live",
            request_identity={"term": "live"},
            summary={"articles": [], "total": 0},
            raw={},
            source_url="https://pubmed.ncbi.nlm.nih.gov/?term=RPE65[gene]",
        )

    monkeypatch.setattr(PubmedTool, "_fetch_live", fake_live)

    result = PubmedTool(settings).get_evidence(_variant(), refresh=True)

    assert result.status == "live"
    assert result.request_identity == {"term": "live"}


def test_pubmed_tool_local_no_hit_can_fall_back_to_live(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path, pubmed_local_enabled=True, use_real_apis=True)
    materialize_pubmed_local_store(
        settings,
        xml_files=[PUBMED_XML],
        query_file=_seed_file(tmp_path),
        source_version="pubmed-local-test",
        force=True,
    )

    def fake_live(self, variant):
        return ToolResult(
            source="pubmed",
            status="live",
            request_identity={"term": "USH2A live"},
            summary={"articles": [], "total": 0},
            raw={},
            source_url="https://pubmed.ncbi.nlm.nih.gov/?term=USH2A[gene]",
        )

    monkeypatch.setattr(PubmedTool, "_fetch_live", fake_live)

    result = PubmedTool(settings).get_evidence(
        _variant(
            gene="USH2A",
            transcript_hgvs="c.2276G>T",
            protein_change="p.Cys759Phe",
            dbsnp_rsid="",
            genomic_hg38="",
        )
    )

    assert result.status == "live"
    assert "pubmed_local_no_hit_live_fallback" in result.warnings
    assert "pubmed_local_coverage_missing" in result.warnings


def test_pubmed_local_clis_emit_sanitized_json(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    db_path = tmp_path / "pubmed-local.sqlite"
    manifest_path = tmp_path / "pubmed-local.manifest.json"
    xml_path = tmp_path / "pubmed-local-sample.xml"
    xml_path.write_bytes(PUBMED_XML.read_bytes())
    xml_path.with_name(f"{xml_path.name}.md5").write_text(
        f"{md5(xml_path.read_bytes(), usedforsecurity=False).hexdigest()}  {xml_path.name}\n",
        encoding="utf-8",
    )
    exit_code = eamos_pubmed_local_materialize.main(
        [
            "--from-xml-file",
            str(xml_path),
            "--query-file",
            str(_seed_file(tmp_path)),
            "--output",
            str(db_path),
            "--manifest",
            str(manifest_path),
            "--source-version",
            "pubmed-local-test",
            "--domain-filter",
            "biomedical",
            "--xml-source-kind",
            "update",
            "--verify-md5-sidecars",
            "--compact",
            "--require-ready",
        ]
    )
    assert exit_code == 0
    materialize_output = json.loads(capsys.readouterr().out)
    assert materialize_output["guardrails"]["startup_download"] == "not_used"
    assert materialize_output["guardrails"]["abstract_text_in_output"] == "blocked"
    assert materialize_output["materialization"]["input_checksum_status"] == "verified"
    assert materialize_output["materialization"]["literature_edge_count"] == 0
    assert materialize_output["materialization"]["source_file_count"] == 1
    assert materialize_output["materialization"]["source_kind_counts"] == {"pubmed_update": 1}
    assert (
        materialize_output["materialization"]["import_stats_by_source"]["pubmed_update"][
            "records_seen_count"
        ]
        == 3
    )
    encoded = json.dumps(materialize_output).lower()
    assert str(tmp_path).lower() not in encoded
    assert "asp87gly variant was observed" not in encoded

    exit_code = eamos_pubmed_local_preflight.main(
        [
            "--db-path",
            str(db_path),
            "--manifest-path",
            str(manifest_path),
            "--compact",
            "--require-ready",
        ]
    )
    assert exit_code == 0
    preflight_output = json.loads(capsys.readouterr().out)
    assert preflight_output["ready"] is True
    assert preflight_output["literature_edge_count"] == 0
    assert preflight_output["source_kind_counts"] == {"pubmed_update": 1}
    assert (
        preflight_output["import_stats_by_source"]["pubmed_update"]["article_imported_count"] == 2
    )
    assert preflight_output["local_path_values_emitted"] is False
    assert preflight_output["abstract_values_emitted"] is False
    encoded = json.dumps(preflight_output).lower()
    assert str(tmp_path).lower() not in encoded
    assert "api_key" not in encoded
