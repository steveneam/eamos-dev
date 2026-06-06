from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
import re
from typing import Iterable

from app.services.computational_calibration import calibrate_predictor


class Esm1bAssemblyError(ValueError):
    """Raised when an ESM1b protein-to-genomic transform cannot be trusted."""


@dataclass(frozen=True)
class Esm1bMissenseSubstitution:
    raw: str
    wt_residue: str
    protein_position: int
    alt_residue: str


@dataclass(frozen=True)
class Esm1bScoreRow:
    mutation_name: str
    esm1b_llr: float
    uniprot_isoform: str


@dataclass(frozen=True)
class Esm1bManeCodonContext:
    uniprot_isoform: str
    protein_position: int
    chrom: str
    ref_codon: str
    codon_positions: tuple[int, int, int]
    strand: str
    mane_tx: str
    gene: str | None = None


@dataclass(frozen=True)
class Esm1bGenomicMissenseRow:
    chrom: str
    position: int
    ref: str
    alt: str
    esm1b_llr: float
    acmg_band: str
    uniprot_isoform: str
    mane_tx: str
    aa_sub: str

    def to_tsv_fields(self) -> tuple[str, ...]:
        return (
            self.chrom,
            str(self.position),
            self.ref,
            self.alt,
            f"{self.esm1b_llr:.4f}",
            self.acmg_band,
            self.uniprot_isoform,
            self.mane_tx,
            self.aa_sub,
        )


@dataclass(frozen=True)
class Esm1bAssemblyManifest:
    source_id: str
    manifest_schema_version: str
    score_source_checksum_algorithm: str
    score_source_checksum: str
    mane_version: str
    grch38_reference_checksum_algorithm: str
    grch38_reference_checksum: str
    code_version: str
    output_checksum_algorithm: str
    output_checksum: str
    row_count: int
    input_score_row_count: int
    internal_fixture_only: bool
    public_serialization_allowed: bool
    license_gate: str
    warnings: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "manifest_schema_version": self.manifest_schema_version,
            "score_source_checksum_algorithm": self.score_source_checksum_algorithm,
            "score_source_checksum": self.score_source_checksum,
            "mane_version": self.mane_version,
            "grch38_reference_checksum_algorithm": self.grch38_reference_checksum_algorithm,
            "grch38_reference_checksum": self.grch38_reference_checksum,
            "code_version": self.code_version,
            "output_checksum_algorithm": self.output_checksum_algorithm,
            "output_checksum": self.output_checksum,
            "row_count": self.row_count,
            "input_score_row_count": self.input_score_row_count,
            "internal_fixture_only": self.internal_fixture_only,
            "public_serialization_allowed": self.public_serialization_allowed,
            "license_gate": self.license_gate,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class Esm1bAssemblyResult:
    rows: tuple[Esm1bGenomicMissenseRow, ...]
    tsv: str
    manifest: Esm1bAssemblyManifest

    def manifest_payload(self) -> dict[str, object]:
        return self.manifest.to_payload()


ESM1B_ASSEMBLY_SOURCE_ID = "esm1b_hg38_assembled_scores"
ESM1B_ASSEMBLY_MANIFEST_SCHEMA_VERSION = "1"
ESM1B_ASSEMBLY_CODE_VERSION = "esm1b_mane_assembly_v2"
ESM1B_DEFAULT_SCORE_ROW_LIMIT: int | None = None
ESM1B_LICENSE_GATE = "esm1b_score_file_terms_unconfirmed"
_REQUIRED_MANIFEST_WARNINGS = (
    "esm1b_license_gate_metadata",
    "esm1b_score_file_terms_unconfirmed",
)

_DNA_BASES = frozenset({"A", "C", "G", "T"})
_COMPLEMENT = str.maketrans("ACGT", "TGCA")
_MISSENSE_RE = re.compile(r"^(?P<wt>[A-Z])(?P<pos>[1-9][0-9]*)(?P<alt>[A-Z])$")

