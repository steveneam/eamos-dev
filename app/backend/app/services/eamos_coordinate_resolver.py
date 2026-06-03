from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import gzip
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import unquote

from app.services.reference_genome import ReferenceGenomeStoreError, TwoBitReferenceGenomeStore
from app.services.sequence_context import NC_CHROMOSOME_ACCESSIONS, genomic_variant_id_to_refseq_hgvs

DEFAULT_MANE_GFF_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "bio_assets"
    / "transcripts"
    / "MANE.GRCh38.v1.5.refseq_genomic.gff.gz"
)
DEFAULT_REFSEQ_GFF_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "bio_assets"
    / "transcripts"
    / "GCF_000001405.40_GRCh38.p14_genomic.gff.gz"
)
_DNA_BASES = frozenset("ACGT")
_COMPLEMENT = str.maketrans("ACGT", "TGCA")


class EamosCoordinateResolverError(ValueError):
    """Structured local coordinate resolver error."""

    def __init__(
        self,
        code: str,
        message: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


@dataclass(frozen=True)
class EamosCoordinateResolution:
    gene: str
    transcript: str
    cdna: str
    chrom: str
    pos: int
    ref: str
    alt: str
    genomic_hg38: str
    genomic_hgvs: str | None
    source: str
    confidence: str = "high"
    accession: str | None = None
    clinvar_variation_id: str | None = None
    canonical_spdi: str | None = None
    provenance: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def vcf(self) -> dict[str, str | int]:
        return {
            "CHROM": self.chrom,
            "POS": self.pos,
            "REF": self.ref,
            "ALT": self.alt,
        }

    def to_catalog_row(self) -> dict[str, object]:
        return {
            "gene": self.gene,
            "transcript": self.transcript,
            "cdna": self.cdna,
            "chrom": self.chrom,
            "pos": self.pos,
            "ref": self.ref,
            "alt": self.alt,
            "genomic_hg38": self.genomic_hg38,
            "genomic_hgvs": self.genomic_hgvs,
            "source": self.source,
            "confidence": self.confidence,
            "accession": self.accession,
            "clinvar_variation_id": self.clinvar_variation_id,
            "canonical_spdi": self.canonical_spdi,
            "provenance": list(self.provenance),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class _TranscriptExon:
    number: int
    transcript_start: int
    transcript_end: int
    genomic_start: int
    genomic_end: int
    sequence: str


@dataclass(frozen=True)
class _TranscriptRecord:
    gene: str
    transcript: str
    chrom: str
    strand: str
    exons: tuple[_TranscriptExon, ...]
    cds_transcript_start: int
    cds_transcript_end: int
    transcript_aliases: tuple[str, ...] = ()
    source: str = "eamos_transcript_model"


@dataclass(frozen=True)
class _MappedCoordinate:
    position: int
    exon: _TranscriptExon
    transcript_base: str | None
    is_intronic: bool = False


@dataclass(frozen=True)
class _CdnaCoordinateToken:
    prefix: str | None
    number: int
    sign: str | None = None
    offset: int | None = None


@dataclass(frozen=True)
class _CdnaEvent:
    kind: str
    start: _CdnaCoordinateToken
    end: _CdnaCoordinateToken | None = None
    ref: str | None = None
    alt: str | None = None
    inserted: str | None = None
    deleted: str | None = None


class _ReferenceStore(Protocol):
    def get_sequence(self, chrom: str, start: int, end: int, build: str | None = None):
        """Return a ReferenceWindow-like object with a sequence attribute."""

    def close(self) -> None:
        """Close backing resources."""


class EamosLocalCoordinateResolver:
    """Resolve variants to GRCh38 VCF coordinates with Eamos-owned local sources.

    The resolver is intentionally local-first:
    1. local MANE/RefSeq transcript geometry plus local/reference-backed allele checks;
    2. optional explicit Eamos snapshot fallback when supplied for regression fixtures;
    3. no live API calls.

    External providers can validate this output in separate workflows, but they
    are not the first gate for search-bar or batch coordinate identity.
    """

    def __init__(
        self,
        *,
        mane_gff_path: Path | None = DEFAULT_MANE_GFF_PATH,
        refseq_gff_path: Path | None = DEFAULT_REFSEQ_GFF_PATH,
        coordinate_catalog_path: Path | None = None,
        reference_store_factory: Callable[[], _ReferenceStore] | None = None,
    ) -> None:
        self.coordinate_catalog_path = coordinate_catalog_path
        self.mane_gff_path = mane_gff_path
        self.refseq_gff_path = refseq_gff_path
        self.reference_store_factory = reference_store_factory or _default_reference_store
        self._catalog = _load_coordinate_catalog(coordinate_catalog_path)
        self._transcripts = _merge_transcript_sources(
            _load_mane_gff_transcript_models(mane_gff_path),
            _load_mane_gff_transcript_models(refseq_gff_path),
        )
        self._reference_store: _ReferenceStore | None = None

    def resolve(
        self,
        *,
        gene: str,
        cdna: str,
        transcript: str | None = None,
        accession: str | None = None,
        clinvar_variation_id: str | None = None,
    ) -> EamosCoordinateResolution | None:
        normalized_gene = gene.strip().upper()
        normalized_cdna = _normalize_cdna(cdna)
        normalized_transcript = transcript.strip() if transcript else None

        transcript_record = self._transcript_record(normalized_gene, normalized_transcript)
        if transcript_record is not None:
            resolved = self._resolve_from_transcript_model(transcript_record, normalized_cdna)
            if resolved is not None:
                return resolved

        return self._catalog_lookup(
            gene=normalized_gene,
            cdna=normalized_cdna,
            transcript=normalized_transcript,
            accession=accession,
            clinvar_variation_id=clinvar_variation_id,
        )

    def _catalog_lookup(
        self,
        *,
        gene: str,
        cdna: str,
        transcript: str | None,
        accession: str | None,
        clinvar_variation_id: str | None,
    ) -> EamosCoordinateResolution | None:
        keys = [
            _catalog_key(gene, transcript, cdna),
            _catalog_key(gene, None, cdna),
        ]
        if accession:
            keys.append(f"accession:{_normalize_accession(accession)}")
        if clinvar_variation_id:
            keys.append(f"variation:{_digits(clinvar_variation_id)}")

        for key in keys:
            row = self._catalog.get(key)
            if row is not None:
                return _resolution_from_catalog_row(row)
        return None

    def _transcript_record(
        self,
        gene: str,
        transcript: str | None,
    ) -> _TranscriptRecord | None:
        candidates = self._transcripts.get(gene, ())
        if not candidates:
            return None
        if transcript is None:
            return candidates[0]

        requested = _versionless(transcript)
        for candidate in candidates:
            aliases = (candidate.transcript, *candidate.transcript_aliases)
            if any(_versionless(alias) == requested for alias in aliases):
                return candidate
        return None

    def _resolve_from_transcript_model(
        self,
        record: _TranscriptRecord,
        cdna: str,
    ) -> EamosCoordinateResolution | None:
        event = _parse_cdna_event(cdna)
        if event is None:
            return None

        start = self._map_cdna_coordinate(record, event.start)
        if start is None:
            return None

        if event.kind == "substitution":
            return self._resolve_substitution(record, cdna, event, start)
        if event.kind == "deletion":
            end = self._map_cdna_coordinate(record, event.end or event.start)
            return self._resolve_deletion(record, cdna, start, end)
        if event.kind == "duplication":
            end = self._map_cdna_coordinate(record, event.end or event.start)
            return self._resolve_duplication(record, cdna, start, end)
        if event.kind == "insertion":
            end = self._map_cdna_coordinate(record, event.end or event.start)
            return self._resolve_insertion(record, cdna, start, end, event.inserted or "")
        if event.kind == "delins":
            end = self._map_cdna_coordinate(record, event.end or event.start)
            return self._resolve_delins(record, cdna, start, end, event.inserted or "")
        return None

    def _resolve_substitution(
        self,
        record: _TranscriptRecord,
        cdna: str,
        event: _CdnaEvent,
        mapped: _MappedCoordinate,
    ) -> EamosCoordinateResolution | None:
        if event.ref is None or event.alt is None:
            return None

        genomic_ref = _transcript_sequence_to_genomic(event.ref, record.strand)
        genomic_alt = _transcript_sequence_to_genomic(event.alt, record.strand)
        warnings: list[str] = []
        provenance = [record.source]

        if not mapped.is_intronic and mapped.transcript_base is not None:
            if mapped.transcript_base != event.ref:
                return None

        observed_ref = self._reference_base(record.chrom, mapped.position)
        if observed_ref is None:
            warnings.append("eamos_reference_base_unavailable")
            if mapped.is_intronic:
                return None
        elif observed_ref != genomic_ref:
            return None
        else:
            provenance.append("ucsc_hg38_2bit_reference_base")

        return self._build_resolution(
            record=record,
            cdna=cdna,
            pos=mapped.position,
            ref=genomic_ref,
            alt=genomic_alt,
            provenance=provenance,
            warnings=warnings,
        )

    def _resolve_deletion(
        self,
        record: _TranscriptRecord,
        cdna: str,
        start: _MappedCoordinate,
        end: _MappedCoordinate | None,
    ) -> EamosCoordinateResolution | None:
        if end is None:
            return None
        interval = _genomic_interval(start, end)
        deleted = self._reference_sequence(record.chrom, interval[0], interval[1])
        if deleted is None:
            return None
        if interval[0] <= 1:
            return None
        anchor_pos = interval[0] - 1
        anchor = self._reference_base(record.chrom, anchor_pos)
        if anchor is None:
            return None
        return self._build_resolution(
            record=record,
            cdna=cdna,
            pos=anchor_pos,
            ref=anchor + deleted,
            alt=anchor,
            provenance=[record.source, "ucsc_hg38_2bit_reference_sequence"],
        )

    def _resolve_duplication(
        self,
        record: _TranscriptRecord,
        cdna: str,
        start: _MappedCoordinate,
        end: _MappedCoordinate | None,
    ) -> EamosCoordinateResolution | None:
        if end is None:
            return None
        interval = _genomic_interval(start, end)
        duplicated = self._reference_sequence(record.chrom, interval[0], interval[1])
        if duplicated is None:
            return None
        if record.strand == "-":
            anchor_pos = interval[0] - 1
        else:
            anchor_pos = interval[1]
        if anchor_pos < 1:
            return None
        anchor = self._reference_base(record.chrom, anchor_pos)
        if anchor is None:
            return None
        return self._build_resolution(
            record=record,
            cdna=cdna,
            pos=anchor_pos,
            ref=anchor,
            alt=anchor + duplicated,
            provenance=[record.source, "ucsc_hg38_2bit_reference_sequence"],
        )

    def _resolve_insertion(
        self,
        record: _TranscriptRecord,
        cdna: str,
        start: _MappedCoordinate,
        end: _MappedCoordinate | None,
        inserted_transcript: str,
    ) -> EamosCoordinateResolution | None:
        if end is None or not inserted_transcript:
            return None
        anchor_pos = min(start.position, end.position)
        anchor = self._reference_base(record.chrom, anchor_pos)
        if anchor is None:
            return None
        inserted = _transcript_sequence_to_genomic(inserted_transcript, record.strand)
        return self._build_resolution(
            record=record,
            cdna=cdna,
            pos=anchor_pos,
            ref=anchor,
            alt=anchor + inserted,
            provenance=[record.source, "ucsc_hg38_2bit_reference_sequence"],
        )

    def _resolve_delins(
        self,
        record: _TranscriptRecord,
        cdna: str,
        start: _MappedCoordinate,
        end: _MappedCoordinate | None,
        inserted_transcript: str,
    ) -> EamosCoordinateResolution | None:
        if end is None or not inserted_transcript:
            return None
        interval = _genomic_interval(start, end)
        deleted = self._reference_sequence(record.chrom, interval[0], interval[1])
        if deleted is None:
            return None
        inserted = _transcript_sequence_to_genomic(inserted_transcript, record.strand)
        return self._build_resolution(
            record=record,
            cdna=cdna,
            pos=interval[0],
            ref=deleted,
            alt=inserted,
            provenance=[record.source, "ucsc_hg38_2bit_reference_sequence"],
        )

    def _build_resolution(
        self,
        *,
        record: _TranscriptRecord,
        cdna: str,
        pos: int,
        ref: str,
        alt: str,
        provenance: list[str],
        warnings: list[str] | None = None,
    ) -> EamosCoordinateResolution:
        pos, ref, alt = self._normalize_vcf(record.chrom, pos, ref, alt)
        variant_id = f"{record.chrom}-{pos}-{ref}-{alt}"
        return EamosCoordinateResolution(
            gene=record.gene,
            transcript=record.transcript,
            cdna=cdna,
            chrom=record.chrom,
            pos=pos,
            ref=ref,
            alt=alt,
            genomic_hg38=variant_id,
            genomic_hgvs=genomic_variant_id_to_refseq_hgvs(variant_id),
            source="eamos_local_transcript_reference",
            provenance=tuple(provenance),
            warnings=tuple(warnings or ()),
        )

    def _map_cdna_coordinate(
        self,
        record: _TranscriptRecord,
        token: _CdnaCoordinateToken,
    ) -> _MappedCoordinate | None:
        transcript_position = _transcript_position_for_cdna_token(record, token)
        if transcript_position < 1:
            return None
        for exon in record.exons:
            if exon.transcript_start <= transcript_position <= exon.transcript_end:
                offset = transcript_position - exon.transcript_start
                if record.strand == "-":
                    genomic_position = exon.genomic_end - offset
                else:
                    genomic_position = exon.genomic_start + offset
                transcript_base = (
                    exon.sequence[offset].upper()
                    if exon.sequence and 0 <= offset < len(exon.sequence)
                    else None
                )
                if token.sign is not None and token.offset is not None:
                    genomic_position = _intronic_position(
                        genomic_position,
                        strand=record.strand,
                        sign=token.sign,
                        offset=token.offset,
                    )
                    transcript_base = None
                return _MappedCoordinate(
                    position=genomic_position,
                    exon=exon,
                    transcript_base=transcript_base,
                    is_intronic=token.sign is not None,
                )
        return None

    def _reference_base(self, chrom: str, position: int) -> str | None:
        try:
            store = self._get_reference_store()
            window = store.get_sequence(chrom, position, position, build="GRCh38")
            sequence = str(window.sequence or "").upper()
            if len(sequence) != 1 or sequence not in _DNA_BASES:
                return None
            return sequence
        except (ReferenceGenomeStoreError, OSError, ImportError, ValueError):
            return None

    def _reference_sequence(self, chrom: str, start: int, end: int) -> str | None:
        if start < 1 or end < start:
            return None
        try:
            store = self._get_reference_store()
            window = store.get_sequence(chrom, start, end, build="GRCh38")
            sequence = str(window.sequence or "").upper()
            if len(sequence) != end - start + 1 or any(base not in _DNA_BASES for base in sequence):
                return None
            return sequence
        except (ReferenceGenomeStoreError, OSError, ImportError, ValueError):
            return None

    def _normalize_vcf(self, chrom: str, pos: int, ref: str, alt: str) -> tuple[int, str, str]:
        ref = ref.upper()
        alt = alt.upper()
        while len(ref) > 1 and len(alt) > 1 and ref[-1] == alt[-1]:
            ref = ref[:-1]
            alt = alt[:-1]
        while len(ref) > 1 and len(alt) > 1 and ref[0] == alt[0]:
            pos += 1
            ref = ref[1:]
            alt = alt[1:]

        if len(ref) == len(alt):
            return pos, ref, alt

        while pos > 1 and ref[-1] == alt[-1]:
            previous = self._reference_base(chrom, pos - 1)
            if previous is None:
                break
            pos -= 1
            ref = previous + ref[:-1]
            alt = previous + alt[:-1]
        return pos, ref, alt

    def _get_reference_store(self) -> _ReferenceStore:
        if self._reference_store is None:
            self._reference_store = self.reference_store_factory()
        return self._reference_store

    def close(self) -> None:
        if self._reference_store is not None:
            close = getattr(self._reference_store, "close", None)
            if callable(close):
                close()
            self._reference_store = None


def _default_reference_store() -> _ReferenceStore:
    return TwoBitReferenceGenomeStore.local_hg38()


_CDNA_COORDINATE_RE = r"(?:-\d+|\*\d+|\d+)(?:[+-]\d+)?"


def _parse_cdna_event(cdna: str) -> _CdnaEvent | None:
    substitution = re.fullmatch(
        rf"c\.(?P<start>{_CDNA_COORDINATE_RE})(?P<ref>[ACGT])>(?P<alt>[ACGT])",
        cdna,
        flags=re.IGNORECASE,
    )
    if substitution is not None:
        return _CdnaEvent(
            kind="substitution",
            start=_parse_cdna_coordinate_token(substitution.group("start")),
            ref=substitution.group("ref").upper(),
            alt=substitution.group("alt").upper(),
        )

    delins = re.fullmatch(
        rf"c\.(?P<start>{_CDNA_COORDINATE_RE})_(?P<end>{_CDNA_COORDINATE_RE})"
        r"delins(?P<inserted>[ACGT]+)",
        cdna,
        flags=re.IGNORECASE,
    )
    if delins is not None:
        return _CdnaEvent(
            kind="delins",
            start=_parse_cdna_coordinate_token(delins.group("start")),
            end=_parse_cdna_coordinate_token(delins.group("end")),
            inserted=delins.group("inserted").upper(),
        )

    insertion = re.fullmatch(
        rf"c\.(?P<start>{_CDNA_COORDINATE_RE})_(?P<end>{_CDNA_COORDINATE_RE})"
        r"ins(?P<inserted>[ACGT]+)",
        cdna,
        flags=re.IGNORECASE,
    )
    if insertion is not None:
        return _CdnaEvent(
            kind="insertion",
            start=_parse_cdna_coordinate_token(insertion.group("start")),
            end=_parse_cdna_coordinate_token(insertion.group("end")),
            inserted=insertion.group("inserted").upper(),
        )

    deletion = re.fullmatch(
        rf"c\.(?P<start>{_CDNA_COORDINATE_RE})"
        rf"(?:_(?P<end>{_CDNA_COORDINATE_RE}))?"
        r"del(?P<deleted>[ACGT]+)?",
        cdna,
        flags=re.IGNORECASE,
    )
    if deletion is not None:
        return _CdnaEvent(
            kind="deletion",
            start=_parse_cdna_coordinate_token(deletion.group("start")),
            end=(
                _parse_cdna_coordinate_token(deletion.group("end"))
                if deletion.group("end")
                else None
            ),
            deleted=(deletion.group("deleted") or "").upper() or None,
        )

    duplication = re.fullmatch(
        rf"c\.(?P<start>{_CDNA_COORDINATE_RE})"
        rf"(?:_(?P<end>{_CDNA_COORDINATE_RE}))?"
        r"dup(?P<duplicated>[ACGT]+)?",
        cdna,
        flags=re.IGNORECASE,
    )
    if duplication is not None:
        return _CdnaEvent(
            kind="duplication",
            start=_parse_cdna_coordinate_token(duplication.group("start")),
            end=(
                _parse_cdna_coordinate_token(duplication.group("end"))
                if duplication.group("end")
                else None
            ),
            inserted=(duplication.group("duplicated") or "").upper() or None,
        )

    return None


def _parse_cdna_coordinate_token(text: str) -> _CdnaCoordinateToken:
    match = re.fullmatch(
        r"(?P<prefix>-|\*)?(?P<number>\d+)(?:(?P<sign>[+-])(?P<offset>\d+))?",
        text,
    )
    if match is None:
        raise EamosCoordinateResolverError(
            "invalid_cdna_coordinate",
            "invalid cDNA coordinate token",
            {"coordinate": text},
        )
    return _CdnaCoordinateToken(
        prefix=match.group("prefix"),
        number=int(match.group("number")),
        sign=match.group("sign"),
        offset=int(match.group("offset")) if match.group("offset") else None,
    )


def _transcript_position_for_cdna_token(
    record: _TranscriptRecord,
    token: _CdnaCoordinateToken,
) -> int:
    if token.prefix == "-":
        return record.cds_transcript_start - token.number
    if token.prefix == "*":
        return record.cds_transcript_end + token.number
    return record.cds_transcript_start + token.number - 1


def _intronic_position(
    anchor_position: int,
    *,
    strand: str,
    sign: str | None,
    offset: int | None,
) -> int:
    if sign is None or offset is None:
        return anchor_position
    if sign == "+":
        return anchor_position + offset if strand == "+" else anchor_position - offset
    return anchor_position - offset if strand == "+" else anchor_position + offset


@lru_cache(maxsize=8)
def _load_mane_gff_transcript_models(path: Path | None) -> dict[str, tuple[_TranscriptRecord, ...]]:
    if path is None or not path.exists():
        return {}

    source_label = _gff_source_label(path)
    transcripts: dict[str, dict[str, Any]] = {}
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            columns = line.rstrip("\n").split("\t")
            if len(columns) != 9:
                continue
            chrom, _source, feature_type, start, end, _score, strand, _phase, raw_attrs = columns
            attrs = _parse_gff_attributes(raw_attrs)
            parent = attrs.get("Parent", "")
            transcript_id = attrs.get("transcript_id")
            if feature_type != "mRNA" and parent.startswith("rna-"):
                transcript_id = parent.removeprefix("rna-")
            if not transcript_id:
                transcript_id = attrs.get("Name")
            if not transcript_id and parent.startswith("rna-"):
                transcript_id = parent.removeprefix("rna-")
            if not transcript_id:
                continue

            record = transcripts.setdefault(
                transcript_id,
                {
                    "gene": attrs.get("gene", ""),
                    "transcript": transcript_id,
                    "chrom": _normalize_chromosome_id(chrom),
                    "strand": strand,
                    "exons": [],
                    "cds": [],
                },
            )
            if attrs.get("gene"):
                record["gene"] = attrs["gene"]
            if feature_type == "mRNA":
                record["chrom"] = _normalize_chromosome_id(chrom)
                record["strand"] = strand
            elif feature_type == "exon":
                record["exons"].append(
                    {
                        "number": _exon_number(attrs),
                        "start": int(start),
                        "end": int(end),
                    }
                )
            elif feature_type == "CDS":
                record["cds"].append({"start": int(start), "end": int(end)})

    by_gene: dict[str, list[_TranscriptRecord]] = {}
    for item in transcripts.values():
        gene = str(item["gene"] or "").upper()
        transcript = str(item["transcript"])
        chrom = _normalize_chromosome_id(str(item["chrom"]))
        strand = str(item["strand"])
        if not gene or not transcript or strand not in {"+", "-"}:
            continue
        raw_exons = item["exons"]
        raw_cds = item["cds"]
        if not raw_exons or not raw_cds:
            continue
        ordered = sorted(
            raw_exons,
            key=lambda exon: (
                exon["number"] if exon["number"] is not None else 10**9,
                exon["start"] if strand == "+" else -exon["end"],
            ),
        )
        transcript_exons: list[_TranscriptExon] = []
        cursor = 1
        for index, exon in enumerate(ordered, start=1):
            length = exon["end"] - exon["start"] + 1
            transcript_exons.append(
                _TranscriptExon(
                    number=exon["number"] or index,
                    transcript_start=cursor,
                    transcript_end=cursor + length - 1,
                    genomic_start=exon["start"],
                    genomic_end=exon["end"],
                    sequence="",
                )
            )
            cursor += length

        projected_cds: list[tuple[int, int]] = []
        for cds in raw_cds:
            for exon in transcript_exons:
                overlap_start = max(cds["start"], exon.genomic_start)
                overlap_end = min(cds["end"], exon.genomic_end)
                if overlap_start > overlap_end:
                    continue
                left = _genomic_to_transcript_position(exon, overlap_start, strand)
                right = _genomic_to_transcript_position(exon, overlap_end, strand)
                projected_cds.append((min(left, right), max(left, right)))
        if not projected_cds:
            continue

        by_gene.setdefault(gene, []).append(
            _TranscriptRecord(
                gene=gene,
                transcript=transcript,
                chrom=chrom,
                strand=strand,
                exons=tuple(transcript_exons),
                cds_transcript_start=min(start for start, _end in projected_cds),
                cds_transcript_end=max(end for _start, end in projected_cds),
                transcript_aliases=("MANE Select",),
                source=source_label,
            )
        )
    return {gene: tuple(records) for gene, records in by_gene.items()}


def _gff_source_label(path: Path) -> str:
    name = path.name.lower()
    if "mane" in name:
        return "eamos_mane_refseq_gff"
    if "gcf_000001405.40" in name or "refseq" in name:
        return "eamos_refseq_grch38p14_gff"
    return "eamos_refseq_gff"


def _merge_transcript_sources(
    *sources: dict[str, tuple[_TranscriptRecord, ...]],
) -> dict[str, tuple[_TranscriptRecord, ...]]:
    merged: dict[str, list[_TranscriptRecord]] = {}
    for source in sources:
        for gene, records in source.items():
            existing = merged.setdefault(gene, [])
            existing_keys = {_versionless(record.transcript) for record in existing}
            for record in records:
                if _versionless(record.transcript) not in existing_keys:
                    existing.append(record)
                    existing_keys.add(_versionless(record.transcript))
    return {gene: tuple(records) for gene, records in merged.items()}


def _parse_gff_attributes(raw: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for item in raw.split(";"):
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        attrs[key] = unquote(value)
    return attrs


def _exon_number(attrs: Mapping[str, str]) -> int | None:
    raw_id = attrs.get("ID", "")
    match = re.search(r"-(\d+)$", raw_id)
    if match is not None:
        return int(match.group(1))
    return None


def _genomic_to_transcript_position(exon: _TranscriptExon, position: int, strand: str) -> int:
    if strand == "-":
        return exon.transcript_start + (exon.genomic_end - position)
    return exon.transcript_start + (position - exon.genomic_start)


@lru_cache(maxsize=8)
def _load_coordinate_catalog(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    index: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return index
    for row in rows:
        if not isinstance(row, dict):
            continue
        gene = str(row.get("gene") or "").upper()
        transcript = str(row.get("transcript") or "").strip() or None
        cdna = _normalize_cdna(str(row.get("cdna") or ""))
        if gene and cdna:
            index[_catalog_key(gene, transcript, cdna)] = row
            index.setdefault(_catalog_key(gene, None, cdna), row)
        accession = _normalize_accession(str(row.get("accession") or ""))
        if accession:
            index[f"accession:{accession}"] = row
        variation_id = _digits(str(row.get("clinvar_variation_id") or ""))
        if variation_id:
            index[f"variation:{variation_id}"] = row
    return index


def _resolution_from_catalog_row(row: Mapping[str, Any]) -> EamosCoordinateResolution:
    chrom = str(row["chrom"]).removeprefix("chr")
    pos = int(row["pos"])
    ref = str(row["ref"]).upper()
    alt = str(row["alt"]).upper()
    variant_id = str(row.get("genomic_hg38") or f"{chrom}-{pos}-{ref}-{alt}")
    return EamosCoordinateResolution(
        gene=str(row["gene"]).upper(),
        transcript=str(row["transcript"]),
        cdna=_normalize_cdna(str(row["cdna"])),
        chrom=chrom,
        pos=pos,
        ref=ref,
        alt=alt,
        genomic_hg38=variant_id,
        genomic_hgvs=str(row.get("genomic_hgvs") or "")
        or genomic_variant_id_to_refseq_hgvs(variant_id),
        source=str(row.get("source") or "eamos_coordinate_catalog"),
        confidence=str(row.get("confidence") or "high"),
        accession=_optional_str(row.get("accession")),
        clinvar_variation_id=_optional_str(row.get("clinvar_variation_id")),
        canonical_spdi=_optional_str(row.get("canonical_spdi")),
        provenance=tuple(str(item) for item in row.get("provenance", []) if str(item).strip()),
        warnings=tuple(str(item) for item in row.get("warnings", []) if str(item).strip()),
    )


def _catalog_key(gene: str, transcript: str | None, cdna: str) -> str:
    transcript_key = _versionless(transcript) if transcript else ""
    return f"variant:{gene}:{transcript_key}:{_normalize_cdna(cdna).upper()}"


def _normalize_cdna(cdna: str) -> str:
    text = re.sub(r"\s+", "", cdna.strip())
    if ":" in text:
        text = text.split(":", 1)[1]
    return text


def _normalize_chromosome_id(chrom: str) -> str:
    normalized = chrom.strip()
    if normalized.lower().startswith("chr"):
        normalized = normalized[3:]
    return NC_CHROMOSOME_ACCESSIONS.get(normalized.upper(), normalized.upper())


def _versionless(transcript: str | None) -> str:
    text = str(transcript or "").strip()
    if not text:
        return ""
    return text.split(".", 1)[0].upper()


def _strand_base(base: str, strand: str) -> str:
    normalized = base.upper()
    if strand == "-":
        return normalized.translate(_COMPLEMENT)
    return normalized


def _transcript_sequence_to_genomic(sequence: str, strand: str) -> str:
    normalized = sequence.upper()
    if strand == "-":
        return normalized.translate(_COMPLEMENT)[::-1]
    return normalized


def _genomic_interval(start: _MappedCoordinate, end: _MappedCoordinate) -> tuple[int, int]:
    return (min(start.position, end.position), max(start.position, end.position))


def _normalize_accession(accession: str) -> str:
    return accession.strip().upper().split(".", 1)[0]


def _digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
