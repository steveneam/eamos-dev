# Full-Gene Workbench Sequence Viewer Plan

Section edited: 2026-05-28 00:31 +1000 - Codex.

## Purpose

Make the Workbench sequence viewer feel like a serious sequence editor: a true
full genomic-locus view for the active gene, including introns and UTRs, with
codon-aware CDS overlays, clean exon/UTR/annotation tracks, vertical scrolling,
and gene-agnostic performance. Benchling is the interaction reference for
density and continuity, not the visual style reference.

This is a planning artifact only. No implementation, schema mirror, runtime
source wiring, production download, or Supabase write was performed while
writing it.

## Source Inputs

- User direction on 2026-05-28:
  - Full gene means the full genomic locus, including introns and UTRs.
  - The spliced transcript/protein interpretation belongs in the protein view.
  - Default should feel like a true full-gene sequence view, not a clipped
    variant window.
  - Stress examples: RPE65, CFTR, BRCA1, ABCA4, TP53, with ABCA4 as the large
    gene proof.
  - Large genes should render fully, not as user-visible chunks.
  - Automatic edit logs should expire after roughly 24 to 48 hours. Deliberate
    notes should be saveable. Scratchpad may grow into a lab-book surface.
  - Primer, CRISPR, and Align should wait for a backend sequence-mode or
    viewer-context contract after the sequence viewer is solid.
  - Nucleotide letters default to black, with optional coloring. Amino-acid
    coloring should follow a recognized biochemical scheme rather than
    arbitrary colors.
- Benchling screenshots under:
  `C:\Users\seamegdool\Desktop\Claude code and website tips\EAMOS Web Tool\Competition\Benchling`
- Existing Eamos files:
  - `plans/gene-viewer/design.md`
  - `plans/gene-viewer/spec.md`
  - `plans/gene-viewer/plan.md`
  - `app/backend/app/schemas/gene_viewer.py`
  - `app/backend/app/services/gene_viewer.py`
  - `app/web/components/workbench/viewer/SequenceViewerV2.tsx`
  - `app/web/components/workbench/viewer/CodonDetail.tsx`
  - `app/web/components/workbench/viewer/GeneMinimap.tsx`
  - `app/web/lib/workbench/gene-viewer-adapter.ts`
  - `app/web/lib/workbench/gene-window.ts`
  - `app/web/lib/workbench/codon-layout.ts`

## Product Decisions

- The Workbench default should be a full genomic-locus sequence view. It may
  initially scroll to and highlight the queried variant because users arrive
  from a variant, but the sequence surface itself must be the whole gene, not a
  small variant window.
- Full-gene means genomic orientation and coordinates for the selected gene
  locus, including UTRs, exons, introns, and flanking annotation only when
  explicitly requested. The protein view remains the spliced coding-product
  interpretation.
- "Render fully" means the full gene is loaded, searchable, scrollable, and
  navigable as one continuous sequence. It must not expose pagination or
  chunk-loading to the user. If the renderer needs virtualization or canvas
  painting internally for ABCA4-class performance, that is an implementation
  detail only; the user still gets one full-gene scrollbar and complete search.
- Default visible tracks:
  - Sequence bases as black letters.
  - Genomic ruler and cDNA/CDS coordinate ticks where applicable.
  - Gene, UTR, exon, CDS, and intron annotation bands.
  - Queried variant vertical pin.
  - Codon frame and amino-acid row over CDS bases only.
  - Active transcript and exon navigation.
- Optional tracks:
  - Nucleotide colorization.
  - ClinVar pins/density.
  - Conservation.
  - Restriction sites.
  - Primer and CRISPR overlays after tool sequence-mode wiring exists.
- Amino-acid colors should use a recognized biochemical grouping, with Eamos
  muted tokens. A good first scheme is Jalview/Zappo-style property grouping:
  aliphatic/hydrophobic, aromatic, positive, negative, hydrophilic, special
  Pro/Gly, cysteine, and stop. Jalview also documents Taylor,
  Hydrophobicity, Clustal, BLOSUM62, and nucleotide schemes, so Eamos should
  label the scheme rather than imply a single universal "correct" palette.
- Nucleotide color has no single universal clinical rulebook. Default black is
  right for Eamos. The optional color mode can use a named "nucleotide" scheme
  with muted Eamos colors and a legend.
- Tool consumption waits. Primer, CRISPR, Align, and Compare should not consume
  full-gene selection state until the backend exposes an approved additive
  `sequence_mode` or `viewer_context_id` contract.

## Shared Architecture Direction

