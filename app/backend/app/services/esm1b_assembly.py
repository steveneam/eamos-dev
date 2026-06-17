from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import md5, sha256
import json
import math
from pathlib import Path
import re
from typing import Any, Callable, Iterable

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
    license_gate: str | None
    warnings: tuple[str, ...]
    score_generation_method: str | None = None
    model_name: str | None = None
    model_source_url: str | None = None
    model_source_license: str | None = None
    scoring_code_source_url: str | None = None
    scoring_code_license: str | None = None

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
            "score_generation_method": self.score_generation_method,
            "model_name": self.model_name,
            "model_source_url": self.model_source_url,
            "model_source_license": self.model_source_license,
            "scoring_code_source_url": self.scoring_code_source_url,
            "scoring_code_license": self.scoring_code_license,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class Esm1bAssemblyResult:
    rows: tuple[Esm1bGenomicMissenseRow, ...]
    tsv: str
    manifest: Esm1bAssemblyManifest

    def manifest_payload(self) -> dict[str, object]:
        return self.manifest.to_payload()


@dataclass(frozen=True)
class Esm1bRuntimeAssetMaterialization:
    target_path: Path
    index_path: Path
    manifest_path: Path
    row_count: int
    input_score_row_count: int
    md5: str
    sha256: str
    index_md5: str
    index_sha256: str
    launch_gate: str | None

    def to_sanitized_dict(self) -> dict[str, object]:
        return {
            "file_name": self.target_path.name,
            "index_file_name": self.index_path.name,
            "manifest_file_name": self.manifest_path.name,
            "row_count": self.row_count,
            "input_score_row_count": self.input_score_row_count,
            "actual_size_bytes": self.target_path.stat().st_size,
            "index_size_bytes": self.index_path.stat().st_size,
            "md5": self.md5,
            "sha256": self.sha256,
            "index_md5": self.index_md5,
            "index_sha256": self.index_sha256,
            "launch_gate": self.launch_gate,
            "local_path_values_emitted": False,
            "secret_values_emitted": False,
        }


ESM1B_ASSEMBLY_SOURCE_ID = "esm1b_hg38_assembled_scores"
ESM1B_ASSEMBLY_MANIFEST_SCHEMA_VERSION = "1"
ESM1B_ASSEMBLY_CODE_VERSION = "esm1b_mane_assembly_v2"
ESM1B_DEFAULT_SCORE_ROW_LIMIT: int | None = None
ESM1B_PRECOMPUTED_SCORE_LICENSE_GATE = "esm1b_precomputed_score_zip_noncommercial"
ESM1B_REGENERATION_REQUIRED_GATE = "esm1b_mit_regeneration_required"
ESM1B_REGENERATED_SCORE_WARNING = "esm1b_mit_model_regenerated"
ESM1B_LICENSE_GATE = ESM1B_PRECOMPUTED_SCORE_LICENSE_GATE
ESM1B_REGENERATED_SCORE_METHOD = "mit_model_regeneration"
ESM1B_MODEL_NAME = "esm1b_t33_650M_UR50S"
ESM1B_MODEL_SOURCE_URL = "https://github.com/facebookresearch/esm"
ESM1B_SCORING_CODE_SOURCE_URL = "https://github.com/ntranoslab/esm-variants"
_GATED_MANIFEST_WARNINGS = (
    "esm1b_license_gate_metadata",
    ESM1B_PRECOMPUTED_SCORE_LICENSE_GATE,
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
    license_gate: str | None = ESM1B_LICENSE_GATE,
    score_generation_method: str | None = None,
    model_name: str | None = None,
    model_source_url: str | None = None,
    model_source_license: str | None = None,
    scoring_code_source_url: str | None = None,
    scoring_code_license: str | None = None,
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
        license_gate=_normalize_license_gate(license_gate),
        warnings=_manifest_warnings(warnings, license_gate=license_gate),
        score_generation_method=_optional_manifest_text(score_generation_method),
        model_name=_optional_manifest_text(model_name),
        model_source_url=_optional_manifest_text(model_source_url),
        model_source_license=_optional_manifest_text(model_source_license),
        scoring_code_source_url=_optional_manifest_text(scoring_code_source_url),
        scoring_code_license=_optional_manifest_text(scoring_code_license),
    )
    return Esm1bAssemblyResult(rows=rows, tsv=tsv, manifest=manifest)


