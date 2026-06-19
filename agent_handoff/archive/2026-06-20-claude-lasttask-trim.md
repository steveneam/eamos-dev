# Claude Last-Task trim - archived 2026-06-20 04:18 +1000
Removed from agent_handoff/CURRENT.md to pass the 500-line handoff-lint gate.
All content below is historical (shipped + on prod 2026-06-16) and also lives in git history + ~/.claude/plans/next-session-eamos.md.

## Block A - Epic-A A10/A11 closeout detail

--- Older Epic-A (A1–A12, A10, A11) detail below is HISTORICAL (all shipped + on prod 2026-06-16). ---

--- A11 detail (closed earlier this session, doc-only): Closed A11 with
`docs/stability-audit/a11-render-budget.md` — grounded the OOM/concurrency safety budget in MEASURED
prod RSS (Render MCP) and recorded the sizing decisions. **KEEP Standard 2 GB** (idle ~0.57 GB / 2 GB ~27% post-A1–A9; OOM'd instance hit
2.07 GB on 06-15; heavy compute off the request path — all guards already enforced by Codex
A1/A2: cache-or-fail-closed `allow_run=False`, `BoundedSemaphore(1)`, `RLIMIT_AS` 1536 MB,
residue cap 5000-safe-on-0, 20 MB upload + 20 MB gzip-decompress ceilings, batch LRU 128/256
TTL 3600s). **KEEP 60 GB disk** (right-sized: ~5–6 GB / 60 GB ~10% today, but durable Supabase
holds dbSNP ~29.6 GB + phyloP ~9.9 GB → full local-first stack ~50–55 GB; Render disks can't
shrink). Doc adds a product-value materialization sequencing lens (Tier 1 ClinGen+PubMed/RAG →
Tier 2 predictor caches → Tier 3 dbSNP/phyloP) referencing Codex's `materialization-plan.md`.
One residual = server-side viewer window-width ceiling is FE-only (A10) today → Codex follow-up,
non-blocking. Answered Steven live: full Render account = 1 web svc (Standard 2 GB) + 60 GB disk,
no Postgres/KV, ≈$40/mo list. **No code/backend/infra change**; `LLM_PROVIDER=mock`; held files
excluded. NEXT = A12 (Codex, build-time) + Tier-1 materialization (Codex lane + gated offline
downloads). Prior milestone (A10 FE virtualization, commit `858a036`, Vercel
`dpl_5g1mV9EhYnz8i7cyrMwarnMw9KWr`) detail retained below for context:

**Prior (2026-06-16 20:42 +1000 - Claude - Epic A A10 (FE virtualization) shipped):**
Implemented + shipped A10, the last request-reachable (FE browser-crash) item of the
stability epic. Commit `858a036` (FE-only, 5 files), pushed, Vercel auto-deploying
(`dpl_5g1mV9EhYnz8i7cyrMwarnMw9KWr`, BUILDING at push time — confirm READY + spot-check).
- **FullLocusViewer** windowed (fixed-height virtual scroller; only on-screen rows mount)
  + `.fl-scroller` gains a viewport `max-height` so the full-gene locus scrolls in its own
  pane — **Steven-approved** visible change (virtualization is impossible without a bounded
  viewport; the scroller was already built for internal scroll). Live-verified RPE65
  full-gene: 265 rows / 21,200 base-spans → **~54 rows / ~4,300 mounted**; scroll shifts the
  window, variant row mounts + highlights, exon/intron banding intact. CFTR (~3,150 rows) =
  same bounded path → no crash.
- **ReportGeneViewer** AlphaMissense band → ≤800 mean-score bins (was ~5,200 rect+title per
  residue); ≤800-aa proteins unchanged. Node-proven (533→identical, 5,202→≤800, averaging,
  ends, variant sums). On-screen long-protein heatmap is a post-deploy spot-check (RPE65
  fixture has no AM data; the local dev server's prod API proxy was 5xx-ing on
  `/lookup/sections`).
