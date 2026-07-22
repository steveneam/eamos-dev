from __future__ import annotations

from dataclasses import dataclass
from gzip import BadGzipFile, GzipFile
from hashlib import sha256
import os
from pathlib import Path
import stat
import tempfile
import time
from typing import BinaryIO, Iterator
from urllib.parse import unquote

from app.schemas.batch import (
    BATCH_MAX_VARIANTS,
    BatchAlleleV2,
    BatchInputEnvelopeV2,
    BatchSampleProvenanceV2,
    ParsedVariant,
)
from app.services.vcf_ingest import VcfIngestLimitError

DEFAULT_MAX_RAW_RECORDS = 200_000
DEFAULT_MAX_DECOMPRESSED_BYTES_V2 = 512 * 1024 * 1024
DEFAULT_MAX_INTAKE_SECONDS = 120.0
_COPY_CHUNK_BYTES = 1024 * 1024
_MAX_VCF_LINE_BYTES = 4 * 1024 * 1024
_BCF_MAGIC = b"BCF\x02"
_GZIP_MAGIC = b"\x1f\x8b"
_BASES = frozenset("ACGTN")
_GVCF_ALTS = {"<NON_REF>", "<*>"}
_SUPPORTED_CONTIGS = frozenset({*(str(value) for value in range(1, 23)), "X", "Y", "MT"})


@dataclass(frozen=True)
class StagedVcf:
    """A server-private, single-use upload plus its immutable intake receipt."""

    path: Path
    envelope: BatchInputEnvelopeV2


@dataclass(frozen=True)
class StreamedVariant:
    """One split ALT from HTSlib without retaining a raw VCF line or sample name."""

    variant: ParsedVariant
    original_allele: BatchAlleleV2
    source_record_index: int
    quality: float | None
    samples: tuple[BatchSampleProvenanceV2, ...]


def stage_vcf_file(
    handle: BinaryIO,
    *,
    staging_dir: Path,
    filename: str | None,
    max_compressed_bytes: int,
    max_decompressed_bytes: int = DEFAULT_MAX_DECOMPRESSED_BYTES_V2,
    max_raw_records: int = DEFAULT_MAX_RAW_RECORDS,
    post_filter_variant_cap: int = BATCH_MAX_VARIANTS,
    max_intake_seconds: float = DEFAULT_MAX_INTAKE_SECONDS,
) -> StagedVcf:
    """Copy and inspect an upload without exposing its name or retaining rows.

    The returned path is an opaque server-generated file with mode ``0600``.
    Callers must remove it after the single create-job use or on expiry.
    """

    compressed_limit = max(1, int(max_compressed_bytes))
    decompressed_limit = max(1, int(max_decompressed_bytes))
    raw_record_limit = max(1, int(max_raw_records))
    candidate_cap = max(1, int(post_filter_variant_cap))
    deadline = time.monotonic() + max(1.0, min(float(max_intake_seconds), 600.0))
    staging_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(staging_dir, 0o700)
    except OSError:
        pass
    descriptor, raw_path = tempfile.mkstemp(prefix="batch-", suffix=".upload", dir=staging_dir)
    path = Path(raw_path)
    digest = sha256()
    compressed_bytes = 0
    try:
        os.chmod(path, 0o600)
        with os.fdopen(descriptor, "wb") as target:
            while True:
                chunk = handle.read(_COPY_CHUNK_BYTES)
                if not chunk:
                    break
                if time.monotonic() > deadline:
                    raise VcfIngestLimitError(
                        "Uploaded VCF intake exceeded the configured wall-time limit.",
                        code="vcf_intake_time_limit_exceeded",
                    )
                compressed_bytes += len(chunk)
                if compressed_bytes > compressed_limit:
                    raise VcfIngestLimitError(
                        "Uploaded VCF exceeds the configured compressed size limit.",
                        code="vcf_compressed_size_limit_exceeded",
                    )
                digest.update(chunk)
                target.write(chunk)
        if compressed_bytes == 0:
            raise VcfIngestLimitError("Uploaded VCF file is empty.", code="vcf_empty")

        magic = _read_magic(path)
        if magic.startswith(_BCF_MAGIC):
            raise VcfIngestLimitError(
                "BCF intake is unavailable until BCF parity is validated.",
                code="bcf_not_supported",
            )
        is_gzip = magic.startswith(_GZIP_MAGIC)
        inspection = _inspect_vcf_text(
            path,
            gzip_encoded=is_gzip,
            max_decompressed_bytes=decompressed_limit,
            max_raw_records=raw_record_limit,
            deadline_monotonic=deadline,
        )
        if inspection.sample_count == 0:
            raise VcfIngestLimitError(
                "WES Batch V2 requires a called-site VCF with one proband or small-family sample.",
                code="vcf_sample_columns_required",
            )
        if is_gzip:
            _replace_gzip_with_plaintext(
                path,
                max_decompressed_bytes=decompressed_limit,
                deadline_monotonic=deadline,
            )
        warnings = list(inspection.warnings)
        if filename and filename.lower().endswith(".bcf"):
            raise VcfIngestLimitError(
                "BCF intake is unavailable until BCF parity is validated.",
                code="bcf_not_supported",
            )
        envelope = BatchInputEnvelopeV2(
            format="vcf_gz" if is_gzip else "vcf",
            analysis_scope="wes",
            cohort_model=inspection.cohort_model,
            genome_build="GRCh38",
            source_sha256=digest.hexdigest(),
            compressed_bytes=compressed_bytes,
            decompressed_bytes=inspection.decompressed_bytes,
            raw_record_count=inspection.raw_record_count,
            sample_count=inspection.sample_count,
            post_filter_variant_cap=candidate_cap,
            accepted_variant_classes=sorted(inspection.variant_classes),
            warnings=warnings,
        )
        return StagedVcf(path=path, envelope=envelope)
    except Exception:
        path.unlink(missing_ok=True)
        raise


