# FGV-003 — Full-Gene Row Renderer Proof: FE Implementation Notes

Claude (frontend lane). Sibling to FGV-003 in `full-gene-workbench-plan.md`
(Codex authored that task). This file captures the FE-side architecture so
Steven can sanity-check before code lands. Backend contract is locked in by
Codex's FGV-001 + FGV-002 (`ViewerFullLocus` in `app/web/lib/backend.ts`
lines 1538–1544); this design only describes the FE consumer.

## Decision

**Parallel new component `FullLocusViewer`** rendered alongside the existing
`SequenceViewerV2`, with `WorkbenchShell` routing on a viewer-mode toggle.

Rejected alternative: retrofitting `SequenceViewerV2` with a discriminated
union `WindowData | FullLocusData` and branching internally. Reason: the
row model is fundamentally different (genomic bases with CDS overlays vs
the existing CDS-flat `FlatBase[]` model). A union retrofit creates deep
conditionals through CodonDetail / GeneMinimap / ProteinView / edit /
scratchpad bindings — high regression risk to window mode that already
works on `/runs`-style window payloads.

This slice keeps window mode untouched. Existing fixture path
(`GENE_VIEWER_SAMPLE` RPE65 c.260A>G) and `/report` link-out still resolve
into window mode by default.

## File inventory (this slice)

New:

- `app/web/lib/workbench/full-locus-layout.ts` — pure row-layout module.
  Input: `ViewerFullLocus` (snake_case, straight from backend). Output:
  `FullLocusRows` (row-keyed structure with base text, genomic positions,
  exon/intron/UTR/CDS band membership, codon overlays). No DOM. No React.
  Unit-testable.
- `app/web/lib/workbench/full-locus-adapter.ts` — *thin* mapper from
  `GeneViewerResponse` → `FullLocusViewModel` (camelCase wrapper around
  the layout result + queried-variant pin + provenance warnings). Mirrors
  the pattern of `gene-viewer-adapter.ts` but keeps mostly snake_case for
  the locus body because the contract is already row-oriented; we don't
  need a second naming convention for the same data.
- `app/web/components/workbench/viewer/FullLocusViewer.tsx` — new
  component. Vertical scroller, stable row heights, variant pin, exon/
  UTR/CDS bands. Reads from `FullLocusViewModel`. No selection / edit /
  scratchpad / minimap this slice (deferred to FGV-004+).

Modified:

- `app/web/components/workbench/WorkbenchShell.tsx` — add
  `viewerMode: 'window' | 'locus'` state (default `'window'`, preserves
  current behavior). When `'locus'`, pass `window: { kind: 'full_gene' }`
  to `getGeneViewer`. When response includes `full_locus`, render
  `<FullLocusViewer />`; otherwise fall back to `<SequenceViewerV2 />`
  with a "full-gene unavailable for this gene" honest banner.
- `app/web/components/workbench/viewer/ViewerToolbar.tsx` — add a
  two-state toggle ("Window" / "Full gene") to drive `viewerMode`.

Unchanged: `SequenceViewerV2`, `CodonDetail`, `GeneMinimap`, `ProteinView`,
`gene-window.ts`, `gene-viewer-adapter.ts`, `EditPopoverV2`,
`HistoryTimeline`, edit reducer, scratchpad. Window mode is byte-stable.

## Data flow

```
WorkbenchShell.fetch
  ├─ window mode → getGeneViewer({ gene, cdna, ... })          → adaptGeneViewer  → SequenceViewerV2
  └─ locus mode  → getGeneViewer({ gene, cdna, window:{kind:'full_gene'} })
                                                               → adaptFullLocus   → FullLocusViewer
```

`adaptFullLocus(resp)`:

- If `resp.full_locus == null` → return `{ kind: 'unsupported', gene, cdna }`.
  WorkbenchShell renders the honest fallback banner (per Codex's
  `workbench_unsupported_input:full_gene` fail-closed contract).
- Else → `{ kind: 'ready', model: buildFullLocusRows(resp.full_locus, ...) }`.

## Row layout algorithm

Inputs:
- `locus.sequence` (one contiguous string, full genomic span, length =
  `locus.end - locus.start`).
- `rendering_hints.bases_per_row_min / _max` — viewer enforces a default
  within the hint range; user can change via existing zoom but that's
  FGV-004 polish, not this slice. Initial constant: 60 bp/row.
- `transcript_projection.intervals` (exon/intron/UTR/CDS spans in genomic
  coords).
