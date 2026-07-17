from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path

import pytest

from app.services.esm1b_clean_regeneration import (
    ESM1B_CLEAN_SOURCE_ROUTE,
    Esm1bCleanRegenerationError,
    build_clean_esm1b_regeneration_fixture,
    ntranos_scoring_windows,
)


def test_clean_source_route_pins_official_inputs_and_keeps_release_gates() -> None:
    route = ESM1B_CLEAN_SOURCE_ROUTE
    payload = route.to_payload()

    assert route.model_name == "esm1b_t33_650M_UR50S"
    assert route.meta_commit == "2b369911bb5b4b0dda914521b9475cad1656b2ac"
    assert route.scorer_commit == "0c33758a5073e5d6e673d9a16a40e5b0af46851d"
    assert route.fair_esm_version == "2.0.0"
    assert route.minimum_overlap_residues == 512
    assert route.max_window_residues == 1022
    assert route.weighting_sigmoid_scale == 20
    assert route.mane_version == "MANE Select v1.5"
    assert route.patch_contig_policy == "exclude_with_explicit_ledger"
    assert route.mane_patch_contig_gene_count == 64
    assert payload["status"] == "fixture_only"
    assert "official_model_weight_sha256_required" in route.release_gates
    assert "materialization_upload_approval_required" in route.release_gates
    assert route.release_ready is False
    assert len(route.checksum()) == 64


def test_ntranos_scoring_windows_match_short_and_over_context_contract() -> None:
    short = ntranos_scoring_windows(1022)
    assert [(window.start, window.end) for window in short] == [(0, 1022)]
    assert set(short[0].normalized_weights) == {1.0}

    long = ntranos_scoring_windows(1023)
    assert [(window.start, window.end) for window in long] == [(0, 1022), (1, 1023)]
    expected_edge = 1 / (1 + math.exp(128 / 20))
    assert long[0].normalized_weights[1] == pytest.approx(1 / (1 + expected_edge))
    assert long[1].normalized_weights[0] == pytest.approx(expected_edge / (1 + expected_edge))

    for position in range(1023):
        total = sum(
            window.normalized_weights[position - window.start]
            for window in long
            if window.start <= position < window.end
        )
        assert total == pytest.approx(1.0)


def test_clean_fixture_worker_is_deterministic_disk_backed_and_raw_only(
    tmp_path: Path,
) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    _write_fixture_inputs(
        inputs,
        contexts=[_context(sequence_id="NP_TEST.1", transcript="NM_TEST.1")],
        scores=[("NP_TEST.1", "V1M", "-14.0000")],
    )

    first = build_clean_esm1b_regeneration_fixture(
        input_root=inputs,
        score_csv_path=Path("scores.csv"),
        context_jsonl_path=Path("contexts.jsonl"),
        context_manifest_path=Path("contexts.manifest.json"),
        scorer_proof_path=Path("scores.proof.json"),
        output_root=tmp_path / "out-a",
    )
    second = build_clean_esm1b_regeneration_fixture(
        input_root=inputs,
        score_csv_path=Path("scores.csv"),
        context_jsonl_path=Path("contexts.jsonl"),
        context_manifest_path=Path("contexts.manifest.json"),
        scorer_proof_path=Path("scores.proof.json"),
        output_root=tmp_path / "out-b",
    )

    expected = (
        "1\t100\tG\tA\t-14\tNP_TEST.1\trefseq\tNM_TEST.1\tV1M\tTEST\t" "NP_TEST.1\tENSPTEST\t\n"
    )
    assert first.raw_tsv_path.read_text(encoding="utf-8") == expected
    assert second.raw_tsv_path.read_bytes() == first.raw_tsv_path.read_bytes()
    assert second.manifest_path.read_bytes() == first.manifest_path.read_bytes()
    assert second.manifest_sha256 == first.manifest_sha256

    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert manifest["output_contract"]["acmg_band_embedded"] is False
    assert "acmg_band" not in manifest["output_contract"]["columns"]
    assert manifest["resource_contract"]["streamed_input"] is True
    assert manifest["resource_contract"]["disk_backed_join"] == "sqlite"
    assert manifest["resource_contract"]["external_sort"] == "sqlite_order_by"
    assert manifest["score_provenance"]["precomputed_score_archive_used"] is False
    assert manifest["guardrails"]["local_path_values_emitted"] is False
    assert manifest["guardrails"]["secret_values_emitted"] is False
    assert manifest["fixture_only"] is True
    assert manifest["public_serialization_allowed"] is False
    assert first.to_sanitized_dict()["local_path_values_emitted"] is False