def remove_staged_vcf(staged: StagedVcf | None) -> None:
    if staged is not None:
        staged.path.unlink(missing_ok=True)


def cleanup_expired_staged_vcfs(
    staging_dir: Path,
    *,
    older_than_seconds: int,
    now_timestamp: float | None = None,
) -> int:
    """Remove only expired opaque uploads created by this intake module."""

    if not staging_dir.is_dir():
        return 0
    cutoff = (time.time() if now_timestamp is None else now_timestamp) - max(
        1, int(older_than_seconds)
    )
    removed = 0
    for path in staging_dir.glob("batch-*.upload"):
        try:
            metadata = path.stat(follow_symlinks=False)
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_mtime > cutoff:
            continue
        try:
            path.unlink()
        except FileNotFoundError:
            continue
        removed += 1
    return removed


def iter_staged_variants(staged: StagedVcf, *, upload_ref: str) -> Iterator[StreamedVariant]:
    """Yield split alleles through pysam/HTSlib with de-identified samples."""

    try:
        import pysam
    except ImportError as exc:  # pragma: no cover - pinned in supported Linux runtime
        raise VcfIngestLimitError(
            "Streaming VCF intake requires the pinned pysam runtime.",
            code="pysam_unavailable",
        ) from exc

    try:
        reader = pysam.VariantFile(str(staged.path))
    except Exception as exc:
        raise VcfIngestLimitError(
            "Uploaded VCF could not be opened by the HTSlib reader.",
            code="vcf_htslib_open_failed",
        ) from exc

    records_seen = 0
    try:
        sample_names = tuple(reader.header.samples)
        for source_index, record in enumerate(reader):
            records_seen += 1
            if records_seen > staged.envelope.raw_record_count:
                raise VcfIngestLimitError(
                    "Uploaded VCF changed after its intake receipt was issued.",
                    code="vcf_intake_receipt_mismatch",
                )
            chrom = _normalize_chrom(str(record.contig))
            _validate_contig(chrom)
            ref = str(record.ref or "").upper()
            alts = tuple(str(alt).upper() for alt in (record.alts or ()))
            if not chrom or record.pos < 1 or not ref or not alts:
                raise VcfIngestLimitError(
                    "Uploaded VCF contains a malformed variant record.",
                    code="vcf_malformed_record",
                )
            filter_value = _record_filter(record)
            gene = _info_gene(record.info)
            hgvs_c = _info_text(record.info, ("HGVS_C", "HGVSC"))
            variant = hgvs_c or _info_text(record.info, ("VARIANT", "HGVS"))
            af_values = _info_af_values(record.info)
            samples = _sample_provenance(
                record,
                sample_names=sample_names,
                upload_ref=upload_ref,
            )
            quality = _finite_float(record.qual)
            for alt_index, alt in enumerate(alts):
                _validate_alleles(ref, alt)
                warnings: list[str] = []
                if len(alts) > 1:
                    warnings.append("multiallelic_alt_split")
                if gene:
                    warnings.append("info_gene_is_unverified_provenance")
                info_af = af_values[alt_index] if alt_index < len(af_values) else None
                original = BatchAlleleV2(
                    genome_build="GRCh38",
                    chromosome=chrom,
                    position=record.pos,
                    reference=ref,
                    alternate=alt,
                )
                yield StreamedVariant(
                    variant=ParsedVariant(
                        raw=None,
                        query=f"{chrom}-{record.pos}-{ref}-{alt}",
                        gene=gene,
                        variant=variant,
                        chrom=chrom,
                        pos=record.pos,
                        ref=ref,
                        alt=alt,
                        filter=filter_value,
                        info_af=info_af,
                        source_index=source_index,
                        sample_id=None,
                        genotype=None,
                        warnings=warnings,
                    ),
                    original_allele=original,
                    source_record_index=source_index,
                    quality=quality,
                    samples=samples,
                )
        if records_seen != staged.envelope.raw_record_count:
            raise VcfIngestLimitError(
                "Uploaded VCF changed after its intake receipt was issued.",
                code="vcf_intake_receipt_mismatch",
            )
    except VcfIngestLimitError:
        raise
    except Exception as exc:
        raise VcfIngestLimitError(
            "Uploaded VCF could not be streamed by the HTSlib reader.",
            code="vcf_htslib_stream_failed",
        ) from exc
    finally:
        reader.close()


