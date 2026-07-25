# Research-unblock and wiring plan

Status: proposed; not started.

Stamped: 2026-07-25 06:03 +0000 · Claude.

Canonical inputs:

- `docs/live-product-verification/free-access-licence-review.md` (what cleared)
- `docs/live-product-verification/wave3-approval-cards.md` (+ its reconciliation)
- `plans/primer-specificity-engine/plan.md` (the named product need)
- `plans/live-product-completion/{research,spec,plan}.md` (the campaign this continues)
- `app/backend/app/runtime-tree-manifest-syd2.json` (what is actually mounted)

## What changed

Steven confirmed on 2026-07-25 that Eamos is **for research, free, and
non-profit**. That answers the entity question and the diagnostic-use question
at once, which between them were holding **ten registry records** plus two Wave 3
NO-GOs. The conventional academic tier now applies to CADD, REVEL, ESM-1b,
SpliceAI precomputed, PrimateAI-3D, Pangolin, and UCSC isPcr.

This continues the Codex campaign rather than replacing it. Waves 0-2 are merged;
Wave 3's cards are frozen and reconciled; Wave 4 has its first slice merged
(PR #31). What follows is the work that the licence determination newly makes
possible, sequenced against a constraint that has now become binding.

## The constraint has moved: disk, not licence

This is the single most important planning fact and it is easy to miss, because
for months the answer to "why can't we have this predictor" was licensing.

Measured, not estimated:

```
syd2 host disk                 61 G used / 99 G   -> 34 G free
current mounted asset tree     47,943,536,945 B   (44.65 GiB, 23 items)
Supabase bucket allowance      43.277 / 100 GB    -> ~57 GB headroom
```

Registry size estimates for what just cleared:

```
CADD hg38               ~30 GB
SpliceAI precomputed    ~20 GB
PrimateAI-3D            ~10 GB
ESM-1b assembled         ~2-4 GB
REVEL                    ~2 GB
Pangolin                 undecided
                        ---------
                        ~64-66 GB
```

**~65 GB of newly-permitted data against 34 GB of free syd2 disk.** Taking it
all whole-genome is not possible, and filling the disk on the sole serving host
is a production risk, not just a tidiness problem. Two consequences:

1. **Bounded slices are the default, not an optimization.** Eamos already has
   this pattern and it is proven: `eamos_compact_index_build`,
   `eamos_esm1b_mane_context_build`, `eamos_pmat_bounded_slice_benchmark`, and
   the RepeatMasker `interval-index.jsonl` in the live tree. A MANE-Select
   coding+splice-flank slice of CADD or SpliceAI is a fraction of whole-genome
   and covers what `/report` §2 actually renders.
2. **Order by value-per-GB, not by prestige.** isPcr (a binary), REVEL (~2 GB),
   and ESM-1b (~2-4 GB) deliver visible product change for ~6 GB. CADD (~30 GB)
   is the largest item and should be last and sliced.

If whole-genome CADD or SpliceAI is genuinely wanted, that is a **syd2 disk
resize** — a founder spend decision, and its own gate. Do not quietly grow into
it.

## Phase 1 — record the determination (cheap, unblocks everything downstream)

No acquisition. Pure bookkeeping that everything else depends on.

1. Write the determination into `registry_records.py` per item: accepted terms,
   dated basis, research-use condition. Never a silent status flip.
2. Add the standing constraint that research-use clearances lapse if Eamos is
   ever positioned for clinical/diagnostic use.
3. Revisit the `commercial_allowed` / `restricted_unlicensed` vocabulary — it
   encodes a commercial assumption and now reads misleadingly.
4. Split the Wave 3 "UCSC isPcr + `hg38.2bit`" NO-GO row into the mounted,
   approved reference and the pending binary.
5. **Apply for OMIM academic access now** — it has real lead time and gates
   InterVar behind it. Non-profit research status makes the application
   straightforward; it is still an application.

## Phase 2 — primer specificity engine (the named need, zero new code)

Full detail in `plans/primer-specificity-engine/plan.md`. Under the
determination, Route A is now the expected path:

1. Accept UCSC terms for non-profit research use; record the basis.
2. Materialize the `isPcr` binary to `bio_assets/bin/isPcr` as a Wave 3-style
   card with checksum, SBOM row, and functional probe.
3. Flip `primer_specificity_provider` to the isPcr provider.
4. Preflight goes green; `hg38.2bit` is already mounted at exactly the
   configured path. **No application code changes.**
5. Prove amplicon truth on a varied matrix: forward/reverse strand, multi-copy
   loci, pseudogene-prone genes, a pair with a known off-target amplicon, one
   with none.
6. Wire dbSNP primer masking end to end — the module and the 29.5 GB source are
   both already present and mounted.

Keep Route B (`blastn`, public domain) recorded as the fallback. It has
standalone value: a licence-free engine can never be re-blocked by a terms
change.

## Phase 3 — predictor wiring, smallest-first

The seams already exist — `services/predictor_runtime.py`,
`alphamissense_local.py`, `capice.py`, `ci_spliceai.py`, `esm1b_local.py` — and
Lane R already gives each predictor independent applicability, execution state,
algorithm/version, and calibration. So this is materialization plus wiring, not
new architecture.

Per predictor, the same wiring checklist:

1. Terms accepted and recorded (Phase 1).
2. Offline build of a **bounded MANE-scoped slice** with checksums and a tracked
   manifest; never a startup or request-time download.
3. Upload to the `eamos-source-assets` bucket, then a syd2 runtime-tree pull —
   the established offline → bucket → disk path.
4. Register in the capability registry with licence row, SBOM, size, and an
   executed functional probe. File presence alone is not readiness.
5. Predictor returns real scores, or a typed unavailable with exact
   requirements — never a fixture, never a heuristic wearing the method's name.
6. `/report` §2 renders it with algorithm, version, calibration, and source
   release visible.

Order: **REVEL** (~2 GB) → **ESM-1b** (~2-4 GB, builder already exists) →
**PrimateAI-3D** (~10 GB) → **SpliceAI** (~20 GB, sliced) → **CADD** (~30 GB,
sliced, and only after a disk decision). **Pangolin** needs its source decided
before it can be sized at all.

Stop after each one and confirm the disk headroom before starting the next.

## Phase 4 — disease and panel truth

1. On the OMIM grant: wire `omim_mim2gene`, then reconsider InterVar, which was
   only ever blocked on the OMIM half plus ANNOVAR's non-profit terms.
2. **PanelApp:** research non-profit use plausibly qualifies, but the separate
   restriction on downstream use of PanelApp *outputs* is untouched by the
   determination. Confirm with Genomics England before enabling, keep it
   launch-gated until then, and never attach its labels to the CC0/custom
   catalog. This is the one row where the earlier caution fully survives.

## Phase 5 — finish Wave 3's own scope

1. Write the 6 missing builders. `eamos_grch38_runtime_build` first — Route B
   needs its FASTA, and W3-REF-01 is the largest remaining genuine acquisition.
2. Execute the reconciled card set: 1,145,215,654 B (1.066 GiB), not 1.673 GiB.
   W3-AM-01 is already materialized and needs verify-and-wire only; W3-MANE-01
   needs its summary file, not its GFF.
3. Keep every deferred/NO-GO item that did **not** clear: the ~62 GiB CRISPR
   off-target index (size), rs3 (`scikit-learn<=1.0.2` incompatibility),
   crisprScore (runtime footprint), TIDE (no truth set), OCR, VEP cache (size),
   CRISPOR web (egress/consent). None of these was ever a commercial block.

## Phase 6 — Wave 4 surface truth, continued

1. **Owed first:** browser evidence for PR #31's panel loading/unavailable
   states. The lane cannot close without it.
2. Remaining fallbacks located: `useReportClient`'s `?fixture=rpe65-negative`
   (already gated — needs a visible-label check), `CompareClient`'s
   `sample-vcf`, and the workbench sample modules.
3. As Phase 3 lands predictors, surface them honestly — a newly-live predictor
   must be visibly distinguishable from one that is unavailable or
   not-applicable.

## Phase 7 — ratchets, then the deployment gate

Wave 5 (`agent/live/product-ratchets-v2`) and the approved deployment gate are
unchanged from the campaign plan. Deployment stays its own founder gate with the
exact environment/provider/material diff, rollback, and smoke matrix.

**Deployment is independently blocked right now, and not by us.** Swordfish
reported on 2026-07-25 that GitHub Actions is under a billing block until the
monthly refresh: no new image builds, therefore **no new Eamos deploys**. The
live image stays digest-frozen at `@sha256:910dc159…`. Anything in the phases
above that would need a fresh backend image — new pinned binaries such as
`isPcr` or `bcftools`, new Python dependencies — lands in the repo and the asset
store but **cannot reach production until that clears.** Plan the work to be
merge-ready and asset-ready, and treat the deploy as a separate later step
rather than the end of a phase. Runtime-tree assets that need no image change
are unaffected.

## Guardrails that still apply

- No download, build, materialization, upload, mount, provider flip,
  environment change, cloud mutation, or deployment until Steven names exact
  card IDs. The determination clears *licences*, not the action gates.
- syd2 is the sole serving path; Render is cancelled and the rollback path is
  gone by design. Treat production asset writes and any disk resize as their own
  named gates.
- A determination is not an acceptance record, and file presence is not
  readiness. Both need executed evidence.
- Never stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

Box conventions confirmed by swordfish 2026-07-25 that this plan must respect:

- **Steven cannot copy text out of any agent terminal.** Never hand him a resume
  prompt or a multi-line command. Founder-typed input is **one short line**
  (`gogogo`); pre-stage everything else so his steps are paste/tap/click/spend
  only.
- **syd4 box actions:** run `~/work/swordfish/provisioning/checks/who-is-live.sh
  --gate` first, and kill processes **by PID from `pgrep -af`, never
  `pkill -f`** — other agents' dev servers share this box. syd4 takes a weekly
  unattended reboot at 18:30 UTC; after any reboot verify public routes from a
  different box.
- **syd2 is the only serving path** and Render is cancelled, so there is no
  rollback. Production asset writes and any disk resize are separately gated.
