from __future__ import annotations

import re


def _decode_cdna(gene: str, cdna: str) -> str | None:
    # Splice site: c.2405+1G>A or c.2405-3C>T
    m = re.match(r"c\.(\d+)([+-])(\d+)([A-Z])>([A-Z])", cdna)
    if m:
        pos, direction, offset, ref, alt = (
            m.group(1),
            m.group(2),
            m.group(3),
            m.group(4),
            m.group(5),
        )
        side = "into the intron after" if direction == "+" else "before the start of"
        n = int(offset)
        return (
            f"In the {gene} gene, a DNA letter changed at a splice site — the signal that tells "
            f"the cell where to cut and join sections of the genetic message. This sits "
            f"{n} position{'s' if n != 1 else ''} {side} coding position {pos}. "
            f"Disrupting this signal likely causes the wrong sections to be included when the "
            f"protein is assembled, producing a faulty or absent {gene} protein."
        )

    # Substitution: c.353G>A
    m = re.match(r"c\.(\d+)([A-Z])>([A-Z])$", cdna)
    if m:
        pos, ref, alt = m.group(1), m.group(2), m.group(3)
        return (
            f"In the {gene} gene, a single DNA letter was swapped at position {pos} — "
            f"a {ref} changed to a {alt}. This one-letter change alters a single amino acid "
            f"in the protein, which may affect how well it functions. The protein is still "
            f"produced but carries this change at that position."
        )

    # Multi-base deletion: c.123_125del
    m = re.match(r"c\.(\d+)_(\d+)del", cdna)
    if m:
        start, end = int(m.group(1)), int(m.group(2))
        count = end - start + 1
        if count % 3 != 0:
            frame_note = (
                f"This deletion is not a multiple of three, so it shifts the reading frame — "
                f"the protein is built incorrectly from that point onward, almost certainly "
                f"producing a shortened or non-functional {gene} protein."
            )
        else:
            frame_note = (
                f"This deletion removes {count} letters, a multiple of three, so the reading "
                f"frame is preserved — the protein is produced but is missing the corresponding amino acids."
            )
        return (
            f"In the {gene} gene, {count} DNA letters were deleted between positions {start} and {end}. "
            f"{frame_note}"
        )

    # Single-base deletion: c.2299delG or c.2299del
    m = re.match(r"c\.(\d+)del[A-Z]?$", cdna)
    if m:
        pos = m.group(1)
        return (
            f"In the {gene} gene, a single DNA letter was deleted at position {pos}. "
            f"Because DNA is read in groups of three letters, removing one letter shifts the "
            f"entire reading frame. The protein is built incorrectly from that point onward — "
            f"almost certainly producing a shortened or non-functional {gene} protein."
        )

    # Insertion: c.123_124insATCG
    m = re.match(r"c\.(\d+)_(\d+)ins([A-Z]+)", cdna)
    if m:
        start, end, inserted = m.group(1), m.group(2), m.group(3)
        count = len(inserted)
        if count % 3 != 0:
            frame_note = (
                "This insertion is not a multiple of three, so it shifts the reading frame — "
                "the protein is built incorrectly from that point onward."
            )
        else:
            frame_note = (
                f"This insertion adds {count} letters, a multiple of three, so the reading "
                f"frame is preserved — the protein gains the corresponding extra amino acids."
            )
        return (
            f"In the {gene} gene, {count} DNA letter{'s were' if count != 1 else ' was'} "
            f"inserted between positions {start} and {end}. {frame_note}"
        )

    # Duplication: c.123dupA or c.123_125dup
    m = re.match(r"c\.(\d+)(?:_(\d+))?dup", cdna)
    if m:
        start, end = m.group(1), m.group(2)
        if end:
            count = int(end) - int(start) + 1
            desc = f"{count} DNA letters between positions {start} and {end} were duplicated"
        else:
            desc = f"a single DNA letter at position {start} was duplicated"
        return (
            f"In the {gene} gene, {desc}. This adds extra genetic material and typically "
            f"shifts the reading frame, producing a faulty or absent {gene} protein."
        )

    return None


def _decode_protein(gene: str, protein_change: str) -> str | None:
    # Frameshift: p.Glu767Serfs*21
    m = re.match(r"p\.([A-Za-z]{3})(\d+)([A-Za-z]{3})fs\*(\d+)", protein_change)
    if m:
        pos, stop = m.group(2), m.group(4)
        return (
            f"In the {gene} gene, a small deletion or insertion shifted the reading frame near "
            f"amino acid position {pos}. The protein is built incorrectly for {stop} amino acids "
            f"after that point, then hits an early stop signal — almost certainly producing a "
            f"shortened, non-functional {gene} protein."
        )

    # Splice: p.(splice)
    if re.search(r"splice", protein_change, re.IGNORECASE):
        return (
            f"In the {gene} gene, a variant disrupted a splice site. The exact protein "
            f"consequence is uncertain, but the change likely produces a faulty or absent "
            f"{gene} protein."
        )

    # Missense: p.Arg436Trp
    m = re.match(r"p\.([A-Za-z]{3})(\d+)([A-Za-z]{3})$", protein_change)
    if m:
        aa1, pos, aa2 = m.group(1), m.group(2), m.group(3)
        return (
            f"In the {gene} gene, a single amino acid changed at position {pos} — "
            f"{aa1} was replaced by {aa2}. The protein is still produced but carries this "
            f"change, which may affect how well it functions."
        )

    return None


def decode_variant(
    gene: str | None,
    transcript_hgvs: str | None,
    protein_change: str | None,
) -> str | None:
    if not gene:
        return None

    cdna: str | None = None
    if transcript_hgvs and ":" in transcript_hgvs:
        cdna = transcript_hgvs.split(":", 1)[1]

    if cdna:
        result = _decode_cdna(gene, cdna)
        if result:
            return result

    if protein_change:
        result = _decode_protein(gene, protein_change)
        if result:
            return result

    return None
