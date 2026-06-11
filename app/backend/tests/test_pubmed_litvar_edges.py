from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from app.cli import eamos_pubmed_litvar_edges
from app.core.config import Settings
from app.services.pubmed_local import PubMedLocalStore, materialize_pubmed_local_store


def _settings(tmp_path: Path, **overrides) -> Settings:
    return Settings(
        jwt_secret="test-secret",
        pubmed_local_enabled=True,
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
            ]
        ),
        encoding="utf-8",
    )
    return path


def _variant() -> SimpleNamespace:
    return SimpleNamespace(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.260A>G",
        protein_change="p.Asp87Gly",
        dbsnp_rsid="rs1645931040",
        genomic_hg38="1-68444869-T-C",
    )


def _write_litvar_fixture(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "request_identity": {
                    "query": "RPE65 c.260A>G",
                    "litvar_id": "litvar-rpe65-c260ag",
                },
                "summary": {
                    "litvar_id": "litvar-rpe65-c260ag",
                    "total_publications": 2,
                    "articles": [
                        {"pmid": "39000011", "title": "RPE65 c.260A>G cohort"},
                        {"pmid": "39000012", "title": "RPE65 Asp87Gly function"},
                    ],
                },
                "raw": {"pmids": ["39000011", "39000012"]},
            }
        ),
        encoding="utf-8",
    )


def test_litvar_converter_outputs_edge_jsonl_and_sanitized_report(
    tmp_path: Path,
    capsys,
) -> None:
    litvar_path = tmp_path / "rpe65-litvar.json"
    _write_litvar_fixture(litvar_path)
    output_path = tmp_path / "rpe65-litvar-edges.jsonl"

    exit_code = eamos_pubmed_litvar_edges.main(
        [
            "--from-litvar-json-file",
            str(litvar_path),
            "--query-file",
            str(_seed_file(tmp_path)),
            "--output",
            str(output_path),
            "--compact",
            "--require-edges",
        ]
    )

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "converted"
    assert report["conversion"]["record_count"] == 1
    assert report["conversion"]["pmid_count"] == 2
    assert report["conversion"]["edge_count"] == 12
    assert report["conversion"]["entity_type_counts"] == {"gene": 2, "rsid": 2, "variant": 8}
    assert report["guardrails"]["network"]["used"] is False
    assert report["output_file_name"] == "rpe65-litvar-edges.jsonl"
    encoded_report = json.dumps(report).lower()
    assert str(tmp_path).lower() not in encoded_report
    assert "39000011" not in encoded_report
    assert "rpe65 c.260a>g" not in encoded_report

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert {row["pmid"] for row in rows} == {"39000011", "39000012"}
    assert {row["source"] for row in rows} == {"litvar2"}
    assert any(row["entity_type"] == "gene" and row["identifier"] == "RPE65" for row in rows)
    assert any(row["entity_type"] == "variant" and row["identifier"] == "c.260A>G" for row in rows)
    assert all(row["relation_type"] == "litvar_publication_for_variant" for row in rows)


def test_litvar_converter_edges_feed_pubmed_local_materializer(
    tmp_path: Path,
) -> None:
    pubmed_jsonl = tmp_path / "neutral-pubmed.jsonl"
    pubmed_jsonl.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {
                    "pmid": "39000011",
                    "title": "RPE65-associated retinal disease cohort",
                    "abstract": "A hereditary eye disease cohort was evaluated.",
                    "journal": "Example Ophthalmology",
                    "year": "2025",
                    "language": "eng",
                    "publication_types": ["Journal Article"],
                    "license_profile": "cc-by",
                },
                {
                    "pmid": "39000012",
                    "title": "RPE65 protein function case series",
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
    litvar_path = tmp_path / "rpe65-litvar.json"
    _write_litvar_fixture(litvar_path)
    edge_path = tmp_path / "rpe65-litvar-edges.jsonl"
    stats = eamos_pubmed_litvar_edges.convert_litvar_exports_to_edge_jsonl(
        [litvar_path],
        edge_path,
        seeds=[next(iter(eamos_pubmed_litvar_edges.read_seed_queries(_seed_file(tmp_path))))],
    )
    settings = _settings(tmp_path)

    result = materialize_pubmed_local_store(
        settings,
        jsonl_files=[pubmed_jsonl],
        litvar_edge_files=[edge_path],
        query_file=_seed_file(tmp_path),
        source_version="pubmed-local-test",
        force=True,
    )

    assert stats.edge_count == 12
    assert result.ready is True
    assert result.article_count == 2
    assert result.literature_edge_count == 12
    assert result.import_stats_by_source["litvar_edges"]["literature_edge_imported_count"] == 12

    tool_result, needs_live = PubMedLocalStore(
        settings.pubmed_local_sqlite_path,
        manifest_path=settings.pubmed_local_manifest_path,
        enabled=True,
    ).search_tool_result(_variant(), limit=10)

    assert needs_live is False
    assert tool_result.status == "local"
    articles_by_pmid = {article["pmid"]: article for article in tool_result.summary["articles"]}
    assert set(articles_by_pmid) == {"39000011", "39000012"}
    assert articles_by_pmid["39000011"]["litvar2_snippet"] == [
        "LitVar2 reported PMID 39000011 for RPE65 AND c.260A>G AND "
        "NM_000329.3:c.260A>G AND p.Asp87Gly AND rs1645931040 AND 1-68444869-T-C."
    ]
