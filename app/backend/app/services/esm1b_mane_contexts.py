from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
from hashlib import md5, sha256
import json
from pathlib import Path
from textwrap import wrap
from typing import Iterable, Iterator, Mapping, Protocol
from urllib.parse import unquote

from app.services.esm1b_assembly import Esm1bManeCodonContext, translate_codon
from app.services.reference_genome import ReferenceWindow


class Esm1bManeContextError(ValueError):
    """Raised when MANE CDS context generation cannot be trusted."""


class ReferenceSequenceStore(Protocol):
    def get_sequence(
        self,
        chrom: str,
        start: int,
        end: int,
        build: str | None = None,
    ) -> ReferenceWindow: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class Esm1bManeProteinContext:
    sequence_id: str
    sequence_id_field: str
    gene: str
    mane_tx: str
    chrom: str
    strand: str
    protein_id: str | None
    ensembl_protein_id: str | None
    protein_sequence: str
    contexts: tuple[Esm1bManeCodonContext, ...]
    nonstandard_codon_count: int = 0


@dataclass(frozen=True)
class Esm1bManeContextBuildResult:
    context_path: Path
    protein_fasta_path: Path
    manifest_path: Path
    sequence_id_field: str
    mane_version: str
    primary_chromosomes_only: bool
    protein_count: int
    context_count: int
    amino_acid_count: int
    nonstandard_codon_count: int
    context_sha256: str
    protein_fasta_sha256: str
    mane_gff_sha256: str
    reference_sha256: str | None

    def to_sanitized_dict(self) -> dict[str, object]:
        return {
            "context_file_name": self.context_path.name,
            "protein_fasta_file_name": self.protein_fasta_path.name,
            "manifest_file_name": self.manifest_path.name,
            "sequence_id_field": self.sequence_id_field,
            "mane_version": self.mane_version,
            "primary_chromosomes_only": self.primary_chromosomes_only,
            "protein_count": self.protein_count,
            "context_count": self.context_count,
            "amino_acid_count": self.amino_acid_count,
            "nonstandard_codon_count": self.nonstandard_codon_count,
            "context_size_bytes": self.context_path.stat().st_size,
            "protein_fasta_size_bytes": self.protein_fasta_path.stat().st_size,
            "context_sha256": self.context_sha256,
            "protein_fasta_sha256": self.protein_fasta_sha256,
            "mane_gff_sha256": self.mane_gff_sha256,
            "reference_sha256": self.reference_sha256,
            "local_path_values_emitted": False,
            "secret_values_emitted": False,
        }


@dataclass(frozen=True)
class _ManeTranscript:
    transcript_id: str
    gene: str
    chrom: str
    strand: str


@dataclass(frozen=True)
class _CdsFeature:
    transcript_id: str
    start: int
    end: int
    protein_id: str | None
    ensembl_protein_id: str | None


_COMPLEMENT = str.maketrans("ACGT", "TGCA")
_SEQUENCE_ID_FIELDS = frozenset({"protein_id", "ensembl_protein_id", "mane_tx"})
_NONSTANDARD_POLICIES = frozenset({"fail", "skip"})
_INVALID_CDS_POLICIES = frozenset({"fail", "skip"})