The existing `POST /api/v1/viewer` contract is window-first. Full-gene mode
should be an additive contract extension, not a replacement.

Recommended backend shape:

- Add a request mode such as `window.kind = "full_gene"` or an explicit
  `view_basis = "genomic_locus"`.
- Return the full genomic sequence for the gene locus, not only CDS windows.
- Return annotation intervals separately from sequence text: UTR, CDS, exon,
  intron, transcript, queried variant, ClinVar, conservation summaries,
  restriction sites, and future tool overlays.
- Preserve transcript-oriented mappings so the frontend can align genomic
  bases to cDNA/CDS/codon/protein coordinates without recomputing biology.
- Preserve source provenance and fail-closed behavior for reference mismatch,
  unsupported variant types, ambiguous transcript, and unavailable sequence.

Recommended frontend shape:

- Keep `SequenceViewerV2` as the product shell but split its current window
  model from a new full-locus row model.
- Build row layout from full genomic bases, then overlay CDS/codon rows only
  where transcript coding bases exist.
- Use one vertical internal sequence scroller, like Benchling, with stable row
  heights and no horizontal drift.
- Avoid one DOM node per base for large genes if performance suffers. Canvas or
  row-level text rendering is acceptable if selection, edit, search, and
  tooltips remain precise.

## Task FGV-001 - Contract Amendment For Full Genomic Locus

### Goal

Define the additive backend contract for full-gene genomic-locus viewing.

### Context

`app/backend/app/schemas/gene_viewer.py` currently models a viewer window
around a variant or CDS range. The new Workbench target needs the whole gene
locus, including introns and UTRs, while preserving cDNA/CDS/protein
projection.

### Relevant Files

- `plans/gene-viewer/spec.md`
- `app/backend/app/schemas/gene_viewer.py`
- `app/backend/tests/test_frontend_contract.py`
- `app/web/lib/backend.ts` after contract approval and frontend coordination

### Proposed Approach

Write a small contract spec before code. Add an explicit full-locus request
mode and response group. Keep existing fields stable. Model the response as
sequence plus intervals, not as pre-rendered base cells.

Required concepts:

- Genomic locus: chrom, start, end, strand, build, sequence.
- Transcript projection: exons, UTRs, CDS ranges, cDNA/CDS coordinate map,
  codon starts, protein coordinate map.
- Feature intervals: queried variant, ClinVar, restriction sites,
  conservation summary bins, primer/guide overlays later.
- Rendering hints: row coordinate policy, recommended bases per row range, and
  maximum safe visual density if needed.
- Provenance: source id, version, checksum/path or URL, transcript ID, and
  warnings.

### Acceptance Criteria

- Existing window viewer requests remain valid.
- Full-gene mode can represent RPE65 and ABCA4 without truncating introns or
  UTRs.
- The contract states whether coordinates are genomic, cDNA, CDS, protein, or
  row-local for every interval.
- The response supports black-base default rendering plus optional base/AA
  color schemes without changing biological data.
- No tool contract changes are included in this task.

### Source Reference

User answers on 2026-05-28 and existing GV-001 to GV-009 plan.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_frontend_contract.py -q -k "not mirrors_are_byte_identical"
```

### Out Of Scope

Runtime provider wiring, frontend implementation, production source downloads,
tool sequence-mode consumption, and saved lab-book persistence.

## Task FGV-002 - Full-Gene Backend Fixtures And Stress Matrix

Status: DONE 2026-05-28 03:27 +1000 - Codex. Implemented deterministic
fixture-mode full-gene hydration for RPE65 and ABCA4 against the FGV-001
`full_locus` contract. ABCA4 is the large-gene stress proof; the remaining
curated transcript-model records can also hydrate through the same fixture path.
Live source-cache preference, production imports/downloads, frontend renderer
swap, and tool sequence-mode wiring remain out of scope.

### Goal

Provide deterministic full-gene payload fixtures for RPE65, CFTR, BRCA1,
ABCA4, and TP53, with ABCA4 as the large-gene stress proof.

### Context

The current backend fixture/provider can return RPE65 and curated non-RPE65
window payloads. A full-gene renderer needs full locus length, UTR/exon/CDS
intervals, sequence, and coordinate projection for multiple genes.

### Relevant Files

- `app/backend/app/services/gene_viewer.py`
- `app/backend/app/services/transcript_model.py`
- `app/backend/app/services/reference_genome.py`
- `app/backend/app/fixtures/workbench/`
- `app/backend/tests/test_gene_viewer.py`
- `app/backend/tests/test_transcript_model_store.py`

### Proposed Approach

Start fixture-first. Build or extend curated fixture payloads for the five
genes. Use existing local-first patterns: no production downloads by default,
explicit provenance, alias normalization, and fail-closed fixture validation.

ABCA4 must be treated as a performance fixture, not just a correctness sample:
the payload should be large enough to exercise full-gene scrolling, search, and
row layout.

### Acceptance Criteria

- RPE65, CFTR, BRCA1, ABCA4, and TP53 fixture requests validate through the
  full-gene response model.
- ABCA4 returns the full gene locus sequence and feature intervals, not a
  clipped display window.
- Reverse-strand genes preserve genomic coordinates and display orientation
  rules.
- Reference mismatch and missing transcript fail closed.
- Fixture tests do not require network, production downloads, Supabase, or
  native Linux-only readers.

### Source Reference

User-selected stress examples on 2026-05-28 and local-first source-model
workflow.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_gene_viewer.py tests/test_transcript_model_store.py -q
python -m ruff check app/services/gene_viewer.py app/services/transcript_model.py tests/test_gene_viewer.py
python -m black --check --target-version py310 app/services/gene_viewer.py app/services/transcript_model.py tests/test_gene_viewer.py
```