- **CodonDetail** O(n²) per-render scans hoisted to parent useMemo Set/Map (search
  window-string + clinvar/oligo/qIdx `flat.findIndex`) → O(1) per base.
- **SequenceViewerV2** `onRestrictionSelect` → useCallback (blocksEqual holds during drags).
Verified: tsc + eslint green; 33/33 Node logic-equivalence checks; live browser pass.
Minor follow-up: full-locus auto-scroll targets model `variantRowIndex` (≈223) but the
variant pin is on row ≈200 — pre-existing adapter mismatch, unchanged from the original;
log for the adapter owner.
**Commit status (UPDATE 2026-06-16 22:30):** Claude drove the coordinated commit as commit-driver —
Codex's A2+A12 backend tree is now committed (`a8710cf`) + deployed (`dep-d8ok50kvikkc73f8elhg`
live + verified) + the A11 doc/handoff/graphify in the following docs commit. No longer uncommitted.

## Block B - historical 2026-06-15/16 Latest narratives + resume prompts

<!-- history below: 2026-06-16 19:46 A1–A9 (shipped 0a209a1); then 1e86a78 deploy-recovery + incident (resolved) -->
**Latest (2026-06-16 19:46 +1000 - Claude - Epic A A1–A9 shipped + prod-verified):**
Adversarially re-reviewed Codex's Epic A A1–A9, ran backend pytest GREEN, committed `0a209a1`,
pushed, deployed Render SG + Vercel, live-verified prod (USH2A `cache_hit`/248 features ~571 MB;
A2 unauth batch upload → 401). Full detail in `~/.claude/plans/next-session-eamos.md`.

<!-- history below: 1e86a78 deploy-recovery + incident (now resolved; A1–A9 superseded it) -->
**Latest (2026-06-15 22:16 +1000 - Claude - deploy recovery + OPEN prod incident):**
Recovered the dropped-webhook Vercel deploy of Codex's `1e86a78`, then discovered `1e86a78`
is a degraded prod release.
- **Deploy recovery (DONE):** `1e86a78` never auto-deployed to `eamos-dev` (one-off dropped
  GitHub->Vercel webhook; auto-deploy otherwise healthy). Re-triggered via `50d9dc8` (handoff +
  `app/web/.gitignore` ignores `.vercel`) -> Vercel built `dpl_8Hced...` READY, aliased to
  `eamos-dev.vercel.app` (200), carrying `1e86a78`'s `ReportGeneViewer.tsx`. Removed the stray
  local `app/web/.vercel` link and **deleted the wrong `web` Vercel project** (Steven OK; Codex's
  manual `vercel --prod` from `app/web` had gone there, to `web-beryl-delta-96`, never the real
  domain). `vercel project ls` -> only `eamos-dev`. **Always deploy from repo root, never `app/web`.**
- **OPEN INCIDENT (next session):** `1e86a78` reached Vercel prod for the first time and showed
  two regressions, both backend-rooted: (1) **Render SG OOM >2GB** (instance 8wqsn, 22:00, on the
  USH2A 5,202 aa protein annotation via the reworked `protein_annotation.py` - inefficient/leak);
  (2) **protein features missing** vs Codex's earlier "50 blocks/248 hits" because the new
  UniProt-first path needs `uniprot_features_enabled` + a seeded Render feature index, both
  off/not-ready. Full write-up: RISKS.md top section (committed `814c1fd`).
- **Steven deferred the fix to next session + authorized Claude CROSS-LANE** (backend + frontend +
  Render/Vercel) to fix it. Prod left on `1e86a78` (degraded). Rollback-first is a valid opener
  (Vercel target `dpl_4FZS9XtQxjrvXmDFyCNGtPPpvpfc` = `1c2df8b`).
- Guardrails held: `LLM_PROVIDER=mock`; no Supabase apply / provider flip; held files excluded
  (`docs/proprietary/eamos-ai-gateway.md`, `scripts/eamos-encoding-scan.mjs`, `graphify-out/2026-06-15/`).

