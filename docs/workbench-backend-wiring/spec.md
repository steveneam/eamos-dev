# Workbench — backend sourcing / wiring requests (Codex CAR ledger)

**Purpose.** A single, living list of every Workbench FE surface that currently
runs on **mock / illustrative / FE-derived** data and needs Codex to source or
wire real backend data. Each item states: the FE state today, what is mocked,
the **contract Codex should add**, and the **FE swap-in** once it lands. This is
the cross-agent request (CAR) home for the Workbench tool work — read top-to-bottom
when Codex is back.

> Author: Claude (FE), 2026-06-10. Standing instruction from Steven: flag
> everything needing backend sourcing/wiring here so there is always a
> Codex-ready spec. Append new items; don't delete resolved ones — mark them
> ✅ DONE with the commit that wired them.

Status key: 🔴 not started · 🟡 partial (fields exist, values not populated) · ✅ done.

---

## 1. 🟡 Primer — secondary-structure thermodynamics

**FE today.** The Primer audit drawer ("Details") shows a **Secondary structure**
section: Self-complementarity (any), Self 3′ complementarity (end), Hairpin Tm,
and Pair 3′ dimer (`PrimerResultCard.tsx`). Values are **deterministic mock**
derived from a hash of each primer sequence — stable per sequence, in the ranges
Primer3 / Primer-BLAST report, and tagged *"illustrative — pending Primer3
thermodynamic alignment"* (`.eamos-mock`).

**Already in the contract.** `PrimerPair` (`lib/backend.ts:1203`) has
`secondary_structure_risk?` + `secondary_structure_notes?` — but **not** the
per-primer numeric scores the drawer renders.

**Codex CAR.** Populate the real Primer3 thermodynamic-alignment outputs and add
typed fields to `PrimerPair` (both `app/web` + `app/frontend` `backend.ts`
mirrors byte-identical):
- `self_any_forward` / `self_any_reverse` — `PRIMER_LEFT/RIGHT_SELF_ANY_TH`
- `self_end_forward` / `self_end_reverse` — `PRIMER_LEFT/RIGHT_SELF_END_TH`
- `hairpin_tm_forward` / `hairpin_tm_reverse` — `PRIMER_LEFT/RIGHT_HAIRPIN_TH` (°C; 0/none if below threshold)
- `pair_compl_end` — `PRIMER_PAIR_COMPL_END_TH` (the pair 3′ dimer)

**FE swap-in.** `PrimerResultCard` drops `mockStruct()` and reads these fields;
keeps the mock as the offline fallback and removes the `.eamos-mock` tag when the
real values are present. (Self-3′ and pair-3′ are the quality-critical ones —
they form primer-dimers; surface a warn state when high.)

---

## 2. 🔴 Primer — primer positions for the gene-view overlay (BLOCKS a requested feature)

**Requested feature (Steven 2026-06-10).** A per-pair checkbox in each Primer
result card that, when ticked, draws the forward + reverse primers as a
**directional (5′→3′) outline on the sequence viewer**, plus the amplicon span.

**Blocker.** `PrimerPair` carries **only the sequences** (no coordinates). The FE
cannot reliably place them on the viewer: the sequence window is a
**collapsed-intron** view around the variant, and a ~300–700 bp amplicon's
primers usually fall **outside** the displayed window — a naive `indexOf` search
would locate nothing (or the wrong copy). So the robust overlay is **backend-gated**.

