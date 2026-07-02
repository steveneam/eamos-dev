from __future__ import annotations

import re
from typing import Any

AA3_TO_AA1 = {
    "Ala": "A",
    "Arg": "R",
    "Asn": "N",
    "Asp": "D",
    "Cys": "C",
    "Gln": "Q",
    "Glu": "E",
    "Gly": "G",
    "His": "H",
    "Ile": "I",
    "Leu": "L",
    "Lys": "K",
    "Met": "M",
    "Phe": "F",
    "Pro": "P",
    "Ser": "S",
    "Thr": "T",
    "Trp": "W",
    "Tyr": "Y",
    "Val": "V",
    "Ter": "*",
}
DNA_COMPLEMENT = str.maketrans("ACGTacgt", "TGCAtgca")


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def versionless(identifier: str) -> str:
    return identifier.split(".", 1)[0] if identifier else ""


def versioned_id(transcript: dict[str, Any]) -> str:
    transcript_id = str(transcript.get("id") or "")
    version = transcript.get("version")
    if transcript_id and version:
        return f"{transcript_id}.{version}"
    return transcript_id


def transcript_aliases(
    *,
    transcript: dict[str, Any],
    requested: str | None,
) -> list[str]:
    aliases: list[str] = []
    for alias in [requested, versioned_id(transcript), str(transcript.get("display_name") or "")]:
        if alias and alias not in aliases:
            aliases.append(alias)
    for mane in as_list(transcript.get("MANE")):
        if not isinstance(mane, dict):
            continue
        refseq_match = str(mane.get("refseq_match") or "")
        if refseq_match and refseq_match not in aliases:
            aliases.append(refseq_match)
        mane_type = str(mane.get("type") or "")
        if mane_type == "MANE_Select" and "MANE Select" not in aliases:
            aliases.append("MANE Select")
    return aliases


def utr_length(transcript: dict[str, Any], utr_type: str) -> int | None:
    total = 0
    found = False
    for utr in as_list(transcript.get("UTR")):
        if not isinstance(utr, dict) or utr.get("type") != utr_type:
            continue
        start = int_or_none(utr.get("start"))
        end = int_or_none(utr.get("end"))
        if start is None or end is None:
            continue
        found = True
        total += abs(end - start) + 1
    return total if found else None


def protein_hgvs_from_variant_validator(variant_payload: dict[str, Any]) -> str | None:
    consequences = variant_payload.get("hgvs_predicted_protein_consequence")
    if not isinstance(consequences, dict):
        return None
    raw = str(consequences.get("tlr") or consequences.get("slr") or "")
    if not raw:
        return None
    hgvs_p = raw.split(":", 1)[1] if ":" in raw else raw
    return hgvs_p.replace("p.(", "p.").removesuffix(")")


def protein_change_parts(hgvs_p: str | None) -> tuple[int | None, str | None, str | None]:
    if hgvs_p is None:
        return None, None, None
    match = re.fullmatch(
        r"p\.(?P<ref>[A-Z][a-z]{2}|[A-Z*])(?P<pos>\d+)(?P<alt>[A-Z][a-z]{2}|[A-Z*])",
        hgvs_p,
    )
    if match is None:
        return None, None, None
    return (
        int(match.group("pos")),
        aa_to_one_letter(match.group("ref")),
        aa_to_one_letter(match.group("alt")),
    )


def aa_to_one_letter(value: str) -> str:
    return AA3_TO_AA1.get(value, value)


def clean_dna(sequence: str) -> str:
    return re.sub(r"[^ACGTNacgtn]", "", sequence).upper()


def reverse_complement(sequence: str) -> str:
    return sequence.translate(DNA_COMPLEMENT)[::-1]


def dedupe_warnings(warnings: list[str]) -> list[str]:
    deduped: list[str] = []
    for warning in warnings:
        if warning not in deduped:
            deduped.append(warning)
    return deduped