_GENETIC_CODE: dict[str, str] = {
    "TTT": "F",
    "TTC": "F",
    "TTA": "L",
    "TTG": "L",
    "TCT": "S",
    "TCC": "S",
    "TCA": "S",
    "TCG": "S",
    "TAT": "Y",
    "TAC": "Y",
    "TAA": "*",
    "TAG": "*",
    "TGT": "C",
    "TGC": "C",
    "TGA": "*",
    "TGG": "W",
    "CTT": "L",
    "CTC": "L",
    "CTA": "L",
    "CTG": "L",
    "CCT": "P",
    "CCC": "P",
    "CCA": "P",
    "CCG": "P",
    "CAT": "H",
    "CAC": "H",
    "CAA": "Q",
    "CAG": "Q",
    "CGT": "R",
    "CGC": "R",
    "CGA": "R",
    "CGG": "R",
    "ATT": "I",
    "ATC": "I",
    "ATA": "I",
    "ATG": "M",
    "ACT": "T",
    "ACC": "T",
    "ACA": "T",
    "ACG": "T",
    "AAT": "N",
    "AAC": "N",
    "AAA": "K",
    "AAG": "K",
    "AGT": "S",
    "AGC": "S",
    "AGA": "R",
    "AGG": "R",
    "GTT": "V",
    "GTC": "V",
    "GTA": "V",
    "GTG": "V",
    "GCT": "A",
    "GCC": "A",
    "GCA": "A",
    "GCG": "A",
    "GAT": "D",
    "GAC": "D",
    "GAA": "E",
    "GAG": "E",
    "GGT": "G",
    "GGC": "G",
    "GGA": "G",
    "GGG": "G",
}
_CODONS_BY_AA: dict[str, tuple[str, ...]] = {
    residue: tuple(codon for codon, aa in _GENETIC_CODE.items() if aa == residue)
    for residue in sorted(set(_GENETIC_CODE.values()))
}


def parse_esm1b_mutation_name(value: str) -> Esm1bMissenseSubstitution:
    text = value.strip()
    match = _MISSENSE_RE.fullmatch(text)
    if match is None:
        raise Esm1bAssemblyError(f"unsupported ESM1b missense mutation name: {value!r}")
    wt = match.group("wt")
    alt = match.group("alt")
    if wt == "*" or alt == "*" or wt == alt:
        raise Esm1bAssemblyError(f"ESM1b assembly requires a residue-changing missense: {value!r}")
    return Esm1bMissenseSubstitution(
        raw=text,
        wt_residue=wt,
        protein_position=int(match.group("pos")),
        alt_residue=alt,
    )


def esm1b_genomic_snv_rows(
    *,
    chrom: str,
    ref_codon: str,
    codon_positions: tuple[int, int, int],
    strand: str,
    substitution: Esm1bMissenseSubstitution,
    esm1b_llr: float,
    uniprot_isoform: str,
    mane_tx: str,
) -> tuple[Esm1bGenomicMissenseRow, ...]:
    """Emit one row per single-base genomic SNV that can produce the ESM1b aa change."""

    coding_ref_codon = _normalize_codon(ref_codon)
    if len(codon_positions) != 3:
        raise Esm1bAssemblyError("codon_positions must contain exactly three genomic positions")
    if strand not in {"+", "-"}:
        raise Esm1bAssemblyError("strand must be '+' or '-'")

    wt_residue = _translate(coding_ref_codon)
    if wt_residue != substitution.wt_residue:
        raise Esm1bAssemblyError(
            "reference codon does not match ESM1b wild-type residue: "
            f"{coding_ref_codon}->{wt_residue}, expected {substitution.wt_residue}"
        )

    band = _esm1b_band(esm1b_llr)
    rows: list[Esm1bGenomicMissenseRow] = []
    for alt_codon in _CODONS_BY_AA.get(substitution.alt_residue, ()):
        diffs = [
            (index, ref_base, alt_base)
            for index, (ref_base, alt_base) in enumerate(zip(coding_ref_codon, alt_codon))
            if ref_base != alt_base
        ]
        if len(diffs) != 1:
            continue
        index, ref_base, alt_base = diffs[0]
        if strand == "-":
            ref_base = _reverse_complement_base(ref_base)
            alt_base = _reverse_complement_base(alt_base)
        rows.append(
            Esm1bGenomicMissenseRow(
                chrom=chrom,
                position=codon_positions[index],
                ref=ref_base,
                alt=alt_base,
                esm1b_llr=esm1b_llr,
                acmg_band=band,
                uniprot_isoform=uniprot_isoform,
                mane_tx=mane_tx,
                aa_sub=substitution.raw,
            )
        )
    return tuple(sorted(rows, key=lambda row: (row.chrom, row.position, row.ref, row.alt)))


