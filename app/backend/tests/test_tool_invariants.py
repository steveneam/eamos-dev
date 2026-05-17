from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.tools.base import FixtureBackedTool
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
