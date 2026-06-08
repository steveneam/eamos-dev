from __future__ import annotations

import argparse
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, TextIO


@dataclass
class PubTatorConvertStats:
    source_file_count: int = 0
    document_count: int = 0
    text_line_count: int = 0
    annotation_line_count: int = 0
    edge_count: int = 0
    invalid_line_count: int = 0
    entity_type_counts: dict[str, int] = dataclass_field(default_factory=dict)

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "source_file_count": self.source_file_count,
            "document_count": self.document_count,
            "text_line_count": self.text_line_count,
            "annotation_line_count": self.annotation_line_count,
            "edge_count": self.edge_count,
            "invalid_line_count": self.invalid_line_count,
            "entity_type_counts": dict(sorted(self.entity_type_counts.items())),
        }


@dataclass(frozen=True)
class PubTatorDocument:
    pmid: str
    title: str = ""
    abstract: str = ""

    @property
    def text(self) -> str:
        if self.title and self.abstract:
            return f"{self.title} {self.abstract}"
        return self.title or self.abstract

    def section_for_offsets(self, start: int | None, end: int | None) -> str:
        if start is None or end is None:
            return ""
        if self.title and start < len(self.title):
            return "title"
        if self.abstract:
            abstract_start = len(self.title) + 1 if self.title else 0
            if start >= abstract_start:
                return "abstract"
        return ""

    def snippet_for_offsets(self, start: int | None, end: int | None) -> str:
        section = self.section_for_offsets(start, end)
        if section == "title":
            return _context_snippet(self.title, start, end)
        if section == "abstract" and start is not None and end is not None:
            abstract_start = len(self.title) + 1 if self.title else 0
            return _context_snippet(self.abstract, start - abstract_start, end - abstract_start)
        return _context_snippet(self.text, start, end)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert operator-staged PubTator flat files into the PubMed-local "
            "literature-edge JSONL shape. This command performs no network, "
            "startup download, runtime materialization, or source DB mutation."
        )
    )
    parser.add_argument("--from-pubtator-file", action="append", type=Path, default=[])
    parser.add_argument("--from-pubtator-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true", help="replace an existing output file")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument(
        "--require-edges",
        action="store_true",
        help="exit non-zero unless at least one edge was written",
    )
    args = parser.parse_args(argv)

    input_files = _collect_input_files(args.from_pubtator_file, args.from_pubtator_dir)
    if not input_files:
        _print_report(
            {
                "mode": "pubmed_pubtator_edge_convert",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "ready": False,
                "code": "no_input",
                "guardrails": _guardrails(),
                "conversion": PubTatorConvertStats().to_sanitized_dict(),
            },
            compact=args.compact,
        )
        return 2
    if args.output.exists() and not args.force:
        _print_report(
            {
                "mode": "pubmed_pubtator_edge_convert",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "ready": False,
                "code": "output_exists",
                "guardrails": _guardrails(),
                "conversion": PubTatorConvertStats(
                    source_file_count=len(input_files)
                ).to_sanitized_dict(),
                "output_file_name": args.output.name,
            },
            compact=args.compact,
        )
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    stats = convert_pubtator_files_to_edge_jsonl(input_files, args.output)
    report = {
        "mode": "pubmed_pubtator_edge_convert",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "converted" if stats.edge_count else "no_edges",
        "ready": bool(stats.edge_count),
        "guardrails": _guardrails(),
        "conversion": stats.to_sanitized_dict(),
        "output_file_name": args.output.name,
    }
    _print_report(report, compact=args.compact)
    if args.require_edges and stats.edge_count == 0:
        return 2
    return 0


def convert_pubtator_files_to_edge_jsonl(
    input_files: Iterable[Path],
    output_path: Path,
) -> PubTatorConvertStats:
    stats = PubTatorConvertStats()
    with output_path.open("w", encoding="utf-8", newline="\n") as output:
        for input_path in input_files:
            stats.source_file_count += 1
            for row in iter_pubtator_edge_rows(input_path, stats=stats):
                output.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                output.write("\n")
                stats.edge_count += 1
                entity_type = str(row.get("entity_type") or "entity")
                stats.entity_type_counts[entity_type] = (
                    stats.entity_type_counts.get(entity_type, 0) + 1
                )
    return stats


def iter_pubtator_edge_rows(
    input_path: Path,
    *,
    stats: PubTatorConvertStats | None = None,
) -> Iterator[dict[str, Any]]:
    with _open_text(input_path) as handle:
        block: list[str] = []
        for raw_line in handle:
            line = raw_line.rstrip("\r\n")
            if not line.strip():
                yield from _edge_rows_from_block(block, stats=stats)
                block = []
                continue
            block.append(line)
        yield from _edge_rows_from_block(block, stats=stats)