- `transcript_projection.codon_starts` (per-codon CDS start with three
  genomic positions and protein position).
- `feature_intervals` (queried_variant, ClinVar, restriction, ...).
- `rendering_hints.orientation` (genomic_forward vs genomic_reverse).

Output (per row):

```ts
interface FullLocusRow {
  rowIndex: number
  genomicStart: number   // inclusive, 1-based per backend
  genomicEnd: number     // inclusive
  bases: string          // length = genomicEnd - genomicStart + 1
  bands: Array<{
    kind: 'utr5' | 'utr3' | 'exon' | 'intron' | 'cds'
    bandStart: number    // column within row, 0-indexed
    bandEnd: number      // exclusive
    label: string        // 'Exon 5' etc.
    exonNumber?: number
    intronNumber?: number
  }>
  codonOverlays: Array<{
    codonNumber: number
    proteinPosition: number
    bases: [number, number, number]  // column indices within row
    aaRef: string
  }>
  queriedVariantCol?: number  // column index in row, when this row holds the variant base
}
```

The renderer paints rows as plain DOM for the proof (`<div>` per row with
`<span>` runs for bases + absolutely-positioned band overlays). Canvas
swap is FGV-004 if ABCA4 perf shows DOM is too heavy — measure first.

For ABCA4 (128,315 bp / 60 bp/row = 2,139 rows): plain DOM should hold
with row virtualization. If we need it, use `react-window` already in
deps; if not, render all rows. Decide after a real measurement.

## Initial scroll behavior

On mount, find the `queriedVariantCol`'s row and scroll it into view at
~30% from the top of the scroller (keeps context above + below visible).
`ref.scrollTop = row.offsetTop - container.height * 0.3`. One-shot — no
sticky scroll-restoration this slice.

## Mode toggle copy

Toolbar: two pill buttons, single-select. Default = "Window".

- `Window` — current CDS-centric view with introns collapsed
- `Full gene` — full genomic locus (introns visible, UTRs visible, scrolls)

Selecting `Full gene` for a gene outside the FGV-002 fixture roster
(RPE65 / CFTR / BRCA1 / ABCA4 / TP53) — backend returns response with
`full_locus: null` and the renderer shows: "Full-gene view is available
for the curated stress matrix (RPE65, CFTR, BRCA1, ABCA4, TP53). Window
view is shown instead." with a button to flip back.

## Out of scope this slice

- GeneMinimap full-locus mode (FGV-004)
- Search by genomic/cDNA/CDS coordinate (FGV-004)
- Exon jump from minimap (FGV-004)
- Color schemes: bases + AA (FGV-005)
- Scratchpad TTL + saved notes (FGV-006)
- Selection / range-edit / replace-selection in full-gene mode (port from
  window mode later)
- Primer / CRISPR / Align consumption of full-gene selection (waits for
  `sequence_mode` contract; user direction 2026-05-28)
- Conservation, restriction sites, ClinVar density in full-gene mode
  (rendering plumbing exists for window mode; ports later)
- Canvas/WebGL row rendering (only if DOM measurement on ABCA4 fails)

## Verification

```powershell
cd app/web
./node_modules/.bin/tsc --noEmit
```

Browser-verify:
- RPE65 c.260A>G in `Full gene` mode → renders ~21 kb locus with variant
  pin centered, exon/intron bands aligned, codon overlay spans exactly
  3 bp per codon.
- ABCA4 c.5435T>A in `Full gene` mode → renders all 128,315 bp scrollable
  without row drift; queried variant pin reachable by scroll; toggle back
  to `Window` mode resolves cleanly.
- Non-fixture gene (any) in `Full gene` mode → honest fallback banner;
  toggle back works.

## Open questions for Steven

1. **Default mode for the curated five.** Should `Full gene` be the
   default when the user lands on RPE65 / CFTR / BRCA1 / ABCA4 / TP53,
   per the FGV plan's "default should feel like a true full-gene
   sequence view" direction? Or keep `Window` as default and let the
   user opt in via the toggle? My read: default to `Window` this slice
   (zero regression risk to existing behavior + `/report` link-outs);
   flip the default after FGV-004 ports selection/edit so the surfaces
   are at parity.

2. **Row width.** 60 bp/row is Benchling-ish. Comfortable on desktop,
   wraps on narrow viewports. Worth confirming or letting me iterate
   in browser?

3. **ABCA4 perf budget.** OK to ship the proof with naive all-rows DOM
   and measure-then-virtualize as a follow-up if it stutters? Or want
   virtualization in this slice?