def translate_codon(ref_codon: str) -> str:
    return _translate(_normalize_codon(ref_codon))


def load_esm1b_score_rows_from_csv(path: Path) -> tuple[Esm1bScoreRow, ...]:
    """Load ESM1b missense rows from a clean MIT-regenerated score CSV.

    The Ntranos MIT scorer emits `seq_id,mut_name,esm_score`. Eamos also accepts
    explicit `uniprot_isoform,mutation_name,esm1b_llr` headers so operator-side
    regeneration pipelines can normalize the CSV before materialization.
    """

    rows: list[Esm1bScoreRow] = []
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise Esm1bAssemblyError("ESM1b score CSV requires a header row")
        for line_number, raw in enumerate(reader, start=2):
            mutation_name = _first_csv_value(raw, "mutation_name", "mut_name", "variant")
            uniprot_isoform = _first_csv_value(raw, "uniprot_isoform", "seq_id", "id")
            score_text = _first_csv_value(raw, "esm1b_llr", "esm_score", "score")
            if mutation_name is None or uniprot_isoform is None or score_text is None:
                raise Esm1bAssemblyError(
                    "ESM1b score CSV row is missing mutation, score, or isoform field "
                    f"at line {line_number}"
                )
            try:
                score = float(score_text)
            except ValueError as exc:
                raise Esm1bAssemblyError(
                    f"ESM1b score CSV row has non-numeric score at line {line_number}"
                ) from exc
            rows.append(
                Esm1bScoreRow(
                    mutation_name=mutation_name,
                    esm1b_llr=score,
                    uniprot_isoform=uniprot_isoform,
                )
            )
    if not rows:
        raise Esm1bAssemblyError("ESM1b score CSV produced zero rows")
    return tuple(rows)


def load_esm1b_codon_contexts_from_jsonl(path: Path) -> tuple[Esm1bManeCodonContext, ...]:
    contexts: list[Esm1bManeCodonContext] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                contexts.append(_codon_context_from_mapping(raw))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise Esm1bAssemblyError(
                    f"invalid ESM1b MANE codon context JSONL row at line {line_number}"
                ) from exc
    if not contexts:
        raise Esm1bAssemblyError("ESM1b MANE codon context JSONL produced zero rows")
    return tuple(contexts)


def materialize_regenerated_esm1b_runtime_asset(
    *,
    score_rows: Iterable[Esm1bScoreRow],
    codon_contexts: Iterable[Esm1bManeCodonContext],
    target_path: Path,
    score_source_checksum: str,
    mane_version: str,
    grch38_reference_checksum: str,
    code_version: str = ESM1B_ASSEMBLY_CODE_VERSION,
    model_name: str = ESM1B_MODEL_NAME,
    model_source_url: str = ESM1B_MODEL_SOURCE_URL,
    model_source_license: str = "MIT",
    scoring_code_source_url: str = ESM1B_SCORING_CODE_SOURCE_URL,
    scoring_code_license: str = "MIT",
    bgzip_tabix_writer: Callable[[str, Path], Path] | None = None,
) -> Esm1bRuntimeAssetMaterialization:
    """Write the commercial-safe ESM1b runtime artifact from regenerated scores."""

    result = assemble_esm1b_mane_fixture_snv_table(
        score_rows=score_rows,
        codon_contexts=codon_contexts,
        score_source_checksum=score_source_checksum,
        mane_version=mane_version,
        grch38_reference_checksum=grch38_reference_checksum,
        code_version=code_version,
        warnings=(ESM1B_REGENERATED_SCORE_WARNING,),
        license_gate=None,
        score_generation_method=ESM1B_REGENERATED_SCORE_METHOD,
        model_name=model_name,
        model_source_url=model_source_url,
        model_source_license=model_source_license,
        scoring_code_source_url=scoring_code_source_url,
        scoring_code_license=scoring_code_license,
    )
    if not result.tsv:
        raise Esm1bAssemblyError("refusing to materialize an empty ESM1b runtime TSV")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    writer = bgzip_tabix_writer or _write_bgzip_and_tabix
    index_path = writer(result.tsv, target_path)
    if not target_path.is_file():
        raise Esm1bAssemblyError("ESM1b runtime asset writer did not create the target file")
    if not index_path.is_file():
        raise Esm1bAssemblyError("ESM1b runtime asset writer did not create the tabix index")

    target_digest = _hash_file(target_path)
    index_digest = _hash_file(index_path)
    manifest_path = target_path.with_suffix(target_path.suffix + ".manifest.json")
    manifest_payload = {
        **result.manifest_payload(),
        "asset_role": "predictor_tabix_tsv",
        "file_name": target_path.name,
        "actual_size_bytes": target_path.stat().st_size,
        "md5": target_digest["md5"],
        "sha256": target_digest["sha256"],
        "uncompressed_tsv_sha256": result.manifest.output_checksum,
        "index_file_name": index_path.name,
        "index_size_bytes": index_path.stat().st_size,
        "index_md5": index_digest["md5"],
        "index_sha256": index_digest["sha256"],
        "launch_gate": None,
        "commercial_use_allowed": True,
        "precomputed_huggingface_score_zip_used": False,
        "startup_download_allowed": False,
        "request_time_materialization_allowed": False,
        "public_access_allowed": False,
        "frontend_direct_access_allowed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return Esm1bRuntimeAssetMaterialization(
        target_path=target_path,
        index_path=index_path,
        manifest_path=manifest_path,
        row_count=result.manifest.row_count,
        input_score_row_count=result.manifest.input_score_row_count,
        md5=target_digest["md5"],
        sha256=target_digest["sha256"],
        index_md5=index_digest["md5"],
        index_sha256=index_digest["sha256"],
        launch_gate=None,
    )


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