def _edge_rows_from_block(
    lines: list[str],
    *,
    stats: PubTatorConvertStats | None,
) -> Iterator[dict[str, Any]]:
    if not lines:
        return

    docs: dict[str, dict[str, str]] = {}
    annotations: list[tuple[int, list[str]]] = []
    block_invalid = 0
    for index, line in enumerate(lines, start=1):
        text_record = _parse_text_line(line)
        if text_record is not None:
            pmid, passage_type, text = text_record
            bucket = docs.setdefault(pmid, {"title": "", "abstract": ""})
            if passage_type == "t":
                bucket["title"] = text
            elif passage_type == "a":
                bucket["abstract"] = text
            else:
                block_invalid += 1
            if stats is not None:
                stats.text_line_count += 1
            continue
        fields = line.split("\t")
        if len(fields) >= 6 and re.fullmatch(r"\d{1,9}", fields[0].strip()):
            annotations.append((index, fields))
            if stats is not None:
                stats.annotation_line_count += 1
            continue
        block_invalid += 1

    if stats is not None:
        stats.invalid_line_count += block_invalid
        stats.document_count += len(docs)

    for line_number, fields in annotations:
        row = _edge_row_from_annotation(fields, line_number=line_number, docs=docs)
        if row is not None:
            yield row
        elif stats is not None:
            stats.invalid_line_count += 1


def _parse_text_line(line: str) -> tuple[str, str, str] | None:
    parts = line.split("|", 2)
    if len(parts) != 3:
        return None
    pmid, passage_type, text = parts
    passage_type = passage_type.strip().lower()
    if not re.fullmatch(r"\d{1,9}", pmid.strip()) or passage_type not in {"t", "a"}:
        return None
    return pmid.strip(), passage_type, text.strip()


def _edge_row_from_annotation(
    fields: list[str],
    *,
    line_number: int,
    docs: dict[str, dict[str, str]],
) -> dict[str, Any] | None:
    pmid = fields[0].strip()
    start = _optional_int(fields[1])
    end = _optional_int(fields[2])
    mention = _normalize_space(fields[3])
    entity_type = _normalize_entity_type(fields[4])
    identifier = _normalize_space(fields[5])
    if not mention and not identifier:
        return None

    doc_payload = docs.get(pmid, {})
    doc = PubTatorDocument(
        pmid=pmid,
        title=doc_payload.get("title", ""),
        abstract=doc_payload.get("abstract", ""),
    )
    evidence_text = doc.snippet_for_offsets(start, end) or mention
    annotation_id = _annotation_id(
        pmid=pmid,
        start=start,
        end=end,
        mention=mention,
        entity_type=entity_type,
        identifier=identifier,
        line_number=line_number,
    )
    return {
        "pmid": pmid,
        "source": "pubtator",
        "entity_type": entity_type,
        "identifier": identifier or None,
        "matched_text": mention,
        "section": doc.section_for_offsets(start, end),
        "offset_start": start,
        "offset_end": end,
        "evidence_text": evidence_text,
        "annotation_id": annotation_id,
    }


def _normalize_entity_type(value: str) -> str:
    text = _normalize_space(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    if text in {"mutation", "mutations", "sequence_variant", "dna_variant"}:
        return "variant"
    if text in {"genes", "gene_symbol"}:
        return "gene"
    if text == "cellline":
        return "cell_line"
    return text or "entity"


def _context_snippet(text: str, start: int | None, end: int | None, *, window: int = 96) -> str:
    if start is None or end is None or start < 0 or end <= start or end > len(text):
        return ""
    left = max(start - window, 0)
    right = min(end + window, len(text))
    return _normalize_space(text[left:right])


def _annotation_id(
    *,
    pmid: str,
    start: int | None,
    end: int | None,
    mention: str,
    entity_type: str,
    identifier: str,
    line_number: int,
) -> str:
    payload = "|".join(
        (
            pmid,
            "" if start is None else str(start),
            "" if end is None else str(end),
            entity_type,
            identifier,
            mention,
            str(line_number),
        )
    )
    return f"pubtator:{sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def _collect_input_files(files: Iterable[Path], directory: Path | None) -> list[Path]:
    result = [path for path in files if path.is_file()]
    if directory is not None and directory.is_dir():
        result.extend(
            sorted(
                path
                for path in directory.iterdir()
                if path.is_file()
                and (
                    path.suffix.lower() in {".pubtator", ".txt", ".tsv"}
                    or path.name.lower().endswith((".pubtator.gz", ".txt.gz", ".tsv.gz"))
                )
            )
        )
    return result


def _open_text(path: Path) -> TextIO:
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _guardrails() -> dict[str, Any]:
    return {
        "network": {"used": False, "provider": None},
        "startup_download": "not_used",
        "request_time_materialization": "not_used",
        "runtime_db_mutation": "not_used",
        "patient_data": "not_used",
        "secrets_in_output": "blocked",
        "local_paths_in_output": "blocked",
        "raw_full_text_in_output": "blocked",
    }


def _print_report(report: dict[str, Any], *, compact: bool) -> None:
    print(json.dumps(report, indent=None if compact else 2, sort_keys=True))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