### Out Of Scope

Live source-cache preference, Supabase imports, production source downloads,
and primer/CRISPR/align changes.

## Task FGV-003 - Full-Gene Row Renderer Proof

### Goal

Render one complete gene locus in the Workbench sequence pane with vertical
scroll, stable rows, codon grouping, and precise variant focus.

### Context

`CodonDetail.tsx` currently lays out a flattened window, not a full genomic
locus. `workbench.css` already caps the sequence pane height and scrolls
internally, which is the right direction.

### Relevant Files

- `app/web/components/workbench/viewer/SequenceViewerV2.tsx`
- `app/web/components/workbench/viewer/CodonDetail.tsx`
- `app/web/lib/workbench/codon-layout.ts`
- `app/web/lib/workbench/gene-window.ts`
- `app/web/components/workbench/workbench.css`

### Proposed Approach

Create a full-locus row model that separates raw genomic base rows from
transcript/CDS/codon overlays. The first render can use the backend fixture
adapter or a checked-in frontend sample, but it must match the backend
contract. Initial viewport should center the queried variant while preserving a
true full-gene scrollbar.

### Acceptance Criteria

- The sequence pane displays the full locus as vertically wrapped rows.
- The queried variant is centered or near-centered on initial load without
  clipping the gene.
- Exon, UTR, CDS, and transcript bands are straight and aligned to bases.
- Codon overlays span exactly three coding bases and do not drift across rows.
- Introns and UTRs remain visible as genomic sequence, not hidden gaps.
- Search and jump can find positions outside the initial viewport.
- No text or tracks overlap at desktop and laptop widths.

### Source Reference

Benchling sequence-viewer screenshots and existing `CodonDetail.tsx`.

### Verify

```powershell
cd app/web
./node_modules/.bin/tsc --noEmit
```

Browser verification is required for RPE65 and ABCA4 at desktop and narrowed
viewport widths.

### Out Of Scope

Saved edits, tool consumption, live backend source preference, and lab-book
persistence.

## Task FGV-004 - Full-Gene Navigation And Selection UX

### Goal

Make full-gene navigation efficient: minimap, row ruler, exon jumping, variant
search, and base/range selection all work on the complete locus.

### Context

Benchling's strength is not decoration; it is tight navigation and selection in
a large sequence. Eamos already has `GeneMinimap`, `ViewerToolbar`, selected
base/range state, and side-panel edit actions.

### Relevant Files

- `app/web/components/workbench/viewer/GeneMinimap.tsx`
- `app/web/components/workbench/viewer/ViewerToolbar.tsx`
- `app/web/components/workbench/viewer/SequenceViewerV2.tsx`
- `app/web/components/workbench/SidePanel.tsx`
- `app/web/components/workbench/workbench.css`

### Proposed Approach

Upgrade navigation for full-locus scale:

- Whole-gene minimap with current viewport window, queried variant flag, exon
  blocks, and optional ClinVar density.
- Search by genomic coordinate, cDNA/CDS coordinate, exon, protein position,
  and sequence string.
- Click exon on minimap to scroll to that exon.
- Range selection summary in the side panel, including genomic span and
  transcript/CDS overlap.
- Base-edit popover remains available, but automatic edits are logged as
  temporary scratchpad events.

### Acceptance Criteria

