# Free-access licence re-review

Status: determination recorded; no source acquired and no `license_status`
changed yet.

Raised: 2026-07-25 · Steven confirmed Eamos is **for research, free, and
non-profit**. That single statement answers both questions this document was
written to sort — the entity question (non-profit) and the use question
(research, not diagnostic) — so most of the queue below is now actionable rather
than merely arguable.

**Read the caveats before treating anything as cleared.** A determination is not
an acceptance record. Each item still needs its own terms accepted and a dated
basis written into `registry_records.py`, and two items need an actual
registration or agreement that no determination can substitute for. Also note
the constraint has moved: with licences resolved, **disk and object-store
allowance become the binding limit** — see
`plans/research-unblock-and-wiring/plan.md`.

## The rule this cannot break

Campaign release rule 4 already says it, and it stays true:

> Universal free access removes Eamos price tiers, **not** upstream licences,
> retention, consent, privacy, rate limits, attribution, or scientific
> validation.

`plans/live-product-completion/research.md` already applies that rule to
PanelApp in as many words: *"A free Eamos price does not itself satisfy those
terms."* This document does not overturn that. It sorts the parked items by
**which question actually decides them**, because they do not all turn on price:

- **Price-decided.** Terms turn on whether the service charges. Free access
  settles these.
- **Entity-decided.** Terms turn on whether the licensee is academic/non-profit
  versus for-profit. Dropping prices does **not** convert a registered
  for-profit entity into a non-profit — Eamos operates under an ABN. These need
  a statement of what the operating entity is, and often a direct ask upstream.
- **Use-decided.** Terms prohibit clinical/diagnostic use, or restrict
  redistribution of outputs, **independent of price**. Free access is
  irrelevant to these.

**The use question is answered, and it was the sharper one.** Several of these
licences prohibit diagnostic or clinical use outright, independent of price.
Being free would not have satisfied them; being **research-use** does. This must
stay true in the product, not just on paper — if Eamos is ever positioned for
clinical or diagnostic use, every row resting on research use has to be
re-reviewed before that ships. Record it as a standing constraint, not a
one-time clearance.

## Queue

Registry statuses are the tracked source:
`app/backend/app/data_sources/registry_records.py`
(`commercial_license_review_required`, `restricted_unlicensed`).

### Cleared by the determination — needs terms acceptance, then wiring

Research + non-profit + non-diagnostic satisfies the conventional academic tier
for all of these. Each still needs its own terms accepted and recorded; sizes
are the registry's own estimates and drive the order (see the wiring plan).

| Item | Registry status | Size | Remaining action |
| --- | --- | --- | --- |
| **UCSC isPcr** (+ already-mounted `hg38.2bit`) | Wave 3 NO-GO | binary only | Accept UCSC terms for non-profit research use, record the basis, drop the binary in. **Zero code — unblocks the primer engine** (`plans/primer-specificity-engine/plan.md`). Do this first: highest value, smallest footprint. |
| `zenodo_revel_scores` | `restricted_unlicensed` | ~2 GB | Accept, record, materialize. Cheapest real predictor win. |
| `esm1b_hg38_assembled_scores` | `commercial_license_review_required` | ~2-4 GB | Accept; MANE-Select assembled table already the intended shape, and `eamos_esm1b_mane_context_build` exists. |
| `illumina_primateai3d_scores` | `restricted_unlicensed` | ~10 GB | Accept Illumina academic terms; confirm the research-use clause explicitly. |
| `illumina_spliceai_precomputed_hg38` | `restricted_unlicensed` | ~20 GB | Same. Needs a bounded slice — see the disk constraint. |
| `uw_cadd_scores_hg38` | `restricted_unlicensed` | ~30 GB | Free for non-commercial. Largest single item; bounded slice effectively mandatory. |
| `pangolin_splice_effect_scores` | `commercial_license_review_required` | undecided | Re-read current upstream terms and pick a model/cache source before sizing. |

### Needs a registration or agreement the determination cannot substitute for

| Item | Registry status | Remaining action |
| --- | --- | --- |
| `omim_mim2gene`, `omim_licensed_api` | `commercial_license_review_required` | OMIM grants free academic/research access but **only via an explicit registered agreement**. Research non-profit status makes the application straightforward rather than automatic. Apply, then record the grant. Unblocks disease-gene curation and the OMIM half of InterVar. |
| `intervar_pipeline_config` | `commercial_license_review_required` | Chained to ANNOVAR **and** OMIM. ANNOVAR is free for non-profit academic use, so that half clears on the determination; this stays blocked until the OMIM registration lands. |
| `interproscan_optional_licensed_apps` | `commercial_license_review_required` | Per member-database terms, not one licence. Most licensed member apps are academic-free, but each decides separately — enumerate them rather than clearing as a block. |
| **Genomics England PanelApp** | Lane B launch-gated | Prohibits commercial **and diagnostic** use without agreement; research non-profit use plausibly qualifies now. The separate restriction on downstream use of PanelApp *outputs* is unaffected by the determination, so its labels still may never be attached to the CC0/custom catalog. Confirm with GEL before enabling; keep launch-gated until then. |

### Unaffected — these were never commercial blocks

Recorded so nobody re-litigates them under this banner:

| Item | Actual blocker |
| --- | --- |
| GRCh38 SpCas9 off-target index | Size/cost: ~62 GiB artifact, ≥130 GiB build headroom |
| rs3 0.0.18 | Technical: pins `scikit-learn<=1.0.2`, incompatible with Python 3.12 |
| R `crisprScore` | Runtime footprint and authority choice not frozen |
| TIDE/TIDER/Tracy | Scientific: no approved truth set for efficiency/fit claims |
| OCR | No exact engine card; Tesseract is Apache-2.0 anyway |
| Offline VEP cache | Size; VEP itself is Apache-2.0 |
| CRISPOR web | Network egress, retention, and consent — not licence |

## What to do next

Sequenced work is in `plans/research-unblock-and-wiring/plan.md`. In short:

1. **Accept and record terms per item**, cheapest-and-highest-value first: UCSC
   isPcr, then REVEL, then ESM-1b. Each gets a dated basis in
   `registry_records.py` — never a silent flip.
2. **Apply for OMIM academic access**, since it is a lead-time item and gates
   InterVar behind it.
3. **Respect the new binding constraint.** Licences no longer limit us; syd2 disk
   and the Supabase allowance do. CADD and SpliceAI need bounded MANE-scoped
   slices, not whole-genome materialization.
4. Re-check the registry's `commercial_allowed` / `restricted_unlicensed`
   vocabulary. It encodes a commercial assumption and now reads misleadingly for
   a research non-profit.

Standing constraint: rows cleared on **research use** are only valid while Eamos
is research-use. Positioning it for clinical or diagnostic use re-opens every one
of them.

No status in `registry_records.py` has been changed by this document. Moving one
is a reviewed slice with its own evidence, not a consequence of this review.