**Codex CAR.** Add primer-placement + specificity fields to `PrimerPair` (both
mirrors identical), matching the **NCBI Primer-BLAST** output the lab workflow
uses (Steven 2026-06-10 confirmed the real format: per-primer Sequence · Template
strand · Length · Start · Stop · Tm · GC% · self-compl · self-3′, then "Products
on intended / unintended targets" with genomic coordinates):
- **Length** is now shown FE-side (`forward.length` / `reverse.length`) — no
  backend needed; remove from this list once you confirm it's the oligo length.
- **Template strand** `forward_strand` / `reverse_strand` (`Plus | Minus`; the FE
  defaults F=Plus / R=Minus — backend should confirm).
- **Template Start/Stop** — the primer's 1-based position on the resolved design
  template (Primer-BLAST "Start"/"Stop"; the reverse primer's Start > Stop).
- **Genomic Start/Stop** — GRCh38 chromosome coordinates (the Primer-BLAST
  "Template <start> … <stop>" line under "Products on intended targets").
- `amplicon_start` / `amplicon_end` (template + genomic) for the gene-view overlay
  (item #2 above — this is what unblocks the directional outline).
- **Products on intended / unintended targets** (richer specificity, later): the
  on-target amplicon (RPE65) + off-target amplicons on other chromosomes with
  mismatch positions — mirrors the CRISPR off-target screen. Today
  `specificity_hits` is only a count; a products list powers a full Primer-BLAST-
  style specificity panel.
- Workflow note: the lab runs Primer-BLAST against the **genome** DB (not RefSeq
  mRNA) over the gDNA region, ~500–1000 bp products, to flank the CRISPR/edit site.

**FE swap-in.** WorkbenchShell lifts a `selectedPrimerPair` state, threads a
select callback to `PrimerResultCard` (the checkbox) and the selection to
`SequenceViewerV2`; the viewer maps the positions onto its `.sv-base[data-idx]`
grid and renders the directional outline + amplicon bracket (same machinery as
the variant pin / selection band). **Until these land the checkbox stays
unbuilt** — see also [[on-map guide overlay]] for CRISPR which has the same need
(`CrisprGuide.cut_position` exists; primers need the analogous fields).

---

## 3. 🔴 CRISPR — ssODN genomic coordinate

**FE today.** `SsodnLabDonor` (the lab-order donor, now rendered **below** the
guide design) renders the variant in c. notation; it has a slot for the genomic
coordinate but the `/crispr/ssodn` response doesn't return one.

**Codex CAR.** Add a `variant_genomic` field to the `/crispr/ssodn` response
(Python schema + both `backend.ts` mirrors). Verified value for the demo:
**c.260 = chr1:68,444,869 (GRCh38, − strand)**. FE renders it once present.

---

## 4. 🔴 CRISPR — ssODN edit direction reconcile

The lab workbook donor is variant-**introducing** (knock-in, A>G) while
`docs/crispr-ssodn/spec.md` + the left-rail copy describe a **corrective** edit
(G>A). **Reconcile the backend `/crispr/ssodn` direction.** The FE labels the
edited codon neutrally ("edited codon / changed base"), so it is correct either
way — but the backend's emitted edit + HDR notes should match the intended
direction.

---

## 5. 🟡 Gene viewer + protein view — real annotation data (rework pending)

**Context.** Steven 2026-06-10: *don't over-invest in the gene/protein viewer —
it will be reworked once the backend is wired.* Logged here so the rework has the
FE's findings.

**Mocked / illustrative today** (gene minimap + protein view, `GeneMinimap.tsx`
/ `ProteinView.tsx`): per-exon ClinVar **density bubbles**, the protein
**domain/feature track** + **AlphaMissense per-residue heatmap**, the ClinVar
**lollipops** (sample-bounded, not gene-wide). These consume real fields when
populated (`exonVariantCount`, `proteinFeatures`, `clinvar`) and are tagged
illustrative until then.

**FE legibility findings to fix during the rework** (caught in a rendered-visual
sweep, not yet changed): minimap **exon fills are low-contrast** cream-on-warm-white
(`#e6dfca`/`#c9bf99`); ClinVar **density bubbles are amber @ 0.3 opacity** so the
two layers blur together; protein **lollipops + point-feature diamonds are
colour-only with no classification legend** (accessibility gap); lollipop **stems
are too faint** (`var(--line)`) to trace to a position. Address these when the
real data lands so the pass isn't done twice.

---

## Already real / not a CAR (for reference)

- CRISPR real-mode design is correctly gated to **local deterministic SpCas9**;
  SaCas9 / Cas12a are schema-only and the panel says so (`crispr-disclosure`).
- Primer specificity is **in-template UCSC isPcr opt-in** (M-002C gated) — the
  panel already discloses this is not an NCBI Primer-BLAST validation.
- The 3-column canvas, rail-foot account cluster, and pane persistence are pure
  FE (no backend dependency).