@dataclass(frozen=True)
class _Inspection:
    decompressed_bytes: int
    raw_record_count: int
    sample_count: int
    cohort_model: str
    variant_classes: frozenset[str]
    warnings: tuple[str, ...]


def _inspect_vcf_text(
    path: Path,
    *,
    gzip_encoded: bool,
    max_decompressed_bytes: int,
    max_raw_records: int,
    deadline_monotonic: float,
) -> _Inspection:
    decompressed_bytes = 0
    raw_record_count = 0
    sample_count = 0
    saw_header = False
    saw_explicit_grch38 = False
    variant_classes: set[str] = set()
    warnings: list[str] = []
    try:
        source = GzipFile(filename=str(path), mode="rb") if gzip_encoded else path.open("rb")
        with source:
            while True:
                raw_line = source.readline(_MAX_VCF_LINE_BYTES + 1)
                if not raw_line:
                    break
                if raw_record_count % 1024 == 0 and time.monotonic() > deadline_monotonic:
                    raise VcfIngestLimitError(
                        "Uploaded VCF intake exceeded the configured wall-time limit.",
                        code="vcf_intake_time_limit_exceeded",
                    )
                if len(raw_line) > _MAX_VCF_LINE_BYTES:
                    raise VcfIngestLimitError(
                        "Uploaded VCF contains a record larger than the line limit.",
                        code="vcf_line_size_limit_exceeded",
                    )
                decompressed_bytes += len(raw_line)
                if decompressed_bytes > max_decompressed_bytes:
                    raise VcfIngestLimitError(
                        "Uploaded VCF exceeds the configured decompressed size limit.",
                        code="vcf_decompressed_size_limit_exceeded",
                    )
                try:
                    line = raw_line.decode("utf-8-sig").strip()
                except UnicodeDecodeError as exc:
                    raise VcfIngestLimitError(
                        "Uploaded VCF must be valid UTF-8 text.",
                        code="vcf_invalid_encoding",
                    ) from exc
                if not line:
                    continue
                lower = line.lower()
                if line.startswith("##"):
                    if any(token in lower for token in ("grch37", "hg19", "b37")):
                        raise VcfIngestLimitError(
                            "Uploaded VCF uses hg19/GRCh37; WES Batch supports GRCh38 only.",
                            code="vcf_unsupported_genome_build",
                        )
                    if (lower.startswith("##reference=") or "assembly=" in lower) and any(
                        token in lower for token in ("grch38", "hg38")
                    ):
                        saw_explicit_grch38 = True
                    continue
                if line.startswith("#CHROM"):
                    columns = line.lstrip("#").split("\t")
                    if len(columns) < 8:
                        raise VcfIngestLimitError(
                            "Uploaded VCF has an invalid #CHROM header.",
                            code="vcf_invalid_header",
                        )
                    sample_count = max(0, len(columns) - 9)
                    if sample_count > 3:
                        raise VcfIngestLimitError(
                            "Cohort VCF input is unavailable; use a single sample or small family.",
                            code="cohort_vcf_not_supported",
                        )
                    saw_header = True
                    continue
                if line.startswith("#"):
                    continue
                if not saw_header:
                    raise VcfIngestLimitError(
                        "Uploaded VCF requires a #CHROM header before data rows.",
                        code="vcf_header_required",
                    )
                raw_record_count += 1
                if raw_record_count > max_raw_records:
                    raise VcfIngestLimitError(
                        "Uploaded VCF exceeds the raw record safety limit.",
                        code="vcf_raw_record_limit_exceeded",
                    )
                columns = line.split("\t")
                if len(columns) < 8:
                    raise VcfIngestLimitError(
                        "Uploaded VCF contains a malformed data row.",
                        code="vcf_malformed_record",
                    )
                ref = columns[3].strip().upper()
                _validate_contig(_normalize_chrom(columns[0]))
                alts = tuple(item.strip().upper() for item in columns[4].split(",") if item.strip())
                if not alts:
                    raise VcfIngestLimitError(
                        "Uploaded VCF contains a record without an ALT allele.",
                        code="vcf_malformed_record",
                    )
                for alt in alts:
                    _validate_alleles(ref, alt)
                    variant_classes.add("snv" if len(ref) == len(alt) == 1 else "short_indel")
    except (BadGzipFile, EOFError, OSError) as exc:
        raise VcfIngestLimitError(
            "Uploaded gzip VCF could not be decompressed.",
            code="gzip_decompression_failed",
        ) from exc
    if not saw_header:
        raise VcfIngestLimitError(
            "Uploaded VCF requires a #CHROM header.",
            code="vcf_header_required",
        )
    if raw_record_count == 0:
        raise VcfIngestLimitError(
            "Uploaded VCF contains no called variant records.",
            code="vcf_no_variants",
        )
    if not saw_explicit_grch38:
        warnings.append("genome_build_header_missing_grch38_api_contract_applied")
    cohort_model = "small_family" if sample_count > 1 else "single"
    return _Inspection(
        decompressed_bytes=decompressed_bytes,
        raw_record_count=raw_record_count,
        sample_count=sample_count,
        cohort_model=cohort_model,
        variant_classes=frozenset(variant_classes),
        warnings=tuple(warnings),
    )


