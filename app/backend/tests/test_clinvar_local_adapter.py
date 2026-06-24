from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.lookup_service import (
    CLINVAR_GENE_DISTRIBUTION_EXCLUDED_PENDING_INDEX,
    _clinvar_distribution_runtime_path,
    _clinvar_gene_distribution_exclusion_warning,
)
from app.services.clinvar_local import (
    CLINVAR_SOURCE_ID,
    DEFAULT_CLINVAR_VCF_FIXTURE_PATH,
    ClinVarIndexedLocalAdapter,
    ClinVarLocalError,
    ClinVarLocalProvenance,
    ClinVarLocalStore,
    build_clinvar_gene_distribution,
    build_clinvar_gene_distribution_from_index,
    inspect_clinvar_gene_distribution_index,
    materialize_clinvar_gene_distribution_index,
    parse_clinvar_vcf,
)
from app.services.indexed_sources import IndexedSourceError, IndexedVcfRecord


def test_store_provenance_records_clinvar_fixture_metadata() -> None:
    store = ClinVarLocalStore()
    provenance = store.provenance()

    assert provenance.source_id == CLINVAR_SOURCE_ID
    assert provenance.source_version == (
        "ClinVar GRCh38 VCF weekly release 2026-05-25 / clinvar_20260523"
    )
    assert provenance.file_date == "20260523"
    assert provenance.relative_path == "app/backend/app/fixtures/data_sources/clinvar_tiny.vcf"
    assert provenance.checksum_algorithm == "sha256"
    assert re.fullmatch(r"[0-9a-f]{64}", provenance.checksum)
    assert provenance.record_id is None


def test_tiny_fixture_resolves_rpe65_variant_by_gnomad_style_id() -> None:
    lookup = ClinVarLocalStore().lookup_variant_id("1-68444869-T-C")

    assert lookup.available is True
    record = lookup.record
    assert record is not None
    assert record.gnomad_variant_id == "1-68444869-T-C"
    assert record.accession == "VCV001421454"
    assert record.variation_id == "1421454"
    assert record.classification == "Uncertain significance"
    assert record.review_status == "criteria provided, single submitter"
    assert record.conditions == ("Retinitis pigmentosa", "Leber congenital amaurosis 2")
    assert record.condition_summary == "Retinitis pigmentosa, Leber congenital amaurosis 2"
    assert record.hgvs_aliases == (
        "NC_000001.11:g.68444869T>C",
        "NM_000329.3:c.260A>G",
        "NP_000320.1:p.Asp87Gly",
    )
    assert record.gene_symbols == ("RPE65",)
    assert record.provenance.source_id == CLINVAR_SOURCE_ID
    assert record.provenance.record_id == "VCV001421454"


def test_gene_distribution_aggregates_installed_local_clinvar_records() -> None:
    distribution = build_clinvar_gene_distribution("RPE65", query_variant_id="1-68444869-T-C")

    assert distribution.source_id == CLINVAR_SOURCE_ID
    assert distribution.source_status == "fixture"
    assert distribution.source_version == (
        "ClinVar GRCh38 VCF weekly release 2026-05-25 / clinvar_20260523"
    )
    assert distribution.public_serialization_allowed is True
    assert distribution.total == 1
    assert distribution.cells["vus_missense"] == 1
    assert distribution.row_totals == {"pathogenic": 0, "vus": 1, "benign": 0}
    assert distribution.query_cell == "vus_missense"
    assert distribution.query_variant_id == "1-68444869-T-C"
    assert distribution.query_accession == "VCV001421454"
    assert distribution.query_classification == "Uncertain significance"
    assert "clinvar_local_fixture_scope" in distribution.warnings
    assert "legacy" not in distribution.subtitle.lower()


