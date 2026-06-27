from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import md5
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from types import SimpleNamespace
from typing import Any, Callable

from app.cli.eamos_pubmed_litvar_edges import convert_litvar_exports_to_edge_jsonl
from app.cli.eamos_pubmed_pubtator_edges import convert_pubtator_files_to_edge_jsonl
from app.core.config import Settings
from app.services.pubmed_local import (
    PubMedLocalStore,
    inspect_pubmed_local_store,
    materialize_pubmed_local_store,
    read_seed_queries,
)
from app.services.pubmed_seed_manifest import load_seed_manifest

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
DEFAULT_MANIFEST_PATH = FIXTURE_ROOT / "literature" / "pmat_seed_manifest_tiny.json"
DEFAULT_PUBMED_XML_PATH = FIXTURE_ROOT / "tools" / "pubmed_local_sample.xml"
DEFAULT_SOURCE_VERSION = "pmat-bounded-slice-fixture-v1"


@dataclass(frozen=True)
class StepMeasurement:
    name: str
    elapsed_ms: int
    rss_bytes_after: int | None
    temp_disk_bytes_after: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "elapsed_ms": self.elapsed_ms,
            "rss_bytes_after": self.rss_bytes_after,
            "temp_disk_bytes_after": self.temp_disk_bytes_after,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the PMAT-005 bounded-slice benchmark harness against checked-in "
            "tiny PubMed/LitVar/PubTator fixtures. This command performs no "
            "source download, network fetch, storage upload, runtime seeding, "
            "runtime flag change, Supabase mutation, or deploy."
        )
    )
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--pubmed-xml-file", type=Path, default=DEFAULT_PUBMED_XML_PATH)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--source-version", default=DEFAULT_SOURCE_VERSION)
    parser.add_argument("--lookup-runs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--batch-runs", type=int, default=3)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    args = parser.parse_args(argv)

    lookup_runs = max(args.lookup_runs, 1)
    batch_size = max(args.batch_size, 1)
    batch_runs = max(args.batch_runs, 1)

    if args.output_dir is None:
        with tempfile.TemporaryDirectory(prefix="eamos-pmat-benchmark-") as temp_dir:
            report = _run_benchmark(
                work_dir=Path(temp_dir),
                manifest_path=args.manifest_path,
                pubmed_xml_file=args.pubmed_xml_file,
                source_version=args.source_version,
                lookup_runs=lookup_runs,
                batch_size=batch_size,
                batch_runs=batch_runs,
                force=True,
                retained_output=False,
            )
    else:
        report = _run_benchmark(
            work_dir=args.output_dir,
            manifest_path=args.manifest_path,
            pubmed_xml_file=args.pubmed_xml_file,
            source_version=args.source_version,
            lookup_runs=lookup_runs,
            batch_size=batch_size,
            batch_runs=batch_runs,
            force=args.force,
            retained_output=True,
        )

    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0 if report["ready"] or not args.require_ready else 2


