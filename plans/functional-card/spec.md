# Lab & Functional Literature card (Report Card 3) — spec

**Status:** product spec (Claude, 2026-06-01) — for Codex backend + Claude frontend.
**Origin:** Steven's two source docs (on Desktop, outside the repo) —
*"Functional Card Display Logic & UI Layout Spec"* + *"Gene Functional Literature
Extraction"* — plus Steven's 2026-06-01 clarifications and the 5 approved
optimizations below. Those Desktop files are the upstream; this is the in-repo
authoritative version.

## 1. Core principle — separate the verdict from the volume

The card answers three questions at a glance, kept **strictly separate**:
- **What** is the wet-lab finding? → plain-language **primary label**.
- **How strong** is the ACMG functional code? → **verdict badge** (the *curator's*
  PS3/BS3) — never derived by Eamos from literature.
- **How much** functional work exists? → **volume badge** (Eamos's deduplicated
  multi-stream study count).

The verdict is **curator-sourced** (ClinGen first, ClinVar second). The count is
**Eamos-aggregated**. The count must NEVER be converted into the verdict, and the
card colour tracks the **functional state**, not the overall ClinGen
pathogenicity (that lives on the Clinical Consensus card).

## 2. State matrix (with the 5 approved optimizations)

| State | Primary label | Verdict badge | Volume badge | Colour |
| --- | --- | --- | --- | --- |
| Strong deficit | Functional Deficit | `PS3_Strong` · *via ClinGen* | `10 studies` | Red (`danger_red_state`) |
| Emerging deficit | Functional Deficit | `PS3_Supporting` · *via ClinVar* | `2 studies` | Soft red |
| Normal | Normal Function | `BS3` · *via ClinGen* | `4 studies` | Green (`safe_green_state`) |
| **Conflict** | Conflicting Functional Data | `Review Required` | `5 studies · 3 deficit / 2 normal` | Yellow (`caution_*`) |
| **Uncurated** (new) | Functional Work Found · Not ACMG-graded | `No code asserted` | `6 studies` | Blue/neutral (new `info_*` token) |
| None | No Functional Data Available | `None` | `0 studies` | Grey (`neutral_slate_state`) |

The 5 optimizations (all approved 2026-06-01):
1. **Source attribution** — the verdict badge carries `via ClinGen` / `via
   ClinVar` (+ `via ClinGen + ClinVar` when both agree). Authority of a `PS3`
   depends entirely on whether a VCEP or a lone submitter asserted it.
2. **Conflict shows the split** — `5 studies · 3 deficit / 2 normal`, not a bare
   "Review Required". Turns a dead-end into triage (critical for reduced-
   penetrance hypomorphs like USH2A C759F).
3. **New "Uncurated" state** — studies exist but neither ClinGen nor ClinVar
   graded them. Avoids the "No Data" lie when papers sit below the fold. Visually
   distinct from the empty grey "None".
4. **Strength from the curator, not the count** — `PS3_Strong` vs
   `PS3_Supporting` comes from the curator's asserted strength, never from the
   study-count tier. The count is a pure volume badge. (A VCEP can award
   `PS3_Strong` on one definitive assay.)
5. **Count is the hook to the evidence** — tapping the volume badge opens the
   below-the-fold deduplicated PMID table; when the count dwarfs the curator's
   cited papers, a micro-note ("code rests on 2 of 10 studies") surfaces the
   "is this code under-weighted?" insight.

## 3. Verdict resolution (curator-only, ClinGen-priority)

```
clingen_code = ClinGen VCEP functional code (PS3*/BS3) | None        # priority
clinvar_code = ClinVar functional code (PS3*/BS3 from verified assay submissions) | None
direction(code): PS3* -> "deficit", BS3 -> "normal"

if clingen_code and clinvar_code:
    if direction(clingen) == direction(clinvar): verdict = clingen_code; source = "ClinGen + ClinVar"
    else:                                        state  = CONFLICT  (split from the two sources, + per-paper if available)
elif clingen_code:                               verdict = clingen_code; source = "ClinGen"
elif clinvar_code:                               verdict = clinvar_code; source = "ClinVar"
else:  # no curator functional code
    if count == 0:                               state = NONE
    elif literature_direction_splits:            state = CONFLICT      # papers disagree deficit vs normal
    else:                                        state = UNCURATED     # studies exist, none graded
```

