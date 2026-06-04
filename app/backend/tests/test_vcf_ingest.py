from __future__ import annotations

import gzip

from app.services.vcf_ingest import parse_vcf_text, parse_vcf_upload_bytes


def test_parse_vcf_text_recovers_whitespace_rows_and_normalizes_variant_fields() -> None:
    parsed = parse_vcf_text(
        "\ufeff##fileformat=VCFv4.2\r\n"
        "#CHROM POS ID REF ALT QUAL FILTER INFO FORMAT proband\r\n"
        "chr1  10  .  a  c,g  .  PASS  GENE=brca1;HGVS_C=c.1A>C;AF=0.01,0.2  GT  0/1\r\n"
    )

    assert parsed.skipped_rows == 0
    assert len(parsed.variants) == 2
    first, second = parsed.variants
    assert first.query == "1-10-A-C"
    assert first.gene == "BRCA1"
    assert first.variant == "c.1A>C"
    assert first.info_af == 0.01
    assert first.sample_id == "proband"
    assert first.genotype == "0/1"
    assert "whitespace_delimited_vcf_row_recovered" in first.warnings
    assert "multiallelic_alt_split" in second.warnings
    assert second.query == "1-10-A-G"
    assert second.info_af == 0.2


def test_parse_vcf_text_skips_unrepairable_rows_with_file_warning() -> None:
    parsed = parse_vcf_text("not enough fields\n")

    assert parsed.variants == []
    assert parsed.skipped_rows == 1
    assert parsed.warnings == ["malformed_vcf_row:line_1"]


def test_parse_vcf_upload_bytes_accepts_gzip_payload() -> None:
    payload = gzip.compress(
        b"##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        b"chr7\t117509068\t.\tc\tt\t.\tPASS\tGENE=CFTR;AF=0.03\n"
    )

    parsed = parse_vcf_upload_bytes(payload, filename="sample.vcf.gz")

    assert len(parsed.variants) == 1
    assert parsed.variants[0].query == "7-117509068-C-T"
    assert parsed.variants[0].gene == "CFTR"
    assert parsed.variants[0].info_af == 0.03
