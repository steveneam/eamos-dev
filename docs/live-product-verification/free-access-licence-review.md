# Free-access licence re-review

Status: review queue; no licence determination made, no source acquired.

Raised: 2026-07-25 · Steven confirmed Eamos is **free access, no longer
commercial**. Every capability previously parked on commercial grounds is
re-listed here for re-review.

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

**The sharpest risk is use-decided, not commercial.** Eamos is a variant
interpretation surface, and several of these licences prohibit diagnostic or
clinical use outright. Being free does not make Eamos non-diagnostic. Any item
below marked use-decided needs that question answered before its licence status
moves, and answering it may be harder than the commercial one ever was.

## Queue

Registry statuses are the tracked source:
`app/backend/app/data_sources/registry_records.py`
(`commercial_license_review_required`, `restricted_unlicensed`).

### Likely unblocked — re-review first

These are conventionally free for academic/non-commercial use, which a free,
non-revenue Eamos plausibly satisfies once the operating entity is stated.

| Item | Registry status | Deciding question |
| --- | --- | --- |
| **UCSC isPcr** (+ already-mounted `hg38.2bit`) | Wave 3 NO-GO | Entity. Free for academic/non-profit/personal; ask UCSC directly whether a free, non-revenue, non-diagnostic service qualifies. **Unblocks the primer engine — see `plans/primer-specificity-engine/plan.md`.** |
| `uw_cadd_scores_hg38` | `restricted_unlicensed` | Entity. CADD is free for non-commercial use, licensed via UW otherwise. |
| `zenodo_revel_scores` | `restricted_unlicensed` | Entity. REVEL is free for academic/non-commercial use. |
| `esm1b_hg38_assembled_scores` | `commercial_license_review_required` | Entity. Model code is MIT; the precomputed score archive is the non-commercial part. Registry already records it as `noncommercial…internal-only`. |
| `illumina_primateai3d_scores` | `restricted_unlicensed` | Entity + use. Illumina non-commercial research licence; check the diagnostic-use clause. |
| `illumina_spliceai_precomputed_hg38` | `restricted_unlicensed` | Entity + use. Same shape as PrimateAI-3D. |
| `pangolin_splice_effect_scores` | `commercial_license_review_required` | Entity. Re-read the current upstream terms; the parked note predates this review. |

### Needs its own agreement regardless of price

| Item | Registry status | Why free access is not enough |
| --- | --- | --- |
| `omim_mim2gene`, `omim_licensed_api` | `commercial_license_review_required` | OMIM requires an explicit registered agreement even for non-commercial use. Free access does not self-serve it. |
| `intervar_pipeline_config` | `commercial_license_review_required` | Chained to ANNOVAR **and** OMIM rights. The ANNOVAR half may relax on entity; the OMIM half does not. |
| `interproscan_optional_licensed_apps` | `commercial_license_review_required` | Per member-database terms, not one licence; each licensed analysis app decides separately. |
| **Genomics England PanelApp** | Lane B launch-gated | Use-decided. Prohibits commercial **and diagnostic** use without agreement and restricts downstream use of PanelApp outputs. Already recorded as not satisfied by a free price. Stays gated. |

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

1. **State the operating entity.** Almost every entity-decided row above turns
   on this one sentence, and no agent can answer it. Steven's input.
2. **Answer the diagnostic-use question once,** in writing, and reuse it. It
   gates more than the commercial question does.
3. **Then re-review the "likely unblocked" rows in order,** starting with UCSC
   isPcr because it unblocks a named product need. Each row that moves gets its
   registry `license_status` updated with the dated basis for the change —
   never a silent flip.
4. Re-check the registry's `commercial_allowed` posture vocabulary. It was
   chosen under a commercial assumption and may now label things misleadingly.

No status in `registry_records.py` has been changed by this document. Moving one
is a reviewed slice with its own evidence, not a consequence of this review.