- **Eamos never assigns PS3/BS3 itself.** "Conflict" and "Uncurated" are *not*
  classifications — they are honest statements that the functional evidence does
  not converge / has not been graded. That is allowed; asserting a PS3/BS3 from
  Eamos's own reading is not.
- **Conflict split sourcing (optimization 2) is phased.** v1: source-level
  disagreement (ClinGen `PS3` vs ClinVar `BS3`). v2: per-paper functional-
  direction extraction yields the `N deficit / M normal` counts. Until v2, show
  the conflict + the source-level reason; do not fabricate a numeric split.

## 4. Volume count — the parallel aggregator (Eamos)

Per the *Gene Functional Literature Extraction* doc — a **parallel** aggregator,
NOT stop-at-first-match (ClinGen often cites 1–2 papers and undercounts global
work). Three streams merged into one deduplicated PMID set:
- **Stream 1 — ClinGen:** PMIDs from the variant's PS3/BS3 `evidence_pmids`.
- **Stream 2 — ClinVar:** PMIDs from citation columns + 8-digit regex over the
  submission free-text.
- **Stream 3 — PubMed:** `"{GENE} AND {aa_change} AND (functional assay OR
  luciferase OR western blot OR activity OR expression OR patch-clamp)"`.

`count = |dedup(stream1 ∪ stream2 ∪ stream3)|`. The deduped PMID list feeds the
below-the-fold table. This reuses **EP-VLEx** machinery
(`publication_literature.py`) where possible — but with the functional-keyword
filter; it is the *functional* study counter, distinct from the general
publication inventory (EP-VLEx caveat: "not the functional evidence study
counter").

## 5. API payload (additive to the existing `FunctionalEvidenceDisplayMetrics`)

```jsonc
{
  "card_id": "card_3_functional",
  "display_metrics": {
    "state": "conflict",                 // strong_deficit|emerging_deficit|normal|conflict|uncurated|none
    "primary_label": "Conflicting Functional Data",
    "acmg_badge_text": "Review Required",// curator code or Review Required / No code asserted / None
    "verdict_source": "clingen_vs_clinvar", // clingen|clinvar|clingen+clinvar|conflict|uncurated|none
    "study_count_badge_text": "5 studies",
    "conflict_split": { "deficit": 3, "normal": 2 },   // null unless state==conflict & v2 available
    "code_rests_on": { "cited": 2, "total": 5 },        // null unless count >> curator-cited
    "ui_color_theme": "caution_yellow_state"
  },
  "underlying_data": {
    "total_unique_count": 5,
    "clingen_asserted_code": null,
    "clinvar_asserted_code": null,
    "deduplicated_pmid_list": ["...", "..."]
  }
}
```

New fields vs today's `display_metrics`: `state`, `verdict_source`,
`conflict_split`, `code_rests_on`. Existing `primary_label`, `acmg_badge_text`,
`study_count_badge_text`, `ui_color_theme` stay; `acmg_badge_text` must now be
curator-sourced.

## 6. What's already built vs. the deltas (corrected 2026-06-01)

**Already built in `app/backend/app/services/functional_evidence.py`** — verified
by reading `FunctionalEvidenceExtractor` (docstring: *"Count functional-study
PMIDs without assigning ACMG PS3/BS3 strength"*):
- Functional-keyword filter (`_FUNCTIONAL_SIGNAL_RE`) over PubMed title/abstract.
- PubMed hits added as **studies only** (`_collect_pubmed_articles` →
  `collector.add(source="pubmed", …)` with **no** `evidence_codes`/
  `asserted_codes`) — PubMed cannot move the verdict.
- PS3/BS3 codes come **only from ClinGen + ClinVar** (`_collect_clingen` /
  `_collect_clinvar`).
- **Dedup by PMID** across all three streams (`_FunctionalEvidenceCollector.
  by_pmid`); a paper in ClinGen *and* PubMed = one study, both tags.
- `source_breakdown` (clingen/clinvar/pubmed), `source_asserted_codes_by_source`,
  and `curator_cited_count` (the basis for `code_rests_on`).

So the count + curator-only verdict + dedup Steven asked for **already exist**.
(My earlier "the card self-classifies from literature" framing was a misread of
the live output + `_display_metrics` in isolation — corrected.)

**Delta status (2026-06-01):**
1. ✅ **`uncurated`** state — Codex shipped: "Functional Work Found - Not
   ACMG-graded" + `info_blue_state`, replacing the old `Functional Evidence
   Found` catch-all.
2. ✅ **`verdict_source`** — Codex shipped (`clingen` / `clinvar` /
   `clingen+clinvar` / `conflict` / `uncurated` / `none`).
3. ✅ **Conflict rule — CONFIRMED by Steven + shipped.** Conflict fires ONLY when
   ClinGen and ClinVar give *different* directions (or one source internally
   contradicts). **Single-source = that source's code** ("PS3 · via ClinVar";
   ClinVar is a valid standalone source). It is no longer the old "both PS3 and
   BS3 present" trigger.
4. ⏳ **Conflict split** (`N deficit / M normal`) — v2, needs per-paper direction;
   `conflict_split` is `null` in v1 (no fabrication).
5. ⏳ **Frontend** (Claude, next) — define `caution_yellow_state` +
   `info_blue_state` tokens; render dual-badge + `verdict_source` attribution +
   `uncurated` state + `code_rests_on`.

The verdict already does NOT derive from PubMed, so no "stop self-classifying"
rewrite was needed — only the display/state deltas above.

### Planned enhancement E1 — dedicated Stream-3 live PubMed functional query

**Current v1 (Codex):** Streams 1–2 (ClinGen, ClinVar) + the keyword filter are
live, but Stream 3 only re-filters PubMed articles **already** in the payload /
evidence map (the general publication pull). So the count is accurate but a
**floor** — functional-assay papers that rank low in the general query and never
get pulled are missed. This is a recall gap, not a correctness bug.

**E1 = fire Stream 3 as its own targeted query.** Entrez esearch:
`"{GENE} AND {aa_change} AND (functional assay OR luciferase OR western blot OR
activity OR expression OR patch-clamp OR splicing OR minigene OR enzyme activity OR
in vitro OR rescue)"`, feeding returned PMIDs into the same
`_FunctionalEvidenceCollector` (auto-deduped against Streams 1–2 by PMID).
Requirements: **bounded** result size (no unbounded sweep), **cached + provenance**,
**fail-closed**, `USE_REAL_APIS`-gated, and reuse EP-VLEx fetch plumbing.

**Dependency:** E1 needs the resolved **amino-acid change** for `{aa_change}`. USH2A
renders `protein_change` null today though `molecular_context` knows p.Cys759Phe
(the `protein_change_derivable_not_surfaced` gap, `eamos_press` spec §5i) — resolve
that first or the functional query loses its strongest term and falls back to gene
+ cDNA only.

Until E1 lands, the count stays an honest floor and the card is fully functional;
E1 raises recall, it does not change any state/verdict logic.

## 7. USH2A:c.2276G>T worked example

Steven's expectation: **Conflict**. The ClinGen Hearing-Loss VCEP did NOT assert
a functional PS3/BS3 (it scored the disulfide-bonding analysis as PP3), and
C759F is a reduced-penetrance hypomorph whose functional/phenotype literature
genuinely splits (syndromic Usher vs isolated RP vs tolerated in some
homozygotes). So the card should land on **Conflict** with the study count, once
the pipeline can see the discrepancy (curator-level and/or per-paper direction).
If v1 can only see "studies exist, no curator code," it lands on **Uncurated** —
and that gap (missing per-paper direction) is itself a finding the `eamos_press`
truth-printer must print, not paper over.

## 8. Verification hook

The `eamos_press` truth-printer (`plans/eamos-press-truth-printer/spec.md` §5a)
is the regression harness for this card: it asserts the verdict is
curator-sourced (`functional_verdict_not_curator_sourced` → contradicted if
Eamos self-derives), the count is the 3-stream deduped aggregate, and prints
which sources/papers drove the state for USH2A.
