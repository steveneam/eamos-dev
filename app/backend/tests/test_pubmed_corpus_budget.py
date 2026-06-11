from __future__ import annotations

import json
from pathlib import Path

from app.cli import eamos_pubmed_corpus_budget


def _listing_html(rows: list[tuple[str, str]]) -> str:
    body = "\n".join(f'<a href="{name}">{name}</a> 2026-01-01 00:00 {size}' for name, size in rows)
    return f"<html><body><pre>{body}</pre></body></html>"


def _write_offline_listings(listing_dir: Path) -> None:
    listing_dir.mkdir()
    fixtures = {
        "pubmed_baseline": [
            ("pubmed26n0001.xml.gz", "1G"),
            ("pubmed26n0002.xml.gz", "512M"),
            ("pubmed26n0002.xml.gz.md5", "1K"),
        ],
        "pubmed_updatefiles": [
            ("pubmed26n1275.xml.gz", "128M"),
            ("pubmed26n1275_stats.html", "1K"),
        ],
        "pubtator3": [
            ("bioconcepts2pubtator3.gz", "5G"),
            ("gene2pubtator3.gz", "700M"),
            ("mutation2pubtator3.gz", "100M"),
            ("relation2pubtator3.gz", "200M"),
            ("BioCXML.0.tar.gz", "20G"),
            ("BioCXML.1.tar.gz", "20G"),
            ("disease2pubtator3.gz", "100M"),
        ],
        "pmc_top": [
            ("PMC-ids.csv.gz", "236M"),
            ("oa_file_list.csv", "12M"),
        ],
        "pmc_oa_comm_xml": [
            ("oa_comm_xml.baseline.2026-01-01.tar.gz", "10G"),
            ("oa_comm_xml.incr.2026-01-08.tar.gz", "1G"),
        ],
        "pmc_oa_noncomm_xml": [
            ("oa_noncomm_xml.baseline.2026-01-01.tar.gz", "20G"),
        ],
        "pmc_oa_other_xml": [
            ("oa_other_xml.baseline.2026-01-01.tar.gz", "5G"),
        ],
        "pmc_oa_comm_txt": [
            ("oa_comm_txt.baseline.2026-01-01.tar.gz", "2G"),
        ],
        "pmc_oa_noncomm_txt": [
            ("oa_noncomm_txt.baseline.2026-01-01.tar.gz", "3G"),
        ],
        "pmc_oa_other_txt": [
            ("oa_other_txt.baseline.2026-01-01.tar.gz", "1G"),
        ],
    }
    for key, rows in fixtures.items():
        (listing_dir / f"{key}.html").write_text(_listing_html(rows), encoding="utf-8")


def test_corpus_budget_uses_offline_listings_and_emits_sanitized_hold_report(
    tmp_path: Path,
    capsys,
) -> None:
    listing_dir = tmp_path / "official-listings"
    _write_offline_listings(listing_dir)

    exit_code = eamos_pubmed_corpus_budget.main(
        [
            "--listing-dir",
            str(listing_dir),
            "--storage-used-gib",
            "38",
            "--storage-quota-gib",
            "40",
            "--database-used-gib",
            "0.1",
            "--database-quota-gib",
            "8",
            "--compact",
        ]
    )

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["mode"] == "pubmed_corpus_budget"
    assert report["status"] == "budgeted"
    assert report["ready_for_upload"] is False
    assert report["approval_required_before_upload"] is True
    assert report["guardrails"]["network"]["used"] is False
    assert report["guardrails"]["source_payload_download"] == "not_used"
    assert report["guardrails"]["supabase_storage_mutation"] == "not_used"
    assert report["guardrails"]["supabase_database_mutation"] == "not_used"
    assert report["guardrails"]["startup_download"] == "not_used"
    assert report["inventory"]["pubtator_selectors"]["file_count"] == 4
    assert report["inventory"]["pubtator_bioc"]["compressed_gib"] == 40.0
    assert report["inventory"]["pmc_oa_xml"]["file_count"] == 3
    assert report["source_listing_summary"]["pmc_oa_comm_xml"]["entry_count"] == 2
    assert report["warnings"] == []

    scenarios = {scenario["id"]: scenario for scenario in report["scenarios"]}
    assert scenarios["pubmed_raw_mirror"]["approval_required"] is True
    assert scenarios["pubmed_raw_mirror"]["risk"]["storage"] == "yellow"
    assert scenarios["pubmed_raw_mirror"]["version_overlap_storage_after_gib"] > 40
    assert scenarios["full_pmc_pubtator_raw_mirrors"]["approval_required"] is True
    assert scenarios["full_pmc_pubtator_raw_mirrors"]["risk"]["storage"] == "red"
    assert scenarios["full_pmc_pubtator_raw_mirrors"]["storage_overage_gib"] > 0

    encoded_report = json.dumps(report).lower()
    assert str(tmp_path).lower() not in encoded_report
    assert "official-listings" not in encoded_report


def test_corpus_budget_requires_an_explicit_listing_source(capsys) -> None:
    exit_code = eamos_pubmed_corpus_budget.main(["--compact"])

    assert exit_code == 2
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "failed"
    assert report["code"] == "listing_source_required"
    assert report["ready_for_upload"] is False
    assert report["approval_required_before_upload"] is True
    assert report["guardrails"]["network"]["used"] is False
    assert report["guardrails"]["source_payload_download"] == "not_used"


def test_parse_apache_listing_handles_binary_units_and_skips_readme() -> None:
    entries = eamos_pubmed_corpus_budget.parse_apache_listing(
        _listing_html(
            [
                ("README.txt", "1K"),
                ("pubmed26n0001.xml.gz", "1.5G"),
                ("PMC-ids.csv.gz", "236M"),
            ]
        )
    )

    assert [entry.name for entry in entries] == ["pubmed26n0001.xml.gz", "PMC-ids.csv.gz"]
    assert entries[0].size_bytes == int(1.5 * 1024**3)
    assert entries[1].size_bytes == 236 * 1024**2