- Minimap reflects the full gene, not only the displayed rows.
- Scroll position updates the active viewport marker.
- Jump to ABCA4 exon and queried variant is fast and accurate.
- Selection over intron, UTR, exon, and mixed ranges reports honest coordinates.
- Keyboard navigation remains usable after row wrapping.

### Source Reference

User's Benchling screenshots and existing Workbench side-panel behavior.

### Verify

```powershell
cd app/web
./node_modules/.bin/tsc --noEmit
```

Browser verification must include selecting bases before and after the queried
variant and jumping to a distant ABCA4 exon.

### Out Of Scope

Backend saved notebooks and downstream tool execution.

## Task FGV-005 - Biological Color Policy

### Goal

Define and implement an Eamos-appropriate color policy for bases, amino acids,
and semantic clinical overlays.

### Context

Eamos should not copy Benchling's saturated sequence colors. User direction is
black nucleotide letters by default, optional nucleotide color, and recognized
amino-acid color rules.

### Relevant Files

- `DESIGN.md`
- `PRODUCT.md`
- `app/web/app/globals.css`
- `app/web/components/workbench/workbench.css`
- `app/web/lib/workbench/codon-table.ts`

### Proposed Approach

Add named color modes:

- `Bases: none` as default: A/C/G/T letters render black.
- `Bases: nucleotide`: optional muted A/C/G/T colors with a small legend.
- `Amino acids: biochemical` as default for the translation row, based on
  Jalview/Zappo-style physicochemical groups but mapped to Eamos muted tokens.
- Future optional modes: hydrophobicity gradient or none.

Clinical classifications keep the existing Eamos ACMG ramp and never reuse AA
or nucleotide colors.

### Acceptance Criteria

- Nucleotide colorization can be toggled without changing the sequence data.
- Default sequence bases are black and highly legible.
- Amino-acid groups are labeled in code and UI tooltips as biochemical groups.
- Color choices are muted and pass contrast checks.
- ClinVar/ACMG colors remain semantically distinct from base and AA colors.

### Source Reference

Jalview documents built-in protein and nucleotide color schemes, including
Zappo, Taylor, Hydrophobicity, Clustal, BLOSUM62, Nucleotide, Nucleotide
Ambiguity, and Purine/Pyrimidine:
https://www.jalview.org/help/html/colourSchemes/index.html

### Verify

```powershell
cd app/web
./node_modules/.bin/tsc --noEmit
```

Run browser checks in default and nucleotide-colored modes.

### Out Of Scope

Changing Eamos ACMG classification colors and introducing saturated Benchling
rainbow styling.

## Task FGV-006 - Scratchpad Persistence And Lab-Book Boundary

### Goal

Separate temporary automatic edit logs from deliberate saved notes, while
leaving a clean path to a full lab-book product.

### Context

`SidePanel.tsx` already has Scratchpad tabs for Log, Notes, and Ask Eamos.
Automatic edit logs are useful but should expire. Notes are deliberate and
should be saveable. A full lab-book is larger than a viewer polish task.

### Relevant Files

- `app/web/components/workbench/SidePanel.tsx`
- `app/web/lib/workbench/edit-state.ts`
- Future backend note/lab-book schema only after approval

### Proposed Approach

First slice:

- Automatic edit log entries include timestamps and expire after a configured
  TTL, defaulting to 48 hours with a 24-hour option if chosen.
- Notes tab supports explicit save, draft state, and last-saved status.
- Saved notes are scoped to gene, variant, transcript, allele mode, and user
  identity when auth-backed persistence exists.
- Until backend persistence is approved, local-only saved notes must be labeled
  honestly.

Future lab-book slice:

- Treat Scratchpad as a notebook entry stream with versioned notes,
  attachments, sequence selections, edit events, provenance snapshots, and
  export.
- This needs its own spec because it touches auth, storage, audit history,
  privacy, and likely billing.

### Acceptance Criteria

- Automatic edit log entries expire without deleting saved notes.
- Notes do not disappear on tab switch or short navigation.
- The UI distinguishes temporary log entries from saved notes.
- The implementation does not imply regulated ELN compliance before that is
  explicitly designed.

### Source Reference

User direction on 2026-05-28.

### Verify

```powershell
cd app/web
./node_modules/.bin/tsc --noEmit
```

Add unit tests for TTL behavior if the persistence logic is factored into a
pure helper.

### Out Of Scope

Full electronic lab notebook, file attachments, audit certification, team
sharing, and Supabase writes without an approved backend storage design.

## Task FGV-007 - ABCA4 Performance And Browser Verification Gate

### Goal

Prove that the full-gene viewer can handle a large gene in normal browser use.

