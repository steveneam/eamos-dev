from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import sqlite3
from tempfile import TemporaryDirectory
from typing import Any, Iterator, Mapping, Sequence

from app.services.esm1b_assembly import (
    Esm1bAssemblyError,
    esm1b_genomic_snv_rows,
    parse_esm1b_mutation_name,
)


class Esm1bCleanRegenerationError(ValueError):
    """Raised when a clean ESM-1b build input or artifact cannot be trusted."""


@dataclass(frozen=True)
class Esm1bCleanSourceRoute:
    route_id: str
    route_schema_version: str
    model_name: str
    model_weight_url: str
    model_weight_sha256: str | None
    model_weight_size_bytes: int
    model_weight_etag: str
    contact_regression_url: str
    contact_regression_sha256: str
    meta_repository_url: str
    meta_commit: str
    scorer_repository_url: str
    scorer_commit: str
    fair_esm_version: str
    torch_version: str
    python_version: str
    numpy_version: str
    pandas_version: str
    biopython_version: str
    scorer_container_digest: str | None
    score_method: str
    max_window_residues: int
    minimum_overlap_residues: int
    weighting_sigmoid_scale: int
    mane_version: str
    mane_gff_url: str
    mane_gff_sha256: str
    grch38_reference_url: str
    grch38_reference_sha256: str
    patch_contig_policy: str
    mane_patch_contig_gene_count: int

    @property
    def release_gates(self) -> tuple[str, ...]:
        gates: list[str] = []
        if self.model_weight_sha256 is None:
            gates.append("official_model_weight_sha256_required")
        if self.scorer_container_digest is None:
            gates.append("scorer_container_digest_required")
        gates.extend(
            (
                "scorer_numerical_parity_required",
                "sequence_context_transport_validation_required",
                "independent_clinical_calibration_validation_required",
                "full_runtime_asset_validation_required",
                "materialization_upload_approval_required",
            )
        )
        return tuple(gates)

    @property
    def release_ready(self) -> bool:
        return not self.release_gates

    def to_payload(self) -> dict[str, object]:
        return {
            "route_id": self.route_id,
            "route_schema_version": self.route_schema_version,
            "status": "release_ready" if self.release_ready else "fixture_only",
            "model": {
                "name": self.model_name,
                "weight_url": self.model_weight_url,
                "weight_sha256": self.model_weight_sha256,
                "weight_size_bytes": self.model_weight_size_bytes,
                "weight_etag_non_checksum": self.model_weight_etag,
                "contact_regression_url": self.contact_regression_url,
                "contact_regression_sha256": self.contact_regression_sha256,
                "repository_url": self.meta_repository_url,
                "repository_commit": self.meta_commit,
            },
            "scorer": {
                "repository_url": self.scorer_repository_url,
                "repository_commit": self.scorer_commit,
                "method": self.score_method,
                "model_mode": "eval",
                "dtype": "float32",
                "gradient_mode": "no_grad",
                "device": "cuda",
                "determinism": {
                    "python_hash_seed": 0,
                    "torch_manual_seed": 0,
                    "cuda_manual_seed_all": 0,
                    "use_deterministic_algorithms": True,
                    "cudnn_deterministic": True,
                    "cudnn_benchmark": False,
                },
                "long_protein_window": {
                    "max_residues": self.max_window_residues,
                    "minimum_overlap_residues": self.minimum_overlap_residues,
                    "sigmoid_scale": self.weighting_sigmoid_scale,
                },
            },
            "environment": {
                "python": self.python_version,
                "fair_esm": self.fair_esm_version,
                "torch": self.torch_version,
                "numpy": self.numpy_version,
                "pandas": self.pandas_version,
                "biopython": self.biopython_version,
                "container_digest": self.scorer_container_digest,
            },
            "sequence_inputs": {
                "scope": "MANE Select missense SNVs",
                "mane_version": self.mane_version,
                "mane_gff_url": self.mane_gff_url,
                "mane_gff_sha256": self.mane_gff_sha256,
                "reference_build": "GRCh38",
                "reference_url": self.grch38_reference_url,
                "reference_sha256": self.grch38_reference_sha256,
                "patch_contig_policy": self.patch_contig_policy,
                "mane_patch_contig_gene_count": self.mane_patch_contig_gene_count,
            },
            "identifier_contract": {
                "protein_sequence_id": "neutral join identifier",
                "refseq_protein_id": "separate optional identifier",
                "ensembl_protein_id": "separate optional identifier",
                "uniprot_isoform_id": "separate optional identifier",
            },
            "forbidden_inputs": [
                "CC BY-NC precomputed ESM-1b score archive",
                "Hugging Face Space precomputed score ZIP",
            ],
            "release_gates": list(self.release_gates),
        }

    def checksum(self) -> str:
        return _canonical_json_sha256(self.to_payload())