def test_clean_fixture_worker_retains_contextual_duplicate_genomic_keys(
    tmp_path: Path,
) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    _write_fixture_inputs(
        inputs,
        contexts=[
            _context(sequence_id="NP_ONE.1", transcript="NM_ONE.1", gene="ONE"),
            _context(sequence_id="NP_TWO.1", transcript="NM_TWO.1", gene="TWO"),
        ],
        scores=[
            ("NP_ONE.1", "V1M", "-14"),
            ("NP_TWO.1", "V1M", "-12.2"),
        ],
    )

    result = _build(inputs, tmp_path / "out")
    rows = result.raw_tsv_path.read_text(encoding="utf-8").splitlines()

    assert len(rows) == 2
    assert [row.split("\t")[:4] for row in rows] == [
        ["1", "100", "G", "A"],
        ["1", "100", "G", "A"],
    ]
    assert {row.split("\t")[7] for row in rows} == {"NM_ONE.1", "NM_TWO.1"}
    assert result.duplicate_genomic_key_count == 1


def test_clean_fixture_worker_fails_closed_on_duplicate_contexts(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    context = _context(sequence_id="NP_TEST.1", transcript="NM_TEST.1")
    _write_fixture_inputs(
        inputs,
        contexts=[context, context],
        scores=[("NP_TEST.1", "V1M", "-14")],
    )

    with pytest.raises(Esm1bCleanRegenerationError, match="duplicate or conflicting"):
        _build(inputs, tmp_path / "out")


def test_clean_fixture_worker_rejects_checksum_mismatch_and_forbidden_archive(
    tmp_path: Path,
) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    _write_fixture_inputs(
        inputs,
        contexts=[_context(sequence_id="NP_TEST.1", transcript="NM_TEST.1")],
        scores=[("NP_TEST.1", "V1M", "-14")],
    )
    proof_path = inputs / "scores.proof.json"
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    proof["score_sha256"] = "f" * 64
    proof_path.write_text(json.dumps(proof), encoding="utf-8")

    with pytest.raises(Esm1bCleanRegenerationError, match="score CSV checksum mismatch"):
        _build(inputs, tmp_path / "out-hash")

    _write_fixture_inputs(
        inputs,
        contexts=[_context(sequence_id="NP_TEST.1", transcript="NM_TEST.1")],
        scores=[("NP_TEST.1", "V1M", "-14")],
        proof_updates={"source_note": "CC BY-NC precomputed score archive"},
    )
    with pytest.raises(Esm1bCleanRegenerationError, match="forbidden score source"):
        _build(inputs, tmp_path / "out-forbidden")


def test_clean_fixture_worker_rejects_symlinked_inputs(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    _write_fixture_inputs(
        inputs,
        contexts=[_context(sequence_id="NP_TEST.1", transcript="NM_TEST.1")],
        scores=[("NP_TEST.1", "V1M", "-14")],
    )
    (inputs / "scores-link.csv").symlink_to(inputs / "scores.csv")

    with pytest.raises(Esm1bCleanRegenerationError, match="symlink"):
        build_clean_esm1b_regeneration_fixture(
            input_root=inputs,
            score_csv_path=Path("scores-link.csv"),
            context_jsonl_path=Path("contexts.jsonl"),
            context_manifest_path=Path("contexts.manifest.json"),
            scorer_proof_path=Path("scores.proof.json"),
            output_root=tmp_path / "out",
        )


def test_clean_fixture_worker_bounds_memory_by_batch_size(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    contexts = [
        _context(
            sequence_id="NP_STREAM.1",
            transcript="NM_STREAM.1",
            protein_position=position,
            genomic_start=position * 3 + 100,
        )
        for position in range(1, 601)
    ]
    scores = [
        ("NP_STREAM.1", f"V{position}M", str(-10 - position / 1000)) for position in range(1, 601)
    ]
    _write_fixture_inputs(inputs, contexts=contexts, scores=scores)

    result = _build(inputs, tmp_path / "out")
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.input_score_row_count == 600
    assert result.row_count == 600
    assert result.max_buffered_rows <= 500
    assert manifest["resource_contract"]["max_buffered_rows"] <= 500


def test_clean_fixture_worker_enforces_fixture_row_limits(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    _write_fixture_inputs(
        inputs,
        contexts=[
            _context(
                sequence_id="NP_LIMIT.1",
                transcript="NM_LIMIT.1",
                protein_position=position,
                genomic_start=position * 3 + 100,
            )
            for position in (1, 2)
        ],
        scores=[("NP_LIMIT.1", "V1M", "-14")],
    )

    with pytest.raises(Esm1bCleanRegenerationError, match="context JSONL exceeds"):
        build_clean_esm1b_regeneration_fixture(
            input_root=inputs,
            score_csv_path=Path("scores.csv"),
            context_jsonl_path=Path("contexts.jsonl"),
            context_manifest_path=Path("contexts.manifest.json"),
            scorer_proof_path=Path("scores.proof.json"),
            output_root=tmp_path / "out-context-limit",
            max_score_rows=1,
        )

    with pytest.raises(Esm1bCleanRegenerationError, match="fixture-only limit"):
        build_clean_esm1b_regeneration_fixture(
            input_root=inputs,
            score_csv_path=Path("scores.csv"),
            context_jsonl_path=Path("contexts.jsonl"),
            context_manifest_path=Path("contexts.manifest.json"),
            scorer_proof_path=Path("scores.proof.json"),
            output_root=tmp_path / "out-hard-limit",
            max_score_rows=100_001,
        )


def _build(inputs: Path, output: Path):
    return build_clean_esm1b_regeneration_fixture(
        input_root=inputs,
        score_csv_path=Path("scores.csv"),
        context_jsonl_path=Path("contexts.jsonl"),
        context_manifest_path=Path("contexts.manifest.json"),
        scorer_proof_path=Path("scores.proof.json"),
        output_root=output,
    )


def _write_fixture_inputs(
    root: Path,
    *,
    contexts: list[dict[str, object]],
    scores: list[tuple[str, str, str]],
    proof_updates: dict[str, object] | None = None,
) -> None:
    context_path = root / "contexts.jsonl"
    context_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in contexts),
        encoding="utf-8",
    )
    score_path = root / "scores.csv"
    score_path.write_text(
        "seq_id,mut_name,esm_score\n"
        + "".join(f"{seq_id},{mutation},{score}\n" for seq_id, mutation, score in scores),
        encoding="utf-8",
    )
    protein_fasta_sha256 = "a" * 64
    context_manifest = {
        "source_id": "esm1b_mane_codon_contexts",
        "manifest_schema_version": "2",
        "context_sha256": _hash(context_path),
        "protein_fasta_sha256": protein_fasta_sha256,
        "mane_gff_sha256": "b" * 64,
        "reference_sha256": "c" * 64,
        "context_count": len(contexts),
        "primary_chromosomes_only": True,
        "patch_contig_policy": "exclude_with_explicit_ledger",
        "skipped_patch_gene_count": 0,
        "precomputed_huggingface_score_zip_used": False,
        "fixture_only": True,
    }
    (root / "contexts.manifest.json").write_text(
        json.dumps(context_manifest, sort_keys=True),
        encoding="utf-8",
    )
    proof = {
        "source_id": "esm1b_clean_local_scores",
        "proof_schema_version": "1",
        "score_sha256": _hash(score_path),
        "score_row_count": len(scores),
        "protein_fasta_sha256": protein_fasta_sha256,
        "score_generation_method": ESM1B_CLEAN_SOURCE_ROUTE.score_method,
        "model_name": ESM1B_CLEAN_SOURCE_ROUTE.model_name,
        "model_weight_sha256": None,
        "meta_commit": ESM1B_CLEAN_SOURCE_ROUTE.meta_commit,
        "scorer_commit": ESM1B_CLEAN_SOURCE_ROUTE.scorer_commit,
        "environment_lock_sha256": "d" * 64,
        "container_digest": None,
        "long_protein_window": {
            "max_residues": 1022,
            "minimum_overlap_residues": 512,
            "sigmoid_scale": 20,
        },
        "precomputed_score_archive_used": False,
        "fixture_only": True,
        "numerical_parity_status": "fixture_not_run",
    }
    proof.update(proof_updates or {})
    (root / "scores.proof.json").write_text(
        json.dumps(proof, sort_keys=True),
        encoding="utf-8",
    )


def _context(
    *,
    sequence_id: str,
    transcript: str,
    gene: str = "TEST",
    protein_position: int = 1,
    genomic_start: int = 100,
) -> dict[str, object]:
    return {
        "protein_sequence_id": sequence_id,
        "protein_sequence_id_namespace": "refseq",
        "protein_position": protein_position,
        "chrom": "chr1",
        "ref_codon": "GTG",
        "codon_positions": [genomic_start, genomic_start + 1, genomic_start + 2],
        "strand": "+",
        "mane_tx": transcript,
        "gene": gene,
        "refseq_protein_id": sequence_id,
        "ensembl_protein_id": f"ENSP{gene}",
        "uniprot_isoform_id": None,
    }


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
