# Primer specificity engine — next-session plan

Status: proposed; not started.

Stamped: 2026-07-25 05:48 +0000 · Claude.

Canonical inputs:

- `plans/live-product-completion/{research,spec,plan}.md` (Lane W required item 2)
- `docs/live-product-verification/wave3-approval-cards.md` (+ its 2026-07-25 reconciliation)
- `app/backend/app/runtime-tree-manifest-syd2.json` (what is actually mounted)

## Why this is the headline

Steven called it directly on 2026-07-25: **we need a primer engine.** The
finding that makes it worth a plan rather than a ticket is that we very nearly
have one already.

## What already exists — verified, not assumed

Read before planning any build. All of this is merged and on `main`:

| Piece | State | Where |
| --- | --- | --- |
| Design + thermodynamics | **ready** — Primer3 2.3.0, pinned, in the capability registry | `primer3-py==2.3.0`, `app/capabilities/composition.py` |
| Template-only specificity | **ready**, and the default | `TemplateAmpliconSpecificityProvider` |
| Whole-genome specificity seam | **coded**: provider, timeout, failure, human/hg38 guards | `LocalIsPcrSpecificityProvider` in `services/workbench_design_primer.py` |
| Honest scope disclosure | **coded** — emits `specificity_scope:verified_template_only` vs `specificity_scope:whole_genome_hg38_ispcr` | `services/workbench_design_runtime.py:162-167` |
| SNP masking | **coded** | `services/workbench_design_primer_snp.py` |
| dbSNP source | **mounted**, 29,552,227,779 B + tabix index | syd2 runtime tree |
| `hg38.2bit` reference | **mounted**, 835,393,456 B, at exactly the configured `bio_assets/genomes/hg38.2bit` | syd2 runtime tree |
| Readiness preflight | **coded** — checks binary + reference, reports `ucsc_ispcr_ready` / `ucsc_ispcr_unavailable` | `cli/eamos_workbench_preflight.py:448-480` |

**The only missing artifact in the entire whole-genome path is the `isPcr`
binary** at `bio_assets/bin/isPcr`. Nothing else is absent, and no code is
waiting to be written for the isPcr route.

## The actual blocker is a licence question, not engineering

UCSC's BLAT/isPcr is free for academic, non-profit, and personal use and
requires a paid licence for commercial use.

**Steven confirmed on 2026-07-25 that Eamos is free access and no longer
commercial**, which changes this from a spend decision into a question worth
simply asking. An earlier draft of this plan asserted Eamos was commercial on
the strength of `/pricing` and an ABN; that was stale.

Be careful how far that goes. Release rule 4 holds: free access removes Eamos
price tiers, not upstream licences. UCSC's terms are **entity-decided** — they
turn on whether the licensee is academic/non-profit rather than on whether the
service charges — and dropping prices does not convert a registered entity into
a non-profit. So this is now a short, cheap question to UCSC, not a settled
"yes". The wider sweep of everything else parked on commercial grounds is in
`docs/live-product-verification/free-access-licence-review.md`.

Note the Wave 3 packet marks "UCSC isPcr + `hg38.2bit`" NO-GO as one row. That
row conflates two things and should be split: `hg38.2bit` is *already* mounted
and approved as `public_allowed_after_terms_review`. Only the binary is gated.

### Two routes — ask about A first, keep B as the certain path

**Route A — confirm isPcr entitlement under free access.** Fastest to working
software by far: drop the binary in, flip `primer_specificity_provider`,
preflight goes green. **Zero new code.** Under free, non-revenue,
non-diagnostic operation this may simply be permitted. Ask UCSC directly, with
the operating entity stated; do not self-certify and do not assume a price.

**Route B — `blastn`, public domain.** NCBI BLAST+ is a US Government work,
free for any use including commercial, and is what Primer-BLAST itself runs on.
No entitlement question exists to answer, so this route cannot be blocked. It
is an additive sibling to `LocalIsPcrSpecificityProvider` against the provider
protocol that already exists — not a rewrite.

