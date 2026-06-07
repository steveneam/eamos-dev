# Workbench Align — stacked multi-read view (MSA) + manual shift

Status: **DRAFT for review** · Authored 2026-06-07 (Claude, FE) · FE-only, no contract change.

Steven's direction (2026-06-07) for the Align tool: move from today's *pairwise cards*
(template vs each read, each in its own card with its own chromatogram) to a **stacked
multiple-sequence view** — template on top, all reads below in **one shared coordinate
frame** — with cross-sequence selection, a compact (trace-hidden) mode, and **manual
left/right shifting** of reads to hand-align Sanger reads that don't start at the same place.

## Current state

- `AlignPanel` renders one `ReadRow` per read; each `ReadRow` → `PairwiseView` →
  `AlignedTrace` (template REF row + that read's row + its 4-channel trace).
- Each read is pairwise-aligned to the template **independently**; reads are not in a
  common column frame with each other.
- Orientation (4-way) + the per-read "Trace shown/hidden" toggle already exist.

## Target

A single **stacked alignment** under the reference:

```
        cols →  (template coordinate frame, one column per ref position)
REF     A C G T A C ...      ← template (top, pinned)
read1   A C G T A C ...      ← aligned, optional chromatogram
read2     G T A C ...        ← starts later; manual shift can nudge it
read3   A C G T A · ...
            ^ click/drag a column or region → highlight band spans ALL rows
```

### Features

1. **Shared-coordinate stack.** Project every read's alignment onto **template
   coordinates** so all rows share one column axis (template position = column). Reads
   that don't cover a column render a blank/gap there. Reuse `AlignedTrace`'s existing
   column model; the new work is laying multiple read rows in the same `<svg>`/grid.

2. **Cross-sequence selection.** Click a column (or drag a region) → a vertical highlight
   band spans the template **and every read row** (mirrors the gene-viewer selection band,
   extended down the stack). Shows the template coordinate(s) of the selection. Single
   shared selection state at the panel level.

3. **Compact mode (hide chromatograms).** A panel-level **"Compact / hide traces"** toggle
   collapses all per-read chromatograms so the base rows pack tightly and many reads are
   comparable at once. (The per-read trace toggle stays for individual control.) When traces
   are hidden, the scale handle is irrelevant and hidden (already gated on trace render).

4. **Manual horizontal shift per read.** Each read carries a **manual column offset**
   (default 0). Drag the read left/right (or − / + nudge buttons in the row header) to shift
   it within the shared frame, so the user can hand-align reads with different start points.
   - Offset is FE-only state per read; it shifts the read's bases **and** its trace together
     (the trace already warps to base columns, so it follows).
   - A small "shifted +N / −N" indicator + a "reset shift" affordance.
   - Auto-alignment still provides the starting position; manual shift is an override.

## Interaction / coordinate model

- One panel-level coordinate frame = template columns (+ space for read insertions, TBD:
  simplest v1 ignores read-only insertions in the stack, or renders them as widened
  columns; decide in Phase 1).
- Selection state: `{ startCol, endCol } | null` at `AlignPanel`, passed to all rows.
- Per-read manual offset: integer column shift stored on the read entry (FE only).
- Base spacing / horizontal scroll shared across all rows so columns line up.

## Phasing

- **Phase 1 — stacked view + cross-select + compact mode.** Lay reads in the shared frame,
  panel-level selection band across rows, global compact toggle. (No manual shift yet.)
- **Phase 2 — manual shift.** Per-read column offset via drag + nudge, indicator + reset.

## Open questions

1. Read-only **insertions** relative to the template — widen the column for all rows, or
   keep template-fixed columns and mark insertions inline? (Phase 1 decision.)
2. Manual shift granularity — whole columns only, or sub-column? (Recommend whole columns.)
3. ~~Keep the existing per-read **pairwise card** view as an alternative, or replace it?~~
   **DECIDED 2026-06-07 (Steven): coexist / toggle.** Keep both — a view switch between the
   per-read pairwise cards and the stacked MSA. Neither replaces the other.
4. Does manual shift feed back into the alignment stats, or is it purely visual? (Recommend
   visual-only in v1; stats stay from the engine alignment.)

## Guardrails

- FE-only; reuses the client aligner + `AlignedTrace` column model; no contract change.
- Honour `prefers-reduced-motion` for any drag animation; keyboard alternative for shift
  (nudge buttons) and for selection.
- Orientation direction glyphs (done 2026-06-07) live in the read row header.