def iter_esm1b_mane_protein_contexts(
    *,
    mane_gff_path: Path,
    reference_store: ReferenceSequenceStore,
    sequence_id_field: str = "protein_id",
    genes: Iterable[str] | None = None,
    nonstandard_codon_policy: str = "fail",
    invalid_cds_policy: str = "fail",
    primary_chromosomes_only: bool = False,
) -> Iterator[Esm1bManeProteinContext]:
    """Yield MANE coding contexts and matching protein sequences.

    The yielded ``sequence_id`` is the identifier the operator-side MIT ESM1b
    scoring run should use as FASTA ``seq_id``. The downstream materializer then
    joins score CSV rows to these contexts by that same value.
    """

    sequence_id_field = _validate_sequence_id_field(sequence_id_field)
    nonstandard_codon_policy = _validate_nonstandard_policy(nonstandard_codon_policy)
    invalid_cds_policy = _validate_invalid_cds_policy(invalid_cds_policy)
    requested_genes = (
        frozenset(gene.strip().upper() for gene in genes if gene.strip())
        if genes is not None
        else None
    )
    transcripts, cds_by_transcript = _load_mane_cds_features(
        mane_gff_path,
        genes=requested_genes,
        primary_chromosomes_only=primary_chromosomes_only,
    )
    if not transcripts:
        raise Esm1bManeContextError("MANE GFF produced zero MANE Select transcripts")

    for transcript_id in sorted(transcripts, key=lambda tx: (transcripts[tx].gene, tx)):
        transcript = transcripts[transcript_id]
        cds_features = tuple(cds_by_transcript.get(transcript_id, ()))
        if not cds_features:
            continue
        protein = _build_protein_context(
            transcript,
            cds_features,
            reference_store=reference_store,
            sequence_id_field=sequence_id_field,
            nonstandard_codon_policy=nonstandard_codon_policy,
            invalid_cds_policy=invalid_cds_policy,
        )
        if protein is not None:
            yield protein


