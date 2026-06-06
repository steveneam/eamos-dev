# Spec — Apply Benchling to the Eamos Workbench (gene-viewer scroller + Align intuitive flow)

> Status: **APPROVED 2026-06-06 (Steven).** Build order locked: **viewer band → Align flow → CRISPR → Primer**, in-slot library picker only (no shared `LibrarySection` change in v1). Build is **gated**: durable UI ships only after Steven's browser-verify OK, slice by slice. Backend is Codex's lane — this spec touches **only `app/web/**`** (FE-only v1; `POST /api/v1/align` already exists).

## What

Apply Benchling's strengths we mined this session to the Eamos Next.js Workbench (`app/web/components/workbench/**`): **(1)** refine the gene-viewer/sequence-map scroller to match Benchling's "robust and tight" feel (a visible drag-handle selection band spanning all rails, a clearer codon-number axis, density-driven zoom polish); **(2)** replace the flat `AlignPanel` (twin textareas + a separate trace card) with an intuitive **top-to-bottom Align flow** — two side-by-side Subject A | ⇄ | B slots, each a multi-source picker + drag-drop target, one prominent **Align** button, and a results stack (metric strip → diff track → collapsed chromatogram); and **(3)** refine the **Primer** and **CRISPR guide** design panels' layout + functions toward Benchling's column sets and on-map overlays (primer property table parity; CRISPR two-table candidate/detail layout with the canonical guide column set; designed primers + guides rendered as tracks on the sequence viewer). All reuse the existing, proven engines underneath (no new alignment/viewer/primer/CRISPR math); the change is the shell, the tables, and the interaction.

## Context

Why: the Align tool is "not intuitive" (Steven) — it's a flat pile of two textareas + a trace card with no clear path, no obvious import, no drag-drop, and the run action is buried. Benchling's gene viewer is the incumbent visual language clinicians expect ("really robust and tight" — Steven). This session gathered the intel to close both gaps. **Benchling = the reference to apply now; Franklin = standing competitive intel (separate, not applied here).**

Evidence base gathered this session (all ground-truthed):
- **Benchling API data model** (via `benchling-pp-cli`, internal): alignments are **template** (`createDnaTemplateAlignment`, reads vs one reference) vs **consensus** (`createDnaConsensusAlignment`); engine **ClustalO** w/ params; each aligned read maps to the template by **0-based `start`/`end` ranges + bases**; AB1 traces feed alignment via blobs; primers = oligo entities; CRISPR is app-only.
- **Benchling gene-viewer screenshots**: `…\EAMOS Web Tool\sources\competition\Benchling\Benchling sequence viewer {1,2,3}.png` and `Benchling Sequence alignment 1.png`. Competitor notes: `…\Wiki\entities\competitors\benchling.md`.
- **4 UX research reports** (Benchling/SnapGene/Geneious · Synthego ICE/TIDE/SnapGene traces · EBI Clustal/MAFFT/Needle+BLAST · NN/g+Carbon+React-Aria), converging on: two-subject side-by-side slots, pre-filled defaults, one prominent primary action, per-slot multi-source picker, drag-drop with keyboard fallback, results = metric strip + mismatch-jump + collapsed chromatogram.

