from __future__ import annotations

from hashlib import md5
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.cli import (
    eamos_pubmed_litvar_edges,
    eamos_pubmed_local_materialize,
    eamos_pubmed_local_preflight,
    eamos_pubmed_pubtator_edges,
    eamos_pubmed_seed_manifest,
)
from app.services.pubmed_local import PubMedLocalStore, read_seed_queries
from app.services.pubmed_seed_manifest import (
    PubMedSeedManifestError,
    load_seed_manifest,
    parse_seed_manifest,
)
from app.services.publication_literature import EamosProprietaryVariantLiteratureExtractor

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "app" / "fixtures"
MANIFEST_PATH = FIXTURE_ROOT / "literature" / "pmat_seed_manifest_tiny.json"
PUBMED_XML = FIXTURE_ROOT / "tools" / "pubmed_local_sample.xml"


def test_tiny_seed_manifest_validates_and_renders_pubmed_query_tsv(tmp_path: Path) -> None:
    manifest = load_seed_manifest(MANIFEST_PATH)

    assert manifest.corpus_label == "targeted_seed"
    assert manifest.source_scope == "tiny_fixture"
    assert manifest.seed_count == 4
    assert manifest.genes == ("ABCA4", "CEP290", "RPE65")
    assert manifest.corpus_labels == ("targeted_seed",)

    query_file = tmp_path / "pubmed-seed.tsv"
    manifest.write_pubmed_query_tsv(query_file)
    seeds = read_seed_queries(query_file)

    assert [(seed.gene, seed.scope) for seed in seeds] == [
        ("RPE65", "variant"),
        ("RPE65", "gene"),
        ("ABCA4", "variant"),
        ("CEP290", "variant"),
    ]
    assert seeds[0].variant_terms == (
        "c.260A>G",
        "NM_000329.3:c.260A>G",
        "p.Asp87Gly",
        "rs1645931040",
        "1-68444869-T-C",
    )
    assert seeds[1].variant_terms == ()
    assert "c.5461-10T>C" in seeds[2].variant_terms


def test_tiny_seed_manifest_sanitized_report_has_no_rows_paths_or_sensitive_fields() -> None:
    manifest = load_seed_manifest(MANIFEST_PATH)

    report = manifest.to_sanitized_dict()
    encoded = json.dumps(report).lower()

    assert report["guardrails"]["network"]["used"] is False
    assert report["guardrails"]["materialization"] == "not_used"
    assert report["seed_count"] == 4
    assert "seed_id" not in encoded
    assert "c.260a>g" not in encoded
    assert "d:\\" not in encoded
    assert "/var/data/" not in encoded
    assert "api_key" not in encoded
    assert "request_headers" not in encoded
    assert "patient_note" not in encoded


def test_seed_manifest_cli_writes_query_file_without_leaking_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    query_file = tmp_path / "pubmed-seed.tsv"

    exit_code = eamos_pubmed_seed_manifest.main(
        [
            "--manifest-path",
            str(MANIFEST_PATH),
            "--write-query-file",
            str(query_file),
            "--compact",
            "--require-ready",
        ]
    )

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "ready"
    assert report["pubmed_query_file_name"] == "pubmed-seed.tsv"
    assert report["validation"]["seed_count"] == 4
    encoded = json.dumps(report).lower()
    assert str(tmp_path).lower() not in encoded
    assert str(MANIFEST_PATH.parent).lower() not in encoded
    assert len(read_seed_queries(query_file)) == 4