**Next (priority):**
1. **Fix the `1e86a78` regression** (cross-lane authorized): profile + fix `protein_annotation.py`
   memory on large proteins (USH2A); fix the flag-off fallback so the full Pfam/HMMER architecture
   shows (no feature loss), OR provision+seed the Render UniProt index + flip the flag. Coordinate
   with Codex (locks). Then redeploy (Render hook + Vercel) and live-verify USH2A.
2. If the fix isn't quick, **roll back first** (Vercel `1c2df8b` + Render pre-`1e86a78`) to restore
   the verified-good protein architecture, then fix offline.
3. Backlog: genomic view Section 4 (not started); graphify semantic pass; B1 forest/B7 beeswarm.

**Resume prompt:**
```
# Resume prompt - 2026-06-15 23:30 +1000 - Claude (1e86a78 incident RESOLVED + verified on prod)
# NOTE: the 1e86a78 fix task in the body below is DONE (Codex shipped a9de024/dd3b71d; Claude verified live on SG at 23:30 - USH2A 200 cache_hit/248 hits, memory flat ~1.21GB, no OOM). Do NOT re-fix. Next work = backlog: genomic view Section 4, a backend hmmscan e-value/overlap threshold (raw 248 hits incl. cross-fold noise), graphify semantic pass. START HERE = ~/.claude/plans/next-session-eamos.md (✅ RESOLVED section). Body kept verbatim for history:
# --- historical resume prompt (1e86a78 fix, now complete) ---
# Resume prompt - 2026-06-15 22:16 +1000 - Claude (OPEN prod incident: fix 1e86a78, cross-lane authorized)
Eamos. Open from D:\eamos. Read ~/.claude/plans/next-session-eamos.md (START HERE) + agent_handoff/CURRENT.md (## Active Status + ## Log Edit-Lock + ## Current State + ## Claude; protocol -> README.md) + agent_handoff/RISKS.md (TOP section = the 1e86a78 incident). First: git -C D:/eamos fetch origin && git status --short --branch && git log -6 --oneline.
Context: Tonight Claude recovered a dropped-webhook Vercel deploy of Codex's 1e86a78 (re-triggered via 50d9dc8 -> live on eamos-dev.vercel.app), removed the stray app/web/.vercel link, and deleted the wrong `web` Vercel project (Steven OK). But 1e86a78 reached prod for the first time and is DEGRADED: (1) Render SG OOM >2GB on the USH2A protein annotation (reworked protein_annotation.py - inefficient/leak), and (2) protein features missing because the new UniProt-first path needs uniprot_features_enabled + a seeded Render feature index, both off/not-ready. Full detail in RISKS.md (committed 814c1fd).
Task: FIX the 1e86a78 regression. STEVEN AUTHORIZED CLAUDE CROSS-LANE this session - drive backend + frontend + web server (Render + Vercel). Plan: reproduce USH2A locally + watch RSS; fix protein_annotation memory (stream/cap, no whole-payload buffering); make flag-off fall back to full Pfam/HMMER architecture without dropping features OR provision+seed the Render UniProt index (pre-seed, no startup-download) + flip the flag; verify (pytest + local browser); deploy Render via .render-deploy-hook + Vercel auto on push; live-verify USH2A full architecture + no OOM under load. Rollback-first is a valid opener if the fix isn't quick (Vercel dpl_4FZS9XtQxjrvXmDFyCNGtPPpvpfc = 1c2df8b; Render pre-1e86a78). COORDINATE with Codex (Log Edit-Lock + Shared File Locks; he got the same handoff - don't double-drive app/backend/**). Guardrails: never cd (git -C / npm --prefix), explicit pathspecs never git add -A, LLM stays mock, no Supabase apply/provider flip without Steven, held files (ai-gateway doc, encoding-scan, graphify-out/2026-06-15) stay excluded, deploy from repo root never app/web. End clear-safe.
```