def assemble_esm1b_mane_fixture_snv_table(
    *,
    score_rows: Iterable[Esm1bScoreRow],
    codon_contexts: Iterable[Esm1bManeCodonContext],
    score_source_checksum: str,
    mane_version: str,
    grch38_reference_checksum: str,
    code_version: str = ESM1B_ASSEMBLY_CODE_VERSION,
    warnings: Iterable[str] = (),
    max_score_rows: int | None = ESM1B_DEFAULT_SCORE_ROW_LIMIT,
) -> Esm1bAssemblyResult:
    """Assemble ESM1b MANE genomic SNV rows with provenance for launch gating."""

    scores = tuple(score_rows)
    if max_score_rows is not None and max_score_rows < 1:
        raise Esm1bAssemblyError("max_score_rows must be positive")
    if max_score_rows is not None and len(scores) > max_score_rows:
        raise Esm1bAssemblyError(
            "ESM1b assembly score row count exceeds configured limit: "
            f"{len(scores)} score rows exceeds limit {max_score_rows}"
        )

    _validate_required_manifest_value(score_source_checksum, "score_source_checksum")
    _validate_required_manifest_value(mane_version, "mane_version")
    _validate_required_manifest_value(grch38_reference_checksum, "grch38_reference_checksum")
    _validate_required_manifest_value(code_version, "code_version")

    context_index = _build_codon_context_index(tuple(codon_contexts))
    output_rows: list[Esm1bGenomicMissenseRow] = []
    for score_row in scores:
        _validate_score_row(score_row)
        substitution = parse_esm1b_mutation_name(score_row.mutation_name)
        context_key = (score_row.uniprot_isoform, substitution.protein_position)
        context = context_index.get(context_key)
        if context is None:
            raise Esm1bAssemblyError(
                "missing MANE codon context for ESM1b score row: "
                f"{score_row.uniprot_isoform} {substitution.raw}"
            )
        output_rows.extend(
            esm1b_genomic_snv_rows(
                chrom=context.chrom,
                ref_codon=context.ref_codon,
                codon_positions=context.codon_positions,
                strand=context.strand,
                substitution=substitution,
                esm1b_llr=score_row.esm1b_llr,
                uniprot_isoform=score_row.uniprot_isoform,
                mane_tx=context.mane_tx,
            )
        )

    rows = tuple(sorted(output_rows, key=_genomic_row_sort_key))
    tsv = _genomic_rows_to_tsv(rows)
    output_checksum = _sha256_text(tsv)
    manifest = Esm1bAssemblyManifest(
        source_id=ESM1B_ASSEMBLY_SOURCE_ID,
        manifest_schema_version=ESM1B_ASSEMBLY_MANIFEST_SCHEMA_VERSION,
        score_source_checksum_algorithm="sha256",
        score_source_checksum=score_source_checksum.strip(),
        mane_version=mane_version.strip(),
        grch38_reference_checksum_algorithm="sha256",
        grch38_reference_checksum=grch38_reference_checksum.strip(),
        code_version=code_version.strip(),
        output_checksum_algorithm="sha256",
        output_checksum=output_checksum,
        row_count=len(rows),
        input_score_row_count=len(scores),
        internal_fixture_only=False,
        public_serialization_allowed=True,
        license_gate=ESM1B_LICENSE_GATE,
        warnings=_manifest_warnings(warnings),
    )
    return Esm1bAssemblyResult(rows=rows, tsv=tsv, manifest=manifest)


