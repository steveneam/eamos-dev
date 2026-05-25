from __future__ import annotations

import pytest

from app.services.gene_viewer import TranscriptExon, VariantProjection
from app.services.variant_applied_model import build_protein_product_effect


@pytest.mark.parametrize(
    "hgvs_p,expected_kind,expected_length",
    [
        ("p.Glu2del", "inframe_deletion", 3),
        ("p.Glu2dup", "inframe_duplication", 5),
        ("p.Glu2_Lys3insArg", "inframe_insertion", 5),
        ("p.Glu2delinsVal", "delins", 4),
        ("p.Ter5Glnext*3", "stop_lost", 7),
    ],
)
def test_protein_product_model_covers_non_truncating_variant_classes(
    hgvs_p: str,
    expected_kind: str,
    expected_length: int,
) -> None:
    product = build_protein_product_effect(
        variant=VariantProjection(
            hgvs_c="c.4G>T",
            cds_pos=4,
            ref="G",
            alt="T",
            hgvs_p=hgvs_p,
            codon_number=2,
        ),
        allele_mode="variant",
        reference_protein_length=4,
        exons=(TranscriptExon(number=1, cds_start=1, cds_end=12, sequence="ATGGAAAAGTAA"),),
    )

    assert product.consequence == expected_kind
    assert product.effective_protein_length == expected_length
    assert product.truncates_protein is False
