from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.tools.base import FixtureBackedTool
from app.tools.litvar2 import LitVar2Tool
from app.tools.pubmed import PubmedTool
from app.tools.spliceai import SpliceAiTool
from app.tools.variant_validator import _mutate_variant


def _settings(**overrides) -> Settings:
    return Settings(jwt_secret="test-secret", **overrides)


def test_spliceai_live_stub_requires_genomic_coordinates(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_get(*args, **kwargs):
        raise AssertionError("SpliceAI live request should not run without genomic_hg38")

    monkeypatch.setattr("app.tools.spliceai.httpx.get", fail_get)
    variant = SimpleNamespace(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.260A>G",
        genomic_hg38=None,
    )

    result = SpliceAiTool(_settings(use_real_apis=True)).get_evidence(variant)

    assert result.status == "live_stub"
    assert result.summary == {}
    assert result.request_identity == {"gene": "RPE65", "cdna": "c.260A>G"}
    assert "requires genomic coordinates" in result.warnings[0]


def test_variant_validator_does_not_fabricate_defaults_without_coordinates() -> None:
    variant = SimpleNamespace(genomic_hg38=None, variation_type="", consequence="")

    _mutate_variant(variant, {"gene": "RPE65", "variant_id": None})

    assert variant.genomic_hg38 is None
    assert variant.variation_type == ""
    assert variant.consequence == ""


def test_variant_validator_defaults_only_after_coordinate_resolution() -> None:
    variant = SimpleNamespace(genomic_hg38=None, variation_type="", consequence="")

    _mutate_variant(variant, {"gene": "RPE65", "variant_id": "1-68444869-T-C"})

    assert variant.genomic_hg38 == "1-68444869-T-C"
    assert variant.variation_type == "single nucleotide variant"
    assert variant.consequence == "missense variant"


def test_pubmed_no_hit_miss_uses_empty_raw(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"esearchresult": {"idlist": []}}

    calls = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        return Response()

    monkeypatch.setattr("app.tools.pubmed.httpx.get", fake_get)
    variant = SimpleNamespace(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.260A>G",
        protein_change="p.Asp87Gly",
        dbsnp_rsid="rs1645931040",
    )

    result = PubmedTool(_settings(use_real_apis=True)).get_evidence(variant)

    assert len(calls) == 2
    assert result.status == "live"
    assert result.summary == {"articles": [], "total": 0}
    assert result.raw == {}
    assert result.raw is not None


def test_litvar2_quotes_variant_id_path_segments(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class Response:
        def __init__(self, payload) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self.payload

    class Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def get(self, url, params=None):
            calls.append(url)
            if url.endswith("/variant/autocomplete/"):
                return Response([{"litvar_id": "litvar@rs752238803##"}])
            assert "litvar%40rs752238803%23%23" in url
            return Response({"pmids": ["41234567"], "pmids_count": 1})

    monkeypatch.setattr("app.tools.litvar2.httpx.Client", Client)
    variant = SimpleNamespace(
        gene="USH2A",
        transcript_hgvs="c.2276G>T",
        protein_change="p.Cys759Phe",
        dbsnp_rsid="rs752238803",
    )

    result = LitVar2Tool(_settings(use_real_apis=True)).get_evidence(variant)

    assert result.status == "live"
    assert result.summary["total_publications"] == 1
    assert result.summary["articles"][0]["pmid"] == "41234567"
    assert "litvar%40rs752238803%23%23" in result.source_url
    assert len(calls) == 2


def test_load_fixture_missing_or_corrupt_degrades_to_empty_dict(tmp_path: Path) -> None:
    class Tool(FixtureBackedTool):
        source = "test"

        def __init__(self, path: Path) -> None:
            super().__init__(_settings())
            self.path = path

        def fixture_path(self) -> Path:
            return self.path

    missing = tmp_path / "missing.json"
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{", encoding="utf-8")

    assert Tool(missing).load_fixture() == {}
    assert Tool(corrupt).load_fixture() == {}
