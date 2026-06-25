# Task E Performance And Memory Evidence

Last updated: 2026-06-26 00:20 +1000 - Codex.
Status: Live read-only evidence captured after pushing `080516b` and `0113521`
to `origin/main`. No deploy, Render env mutation, Supabase mutation, Vercel
command, or materialization was run.

## Scope

This evidence covers the Task E gate from
`docs/architecture-consistency-gate/plan.md`:

- repeated cold/warm report data-path timing;
- payload-size ceilings;
- desktop report preflight with required section slots;
- duplicate `/api/v1/viewer` first-paint guard;
- fast report-cache test target timing;
- Render peak RSS during ABCA4/RPE65/USH2A live read-only report audits.

The live backend had not been redeployed to the just-pushed commits during this
run. Treat live route gaps below as production follow-ups, not local-code
regressions.

## Commands

```powershell
npm --prefix app/web run audit:report-performance -- `
  --base=https://eamos-dev-sg.onrender.com `
  --runs=3 `
  --skip-viewer `
  --variant=ABCA4:c.5435T>A `
  --variant=RPE65:c.260A>G `
  --variant=USH2A:c.2276G>T `
  --max-report-payload-bytes=750000 `
  --max-section-envelope-bytes=200000 `
  --max-section-payload-bytes=200000

node scripts/eamos-report-preflight.mjs `
  --url=https://eamos-dev.vercel.app/report?gene=<GENE>&cdna=<ENCODED_CDNA> `
  --widths=1280 `
  --forbid-viewer `
  --timeout=60000

python -m pytest -m report_cache_contract -q --durations=10
python -m pytest tests/test_variant_cache.py -m "not slow" -q --durations=10
python -m pytest tests/test_lookup_section_fetch_contract.py -q --durations=10
```

Render RSS was sampled with the read-only Render metrics endpoint for
`srv-d8ctvoh9rddc73a27nb0` over the audit UTC window.

## Live Timing And Payload Results

Window: `2026-06-25T14:13:05Z` to `2026-06-25T14:16:44Z`.

| Variant | Lookup p50/p95 | Lookup warm p50/p95 | Summary p50/p95 | Report payload bytes | Total lookup bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| ABCA4 `c.5435T>A` | 5193 / 7410 ms | 4993 / 5193 ms | 4906 / 5232 ms | 59107 | 83174 |
| RPE65 `c.260A>G` | 3868 / 3907 ms | 3830 / 3868 ms | 3786 / 4274 ms | 77725 | 108001 |
| USH2A `c.2276G>T` | 5376 / 5992 ms | 4863 / 5376 ms | 5310 / 5395 ms | 403884 | 504311 |

| Variant | Publications p50/p95 | Computational p50/p95 | ClinGen/VCEP p50/p95 | Largest section payload |
| --- | ---: | ---: | ---: | ---: |
| ABCA4 `c.5435T>A` | 4997 / 5201 ms | 4785 / 4898 ms | 4708 / 5531 ms | 2059 bytes |
| RPE65 `c.260A>G` | 3863 / 4056 ms | 3903 / 3942 ms | 3801 / 4063 ms | 5911 bytes |
| USH2A `c.2276G>T` | 5307 / 5555 ms | 4800 / 5478 ms | 5101 / 5574 ms | 10819 bytes |

Payload ceilings passed:

- `report_payload <= 750000` bytes;
- section envelope `<= 200000` bytes;
- section payload `<= 200000` bytes.

Live gap:

- `/api/v1/lookup/sections` still returned `422` for `therapies_trials` on the
  deployed backend. Local contracts already include `therapies_trials`; this
  needs deploy-and-rerun verification before claiming production Task E closed.

## Render RSS

Memory metrics window:
`2026-06-25T14:12:05Z..2026-06-25T14:17:54Z`.

| Instance | Points | Min | Avg | Peak | Peak of 2 GB cap |
| --- | ---: | ---: | ---: | ---: | ---: |
| `srv-d8ctvoh9rddc73a27nb0-xcfhz` | 6 | 636.0 MB | 639.0 MB | 641.9 MB | 31.3% |

Result: no RSS spike, OOM, or restart was observed during the three-variant
read-only report audit window.

## Browser Preflight

Desktop preflight passed at 1280 px for:

- ABCA4 `c.5435T>A`;
- RPE65 `c.260A>G`;
- USH2A `c.2276G>T`.

Observed for each:

- `html overflow: 0px`;
- `body overflow: 0px`;
- `fixable offenders: 0`;
- `required report slots: missing=[] / missing-anchors=[]`;
- `--forbid-viewer` passed, so no first-paint `/api/v1/viewer` request was
  observed.

## Fast Test Timing

| Target | Result | Wall time |
| --- | --- | ---: |
| `python -m pytest -m report_cache_contract -q --durations=10` | passed | 27.9 s |
| `python -m pytest tests/test_variant_cache.py -m "not slow" -q --durations=10` | passed | 15.1 s |
| `python -m pytest tests/test_lookup_section_fetch_contract.py -q --durations=10` | passed | 23.2 s |

The fast cache/report contract gate is now separate from slow legacy
integration-style cache cases.

## Live Health Snapshot

Read-only health checks after the audit:

- `/healthz`: `status=ok`, `database=ok`, `llm_provider=gateway`,
  `use_real_apis=true`.
- `/api/v1/health/provider-cache`: `status=ok`;
  `local_evidence_runtime_assets.ready=true` with `ready_count=4/4`;
  `clingen_local.status=ready`, `classification_count=12690`;
  PubMed local and literature embeddings remain disabled/missing as expected.

## Remaining Task E Work

Task E is locally satisfied as a gate harness, but not production-closed:

1. Deploy the pushed backend/report-cache changes when Steven explicitly
   approves deployment.
2. Rerun this same audit against the deployed commit and confirm
   `therapies_trials` no longer returns 422.
3. Capture lookup timing header data only if `LOOKUP_TIMING_DIAGNOSTICS_ENABLED`
   is deliberately enabled for a bounded diagnostic run.
4. If a stricter "no performance issues" sign-off is needed, repeat the memory
   watch for a longer window and include a viewer-enabled audit separately.