### Context

ABCA4 is the explicit stress case. The risk is not backend biology alone; it is
browser rendering, scroll performance, text overlap, selection precision, and
memory use.

### Relevant Files

- `app/web/components/workbench/viewer/**`
- `app/web/lib/workbench/**`
- `app/web/components/workbench/workbench.css`
- `app/backend/tests/test_gene_viewer.py`

### Proposed Approach

Add a verification gate that runs after the full-gene renderer and backend
fixture exist. Measure and inspect:

- Initial load and scroll responsiveness.
- Full-gene scrollbar and row count.
- Search across distant regions.
- Variant jump.
- Exon jump.
- Base selection and range selection.
- Track toggles.
- No overlapping row text, codon labels, exon labels, or right-side metrics.

### Acceptance Criteria

- ABCA4 renders as one complete gene view.
- Scrolling remains usable on a normal desktop browser.
- No sequence rows drift horizontally or wrap inconsistently.
- Codon triplets remain aligned to three coding bases.
- Browser screenshot checks pass at desktop and narrowed widths.

### Source Reference

User direction on 2026-05-28: ABCA4 must prove large-gene handling.

### Verify

```powershell
cd app/web
./node_modules/.bin/tsc --noEmit
```

Run Browser or Chrome verification against the Workbench route with RPE65 and
ABCA4 fixtures. Capture screenshots for the full-gene top, queried variant,
distant exon, and colored-mode toggle.

### Out Of Scope

Mobile-first optimization, DMD-scale multi-megabase stress, and tool execution.

## Task FGV-008 - Tool Sequence-Mode Follow-Up

### Goal

After the full-gene viewer is tight, add the backend-led sequence-basis
contract that lets Primer, CRISPR, Align, and later Compare consume the same
sequence basis.

### Context

The user confirmed this should wait. The current tool panels can remain
mock-first or use existing endpoint contracts while the viewer is hardened.

### Relevant Files

- `plans/gene-viewer/plan.md` GV-007
- `app/backend/app/schemas/workbench.py`
- `app/backend/app/services/workbench_design.py`
- `app/backend/app/services/gene_viewer.py`
- `app/web/lib/backend.ts`
- `app/web/components/workbench/primer/**`
- `app/web/components/workbench/crispr/**`
- `app/web/components/workbench/align/**`

### Proposed Approach

Open a backend-led contract task only after FGV-001 to FGV-007 pass. Preferred
shape is still either:

- `sequence_mode: "reference" | "variant"`, or
- `viewer_context_id` for a saved/resolved viewer sequence basis.

The contract must preserve current tool defaults and add explicit sequence
selection only when the user chooses it.

### Acceptance Criteria

- Existing Primer, CRISPR, and Align requests remain valid.
- Tool requests can explicitly target reference or variant-applied sequence.
- Tool results identify the sequence basis they used.
- Frontend mirrors and backend contract tests are updated together.
- The full-gene viewer remains the source of visual truth for target selection.

### Source Reference

User direction on 2026-05-28 and `plans/gene-viewer/plan.md` GV-007.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_workbench_api.py tests/test_gene_viewer.py tests/test_frontend_contract.py -q
cd ../web
./node_modules/.bin/tsc --noEmit
```

### Out Of Scope

Real Primer-BLAST parity, genome-wide CRISPR off-target enumeration, TIDE
backend completion, and Compare implementation.

## Recommended Order

1. FGV-001 contract amendment.
2. FGV-002 backend fixtures and ABCA4 stress payload.
3. FGV-003 full-gene row renderer proof.
4. FGV-004 navigation and selection UX.
5. FGV-005 biological color policy.
6. FGV-007 ABCA4 browser/performance gate.
7. FGV-006 scratchpad persistence, unless notes saving becomes product urgent.
8. FGV-008 tool sequence-mode follow-up.

## Open Decisions

- TTL default for automatic edit logs: Codex recommendation is 48 hours, with
  a user setting for 24 hours later.
- Notes persistence target: local-only first, or authenticated backend storage
  from the start. Backend storage should be a separate approved task because it
  touches auth and durable user data.
- Full-gene orientation default: genomic plus/minus orientation versus
  transcript-readable orientation. Codex recommendation: genomic locus view
  with an obvious orientation toggle, because the product requirement is full
  genomic locus; protein view covers spliced product interpretation.
- Internal rendering strategy: DOM rows, canvas rows, or virtualization. Codex
  recommendation: preserve full-gene user semantics, then choose the renderer
  that keeps ABCA4 smooth.