ESM1B_CLEAN_SOURCE_ROUTE = Esm1bCleanSourceRoute(
    route_id="esm1b_clean_mane_select_v1",
    route_schema_version="1",
    model_name="esm1b_t33_650M_UR50S",
    model_weight_url=("https://dl.fbaipublicfiles.com/fair-esm/models/esm1b_t33_650M_UR50S.pt"),
    # Meta publishes a multipart S3 ETag, not a SHA-256. Acquiring the 7.8 GB
    # object and pinning its SHA-256 is an explicit operator/materialization gate.
    model_weight_sha256=None,
    model_weight_size_bytes=7_828_576_466,
    model_weight_etag="80558ee238433d05fafc92b4a447b41d-934",
    contact_regression_url=(
        "https://dl.fbaipublicfiles.com/fair-esm/regression/"
        "esm1b_t33_650M_UR50S-contact-regression.pt"
    ),
    contact_regression_sha256=("77193a8814f0db0b36a03aebb1a311adc6b4745f463c04839defc15407bbb28a"),
    meta_repository_url="https://github.com/facebookresearch/esm",
    meta_commit="2b369911bb5b4b0dda914521b9475cad1656b2ac",
    scorer_repository_url="https://github.com/ntranoslab/esm-variants",
    scorer_commit="0c33758a5073e5d6e673d9a16a40e5b0af46851d",
    fair_esm_version="2.0.0",
    torch_version="1.12.1+cu116",
    python_version="3.10.13",
    numpy_version="1.23.5",
    pandas_version="1.5.3",
    biopython_version="1.81",
    scorer_container_digest=None,
    score_method="wild_type_marginal_log_likelihood_ratio",
    max_window_residues=1022,
    # The pinned scorer invokes get_intervals_and_weights(min_overlap=512,
    # max_len=1022, s=20), even though the helper's unused default is 511.
    minimum_overlap_residues=512,
    weighting_sigmoid_scale=20,
    mane_version="MANE Select v1.5",
    mane_gff_url=(
        "https://ftp.ncbi.nlm.nih.gov/refseq/MANE/MANE_human/release_1.5/"
        "MANE.GRCh38.v1.5.refseq_genomic.gff.gz"
    ),
    mane_gff_sha256="040f0d4056de2e9a416cd52bc20ff07ef403baadf5f5968faf188907893f6002",
    grch38_reference_url=("https://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/hg38.2bit"),
    grch38_reference_sha256=("1f67aaa17a77b327738fe750ab37430a85dddf73c7d9189385ad1839259acec0"),
    patch_contig_policy="exclude_with_explicit_ledger",
    mane_patch_contig_gene_count=64,
)


@dataclass(frozen=True)
class Esm1bScoringWindow:
    start: int
    end: int
    normalized_weights: tuple[float, ...]


@dataclass(frozen=True)
class Esm1bCleanRegenerationResult:
    raw_tsv_path: Path
    shards_path: Path
    build_log_path: Path
    manifest_path: Path
    manifest_sha256: str
    row_count: int
    input_score_row_count: int
    duplicate_genomic_key_count: int
    max_buffered_rows: int

    def to_sanitized_dict(self) -> dict[str, object]:
        return {
            "raw_tsv_file_name": self.raw_tsv_path.name,
            "shards_directory_name": self.shards_path.name,
            "build_log_file_name": self.build_log_path.name,
            "manifest_file_name": self.manifest_path.name,
            "manifest_sha256": self.manifest_sha256,
            "row_count": self.row_count,
            "input_score_row_count": self.input_score_row_count,
            "duplicate_genomic_key_count": self.duplicate_genomic_key_count,
            "max_buffered_rows": self.max_buffered_rows,
            "local_path_values_emitted": False,
            "secret_values_emitted": False,
        }


_OUTPUT_COLUMNS = (
    "chrom",
    "position",
    "ref",
    "alt",
    "esm1b_llr",
    "protein_sequence_id",
    "protein_sequence_id_namespace",
    "mane_tx",
    "aa_sub",
    "gene",
    "refseq_protein_id",
    "ensembl_protein_id",
    "uniprot_isoform_id",
)
_PRIMARY_CHROMS = tuple(str(value) for value in range(1, 23)) + ("X", "Y")
_CHROM_RANK = {chrom: index for index, chrom in enumerate(_PRIMARY_CHROMS, start=1)}
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_SAFE_GENE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CONTAINER_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_SOURCE_TOKENS = (
    "score_zip",
    "score zip",
    "cc by-nc",
    "cc-by-nc",
    "huggingface.co/spaces/ntranos",
    "esm1b_t33_650m_ur50s.csv.zip",
)
_CONTEXT_LINE_LIMIT = 32 * 1024
_SCORE_LINE_LIMIT = 16 * 1024
_JSON_FILE_LIMIT = 1024 * 1024
_BATCH_SIZE = 500
_MAX_FIXTURE_ROWS = 100_000


def ntranos_scoring_windows(
    sequence_length: int,
    *,
    minimum_overlap: int = 512,
    max_length: int = 1022,
    sigmoid_scale: int = 20,
) -> tuple[Esm1bScoringWindow, ...]:
    """Mirror the pinned ntranos long-protein tiling and normalized weights."""

    if sequence_length < 1:
        raise Esm1bCleanRegenerationError("sequence_length must be positive")
    if max_length < 2 or minimum_overlap < 1 or minimum_overlap >= max_length:
        raise Esm1bCleanRegenerationError("invalid long-protein window parameters")
    if sigmoid_scale < 1:
        raise Esm1bCleanRegenerationError("sigmoid_scale must be positive")
    if sequence_length <= max_length:
        return (
            Esm1bScoringWindow(
                start=0,
                end=sequence_length,
                normalized_weights=(1.0,) * sequence_length,
            ),
        )

    intervals = _ntranos_intervals(
        tuple(range(sequence_length)),
        minimum_overlap=minimum_overlap,
        max_length=max_length,
        parts=(),
    )
    intervals = tuple(
        (segment[0], segment[-1] + 1) for segment in sorted(intervals, key=lambda item: item[0])
    )
    a = int(round(minimum_overlap / 2))
    edge_positions = tuple(range(a))

    middle_filter = [1.0] * max_length
    for index in edge_positions:
        middle_filter[index] = 1 / (1 + math.exp(-((index - a / 2) / sigmoid_scale)))
        middle_filter[max_length - a + index] = 1 / (1 + math.exp((index - a / 2) / sigmoid_scale))
    first_filter = [1.0] * max_length
    first_filter[max_length - a :] = middle_filter[max_length - a :]
    last_filter = [1.0] * max_length
    last_filter[:a] = middle_filter[:a]

    filters: list[Sequence[float]] = [first_filter]
    filters.extend(middle_filter for _item in intervals[1:-1])
    filters.append(last_filter)
    totals = [0.0] * sequence_length
    for interval, weights in zip(intervals, filters):
        for offset, position in enumerate(range(interval[0], interval[1])):
            totals[position] += weights[offset]
    if any(total <= 0 for total in totals):
        raise Esm1bCleanRegenerationError("long-protein windows do not cover every residue")

    windows: list[Esm1bScoringWindow] = []
    for interval, weights in zip(intervals, filters):
        normalized = tuple(
            weights[offset] / totals[position]
            for offset, position in enumerate(range(interval[0], interval[1]))
        )
        windows.append(
            Esm1bScoringWindow(
                start=interval[0],
                end=interval[1],
                normalized_weights=normalized,
            )
        )
    return tuple(windows)


