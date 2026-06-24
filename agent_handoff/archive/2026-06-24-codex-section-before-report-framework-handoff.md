# Archived: Codex `CURRENT.md` Section - Before Report Framework Handoff Refresh

Archived at 2026-06-24 00:04 +1000 by Codex before replacing the stale
2026-06-22 Codex section with the current ABCA4/report-framework handoff.

## Codex - Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule 1/2).
Section last edited: 2026-06-22 09:05 +1000 - Codex.

**Latest Codex update (2026-06-22 09:05 +1000 - Codex):**
Steven asked to pause after widening the protein-architecture fix into a
gene-agnostic Workbench contract cleanup. This is a break checkpoint only: no
source edits after the scope changed, no commit, no push.

Context read this session: `AGENTS.md`, handoff protocol/current state,
`agent_handoff/RISKS.md` matches for protein/viewer risk, `git status
--short --branch`, `python -m graphify query "Workbench transcript protein
sequence viewer hard coded sample scaffold gene agnostic API driven variant
architecture"`, and the uncommitted diff/component files around Report,
Workbench SidePanel, WorkbenchShell, ProteinView, SequenceViewerV2,
CodonDetail, and `gene-viewer-adapter`.

Current uncommitted implementation state from the carried frontend work:
`app/web/lib/protein-architecture.ts` centralizes protein feature lane/source
semantics; Report and Workbench adapter use it for primary protein architecture;
Workbench classification now requests `lookupSummary` alongside `/viewer`;
protein lollipop fill is classification-driven and shape is consequence-driven;
the side-panel class row was changed from hard-coded Likely Pathogenic to
`classLabel(qv.classification)`; Vercel guard script/package hooks were added;
root `.vercel` points to `eamos-dev` and nested `app/web/.vercel` was removed.

Important remaining work before verification/commit:
- Make Workbench transcript/protein/sequence UI fully gene-agnostic. Known hard
  spots: `SidePanel.tsx` still has fixed `VARIANT_LINKS` with ClinVar 99473;
  transcript UTR labels assume `exons 1-2` / last exon; exon table styling
  marks exons `3..5` as `in-window`; `SequenceViewerV2.tsx` and
  `ViewerToolbar.tsx` use RPE65 example placeholders/errors; `CodonDetail.tsx`
  draws the first protein domain across every sequence row instead of a
  coordinate-aware/API-derived domain overlay.
- Keep the design matched to the USH2A protein blocks. Do not invent a new
  motif/site/domain look.
- Preserve gene-agnostic behavior for RPE65, USH2A, BRCA1, BRAF, and CFTR.
- Before any push, delete or confirm removal of the accidentally-created
  remote Vercel `web` project; do not rely only on local guard files.

Verification status at break: earlier carried work had lint/build passing, and
browser/API checks showed RPE65/USH2A/BRCA1 report protein schematics behaving
as intended. After the latest SidePanel class fix and widened Workbench
gene-agnostic requirement, final browser verification has NOT been rerun.

Parked dirty files remain excluded from staging: `PROGRESS.md`,
`docs/proprietary/eamos-ai-gateway.md`, and
`scripts/eamos-encoding-scan.mjs`. Also stage intended files only; do not use
`git add -A`.

**Latest resume prompt:**
```text
# Resume prompt - 2026-06-22 09:05 +1000 - Codex protein architecture / Workbench gene-agnostic refactor paused
Eamos. Open D:\eamos. Read AGENTS.md, agent_handoff/README.md, agent_handoff/CURRENT.md (Codex section), agent_handoff/RISKS.md, then run git status --short --branch and inspect the uncommitted diff.
Delta: Protein architecture work is uncommitted. Report/Workbench now share normalized protein architecture semantics, lollipop colour/shape is dynamic, Workbench classification is summary-backed, and a Vercel project guard exists; no final commit/push yet.
Next: make Workbench transcript/protein/sequence views fully gene-agnostic: remove fixed SidePanel ClinVar link/UTR/exon-window assumptions, replace RPE65 search placeholders, and make the sequence domain row coordinate/API-driven or remove it when not supported.
Vercel gate: before any push, delete or confirm removal of the accidental remote `web` Vercel project; root `.vercel` must remain linked to `eamos-dev`.
Verify after fixes: browser-check /report and /workbench for RPE65 c.260A>G, USH2A c.2276G>T, BRCA1 c.5266dup, BRAF c.1799T>A, CFTR c.1521_1523delCTT; then run app/web lint, SG-target build, and python -m graphify update ..
Stage only intended protein/workbench/Vercel-guard files. Do not stage PROGRESS.md, docs/proprietary/eamos-ai-gateway.md, or scripts/eamos-encoding-scan.mjs. Commit only after verification. End clear-safe.
```