def test_materialized_gene_distribution_index_reads_bounded_gene_payload(
    tmp_path: Path,
) -> None:
    index_path = tmp_path / "clinvar-gene-distribution.sqlite"
    manifest_path = tmp_path / "clinvar-gene-distribution.manifest.json"

    inspection = materialize_clinvar_gene_distribution_index(
        vcf_path=DEFAULT_CLINVAR_VCF_FIXTURE_PATH,
        index_path=index_path,
        manifest_path=manifest_path,
        force=True,
    )
    distribution = build_clinvar_gene_distribution_from_index(
        "RPE65",
        index_path=index_path,
        query_variant_id="1-68444869-T-C",
    )

    assert inspection.ready is True
    assert inspection.schema_version == "eamos.clinvar_gene_distribution.v1"
    assert inspection.gene_count == 1
    assert inspection.variant_count == 1
    assert distribution.source_id == CLINVAR_SOURCE_ID
    assert distribution.source_status == "fixture_index"
    assert distribution.total == 1
    assert distribution.cells["vus_missense"] == 1
    assert distribution.row_totals == {"pathogenic": 0, "vus": 1, "benign": 0}
    assert distribution.query_cell == "vus_missense"
    assert distribution.query_variant_id == "1-68444869-T-C"
    assert distribution.query_accession == "VCV001421454"
    assert distribution.query_classification == "Uncertain significance"
    assert "clinvar_local_fixture_scope" in distribution.warnings
    assert manifest_path.exists()
    encoded = str(inspection.to_sanitized_dict()).lower()
    assert str(tmp_path).lower() not in encoded


