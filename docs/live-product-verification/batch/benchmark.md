# Synthetic WES benchmark — 2026-07-22

Command:

```bash
cd app/backend
.venv/bin/python -m app.fixtures.batch.benchmark_wes
```

Environment: Linux 6.8 x86-64, Python 3.12.3, `pysam==0.24.0`. The generator
contains no patient data. Timings cover private staging, receipt inspection,
HTSlib iteration, coordinate filtering, and construction of the bounded
post-filter candidate set. Source generation is outside the timer.

| Raw rows | Retained | Source bytes | Wall time | Peak traced Python heap |
| ---: | ---: | ---: | ---: | ---: |
| 25,000 | 10 | 764,102 | 4.932 s | 1.738 MiB |
| 75,000 | 500 | 2,314,102 | 13.947 s | 2.010 MiB |
| 150,000 | 5,000 | 4,689,103 | 30.992 s | 18.579 MiB |

The process-wide maximum RSS was 387.152 MiB for this interpreter, but that is
an absolute high-water mark including the preloaded Python/backend runtime; it
is not an isolated Batch delta. Container RSS and startup/image measurements
remain a Wave 2 composition gate.

## Neutral limits frozen from this lane

| Control | V1 limit | Evidence/posture |
| --- | ---: | --- |
| Compressed upload | deployment `MAX_UPLOAD_MB` (20 MiB default) | Existing neutral deployment control |
| Decompressed bytes | min(512 MiB, 20× compressed limit) | Independent bomb bound |
| Raw records | 200,000 | Covers the validated 150k matrix with headroom |
| Samples | 3 | Proband/small-family envelope |
| Unique normalized rows sent to annotation | 5,000 | Validated post-filter cap |
| Synchronous preparation wall time | 120 s | Checked while streaming; normalizer subprocess also has a 15 s per-call bound |
| Concurrent jobs per process | 1 | Durable lease-backed executor |
| Concurrent direct lookups per job | 3 | Existing free-runtime bound |

The automated matrix also covers filtered sets of 0, 10, 500, 5,000, and over
cap; normalized duplicates that occur before and after the old raw-row cap;
gzip/multiallelic parity; sample/cohort/contig/build/format rejection; restart
retry; cancellation/deletion; snapshot cursors; and all four streamed exports.

These limits are scientific/runtime safety limits, not account tiers. WGS,
cohort-scale matrices, BCF, SV/CNV, and gVCF remain unavailable until their own
streaming, storage, parity, and validation evidence exists.