def _run_benchmark(
    *,
    work_dir: Path,
    manifest_path: Path,
    pubmed_xml_file: Path,
    source_version: str,
    lookup_runs: int,
    batch_size: int,
    batch_runs: int,
    force: bool,
    retained_output: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    work_dir.mkdir(parents=True, exist_ok=True)
    _ensure_output_is_writable(work_dir, force=force)

    steps: list[StepMeasurement] = []

    def measure(name: str, action: Callable[[], Any]) -> Any:
        step_started = time.perf_counter()
        value = action()
        steps.append(
            StepMeasurement(
                name=name,
                elapsed_ms=_elapsed_ms(step_started),
                rss_bytes_after=_current_rss_bytes(),
                temp_disk_bytes_after=_tree_size_bytes(work_dir),
            )
        )
        return value

    query_file = work_dir / "pmat-seed.tsv"
    pubtator_path = work_dir / "pmat-pubtator.pubtator"
    pubtator_edges = work_dir / "pmat-pubtator-edges.jsonl"
    litvar_path = work_dir / "pmat-litvar.json"
    litvar_edges = work_dir / "pmat-litvar-edges.jsonl"
    xml_path = work_dir / "pubmed25n0001.xml"
    db_path = work_dir / "pubmed-local.sqlite"
    materialization_manifest = work_dir / "pubmed-local.manifest.json"

    manifest = measure("seed_manifest_render", lambda: _write_query_file(manifest_path, query_file))
    measure("fixture_input_stage", lambda: _stage_pubmed_fixture(pubmed_xml_file, xml_path))
    measure("pubtator_fixture_write", lambda: _write_pmat_pubtator_fixture(pubtator_path))
    litvar_payload = measure(
        "litvar_fixture_write", lambda: _write_pmat_litvar_fixture(litvar_path)
    )
    pubtator_stats = measure(
        "pubtator_edge_conversion",
        lambda: convert_pubtator_files_to_edge_jsonl([pubtator_path], pubtator_edges),
    )
    litvar_stats = measure(
        "litvar_edge_conversion",
        lambda: convert_litvar_exports_to_edge_jsonl(
            [litvar_path],
            litvar_edges,
            seeds=read_seed_queries(query_file),
        ),
    )
    settings = Settings(
        jwt_secret="pmat-bounded-slice-benchmark-local",
        pubmed_local_sqlite_path=db_path,
        pubmed_local_manifest_path=materialization_manifest,
    )
    materialization = measure(
        "pubmed_local_materialization",
        lambda: materialize_pubmed_local_store(
            settings,
            xml_files=[xml_path],
            pubtator_edge_files=[pubtator_edges],
            litvar_edge_files=[litvar_edges],
            query_file=query_file,
            output_path=db_path,
            manifest_path=materialization_manifest,
            source_version=source_version,
            coverage_completeness="partial",
            verify_md5_sidecars=True,
            xml_source_kind="baseline",
            force=True,
        ),
    )
    inspection = measure(
        "pubmed_local_preflight",
        lambda: inspect_pubmed_local_store(settings, verify_checksum=True),
    )
    store = PubMedLocalStore(db_path, manifest_path=materialization_manifest, enabled=True)
    lookup_stats = measure(
        "local_lookup_latency",
        lambda: _measure_lookup_runs(store, lookup_runs=lookup_runs),
    )
    batch_stats = measure(
        "local_batch_latency",
        lambda: _measure_batch_runs(store, batch_size=batch_size, batch_runs=batch_runs),
    )

    files = {
        "pubmed_sqlite": db_path,
        "manifest": materialization_manifest,
        "seed_query_tsv": query_file,
        "pubtator_edges": pubtator_edges,
        "litvar_edges": litvar_edges,
    }
    materialization_report = materialization.to_sanitized_dict()
    preflight_report = inspection.to_sanitized_dict()
    encoded_report_guard = {
        "local_path_values_emitted": False,
        "abstract_values_emitted": False,
        "secret_values_emitted": False,
        "seed_rows_emitted": False,
    }
    ready = (
        materialization.ready
        and inspection.ready
        and pubtator_stats.edge_count > 0
        and litvar_stats.edge_count > 0
        and lookup_stats["ok"] == lookup_runs
        and batch_stats["ok"] == batch_runs
    )
    return {
        "mode": "pmat_bounded_slice_benchmark",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ready": ready,
        "status": "ready" if ready else "failed",
        "source_scope": "tiny_fixture_benchmark",
        "retained_output": retained_output,
        "output_file_names": {key: path.name for key, path in files.items()},
        "guardrails": {
            "network": {"used": False, "provider": None},
            "source_download": "not_used",
            "real_corpus_materialization": "not_used",
            "storage_upload": "not_used",
            "runtime_seeding": "not_used",
            "runtime_flag_change": "not_used",
            "supabase_mutation": "not_used",
            "render_or_vercel_mutation": "not_used",
            "startup_download": "not_used",
            "request_time_materialization": "not_used",
            **encoded_report_guard,
        },
        "benchmark_contract": _benchmark_contract(),
        "measurements": {
            "total_wall_time_ms": _elapsed_ms(started),
            "steps": {step.name: step.to_dict() for step in steps},
            "rss_checkpoint_peak_bytes": _max_optional(step.rss_bytes_after for step in steps),
            "temp_disk_peak_bytes": max(step.temp_disk_bytes_after for step in steps),
            "output_size_bytes": {
                **{key: _safe_size(path) for key, path in files.items()},
                "total_generated": sum(_safe_size(path) for path in files.values()),
            },
            "input_profile": {
                "manifest_file_name": manifest_path.name,
                "pubmed_xml_file_name": pubmed_xml_file.name,
                "pubmed_xml_bytes": _safe_size(pubmed_xml_file),
                "seed_count": manifest.seed_count,
                "genes": list(manifest.genes),
                "corpus_labels": list(manifest.corpus_labels),
            },
            "row_count_profile": {
                "article_count": inspection.article_count,
                "deleted_count": inspection.deleted_count,
                "coverage_count": inspection.coverage_count,
                "source_file_count": inspection.source_file_count,
                "literature_edge_count": inspection.literature_edge_count,
            },
            "license_profile": {
                "licensed_abstract_count": inspection.licensed_abstract_count,
                "metadata_only_count": inspection.metadata_only_count,
                "pmc_license_overlay_count": inspection.pmc_license_overlay_count,
            },
            "edge_profile": {
                "pubtator_conversion": pubtator_stats.to_sanitized_dict(),
                "litvar_conversion": litvar_stats.to_sanitized_dict(),
                "import_stats_by_source": inspection.import_stats_by_source,
            },
            "preflight": {
                "elapsed_ms": _step_elapsed_ms(steps, "pubmed_local_preflight"),
                "ready": inspection.ready,
                "status": inspection.status,
                "checksum_verified": inspection.checksum_verified,
                "fts_status": inspection.fts_status,
            },
            "lookup_latency_ms": lookup_stats,
            "batch_latency_ms": batch_stats,
        },
        "materialization": materialization_report,
        "preflight": preflight_report,
        "rollback_procedure": _rollback_procedure(),
        "representative_slice_requirements": _representative_slice_requirements(),
        "notes": [
            "This is a tiny-fixture harness that proves the benchmark contract and "
            "sanitization shape before any representative real source slice.",
            "A real bounded slice still requires a separately approved operator-staged "
            "input set and must not download sources or mutate Supabase/Render/Vercel.",
        ],
        "fixture_payload_profile": {
            "pubtator_document_count": 2,
            "litvar_record_count": 1,
            "litvar_fixture_pmids": litvar_payload["summary"]["total_publications"],
        },
    }


def _write_query_file(manifest_path: Path, query_file: Path):
    manifest = load_seed_manifest(manifest_path)
    manifest.write_pubmed_query_tsv(query_file, force=True)
    return manifest


def _stage_pubmed_fixture(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    destination.with_name(f"{destination.name}.md5").write_text(
        f"{md5(destination.read_bytes(), usedforsecurity=False).hexdigest()}  "
        f"{destination.name}\n",
        encoding="utf-8",
    )


def _measure_lookup_runs(store: PubMedLocalStore, *, lookup_runs: int) -> dict[str, Any]:
    timings: list[int] = []
    statuses: dict[str, int] = {}
    article_counts: list[int] = []
    live_fallback_needed = False
    for _ in range(lookup_runs):
        started = time.perf_counter()
        result, needs_live = store.search_tool_result(_pmat_variant(), limit=10)
        timings.append(_elapsed_ms(started))
        statuses[result.status] = statuses.get(result.status, 0) + 1
        article_counts.append(int(result.summary.get("total") or 0))
        live_fallback_needed = live_fallback_needed or needs_live
    return {
        "runs": lookup_runs,
        "ok": statuses.get("local", 0),
        "statuses": statuses,
        "elapsed": _number_stats(timings),
        "article_count": _number_stats(article_counts),
        "live_fallback_needed": live_fallback_needed,
    }


def _measure_batch_runs(
    store: PubMedLocalStore,
    *,
    batch_size: int,
    batch_runs: int,
) -> dict[str, Any]:
    timings: list[int] = []
    statuses: dict[str, int] = {}
    for _ in range(batch_runs):
        started = time.perf_counter()
        local_count = 0
        for _index in range(batch_size):
            result, _needs_live = store.search_tool_result(_pmat_variant(), limit=10)
            local_count += 1 if result.status == "local" else 0
        timings.append(_elapsed_ms(started))
        status = "local" if local_count == batch_size else "partial"
        statuses[status] = statuses.get(status, 0) + 1
    return {
        "runs": batch_runs,
        "batch_size": batch_size,
        "ok": statuses.get("local", 0),
        "statuses": statuses,
        "elapsed": _number_stats(timings),
    }


def _pmat_variant() -> SimpleNamespace:
    return SimpleNamespace(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.260A>G",
        protein_change="p.Asp87Gly",
        dbsnp_rsid="rs1645931040",
        genomic_hg38="1-68444869-T-C",
    )


def _write_pmat_pubtator_fixture(path: Path) -> None:
    imported_title = "Long-term outcomes of RPE65 gene therapy"
    imported_abstract = "The RPE65 c.260A>G variant was linked by PubTator."
    orphan_title = "Unimported RPE65 edge"
    orphan_abstract = "The RPE65 c.260A>G orphan mention should be skipped."
    path.write_text(
        "\n".join(
            [
                *_pubtator_document_lines("37042101", imported_title, imported_abstract),
                "",
                *_pubtator_document_lines("39900000", orphan_title, orphan_abstract),
                "",
            ]
        ),
        encoding="utf-8",
    )


def _pubtator_document_lines(pmid: str, title: str, abstract: str) -> list[str]:
    text = f"{title} {abstract}"
    gene_start = text.index("RPE65")
    variant_start = text.index("c.260A>G")
    return [
        f"{pmid}|t|{title}",
        f"{pmid}|a|{abstract}",
        f"{pmid}\t{gene_start}\t{gene_start + len('RPE65')}\tRPE65\tGene\t6121",
        (
            f"{pmid}\t{variant_start}\t{variant_start + len('c.260A>G')}\tc.260A>G"
            "\tMutation\tc|SUB|A|260|G"
        ),
    ]


def _write_pmat_litvar_fixture(path: Path) -> dict[str, Any]:
    payload = {
        "request_identity": {
            "query": "RPE65 c.260A>G",
            "litvar_id": "litvar-rpe65-c260ag-pmat",
        },
        "seed": {
            "gene": "RPE65",
            "scope": "variant",
            "cdna": "c.260A>G",
            "transcript": "NM_000329.3:c.260A>G",
            "protein_change": "p.Asp87Gly",
            "rsid": "rs1645931040",
            "genomic_hg38": "1-68444869-T-C",
        },
        "summary": {
            "litvar_id": "litvar-rpe65-c260ag-pmat",
            "total_publications": 2,
            "articles": [
                {"pmid": "37042101", "title": "RPE65 gene therapy edge"},
                {"pmid": "39900001", "title": "RPE65 orphan edge"},
            ],
        },
        "raw": {"pmids": ["37042101", "39900001"]},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def _benchmark_contract() -> dict[str, Any]:
    return {
        "minimum_metrics": [
            "wall_time_ms",
            "rss_checkpoint_peak_bytes",
            "temp_disk_peak_bytes",
            "output_size_bytes",
            "row_count_profile",
            "license_profile",
            "edge_profile",
            "preflight.elapsed_ms",
            "lookup_latency_ms.p50_p95",
            "batch_latency_ms.p50_p95",
            "rollback_procedure",
        ],
        "required_guards": [
            "operator_staged_inputs_only",
            "no_network_download",
            "no_supabase_or_storage_mutation",
            "no_render_or_vercel_mutation",
            "no_runtime_seeding_or_flag_change",
            "sanitized_output_no_paths_raw_abstracts_or_secrets",
        ],
    }


def _representative_slice_requirements() -> dict[str, Any]:
    return {
        "approval_required": True,
        "source_scope_labels": ["targeted_seed", "filtered_pubmed"],
        "minimum_lookup_runs": 5,
        "minimum_batch_size": 1000,
        "minimum_batch_runs": 3,
        "must_record": [
            "seed manifest identity and corpus label",
            "staged input file count and byte count",
            "output SQLite/manifest/edge byte counts",
            "article/license/edge/source-file counts",
            "materialization/preflight/search wall times",
            "peak RSS from this harness plus external sampler for long slices",
            "temp disk peak and rollback/delete path",
        ],
    }


def _rollback_procedure() -> list[str]:
    return [
        "Discard or delete the generated benchmark output directory.",
        "Do not upload generated SQLite, manifest, or edge files to private Storage.",
        "Do not register generated artifacts in Supabase metadata.",
        "Keep PUBMED_LOCAL_ENABLED, LOCAL_EVIDENCE_ENABLED, and RAG_ENABLED unchanged.",
        "Before any later runtime seed, rerun preflight and get explicit approval.",
    ]


def _ensure_output_is_writable(work_dir: Path, *, force: bool) -> None:
    expected = {
        "pmat-seed.tsv",
        "pmat-pubtator.pubtator",
        "pmat-pubtator-edges.jsonl",
        "pmat-litvar.json",
        "pmat-litvar-edges.jsonl",
        "pubmed25n0001.xml",
        "pubmed25n0001.xml.md5",
        "pubmed-local.sqlite",
        "pubmed-local.manifest.json",
    }
    existing = [path.name for path in work_dir.iterdir() if path.name in expected]
    if existing and not force:
        raise SystemExit(
            "output directory already contains PMAT benchmark files; pass --force "
            "or choose an empty --output-dir"
        )


def _number_stats(values: list[int]) -> dict[str, int | None]:
    if not values:
        return {"n": 0, "min": None, "p50": None, "p95": None, "max": None}
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "min": ordered[0],
        "p50": _percentile(ordered, 50),
        "p95": _percentile(ordered, 95),
        "max": ordered[-1],
    }


def _percentile(ordered: list[int], percentile: int) -> int:
    index = max(0, min(len(ordered) - 1, ((len(ordered) * percentile + 99) // 100) - 1))
    return ordered[index]


def _step_elapsed_ms(steps: list[StepMeasurement], name: str) -> int | None:
    for step in steps:
        if step.name == name:
            return step.elapsed_ms
    return None


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))


def _safe_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _tree_size_bytes(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += _safe_size(child)
    return total


def _max_optional(values: Any) -> int | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _current_rss_bytes() -> int | None:
    try:
        import psutil  # type: ignore[import-not-found]

        return int(psutil.Process(os.getpid()).memory_info().rss)
    except Exception:
        pass

    if os.name == "nt":
        return _windows_rss_bytes()
    try:
        import resource

        rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return rss if sys.platform == "darwin" else rss * 1024
    except Exception:
        return None


def _windows_rss_bytes() -> int | None:
    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(ProcessMemoryCounters)
    kernel32 = ctypes.WinDLL("kernel32.dll")
    psapi = ctypes.WinDLL("psapi.dll")
    get_process_memory_info = psapi.GetProcessMemoryInfo
    get_process_memory_info.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    get_process_memory_info.restype = wintypes.BOOL
    handle = kernel32.GetCurrentProcess()
    ok = get_process_memory_info(
        handle,
        ctypes.byref(counters),
        ctypes.sizeof(counters),
    )
    return int(counters.WorkingSetSize) if ok else None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