Its one real cost: `blastn` needs a FASTA-derived BLAST database, and the tree
has `hg38.2bit`, not FASTA. That makes **W3-REF-01's GRCh38.p14 FASTA
load-bearing** — which also answers the open question in the cards
reconciliation about whether a second reference representation is wanted. It
is, if we take Route B.

**Recommendation:** ask about A, because a yes costs nothing and needs no code.
Build B if the answer is no or slow — and note B has standalone value, since a
licence-free specificity engine can never be re-blocked by a terms change.

## Plan

### Phase 0 — settle the route (founder gate, non-blocking)

1. **State the operating entity** — the one input no agent can supply, and the
   thing every entity-decided licence turns on.
2. **Ask UCSC** whether isPcr use is permitted for a free, non-revenue,
   non-diagnostic service run by that entity. A yes makes Route A immediate and
   free.
3. If the answer is no, slow, or conditional, build Route B.

This phase does not block Phase 1, and the same two answers unblock most of
`docs/live-product-verification/free-access-licence-review.md`, so it is worth
asking once and reusing.

### Phase 1 — ungated work, start immediately

No approval needed for any of this; it is code and already-mounted data.

1. **Wire dbSNP primer masking end to end.** The masking module and the dbSNP
   source both exist and are mounted; prove the path with tests over the shared
   variant matrix, and make an unmasked design say so rather than imply a
   masked one.
2. **Split the isPcr NO-GO row** in the cards doc into `hg38.2bit` (mounted,
   approved) and `isPcr binary` (entitlement pending), and re-review the other
   commercially-parked capabilities per
   `docs/live-product-verification/free-access-licence-review.md`. Several
   predictors Lane R currently returns as unavailable — CADD, REVEL, ESM-1b,
   SpliceAI, PrimateAI-3D — are entity-decided and may move on the same answer.
3. **Rescope W3-AM-01 and W3-MANE-01** per the reconciliation — AlphaMissense
   needs verify-and-wire, not a 613 MiB re-download.
4. **Write the missing builders** (6 of 8; ungated). Priority order for this
   lane: `eamos_grch38_runtime_build` first, because Route B needs its FASTA.
5. **Prove the honest-disclosure path in tests** — a template-only result must
   be indistinguishable from a whole-genome result *only* in that it says which
   it is. This is the release-rule-1 guarantee for primers.

### Phase 2 — implement the chosen provider

**If Route B:** add `BlastnSpecificityProvider` against the existing
`PrimerSpecificityProvider` protocol — pinned BLAST+, fixed argv, bounded
subprocess, no shell, no user paths, typed unavailable when the DB is absent.
Reuse the isPcr provider's timeout/failure/guard shape; it is already correct.
Then extend the preflight the same way, add a `blastn` capability-registry row
with its public-domain licence, and build the BLAST DB offline from W3-REF-01.

**If Route A:** obtain the binary under licence, record it as a Wave 3 card
with entitlement reference, checksum, SBOM row, and a functional probe. No app
code changes.

Either way, finish by proving amplicon truth on a deliberately varied matrix:
forward/reverse strand, multi-copy loci, pseudogene-prone genes, a primer pair
with a known off-target amplicon, and one with none.

### Phase 3 — surface it (folds into Wave 4)

Render measured Tm/structure/specificity honestly, and make template-only vs
whole-genome visible rather than buried. This is Wave 4 task 3 and belongs to
that lane, not this one.

## Rest of the next session, in order

1. Merge PR #31 (Wave 4 panel fixture fallback) and PR #32 (Wave 3 asset
   correction) if not already merged — both green at wrap.
2. **Owed from this session:** browser evidence for the panel
   loading/unavailable states in PR #31. Not captured; the lane cannot close
   without it.
3. Primer Phase 1 above.
4. Continue Wave 4 slices: `useReportClient`'s `?fixture=rpe65-negative` label
   check, `CompareClient`'s `sample-vcf`, and the workbench sample modules.

## Guardrails that still apply

- No download, build, materialization, upload, mount, provider flip,
  environment change, cloud mutation, or deployment until Steven names exact
  card IDs.
- syd2 is the sole serving path; Render is cancelled and the rollback path is
  gone by design. Treat production asset writes as their own named gate.
- Never stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.