What exists today (code):
- **Align**: `app/web/components/workbench/align/AlignPanel.tsx` — twin textareas (`referenceInput`/`editedInput`), a "Trace input" card (AB1/JSON/API) + a separate "Browser fallback" card, `runApiAlignment()`/`requestApiAlignment()` → `alignSequences()` (Phase A mock-first, landed), browser pairwise via `compareSequences()`, `TracePanel` chromatogram. Engine + types: `lib/workbench/alignment-pairwise.ts` (`compareSequences`, `normalizeAlignResponse`, `makeAlignmentSeed`, `AlignApiResponseShape`, `AlignTraceView`). Offline fixture: `lib/workbench/align-sample.ts` (`ALIGN_SAMPLE`). API: `lib/api.ts` `alignSequences()`.
- **Viewer**: `app/web/components/workbench/viewer/SequenceViewerV2.tsx` — wrapped exon/intron rows, AA/codon strip (`buildCodons`), ruler, ClinVar lollipops; range `selection` state `{start,end}` with click-drag (`:109`, `:430`) + keyboard (`:494+`); `onSelectionChange` → side-panel edit hub; right-click edit (`EditPopoverV2`). Zoom: `ZoomSlider.tsx` + `zoom-config.ts` (continuous px/base 8–22; chips gene=9/exon=14/codon=20). Minimap: `GeneMinimap.tsx`.
- **Library store** (drag source): `lib/variant-library.ts` — `getLibrary()`/`subscribe()` (useSyncExternalStore), `SavedVariant {gene, variant(cdna), query, classification, hgvs_full}` — **no sequence stored**; rendered in the left controls rail as "SAVED VARIANTS".
- **Window/edit model**: `lib/workbench/gene-window.ts` (`GeneWindowData`, `makeAlignmentSeed`), `lib/workbench/gene-viewer-adapter.ts` (`adaptGeneViewer`), `lib/api.ts` `getGeneViewer()` (`POST /api/v1/viewer`, mock-first only for the default RPE65 payload).
- **Primer**: `align`-adjacent `primer/PrimerPanel.tsx` (modes Sanger/qPCR/ARMS, Generate & validate → feed of `PrimerResultCard` 3-layer disclosure cards; ARMS = "unsupported" placeholder), `lib/api.ts` `designPrimers()` (mock-first → `PRIMER_SAMPLE`). Engine = Primer3 backend (`use_real_apis`-gated). Benchling uses the **same Primer3** algorithm (per `benchling.md`).
- **CRISPR**: `crispr/CrisprPanel.tsx` (Design + Outcomes tabs), `crispr/DesignTab.tsx` (gRNA table + `GuideTrack` + ssODN block; SpCas9 only, SaCas9/Cas12a disabled), `crispr/OutcomesTab.tsx` (TIDE, observed-only), `lib/api.ts` `designGuides()` (mock-first → `CRISPR_SAMPLE`). Off-target via backend NGG regex + RepeatMasker (no API guide endpoint on Benchling — app-only). Benchling intel: `…\sources\competition\Benchling\Benchling CRISPR {1,2}.png`, `Benchling Primer design.png`.

## Requirements

### Part 1 — Gene-viewer scroller refinements
1. The current sequence selection MUST render as a **visible vertical band** spanning all stacked rails (DNA both-strands + AA/codon strip + feature rails) for the selected `[start,end]`, not just an implicit state.
2. The band MUST have **drag handles** (start edge + end edge) that extend/shrink the selection by base/codon; existing click-drag and keyboard selection MUST continue to work (augment, not replace).
3. The translation strip MUST show a **codon-number axis** (periodic codon numbers aligned to codons), matching Benchling's `6 8 10 …` density.
4. Zoom MUST remain density-driven (px/base via `ZoomSlider`); no regression to the chips or slider. (Polish only — see Decisions.)
5. No regression: existing edit (right-click `EditPopoverV2`), jump-to, lollipops, both-strand render, exon/intron wrapping, and the side-panel edit hub all keep working.

