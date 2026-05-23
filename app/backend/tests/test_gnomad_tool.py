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
                                "id": "1kg:gbr",
                                "ac": 4,
                                "an": 174,
                                "homozygote_count": 0,
                            },
                            {
                                "id": "eas",
                                "ac": 0,
                                "an": 43066,
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
                        "populations": [],
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
                    "genome": None,
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
            "id": "nfe",
            "allele_count": 19432,
            "allele_number": 1164182,
            "allele_frequency": 19432 / 1164182,
            "homozygote_count": 159,
        },
        {
            "id": "eas",
            "allele_count": 0,
            "allele_number": 43066,
            "allele_frequency": 0.0,
            "homozygote_count": 0,
        },
    ]
    assert result.summary["age_distribution"]["het"]["bin_edges"] == [30, 35, 40]
    assert result.summary["age_distribution"]["het"]["bin_freq"] == [58, 79]


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
