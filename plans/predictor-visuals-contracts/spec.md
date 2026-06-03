# Predictor-Visuals FE↔Backend Data Contracts

> **Coordination artifact (Claude FE → Codex backend), authored for the backend-heavy build cycle.**
> The next-gen predictor build set (vault `build-ledger` §2 / ADR 0009) is ~90% backend. Three of
> its signature **frontend visuals** are blocked only on backend *serialization* decisions, not on
> the engines themselves. This file pins the three contracts so Codex can emit them as he builds the
> engines, and so the FE can scaffold against a fixture in parallel.
>
> Source specs (vault `EAMOS Web Tool/Wiki/`):
> `product/predictor-visuals-build-spec.md` · `syntheses/predictor-build-roadmap.md` (§2/§4) ·
> `sources/spliceai-revel-backend-implementation.md` (SAI-10k) · `sources/gene-viewer-backend-spec.md`.
> As-built code refs: `app/web/lib/backend.ts`, `app/web/components/report/ReportClient.tsx`.

## Why this exists

Every committed predictor produces a *score*; EAMOS's wedge is **drawing and explaining** what
Varsome/Franklin only score. The drawing is the FE lane. But the FE can only draw what the backend
serializes. Of the three Tier-2/3 visuals:

- **3D structure (AlphaFold + PDBe-Molstar) — DROPPED 2026-06-03** (Steven). Tier-3, deferred anyway;
  no backend/adapter integration. Not in this contract set.
- **Splice-outcome SVG** — contract does **not** exist yet (net-new both sides). ← Contract 1.
- **Nightingale §4 protein-domain track** — contract **already exists** in `backend.ts`
  (`ProteinDomainTrack`); open item is which source populates it + when real data lands. ← Contract 2.
- **Per-gene confidence badge** — needs one new field on the in-silico block. ← Contract 3.

---

## Contract 1 — `splice_outcome` (Splice-Outcome SVG · report §2 In-silico)

**Status:** net-new on both sides. `splicing_summary` / `splice_outcome` do **not** appear in
`backend.ts` today. FE blocked until serialized.

**FE consumes (proposed shape — Codex owns the exact attachment point):**

```ts
interface SpliceOutcome {
  aberration:
    | 'pseudoexon' | 'partial_intron_retention' | 'partial_exon_deletion'
    | 'exon_skipping' | 'multi_exon_skipping' | 'whole_intron_retention' | 'normal'
  max_delta: number                       // max(DS_AG,DS_AL,DS_DG,DS_DL) — already computed
  affected_feature: { kind: 'exon' | 'intron'; rank: number; transcript_start: number; transcript_end: number }
  size_bp: number
  size_direction: 'inserted' | 'deleted'
  reading_frame: 'in_frame' | 'frameshift'
  ptc: { introduced: boolean; nmd_predicted: boolean } | null
  pvs1_strength?: 'VeryStrong' | 'Strong' | 'Moderate' | 'Supporting' | 'pending'
  low_confidence?: boolean                // SAI-10k's 3 unresolvable combos → dominant call + dashed render
  source: { name: 'CI-SpliceAI → SAI-10k-calc'; release: string; url?: string }
}
```

**Codex owns / decides:**
1. **Attachment point.** Proposed `report_payload.splicing_summary.splice_outcome`. If splice data
   already rides inside `computational_deep_dive.predictors[spliceai]`, attaching there is fine —
   tell the FE which, and add the field to the `backend.ts` contract.
2. **[GAP] SAI-10k fidelity (gates correctness).** Confirm the backend serializes SAI-10k's
   altered-AA length → `size_bp` and its frame call → `reading_frame` **exactly** (flagged in
   `spliceai-revel-backend-implementation`). For the 3 unresolvable SAI-10k combos, emit the
   dominant call + `low_confidence: true`.
3. PVS1 strength is optional here — if the PVS1 module isn't wired yet, omit or send `'pending'`.

**FE delivers once contract lands:** hand-rolled inline SVG (no library) — two stacked rows (reference
exons + aberrant transcript) + reading-frame ribbon + NMD chip + source stamp; Reading-Room tokens;
a11y (`role=group`, `<title>`/`<desc>`, never colour-only); reduced-motion safe. **No new compute.**

---

## Contract 2 — Protein-domain track source (Nightingale · report §4 Gene & locus)

**Status:** contract **already exists** in `backend.ts` — `ProteinDomainTrack` /
`ProteinDomainTrackFeature` / `ProteinTrackVariantMarker` (lines ~1539–1599), reachable today at
`ProteinFeatures.domain_track`. The §4 slot in `ReportClient.tsx` (~line 785) is a live placeholder
("Protein-domain viewer wiring in progress"). The Protein-Annotation tool that fills it is **gated on
the persistent-disk runtime** (`current-state`: `PROTEIN_ANNOTATION_ENABLED=false` until a POSIX disk
exists; ADR 0010 is the fix).