def translate_codon(ref_codon: str) -> str:
    return _translate(_normalize_codon(ref_codon))


def _build_codon_context_index(
    contexts: tuple[Esm1bManeCodonContext, ...],
) -> dict[tuple[str, int], Esm1bManeCodonContext]:
    index: dict[tuple[str, int], Esm1bManeCodonContext] = {}
    for context in contexts:
        _validate_codon_context(context)
        key = (context.uniprot_isoform.strip(), context.protein_position)
        if key in index:
            raise Esm1bAssemblyError(
                "duplicate MANE codon context for ESM1b protein position: "
                f"{context.uniprot_isoform} {context.protein_position}"
            )
        index[key] = context
    return index


def _validate_score_row(row: Esm1bScoreRow) -> None:
    if not row.uniprot_isoform.strip():
        raise Esm1bAssemblyError("ESM1b score row requires a UniProt isoform")
    if not math.isfinite(float(row.esm1b_llr)):
        raise Esm1bAssemblyError("ESM1b score row requires a finite LLR score")


def _validate_codon_context(context: Esm1bManeCodonContext) -> None:
    if not context.uniprot_isoform.strip():
        raise Esm1bAssemblyError("MANE codon context requires a UniProt isoform")
    if context.protein_position < 1:
        raise Esm1bAssemblyError("MANE codon context protein_position must be positive")
    if not context.chrom.strip():
        raise Esm1bAssemblyError("MANE codon context requires a chromosome")
    if not context.mane_tx.strip():
        raise Esm1bAssemblyError("MANE codon context requires a MANE transcript")
    _normalize_codon(context.ref_codon)
    if len(context.codon_positions) != 3:
        raise Esm1bAssemblyError("MANE codon context must contain three codon positions")
    if context.strand not in {"+", "-"}:
        raise Esm1bAssemblyError("MANE codon context strand must be '+' or '-'")


def _validate_required_manifest_value(value: str, field_name: str) -> None:
    if not value.strip():
        raise Esm1bAssemblyError(f"ESM1b assembly manifest requires {field_name}")


def _genomic_rows_to_tsv(rows: tuple[Esm1bGenomicMissenseRow, ...]) -> str:
    if not rows:
        return ""
    return "\n".join("\t".join(row.to_tsv_fields()) for row in rows) + "\n"


def _genomic_row_sort_key(
    row: Esm1bGenomicMissenseRow,
) -> tuple[str, int, str, str, str, str, str]:
    return (row.chrom, row.position, row.ref, row.alt, row.uniprot_isoform, row.mane_tx, row.aa_sub)


def _manifest_warnings(warnings: Iterable[str]) -> tuple[str, ...]:
    deduped: list[str] = []
    for warning in (*tuple(warnings), *_REQUIRED_MANIFEST_WARNINGS):
        text = warning.strip()
        if text and text not in deduped:
            deduped.append(text)
    return tuple(deduped)


def _sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _normalize_codon(value: str) -> str:
    codon = value.strip().upper().replace("U", "T")
    if len(codon) != 3 or any(base not in _DNA_BASES for base in codon):
        raise Esm1bAssemblyError(f"invalid DNA codon: {value!r}")
    return codon


def _translate(codon: str) -> str:
    try:
        return _GENETIC_CODE[codon]
    except KeyError as exc:
        raise Esm1bAssemblyError(f"unsupported DNA codon: {codon!r}") from exc


def _reverse_complement_base(base: str) -> str:
    return base.translate(_COMPLEMENT)


def _esm1b_band(score: float) -> str:
    calibration = calibrate_predictor("ESM1b", score)
    return calibration.calibrated_label if calibration is not None else ""
