from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import httpx

from app.core.config import Settings
from app.tools.gnomad import GnomadTool


class _FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "data": {
                "variant": {
                    "variantId": "1-55039974-G-T",
                    "joint": {
                        "ac": 23500,
                        "an": 1580590,
                        "homozygote_count": 226,
                        "populations": [
                            {
                                "id": "XX",
                                "ac": 12400,
                                "an": 790000,
                                "homozygote_count": 118,
                            },
                            {
                                "id": "XY",
                                "ac": 11100,
                                "an": 790590,
                                "homozygote_count": 108,
                            },
                            {
                                "id": "remaining",
                                "ac": 813,
                                "an": 61242,
                                "homozygote_count": 12,
                            },
                            {
                                "id": "amr",
                                "ac": 406,
                                "an": 55508,
                                "homozygote_count": 3,
                            },
                            {
                                "id": "fin",
                                "ac": 2394,
                                "an": 61024,
                                "homozygote_count": 48,
                            },
                            {
                                "id": "ami",
                                "ac": 6,
                                "an": 912,
                                "homozygote_count": 0,
                            },
                            {
                                "id": "eas",
                                "ac": 0,
                                "an": 43066,
                                "homozygote_count": 0,
                            },
                            {
                                "id": "mid",
                                "ac": 26,
                                "an": 5138,
                                "homozygote_count": 1,
                            },
                            {
                                "id": "sas",
                                "ac": 92,
                                "an": 86168,
                                "homozygote_count": 1,
                            },
                            {
                                "id": "asj",
                                "ac": 147,
                                "an": 28948,
                                "homozygote_count": 0,
                            },
                            {
                                "id": "afr",
                                "ac": 184,
                                "an": 74402,
                                "homozygote_count": 2,
                            },
                            {
                                "id": "nfe",
                                "ac": 19432,
                                "an": 1164182,
                                "homozygote_count": 159,
                            },
                            {
                                "id": "nfe_XX",
                                "ac": 10282,
                                "an": 605804,
                                "homozygote_count": 75,
                            },
                            {
                                "id": "nfe_XY",
                                "ac": 9150,
                                "an": 558378,
                                "homozygote_count": 84,
                            },
                            {
                                "id": "1kg:gbr",
                                "ac": 4,
                                "an": 174,
                                "homozygote_count": 0,
                            },
                        ],
                        "age_distribution": None,
                        "faf95": {"popmax": 0.01649444, "popmax_population": "nfe"},
                    },
                    "exome": {
                        "ac": 21634,
                        "an": 1428186,
                        "homozygote_count": 209,
                        "af": 0.015147886899885589,
                        "populations": [
                            {
                                "id": "nfe",
                                "ac": 18000,
                                "an": 1050000,
                                "homozygote_count": 150,
                            },
                        ],
                        "age_distribution": {
                            "het": {
                                "bin_edges": [30, 35, 40],
                                "bin_freq": [58, 79],
                                "n_smaller": 132,
                                "n_larger": 55,
                            },
                            "hom": {
                                "bin_edges": [30, 35, 40],
                                "bin_freq": [0, 0],
                                "n_smaller": 0,
                                "n_larger": 0,
                            },
                        },
                        "faf95": {"popmax": 0.01542945, "popmax_population": "nfe"},
                    },
                    "genome": {
                        "ac": 1866,
                        "an": 152404,
                        "homozygote_count": 3,
                        "af": 0.012243772,
                        "populations": [
                            {
                                "id": "nfe",
                                "ac": 1432,
                                "an": 114182,
                                "homozygote_count": 9,
                            },
                        ],
                        "age_distribution": {
                            "het": {
                                "bin_edges": [30, 35, 40],
                                "bin_freq": [8, 7],
                                "n_smaller": 3,
                                "n_larger": 2,
                            },
                            "hom": {
                                "bin_edges": [30, 35, 40],
                                "bin_freq": [0, 0],
                                "n_smaller": 0,
                                "n_larger": 0,
                            },
                        },
                        "faf95": {"popmax": 0.01484423, "popmax_population": "nfe"},
                    },
                    "flags": [],
                }
            }
        }


class _NoHitResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"data": {"variant": None}}


