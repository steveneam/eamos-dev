# Report v3 — Codex backend handoff (one-shot)

> FE for the `/report` v3 redesign is shipped (uncommitted, `app/web/**`). Every
> item below currently renders a **mock value + visible "needs live data"
> marker** (`.eamos-mock`) or an FE-derived stopgap; wiring these makes them
> live with no further FE change. **Any new field must be added to BOTH
> `app/web/lib/backend.ts` and `app/frontend/src/lib/backend.ts` byte-identical.**
> Codex also owns the Render SG redeploy + live-verify after wiring (standing rule).
> Not urgent — Codex is on the local-PubMed wiring; this is the next backend batch.

## A. Variant hero — details disclosure (FE rows exist, data missing)
The 2-column "Variant details" panel renders these rows; these are **null in the
RPE65 report payload today** so they show the ghost marker:
1. **`protein_change` (p.Asp87Gly)** — `report_profile.header.protein_change` AND
   `variant_summary_rows[0].protein_change` are both null for RPE65 c.260A>G.
   The protein change exists in the gene-viewer path but not the report payload.
   → populate `header.protein_change` (preferred) and/or the summary row.
2. **`exon`** — `molecular_context` evidence summary has no `exon` for this
   variant (the FE reads `summary.exon`, same place MolecularContextBlock reads).
   → populate `MolecularContextSection.exon` (e.g. "exon 4 / 14").
3. **rsID (dbSNP)** — not in the contract. Add `rsid?: string | null` to
   `VariantReportHeader` (and/or `VariantSummaryRow`).
4. **Ensembl transcript (ENST)** — not in the contract. Add
   `ensembl_transcript?: string | null` to `VariantReportHeader`. (Ensembl *gene*
   ENSG is derived FE-side from a small map and shows live.)
5. **MANE-select flag** — optional `is_mane_select?: boolean` on the header.

## B. 4 call cards
6. **Population card colour** — backend emits `ui_color_theme:
   "neutral_slate_state"` for `population_frequency`, so it rendered grey. The FE
   now **derives its theme from the joint AF band** (BA1/BS1→green, 0.1–1%→yellow,
   <0.1%/absent→orange) as a stopgap. → have `report_call_cards` emit the
   AF-class `ui_color_theme` for the population card so the FE override can be
   dropped. (The other 3 cards already emit a real theme.)

## C. Metrics (hero + related variants) — all mock+labelled now
7. **View count** — `VariantReportHeader.view_count?: number | null` (or a
   `report_metrics` block). Drives hero "1,204 views" + related-card views.
8. **Last-updated** — `VariantReportHeader.last_updated?: string | null` (ISO).
9. **New / Updated** — `NearbyVariant.created_at?` / `updated_at?` (ISO) → drives
   the related-card pill (FE computes new-vs-updated from age).
10. **Per-related-variant 4-axis states** — `NearbyVariant.axis_states?: {
    computational?; clinical?; population?; lab_functional? }` using the same
    7-state `ui_color_theme` vocabulary → drives the mini 4-colour chip row
    (FE currently colours all 4 from the variant's overall classification).

## D. §3 Population
11. **Constraint Z-scores** — `MolecularContextSection.mis_z?: number | null`,
    `lof_z?: number | null` (LOEUF + pLI already flow). Drives the §3 thermometer
    "Missense Z" stat (mock now).

## E. §1 Clinical
12. **ClinVar submitter free-text interpretation** — add a per-submitter
    `interpretation` / `comment` string to the `clinvar` evidence summary
    (alongside the existing numeric `submitter_counts`). Drives the ClinVar
    `<CuratorQuote>` (mock-marked now). ClinGen narrative already flows.

## F. §6 Publications
13. **Pub-graph per-year counts** — `PublicationScopeCounts.{variant,gene}.per_year?:
    { year: number; count: number }[]` for BOTH scopes (spec: graph reflects
    variant *and* gene).
14. *(optional)* **Variant-scoped PubMed `term`** — `PublicationScopeCounts.variant.query`
    so the §6 "PubMed ↗" link uses a curated variant term instead of the FE-built one.

---
### Paste-ready Codex message
```
Report v3 FE is shipped (uncommitted, app/web/**). Backend gaps to wire when you're
free (full detail: docs/report-redesign/codex-handoff.md, contract table in
plan.md §10). Each ships mock+labelled FE-side, so additive + optional is fine;
mirror both backend.ts byte-identical; you own the SG redeploy+verify after.
Priority order: (A) report payload protein_change + molecular_context.exon for RPE65
(both null today → hero shows "needs live data"); (B) population_frequency card
ui_color_theme should reflect the AF band (emits neutral_slate now, FE overrides);
(C) view_count + last_updated + NearbyVariant.created_at/updated_at/axis_states;
(D) MolecularContextSection.mis_z/lof_z; (E) clinvar submitter interpretation text;
(F) PublicationScopeCounts.per_year (variant+gene) + variant.query. rsID + ENST +
MANE flag on VariantReportHeader round it out.
```