def build_clean_esm1b_regeneration_fixture(
    *,
    input_root: Path,
    score_csv_path: Path,
    context_jsonl_path: Path,
    context_manifest_path: Path,
    scorer_proof_path: Path,
    output_root: Path,
    source_route: Esm1bCleanSourceRoute = ESM1B_CLEAN_SOURCE_ROUTE,
    max_score_rows: int = 100_000,
) -> Esm1bCleanRegenerationResult:
    """Build deterministic raw ESM-1b shards from small, synthetic fixtures.

    This path intentionally cannot create the public/runtime bgzip asset. The
    resulting manifest carries every unresolved scientific and operator gate.
    """

    if max_score_rows < 1:
        raise Esm1bCleanRegenerationError("max_score_rows must be positive")
    if max_score_rows > _MAX_FIXTURE_ROWS:
        raise Esm1bCleanRegenerationError(
            f"max_score_rows cannot exceed the fixture-only limit of {_MAX_FIXTURE_ROWS}"
        )
    input_root = _trusted_root(input_root, require_existing=True)
    score_csv_path = _safe_input_path(input_root, score_csv_path)
    context_jsonl_path = _safe_input_path(input_root, context_jsonl_path)
    context_manifest_path = _safe_input_path(input_root, context_manifest_path)
    scorer_proof_path = _safe_input_path(input_root, scorer_proof_path)
    output_root = _trusted_root(output_root, require_existing=False)

    score_sha256 = _sha256_file(score_csv_path)
    context_sha256 = _sha256_file(context_jsonl_path)
    context_manifest_sha256 = _sha256_file(context_manifest_path)
    scorer_proof_sha256 = _sha256_file(scorer_proof_path)
    context_manifest = _load_small_json(context_manifest_path)
    scorer_proof = _load_small_json(scorer_proof_path)
    _validate_context_manifest(
        context_manifest,
        context_sha256=context_sha256,
        source_route=source_route,
        fixture_only=True,
    )
    _validate_scorer_proof(
        scorer_proof,
        score_sha256=score_sha256,
        protein_fasta_sha256=_required_sha256(
            context_manifest.get("protein_fasta_sha256"),
            "context manifest protein_fasta_sha256",
        ),
        source_route=source_route,
        fixture_only=True,
    )

    fixed_targets = (
        output_root / "esm1b_hg38.raw.tsv",
        output_root / "esm1b_clean.build.jsonl",
        output_root / "esm1b_clean.manifest.json",
        output_root / "shards",
    )
    if any(target.exists() or target.is_symlink() for target in fixed_targets):
        raise Esm1bCleanRegenerationError("refusing to overwrite an existing build artifact")

    max_buffered_rows = 0
    with TemporaryDirectory(prefix=".esm1b-clean-", dir=output_root) as temporary:
        staging = Path(temporary)
        database_path = staging / "join.sqlite3"
        connection = sqlite3.connect(database_path)
        try:
            _configure_sqlite(connection)
            _create_tables(connection)
            context_count, context_max = _load_contexts(
                connection,
                context_jsonl_path,
                max_context_rows=max_score_rows,
            )
            max_buffered_rows = max(max_buffered_rows, context_max)
            expected_context_count = _required_positive_int(
                context_manifest.get("context_count"),
                "context manifest context_count",
            )
            if context_count != expected_context_count:
                raise Esm1bCleanRegenerationError(
                    "context row count does not match its verified manifest"
                )
            score_count, score_max = _load_scores(
                connection,
                score_csv_path,
                max_score_rows=max_score_rows,
            )
            max_buffered_rows = max(max_buffered_rows, score_max)
            expected_score_count = _required_positive_int(
                scorer_proof.get("score_row_count"),
                "scorer proof score_row_count",
            )
            if score_count != expected_score_count:
                raise Esm1bCleanRegenerationError(
                    "score row count does not match its verified scorer proof"
                )
            missing_context_count = connection.execute("""
                SELECT COUNT(*)
                FROM scores AS scores
                LEFT JOIN contexts AS contexts
                  ON contexts.protein_sequence_id = scores.protein_sequence_id
                 AND contexts.protein_position = scores.protein_position
                WHERE contexts.protein_sequence_id IS NULL
                """).fetchone()[0]
            if missing_context_count:
                raise Esm1bCleanRegenerationError(
                    "one or more score rows have no exact MANE codon context"
                )
            emitted_count, without_snv_count, output_max = _build_output_rows(connection)
            max_buffered_rows = max(max_buffered_rows, output_max)
            if emitted_count < 1:
                raise Esm1bCleanRegenerationError("fixture produced zero genomic SNV rows")
            duplicate_genomic_key_count = connection.execute("""
                SELECT COUNT(*) FROM (
                    SELECT chrom, position, ref, alt
                    FROM output_rows
                    GROUP BY chrom, position, ref, alt
                    HAVING COUNT(*) > 1
                )
                """).fetchone()[0]

            staged_shards = staging / "shards"
            staged_shards.mkdir()
            shard_records = _write_shards(connection, staged_shards)
            staged_raw = staging / "esm1b_hg38.raw.tsv"
            _concatenate_shards(shard_records, staged_shards, staged_raw)
            raw_sha256 = _sha256_file(staged_raw)

            build_log_records = (
                {
                    "step": "source_route_validated",
                    "source_route_sha256": source_route.checksum(),
                },
                {
                    "step": "allowlisted_inputs_verified",
                    "score_csv_sha256": score_sha256,
                    "context_jsonl_sha256": context_sha256,
                    "context_manifest_sha256": context_manifest_sha256,
                    "scorer_proof_sha256": scorer_proof_sha256,
                    "precomputed_score_archive_used": False,
                },
                {
                    "step": "disk_backed_join_complete",
                    "context_row_count": context_count,
                    "score_row_count": score_count,
                    "score_rows_without_genomic_snv": without_snv_count,
                    "output_row_count": emitted_count,
                },
                {
                    "step": "external_genomic_sort_complete",
                    "shard_count": len(shard_records),
                    "final_raw_sha256": raw_sha256,
                },
            )
            staged_log = staging / "esm1b_clean.build.jsonl"
            _write_jsonl(staged_log, build_log_records)
            build_log_sha256 = _sha256_file(staged_log)

            build_id = _canonical_json_sha256(
                {
                    "route": source_route.checksum(),
                    "score": score_sha256,
                    "context": context_sha256,
                    "proof": scorer_proof_sha256,
                    "raw": raw_sha256,
                }
            )
            manifest_payload = {
                "source_id": "esm1b_clean_regenerated_scores",
                "manifest_schema_version": "2",
                "build_id": build_id,
                "source_route": source_route.to_payload(),
                "source_route_sha256": source_route.checksum(),
                "fixture_only": True,
                "public_serialization_allowed": False,
                "runtime_activation_allowed": False,
                "launch_gates": list(source_route.release_gates),
                "inputs": {
                    "score_csv_sha256": score_sha256,
                    "context_jsonl_sha256": context_sha256,
                    "context_manifest_sha256": context_manifest_sha256,
                    "scorer_proof_sha256": scorer_proof_sha256,
                    "protein_fasta_sha256": context_manifest["protein_fasta_sha256"],
                    "mane_gff_sha256": context_manifest["mane_gff_sha256"],
                    "reference_sha256": context_manifest["reference_sha256"],
                },
                "score_provenance": {
                    "generation_method": source_route.score_method,
                    "meta_commit": scorer_proof["meta_commit"],
                    "scorer_commit": scorer_proof["scorer_commit"],
                    "model_weight_sha256": scorer_proof.get("model_weight_sha256"),
                    "environment_lock_sha256": scorer_proof["environment_lock_sha256"],
                    "container_digest": scorer_proof.get("container_digest"),
                    "numerical_parity_status": scorer_proof["numerical_parity_status"],
                    "precomputed_score_archive_used": False,
                },
                "scope": {
                    "mane_version": source_route.mane_version,
                    "reference_build": "GRCh38",
                    "variant_class": "missense_snv",
                    "primary_chromosomes_only": True,
                    "patch_contig_policy": source_route.patch_contig_policy,
                    "skipped_patch_gene_count": context_manifest["skipped_patch_gene_count"],
                },
                "output_contract": {
                    "columns": list(_OUTPUT_COLUMNS),
                    "score_field": "raw_model_score",
                    "acmg_band_embedded": False,
                    "sort_order": [
                        "chromosome_natural",
                        "position",
                        "ref",
                        "alt",
                        "gene",
                        "mane_tx",
                        "protein_sequence_id",
                        "aa_sub",
                    ],
                    "duplicate_genomic_keys": "retained_with_transcript_and_protein_context",
                    "bgzip_tabix_status": "not_materialized",
                },
                "counts": {
                    "context_rows": context_count,
                    "input_score_rows": score_count,
                    "score_rows_without_genomic_snv": without_snv_count,
                    "output_rows": emitted_count,
                    "duplicate_genomic_key_count": duplicate_genomic_key_count,
                },
                "shards": shard_records,
                "final_raw": {
                    "file_name": staged_raw.name,
                    "size_bytes": staged_raw.stat().st_size,
                    "sha256": raw_sha256,
                },
                "build_log": {
                    "file_name": staged_log.name,
                    "sha256": build_log_sha256,
                },
                "resource_contract": {
                    "streamed_input": True,
                    "disk_backed_join": "sqlite",
                    "external_sort": "sqlite_order_by",
                    "batch_size": _BATCH_SIZE,
                    "max_buffered_rows": max_buffered_rows,
                },
                "guardrails": {
                    "precomputed_score_archive_used": False,
                    "storage_upload": "not_used",
                    "supabase_metadata_mutation": "not_used",
                    "provider_flip": "not_used",
                    "startup_download": "not_used",
                    "request_time_materialization": "not_used",
                    "local_path_values_emitted": False,
                    "secret_values_emitted": False,
                },
            }
            staged_manifest = staging / "esm1b_clean.manifest.json"
            staged_manifest.write_text(
                json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            manifest_sha256 = _sha256_file(staged_manifest)
        finally:
            connection.close()

        final_raw = output_root / staged_raw.name
        final_log = output_root / staged_log.name
        final_manifest = output_root / staged_manifest.name
        final_shards = output_root / "shards"
        staged_raw.replace(final_raw)
        staged_log.replace(final_log)
        staged_manifest.replace(final_manifest)
        staged_shards.replace(final_shards)

    return Esm1bCleanRegenerationResult(
        raw_tsv_path=final_raw,
        shards_path=final_shards,
        build_log_path=final_log,
        manifest_path=final_manifest,
        manifest_sha256=manifest_sha256,
        row_count=emitted_count,
        input_score_row_count=score_count,
        duplicate_genomic_key_count=duplicate_genomic_key_count,
        max_buffered_rows=max_buffered_rows,
    )


def _ntranos_intervals(
    remaining: tuple[int, ...],
    *,
    minimum_overlap: int,
    max_length: int,
    parts: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, ...], ...]:
    if len(remaining) <= max_length:
        if parts[-2][-1] - parts[-1][0] < minimum_overlap:
            center = remaining[int(len(remaining) / 2)]
            half = int(max_length / 2)
            return parts + (tuple(range(center - half, center + half)),)
        return parts
    next_parts = parts + (remaining[:max_length], remaining[-max_length:])
    chopped = remaining[max_length - minimum_overlap : -max_length + minimum_overlap]
    return _ntranos_intervals(
        chopped,
        minimum_overlap=minimum_overlap,
        max_length=max_length,
        parts=next_parts,
    )