def test_gnomad_live_summary_keeps_ancestry_and_age_distribution(monkeypatch, tmp_path: Path):
    def fake_post(*args, **kwargs):
        return _FakeResponse()

    monkeypatch.setattr("app.tools.gnomad.httpx.post", fake_post)
    settings = Settings(
        jwt_secret="test-secret",
        use_real_apis=True,
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
    )
    tool = GnomadTool(settings)
    variant = SimpleNamespace(
        gene="PCSK9",
        transcript_hgvs="NM_174936.4:c.137G>T",
        genomic_hg38="1-55039974-G-T",
    )

    result = tool.get_evidence(variant=variant)

    assert result.status == "live"
    assert result.summary["dataset"] == "gnomad_r4"
    assert result.summary["sequencing_type"] == "joint"
    assert result.summary["allele_frequency"] == 23500 / 1580590
    assert result.summary["popmax_population"] == "nfe"
    assert result.summary["genetic_ancestry_groups"] == [
        {
            "id": "remaining",
            "allele_count": 813,
            "allele_number": 61242,
            "allele_frequency": 813 / 61242,
            "homozygote_count": 12,
        },
        {
            "id": "amr",
            "allele_count": 406,
            "allele_number": 55508,
            "allele_frequency": 406 / 55508,
            "homozygote_count": 3,
        },
        {
            "id": "fin",
            "allele_count": 2394,
            "allele_number": 61024,
            "allele_frequency": 2394 / 61024,
            "homozygote_count": 48,
        },
        {
            "id": "ami",
            "allele_count": 6,
            "allele_number": 912,
            "allele_frequency": 6 / 912,
            "homozygote_count": 0,
        },
        {
            "id": "eas",
            "allele_count": 0,
            "allele_number": 43066,
            "allele_frequency": 0.0,
            "homozygote_count": 0,
        },
        {
            "id": "mid",
            "allele_count": 26,
            "allele_number": 5138,
            "allele_frequency": 26 / 5138,
            "homozygote_count": 1,
        },
        {
            "id": "sas",
            "allele_count": 92,
            "allele_number": 86168,
            "allele_frequency": 92 / 86168,
            "homozygote_count": 1,
        },
        {
            "id": "asj",
            "allele_count": 147,
            "allele_number": 28948,
            "allele_frequency": 147 / 28948,
            "homozygote_count": 0,
        },
        {
            "id": "afr",
            "allele_count": 184,
            "allele_number": 74402,
            "allele_frequency": 184 / 74402,
            "homozygote_count": 2,
        },
        {
            "id": "nfe",
            "allele_count": 19432,
            "allele_number": 1164182,
            "allele_frequency": 19432 / 1164182,
            "homozygote_count": 159,
            "xx": {
                "allele_count": 10282,
                "allele_number": 605804,
                "allele_frequency": 10282 / 605804,
                "homozygote_count": 75,
            },
            "xy": {
                "allele_count": 9150,
                "allele_number": 558378,
                "allele_frequency": 9150 / 558378,
                "homozygote_count": 84,
            },
            "exome": {
                "allele_count": 18000,
                "allele_number": 1050000,
                "allele_frequency": 18000 / 1050000,
                "homozygote_count": 150,
            },
            "genome": {
                "allele_count": 1432,
                "allele_number": 114182,
                "allele_frequency": 1432 / 114182,
                "homozygote_count": 9,
            },
        },
    ]
    assert result.summary["overall"] == {
        "total": {
            "allele_count": 23500,
            "allele_number": 1580590,
            "allele_frequency": 23500 / 1580590,
            "homozygote_count": 226,
            "exome": {
                "allele_count": 21634,
                "allele_number": 1428186,
                "allele_frequency": 0.015147886899885589,
                "homozygote_count": 209,
            },
            "genome": {
                "allele_count": 1866,
                "allele_number": 152404,
                "allele_frequency": 0.012243772,
                "homozygote_count": 3,
            },
        },
        "xx": {
            "allele_count": 12400,
            "allele_number": 790000,
            "allele_frequency": 12400 / 790000,
            "homozygote_count": 118,
        },
        "xy": {
            "allele_count": 11100,
            "allele_number": 790590,
            "allele_frequency": 11100 / 790590,
            "homozygote_count": 108,
        },
    }
    assert result.summary["age_distribution"]["het"]["bin_edges"] == [30, 35, 40]
    assert result.summary["age_distribution"]["het"]["bin_freq"] == [58, 79]
    assert [item["sequencing_type"] for item in result.summary["age_distributions"]] == [
        "exome",
        "genome",
    ]
    assert result.summary["age_distributions"][1]["age_distribution"]["het"]["bin_freq"] == [
        8,
        7,
    ]