def _read_magic(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(5)


def _replace_gzip_with_plaintext(
    path: Path,
    *,
    max_decompressed_bytes: int,
    deadline_monotonic: float,
) -> None:
    descriptor, raw_plaintext_path = tempfile.mkstemp(
        prefix="batch-plaintext-",
        suffix=".upload",
        dir=path.parent,
    )
    plaintext_path = Path(raw_plaintext_path)
    bytes_written = 0
    try:
        os.chmod(plaintext_path, 0o600)
        with (
            GzipFile(filename=str(path), mode="rb") as source,
            os.fdopen(descriptor, "wb") as target,
        ):
            while True:
                chunk = source.read(_COPY_CHUNK_BYTES)
                if not chunk:
                    break
                if time.monotonic() > deadline_monotonic:
                    raise VcfIngestLimitError(
                        "Uploaded VCF intake exceeded the configured wall-time limit.",
                        code="vcf_intake_time_limit_exceeded",
                    )
                bytes_written += len(chunk)
                if bytes_written > max_decompressed_bytes:
                    raise VcfIngestLimitError(
                        "Uploaded VCF exceeds the configured decompressed size limit.",
                        code="vcf_decompressed_size_limit_exceeded",
                    )
                target.write(chunk)
        os.replace(plaintext_path, path)
        os.chmod(path, 0o600)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        plaintext_path.unlink(missing_ok=True)
        raise


def _validate_alleles(ref: str, alt: str) -> None:
    if alt in _GVCF_ALTS:
        raise VcfIngestLimitError(
            "gVCF records with symbolic non-reference alleles are not supported.",
            code="gvcf_not_supported",
        )
    if (
        not ref
        or not alt
        or len(ref) > 2048
        or len(alt) > 2048
        or any(base not in _BASES for base in ref)
        or any(base not in _BASES for base in alt)
    ):
        raise VcfIngestLimitError(
            "Only SNVs and short sequence-resolved indels are supported in WES Batch V1.",
            code="unsupported_variant_class",
        )


def _normalize_chrom(value: str) -> str:
    chrom = value.strip()
    if chrom.lower().startswith("chr"):
        chrom = chrom[3:]
    normalized = chrom.upper()
    return "MT" if normalized == "M" else normalized


def _validate_contig(chromosome: str) -> None:
    if chromosome not in _SUPPORTED_CONTIGS:
        raise VcfIngestLimitError(
            "WES Batch V1 supports canonical GRCh38 contigs 1-22, X, Y, and MT only.",
            code="unsupported_contig",
        )


def _record_filter(record) -> str | None:
    values = tuple(str(value) for value in record.filter.keys())
    if not values:
        return None
    if values == ("PASS",):
        return "PASS"
    return ";".join(values)


def _info_gene(info) -> str | None:
    for key in ("GENE", "SYMBOL", "HGNC_SYMBOL"):
        value = _safe_info_get(info, key)
        text = _first_scalar_text(value)
        if text:
            return text.upper()
    ann = _first_scalar_text(_safe_info_get(info, "ANN"))
    if ann:
        fields = ann.split(",", 1)[0].split("|")
        if len(fields) > 3 and fields[3].strip():
            return fields[3].strip().upper()
    return None


def _info_text(info, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        text = _first_scalar_text(_safe_info_get(info, key))
        if text:
            return unquote(text)
    return None


def _first_scalar_text(value) -> str | None:
    if isinstance(value, (tuple, list)):
        value = value[0] if value else None
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    return text or None


def _info_af_values(info) -> tuple[float, ...]:
    value = _safe_info_get(info, "AF")
    values = value if isinstance(value, (tuple, list)) else (value,)
    parsed: list[float] = []
    for item in values:
        number = _finite_float(item)
        if number is not None and 0 <= number <= 1:
            parsed.append(number)
    return tuple(parsed)


def _safe_info_get(info, key: str):
    try:
        return info.get(key)
    except (KeyError, ValueError):
        return None


def _sample_provenance(record, *, sample_names: tuple[str, ...], upload_ref: str):
    samples: list[BatchSampleProvenanceV2] = []
    for source_index, sample_name in enumerate(sample_names):
        sample = record.samples[sample_name]
        alleles = sample.get("GT")
        if alleles is None:
            genotype = "./."
        else:
            separator = "|" if sample.phased else "/"
            genotype = separator.join("." if allele is None else str(allele) for allele in alleles)
        opaque = sha256(f"{upload_ref}:{source_index}".encode("utf-8")).hexdigest()[:24]
        depth = _bounded_int(sample.get("DP"), maximum=10_000_000)
        quality = _finite_float(sample.get("GQ"))
        samples.append(
            BatchSampleProvenanceV2(
                sample_key=f"sample-{opaque}",
                source_sample_index=source_index,
                genotype=genotype,
                phased=bool(sample.phased),
                depth=depth,
                genotype_quality=quality,
            )
        )
    return tuple(samples)


def _bounded_int(value, *, maximum: int) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if 0 <= parsed <= maximum else None


def _finite_float(value) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed or parsed in {float("inf"), float("-inf")}:
        return None
    return parsed
