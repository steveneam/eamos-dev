from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from app.cli import eamos_pubmed_pubtator_edges
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


def _write_pubtator_fixture(path: Path) -> str:
    title = "Retinal disease cohort study"
    abstract = "The RPE65 c.260A>G variant was observed in inherited retinal disease."
    text = f"{title} {abstract}"
    gene_start = text.index("RPE65")
    variant_start = text.index("c.260A>G")
    gene_end = gene_start + len("RPE65")
    variant_end = variant_start + len("c.260A>G")
    path.write_text(
        "\n".join(
            [
                f"39000001|t|{title}",
                f"39000001|a|{abstract}",
                f"39000001\t{gene_start}\t{gene_end}\tRPE65\tGene\t6121",
                (f"39000001\t{variant_start}\t{variant_end}\tc.260A>G" "\tMutation\tc|SUB|A|260|G"),
                "not a valid pubtator line",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return abstract


def test_pubtator_converter_outputs_edge_jsonl_and_sanitized_report(
    tmp_path: Path,
    capsys,
) -> None:
    pubtator_path = tmp_path / "rpe65.pubtator"
    expected_snippet = _write_pubtator_fixture(pubtator_path)
    output_path = tmp_path / "rpe65-pubtator-edges.jsonl"

    exit_code = eamos_pubmed_pubtator_edges.main(
        [
            "--from-pubtator-file",
            str(pubtator_path),
            "--output",
            str(output_path),
            "--compact",
            "--require-edges",
        ]
    )

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "converted"
    assert report["conversion"]["edge_count"] == 2
    assert report["conversion"]["entity_type_counts"] == {"gene": 1, "variant": 1}
    assert report["guardrails"]["network"]["used"] is False
    assert report["output_file_name"] == "rpe65-pubtator-edges.jsonl"
    encoded_report = json.dumps(report).lower()
    assert str(tmp_path).lower() not in encoded_report
    assert expected_snippet.lower() not in encoded_report

    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows[0]["source"] == "pubtator"
    assert rows[0]["entity_type"] == "gene"
    assert rows[0]["section"] == "abstract"
    assert rows[1]["entity_type"] == "variant"
    assert rows[1]["offset_start"] > rows[0]["offset_start"]
    assert expected_snippet in rows[1]["evidence_text"]


def test_pubtator_converter_edges_feed_pubmed_local_materializer(
    tmp_path: Path,
) -> None:
    pubmed_jsonl = tmp_path / "neutral-pubmed.jsonl"
    pubmed_jsonl.write_text(
        json.dumps(
            {
                "pmid": "39000001",
                "title": "Retinal disease cohort study",
                "abstract": "A hereditary eye disease cohort was evaluated.",
                "journal": "Example Ophthalmology",
                "year": "2025",
                "language": "eng",
                "publication_types": ["Journal Article"],
                "license_profile": "cc-by",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    pubtator_path = tmp_path / "rpe65.pubtator"
    expected_snippet = _write_pubtator_fixture(pubtator_path)
    edge_path = tmp_path / "rpe65-pubtator-edges.jsonl"
    stats = eamos_pubmed_pubtator_edges.convert_pubtator_files_to_edge_jsonl(
        [pubtator_path],
        edge_path,
    )
    settings = _settings(tmp_path)

    result = materialize_pubmed_local_store(
        settings,
        jsonl_files=[pubmed_jsonl],
        pubtator_edge_files=[edge_path],
        query_file=_seed_file(tmp_path),
        source_version="pubmed-local-test",
        force=True,
    )

    assert stats.edge_count == 2
    assert result.ready is True
    assert result.article_count == 1
    assert result.literature_edge_count == 2
    assert result.import_stats_by_source["pubtator_edges"]["literature_edge_imported_count"] == 2

    tool_result, needs_live = PubMedLocalStore(
        settings.pubmed_local_sqlite_path,
        manifest_path=settings.pubmed_local_manifest_path,
        enabled=True,
    ).search_tool_result(_variant(), limit=10)

    assert needs_live is False
    assert tool_result.status == "local"
    assert tool_result.summary["articles"][0]["pmid"] == "39000001"
    assert tool_result.summary["articles"][0]["pubtator"] == [expected_snippet]
