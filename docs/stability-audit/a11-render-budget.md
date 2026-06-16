# A11 — Render instance & disk budget (Epic A, infra)

Status: **A11 closed** (documentation + decision; guards already enforced by A1/A2).
Owner: Claude (infra/shared), with Codex (backend lane) owning any code follow-up.
Last verified against live prod: **2026-06-16 21:27 +1000**.

Companion docs: `docs/stability-audit/findings.md` (the audit), Codex's
execution plan `docs/backend-build-ledger-runtime/materialization-plan.md`
(per-asset sequence), `docs/backend-build-ledger-runtime/design.md` (runtime
policy). This doc is the **infra budget** — it does not duplicate the
materialization steps, it grounds the numbers and records the sizing decision.

---

## TL;DR — decisions

1. **Compute: keep the Render Standard plan (2 GB / 1 CPU). Do NOT upsize.**
   After A1–A9, measured idle RSS dropped to **~0.57 GB / 2 GB (~27%)** and the
   heavy compute (HMMER `hmmscan`) is off the request path. The 2 GB ceiling the
   whole audit summed against now has comfortable headroom.
2. **Storage: keep the 60 GB disk. It is right-sized for the destination, not
   over-provisioned.** It only *looks* empty (~10% full) because materialization
   is mid-rollout. The durable Supabase footprint already shows **dbSNP ~29.6 GB
   + phyloP ~9.9 GB**; the full local-first stack lands at **~50–55 GB**.
   Render disks **cannot be shrunk** (only grown), so the lever is "fill it to
   earn the $15/mo," not "downsize."
3. The OOM/concurrency safety budget below is **already enforced in code** (Codex,
   A1/A2). A11's deliverable is to ground those numbers in measured RSS and record
   them in one place. One residual (server-side viewer window-width ceiling) is a
   Codex-lane follow-up, not a blocker.

Total Render spend ≈ **$40/mo** (Standard service $25 + 60 GB disk $15; list
rates — MCP cannot read the actual invoice/discounts). No Postgres, no Key-Value.

---

## Part A — Compute budget (instance sizing)

### Measured RSS (prod, `srv-d8ctvoh9rddc73a27nb0`, 2 GB hard cap = 2,147,483,600 B)

| Window | Instance | RSS | Note |
| --- | --- | --- | --- |
| 2026-06-15 ~21:30–22:00 +1000 | `8wqsn` | **2.07 GB** | The OOM. Exceeded the 2 GB cap → killed + restarted. |
| Pre-fix steady state | `zwl5k`/`mc2zh` | ~1.2–1.6 GB | `1e86a78` idled heavy. |
| **Post A1–A9** (from 2026-06-16 ~19:45 +1000) | `mms2f` | **~0.53–0.58 GB** | Heavy compute off the request path; idle ~halved. |

The OOM was real and measured, not inferred. The fixes removed the structural
risk: idle headroom is now ~1.45 GB.

### Enforced guards (already in code — the safety budget)

All values below are live in the working tree (Codex, A1/A2). Grounded in the
2 GB cap and measured single-`hmmscan` behaviour, not round guesses:

| Budget knob | Value | Where | Rationale vs 2 GB |
| --- | --- | --- | --- |
| Web tier = cache-or-fail-closed | `allow_run=False` on `/viewer` + lookup snapshot | `gene_viewer.py:1430,1495`; `protein_annotation.py:478` | No in-request `hmmscan` on the hot paths; annotation only populates cache via the offline warmer. |
| hmmscan concurrency | **`BoundedSemaphore(1)`** | `protein_annotation.py:35,245` | At most one `hmmscan` per instance → parallel large-protein requests cannot sum past 2 GB. |
| hmmscan child memory | **`RLIMIT_AS` 1536 MB** via `preexec_fn` | `protein_annotation.py:1415–1425` (`_hmmscan_preexec_fn`) | Child is hard-capped well under the cap; leaves ~0.6 GB for the parent + OS. |
| hmmscan residue cap | **5000** aa, `<=0` ⇒ safe default (never "unlimited") | `protein_annotation.py:33,1405–1412` (`_safe_hmmscan_max_residues`) | Stops USH2A (5202 aa) and bounds the largest in-request scan. |
| hmmscan timeout | 30 s | `protein_annotation_hmmscan_timeout_seconds` | Bounds worker-hold time. |
| Batch upload raw cap | **20 MB** | `config.py:28` (`max_upload_mb`) | Bounds the request body. |
| Batch gzip decompressed ceiling | **20 MB** | `vcf_ingest.py:13` (`DEFAULT_MAX_DECOMPRESSED_BYTES`) | Closes the gzip-bomb (was unbounded `gzip.decompress`). |
| Batch in-process registries | LRU **128 uploads / 256 jobs**, TTL **3600 s** | `config.py:60–62` | `_uploads`/`_jobs` no longer leak monotonically. |
| Worker pools | run-chat 2, workflow 5; per-tool/LLM timeouts | `config.py:73–82` | Bounds concurrent heavy in-band work + hang exposure. |
| Result-set / payload caps | `ReportPayload` list `max_length`, screening-primer sites `max_length=50` | A8 | Bounds externally-driven response sizes. |

### Residual (Codex-lane follow-up, non-blocking)

- **Viewer window width** is bounded at the **frontend** (A10 virtualization: the
  full-locus viewer windows rows; AlphaMissense heatmap ≤800 bins). There is **no
  explicit server-side max-window-width param ceiling** on `/viewer` today; the A8
  payload caps bound the response, but a malicious wide-window request still builds
  the full payload server-side. Low risk (rate-limited, bounded by gene length),
  but a server-side window cap would make the "max window width" budget element
  server-enforced rather than FE-enforced. Hand to Codex if wanted.

### Verdict — compute

**Keep Standard 2 GB. No dedicated worker needed.** The cache-or-fail-closed web
tier + semaphore + RLIMIT mean the instance no longer sums toward the cap under
load. Revisit only if (a) real traffic concurrency rises materially, or (b) a
future feature reintroduces in-request heavy compute — in which case prefer a
background worker over upsizing the web tier.

---

## Part B — Storage budget (disk sizing & fill)

### What the disk is for

`/var/data/eamos` (60 GB) is the **local-file runtime cache** for assets that
physically require a local file handle and cannot be read over the network from
Supabase object storage:

- **pysam/tabix** — dbSNP, ClinVar, gnomAD, predictor `.vcf.gz` + `.tbi`
- **HMMER `hmmscan`** — the Pfam binary indexes
- **sqlite / sqlite-vec** — PubMed local, ClinGen local, the literature RAG vector store
- **2bit** — the hg38 reference genome