def _manifest_warnings(
    warnings: Iterable[str],
    *,
    license_gate: str | None,
) -> tuple[str, ...]:
    deduped: list[str] = []
    required = _GATED_MANIFEST_WARNINGS if _normalize_license_gate(license_gate) else ()
    for warning in (*tuple(warnings), *required):
        text = warning.strip()
        if text and text not in deduped:
            deduped.append(text)
    return tuple(deduped)


def _normalize_license_gate(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_manifest_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _first_csv_value(row: dict[str, str], *names: str) -> str | None:
    for name in names:
        value = row.get(name)
        if value is None:
            continue
        text = value.strip()
        if text:
            return text
    return None


def _codon_context_from_mapping(raw: dict[str, Any]) -> Esm1bManeCodonContext:
    positions = raw["codon_positions"]
    if not isinstance(positions, list | tuple) or len(positions) != 3:
        raise ValueError("codon_positions must contain exactly three positions")
    return Esm1bManeCodonContext(
        uniprot_isoform=str(raw["uniprot_isoform"]),
        protein_position=int(raw["protein_position"]),
        chrom=str(raw["chrom"]),
        ref_codon=str(raw["ref_codon"]),
        codon_positions=tuple(int(value) for value in positions),
        strand=str(raw["strand"]),
        mane_tx=str(raw["mane_tx"]),
        gene=None if raw.get("gene") is None else str(raw.get("gene")),
    )


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


def _write_bgzip_and_tabix(tsv: str, target_path: Path) -> Path:
    try:
        import pysam
    except ImportError as exc:
        raise Esm1bAssemblyError(
            "pysam is required to bgzip and tabix-index regenerated ESM1b scores"
        ) from exc

    temp_tsv = target_path.with_name(f".{target_path.name}.tmp.tsv")
    temp_gz = target_path.with_name(f".{target_path.name}.tmp.gz")
    temp_tsv.write_text(tsv, encoding="utf-8")
    try:
        pysam.tabix_compress(str(temp_tsv), str(temp_gz), force=True)
        temp_gz.replace(target_path)
        pysam.tabix_index(
            str(target_path),
            force=True,
            seq_col=0,
            start_col=1,
            end_col=1,
            meta_char="#",
            zerobased=False,
        )
    finally:
        temp_tsv.unlink(missing_ok=True)
        temp_gz.unlink(missing_ok=True)
    index_path = Path(f"{target_path}.tbi")
    if not index_path.is_file():
        raise Esm1bAssemblyError("ESM1b tabix index was not created")
    return index_path


def _hash_file(path: Path) -> dict[str, str]:
    md5_digest = md5(usedforsecurity=False)
    sha256_digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(4 * 1024 * 1024), b""):
            md5_digest.update(chunk)
            sha256_digest.update(chunk)
    return {"md5": md5_digest.hexdigest(), "sha256": sha256_digest.hexdigest()}
