from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.gene_viewer_errors import (
    GENE_VIEWER_UNSUPPORTED_VARIANT,
    HTTP_UNPROCESSABLE_ENTITY,
    GeneViewerError,
)


@dataclass(frozen=True)
class VariantProjection:
    hgvs_c: str
    cds_pos: int
    ref: str
    alt: str
    cds_end: int | None = None
    variant_type: str = "substitution"
    hgvs_p: str | None = None
    genomic_hg38: str | None = None
    codon_number: int | None = None
    codon_offset: int | None = None
    aa_ref: str | None = None
    aa_alt: str | None = None
    classification: str = "unknown"

    @classmethod
    def from_hgvs_c(cls, hgvs_c: str) -> VariantProjection:
        substitution = re.fullmatch(
            r"c\.(?P<pos>\d+)(?P<ref>[ACGT]+)>(?P<alt>[ACGT]+)",
            hgvs_c,
            flags=re.IGNORECASE,
        )
        if substitution is not None:
            return cls(
                hgvs_c=hgvs_c,
                cds_pos=int(substitution.group("pos")),
                cds_end=int(substitution.group("pos")) + len(substitution.group("ref")) - 1,
                ref=substitution.group("ref").upper(),
                alt=substitution.group("alt").upper(),
                variant_type="substitution",
            )

        deletion = re.fullmatch(
            r"c\.(?P<start>\d+)(?:_(?P<end>\d+))?del(?P<ref>[ACGT]+)?",
            hgvs_c,
            flags=re.IGNORECASE,
        )
        if deletion is not None:
            start = int(deletion.group("start"))
            end = int(deletion.group("end") or start)
            return cls(
                hgvs_c=hgvs_c,
                cds_pos=start,
                cds_end=end,
                ref=(deletion.group("ref") or "").upper(),
                alt="",
                variant_type="deletion",
            )

        duplication = re.fullmatch(
            r"c\.(?P<start>\d+)(?:_(?P<end>\d+))?dup(?P<alt>[ACGT]+)?",
            hgvs_c,
            flags=re.IGNORECASE,
        )
        if duplication is not None:
            start = int(duplication.group("start"))
            end = int(duplication.group("end") or start)
            return cls(
                hgvs_c=hgvs_c,
                cds_pos=start,
                cds_end=end,
                ref="",
                alt=(duplication.group("alt") or "").upper(),
                variant_type="duplication",
            )

        insertion = re.fullmatch(
            r"c\.(?P<left>\d+)_(?P<right>\d+)ins(?P<alt>[ACGT]+)",
            hgvs_c,
            flags=re.IGNORECASE,
        )
        if insertion is not None:
            return cls(
                hgvs_c=hgvs_c,
                cds_pos=int(insertion.group("left")),
                cds_end=int(insertion.group("right")),
                ref="",
                alt=insertion.group("alt").upper(),
                variant_type="insertion",
            )

        delins = re.fullmatch(
            r"c\.(?P<start>\d+)(?:_(?P<end>\d+))?delins(?P<alt>[ACGT]+)",
            hgvs_c,
            flags=re.IGNORECASE,
        )
        if delins is not None:
            start = int(delins.group("start"))
            end = int(delins.group("end") or start)
            return cls(
                hgvs_c=hgvs_c,
                cds_pos=start,
                cds_end=end,
                ref="",
                alt=delins.group("alt").upper(),
                variant_type="delins",
            )

        raise GeneViewerError(
            code=GENE_VIEWER_UNSUPPORTED_VARIANT,
            message=(
                "Only simple coding substitution, deletion, duplication, insertion, "
                "and delins viewer overlays are supported."
            ),
            status_code=HTTP_UNPROCESSABLE_ENTITY,
        )
