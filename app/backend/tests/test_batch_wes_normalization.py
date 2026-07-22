from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.schemas.batch import BatchAlleleV2
from app.services.batch_engine.normalization import (
    BatchNormalizationFailed,
    BatchNormalizationUnavailable,
    BcftoolsBatchNormalizer,
)


def test_bcftools_normalizer_uses_fixed_argv_and_immutable_reference(
    monkeypatch,
    tmp_path: Path,
) -> None:
    executable, reference, digest = _runtime_files(tmp_path)
    calls: list[tuple[list[str], dict]] = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "##fileformat=VCFv4.2\n"
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
                "1\t9\t.\tAC\tA\t.\tPASS\t.\n"
            ),
            stderr="",
        )

    monkeypatch.setattr("app.services.batch_engine.normalization.subprocess.run", fake_run)
    normalizer = BcftoolsBatchNormalizer(
        executable=executable,
        reference_fasta=reference,
        reference_release="GRCh38.p14-test",
        reference_manifest_id="grch38-test-manifest",
        reference_sha256=digest,
        algorithm_version="1.20-test",
        validation_matrix_id="batch-normalization-test",
    )
    result = normalizer.normalize(
        BatchAlleleV2(
            genome_build="GRCh38",
            chromosome="1",
            position=10,
            reference="C",
            alternate="A",
        ),
        source_record_index=4,
    )

    assert result.status == "normalized"
    assert result.normalized is not None and result.normalized.position == 9
    assert result.reference_sha256 == digest
    command, kwargs = calls[0]
    assert command == [
        str(executable.resolve()),
        "norm",
        "--check-ref",
        "e",
        "--fasta-ref",
        str(reference.resolve()),
        "--multiallelics",
        "-any",
        "--output-type",
        "v",
        command[-1],
    ]
    assert Path(command[-1]).name == "input.vcf"
    assert kwargs.get("shell") in {None, False}
    assert kwargs["timeout"] == 15.0
    assert kwargs["env"] == {"LC_ALL": "C", "LANG": "C"}
    disclosure = normalizer.disclosure()
    assert disclosure.execution == "mounted_artifact"
    assert disclosure.validation_status == "validated"


def test_bcftools_normalizer_requires_fasta_index_and_exact_digest(tmp_path: Path) -> None:
    executable, reference, digest = _runtime_files(tmp_path)
    Path(f"{reference}.fai").unlink()
    with pytest.raises(BatchNormalizationUnavailable, match="unavailable"):
        BcftoolsBatchNormalizer(
            executable=executable,
            reference_fasta=reference,
            reference_release="GRCh38.p14-test",
            reference_manifest_id="grch38-test-manifest",
            reference_sha256=digest,
            algorithm_version="1.20-test",
        )

    Path(f"{reference}.fai").write_text("1\t1\t0\t1\t2\n", encoding="ascii")
    with pytest.raises(BatchNormalizationUnavailable, match="unavailable"):
        BcftoolsBatchNormalizer(
            executable=executable,
            reference_fasta=reference,
            reference_release="GRCh38.p14-test",
            reference_manifest_id="grch38-test-manifest",
            reference_sha256="0" * 64,
            algorithm_version="1.20-test",
        )


def test_bcftools_failure_is_typed_without_releasing_raw_diagnostics(
    monkeypatch,
    tmp_path: Path,
) -> None:
    executable, reference, digest = _runtime_files(tmp_path)
    normalizer = BcftoolsBatchNormalizer(
        executable=executable,
        reference_fasta=reference,
        reference_release="GRCh38.p14-test",
        reference_manifest_id="grch38-test-manifest",
        reference_sha256=digest,
        algorithm_version="1.20-test",
    )

    def fail_run(*_args, **_kwargs):
        raise OSError("SECRET_PATIENT_PATH")

    monkeypatch.setattr("app.services.batch_engine.normalization.subprocess.run", fail_run)
    with pytest.raises(BatchNormalizationFailed) as exc:
        normalizer.normalize(
            BatchAlleleV2(
                genome_build="GRCh38",
                chromosome="1",
                position=10,
                reference="A",
                alternate="C",
            ),
            source_record_index=0,
        )
    assert "SECRET_PATIENT_PATH" not in str(exc.value)


def _runtime_files(tmp_path: Path) -> tuple[Path, Path, str]:
    executable = tmp_path / "bcftools"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="ascii")
    executable.chmod(0o700)
    reference = tmp_path / "GRCh38.fa"
    reference.write_text(">1\nA\n", encoding="ascii")
    Path(f"{reference}.fai").write_text("1\t1\t3\t1\t2\n", encoding="ascii")
    digest = sha256(reference.read_bytes()).hexdigest()
    return executable, reference, digest