def _configure_sqlite(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA temp_store=FILE")
    connection.execute("PRAGMA cache_size=-32768")


def _create_tables(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE contexts (
            protein_sequence_id TEXT NOT NULL,
            protein_position INTEGER NOT NULL,
            protein_sequence_id_namespace TEXT NOT NULL,
            chrom TEXT NOT NULL,
            chrom_rank INTEGER NOT NULL,
            ref_codon TEXT NOT NULL,
            codon_position_1 INTEGER NOT NULL,
            codon_position_2 INTEGER NOT NULL,
            codon_position_3 INTEGER NOT NULL,
            strand TEXT NOT NULL,
            mane_tx TEXT NOT NULL,
            gene TEXT NOT NULL,
            refseq_protein_id TEXT,
            ensembl_protein_id TEXT,
            uniprot_isoform_id TEXT,
            PRIMARY KEY (protein_sequence_id, protein_position)
        ) WITHOUT ROWID;
        CREATE TABLE scores (
            protein_sequence_id TEXT NOT NULL,
            protein_position INTEGER NOT NULL,
            mutation_name TEXT NOT NULL,
            score_text TEXT NOT NULL,
            PRIMARY KEY (protein_sequence_id, mutation_name)
        ) WITHOUT ROWID;
        CREATE TABLE output_rows (
            chrom TEXT NOT NULL,
            chrom_rank INTEGER NOT NULL,
            position INTEGER NOT NULL,
            ref TEXT NOT NULL,
            alt TEXT NOT NULL,
            score_text TEXT NOT NULL,
            protein_sequence_id TEXT NOT NULL,
            protein_sequence_id_namespace TEXT NOT NULL,
            mane_tx TEXT NOT NULL,
            aa_sub TEXT NOT NULL,
            gene TEXT NOT NULL,
            refseq_protein_id TEXT,
            ensembl_protein_id TEXT,
            uniprot_isoform_id TEXT,
            PRIMARY KEY (
                chrom, position, ref, alt, protein_sequence_id, mane_tx, aa_sub
            )
        ) WITHOUT ROWID;
        CREATE INDEX output_genomic_sort ON output_rows (
            chrom_rank, position, ref, alt, gene, mane_tx, protein_sequence_id, aa_sub
        );
        """)


def _load_contexts(
    connection: sqlite3.Connection,
    path: Path,
    *,
    max_context_rows: int,
) -> tuple[int, int]:
    insert = """
        INSERT INTO contexts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    batch: list[tuple[object, ...]] = []
    count = 0
    max_buffered = 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(
                _bounded_lines(handle, _CONTEXT_LINE_LIMIT, "context JSONL"),
                start=1,
            ):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise Esm1bCleanRegenerationError(
                        f"context JSONL contains invalid JSON at line {line_number}"
                    ) from exc
                count += 1
                if count > max_context_rows:
                    raise Esm1bCleanRegenerationError("context JSONL exceeds the fixture row limit")
                batch.append(_validated_context_row(payload))
                max_buffered = max(max_buffered, len(batch))
                if len(batch) >= _BATCH_SIZE:
                    connection.executemany(insert, batch)
                    batch.clear()
            if batch:
                connection.executemany(insert, batch)
            connection.commit()
    except sqlite3.IntegrityError as exc:
        raise Esm1bCleanRegenerationError(
            "duplicate or conflicting MANE codon context detected"
        ) from exc
    if count == 0:
        raise Esm1bCleanRegenerationError("context JSONL produced zero rows")
    return count, max_buffered


def _load_scores(
    connection: sqlite3.Connection,
    path: Path,
    *,
    max_score_rows: int,
) -> tuple[int, int]:
    insert = "INSERT INTO scores VALUES (?, ?, ?, ?)"
    batch: list[tuple[object, ...]] = []
    count = 0
    max_buffered = 0
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            lines = _bounded_lines(handle, _SCORE_LINE_LIMIT, "score CSV")
            header = next(lines, "").rstrip("\r\n")
            if header != "seq_id,mut_name,esm_score":
                raise Esm1bCleanRegenerationError(
                    "score CSV header must be exactly seq_id,mut_name,esm_score"
                )
            for line_number, line in enumerate(lines, start=2):
                stripped = line.rstrip("\r\n")
                if '"' in stripped:
                    raise Esm1bCleanRegenerationError(
                        "score CSV does not allow quoted or multiline fields"
                    )
                fields = stripped.split(",")
                if len(fields) != 3:
                    raise Esm1bCleanRegenerationError(
                        f"score CSV row has the wrong column count at line {line_number}"
                    )
                sequence_id = _safe_identifier(fields[0], "score sequence id")
                mutation_name = _safe_identifier(fields[1], "mutation name")
                try:
                    substitution = parse_esm1b_mutation_name(mutation_name)
                except Esm1bAssemblyError as exc:
                    raise Esm1bCleanRegenerationError(
                        f"score CSV contains invalid mutation at line {line_number}"
                    ) from exc
                score_text = _canonical_decimal(fields[2], "ESM-1b score")
                batch.append(
                    (
                        sequence_id,
                        substitution.protein_position,
                        mutation_name,
                        score_text,
                    )
                )
                count += 1
                if count > max_score_rows:
                    raise Esm1bCleanRegenerationError("score CSV exceeds the fixture row limit")
                max_buffered = max(max_buffered, len(batch))
                if len(batch) >= _BATCH_SIZE:
                    connection.executemany(insert, batch)
                    batch.clear()
            if batch:
                connection.executemany(insert, batch)
            connection.commit()
    except sqlite3.IntegrityError as exc:
        raise Esm1bCleanRegenerationError("duplicate ESM-1b score row detected") from exc
    if count == 0:
        raise Esm1bCleanRegenerationError("score CSV produced zero rows")
    return count, max_buffered


def _build_output_rows(connection: sqlite3.Connection) -> tuple[int, int, int]:
    query = """
        SELECT
            scores.protein_sequence_id,
            scores.mutation_name,
            scores.score_text,
            contexts.protein_sequence_id_namespace,
            contexts.chrom,
            contexts.chrom_rank,
            contexts.ref_codon,
            contexts.codon_position_1,
            contexts.codon_position_2,
            contexts.codon_position_3,
            contexts.strand,
            contexts.mane_tx,
            contexts.gene,
            contexts.refseq_protein_id,
            contexts.ensembl_protein_id,
            contexts.uniprot_isoform_id
        FROM scores
        JOIN contexts
          ON contexts.protein_sequence_id = scores.protein_sequence_id
         AND contexts.protein_position = scores.protein_position
        ORDER BY scores.protein_sequence_id, scores.mutation_name
    """
    insert = "INSERT INTO output_rows VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    batch: list[tuple[object, ...]] = []
    emitted_count = 0
    without_snv_count = 0
    max_buffered = 0
    try:
        for row in connection.execute(query):
            (
                sequence_id,
                mutation_name,
                score_text,
                sequence_namespace,
                chrom,
                chrom_rank,
                ref_codon,
                position_1,
                position_2,
                position_3,
                strand,
                mane_tx,
                gene,
                refseq_protein_id,
                ensembl_protein_id,
                uniprot_isoform_id,
            ) = row
            substitution = parse_esm1b_mutation_name(mutation_name)
            mapped = esm1b_genomic_snv_rows(
                chrom=chrom,
                ref_codon=ref_codon,
                codon_positions=(position_1, position_2, position_3),
                strand=strand,
                substitution=substitution,
                esm1b_llr=float(Decimal(score_text)),
                uniprot_isoform=sequence_id,
                mane_tx=mane_tx,
            )
            if not mapped:
                without_snv_count += 1
                continue
            for genomic in mapped:
                batch.append(
                    (
                        genomic.chrom,
                        chrom_rank,
                        genomic.position,
                        genomic.ref,
                        genomic.alt,
                        score_text,
                        sequence_id,
                        sequence_namespace,
                        mane_tx,
                        mutation_name,
                        gene,
                        refseq_protein_id,
                        ensembl_protein_id,
                        uniprot_isoform_id,
                    )
                )
                emitted_count += 1
                max_buffered = max(max_buffered, len(batch))
                if len(batch) >= _BATCH_SIZE:
                    connection.executemany(insert, batch)
                    batch.clear()
        if batch:
            connection.executemany(insert, batch)
        connection.commit()
    except (sqlite3.IntegrityError, Esm1bAssemblyError) as exc:
        raise Esm1bCleanRegenerationError(
            "duplicate output context or codon reconciliation failure"
        ) from exc
    return emitted_count, without_snv_count, max_buffered


def _write_shards(
    connection: sqlite3.Connection,
    shards_path: Path,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    chroms = tuple(
        row[0]
        for row in connection.execute("SELECT DISTINCT chrom FROM output_rows ORDER BY chrom_rank")
    )
    for index, chrom in enumerate(chroms, start=1):
        file_name = f"part-{index:03d}-chr{chrom}.tsv"
        path = shards_path / file_name
        row_count = 0
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in connection.execute(
                """
                SELECT chrom, position, ref, alt, score_text,
                       protein_sequence_id, protein_sequence_id_namespace,
                       mane_tx, aa_sub, gene, refseq_protein_id,
                       ensembl_protein_id, uniprot_isoform_id
                FROM output_rows
                WHERE chrom = ?
                ORDER BY chrom_rank, position, ref, alt, gene, mane_tx,
                         protein_sequence_id, aa_sub
                """,
                (chrom,),
            ):
                handle.write("\t".join("" if value is None else str(value) for value in row))
                handle.write("\n")
                row_count += 1
        records.append(
            {
                "file_name": file_name,
                "chrom": chrom,
                "row_count": row_count,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    return records


def _concatenate_shards(
    shard_records: Sequence[Mapping[str, object]],
    shards_path: Path,
    target: Path,
) -> None:
    with target.open("wb") as output:
        for record in shard_records:
            source = shards_path / str(record["file_name"])
            with source.open("rb") as handle:
                for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                    output.write(chunk)


def _validated_context_row(payload: object) -> tuple[object, ...]:
    if not isinstance(payload, dict):
        raise Esm1bCleanRegenerationError("context JSONL row must be an object")
    sequence_id = _safe_identifier(payload.get("protein_sequence_id"), "protein sequence id")
    namespace = str(payload.get("protein_sequence_id_namespace") or "").strip()
    if namespace not in {"refseq", "ensembl", "mane_transcript", "uniprot"}:
        raise Esm1bCleanRegenerationError("invalid protein sequence id namespace")
    protein_position = _required_positive_int(
        payload.get("protein_position"),
        "protein position",
    )
    chrom = _normalize_primary_chrom(payload.get("chrom"))
    ref_codon = str(payload.get("ref_codon") or "").strip().upper()
    if len(ref_codon) != 3 or any(base not in "ACGT" for base in ref_codon):
        raise Esm1bCleanRegenerationError("context row has an invalid reference codon")
    positions = payload.get("codon_positions")
    if (
        not isinstance(positions, list)
        or len(positions) != 3
        or any(not isinstance(value, int) or value < 1 for value in positions)
        or len(set(positions)) != 3
    ):
        raise Esm1bCleanRegenerationError("context row has invalid codon positions")
    strand = str(payload.get("strand") or "").strip()
    if strand not in {"+", "-"}:
        raise Esm1bCleanRegenerationError("context row has an invalid strand")
    mane_tx = _safe_identifier(payload.get("mane_tx"), "MANE transcript")
    gene = _safe_gene(payload.get("gene"))
    refseq = _optional_identifier(payload.get("refseq_protein_id"))
    ensembl = _optional_identifier(payload.get("ensembl_protein_id"))
    uniprot = _optional_identifier(payload.get("uniprot_isoform_id"))
    required_identity = {
        "refseq": refseq,
        "ensembl": ensembl,
        "mane_transcript": mane_tx,
        "uniprot": uniprot,
    }[namespace]
    if sequence_id != required_identity:
        raise Esm1bCleanRegenerationError(
            "protein sequence id does not match its declared identifier namespace"
        )
    return (
        sequence_id,
        protein_position,
        namespace,
        chrom,
        _CHROM_RANK[chrom],
        ref_codon,
        positions[0],
        positions[1],
        positions[2],
        strand,
        mane_tx,
        gene,
        refseq,
        ensembl,
        uniprot,
    )


def _validate_context_manifest(
    payload: Mapping[str, object],
    *,
    context_sha256: str,
    source_route: Esm1bCleanSourceRoute,
    fixture_only: bool,
) -> None:
    if payload.get("source_id") != "esm1b_mane_codon_contexts":
        raise Esm1bCleanRegenerationError("unexpected context manifest source id")
    if payload.get("manifest_schema_version") != "2":
        raise Esm1bCleanRegenerationError("unsupported context manifest schema")
    if payload.get("context_sha256") != context_sha256:
        raise Esm1bCleanRegenerationError("context JSONL checksum mismatch")
    _required_sha256(payload.get("protein_fasta_sha256"), "protein FASTA checksum")
    _required_sha256(payload.get("mane_gff_sha256"), "MANE GFF checksum")
    _required_sha256(payload.get("reference_sha256"), "reference checksum")
    if payload.get("primary_chromosomes_only") is not True:
        raise Esm1bCleanRegenerationError(
            "clean ESM-1b context manifest must use primary chromosomes only"
        )
    if payload.get("patch_contig_policy") != source_route.patch_contig_policy:
        raise Esm1bCleanRegenerationError("context patch-contig policy mismatch")
    skipped = payload.get("skipped_patch_gene_count")
    if not isinstance(skipped, int) or skipped < 0:
        raise Esm1bCleanRegenerationError("context manifest lacks a skipped patch ledger")
    if payload.get("precomputed_huggingface_score_zip_used") is not False:
        raise Esm1bCleanRegenerationError("forbidden precomputed score archive marker")
    if fixture_only:
        if payload.get("fixture_only") is not True:
            raise Esm1bCleanRegenerationError("fixture context manifest must be fixture-only")
    else:
        if payload.get("mane_version") != source_route.mane_version:
            raise Esm1bCleanRegenerationError("MANE version mismatch")
        if payload.get("mane_gff_sha256") != source_route.mane_gff_sha256:
            raise Esm1bCleanRegenerationError("MANE GFF is not the allowlisted input")
        if payload.get("reference_sha256") != source_route.grch38_reference_sha256:
            raise Esm1bCleanRegenerationError("reference is not the allowlisted input")
        if skipped != source_route.mane_patch_contig_gene_count:
            raise Esm1bCleanRegenerationError("patch-contig skipped ledger is incomplete")


def _validate_scorer_proof(
    payload: Mapping[str, object],
    *,
    score_sha256: str,
    protein_fasta_sha256: str,
    source_route: Esm1bCleanSourceRoute,
    fixture_only: bool,
) -> None:
    serialized = json.dumps(payload, sort_keys=True).casefold()
    if any(token in serialized for token in _FORBIDDEN_SOURCE_TOKENS):
        raise Esm1bCleanRegenerationError("scorer proof names a forbidden score source")
    if payload.get("source_id") != "esm1b_clean_local_scores":
        raise Esm1bCleanRegenerationError("unexpected scorer proof source id")
    if payload.get("proof_schema_version") != "1":
        raise Esm1bCleanRegenerationError("unsupported scorer proof schema")
    if payload.get("score_sha256") != score_sha256:
        raise Esm1bCleanRegenerationError("score CSV checksum mismatch")
    if payload.get("protein_fasta_sha256") != protein_fasta_sha256:
        raise Esm1bCleanRegenerationError("scorer proof protein FASTA mismatch")
    if payload.get("score_generation_method") != source_route.score_method:
        raise Esm1bCleanRegenerationError("scorer method mismatch")
    if payload.get("model_name") != source_route.model_name:
        raise Esm1bCleanRegenerationError("scorer model mismatch")
    if payload.get("meta_commit") != source_route.meta_commit:
        raise Esm1bCleanRegenerationError("Meta code commit mismatch")
    if payload.get("scorer_commit") != source_route.scorer_commit:
        raise Esm1bCleanRegenerationError("scorer code commit mismatch")
    if payload.get("precomputed_score_archive_used") is not False:
        raise Esm1bCleanRegenerationError("precomputed score archives are forbidden")
    window = payload.get("long_protein_window")
    if not isinstance(window, dict) or window != {
        "max_residues": source_route.max_window_residues,
        "minimum_overlap_residues": source_route.minimum_overlap_residues,
        "sigmoid_scale": source_route.weighting_sigmoid_scale,
    }:
        raise Esm1bCleanRegenerationError("long-protein scoring contract mismatch")
    _required_sha256(payload.get("environment_lock_sha256"), "environment lock checksum")
    if fixture_only:
        if payload.get("fixture_only") is not True:
            raise Esm1bCleanRegenerationError("fixture scorer proof must be fixture-only")
        if payload.get("numerical_parity_status") != "fixture_not_run":
            raise Esm1bCleanRegenerationError("fixture scorer proof has an invalid parity state")
    else:
        if not source_route.release_ready:
            raise Esm1bCleanRegenerationError("source route is not release-ready")
        if payload.get("model_weight_sha256") != source_route.model_weight_sha256:
            raise Esm1bCleanRegenerationError("model weight checksum mismatch")
        if payload.get("container_digest") != source_route.scorer_container_digest:
            raise Esm1bCleanRegenerationError("scorer container digest mismatch")
        if not _CONTAINER_DIGEST_RE.fullmatch(str(payload.get("container_digest") or "")):
            raise Esm1bCleanRegenerationError("invalid scorer container digest")
        if payload.get("numerical_parity_status") != "passed":
            raise Esm1bCleanRegenerationError("scorer numerical parity has not passed")


def _trusted_root(path: Path, *, require_existing: bool) -> Path:
    raw = path.expanduser().absolute()
    _reject_symlink_components(raw)
    if require_existing:
        if not raw.is_dir():
            raise Esm1bCleanRegenerationError("trusted input root is not a directory")
    else:
        raw.mkdir(parents=True, exist_ok=True)
        if not raw.is_dir():
            raise Esm1bCleanRegenerationError("output root is not a directory")
    return raw.resolve(strict=True)


def _safe_input_path(root: Path, path: Path) -> Path:
    candidate = path if path.is_absolute() else root / path
    candidate = Path(os.path.abspath(candidate))
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise Esm1bCleanRegenerationError("input path escapes the trusted root") from exc
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise Esm1bCleanRegenerationError("input path cannot contain symlinks")
    if not candidate.is_file():
        raise Esm1bCleanRegenerationError("required input is not a regular file")
    return candidate


def _load_small_json(path: Path) -> dict[str, object]:
    if path.stat().st_size > _JSON_FILE_LIMIT:
        raise Esm1bCleanRegenerationError("proof manifest exceeds size limit")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Esm1bCleanRegenerationError("proof manifest is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise Esm1bCleanRegenerationError("proof manifest must be a JSON object")
    return payload


def _bounded_lines(handle: Any, limit: int, label: str) -> Iterator[str]:
    while True:
        line = handle.readline(limit + 1)
        if not line:
            return
        if len(line) > limit and not line.endswith("\n"):
            raise Esm1bCleanRegenerationError(f"{label} row exceeds size limit")
        if len(line.encode("utf-8")) > limit:
            raise Esm1bCleanRegenerationError(f"{label} row exceeds size limit")
        yield line


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.exists() and current.is_symlink():
            raise Esm1bCleanRegenerationError("trusted path cannot contain symlinks")


def _normalize_primary_chrom(value: object) -> str:
    text = str(value or "").strip()
    if text.casefold().startswith("chr"):
        text = text[3:]
    text = text.upper()
    if text not in _CHROM_RANK:
        raise Esm1bCleanRegenerationError("context row is not on a primary chromosome")
    return text


def _safe_identifier(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    if not _SAFE_ID_RE.fullmatch(text):
        raise Esm1bCleanRegenerationError(f"{field_name} has an invalid shape")
    return text


def _optional_identifier(value: object) -> str | None:
    if value is None or not str(value).strip():
        return None
    return _safe_identifier(value, "optional protein identifier")


def _safe_gene(value: object) -> str:
    text = str(value or "").strip().upper()
    if not _SAFE_GENE_RE.fullmatch(text):
        raise Esm1bCleanRegenerationError("gene has an invalid shape")
    return text


def _canonical_decimal(value: object, field_name: str) -> str:
    raw = str(value or "").strip()
    if not raw or len(raw) > 64:
        raise Esm1bCleanRegenerationError(f"{field_name} has an invalid length")
    try:
        number = Decimal(raw)
    except (InvalidOperation, AttributeError) as exc:
        raise Esm1bCleanRegenerationError(f"{field_name} is not numeric") from exc
    if not number.is_finite():
        raise Esm1bCleanRegenerationError(f"{field_name} must be finite")
    if abs(number) > Decimal("10000") or len(number.as_tuple().digits) > 32:
        raise Esm1bCleanRegenerationError(f"{field_name} is outside the accepted range")
    if number == 0:
        return "0"
    return format(number.normalize(), "f")


def _required_positive_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise Esm1bCleanRegenerationError(f"{field_name} must be a positive integer")
    return value


def _required_sha256(value: object, field_name: str) -> str:
    text = str(value or "").strip().lower()
    if not _SHA256_RE.fullmatch(text):
        raise Esm1bCleanRegenerationError(f"{field_name} is not a SHA-256")
    return text


def _write_jsonl(path: Path, records: Sequence[Mapping[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, separators=(",", ":"), sort_keys=True))
            handle.write("\n")


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256(encoded).hexdigest()
