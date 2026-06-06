from __future__ import annotations

from dataclasses import dataclass, field
from gzip import BadGzipFile, decompress
from pathlib import Path
from urllib.parse import unquote

from app.schemas.batch import ParsedVariant


@dataclass(frozen=True)
class ParsedVcfUpload:
    variants: list[ParsedVariant]
    warnings: list[str] = field(default_factory=list)
    skipped_rows: int = 0


def parse_vcf_upload_bytes(payload: bytes, *, filename: str | None = None) -> ParsedVcfUpload:
    text, warnings = _decode_payload(payload, filename=filename)
    parsed = parse_vcf_text(text)
    return ParsedVcfUpload(
        variants=parsed.variants,
        warnings=[*warnings, *parsed.warnings],
        skipped_rows=parsed.skipped_rows,
    )


def parse_vcf_text(text: str) -> ParsedVcfUpload:
    warnings: list[str] = []
    variants: list[ParsedVariant] = []
    skipped_rows = 0
    sample_names: list[str] = []
    saw_header = False

    for source_index, raw_line in enumerate(text.replace("\r\n", "\n").splitlines()):
        line = raw_line.strip()
        if source_index == 0:
            line = line.removeprefix("\ufeff")
        if not line:
            continue
        if line.startswith("##"):
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
        variants.extend(row_variants)

    return ParsedVcfUpload(variants=variants, warnings=warnings, skipped_rows=skipped_rows)


def _decode_payload(payload: bytes, *, filename: str | None) -> tuple[str, list[str]]:
    warnings: list[str] = []
    data = payload
    if payload.startswith(b"\x1f\x8b") or (filename or "").lower().endswith(".gz"):
        try:
            data = decompress(payload)
        except (BadGzipFile, OSError):
            warnings.append("gzip_decompression_failed_treating_as_plain_text")
            data = payload
    return data.decode("utf-8-sig", errors="replace"), warnings


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

    variants: list[ParsedVariant] = []
    af_values = _af_values(info.get("AF"))
    for alt_index, alt in enumerate(alts):
        warnings = list(row_warnings)
        if len(alts) > 1:
            warnings.append("multiallelic_alt_split")
        if not _looks_like_bases(ref) or not _looks_like_bases(alt):
            warnings.append("non_acgtn_allele_preserved")
        info_af = af_values[alt_index] if alt_index < len(af_values) else None
        query = f"{chrom}-{pos}-{ref}-{alt}"
        variants.append(
            ParsedVariant(
                raw=raw,
                query=query,
                gene=gene,
                variant=variant,
                chrom=chrom,
                pos=pos,
                ref=ref,
                alt=alt,
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