**Codex owns / decides:**
1. **[GAP] Canonical domain source** (vault `gene-viewer-backend-spec`): which of InterPro / Pfam /
   UniProt populates `feature.source`, and is the `ProteinDomainFeatureKind` enum (domain/site/motif/
   repeat/region/family/epitope/coiled_coil/low_complexity/signal_peptide/transmembrane/
   topological_domain) **frozen**? The FE glyph map keys on `source` + `kind`, so it tolerates the
   open decision — but the FE needs the enum frozen and the set of real `source` strings that appear.
2. **When does real `domain_track` data land?** It's downstream of the persistent-disk gate. Until
   then the FE scaffolds the Nightingale track against a fixture (e.g. RPE65/Q16518) and reads
   `status: 'unavailable'` / `fail_closed_reason` to keep the honest placeholder.

**FE delivers (can scaffold now against fixture):** `@nightingale-elements/nightingale-track` 5.6.0
(MIT) parallel-track layout (domains + ClinVar variants + queried lollipop on one axis); glyph+palette
per `workbench-protein-domain-design` V2 pastel; resolve Reading-Room token → computed hex once and
pass across the shadow boundary; `<details>` data-table a11y fallback. Wires to live data the moment
`status: 'available'`.

---

## Contract 3 — Per-gene calibration tier (Confidence badge · report §2)

**Status:** net-new field. The honest "we're poorly calibrated for *this* gene" badge
(`predictor-build-roadmap` Tier-2) needs a per-gene calibration tier the FE can render.

**FE consumes (proposed — attach on the computational/in-silico block):**

```ts
interface PredictorCalibrationConfidence {
  gene_tier: 'high' | 'moderate' | 'low' | 'insufficient_data'
  path_truth_n: number                    // ClinVar P/LP truth count for this gene
  benign_truth_n: number                  // ClinVar B/LB truth count
  agreement: 'concordant' | 'split'       // do the active predictors agree?
  source: { name: string; release: string }   // e.g. Bergquist-2025 / acmgscaler
}
```

**Codex owns / decides:** the tier rule (acmgscaler-style ≥10 path + ≥10 benign → calibrated) and the
attachment point; whether it rides `computational_deep_dive` or a new sibling.

**FE delivers:** a small badge chip beside the §2 verdict — High/Moderate/Low/"insufficient data for
this gene" + an agreement/disagreement indicator + source stamp. Pure render.

---

## What the FE can do **without** waiting

- **Scaffold Contract 2's Nightingale track** against a fixture (contract already typed).
- **Draft the SVG/badge components** behind the `?`-optional fields so they no-op until data arrives
  (graceful-degrade is the existing report pattern — see `populationTarget?.match_level`).
- Everything else is gated on the three decisions above.

## Handshake / acceptance

- [ ] Codex confirms Contract 1 attachment point + adds `SpliceOutcome` to `backend.ts`; resolves the
      SAI-10k fidelity [GAP].
- [ ] Codex confirms Contract 2 canonical `source` + freezes the `kind` enum + signals when real
      `domain_track` data is disk-backed.
- [ ] Codex confirms Contract 3 field shape + attachment point.
- [ ] Codex defines the **functional-evidence states** + **ACMG point-breakdown** contracts (added to
      the seam list per the 2026-06-03 Codex note below).
- [ ] FE builds each visual against the confirmed contract, browser-verified on the USH2A demo +
      a domain-bearing gene (RPE65), Reading-Room + a11y + reduced-motion per `design-invariants`.

## Codex coordination (2026-06-03)

Codex's reply after reading the vault confirms this contracts-first sequencing:

> "Claude should stay on frontend-owned work until backend contracts are stable: report loading state
> changes currently in the worktree, Gene Viewer mobile/full-gene overflow, and later predictor
> visuals. Backend should hand Claude explicit response contracts for splice visuals, protein/domain
> tracks, functional evidence states, and ACMG point breakdowns before UI buildout."

**Net:** backend-led contracts (matches the agent protocol). Two seams to add to this set as Codex
serializes them — they belong in the same handshake even though they're not "visuals":

- **Functional-evidence states** — the Lab & Functional card's dual-badge state machine (curator
  verdict + Eamos 3-stream count; 6 states incl. the NEW uncurated/`info_blue`). Backend slice already
  shipped (uncommitted, per `current-state`); FE was already queued as Claude's next functional-card
  task. Codex to confirm the final state enum + conflict rule in `backend.ts`.
- **ACMG point breakdown** — the EAMOS points-based classifier's per-criterion audit
  (`eamos-acmg-classifier-tool` / ADR 0011): the point value + firing criteria behind the advisory
  verdict, so the FE can render an auditable breakdown rather than a black-box score.

**FE-owned, contract-stable work Claude does meanwhile** (no backend dependency): the report loading
state (in worktree), Gene Viewer mobile/full-gene overflow, and **report export** (`report-export.ts`
+ `ExportMenu` — consumes the existing `ReportPayload`, zero new contract).

---
*Authored 2026-06-03 by Claude (FE lane). Pairs with the vault `predictor-visuals-build-spec`
(implementation detail) — this file is the **contract handshake** Codex serializes against. No code
shipped by this file; it unblocks the §2/§4 visuals in the build-ledger §2 backlog.*