def write_esm1b_mane_context_artifacts(
    *,
    mane_gff_path: Path,
    reference_path: Path,
    reference_store: ReferenceSequenceStore,
    context_path: Path,
    protein_fasta_path: Path,
    manifest_path: Path,
    sequence_id_field: str = "protein_id",
    mane_version: str,
    genes: Iterable[str] | None = None,
    nonstandard_codon_policy: str = "fail",
    invalid_cds_policy: str = "fail",
    primary_chromosomes_only: bool = False,
    reference_sha256: str | None = None,
) -> Esm1bManeContextBuildResult:
    """Write ESM1b MANE context JSONL plus matching protein FASTA."""

    _require_text(mane_version, "mane_version")
    context_path.parent.mkdir(parents=True, exist_ok=True)
    protein_fasta_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    protein_count = 0
    context_count = 0
    amino_acid_count = 0
    nonstandard_codon_count = 0
    with (
        context_path.open("w", encoding="utf-8", newline="\n") as context_file,
        protein_fasta_path.open("w", encoding="utf-8", newline="\n") as fasta_file,
    ):
        for protein in iter_esm1b_mane_protein_contexts(
            mane_gff_path=mane_gff_path,
            reference_store=reference_store,
            sequence_id_field=sequence_id_field,
            genes=genes,
            nonstandard_codon_policy=nonstandard_codon_policy,
            invalid_cds_policy=invalid_cds_policy,
            primary_chromosomes_only=primary_chromosomes_only,
        ):
            if not protein.contexts:
                continue
            protein_count += 1
            context_count += len(protein.contexts)
            amino_acid_count += len(protein.protein_sequence)
            nonstandard_codon_count += protein.nonstandard_codon_count
            fasta_file.write(_fasta_record(protein))
            for context in protein.contexts:
                context_file.write(
                    json.dumps(
                        _context_payload(context),
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                )
                context_file.write("\n")

    if protein_count == 0 or context_count == 0:
        raise Esm1bManeContextError("refusing to write empty ESM1b MANE context artifacts")

    context_hash = _hash_file(context_path)
    fasta_hash = _hash_file(protein_fasta_path)
    mane_gff_hash = _hash_file(mane_gff_path)
    if reference_sha256 is None:
        reference_sha256 = _sha256_file(reference_path)

    manifest_payload = {
        "source_id": "esm1b_mane_codon_contexts",
        "manifest_schema_version": "1",
        "mane_version": mane_version.strip(),
        "sequence_id_field": sequence_id_field,
        "context_file_name": context_path.name,
        "context_size_bytes": context_path.stat().st_size,
        "context_md5": context_hash["md5"],
        "context_sha256": context_hash["sha256"],
        "protein_fasta_file_name": protein_fasta_path.name,
        "protein_fasta_size_bytes": protein_fasta_path.stat().st_size,
        "protein_fasta_md5": fasta_hash["md5"],
        "protein_fasta_sha256": fasta_hash["sha256"],
        "mane_gff_file_name": mane_gff_path.name,
        "mane_gff_sha256": mane_gff_hash["sha256"],
        "reference_file_name": reference_path.name,
        "reference_sha256": reference_sha256,
        "protein_count": protein_count,
        "context_count": context_count,
        "amino_acid_count": amino_acid_count,
        "nonstandard_codon_policy": nonstandard_codon_policy,
        "nonstandard_codon_count": nonstandard_codon_count,
        "invalid_cds_policy": invalid_cds_policy,
        "primary_chromosomes_only": primary_chromosomes_only,
        "score_generation_method": "mit_model_regeneration_input",
        "precomputed_huggingface_score_zip_used": False,
        "storage_upload": "not_used",
        "supabase_metadata_mutation": "not_used",
        "render_disk_seeding": "not_used",
        "provider_flip": "not_used",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return Esm1bManeContextBuildResult(
        context_path=context_path,
        protein_fasta_path=protein_fasta_path,
        manifest_path=manifest_path,
        sequence_id_field=sequence_id_field,
        mane_version=mane_version,
        primary_chromosomes_only=primary_chromosomes_only,
        protein_count=protein_count,
        context_count=context_count,
        amino_acid_count=amino_acid_count,
        nonstandard_codon_count=nonstandard_codon_count,
        context_sha256=context_hash["sha256"],
        protein_fasta_sha256=fasta_hash["sha256"],
        mane_gff_sha256=mane_gff_hash["sha256"],
        reference_sha256=reference_sha256,
    )


def _load_mane_cds_features(
    path: Path,
    *,
    genes: frozenset[str] | None,
    primary_chromosomes_only: bool,
) -> tuple[dict[str, _ManeTranscript], dict[str, tuple[_CdsFeature, ...]]]:
    if not path.is_file():
        raise Esm1bManeContextError("MANE GFF path is not a file")

    transcripts: dict[str, _ManeTranscript] = {}
    cds_by_transcript: dict[str, list[_CdsFeature]] = {}
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            columns = line.rstrip("\n").split("\t")
            if len(columns) != 9:
                continue
            chrom, _source, feature_type, start, end, _score, strand, _phase, raw_attrs = columns
            if feature_type not in {"mRNA", "CDS"}:
                continue
            normalized_chrom = _normalize_chromosome(chrom)
            if primary_chromosomes_only and not _is_primary_chromosome(normalized_chrom):
                continue
            attrs = _parse_gff_attributes(raw_attrs)
            gene = str(attrs.get("gene") or "").strip().upper()
            if genes is not None and gene not in genes:
                continue
            if feature_type == "mRNA":
                if "MANE Select" not in _attribute_values(attrs.get("tag")):
                    continue
                transcript_id = _transcript_id(feature_type, attrs)
                if not transcript_id or strand not in {"+", "-"}:
                    continue
                transcripts[transcript_id] = _ManeTranscript(
                    transcript_id=transcript_id,
                    gene=gene,
                    chrom=normalized_chrom,
                    strand=strand,
                )
                continue

            transcript_id = _transcript_id(feature_type, attrs)
            if not transcript_id:
                continue
            cds_by_transcript.setdefault(transcript_id, []).append(
                _CdsFeature(
                    transcript_id=transcript_id,
                    start=int(start),
                    end=int(end),
                    protein_id=_optional_text(attrs.get("protein_id")),
                    ensembl_protein_id=_ensembl_protein_id(attrs),
                )
            )

    filtered_cds = {
        transcript_id: tuple(features)
        for transcript_id, features in cds_by_transcript.items()
        if transcript_id in transcripts
    }
    return transcripts, filtered_cds


def _build_protein_context(
    transcript: _ManeTranscript,
    cds_features: tuple[_CdsFeature, ...],
    *,
    reference_store: ReferenceSequenceStore,
    sequence_id_field: str,
    nonstandard_codon_policy: str,
    invalid_cds_policy: str,
) -> Esm1bManeProteinContext | None:
    protein_id = _single_optional_value(feature.protein_id for feature in cds_features)
    ensembl_protein_id = _single_optional_value(
        feature.ensembl_protein_id for feature in cds_features
    )
    sequence_id = _sequence_id(
        sequence_id_field,
        transcript=transcript,
        protein_id=protein_id,
        ensembl_protein_id=ensembl_protein_id,
    )
    coding_bases = _coding_bases(transcript, cds_features, reference_store)
    if len(coding_bases) % 3 != 0:
        if invalid_cds_policy == "skip":
            return None
        raise Esm1bManeContextError(
            f"CDS length is not divisible by 3 for MANE transcript {transcript.transcript_id}"
        )

    protein_sequence: list[str] = []
    contexts: list[Esm1bManeCodonContext] = []
    nonstandard_count = 0
    codon_count = len(coding_bases) // 3
    for codon_index in range(codon_count):
        codon_items = coding_bases[codon_index * 3 : codon_index * 3 + 3]
        ref_codon = "".join(base for base, _position in codon_items)
        positions = tuple(position for _base, position in codon_items)
        residue = translate_codon(ref_codon)
        protein_position = codon_index + 1
        is_terminal_stop = residue == "*" and codon_index == codon_count - 1
        if residue == "*":
            if is_terminal_stop:
                continue
            nonstandard_count += 1
            if nonstandard_codon_policy == "fail":
                raise Esm1bManeContextError(
                    "internal stop or nonstandard codon found in MANE CDS: "
                    f"{transcript.gene} {transcript.transcript_id} position {protein_position}"
                )
            protein_sequence.append("X")
            continue
        protein_sequence.append(residue)
        contexts.append(
            Esm1bManeCodonContext(
                uniprot_isoform=sequence_id,
                protein_position=protein_position,
                chrom=transcript.chrom,
                ref_codon=ref_codon,
                codon_positions=positions,
                strand=transcript.strand,
                mane_tx=transcript.transcript_id,
                gene=transcript.gene,
            )
        )
    if not protein_sequence:
        raise Esm1bManeContextError(
            f"MANE transcript {transcript.transcript_id} produced an empty protein sequence"
        )
    return Esm1bManeProteinContext(
        sequence_id=sequence_id,
        sequence_id_field=sequence_id_field,
        gene=transcript.gene,
        mane_tx=transcript.transcript_id,
        chrom=transcript.chrom,
        strand=transcript.strand,
        protein_id=protein_id,
        ensembl_protein_id=ensembl_protein_id,
        protein_sequence="".join(protein_sequence),
        contexts=tuple(contexts),
        nonstandard_codon_count=nonstandard_count,
    )


def _coding_bases(
    transcript: _ManeTranscript,
    cds_features: tuple[_CdsFeature, ...],
    reference_store: ReferenceSequenceStore,
) -> list[tuple[str, int]]:
    ordered = sorted(
        cds_features,
        key=lambda feature: feature.start if transcript.strand == "+" else -feature.end,
    )
    bases: list[tuple[str, int]] = []
    for feature in ordered:
        window = reference_store.get_sequence(
            transcript.chrom,
            feature.start,
            feature.end,
            build="GRCh38",
        )
        sequence = str(window.sequence or "").upper()
        if len(sequence) != feature.end - feature.start + 1:
            raise Esm1bManeContextError(
                f"short reference read for {transcript.transcript_id} CDS segment"
            )
        if transcript.strand == "-":
            sequence = _reverse_complement(sequence)
            positions = range(feature.end, feature.start - 1, -1)
        else:
            positions = range(feature.start, feature.end + 1)
        bases.extend((base, position) for base, position in zip(sequence, positions))
    return bases


def _context_payload(context: Esm1bManeCodonContext) -> dict[str, object]:
    return {
        "uniprot_isoform": context.uniprot_isoform,
        "protein_position": context.protein_position,
        "chrom": context.chrom,
        "ref_codon": context.ref_codon,
        "codon_positions": list(context.codon_positions),
        "strand": context.strand,
        "mane_tx": context.mane_tx,
        "gene": context.gene,
    }


def _fasta_record(protein: Esm1bManeProteinContext) -> str:
    metadata = [
        f"gene={protein.gene}",
        f"mane_tx={protein.mane_tx}",
        f"sequence_id_field={protein.sequence_id_field}",
    ]
    if protein.protein_id:
        metadata.append(f"protein_id={protein.protein_id}")
    if protein.ensembl_protein_id:
        metadata.append(f"ensembl_protein_id={protein.ensembl_protein_id}")
    header = f">{protein.sequence_id} " + " ".join(metadata)
    return header + "\n" + "\n".join(wrap(protein.protein_sequence, width=80)) + "\n"


def _validate_sequence_id_field(value: str) -> str:
    text = value.strip()
    if text not in _SEQUENCE_ID_FIELDS:
        raise Esm1bManeContextError(
            "sequence_id_field must be one of: " + ", ".join(sorted(_SEQUENCE_ID_FIELDS))
        )
    return text


def _validate_nonstandard_policy(value: str) -> str:
    text = value.strip()
    if text not in _NONSTANDARD_POLICIES:
        raise Esm1bManeContextError(
            "nonstandard_codon_policy must be one of: " + ", ".join(sorted(_NONSTANDARD_POLICIES))
        )
    return text


def _validate_invalid_cds_policy(value: str) -> str:
    text = value.strip()
    if text not in _INVALID_CDS_POLICIES:
        raise Esm1bManeContextError(
            "invalid_cds_policy must be one of: " + ", ".join(sorted(_INVALID_CDS_POLICIES))
        )
    return text


def _sequence_id(
    field: str,
    *,
    transcript: _ManeTranscript,
    protein_id: str | None,
    ensembl_protein_id: str | None,
) -> str:
    value = {
        "protein_id": protein_id,
        "ensembl_protein_id": ensembl_protein_id,
        "mane_tx": transcript.transcript_id,
    }[field]
    if value is None or not value.strip():
        raise Esm1bManeContextError(
            f"MANE transcript {transcript.transcript_id} is missing sequence id field {field}"
        )
    return value.strip()


def _single_optional_value(values: Iterable[str | None]) -> str | None:
    cleaned = tuple(dict.fromkeys(value.strip() for value in values if value and value.strip()))
    if not cleaned:
        return None
    if len(cleaned) > 1:
        raise Esm1bManeContextError("CDS segments disagree on protein identifier")
    return cleaned[0]


def _parse_gff_attributes(raw: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for item in raw.split(";"):
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        attrs[key] = unquote(value)
    return attrs


def _attribute_values(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(value.strip() for value in raw.split(",") if value.strip())


def _transcript_id(feature_type: str, attrs: Mapping[str, str]) -> str | None:
    if feature_type == "mRNA":
        transcript_id = attrs.get("transcript_id") or attrs.get("Name")
        raw_id = attrs.get("ID", "")
        if not transcript_id and raw_id.startswith("rna-"):
            transcript_id = raw_id.removeprefix("rna-")
        return transcript_id or None
    parent = attrs.get("Parent", "")
    if parent.startswith("rna-"):
        return parent.removeprefix("rna-")
    return attrs.get("transcript_id") or None


def _ensembl_protein_id(attrs: Mapping[str, str]) -> str | None:
    for value in _attribute_values(attrs.get("Dbxref")):
        if value.startswith("Ensembl:ENSP"):
            return value.split(":", 1)[1]
    return None


def _normalize_chromosome(chrom: str) -> str:
    text = chrom.strip()
    return text[3:] if text.lower().startswith("chr") else text


def _is_primary_chromosome(chrom: str) -> bool:
    normalized = _normalize_chromosome(chrom).upper()
    if normalized in {"X", "Y", "M", "MT"}:
        return True
    try:
        number = int(normalized)
    except ValueError:
        return False
    return 1 <= number <= 22


def _reverse_complement(sequence: str) -> str:
    return sequence.translate(_COMPLEMENT)[::-1]


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise Esm1bManeContextError(f"{field_name} is required")


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _hash_file(path: Path) -> dict[str, str]:
    md5_digest = md5(usedforsecurity=False)
    sha256_digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8 * 1024 * 1024), b""):
            md5_digest.update(chunk)
            sha256_digest.update(chunk)
    return {"md5": md5_digest.hexdigest(), "sha256": sha256_digest.hexdigest()}


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