### Part 2 — Align intuitive flow
6. `AlignPanel` MUST present a **top-to-bottom flow**: Subject A and Subject B slots (side-by-side desktop, stacked narrow) → a single primary **Align** action → results.
7. Each slot MUST offer a **source switcher** with: current variant · reference/control · saved library variant · paste/FASTA · Sanger AB1.
8. Slots MUST be **pre-filled by default** (A = reference/control, B = current variant) so the panel is never empty and Align produces a result immediately (= today's `makeAlignmentSeed` behaviour).
9. Each slot MUST be a **drop target** accepting a dragged saved-variant chip from the library rail AND a dropped file (AB1/FASTA). Drag MUST have a **keyboard/click fallback** (a "→ A / → B" or pick action on each library row; native `<input type=file>` retained). (React-Aria model per UX research.)
10. A **swap (⇄)** control MUST exchange A and B.
11. The **Align** button MUST be the single high-emphasis action, **disabled with an inline reason** until both subjects are resolved.
12. A **saved/template library variant** chosen as a subject MUST resolve to its sequence by fetching that variant's gene window (`getGeneViewer` → `adaptGeneViewer` → `makeAlignmentSeed().edited`), v1 limited to **same-gene** variants (cross-gene → disabled with a note; paste still available). Per-slot loading/error states required.
13. Results MUST render in order: **metric strip** (identity % · matches · mismatches · gaps · spans) → **diff track / pairwise block** (REF/MATCH/EDITED + diff chips) → **collapsed chromatogram** (disclosure; only when a subject is an AB1/API trace) → **mismatch-jump ◀▶** navigation over the diffs.
14. The existing engine MUST be reused unchanged: `compareSequences()` for the pairwise, `alignSequences()`/`normalizeAlignResponse()`/`TracePanel` for AB1/API + chromatogram, `ALIGN_SAMPLE` offline fallback.

### Part 3 — Primer + CRISPR guide design (layout + functions)
15. **CRISPR** results MUST adopt Benchling's **two-table** shape: a candidate-summary table + a detailed-guide table whose canonical columns are `Start | End | Strand | Guide (colour-coded 20-mer) | On-target | Off-target | Genome/region`. Eamos's transparent scoring (NGG regex + RepeatMasker off-target) stays the source — only the **column shape + colour-coded guide rendering** are matched.
16. Designed **CRISPR guides** MUST render as **tracks overlaid on the sequence viewer** (extend `GuideTrack`), so candidates are visible on the map (Benchling parity), not table-only.
17. The CRISPR **ssODN / HR-template** affordance MUST remain a first-class sibling of the guide table (Eamos already has it in `DesignTab`); keep, don't regress.
18. **Primer** results MUST present a tight **property table** with column parity to Primer3 output: `Tm · GC% · product length · self-dimer · hetero-dimer · hairpin · penalty` (in addition to / behind the existing 3-layer cards). Recommended ★ row preserved.
19. Designed **primers** MUST render as **tracks overlaid on the sequence viewer** (forward/reverse primer spans), matching Benchling showing primers on the map.
20. Part 3 MUST NOT add a cross-document primer/guide registry ("Attach existing" is ELN territory — explicitly excluded per `benchling.md`), MUST NOT change `designPrimers`/`designGuides` request contracts, and MUST keep mock-first behaviour (`PRIMER_SAMPLE`/`CRISPR_SAMPLE`).

## Design

**Shared principle: new shell, same engine.** Both parts are interaction/layout changes over existing pure logic. No changes to `alignment-pairwise.ts` math, `gene-window.ts` builders, or any `app/backend/**`.

### Part 1 files
- `viewer/SequenceViewerV2.tsx` — render a selection-band overlay across the rail stack for `[min(start,end), max(start,end)]`; add two handle elements (pointer-drag to update `selection` via the existing setter); add periodic codon-number labels in the AA strip. Keep `onSelectionChange`/edit-hub contract intact.
- `viewer/workbench.css` (or the viewer's CSS module) — `.seq-selection-band` + `.seq-selection-handle` using existing tokens (`--teal-tint` band, `--line`/`--teal-deep` handles); **no new token** unless Steven wants a dedicated selection colour (flagged).
- (Possibly) `viewer/viewer-types.ts` — if a handle-drag mode enum is needed.

### Part 2 files
- `align/AlignPanel.tsx` — restructure the render into: header → `SubjectSlot A` ⇄ `SubjectSlot B` → primary Align button → `AlignResults`. Keep the `apiStatus` machine, `compareSequences`, `runApiAlignment`, `normalizeAlignResponse` calls; move them behind the new shell. The twin-textarea bodies become the "paste/FASTA" source inside a slot.
- **NEW** `align/SubjectSlot.tsx` — one slot: source switcher (segmented/menu), the source-specific body (read-only chip for current/reference/library; textarea for paste; file dropzone for AB1), drop-target handlers (file + library-chip), loading/error, a clear ✕. Emits a resolved `{ label, sequence, targetIndex, trace? }`.
- **NEW** `align/align-subjects.ts` — pure resolver: `resolveSubject(source, ctx) → Promise<ResolvedSubject>`; `current`→`seed.edited`, `reference`→`seed.reference`, `library`→fetch-window-per-variant, `paste`→parsed, `ab1`→`alignSequences()`/trace. Same-gene guard for library.
- **NEW** `align/AlignResults.tsx` — metric strip + pairwise block + diff chips + mismatch-jump ◀▶ + `<TracePanel>` behind a disclosure. (Moves existing render fns out of `AlignPanel`.)
- Library rail (`LibrarySection` in the controls rail) — add a keyboard/click "send to Align A/B" affordance + make rows draggable (drag payload = `query`). Mandatory fallback per Req 9. (⚠ touches shared `LibrarySection` — gated.)

### Data flow (Align)
`SubjectSlot(source)` → `resolveSubject()` → `{sequence,label,targetIndex,trace}` → on **Align**, feed A.sequence/B.sequence to `compareSequences()` (browser pairwise) and, if a subject is AB1/API, `alignSequences()`→`normalizeAlignResponse()`→chromatogram → `AlignResults`.

### Part 3 files
- `crispr/DesignTab.tsx` — restructure the guide output into the two-table shape (candidate summary + detailed guides) with the canonical column set + colour-coded 20-mer; keep `designGuides()` call + ssODN block. Reuse `.tool-table` idioms (no new table system).
- `crispr/GuideTrack.tsx` — already a track component; ensure designed guides render as overlaid tracks on the viewer canvas (Req 16). Confirm wiring from `DesignTab`.
- `primer/PrimerPanel.tsx` + `primer/PrimerResultCard.tsx` — add a compact primer-properties table (Tm/GC/product/dimers/hairpin/penalty) alongside the existing 3-layer cards (Req 18); keep the recommended ★ row.
- **NEW (small)** `primer/PrimerTrack.tsx` (or extend an existing track) — render designed primer spans (fwd/rev) as viewer tracks (Req 19). `Assumption:` mirrors `GuideTrack` rendering.
- No `lib/api.ts` contract change; no new sample fixtures (reuse `PRIMER_SAMPLE`/`CRISPR_SAMPLE`).

## Decisions

1. **Align restructure depth — new shell over the existing engine (not a from-scratch rebuild, not just pickers-bolted-on).** Steven first chose "surgical source-pickers," then asked for an "intuitive top-to-bottom flow." Reconciliation: rebuild the *layout/interaction* into the A/B flow (the intuitive part) while reusing every existing pure function and the `apiStatus` machine (the surgical part). Reversible (the engine is untouched). *Alternatives:* (a) pickers bolted onto today's textareas — rejected, doesn't deliver the top-to-bottom feel; (b) full rewrite incl. engine — rejected, needless risk.
2. **Library variant → sequence via fetch-window-per-variant (Steven-locked).** Resolve any same-gene saved variant through `getGeneViewer`+adapter+`makeAlignmentSeed`. Cross-gene = disabled with a note (paste still works). Reversible.
3. **Selection band augments, not replaces, existing selection (Part 1).** The `{start,end}` state and click-drag/keyboard stay; we add the visible band + handles on top. Reversible.
4. **No new design tokens** unless Steven wants a dedicated selection-band colour. `Assumption:` reuse `--teal-tint`/`--line`.
5. **`compare`/Comparator stays dead.** Do not add `'compare'` to `TOOL_ORDER`; the ghost CSS/meta remain dormant (prior decision).
6. `Assumption:` chromatogram shows only when a subject is AB1/API trace; variant-vs-variant/control render the pairwise block with no chromatogram (correct — no trace exists).
7. `Assumption:` v1 keeps a single pairwise A-vs-B (no 3+ MSA); "template vs consensus" informs framing/labels, not a new multi-read engine this cycle.
8. **Part 3 is column-shape + on-map-overlay parity, not engine change.** Match Benchling's CRISPR two-table column set + colour-coded guides and primer property table, and render guides/primers as viewer tracks — but keep Eamos's transparent engines (Primer3, NGG+RepeatMasker) and existing mock-first contracts. Reversible. *Alternatives:* a from-scratch primer/CRISPR rebuild — rejected (they ship today; this is refinement). `Assumption:` real-data parity waits on Codex's `use_real_apis` flip (out of scope).

## Open Questions for Steven — RESOLVED 2026-06-06 (Steven review)
- **OQ1 (Part 1 priority):** **Resolved → band first.** Build the drag-handle selection band first, then the codon-number axis; defer density polish. (Claude default, accepted.)
- **OQ2 / OQ5 (build order):** **Resolved → viewer band first.** Sequence: **viewer band → Align flow → CRISPR two-table+overlay → Primer table+overlay.** Part 3's on-map overlays depend on the viewer track work, so they follow the band slice. Each slice is independently gated on Steven's browser-verify before ship (so "stage Part 3" is handled by the per-slice gate — he can stop after any slice).
- **OQ3 (library drag scope):** **Resolved → in-slot picker only for v1.** Each Align slot gets a library picker; **no change to the shared `LibrarySection`** this cycle. Drag-drop + "→A/→B" send actions deferred to a follow-up.
- **OQ4 (template/consensus labelling):** **Resolved → keep clinical vocabulary** ("reference/control vs variant/read"); note Benchling's template/consensus parity only in tooltips.

## Invariants
- `POST /api/v1/align` request body stays `{gene, cdna, user_sequence, ab1_blob_base64}` (Req 14; do not change the contract — Codex owns backend).
- The viewer's `onSelectionChange`/edit-hub contract and right-click edit path must not regress (Req 5).
- tsc `--noEmit` 0 errors; lint 0 errors (6 pre-existing warnings tolerated).

## Error Behavior
- Library-variant fetch fails / cross-gene / out-of-window → per-slot inline error + the slot stays usable (pick another source); the other slot + Align unaffected.
- AB1/API offline → existing `ALIGN_SAMPLE` mock fallback (TypeError) paints the chromatogram; real non-OK → error state (today's behaviour, unchanged).
- Drop of an unsupported file → per-slot inline "not an AB1/FASTA" message; native picker retained.

## Testing Strategy
- `app/web` has no test runner (no vitest) → gate = `( cd app/web && npx tsc --noEmit )` 0 errors + `npm --prefix app/web run lint` 0 errors + **browser-verify on `:3000`** per slice:
  - Part 1: select a range → band + handles render across all rails; drag a handle → selection extends; codon numbers align; existing edit/jump/lollipops unaffected.
  - Part 2: panel pre-filled (A=ref, B=variant) → Align paints immediately; switch B to a same-gene library variant → resolves + diffs render; cross-gene → disabled+note; AB1 source → chromatogram in disclosure; offline → `ALIGN_SAMPLE`; swap ⇄ works; Align disabled-with-reason until both filled; mismatch ◀▶ navigates.
  - Part 3: CRISPR Design → two-table layout with the canonical columns + colour-coded guides; guides overlay as tracks on the viewer; ssODN block intact. Primer Generate → property table (Tm/GC/product/dimers/hairpin/penalty) + recommended ★; designed primers overlay as viewer tracks. Mock-first still works offline (`CRISPR_SAMPLE`/`PRIMER_SAMPLE`); no contract change.
- Pure resolver `align-subjects.ts` is type-checked + exercised in the browser checks (no unit runner). Optionally add vitest to `app/web` later (out of scope).

## Out of Scope
- Any `app/backend/**` change; new `/api/v1` contracts; flipping `use_real_apis`.
- 3+ sequence MSA / a real consensus engine; new alignment algorithm.
- New primer/CRISPR **engine or scoring model** (Part 3 is column-shape + on-map-overlay parity only); cross-document primer/guide registry ("Attach existing"); ARMS real-mode; flipping `use_real_apis`.
- Authenticated Franklin features; publishing the intel CLIs.
- The `compare`/Comparator tool; AskEamos pill.
- Full viewer rebuild (this is refinement).