def test_gnomad_fixture_uses_variant_source_url(tmp_path: Path):
    settings = Settings(
        jwt_secret="test-secret",
        use_real_apis=False,
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
    )
    tool = GnomadTool(settings)
    variant = SimpleNamespace(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.260A>G",
        genomic_hg38="1-68444869-T-C",
    )

    result = tool.get_evidence(variant=variant)

    assert result.status == "fixture"
    assert (
        result.source_url
        == "https://gnomad.broadinstitute.org/variant/1-68444869-T-C?dataset=gnomad_r4"
    )


def test_gnomad_fixture_top_level_source_url_does_not_duplicate(tmp_path: Path):
    settings = Settings(
        jwt_secret="test-secret",
        use_real_apis=False,
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
    )
    tool = GnomadTool(settings)
    tool.load_fixture = lambda: {
        "request_identity": {"variant_id": "1-68444869-T-C"},
        "summary": {"variant_id": "1-68444869-T-C", "dataset": "gnomad_r4"},
        "warnings": [],
        "raw": None,
        "source_url": "https://gnomad.example/source",
    }
    variant = SimpleNamespace(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.260A>G",
        genomic_hg38="1-68444869-T-C",
    )

    result = tool.get_evidence(variant=variant)

    assert result.status == "fixture"
    assert result.source_url == "https://gnomad.example/source"
    assert "source_url" not in result.summary


def test_gnomad_live_fallback_does_not_attach_mismatched_fixture_detail(
    monkeypatch, tmp_path: Path
):
    def fake_post(*args, **kwargs):
        raise httpx.ReadTimeout("gnomAD was slow")

    monkeypatch.setattr("app.tools.gnomad.httpx.post", fake_post)
    settings = Settings(
        jwt_secret="test-secret",
        use_real_apis=True,
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
    )
    tool = GnomadTool(settings)
    variant = SimpleNamespace(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.1301C>T",
        genomic_hg38="1-68431319-G-A",
    )

    result = tool.get_evidence(variant=variant)

    assert result.status == "fallback"
    assert result.request_identity == {
        "variant_id": "1-68431319-G-A",
        "dataset": "gnomad_r4",
    }
    assert result.summary == {
        "gene": "RPE65",
        "variant_id": "1-68431319-G-A",
        "dataset": "gnomad_r4",
        "url": "https://gnomad.broadinstitute.org/variant/1-68431319-G-A?dataset=gnomad_r4",
    }
    assert "allele_count" not in result.summary
    assert result.warnings == [
        "live_fetch_failed:ReadTimeout",
        "gnomad_fallback_fixture_variant_mismatch",
    ]


def test_gnomad_live_no_hit_does_not_attach_fixture_metrics(monkeypatch, tmp_path: Path):
    def fake_post(*args, **kwargs):
        return _NoHitResponse()

    monkeypatch.setattr("app.tools.gnomad.httpx.post", fake_post)
    settings = Settings(
        jwt_secret="test-secret",
        use_real_apis=True,
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
    )
    tool = GnomadTool(settings)
    variant = SimpleNamespace(
        gene="RPGRIP1",
        transcript_hgvs="NM_020366.4:c.1997C>T",
        genomic_hg38="14-21324852-C-T",
    )

    result = tool.get_evidence(variant=variant)

    assert result.status == "live"
    assert result.summary["variant_id"] == "14-21324852-C-T"
    assert result.summary["dataset"] == "gnomad_r4"
    assert "allele_count" not in result.summary
    assert "allele_frequency" not in result.summary
    assert "gnomad_variant_not_found" in result.warnings