def test_seed_manifest_drives_pubmed_local_fixture_materialization_and_preflight(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    query_file = tmp_path / "pmat-seed.tsv"
    seed_exit = eamos_pubmed_seed_manifest.main(
        [
            "--manifest-path",
            str(MANIFEST_PATH),
            "--write-query-file",
            str(query_file),
            "--compact",
            "--require-ready",
        ]
    )
    assert seed_exit == 0
    capsys.readouterr()

    xml_path = tmp_path / "pubmed25n0001.xml"
    xml_path.write_bytes(PUBMED_XML.read_bytes())
    xml_path.with_name(f"{xml_path.name}.md5").write_text(
        f"{md5(xml_path.read_bytes(), usedforsecurity=False).hexdigest()}  {xml_path.name}\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "pubmed-local.sqlite"
    materialization_manifest = tmp_path / "pubmed-local.manifest.json"

    materialize_exit = eamos_pubmed_local_materialize.main(
        [
            "--from-xml-file",
            str(xml_path),
            "--query-file",
            str(query_file),
            "--output",
            str(db_path),
            "--manifest",
            str(materialization_manifest),
            "--source-version",
            "pmat-tiny-fixture-2026-06-27",
            "--xml-source-kind",
            "baseline",
            "--verify-md5-sidecars",
            "--compact",
            "--require-ready",
        ]
    )

    assert materialize_exit == 0
    materialize_report = json.loads(capsys.readouterr().out)
    materialization = materialize_report["materialization"]
    assert materialize_report["guardrails"]["network"] == {"provider": None, "used": False}
    assert materialize_report["guardrails"]["startup_download"] == "not_used"
    assert materialize_report["guardrails"]["request_time_materialization"] == "not_used"
    assert materialization["ready"] is True
    assert materialization["status"] == "ready"
    assert materialization["article_count"] == 2
    assert materialization["licensed_abstract_count"] == 1
    assert materialization["metadata_only_count"] == 1
    assert materialization["deleted_count"] == 1
    assert materialization["coverage_count"] == 6
    assert materialization["source_file_count"] == 1
    assert materialization["source_kind_counts"] == {"pubmed_baseline": 1}
    assert materialization["input_checksum_status"] == "verified"
    assert materialization["input_checksum_verified_count"] == 1

    preflight_exit = eamos_pubmed_local_preflight.main(
        [
            "--db-path",
            str(db_path),
            "--manifest-path",
            str(materialization_manifest),
            "--compact",
            "--require-ready",
        ]
    )

    assert preflight_exit == 0
    preflight_report = json.loads(capsys.readouterr().out)
    assert preflight_report["ready"] is True
    assert preflight_report["status"] == "ready"
    assert preflight_report["checksum_verified"] is True
    assert preflight_report["article_count"] == 2
    assert preflight_report["licensed_abstract_count"] == 1
    assert preflight_report["metadata_only_count"] == 1
    assert preflight_report["coverage"]["queries"] == 6
    assert preflight_report["local_path_values_emitted"] is False
    assert preflight_report["abstract_values_emitted"] is False
    assert preflight_report["secret_values_emitted"] is False
    encoded = json.dumps(preflight_report).lower()
    assert str(tmp_path).lower() not in encoded
    assert "asp87gly variant was observed" not in encoded


def test_seed_manifest_drives_litvar_pubtator_edge_fixture_gate(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    query_file = tmp_path / "pmat-seed.tsv"
    seed_exit = eamos_pubmed_seed_manifest.main(
        [
            "--manifest-path",
            str(MANIFEST_PATH),
            "--write-query-file",
            str(query_file),
            "--compact",
            "--require-ready",
        ]
    )
    assert seed_exit == 0
    capsys.readouterr()

    pubtator_path = tmp_path / "pmat-pubtator.pubtator"
    pubtator_snippet = _write_pmat_pubtator_fixture(pubtator_path)
    pubtator_edges = tmp_path / "pmat-pubtator-edges.jsonl"
    pubtator_exit = eamos_pubmed_pubtator_edges.main(
        [
            "--from-pubtator-file",
            str(pubtator_path),
            "--output",
            str(pubtator_edges),
            "--compact",
            "--require-edges",
        ]
    )
    assert pubtator_exit == 0
    pubtator_report = json.loads(capsys.readouterr().out)
    assert pubtator_report["guardrails"]["network"] == {"provider": None, "used": False}
    assert pubtator_report["conversion"]["edge_count"] == 4
    assert pubtator_report["conversion"]["entity_type_counts"] == {"gene": 2, "variant": 2}

    litvar_path = tmp_path / "pmat-litvar.json"
    _write_pmat_litvar_fixture(litvar_path)
    litvar_edges = tmp_path / "pmat-litvar-edges.jsonl"
    litvar_exit = eamos_pubmed_litvar_edges.main(
        [
            "--from-litvar-json-file",
            str(litvar_path),
            "--query-file",
            str(query_file),
            "--output",
            str(litvar_edges),
            "--compact",
            "--require-edges",
        ]
    )
    assert litvar_exit == 0
    litvar_report = json.loads(capsys.readouterr().out)
    assert litvar_report["guardrails"]["network"] == {"provider": None, "used": False}
    assert litvar_report["conversion"]["record_count"] == 1
    assert litvar_report["conversion"]["pmid_count"] == 2
    assert litvar_report["conversion"]["edge_count"] == 12
    assert litvar_report["conversion"]["entity_type_counts"] == {
        "gene": 2,
        "rsid": 2,
        "variant": 8,
    }

    xml_path = tmp_path / "pubmed25n0001.xml"
    xml_path.write_bytes(PUBMED_XML.read_bytes())
    xml_path.with_name(f"{xml_path.name}.md5").write_text(
        f"{md5(xml_path.read_bytes(), usedforsecurity=False).hexdigest()}  {xml_path.name}\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "pubmed-local.sqlite"
    materialization_manifest = tmp_path / "pubmed-local.manifest.json"

    materialize_exit = eamos_pubmed_local_materialize.main(
        [
            "--from-xml-file",
            str(xml_path),
            "--from-pubtator-edge-jsonl-file",
            str(pubtator_edges),
            "--from-litvar-edge-jsonl-file",
            str(litvar_edges),
            "--query-file",
            str(query_file),
            "--output",
            str(db_path),
            "--manifest",
            str(materialization_manifest),
            "--source-version",
            "pmat-tiny-edge-fixture-2026-06-27",
            "--xml-source-kind",
            "baseline",
            "--verify-md5-sidecars",
            "--compact",
            "--require-ready",
        ]
    )
    assert materialize_exit == 0
    materialize_report = json.loads(capsys.readouterr().out)
    materialization = materialize_report["materialization"]
    assert materialize_report["guardrails"]["network"] == {"provider": None, "used": False}
    assert materialization["ready"] is True
    assert materialization["article_count"] == 2
    assert materialization["literature_edge_count"] == 8
    assert materialization["source_file_count"] == 3
    assert materialization["source_kind_counts"] == {
        "litvar_edges": 1,
        "pubmed_baseline": 1,
        "pubtator_edges": 1,
    }
    assert materialization["input_checksum_status"] == "verified"
    assert (
        materialization["import_stats_by_source"]["pubtator_edges"][
            "literature_edge_imported_count"
        ]
        == 2
    )
    assert (
        materialization["import_stats_by_source"]["pubtator_edges"][
            "literature_edge_orphan_skipped_count"
        ]
        == 2
    )
    assert (
        materialization["import_stats_by_source"]["litvar_edges"]["literature_edge_imported_count"]
        == 6
    )
    assert (
        materialization["import_stats_by_source"]["litvar_edges"][
            "literature_edge_orphan_skipped_count"
        ]
        == 6
    )

    preflight_exit = eamos_pubmed_local_preflight.main(
        [
            "--db-path",
            str(db_path),
            "--manifest-path",
            str(materialization_manifest),
            "--compact",
            "--require-ready",
        ]
    )
    assert preflight_exit == 0
    preflight_report = json.loads(capsys.readouterr().out)
    assert preflight_report["ready"] is True
    assert preflight_report["network_used"] is False
    assert preflight_report["literature_edge_count"] == 8
    assert (
        preflight_report["import_stats_by_source"]["pubtator_edges"][
            "literature_edge_orphan_skipped_count"
        ]
        == 2
    )
    assert (
        preflight_report["import_stats_by_source"]["litvar_edges"][
            "literature_edge_orphan_skipped_count"
        ]
        == 6
    )
    assert preflight_report["local_path_values_emitted"] is False
    assert preflight_report["abstract_values_emitted"] is False
    encoded_preflight = json.dumps(preflight_report).lower()
    assert str(tmp_path).lower() not in encoded_preflight
    assert "linked by pubtator" not in encoded_preflight

    tool_result, needs_live = PubMedLocalStore(
        db_path,
        manifest_path=materialization_manifest,
        enabled=True,
    ).search_tool_result(_pmat_variant(), limit=10)

    assert needs_live is False
    assert tool_result.status == "local"
    articles_by_pmid = {article["pmid"]: article for article in tool_result.summary["articles"]}
    assert pubtator_snippet in articles_by_pmid["37042101"]["pubtator"]
    assert articles_by_pmid["37042101"]["litvar2_snippet"] == [
        "LitVar2 reported PMID 37042101 for RPE65 AND c.260A>G AND "
        "NM_000329.3:c.260A>G AND p.Asp87Gly AND rs1645931040 AND 1-68444869-T-C."
    ]

    literature = EamosProprietaryVariantLiteratureExtractor().build_for_lookup(
        _pmat_variant(),
        {"pubmed": tool_result.summary},
        source_statuses={"pubmed": "local"},
        limit=10,
    )
    edge_article = next(article for article in literature.articles if article.pmid == "37042101")
    assert edge_article.snippet_status == "exact_variant_snippet"
    assert edge_article.snippets[0].source == "pubtator"
    assert "c.260A>G" in edge_article.snippets[0].text


def test_seed_manifest_rejects_variant_without_pubmed_alias() -> None:
    payload = _valid_payload()
    payload["seeds"][0]["variant_aliases"] = {}

    with pytest.raises(PubMedSeedManifestError) as exc:
        parse_seed_manifest(payload)

    assert "variant scope needs a PubMed-compatible variant alias" in str(exc.value)


def test_seed_manifest_rejects_user_patient_or_request_payload_fields() -> None:
    payload = _valid_payload()
    payload["seeds"][0]["patient_note"] = "Do not allow clinical free text here."
    payload["seeds"][1]["clinical_trials"]["request_headers"] = {"Authorization": "Bearer test"}

    with pytest.raises(PubMedSeedManifestError) as exc:
        parse_seed_manifest(payload)

    message = str(exc.value)
    assert "patient_note is not allowed" in message
    assert "request_headers is not allowed" in message


def _valid_payload() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _pmat_variant() -> SimpleNamespace:
    return SimpleNamespace(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.260A>G",
        protein_change="p.Asp87Gly",
        dbsnp_rsid="rs1645931040",
        genomic_hg38="1-68444869-T-C",
    )


def _write_pmat_pubtator_fixture(path: Path) -> str:
    imported_title = "Long-term outcomes of RPE65 gene therapy"
    imported_abstract = "The RPE65 c.260A>G variant was linked by PubTator."
    orphan_title = "Unimported RPE65 edge"
    orphan_abstract = "The RPE65 c.260A>G orphan mention should be skipped."
    path.write_text(
        "\n".join(
            [
                *_pubtator_document_lines("37042101", imported_title, imported_abstract),
                "",
                *_pubtator_document_lines("39900000", orphan_title, orphan_abstract),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return imported_abstract


def _pubtator_document_lines(pmid: str, title: str, abstract: str) -> list[str]:
    text = f"{title} {abstract}"
    gene_start = text.index("RPE65")
    variant_start = text.index("c.260A>G")
    return [
        f"{pmid}|t|{title}",
        f"{pmid}|a|{abstract}",
        f"{pmid}\t{gene_start}\t{gene_start + len('RPE65')}\tRPE65\tGene\t6121",
        (
            f"{pmid}\t{variant_start}\t{variant_start + len('c.260A>G')}\tc.260A>G"
            "\tMutation\tc|SUB|A|260|G"
        ),
    ]


def _write_pmat_litvar_fixture(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "request_identity": {
                    "query": "RPE65 c.260A>G",
                    "litvar_id": "litvar-rpe65-c260ag-pmat",
                },
                "seed": {
                    "gene": "RPE65",
                    "scope": "variant",
                    "cdna": "c.260A>G",
                    "transcript": "NM_000329.3:c.260A>G",
                    "protein_change": "p.Asp87Gly",
                    "rsid": "rs1645931040",
                    "genomic_hg38": "1-68444869-T-C",
                },
                "summary": {
                    "litvar_id": "litvar-rpe65-c260ag-pmat",
                    "total_publications": 2,
                    "articles": [
                        {"pmid": "37042101", "title": "RPE65 gene therapy edge"},
                        {"pmid": "39900001", "title": "RPE65 orphan edge"},
                    ],
                },
                "raw": {"pmids": ["37042101", "39900001"]},
            }
        ),
        encoding="utf-8",
    )
