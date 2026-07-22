"""Synthetic-only WES intake benchmark for the Batch V2 release matrix."""

from __future__ import annotations

import json
from pathlib import Path
import platform
import resource
import tempfile
import time
import tracemalloc

import pysam

from app.schemas.batch import BatchFilters
from app.services.batch_engine.filters import GenomicInterval, filter_pre_annotation
from app.services.batch_engine.intake import (
    iter_staged_variants,
    remove_staged_vcf,
    stage_vcf_file,
)

MATRIX = ((25_000, 10), (75_000, 500), (150_000, 5_000))


def run_matrix() -> dict:
    measurements = []
    with tempfile.TemporaryDirectory(prefix="eamos-batch-benchmark-") as directory:
        root = Path(directory)
        for raw_rows, retained_rows in MATRIX:
            source_path = root / f"synthetic-{raw_rows}.vcf"
            _write_vcf(source_path, row_count=raw_rows)
            tracemalloc.start()
            started = time.perf_counter()
            with source_path.open("rb") as source:
                staged = stage_vcf_file(
                    source,
                    staging_dir=root / "staged",
                    filename=source_path.name,
                    max_compressed_bytes=64 * 1024 * 1024,
                    max_raw_records=200_000,
                    post_filter_variant_cap=5_000,
                )
            try:
                filtered = filter_pre_annotation(
                    iter_staged_variants(staged, upload_ref=f"benchmark-{raw_rows}"),
                    legacy_filters=BatchFilters(panel_slug="synthetic-benchmark"),
                    filter_plan=None,
                    panel_intervals=(
                        GenomicInterval(
                            chromosome="1",
                            start=1,
                            end=retained_rows,
                        ),
                    ),
                    source_snapshot_id=f"benchmark-{raw_rows}",
                    post_filter_cap=5_000,
                )
            finally:
                remove_staged_vcf(staged)
            elapsed_seconds = time.perf_counter() - started
            _current_bytes, peak_python_bytes = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            measurements.append(
                {
                    "raw_rows": raw_rows,
                    "retained_rows": len(filtered.candidates),
                    "source_bytes": source_path.stat().st_size,
                    "wall_seconds": round(elapsed_seconds, 3),
                    "peak_python_mib": round(peak_python_bytes / (1024 * 1024), 3),
                    "process_max_rss_mib": round(
                        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                        3,
                    ),
                }
            )
    return {
        "schema_version": "batch_wes_benchmark.v1",
        "synthetic_only": True,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "pysam": pysam.__version__,
        "post_filter_cap": 5_000,
        "measurements": measurements,
    }


def _write_vcf(path: Path, *, row_count: int) -> None:
    with path.open("w", encoding="ascii", newline="") as handle:
        handle.write(
            "##fileformat=VCFv4.2\n"
            "##reference=GRCh38.p14\n"
            "##contig=<ID=1,length=248956422,assembly=GRCh38>\n"
            '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n'
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tPROBAND\n"
        )
        for position in range(1, row_count + 1):
            handle.write(f"1\t{position}\t.\tA\tC\t60\tPASS\t.\tGT\t0/1\n")


if __name__ == "__main__":
    print(json.dumps(run_matrix(), indent=2, sort_keys=True))
