"""Typed, bounded deterministic variant-mention grammar (L1-L3)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.schemas.paper_variants import PaperEvidenceSpanV2, PaperVariantMentionV2
from app.services.paper_extract.segment import (
    SectionSpan,
    bounded_quote,
    section_at,
    segment_page,
    sentence_window,
)

_ACCESSION = r"(?:N[CMRTP]_[0-9]{4,12}(?:\.[0-9]{1,4})?|ENST[0-9]{6,12}(?:\.[0-9]{1,4})?|LRG_[0-9]{1,10}(?:t[0-9]{1,4})?)"
_DNA_POSITION = (
    r"(?:[*-]?[0-9]{1,12}(?:[+-][0-9]{1,8})?)(?:_(?:[*-]?[0-9]{1,12}(?:[+-][0-9]{1,8})?))?"
)
_DNA_CHANGE = r"(?:[ACGTUN]{1,64}>[ACGTUN]{1,64}|delins[ACGTUN]{1,128}|del[ACGTUN]{0,128}|dup[ACGTUN]{0,128}|ins[ACGTUN]{1,128}|=)"
_DNA_HGVS = rf"[cgnrm]\.({_DNA_POSITION})({_DNA_CHANGE})"
_AA = r"(?:Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val|Ter|[ACDEFGHIKLMNPQRSTVWY*])"
_PROTEIN_FRAMESHIFT = r"fs(?:(?:Ter|\*)[0-9]{1,9})?"
_PROTEIN_SIMPLE = (
    rf"{_AA}[0-9]{{1,9}}(?:{_AA}(?:{_PROTEIN_FRAMESHIFT})?|=|{_PROTEIN_FRAMESHIFT}|del|dup)"
)
_PROTEIN_RANGE = (
    rf"{_AA}[0-9]{{1,9}}_{_AA}[0-9]{{1,9}}(?:delins{_AA}{{1,32}}|del|dup|ins{_AA}{{1,32}})"
)
_PROTEIN_BODY = rf"(?:{_PROTEIN_RANGE}|{_PROTEIN_SIMPLE})"
_PROTEIN_HGVS = rf"p\.(?:\({_PROTEIN_BODY}\)|{_PROTEIN_BODY})"

_STRICT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "hgvs",
        re.compile(
            rf"(?<![\w.])(?:(?P<accession>{_ACCESSION})(?:\((?P<qualified_gene>[A-Z][A-Z0-9-]{{1,14}})\))?:)?(?P<hgvs>{_DNA_HGVS})(?![\w])"
        ),
    ),
    ("protein", re.compile(rf"(?<![\w.])(?P<hgvs>{_PROTEIN_HGVS})(?![\w])")),
    ("rsid", re.compile(r"(?<![A-Za-z0-9])(?P<hgvs>rs[0-9]{3,12})(?![A-Za-z0-9])", re.I)),
    (
        "legacy_splice",
        re.compile(
            r"(?<![A-Za-z0-9])(?P<hgvs>IVS[0-9]{1,3}[+-][0-9]{1,4}[ACGT]>[ACGT])(?![A-Za-z0-9])",
            re.I,
        ),
    ),
    (
        "legacy_protein",
        re.compile(rf"(?<![\w.])(?P<hgvs>(?:{_AA})[0-9]{{1,5}}(?:{_AA}))(?![\w])"),
    ),
)

_RECOVERY_GAP = r"[ \t\r\n]{0,8}"
_RECOVERY_DNA_RE = re.compile(
    rf"(?<![\w.])(?:(?P<accession>{_ACCESSION}){_RECOVERY_GAP}(?:\({_RECOVERY_GAP}(?P<qualified_gene>[A-Z][A-Z0-9-]{{1,14}}){_RECOVERY_GAP}\))?{_RECOVERY_GAP}:{_RECOVERY_GAP})?"
    rf"(?P<hgvs>[cgnrm]{_RECOVERY_GAP}\.{_RECOVERY_GAP}[*-]?{_RECOVERY_GAP}[0-9]{{1,12}}(?:{_RECOVERY_GAP}[+-]{_RECOVERY_GAP}[0-9]{{1,8}})?(?:{_RECOVERY_GAP}_{_RECOVERY_GAP}[*-]?{_RECOVERY_GAP}[0-9]{{1,12}}(?:{_RECOVERY_GAP}[+-]{_RECOVERY_GAP}[0-9]{{1,8}})?)?{_RECOVERY_GAP}"
    rf"(?:[ACGTUN]{{1,64}}{_RECOVERY_GAP}>{_RECOVERY_GAP}[ACGTUN]{{1,64}}|delins{_RECOVERY_GAP}[ACGTUN]{{1,128}}|del{_RECOVERY_GAP}[ACGTUN]{{0,128}}|dup{_RECOVERY_GAP}[ACGTUN]{{0,128}}|ins{_RECOVERY_GAP}[ACGTUN]{{1,128}}|=))(?![\w])",
    re.I,
)
_TRANSCRIPT_RE = re.compile(_ACCESSION)
_GENE_RE = re.compile(r"\b[A-Z][A-Z0-9-]{1,14}\b")
_GENE_STOP = {
    "ABSTRACT",
    "BACKGROUND",
    "BODY",
    "CASE",
    "CDNA",
    "DNA",
    "DOI",
    "FIGURE",
    "HGVS",
    "METHODS",
    "PMID",
    "RESULTS",
    "RNA",
    "TABLE",
    "WILD",
}
_CONSTRUCT_HINTS = ("construct", "mutagenesis", "mutant", "engineered", "transfected")
_RESCUE_HINTS = ("engineered rescue", "rescue variant", "rescued by")
_FAMILY_HINTS = ("segregat", "pedigree", "kindred", "family", "sibling", "parental")
_CASE_HINTS = ("proband", "patient", "case", "carrier")
_CLINICAL_HINTS = ("clinical", "pathogenic", "diagnosed", "homozygous", "heterozygous")
_COMPARATOR_HINTS = ("wild-type", "wild type", "background", "comparator", "compared with")
_MAX_MENTION_CHARACTERS = 180


@dataclass(frozen=True, slots=True)
class DetectedMention:
    mention: PaperVariantMentionV2
    canonical_notation: str


def extract_page_mentions(
    *, document_id: str, page_number: int, text: str
) -> list[PaperVariantMentionV2]:
    return [
        record.mention
        for record in extract_page_records(
            document_id=document_id,
            page_number=page_number,
            text=text,
        )
    ]


def extract_page_records(
    *,
    document_id: str,
    page_number: int,
    text: str,
    max_records: int | None = None,
) -> list[DetectedMention]:
    if max_records is not None and max_records < 1:
        raise ValueError("max_records must be positive")
    sections = segment_page(text)
    raw_hits: list[tuple[int, int, str, str, str | None, str | None]] = []
    occupied: list[tuple[int, int]] = []
    for kind, pattern in _STRICT_PATTERNS:
        pattern_hits = 0
        for match in pattern.finditer(text):
            start, end = match.span()
            if end - start > _MAX_MENTION_CHARACTERS:
                continue
            if _overlaps(start, end, occupied):
                continue
            occupied.append((start, end))
            raw_hits.append(
                (
                    start,
                    end,
                    kind,
                    _canonicalize(match.group(0)),
                    match.groupdict().get("accession"),
                    match.groupdict().get("qualified_gene"),
                )
            )
            pattern_hits += 1
            if max_records is not None and pattern_hits >= max_records:
                break

    recovery_hits = 0
    for match in _RECOVERY_DNA_RE.finditer(text):
        start, end = match.span()
        if end - start > _MAX_MENTION_CHARACTERS:
            continue
        if _overlaps(start, end, occupied):
            continue
        occupied.append((start, end))
        raw_hits.append(
            (
                start,
                end,
                "recovery",
                _canonicalize(match.group(0)),
                match.group("accession"),
                match.group("qualified_gene"),
            )
        )
        recovery_hits += 1
        if max_records is not None and recovery_hits >= max_records:
            break

    records: list[DetectedMention] = []
    for start, end, kind, canonical, accession, qualified_gene in sorted(raw_hits):
        section = section_at(sections, start)
        exact = text[start:end]
        transcript_evidence = _transcript_evidence(text, start, end, section, direct=accession)
        gene_evidence = _gene_evidence(
            text,
            start,
            end,
            section,
            direct=qualified_gene,
        )
        context = _biological_context(text, start, end, section)
        layer = "l2_recovery" if kind == "recovery" else "l1_structured"
        if context == "bibliography_only" or (not gene_evidence and not transcript_evidence):
            layer = "l3_inventory" if kind != "recovery" else layer
        notation_type = _notation_type(canonical, kind)
        mention_id = _mention_id(
            document_id=document_id,
            page_number=page_number,
            start=start,
            end=end,
            canonical=canonical,
        )
        warnings: list[str] = []
        if not gene_evidence and notation_type not in {"rsid", "genomic", "mitochondrial"}:
            warnings.append("gene_association_unresolved")
        if context == "bibliography_only":
            warnings.append("bibliography_only_excluded_from_resolution")
        mention = PaperVariantMentionV2(
            mention_id=mention_id,
            notation_type=notation_type,
            biological_context=context,
            extraction_layer=layer,
            confidence=_confidence(layer, gene_evidence, transcript_evidence, context),
            span=PaperEvidenceSpanV2(
                document_id=document_id,
                page_number=page_number,
                section=section.label,
                start_character=start,
                end_character=end,
                exact_text=exact,
                bounded_quote=bounded_quote(text, start, end, section),
            ),
            gene_evidence=gene_evidence,
            transcript_evidence=transcript_evidence,
            warnings=warnings,
        )
        records.append(DetectedMention(mention=mention, canonical_notation=canonical))
        if max_records is not None and len(records) >= max_records:
            break
    return records


def _canonicalize(surface: str) -> str:
    normalized = surface.translate(
        str.maketrans({"\u2010": "-", "\u2011": "-", "\u2212": "-", "\u2192": ">"})
    )
    compact = re.sub(r"\s+", "", normalized)
    prefix, separator, notation = compact.rpartition(":")
    if not separator:
        notation = compact
    if notation.lower().startswith("rs"):
        notation = "rs" + notation[2:]
    elif len(notation) >= 2 and notation[0].lower() in "cgnrmp" and notation[1] == ".":
        notation = notation[0].lower() + notation[1:]
        dna = re.fullmatch(
            r"(?P<position>[cgnrm]\.[*0-9+_-]+)(?P<change>[A-Za-z]+(?:>[A-Za-z]+)?|=)",
            notation,
            re.I,
        )
        if dna:
            change = dna.group("change")
            substitution = re.fullmatch(r"([ACGTUN]+)>([ACGTUN]+)", change, re.I)
            if substitution:
                change = f"{substitution.group(1).upper()}>{substitution.group(2).upper()}"
            else:
                operation = re.fullmatch(r"(delins|del|dup|ins)([ACGTUN]*)", change, re.I)
                if operation:
                    change = operation.group(1).lower() + operation.group(2).upper()
            notation = dna.group("position") + change
    elif notation.upper().startswith("IVS"):
        notation = notation.upper()
    return f"{prefix}:{notation}" if separator else notation


def _notation_type(canonical: str, kind: str) -> str:
    notation = canonical.split(":")[-1]
    if kind == "rsid":
        return "rsid"
    if kind.startswith("legacy"):
        return "legacy"
    prefix = notation[:2].lower()
    return {
        "c.": "cdna",
        "g.": "genomic",
        "n.": "genomic",
        "r.": "rna",
        "m.": "mitochondrial",
        "p.": "protein",
    }.get(prefix, "unknown")


def _gene_evidence(
    text: str,
    start: int,
    end: int,
    section: SectionSpan,
    *,
    direct: str | None,
) -> list[str]:
    if direct:
        return [direct]
    sentence_start, sentence_end = sentence_window(text, start, end, section)
    candidates: list[tuple[int, str]] = []
    for match in _GENE_RE.finditer(text, sentence_start, sentence_end):
        token = match.group(0)
        if token in _GENE_STOP or _TRANSCRIPT_RE.fullmatch(token):
            continue
        if token.startswith("RS") and token[2:].isdigit():
            continue
        if re.fullmatch(r"[ACDEFGHIKLMNPQRSTVWY][0-9]{1,5}[ACDEFGHIKLMNPQRSTVWY]", token):
            continue
        absolute = sentence_start + match.start()
        distance = min(abs(absolute - start), abs(absolute - end))
        if distance <= 180:
            candidates.append((distance, token))
    if not candidates:
        return []
    candidates.sort(key=lambda item: item[0])
    return [candidates[0][1]]


def _transcript_evidence(
    text: str,
    start: int,
    end: int,
    section: SectionSpan,
    *,
    direct: str | None,
) -> list[str]:
    if direct:
        return [direct]
    sentence_start, sentence_end = sentence_window(text, start, end, section)
    values: list[str] = []
    for match in _TRANSCRIPT_RE.finditer(text[sentence_start:sentence_end]):
        absolute = sentence_start + match.start()
        if min(abs(absolute - start), abs(absolute - end)) <= 180:
            values.append(match.group(0))
    return list(dict.fromkeys(values))[:16]


def _biological_context(text: str, start: int, end: int, section: SectionSpan) -> str:
    if section.label == "References":
        return "bibliography_only"
    sentence_start, sentence_end = sentence_window(text, start, end, section)
    context = text[sentence_start:sentence_end].lower()
    if any(hint in context for hint in _RESCUE_HINTS):
        return "engineered_rescue"
    if any(hint in context for hint in _CONSTRUCT_HINTS):
        return "experimental_construct"
    if any(hint in context for hint in _FAMILY_HINTS):
        return "family_segregation"
    if any(hint in context for hint in _CASE_HINTS):
        return "case_or_proband"
    if any(hint in context for hint in _COMPARATOR_HINTS):
        return "comparator_or_background"
    if any(hint in context for hint in _CLINICAL_HINTS):
        return "clinical_allele"
    return "unknown"


def _mention_id(*, document_id: str, page_number: int, start: int, end: int, canonical: str) -> str:
    material = f"{document_id}\0{page_number}\0{start}\0{end}\0{canonical}".encode("utf-8")
    return f"mention-{hashlib.sha256(material).hexdigest()[:24]}"


def _confidence(
    layer: str,
    genes: list[str],
    transcripts: list[str],
    context: str,
) -> float:
    score = {"l1_structured": 0.90, "l2_recovery": 0.76, "l3_inventory": 0.62}[layer]
    if genes:
        score += 0.04
    if transcripts:
        score += 0.04
    if context == "bibliography_only":
        score = min(score, 0.75)
    return min(score, 0.99)


def _overlaps(start: int, end: int, occupied: list[tuple[int, int]]) -> bool:
    return any(start < other_end and other_start < end for other_start, other_end in occupied)
