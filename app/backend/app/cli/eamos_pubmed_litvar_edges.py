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

from app.services.pubmed_local import PubMedSeedQuery, read_seed_queries


@dataclass
class LitVarEdgeConvertStats:
    source_file_count: int = 0
    record_count: int = 0
    pmid_count: int = 0
    seed_matched_count: int = 0
    edge_count: int = 0
    invalid_record_count: int = 0
    entity_type_counts: dict[str, int] = dataclass_field(default_factory=dict)

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "source_file_count": self.source_file_count,
            "record_count": self.record_count,
            "pmid_count": self.pmid_count,
            "seed_matched_count": self.seed_matched_count,
            "edge_count": self.edge_count,
            "invalid_record_count": self.invalid_record_count,
            "entity_type_counts": dict(sorted(self.entity_type_counts.items())),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert operator-staged LitVar/LitVar2 publication exports into the "
            "PubMed-local literature-edge JSONL shape. This command performs no "
            "network, startup download, runtime materialization, or source DB mutation."
        )
    )
    parser.add_argument("--from-litvar-json-file", action="append", type=Path, default=[])
    parser.add_argument("--from-litvar-jsonl-file", action="append", type=Path, default=[])
    parser.add_argument(
        "--query-file",
        type=Path,
        help="optional PubMed-local seed TSV; a single seed applies to all input records",
    )
    parser.add_argument("--gene", help="manual gene seed when no query file is supplied")
    parser.add_argument("--cdna")
    parser.add_argument("--transcript")
    parser.add_argument("--protein-change")
    parser.add_argument("--rsid")
    parser.add_argument("--genomic-hg38")
    parser.add_argument("--scope", choices=("variant", "gene"), default="variant")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true", help="replace an existing output file")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument(
        "--require-edges",
        action="store_true",
        help="exit non-zero unless at least one edge was written",
    )
    args = parser.parse_args(argv)

    input_files = _collect_input_files(args.from_litvar_json_file, args.from_litvar_jsonl_file)
    if not input_files:
        _print_report(
            {
                "mode": "pubmed_litvar_edge_convert",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "ready": False,
                "code": "no_input",
                "guardrails": _guardrails(),
                "conversion": LitVarEdgeConvertStats().to_sanitized_dict(),
            },
            compact=args.compact,
        )
        return 2
    if args.output.exists() and not args.force:
        _print_report(
            {
                "mode": "pubmed_litvar_edge_convert",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "ready": False,
                "code": "output_exists",
                "guardrails": _guardrails(),
                "conversion": LitVarEdgeConvertStats(
                    source_file_count=len(input_files)
                ).to_sanitized_dict(),
                "output_file_name": args.output.name,
            },
            compact=args.compact,
        )
        return 2

    try:
        seeds = _load_seeds(args)
    except ValueError as exc:
        _print_report(
            {
                "mode": "pubmed_litvar_edge_convert",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "ready": False,
                "code": "invalid_seed",
                "message": str(exc),
                "guardrails": _guardrails(),
                "conversion": LitVarEdgeConvertStats(
                    source_file_count=len(input_files)
                ).to_sanitized_dict(),
                "output_file_name": args.output.name,
            },
            compact=args.compact,
        )
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    stats = convert_litvar_exports_to_edge_jsonl(input_files, args.output, seeds=seeds)
    report = {
        "mode": "pubmed_litvar_edge_convert",
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


def convert_litvar_exports_to_edge_jsonl(
    input_files: Iterable[Path],
    output_path: Path,
    *,
    seeds: Iterable[PubMedSeedQuery] = (),
) -> LitVarEdgeConvertStats:
    seed_list = list(seeds)
    stats = LitVarEdgeConvertStats()
    with output_path.open("w", encoding="utf-8", newline="\n") as output:
        for input_path in input_files:
            stats.source_file_count += 1
            for record in _iter_litvar_records(input_path, stats=stats):
                seed = _seed_for_record(record, seed_list)
                pmids = _pmids_from_record(record)
                if seed is None or not pmids:
                    stats.invalid_record_count += 1
                    continue
                stats.seed_matched_count += 1
                stats.pmid_count += len(pmids)
                for pmid in pmids:
                    for row in _edge_rows_for_pmid(pmid, seed, record):
                        output.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                        output.write("\n")
                        stats.edge_count += 1
                        entity_type = str(row.get("entity_type") or "entity")
                        stats.entity_type_counts[entity_type] = (
                            stats.entity_type_counts.get(entity_type, 0) + 1
                        )
    return stats


def _iter_litvar_records(
    input_path: Path,
    *,
    stats: LitVarEdgeConvertStats,
) -> Iterator[dict[str, Any]]:
    if input_path.name.lower().endswith((".jsonl", ".jsonl.gz")):
        with _open_text(input_path) as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    record = json.loads(stripped)
                except json.JSONDecodeError:
                    stats.invalid_record_count += 1
                    continue
                if not isinstance(record, dict):
                    stats.invalid_record_count += 1
                    continue
                stats.record_count += 1
                yield record
        return

    try:
        with _open_text(input_path) as handle:
            payload = json.load(handle)
    except (json.JSONDecodeError, OSError):
        stats.invalid_record_count += 1
        return
    for record in _records_from_json_payload(payload):
        stats.record_count += 1
        yield record


def _records_from_json_payload(payload: Any) -> Iterator[dict[str, Any]]:
    if isinstance(payload, dict):
        yield payload
        return
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item


def _edge_rows_for_pmid(
    pmid: str,
    seed: PubMedSeedQuery,
    record: dict[str, Any],
) -> Iterator[dict[str, Any]]:
    litvar_id = _litvar_id(record)
    source_url = _source_url(record, litvar_id)
    evidence_text = f"LitVar2 reported PMID {pmid} for {seed.source_query}."
    for entity_type, value in _seed_edge_terms(seed):
        annotation_id = _annotation_id(
            pmid=pmid,
            entity_type=entity_type,
            value=value,
            litvar_id=litvar_id,
            source_query=seed.source_query,
        )
        yield {
            "pmid": pmid,
            "source": "litvar2",
            "entity_type": entity_type,
            "identifier": value,
            "matched_text": value,
            "section": "litvar2",
            "relation_type": "litvar_publication_for_variant",
            "evidence_text": evidence_text,
            "source_url": source_url,
            "annotation_id": annotation_id,
        }


def _seed_edge_terms(seed: PubMedSeedQuery) -> Iterator[tuple[str, str]]:
    yield "gene", seed.gene
    for term_type, value in seed.terms:
        if term_type == "gene" or not value:
            continue
        entity_type = "rsid" if term_type == "rsid" else "variant"
        yield entity_type, value


def _seed_for_record(
    record: dict[str, Any],
    seeds: list[PubMedSeedQuery],
) -> PubMedSeedQuery | None:
    record_seed = _seed_from_record(record)
    if record_seed is not None:
        return record_seed
    if len(seeds) == 1:
        return seeds[0]
    if not seeds:
        return None

    query_text = " ".join(_record_query_texts(record)).lower()
    matches = [seed for seed in seeds if _query_text_matches_seed(query_text, seed)]
    return matches[0] if len(matches) == 1 else None


def _query_text_matches_seed(query_text: str, seed: PubMedSeedQuery) -> bool:
    if _normalize_for_contains(seed.gene) not in query_text:
        return False
    variant_terms = [_normalize_for_contains(term) for term in seed.variant_terms]
    return not variant_terms or any(term and term in query_text for term in variant_terms)


def _seed_from_record(record: dict[str, Any]) -> PubMedSeedQuery | None:
    variant = record.get("variant")
    seed_payload = record.get("seed")
    nested: dict[str, Any] = {}
    if isinstance(variant, dict):
        nested.update(variant)
    if isinstance(seed_payload, dict):
        nested.update(seed_payload)
    gene = _clean_optional(record.get("gene") or nested.get("gene"))
    if not gene:
        return None
    scope = _clean_optional(record.get("scope") or nested.get("scope")) or "variant"
    seed = PubMedSeedQuery(
        gene=gene.upper(),
        cdna=_clean_optional(record.get("cdna") or nested.get("cdna")),
        transcript=_clean_optional(record.get("transcript") or nested.get("transcript")),
        protein_change=_clean_optional(
            record.get("protein_change") or nested.get("protein_change")
        ),
        rsid=_clean_optional(record.get("rsid") or nested.get("rsid")),
        genomic_hg38=_clean_optional(record.get("genomic_hg38") or nested.get("genomic_hg38")),
        scope=scope,
    )
    return seed if seed.scope == "gene" or seed.variant_terms else None


def _pmids_from_record(record: dict[str, Any]) -> list[str]:
    candidates: list[Any] = []
    for key in ("pmid", "pubmed_id", "pmids", "pubmed_ids"):
        candidates.append(record.get(key))
    summary = record.get("summary")
    if isinstance(summary, dict):
        candidates.extend(summary.get(key) for key in ("pmid", "pubmed_id", "pmids", "pubmed_ids"))
        candidates.append(summary.get("articles"))
    raw = record.get("raw")
    if isinstance(raw, dict):
        candidates.extend(raw.get(key) for key in ("pmid", "pubmed_id", "pmids", "pubmed_ids"))
    candidates.append(record.get("articles"))
    candidates.append(record.get("publications"))

    pmids: list[str] = []
    seen: set[str] = set()
    for value in candidates:
        for pmid in _iter_pmids(value):
            if pmid in seen:
                continue
            seen.add(pmid)
            pmids.append(pmid)
    return pmids


def _iter_pmids(value: Any) -> Iterator[str]:
    if value is None:
        return
    if isinstance(value, (int, float)):
        text = str(int(value))
        if re.fullmatch(r"\d{1,9}", text):
            yield text
        return
    if isinstance(value, str):
        for match in re.findall(r"\b\d{1,9}\b", value):
            yield match
        return
    if isinstance(value, dict):
        for key in ("pmid", "pubmed_id", "id"):
            if key in value:
                yield from _iter_pmids(value.get(key))
        return
    if isinstance(value, Iterable):
        for item in value:
            yield from _iter_pmids(item)


def _record_query_texts(record: dict[str, Any]) -> Iterator[str]:
    for key in ("query", "source_query", "search_text"):
        value = record.get(key)
        if isinstance(value, str):
            yield value
    request_identity = record.get("request_identity")
    if isinstance(request_identity, dict):
        for key in ("query", "term"):
            value = request_identity.get(key)
            if isinstance(value, str):
                yield value
    summary = record.get("summary")
    if isinstance(summary, dict):
        for key in ("query", "litvar_id"):
            value = summary.get(key)
            if isinstance(value, str):
                yield value


def _litvar_id(record: dict[str, Any]) -> str | None:
    for container in (record, record.get("summary"), record.get("request_identity")):
        if not isinstance(container, dict):
            continue
        value = container.get("litvar_id") or container.get("variant_id") or container.get("id")
        if value:
            return str(value).strip()
    return None


def _source_url(record: dict[str, Any], litvar_id: str | None) -> str:
    for container in (record, record.get("summary")):
        if not isinstance(container, dict):
            continue
        value = container.get("source_url") or container.get("url")
        if isinstance(value, str) and value.strip():
            return value.strip()
    if litvar_id:
        return f"https://www.ncbi.nlm.nih.gov/research/litvar2/variant/{litvar_id}"
    return "https://www.ncbi.nlm.nih.gov/research/litvar2-api"


def _load_seeds(args: argparse.Namespace) -> list[PubMedSeedQuery]:
    seeds = read_seed_queries(args.query_file) if args.query_file is not None else []
    manual_seed = _manual_seed(args)
    if manual_seed is not None:
        seeds.append(manual_seed)
    return seeds


def _manual_seed(args: argparse.Namespace) -> PubMedSeedQuery | None:
    gene = _clean_optional(args.gene)
    if not gene:
        return None
    seed = PubMedSeedQuery(
        gene=gene.upper(),
        cdna=_clean_optional(args.cdna),
        transcript=_clean_optional(args.transcript),
        protein_change=_clean_optional(args.protein_change),
        rsid=_clean_optional(args.rsid),
        genomic_hg38=_clean_optional(args.genomic_hg38),
        scope=args.scope,
    )
    if seed.scope == "variant" and not seed.variant_terms:
        raise ValueError("manual variant seed needs at least one variant identifier")
    return seed


def _collect_input_files(json_files: Iterable[Path], jsonl_files: Iterable[Path]) -> list[Path]:
    result = [path for path in json_files if path.is_file()]
    result.extend(path for path in jsonl_files if path.is_file())
    return result


def _open_text(path: Path) -> TextIO:
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def _annotation_id(
    *,
    pmid: str,
    entity_type: str,
    value: str,
    litvar_id: str | None,
    source_query: str,
) -> str:
    payload = "|".join((pmid, entity_type, value, litvar_id or "", source_query))
    return f"litvar2:{sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def _normalize_for_contains(value: str | None) -> str:
    return re.sub(r"[^a-z0-9.>:_-]+", " ", str(value or "").strip().lower())


def _guardrails() -> dict[str, Any]:
    return {
        "network": {"used": False, "provider": None},
        "startup_download": "not_used",
        "request_time_materialization": "not_used",
        "runtime_db_mutation": "not_used",
        "patient_data": "not_used",
        "secrets_in_output": "blocked",
        "local_paths_in_output": "blocked",
        "seed_rows_in_output": "blocked",
        "raw_full_text_in_output": "blocked",
    }


def _print_report(report: dict[str, Any], *, compact: bool) -> None:
    print(json.dumps(report, indent=None if compact else 2, sort_keys=True))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
