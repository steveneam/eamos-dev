from __future__ import annotations

import os
from pathlib import Path

import pytest

import app.services.eamos_coordinate_resolver as coordinate_resolver_module
from app.data_sources import (
    DEFAULT_DATA_SOURCE_REGISTRY,
    LOCAL_HG38_2BIT_SOURCE_ID,
    resolve_local_asset_path,
)
from app.services.eamos_coordinate_resolver import (
    DEFAULT_MANE_GFF_PATH,
    DEFAULT_REFSEQ_GFF_PATH,
    EamosLocalCoordinateResolver,
)
from app.services.search_input_resolver import EamosSearchInputResolver, parse_search_text
from scripts.validate_project_100_coordinates import _project_100_source_rows

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "app" / "fixtures"
VERIFY_PROJECT_100_COORDINATES = os.environ.get("EAMOS_VERIFY_PROJECT_100_COORDINATES") == "1"


def _missing_reference_store():
    raise OSError("reference asset intentionally unavailable in this unit test")


def _tiny_gff(
    tmp_path: Path,
    name: str,
    *,
    gene: str = "TEST",
    transcript: str = "NM_TEST.1",
) -> Path:
    path = tmp_path / name
    path.write_text(
        "\n".join(
            [
                "##gff-version 3",
                (
                    "NC_000001.11\tRefSeq\tmRNA\t100\t108\t.\t+\t.\t"
                    f"ID=rna-{transcript};transcript_id={transcript};gene={gene}"
                ),
                (
                    "NC_000001.11\tRefSeq\texon\t100\t108\t.\t+\t.\t"
                    f"ID=exon-{transcript}-1;Parent=rna-{transcript};gene={gene}"
                ),
                (
                    "NC_000001.11\tRefSeq\tCDS\t100\t108\t.\t+\t0\t"
                    f"ID=cds-{transcript}-1;Parent=rna-{transcript};gene={gene}"
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _tiny_refseq_gff(tmp_path: Path) -> Path:
    return _tiny_gff(tmp_path, "tiny_refseq.gff")


def test_eamos_local_coordinate_resolver_maps_local_refseq_gff_without_live_api(
    tmp_path: Path,
) -> None:
    refseq_gff = _tiny_refseq_gff(tmp_path)
    resolver = EamosLocalCoordinateResolver(
        mane_gff_path=None,
        refseq_gff_path=refseq_gff,
        coordinate_catalog_path=None,
        reference_store_factory=_missing_reference_store,
    )

    resolved = resolver.resolve(
        gene="TEST",
        transcript="NM_TEST.1",
        cdna="c.3G>T",
    )

    assert resolved is not None
    assert resolved.genomic_hg38 == "1-102-G-T"
    assert resolved.genomic_hgvs == "NC_000001.11:g.102G>T"
    assert resolved.source == "eamos_local_transcript_reference"
    assert any(source.startswith("eamos_refseq") for source in resolved.provenance)
    assert resolved.warnings == ("eamos_reference_base_unavailable",)


def test_search_text_parser_accepts_gene_space_transcript_hgvs() -> None:
    parsed = parse_search_text("ABCA4 NM_000350.3:c.5435T>A")

    assert parsed.gene == "ABCA4"
    assert parsed.transcript == "NM_000350.3"
    assert parsed.cdna == "c.5435T>A"


def test_search_input_resolver_uses_eamos_local_coordinates_before_live_api(
    tmp_path: Path,
) -> None:
    refseq_gff = _tiny_refseq_gff(tmp_path)
    local_resolver = EamosLocalCoordinateResolver(
        mane_gff_path=None,
        refseq_gff_path=refseq_gff,
        coordinate_catalog_path=None,
        reference_store_factory=_missing_reference_store,
    )

    resolution = EamosSearchInputResolver(
        settings=None,
        resolve_coordinates=True,
        local_coordinate_resolver=local_resolver,
    ).resolve_text("TEST NM_TEST.1:c.3G>T")

    assert resolution.genomic_hg38 == "1-102-G-T"
    assert resolution.genomic_hgvs == "NC_000001.11:g.102G>T"
    assert resolution.local_coordinate_summary is not None
    assert resolution.local_coordinate_summary["source"] == "eamos_local_transcript_reference"
    assert resolution.coordinate_resolution_audit.resolver_path == "eamos_local"
    assert resolution.coordinate_resolution_audit.used_eamos_local is True
    assert resolution.coordinate_resolution_audit.used_variant_validator is False
    assert resolution.coordinate_resolution_audit.used_clinvar_for_coordinates is False
    assert (
        resolution.coordinate_resolution_audit.clinvar_role
        == "source_query_input_not_coordinate_provider"
    )
    assert resolution.variant_validator_summary is None
    assert resolution.provenance == ("eamos_local_coordinate_resolver",)


def test_eamos_local_coordinate_resolver_loads_only_requested_gene_lazily(
    tmp_path: Path,
    monkeypatch,
) -> None:
    refseq_gff = _tiny_refseq_gff(tmp_path)
    calls: list[tuple[Path | None, tuple[str, ...]]] = []
    original = coordinate_resolver_module._load_gff_transcript_models_for_genes

    def spy(path: Path | None, genes: tuple[str, ...]):
        calls.append((path, genes))
        return original(path, genes)

    monkeypatch.setattr(
        coordinate_resolver_module,
        "_load_gff_transcript_models_for_genes",
        spy,
    )

    resolver = EamosLocalCoordinateResolver(
        mane_gff_path=None,
        refseq_gff_path=refseq_gff,
        coordinate_catalog_path=None,
        reference_store_factory=_missing_reference_store,
    )

    assert calls == []

    resolved = resolver.resolve(
        gene="TEST",
        transcript="NM_TEST.1",
        cdna="c.3G>T",
    )

    assert resolved is not None
    assert calls == [(refseq_gff, ("TEST",))]


def test_eamos_local_coordinate_resolver_does_not_load_refseq_when_mane_matches(
    tmp_path: Path,
    monkeypatch,
) -> None:
    mane_gff = _tiny_gff(tmp_path, "tiny_mane.gff", transcript="NM_TEST.1")
    refseq_gff = _tiny_gff(tmp_path, "tiny_refseq.gff", transcript="NM_OTHER.1")
    calls: list[tuple[Path | None, tuple[str, ...]]] = []
    original = coordinate_resolver_module._load_gff_transcript_models_for_genes

    def spy(path: Path | None, genes: tuple[str, ...]):
        calls.append((path, genes))
        return original(path, genes)

    monkeypatch.setattr(
        coordinate_resolver_module,
        "_load_gff_transcript_models_for_genes",
        spy,
    )

    resolver = EamosLocalCoordinateResolver(
        mane_gff_path=mane_gff,
        refseq_gff_path=refseq_gff,
        coordinate_catalog_path=None,
        reference_store_factory=_missing_reference_store,
    )

    resolved = resolver.resolve(
        gene="TEST",
        transcript="NM_TEST.1",
        cdna="c.3G>T",
    )

    assert resolved is not None
    assert resolved.transcript == "NM_TEST.1"
    assert calls == [(mane_gff, ("TEST",))]


def test_eamos_local_coordinate_resolver_loads_refseq_when_mane_lacks_requested_transcript(
    tmp_path: Path,
    monkeypatch,
) -> None:
    mane_gff = _tiny_gff(tmp_path, "tiny_mane.gff", transcript="NM_MANE.1")
    refseq_gff = _tiny_gff(tmp_path, "tiny_refseq.gff", transcript="NM_REFSEQ.1")
    calls: list[tuple[Path | None, tuple[str, ...]]] = []
    original = coordinate_resolver_module._load_gff_transcript_models_for_genes

    def spy(path: Path | None, genes: tuple[str, ...]):
        calls.append((path, genes))
        return original(path, genes)

    monkeypatch.setattr(
        coordinate_resolver_module,
        "_load_gff_transcript_models_for_genes",
        spy,
    )

    resolver = EamosLocalCoordinateResolver(
        mane_gff_path=mane_gff,
        refseq_gff_path=refseq_gff,
        coordinate_catalog_path=None,
        reference_store_factory=_missing_reference_store,
    )

    resolved = resolver.resolve(
        gene="TEST",
        transcript="NM_REFSEQ.1",
        cdna="c.3G>T",
    )

    assert resolved is not None
    assert resolved.transcript == "NM_REFSEQ.1"
    assert calls == [(mane_gff, ("TEST",)), (refseq_gff, ("TEST",))]


@pytest.mark.skipif(
    not VERIFY_PROJECT_100_COORDINATES,
    reason=(
        "set EAMOS_VERIFY_PROJECT_100_COORDINATES=1 to verify the ignored local "
        "MANE/RefSeq/hg38 assets against the project-100 stack"
    ),
)
def test_eamos_local_coordinate_resolver_maps_project_100_stack_without_catalog() -> None:
    missing_assets = _missing_project_100_assets()
    if missing_assets:
        pytest.skip(f"ignored local resolver assets are absent: {', '.join(missing_assets)}")

    resolver = EamosLocalCoordinateResolver(coordinate_catalog_path=None)
    unresolved: list[str] = []
    try:
        for row in _project_100_source_rows():
            resolved = resolver.resolve(
                gene=row["gene"],
                transcript=row["transcript"],
                cdna=row["cdna"],
                accession=row.get("accession"),
                clinvar_variation_id=row.get("clinvar_variation_id"),
            )
            if resolved is None:
                unresolved.append(f"{row['sample_id']} {row['gene']} {row['cdna']}")
                continue

            assert resolved.source == "eamos_local_transcript_reference"
            assert "eamos_coordinate_catalog" not in resolved.provenance
            assert resolved.chrom
            assert resolved.pos > 0
            assert resolved.ref
            assert resolved.alt
            assert resolved.genomic_hg38 == (
                f"{resolved.chrom}-{resolved.pos}-{resolved.ref}-{resolved.alt}"
            )
            assert resolved.genomic_hgvs is not None
            assert resolved.genomic_hgvs.startswith("NC_")
    finally:
        resolver.close()

    assert unresolved == []


def _missing_project_100_assets() -> list[str]:
    missing: list[str] = []
    for path in (DEFAULT_MANE_GFF_PATH, DEFAULT_REFSEQ_GFF_PATH):
        if not path.exists():
            missing.append(str(path))

    record = DEFAULT_DATA_SOURCE_REGISTRY.get(LOCAL_HG38_2BIT_SOURCE_ID)
    hg38_path = resolve_local_asset_path(record)
    if not hg38_path.exists():
        missing.append(str(hg38_path))
    return missing
