from __future__ import annotations

import codecs
from dataclasses import dataclass, field
from gzip import BadGzipFile, GzipFile
from io import BytesIO
from pathlib import Path
from typing import Iterable, Iterator
from urllib.parse import unquote

from app.schemas.batch import BATCH_MAX_VARIANTS, ParsedVariant

DEFAULT_MAX_DECOMPRESSED_BYTES = 20 * 1024 * 1024
_STREAM_CHUNK_BYTES = 64 * 1024
_GVCF_SYMBOLIC_ALTS = {"<NON_REF>", "<*>"}
_HG19_CONTIG_LENGTHS = {
    "1": 249250621,
    "2": 243199373,
    "X": 155270560,
    "Y": 59373566,
    "M": 16571,
    "MT": 16571,
}


class VcfIngestLimitError(ValueError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ParsedVcfUpload:
    variants: list[ParsedVariant]
    warnings: list[str] = field(default_factory=list)
    skipped_rows: int = 0


def parse_vcf_upload_bytes(
    payload: bytes,
    *,
    filename: str | None = None,
    max_decompressed_bytes: int = DEFAULT_MAX_DECOMPRESSED_BYTES,
    max_variants: int = BATCH_MAX_VARIANTS,
) -> ParsedVcfUpload:
    lines, warnings = _decode_payload_lines(
        payload,
        filename=filename,
        max_decompressed_bytes=max_decompressed_bytes,
    )
    parsed = parse_vcf_lines(lines, max_variants=max_variants)
    return ParsedVcfUpload(
        variants=parsed.variants,
        warnings=[*warnings, *parsed.warnings],
        skipped_rows=parsed.skipped_rows,
    )


def parse_vcf_text(
    text: str,
    *,
    max_variants: int = BATCH_MAX_VARIANTS,
) -> ParsedVcfUpload:
    return parse_vcf_lines(text.replace("\r\n", "\n").splitlines(), max_variants=max_variants)


def parse_vcf_lines(
    lines: Iterable[str],
    *,
    max_variants: int = BATCH_MAX_VARIANTS,
) -> ParsedVcfUpload:
    warnings: list[str] = []
    variants: list[ParsedVariant] = []
    skipped_rows = 0
    sample_names: list[str] = []
    saw_header = False

    for source_index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if source_index == 0:
            line = line.removeprefix("\ufeff")
        if not line:
            continue
        if line.startswith("##"):
            unsupported_build = _unsupported_genome_build(line)
            if unsupported_build:
                raise VcfIngestLimitError(
                    (
                        "Uploaded VCF appears to use hg19/GRCh37 coordinates. "
                        "Batch VCF lookup v1 supports hg38/GRCh38 only."
                    ),
                    code="vcf_unsupported_genome_build",
                )
            continue
        if line.startswith("#CHROM"):
            saw_header = True
            columns = _split_vcf_fields(line.lstrip("#"))
            sample_names = columns[9:] if len(columns) > 9 else []
            continue
        if line.startswith("#"):
            continue

        columns, row_warnings = _data_columns(line)
        if not saw_header:
            row_warnings.append("missing_vcf_header")
            saw_header = True
        if len(columns) < 8:
            warnings.extend(_row_warning(source_index, "malformed_vcf_row"))
            skipped_rows += 1
            continue

        row_variants = _row_variants(
            columns,
            raw=line,
            source_index=source_index,
            sample_names=sample_names,
            row_warnings=row_warnings,
        )
        if not row_variants:
            warnings.extend(_row_warning(source_index, "unusable_vcf_row"))
            skipped_rows += 1
            continue
        if len(variants) + len(row_variants) > max_variants:
            raise VcfIngestLimitError(
                f"Uploaded VCF exceeds the maximum of {max_variants} parsed variants.",
                code="vcf_variant_count_limit_exceeded",
            )
        variants.extend(row_variants)

    return ParsedVcfUpload(variants=variants, warnings=warnings, skipped_rows=skipped_rows)


def _decode_payload_lines(
    payload: bytes,
    *,
    filename: str | None,
    max_decompressed_bytes: int,
) -> tuple[Iterator[str], list[str]]:
    warnings: list[str] = []
    if payload.startswith(b"\x1f\x8b") or (filename or "").lower().endswith(".gz"):
        return (
            _iter_gzip_text_lines(payload, max_decompressed_bytes=max_decompressed_bytes),
            warnings,
        )
    return (
        _iter_text_lines(BytesIO(payload), max_bytes=max_decompressed_bytes),
        warnings,
    )


def _iter_gzip_text_lines(
    payload: bytes,
    *,
    max_decompressed_bytes: int,
) -> Iterator[str]:
    try:
        with GzipFile(fileobj=BytesIO(payload), mode="rb") as handle:
            yield from _iter_text_lines(handle, max_bytes=max_decompressed_bytes)
    except (BadGzipFile, EOFError, OSError) as exc:
        raise VcfIngestLimitError(
            "Uploaded gzip VCF could not be decompressed.",
            code="gzip_decompression_failed",
        ) from exc


def _iter_text_lines(handle, *, max_bytes: int) -> Iterator[str]:
    limit = max(1, int(max_bytes))
    bytes_seen = 0
    pending = ""
    decoder = codecs.getincrementaldecoder("utf-8-sig")(errors="replace")

    while True:
        chunk = handle.read(_STREAM_CHUNK_BYTES)
        if not chunk:
            break
        bytes_seen += len(chunk)
        if bytes_seen > limit:
            raise VcfIngestLimitError(
                f"Uploaded VCF exceeds the decompressed size limit of {limit} bytes.",
                code="vcf_decompressed_size_limit_exceeded",
            )
        text = pending + decoder.decode(chunk, final=False).replace("\r\n", "\n")
        parts = text.split("\n")
        pending = parts.pop()
        yield from parts

    tail = pending + decoder.decode(b"", final=True)
    if tail:
        yield tail


def _data_columns(line: str) -> tuple[list[str], list[str]]:
    tab_columns = line.split("\t")
    if len(tab_columns) >= 8:
        return tab_columns, []
    recovered = _split_vcf_fields(line)
    warnings = ["whitespace_delimited_vcf_row_recovered"] if len(recovered) >= 8 else []
    return recovered, warnings


def _split_vcf_fields(line: str) -> list[str]:
    return [part for part in line.strip().split() if part]


def _row_variants(
    columns: list[str],
    *,
    raw: str,
    source_index: int,
    sample_names: list[str],
    row_warnings: list[str],
) -> list[ParsedVariant]:
    chrom = _normalize_chrom(columns[0])
    pos = _positive_int(columns[1])
    ref = columns[3].strip().upper()
    alts = [alt.strip().upper() for alt in columns[4].split(",") if alt.strip()]
    filter_value = columns[6].strip() or None
    info = _parse_info(columns[7])
    gene = _gene_from_info(info)
    hgvs_c = _first_info_value(info, ("HGVS_C", "HGVSC"))
    variant = hgvs_c or _first_info_value(info, ("VARIANT", "HGVS"))
    sample_id, genotype = _sample_context(columns, sample_names)
    if not chrom or pos is None or not ref or not alts:
        return []
    if any(alt in _GVCF_SYMBOLIC_ALTS for alt in alts):
        raise VcfIngestLimitError(
            "gVCF rows with <NON_REF> symbolic alleles are not supported. Upload a called-sites VCF.",
            code="gvcf_not_supported",
        )

    variants: list[ParsedVariant] = []
    af_values = _af_values(info.get("AF"))
    for alt_index, alt in enumerate(alts):
        warnings = list(row_warnings)
        if len(alts) > 1:
            warnings.append("multiallelic_alt_split")
        normalized_pos, normalized_ref, normalized_alt, normalized = _normalize_alleles(
            pos,
            ref,
            alt,
        )
        if normalized:
            warnings.append("parsimonious_allele_normalized")
        if not _looks_like_bases(normalized_ref) or not _looks_like_bases(normalized_alt):
            warnings.append("non_acgtn_allele_preserved")
        info_af = af_values[alt_index] if alt_index < len(af_values) else None
        query = f"{chrom}-{normalized_pos}-{normalized_ref}-{normalized_alt}"
        variants.append(
            ParsedVariant(
                raw=raw,
                query=query,
                gene=gene,
                variant=variant,
                chrom=chrom,
                pos=normalized_pos,
                ref=normalized_ref,
                alt=normalized_alt,
                filter=filter_value,
                info_af=info_af,
                source_index=source_index,
                sample_id=sample_id,
                genotype=genotype,
                warnings=warnings,
            )
        )
    return variants


def _parse_info(raw: str) -> dict[str, str | bool]:
    info: dict[str, str | bool] = {}
    if not raw or raw == ".":
        return info
    for item in raw.split(";"):
        if not item:
            continue
        if "=" not in item:
            info[item.upper()] = True
            continue
        key, value = item.split("=", 1)
        info[key.strip().upper()] = value.strip()
    return info


def _gene_from_info(info: dict[str, str | bool]) -> str | None:
    for key in ("GENE", "SYMBOL", "HGNC_SYMBOL"):
        value = info.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper()
    ann = info.get("ANN")
    if isinstance(ann, str) and ann.strip():
        first = ann.split(",", 1)[0].split("|")
        if len(first) > 3 and first[3].strip():
            return first[3].strip().upper()
    return None


def _first_info_value(info: dict[str, str | bool], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = info.get(key)
        if isinstance(value, str) and value.strip():
            return unquote(value.strip())
    return None


def _af_values(value: str | bool | None) -> list[float]:
    if not isinstance(value, str):
        return []
    afs: list[float] = []
    for item in value.split(","):
        try:
            af = float(item)
        except ValueError:
            continue
        if 0 <= af <= 1:
            afs.append(af)
    return afs


def _sample_context(
    columns: list[str],
    sample_names: list[str],
) -> tuple[str | None, str | None]:
    if len(columns) < 10:
        return None, None
    sample_name = sample_names[0] if sample_names else None
    format_keys = columns[8].split(":")
    sample_values = columns[9].split(":")
    genotype = (
        sample_values[0] if format_keys and format_keys[0] == "GT" and sample_values else None
    )
    return sample_name, genotype


def _normalize_chrom(value: str) -> str:
    chrom = value.strip()
    if chrom.lower().startswith("chr"):
        chrom = chrom[3:]
    return chrom.upper() if chrom.upper() in {"X", "Y", "M", "MT"} else chrom


def _unsupported_genome_build(line: str) -> str | None:
    text = line.strip()
    lower = text.lower()
    if lower.startswith("##reference=") or lower.startswith("##genome-build="):
        if any(token in lower for token in ("grch37", "hg19", "b37")):
            return "hg19"
        return None
    if not lower.startswith("##contig=<"):
        return None
    payload = text.split("<", 1)[1].rsplit(">", 1)[0]
    fields = _parse_header_fields(payload)
    assembly = str(fields.get("assembly") or fields.get("genome") or "").lower()
    if any(token in assembly for token in ("grch37", "hg19", "b37")):
        return "hg19"
    contig = _normalize_chrom(str(fields.get("id") or fields.get("ID") or ""))
    length = _positive_int(str(fields.get("length") or fields.get("Length") or ""))
    if contig in _HG19_CONTIG_LENGTHS and length == _HG19_CONTIG_LENGTHS[contig]:
        return "hg19"
    return None


def _parse_header_fields(payload: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in payload.split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        fields[key.strip().lower()] = value.strip().strip('"')
    return fields


def _normalize_alleles(pos: int, ref: str, alt: str) -> tuple[int, str, str, bool]:
    if not (_looks_like_bases(ref) and _looks_like_bases(alt)):
        return pos, ref, alt, False
    normalized_pos = pos
    normalized_ref = ref
    normalized_alt = alt
    changed = False
    while (
        len(normalized_ref) > 1
        and len(normalized_alt) > 1
        and normalized_ref[-1] == normalized_alt[-1]
    ):
        normalized_ref = normalized_ref[:-1]
        normalized_alt = normalized_alt[:-1]
        changed = True
    while (
        len(normalized_ref) > 1
        and len(normalized_alt) > 1
        and normalized_ref[0] == normalized_alt[0]
    ):
        normalized_ref = normalized_ref[1:]
        normalized_alt = normalized_alt[1:]
        normalized_pos += 1
        changed = True
    return normalized_pos, normalized_ref, normalized_alt, changed


def _positive_int(value: str) -> int | None:
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _looks_like_bases(value: str) -> bool:
    return bool(value) and all(base in {"A", "C", "G", "T", "N"} for base in value.upper())


def _row_warning(source_index: int, code: str) -> list[str]:
    return [f"{code}:line_{source_index + 1}"]


def read_vcf_upload_file(path: Path) -> ParsedVcfUpload:
    return parse_vcf_upload_bytes(path.read_bytes(), filename=path.name)
