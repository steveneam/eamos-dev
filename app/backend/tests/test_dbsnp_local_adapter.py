from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services.dbsnp_local import (
    DBSNP_SOURCE_ID,
    DbSnpLocalError,
    DbSnpLocalProvenance,
    DbSnpLocalStore,
    parse_dbsnp_vcf,
)


def test_store_provenance_records_dbsnp_fixture_metadata() -> None:
    store = DbSnpLocalStore()
    provenance = store.provenance()

    assert provenance.source_id == DBSNP_SOURCE_ID
    assert provenance.source_version == "dbSNP latest_release GRCh38 GCF_000001405.40"
    assert provenance.assembly_accession == "GCF_000001405.40"
    assert provenance.file_date == "20260527"
    assert provenance.relative_path == "app/backend/app/fixtures/data_sources/dbsnp_tiny.vcf"
    assert provenance.checksum_algorithm == "sha256"
    assert re.fullmatch(r"[0-9a-f]{64}", provenance.checksum)
    assert provenance.record_id is None


def test_known_rsid_resolves_to_normalized_grch38_identity() -> None:
    lookup = DbSnpLocalStore().lookup_rsid("RS1645931040")

    assert lookup.available is True
    record = lookup.record
    assert record is not None
    assert record.rsid == "rs1645931040"
    assert record.chrom == "1"
    assert record.position == 68444869
    assert record.ref == "T"
    assert record.alts == ("C",)
    assert record.dbsnp_build_id == "155"
    assert record.is_multiallelic is False
    assert record.provenance.source_id == DBSNP_SOURCE_ID
    assert record.provenance.record_id == "rs1645931040"

    assert record.allele_identities[0].gnomad_variant_id == "1-68444869-T-C"
    assert record.allele_identities[0].genomic_hgvs == "NC_000001.11:g.68444869T>C"


def test_multiallelic_rsid_row_is_represented_without_single_allele_guess() -> None:
    lookup = DbSnpLocalStore().lookup_rsid("rs1801133")

    assert lookup.available is True
    record = lookup.record
    assert record is not None
    assert record.is_multiallelic is True
    assert record.ref == "G"
    assert record.alts == ("A", "C")
    assert [identity.gnomad_variant_id for identity in record.allele_identities] == [
        "1-11796321-G-A",
        "1-11796321-G-C",
    ]
    assert [identity.genomic_hgvs for identity in record.allele_identities] == [
        "NC_000001.11:g.11796321G>A",
        "NC_000001.11:g.11796321G>C",
    ]


def test_lookup_accepts_contig_aliases_at_adapter_boundary() -> None:
    store = DbSnpLocalStore()

    by_ncbi_contig = store.lookup_variant(
        chrom="NC_000001.11",
        position=68444869,
        ref="T",
        alt="C",
    )
    by_chr_contig = store.lookup_variant(chrom="chr1", position=68444869, ref="T", alt="C")
    at_chr = store.records_at("chr1", 68444869)
    at_ncbi = store.records_at("NC_000001.11", 68444869)

    assert by_ncbi_contig.available is True
    assert by_chr_contig.record == by_ncbi_contig.record
    assert at_chr == at_ncbi == (by_ncbi_contig.record,)


def test_no_hit_mismatch_and_invalid_queries_return_fail_closed_states() -> None:
    store = DbSnpLocalStore()

    no_hit = store.lookup_rsid("rs999999999")
    allele_mismatch = store.lookup_variant(chrom="1", position=68444869, ref="T", alt="A")
    contig_mismatch = store.lookup_variant(chrom="chr7", position=68444869, ref="T", alt="C")
    invalid = store.lookup_rsid("not-a-rsid")

    assert no_hit.available is False
    assert no_hit.unavailable_reason == "rsid_not_found"
    assert no_hit.warnings == ("dbsnp_local_rsid_not_found",)
    assert allele_mismatch.available is False
    assert allele_mismatch.unavailable_reason == "allele_mismatch"
    assert allele_mismatch.warnings == ("dbsnp_local_allele_mismatch",)
    assert contig_mismatch.available is False
    assert contig_mismatch.unavailable_reason == "contig_not_found"
    assert contig_mismatch.warnings == ("dbsnp_local_contig_not_found",)
    assert invalid.available is False
    assert invalid.unavailable_reason == "invalid_rsid"
    assert invalid.warnings == ("dbsnp_local_invalid_rsid",)


def test_parser_failures_are_structured_for_malformed_vcf_rows(tmp_path: Path) -> None:
    provenance = DbSnpLocalProvenance(
        source_id=DBSNP_SOURCE_ID,
        source_version="test",
        assembly_accession="GCF_000001405.40",
        file_date=None,
        checksum_algorithm="sha256",
        checksum="0" * 64,
        relative_path="bad.vcf",
    )

    bad_missing_rsid = tmp_path / "bad_missing_rsid.vcf"
    bad_missing_rsid.write_text(
        "\n".join(
            [
                "##fileformat=VCFv4.2",
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
                "1\t68444869\t.\tT\tC\t.\t.\tdbSNPBuildID=155",
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(DbSnpLocalError) as missing_rsid_exc:
        parse_dbsnp_vcf(bad_missing_rsid, provenance=provenance)

    bad_position = tmp_path / "bad_position.vcf"
    bad_position.write_text(
        "\n".join(
            [
                "##fileformat=VCFv4.2",
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
                "1\tbad\trs1645931040\tT\tC\t.\t.\tdbSNPBuildID=155",
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(DbSnpLocalError) as bad_position_exc:
        parse_dbsnp_vcf(bad_position, provenance=provenance)

    assert missing_rsid_exc.value.code == "malformed_dbsnp_vcf_row"
    assert missing_rsid_exc.value.details == {"row": 3}
    assert bad_position_exc.value.code == "malformed_dbsnp_vcf_row"
    assert bad_position_exc.value.details == {"row": 3, "position": "bad"}