Supabase private Storage is the **durable** copy; the disk is the **working**
copy. Hence the standing rule: materialize **offline → push to Supabase → sync to
disk**, never download at startup (`startup_download_allowed=false`), and never
seed via Render one-off jobs (they don't write the web-service disk).

### Current fill (live, 2026-06-16 21:27 +1000)

| Asset | Status | Size |
| --- | --- | --- |
| hg38 `hg38.2bit` | ready | **0.835 GB** (835,393,456 B) |
| Pfam/HMMER (`Pfam-A.hmm` + hmmpress indexes) | ready | ~1.5–3 GB (not size-reported in health) |
| AlphaMissense hg38 | ready | **0.643 GB** (642,961,469 B) |
| Compact coordinate index | ready | 0.012 GB (11,597,735 B) |
| MANE + RefSeq GFFs | ready | ~0.5 GB |
| app SQLite + uploads/reports | live | small |
| **Total in use** | | **≈ 5–6 GB of 60 GB (~10%)** |

(Disk usage is not exposed via the Render metrics API — exact fill needs the
dashboard or SSH. The above is summed from `provider-cache` `actual_size_bytes`
plus known asset footprints.)

### Destination footprint (why 60 GB is right-sized)

From the durable Supabase inventory in `materialization-plan.md` (real objects,
not estimates) plus the pending predictor/literature lanes:

| Asset (pending) | Footprint | Source of figure |
| --- | --- | --- |
| **dbSNP** (`ncbi_dbsnp_gcf_000001405_40`, bgzip VCF + `.tbi`) | **~29.6 GB** | 6 objects already in Storage |
| **phyloP 100-way** (`ucsc_phylop100way_hg38`, bigWig) | **~9.9 GB** | 4 objects already in Storage |
| ClinVar local (bgzip + `.tbi`) | ~1–2 GB (est) | not yet uploaded |
| ESM1b / CI-SpliceAI / CAPICE score caches | several GB total (est) | not yet materialized |
| PubMed local + literature embeddings (RAG) | ~1–5 GB (est) | not yet materialized |
| ClinGen local, RepeatMasker, MaveDB | small | not yet materialized |
| **Current ready** | ~5–6 GB | (above) |
| **Projected total** | **~50–55 GB** | |

**dbSNP (~30 GB) + phyloP (~10 GB) alone consume ~40 GB.** So 60 GB is
appropriately sized for the full local-first stack — even slightly tight if every
lane materializes. It is *not* over-provisioned.

### Verdict — storage

**Keep 60 GB.** It cannot be shrunk without recreating the service (and
re-materializing every asset), so "downsize to save money" is not a real option.
The $15/mo is effectively committed; the productive move is to **use the headroom**
by materializing the pending stack (Part C). If the intent were to stay lean
(Tier 1 only, ~+5 GB → ~10 GB used), the disk would be over-provisioned — but the
durable dbSNP/phyloP objects show the plan of record is the full stack.

---

## Part C — Materialization roadmap (sequencing)

Codex's `materialization-plan.md` owns the **execution mechanics** (offline build
→ Supabase register → Render-shell seed → health verify) and sequences the
**infra batch** (dbSNP → phyloP → ClinVar → RepeatMasker) first because it gates
`LOCAL_EVIDENCE_ENABLED`. Below is the **product-value lens** on top of that — a
recommendation for *which lanes buy the most visible product per GB*, for Steven
to weigh against the infra-batch ordering.

### Tier 1 — small footprint, biggest product unlock (recommended first)
- **ClinGen local** (<0.5 GB) → source-backed VCEP classifications (FE already wired).
- **PubMed local + literature embeddings** (~1–5 GB) → the literature engine **and**
  the variant-chat RAG. Natural companion to the staged AI-gateway work.

### Tier 2 — predictor score caches (flip report §2 from mock → real)
- **CI-SpliceAI**, **CAPICE**, **ESM1b** — the in-silico predictor table is mock until these land.

### Tier 3 — heavy offline-clinical + conservation (the big GB)
- **dbSNP** (~30 GB), **phyloP** (~10 GB), **ClinVar**, **RepeatMasker** → offline
  clinical lookups (less external-API dependency + latency) and the **real
  conservation axis** in the ACMG EvidenceFingerprint (mock today). This is Codex's
  infra batch; biggest disk consumer.

> Note the tension: Codex's plan does the **infra batch (Tier 3) first** to unlock
> `local_evidence_orchestrator`; the product-value lens does **Tier 1 first** for
> quick visible wins. Which leads is **Steven's product call** — both are valid;
> they're not mutually exclusive (Tier 1 is small and can run alongside the infra batch).

### Hard gates (unchanged, from `materialization-plan.md`)
- `LLM_PROVIDER=mock` until the AI-gateway release gate is crossed.
- No coordinate/protein **startup** materialization; no raw-GFF runtime scans.
- No Render one-off jobs for disk seeding.
- No `LOCAL_EVIDENCE_ENABLED=true` until the full indexed batch is verified.
- **A12 caveat:** the materializer CLIs must **stream** (not load whole corpora into
  RAM) if ever run on the Render box — otherwise they reintroduce the OOM class.
  Prefer running them offline. (Epic A A12, Codex, build-time.)
