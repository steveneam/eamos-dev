from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Protocol

from app.schemas.batch import BatchAlleleIdentityV2, BatchAlleleV2
from app.schemas.capabilities import CapabilityExecutionDisclosureV2


class BatchNormalizationUnavailable(RuntimeError):
    def __init__(self, requirements: tuple[str, ...]) -> None:
        super().__init__("Batch reference normalization is unavailable.")
        self.requirements = requirements


class BatchNormalizationFailed(RuntimeError):
    pass


class BatchAlleleNormalizer(Protocol):
    reference_release: str

    def disclosure(self) -> CapabilityExecutionDisclosureV2: ...

    def normalize(
        self,
        allele: BatchAlleleV2,
        *,
        source_record_index: int,
    ) -> BatchAlleleIdentityV2: ...


@dataclass(frozen=True)
class UnavailableBatchNormalizer:
    reference_release: str = "GRCh38.p14-required"
    requirements: tuple[str, ...] = (
        "mount a checksum-verified GRCh38 reference FASTA with index",
        "install the pinned bcftools runtime",
        "configure the immutable reference manifest and functional preflight",
    )

    def disclosure(self) -> CapabilityExecutionDisclosureV2:
        return CapabilityExecutionDisclosureV2(
            capability_id="batch.variant_normalization",
            claim="GRCh38 REF validation, multiallelic split, and left normalization",
            execution="unavailable",
            input_scope="grch38_snv_short_indel",
            source_status="unavailable",
            source_release=self.reference_release,
            applicability="applicable",
            validation_status="unvalidated",
            retention="none",
            consent_required=False,
            warnings=["Batch rows are not annotated without verified reference normalization."],
            requirements=list(self.requirements),
        )

    def normalize(
        self,
        allele: BatchAlleleV2,
        *,
        source_record_index: int,
    ) -> BatchAlleleIdentityV2:
        del allele, source_record_index
        raise BatchNormalizationUnavailable(self.requirements)


class BcftoolsBatchNormalizer:
    """Fixed-argv ``bcftools norm`` adapter over an immutable GRCh38 FASTA."""

    algorithm_id = "bcftools_norm"

    def __init__(
        self,
        *,
        executable: Path,
        reference_fasta: Path,
        reference_release: str,
        reference_manifest_id: str,
        reference_sha256: str,
        algorithm_version: str,
        validation_matrix_id: str | None = None,
        timeout_seconds: float = 15.0,
        verify_reference_digest: bool = True,
    ) -> None:
        self.executable = executable.resolve()
        self.reference_fasta = reference_fasta.resolve()
        self.reference_release = reference_release
        self.reference_manifest_id = reference_manifest_id
        self.reference_sha256 = reference_sha256.lower()
        self.algorithm_version = algorithm_version
        self.validation_matrix_id = validation_matrix_id
        self.timeout_seconds = max(1.0, min(float(timeout_seconds), 120.0))
        if not self.executable.is_file() or not os.access(self.executable, os.X_OK):
            raise BatchNormalizationUnavailable(("install the pinned bcftools executable",))
        if not self.reference_fasta.is_file():
            raise BatchNormalizationUnavailable(("mount the configured GRCh38 reference FASTA",))
        reference_index = Path(f"{self.reference_fasta}.fai")
        if not reference_index.is_file():
            raise BatchNormalizationUnavailable(
                ("mount the samtools-compatible index for the configured GRCh38 FASTA",)
            )
        if verify_reference_digest and _sha256_file(self.reference_fasta) != self.reference_sha256:
            raise BatchNormalizationUnavailable(
                ("replace the GRCh38 reference whose digest failed verification",)
            )

    def disclosure(self) -> CapabilityExecutionDisclosureV2:
        return CapabilityExecutionDisclosureV2(
            capability_id="batch.variant_normalization",
            claim="GRCh38 REF validation, multiallelic split, and left normalization",
            execution="mounted_artifact",
            algorithm_id=self.algorithm_id,
            algorithm_version=self.algorithm_version,
            input_scope="grch38_snv_short_indel",
            source_status="source_backed",
            source_record_ids=[self.reference_manifest_id],
            source_release=self.reference_release,
            artifact_manifest_id=self.reference_manifest_id,
            artifact_sha256=self.reference_sha256,
            applicability="applicable",
            validation_status="validated" if self.validation_matrix_id else "unvalidated",
            validation_matrix_id=self.validation_matrix_id,
            retention="none",
            consent_required=False,
            warnings=[],
            requirements=[],
        )

    def normalize(
        self,
        allele: BatchAlleleV2,
        *,
        source_record_index: int,
    ) -> BatchAlleleIdentityV2:
        with tempfile.TemporaryDirectory(prefix="eamos-batch-norm-") as directory:
            input_path = Path(directory) / "input.vcf"
            input_path.write_text(_single_record_vcf(allele), encoding="ascii")
            command = [
                str(self.executable),
                "norm",
                "--check-ref",
                "e",
                "--fasta-ref",
                str(self.reference_fasta),
                "--multiallelics",
                "-any",
                "--output-type",
                "v",
                str(input_path),
            ]
            try:
                completed = subprocess.run(
                    command,
                    cwd=directory,
                    env={"LC_ALL": "C", "LANG": "C"},
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=self.timeout_seconds,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise BatchNormalizationFailed("bcftools normalization did not complete") from exc
        if completed.returncode != 0:
            stderr = completed.stderr.lower()
            status = "reference_mismatch" if "ref" in stderr and "mismatch" in stderr else "failed"
            return BatchAlleleIdentityV2(
                original=allele,
                normalized=None,
                status=status,
                source_record_index=source_record_index,
                normalization_algorithm_id=self.algorithm_id,
                normalization_algorithm_version=self.algorithm_version,
                reference_manifest_id=self.reference_manifest_id,
                reference_sha256=self.reference_sha256,
                warnings=[
                    (
                        "reference allele did not match the configured GRCh38 artifact"
                        if status == "reference_mismatch"
                        else "bcftools normalization failed without releasing raw diagnostics"
                    )
                ],
            )
        normalized = _parse_single_normalized_record(completed.stdout)
        return BatchAlleleIdentityV2(
            original=allele,
            normalized=normalized,
            status="normalized",
            source_record_index=source_record_index,
            normalization_algorithm_id=self.algorithm_id,
            normalization_algorithm_version=self.algorithm_version,
            reference_manifest_id=self.reference_manifest_id,
            reference_sha256=self.reference_sha256,
            warnings=[],
        )


def _single_record_vcf(allele: BatchAlleleV2) -> str:
    return (
        "##fileformat=VCFv4.2\n"
        f"##reference={allele.genome_build}\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        f"{allele.chromosome}\t{allele.position}\t.\t{allele.reference}\t"
        f"{allele.alternate}\t.\tPASS\t.\n"
    )


def _parse_single_normalized_record(output: str) -> BatchAlleleV2:
    rows = [line for line in output.splitlines() if line and not line.startswith("#")]
    if len(rows) != 1:
        raise BatchNormalizationFailed("bcftools returned an unexpected normalized row count")
    columns = rows[0].split("\t")
    if len(columns) < 5:
        raise BatchNormalizationFailed("bcftools returned a malformed normalized record")
    try:
        position = int(columns[1])
    except ValueError as exc:
        raise BatchNormalizationFailed(
            "bcftools returned an invalid normalized coordinate"
        ) from exc
    return BatchAlleleV2(
        genome_build="GRCh38",
        chromosome=columns[0].removeprefix("chr"),
        position=position,
        reference=columns[3],
        alternate=columns[4],
    )


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