def test_gene_distribution_buckets_classification_and_effect_types(tmp_path: Path) -> None:
    vcf_path = tmp_path / "clinvar_gene_distribution.vcf"
    vcf_path.write_text(
        "\n".join(
            [
                "##fileformat=VCFv4.2",
                "##fileDate=20260523",
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
                (
                    "1\t101\t1421454\tA\tT\t.\t.\t"
                    "VCV=1421454;CLNSIG=Likely_pathogenic;"
                    "CLNREVSTAT=criteria_provided;CLNDN=Example;"
                    "HGVS=NM_000329.3:c.1A>T|NP_000320.1:p.Trp1Ter;GENEINFO=RPE65:6121"
                ),
                (
                    "1\t102\t1421455\tA\tG\t.\t.\t"
                    "VCV=1421455;CLNSIG=Benign;"
                    "CLNREVSTAT=criteria_provided;CLNDN=Example;"
                    "HGVS=NM_000329.3:c.3A>G|NP_000320.1:p.=;GENEINFO=RPE65:6121"
                ),
                (
                    "1\t103\t1421456\tA\tG\t.\t.\t"
                    "VCV=1421456;CLNSIG=Conflicting_classifications_of_pathogenicity;"
                    "CLNREVSTAT=criteria_provided;CLNDN=Example;"
                    "HGVS=NM_000329.3:c.4+1A>G;GENEINFO=RPE65:6121"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    distribution = build_clinvar_gene_distribution(
        "RPE65",
        store=ClinVarLocalStore(vcf_path),
        query_variant_id="1-102-A-G",
    )

    assert distribution.source_status == "local"
    assert distribution.total == 3
    assert distribution.cells["pathogenic_lof"] == 1
    assert distribution.cells["benign_synonymous"] == 1
    assert distribution.cells["vus_noncoding"] == 1
    assert distribution.row_totals == {"pathogenic": 1, "vus": 1, "benign": 1}
    assert distribution.query_cell == "benign_synonymous"
    assert distribution.query_accession == "VCV001421455"
    assert "clinvar_local_fixture_scope" not in distribution.warnings


def test_lookup_service_excludes_full_vcf_clinvar_distribution_when_m9_lookup_enabled(
    tmp_path: Path,
) -> None:
    vcf_path = tmp_path / "clinvar.vcf.gz"
    index_path = tmp_path / "clinvar.vcf.gz.tbi"
    distribution_index_path = tmp_path / "clinvar-gene-distribution.sqlite"
    distribution_manifest_path = tmp_path / "clinvar-gene-distribution.manifest.json"
    vcf_path.write_bytes(b"vcf")
    settings = SimpleNamespace(
        backend_root=tmp_path,
        clinvar_runtime_vcf_path=vcf_path,
        clinvar_runtime_index_path=index_path,
        clinvar_gene_distribution_index_path=distribution_index_path,
        clinvar_gene_distribution_manifest_path=distribution_manifest_path,
        local_evidence_enabled=False,
        local_evidence_allowed_flows_raw="lookup",
        local_evidence_require_real_apis=True,
        use_real_apis=True,
    )

    assert _clinvar_distribution_runtime_path(settings) is None
    assert _clinvar_gene_distribution_exclusion_warning(settings) is None

    index_path.write_bytes(b"index")

    assert _clinvar_distribution_runtime_path(settings) is None
    assert _clinvar_gene_distribution_exclusion_warning(settings) is None

    settings.local_evidence_enabled = True
    assert _clinvar_distribution_runtime_path(settings) is None
    assert (
        _clinvar_gene_distribution_exclusion_warning(settings)
        == CLINVAR_GENE_DISTRIBUTION_EXCLUDED_PENDING_INDEX
    )

    materialize_clinvar_gene_distribution_index(
        vcf_path=DEFAULT_CLINVAR_VCF_FIXTURE_PATH,
        index_path=distribution_index_path,
        force=True,
    )
    assert _clinvar_distribution_runtime_path(settings) is None
    assert (
        _clinvar_gene_distribution_exclusion_warning(settings)
        == CLINVAR_GENE_DISTRIBUTION_EXCLUDED_PENDING_INDEX
    )

    materialize_clinvar_gene_distribution_index(
        vcf_path=DEFAULT_CLINVAR_VCF_FIXTURE_PATH,
        index_path=distribution_index_path,
        manifest_path=distribution_manifest_path,
        force=True,
    )
    assert _clinvar_distribution_runtime_path(settings) == str(distribution_index_path)
    assert _clinvar_gene_distribution_exclusion_warning(settings) is None
    ready = inspect_clinvar_gene_distribution_index(settings)
    assert ready.ready is True

    settings.local_evidence_allowed_flows_raw = "gene_viewer"
    assert _clinvar_distribution_runtime_path(settings) is None
    assert _clinvar_gene_distribution_exclusion_warning(settings) is None


def test_clinvar_gene_distribution_index_requires_matching_manifest(
    tmp_path: Path,
) -> None:
    index_path = tmp_path / "clinvar-gene-distribution.sqlite"
    manifest_path = tmp_path / "clinvar-gene-distribution.manifest.json"
    materialize_clinvar_gene_distribution_index(
        vcf_path=DEFAULT_CLINVAR_VCF_FIXTURE_PATH,
        index_path=index_path,
        force=True,
    )
    settings = SimpleNamespace(
        backend_root=tmp_path,
        clinvar_gene_distribution_index_path=index_path,
        clinvar_gene_distribution_manifest_path=manifest_path,
    )

    missing = inspect_clinvar_gene_distribution_index(settings)
    assert missing.ready is False
    assert missing.status == "manifest_missing"
    assert "clinvar_gene_distribution_manifest_missing" in missing.warnings
    existing_without_manifest = materialize_clinvar_gene_distribution_index(
        vcf_path=DEFAULT_CLINVAR_VCF_FIXTURE_PATH,
        index_path=index_path,
        manifest_path=manifest_path,
        force=False,
    )
    assert existing_without_manifest.ready is False
    assert existing_without_manifest.status == "manifest_missing"

    manifest_path.write_text(
        json.dumps(
            {
                "artifact_id": "clinvar_gene_distribution_index",
                "source_id": "eamos_clinvar_gene_distribution_index",
                "upstream_source_id": CLINVAR_SOURCE_ID,
                "schema_version": "eamos.clinvar_gene_distribution.v1",
                "byte_size": index_path.stat().st_size,
                "sha256": "not-the-real-checksum",
            }
        ),
        encoding="utf-8",
    )
    mismatch = inspect_clinvar_gene_distribution_index(settings)
    assert mismatch.ready is False
    assert mismatch.status == "manifest_checksum_mismatch"
    assert mismatch.checksum_verified is True
    assert mismatch.checksum_algorithm == "sha256"


def test_indexed_adapter_resolves_exact_clinvar_variant_without_full_vcf_parse(
    tmp_path: Path,
) -> None:
    vcf_path = tmp_path / "clinvar.vcf.gz"
    index_path = tmp_path / "clinvar.vcf.gz.tbi"
    vcf_path.write_bytes(b"indexed-vcf")
    index_path.write_bytes(b"index")
    reader = _FakeIndexedClinVarReader(
        (
            IndexedVcfRecord(
                requested_chrom="NC_000001.11",
                chrom="1",
                position=68444869,
                record_id="VCV001421454",
                ref="T",
                alts=("C",),
                info={
                    "CLNSIG": ("Uncertain_significance",),
                    "CLNREVSTAT": ("criteria_provided,_single_submitter",),
                    "CLNDN": ("Retinitis_pigmentosa", "Leber_congenital_amaurosis_2"),
                    "CLNHGVS": ("NC_000001.11:g.68444869T>C", "NM_000329.3:c.260A>G"),
                    "GENEINFO": ("RPE65:6121",),
                },
                source_id=CLINVAR_SOURCE_ID,
            ),
        )
    )
    adapter = ClinVarIndexedLocalAdapter(
        vcf_path=vcf_path,
        index_path=index_path,
        reader_factory=lambda _vcf, _index: reader,
    )

    lookup = adapter.lookup_variant_id("1-68444869-T-C")

    assert reader.queries == [("1", 68444869)]
    assert lookup.available is True
    assert lookup.record is not None
    assert lookup.record.accession == "VCV001421454"
    assert lookup.record.gnomad_variant_id == "1-68444869-T-C"
    assert lookup.record.classification == "Uncertain significance"
    assert lookup.record.review_status == "criteria provided, single submitter"
    assert lookup.record.conditions == (
        "Retinitis pigmentosa",
        "Leber congenital amaurosis 2",
    )
    assert lookup.record.gene_symbols == ("RPE65",)
    assert lookup.record.provenance.relative_path == "runtime:clinvar.vcf.gz"
    assert lookup.record.provenance.checksum_algorithm == "runtime_manifest"


def test_indexed_adapter_from_settings_resolves_backend_relative_paths(
    tmp_path: Path,
) -> None:
    backend_root = tmp_path / "backend"
    vcf_rel = Path("data/bio_assets/clinvar/clinvar.vcf.gz")
    index_rel = Path("data/bio_assets/clinvar/clinvar.vcf.gz.tbi")
    vcf_path = backend_root / vcf_rel
    index_path = backend_root / index_rel
    vcf_path.parent.mkdir(parents=True)
    vcf_path.write_bytes(b"indexed-vcf")
    index_path.write_bytes(b"index")
    reader = _FakeIndexedClinVarReader(
        (
            IndexedVcfRecord(
                requested_chrom="1",
                chrom="1",
                position=68444869,
                record_id="VCV001421454",
                ref="T",
                alts=("C",),
                info={
                    "CLNSIG": ("Uncertain_significance",),
                    "CLNREVSTAT": ("criteria_provided,_single_submitter",),
                    "CLNDN": ("Retinitis_pigmentosa",),
                    "GENEINFO": ("RPE65:6121",),
                },
                source_id=CLINVAR_SOURCE_ID,
            ),
        )
    )
    factory_calls: list[tuple[Path, Path]] = []

    def reader_factory(path: Path, index: Path) -> _FakeIndexedClinVarReader:
        factory_calls.append((path, index))
        return reader

    adapter = ClinVarIndexedLocalAdapter.from_settings(
        SimpleNamespace(
            backend_root=backend_root,
            clinvar_runtime_vcf_path=vcf_rel,
            clinvar_runtime_index_path=index_rel,
        ),
        reader_factory=reader_factory,
    )

    lookup = adapter.lookup_variant_id("1-68444869-T-C")

    assert factory_calls == [(vcf_path, index_path)]
    assert reader.queries == [("1", 68444869)]
    assert lookup.available is True
    assert lookup.record is not None
    assert lookup.record.accession == "VCV001421454"


def test_indexed_adapter_distinguishes_clinvar_allele_mismatch(tmp_path: Path) -> None:
    vcf_path = tmp_path / "clinvar.vcf.gz"
    index_path = tmp_path / "clinvar.vcf.gz.tbi"
    vcf_path.write_bytes(b"indexed-vcf")
    index_path.write_bytes(b"index")
    adapter = ClinVarIndexedLocalAdapter(
        vcf_path=vcf_path,
        index_path=index_path,
        reader_factory=lambda _vcf, _index: _FakeIndexedClinVarReader(
            (
                IndexedVcfRecord(
                    requested_chrom="1",
                    chrom="1",
                    position=101,
                    record_id="VCV000000001",
                    ref="A",
                    alts=("G",),
                    info={
                        "CLNSIG": ("Pathogenic",),
                        "CLNREVSTAT": ("criteria_provided",),
                        "CLNDN": ("Example",),
                        "GENEINFO": ("RPE65:6121",),
                    },
                    source_id=CLINVAR_SOURCE_ID,
                ),
            )
        ),
    )

    mismatch = adapter.lookup(chrom="1", position=101, ref="A", alt="T")
    no_hit = adapter.lookup(chrom="1", position=102, ref="A", alt="T")

    assert mismatch.available is False
    assert mismatch.unavailable_reason == "allele_mismatch"
    assert mismatch.warnings == ("clinvar_local_allele_mismatch",)
    assert no_hit.unavailable_reason == "variant_not_found"
    assert no_hit.warnings == ("clinvar_local_variant_not_found",)


def test_indexed_adapter_fail_closed_on_reader_errors(tmp_path: Path) -> None:
    vcf_path = tmp_path / "clinvar.vcf.gz"
    index_path = tmp_path / "clinvar.vcf.gz.tbi"
    vcf_path.write_bytes(b"indexed-vcf")
    index_path.write_bytes(b"index")
    adapter = ClinVarIndexedLocalAdapter(
        vcf_path=vcf_path,
        index_path=index_path,
        reader_factory=lambda _vcf, _index: _FailingIndexedClinVarReader(),
    )

    lookup = adapter.lookup_variant_id("1-101-A-G")

    assert lookup.available is False
    assert lookup.unavailable_reason == "unknown_contig"
    assert lookup.warnings == ("clinvar_local_unknown_contig",)


def test_lookup_accepts_contig_alias_and_vcv_or_variation_id() -> None:
    store = ClinVarLocalStore()

    by_ncbi_contig = store.lookup(
        chrom="NC_000001.11",
        position=68444869,
        ref="T",
        alt="C",
    )
    by_chr_contig = store.lookup(chrom="chr1", position=68444869, ref="T", alt="C")
    by_vcv = store.lookup_accession("VCV001421454")
    by_variation_id = store.lookup_accession("1421454")

    assert by_ncbi_contig.available is True
    assert by_chr_contig.record == by_ncbi_contig.record
    assert by_vcv.record == by_ncbi_contig.record
    assert by_variation_id.record == by_ncbi_contig.record


def test_parser_canonicalizes_refseq_contigs_for_variant_identity(tmp_path: Path) -> None:
    vcf_path = tmp_path / "clinvar_nc_contig.vcf"
    vcf_path.write_text(
        "\n".join(
            [
                "##fileformat=VCFv4.2",
                "##fileDate=20260523",
                "##reference=GRCh38",
                "##contig=<ID=NC_000001.11,length=248956422>",
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
                (
                    "NC_000001.11\t101\t1421454\tA\tG\t.\t.\t"
                    "VCV=1421454;CLNSIG=Likely_pathogenic;"
                    "CLNREVSTAT=criteria_provided,_single_submitter;"
                    "CLNDN=Leber_congenital_amaurosis_2;"
                    "CLNHGVS=NC_000001.11:g.101A>G;GENEINFO=RPE65:6121"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    store = ClinVarLocalStore(vcf_path)
    lookup = store.lookup(chrom="chr1", position=101, ref="a", alt="g")

    assert lookup.available is True
    assert lookup.record is not None
    assert lookup.record.chrom == "1"
    assert lookup.record.gnomad_variant_id == "1-101-A-G"
    assert lookup.record.accession == "VCV001421454"
    assert lookup.record.provenance.record_id == "VCV001421454"


def test_store_rejects_duplicate_variant_and_accession_identities(tmp_path: Path) -> None:
    duplicate_variant = tmp_path / "clinvar_duplicate_variant.vcf"
    duplicate_variant.write_text(
        "\n".join(
            [
                "##fileformat=VCFv4.2",
                "##fileDate=20260523",
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
                (
                    "1\t101\t1421454\tA\tG\t.\t.\t"
                    "VCV=1421454;CLNSIG=Uncertain_significance;"
                    "CLNREVSTAT=criteria_provided,_single_submitter"
                ),
                (
                    "1\t101\t1421455\tA\tG\t.\t.\t"
                    "VCV=1421455;CLNSIG=Likely_pathogenic;"
                    "CLNREVSTAT=criteria_provided,_single_submitter"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    duplicate_accession = tmp_path / "clinvar_duplicate_accession.vcf"
    duplicate_accession.write_text(
        "\n".join(
            [
                "##fileformat=VCFv4.2",
                "##fileDate=20260523",
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
                (
                    "1\t101\t1421454\tA\tG\t.\t.\t"
                    "VCV=1421454;CLNSIG=Uncertain_significance;"
                    "CLNREVSTAT=criteria_provided,_single_submitter"
                ),
                (
                    "1\t102\t1421454\tC\tT\t.\t.\t"
                    "VCV=1421454;CLNSIG=Likely_pathogenic;"
                    "CLNREVSTAT=criteria_provided,_single_submitter"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ClinVarLocalError) as duplicate_variant_exc:
        ClinVarLocalStore(duplicate_variant)
    with pytest.raises(ClinVarLocalError) as duplicate_accession_exc:
        ClinVarLocalStore(duplicate_accession)

    assert duplicate_variant_exc.value.code == "duplicate_clinvar_variant_identity"
    assert duplicate_variant_exc.value.details["variant_id"] == "1-101-A-G"
    assert duplicate_accession_exc.value.code == "duplicate_clinvar_accession"
    assert duplicate_accession_exc.value.details["accession"] == "VCV001421454"


def test_no_hit_mismatch_and_invalid_queries_return_fail_closed_states() -> None:
    store = ClinVarLocalStore()

    no_hit = store.lookup_variant_id("1-68444870-T-C")
    allele_mismatch = store.lookup(chrom="1", position=68444869, ref="T", alt="A")
    contig_mismatch = store.lookup(chrom="chr7", position=68444869, ref="T", alt="C")
    invalid = store.lookup_variant_id("not-a-variant")

    assert no_hit.available is False
    assert no_hit.unavailable_reason == "variant_not_found"
    assert no_hit.warnings == ("clinvar_local_variant_not_found",)
    assert allele_mismatch.available is False
    assert allele_mismatch.unavailable_reason == "allele_mismatch"
    assert allele_mismatch.warnings == ("clinvar_local_allele_mismatch",)
    assert contig_mismatch.available is False
    assert contig_mismatch.unavailable_reason == "contig_not_found"
    assert contig_mismatch.warnings == ("clinvar_local_contig_not_found",)
    assert invalid.available is False
    assert invalid.unavailable_reason == "invalid_variant_id"


def test_parser_failures_are_structured_for_malformed_vcf_rows(tmp_path: Path) -> None:
    provenance = ClinVarLocalProvenance(
        source_id=CLINVAR_SOURCE_ID,
        source_version="test",
        file_date=None,
        checksum_algorithm="sha256",
        checksum="0" * 64,
        relative_path="bad.vcf",
    )

    bad_missing_info = tmp_path / "bad_missing_info.vcf"
    bad_missing_info.write_text(
        "\n".join(
            [
                "##fileformat=VCFv4.2",
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
                "1\t68444869\tVCV001421454\tT\tC\t.\t.\tCLNSIG=Uncertain_significance",
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ClinVarLocalError) as missing_info_exc:
        parse_clinvar_vcf(bad_missing_info, provenance=provenance)

    bad_position = tmp_path / "bad_position.vcf"
    bad_position.write_text(
        "\n".join(
            [
                "##fileformat=VCFv4.2",
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
                (
                    "1\tbad\tVCV001421454\tT\tC\t.\t.\t"
                    "CLNSIG=Uncertain_significance;CLNREVSTAT=criteria_provided"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ClinVarLocalError) as bad_position_exc:
        parse_clinvar_vcf(bad_position, provenance=provenance)

    bad_duplicate_info = tmp_path / "bad_duplicate_info.vcf"
    bad_duplicate_info.write_text(
        "\n".join(
            [
                "##fileformat=VCFv4.2",
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
                (
                    "1\t68444869\tVCV001421454\tT\tC\t.\t.\t"
                    "CLNSIG=Uncertain_significance;CLNREVSTAT=criteria_provided;"
                    "CLNSIG=Likely_pathogenic"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ClinVarLocalError) as duplicate_info_exc:
        parse_clinvar_vcf(bad_duplicate_info, provenance=provenance)

    assert missing_info_exc.value.code == "malformed_clinvar_vcf_row"
    assert missing_info_exc.value.details == {"row": 3, "field": "CLNREVSTAT"}
    assert bad_position_exc.value.code == "malformed_clinvar_vcf_row"
    assert bad_position_exc.value.details == {"row": 3, "position": "bad"}
    assert duplicate_info_exc.value.code == "malformed_clinvar_vcf_row"
    assert duplicate_info_exc.value.details == {"row": 3, "field": "CLNSIG"}


class _FakeIndexedClinVarReader:
    def __init__(self, records: tuple[IndexedVcfRecord, ...]) -> None:
        self.records = records
        self.queries: list[tuple[str, int]] = []

    def query_position(self, chrom: str, position: int) -> tuple[IndexedVcfRecord, ...]:
        normalized_chrom = chrom.removeprefix("chr")
        if normalized_chrom == "NC_000001.11":
            normalized_chrom = "1"
        self.queries.append((normalized_chrom, position))
        return tuple(
            record
            for record in self.records
            if record.chrom == normalized_chrom and record.position == position
        )

    def close(self) -> None:
        return None


class _FailingIndexedClinVarReader:
    def query_position(self, chrom: str, position: int) -> tuple[IndexedVcfRecord, ...]:
        raise IndexedSourceError(
            "unknown_contig",
            "contig is not present in indexed VCF",
            {"requested_chrom": chrom, "position": position},
        )

    def close(self) -> None:
        return None
