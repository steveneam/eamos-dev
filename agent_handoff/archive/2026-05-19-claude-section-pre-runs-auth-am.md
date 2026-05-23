# Archived verbatim — Claude `CURRENT.md` section pre-(runs-auth + AlphaMissense-hold)

Archived 2026-05-19 13:59 +1000 · Claude (README Hard Rule 1/9: append+archive
before replacing the Claude section). Superseded by the runs-auth +
AlphaMissense-on-hold state. Full GV-005/006 detail also lives in
`~/.claude/plans/next-session-eamos.md`.

---

## Claude — Last Task & Resume

Owner-written by **Claude only**. Codex: read, never rewrite (README Rule 2).
Section last edited: 2026-05-19 09:38 +1000 · Claude. Prior FE-6 Primer
section archived verbatim →
`agent_handoff/archive/2026-05-19-claude-section-pre-gv006.md` (Rule 1/9);
incremental detail + gotchas in `~/.claude/plans/next-session-eamos.md`.

**GV-005 + GV-006 — DONE + verified (2026-05-19, user-directed; user-chosen
hybrid adapter + Option-B viewer layout). `plans/gene-viewer/{spec,plan}.md`.**
GV-005: TS mirror of `app/backend/app/schemas/gene_viewer.py` appended to
`lib/backend.ts` (exact Pydantic names; FE mirrors, never reshapes — Codex
owns shape); `getGeneViewer()` in `lib/api.ts` (mock-first → sample on
transport failure, mirrors `designPrimers`); new
`lib/workbench/gene-viewer-sample.ts` (byte-faithful `viewer_rpe65.json`
transcription) + `gene-viewer-adapter.ts` (pure: backend-authoritative for
window/variant/sequence/segments/in-window-ClinVar/protein-features;
RPE65_V2 sample scaffold ONLY for exon/intron/conservation;
`geneViewerScaffoldWarnings()` names the scaffolded fields honestly) +
`gene-viewer-adapter.test.ts` (**20 cases**). GV-006: `WorkbenchShell`
loads via `getGeneViewer`→`adaptGeneViewer` (instant sample render → effect
refines; reachable-error keeps sample, no blank); `[Reference|Variant]`
allele pill in `CanvasHeader` (viewer-only, default reference per spec);
detail-pane `[Sequence|Protein]` switch in `SequenceViewerV2` (minimap stays
= genomic overview); new `viewer/ProteinView.tsx` (backbone + domain bars +
region/point features + domain-aware ClinVar lollipop, **uniform marker
size — no frequency implication**, splice/intronic excluded+listed, queried
emphasized at aa87). FE-5.6 Unit-E synthetic baseline overlay **superseded**:
the displayed allele is now adapter-driven; `CodonDetail` reconstructs the
queried codon's ref→alt badge from `data.queriedVariant` (user edit takes
precedence). CSS reuses the proven `.sv-strand-pill` idiom + new `.sv-pv-*`.
Verified: **vitest 73/73** (+20 adapter), **build clean** (tsc -b + vite,
chunk advisory only), **contract 40/40** (unchanged — Codex extends the
viewer canary, filed). **Browser pixel-check** at `/workbench`: reference
codon 87 = D(Asp)/c.260 A; Variant toggle → codon 87 G(Gly) + Asp old-badge
/ c.260 G, side-panel labels preserved; Protein view domain bar + 4
lane-stacked lollipops (queried ringed) + honest legend; minimap preserved
both modes; Primer panel renders below the viewer; only console error =
expected mock-first `ERR_CONNECTION_REFUSED` (no backend). Dev server
stopped (port 5173 free).

**Carry-forward (uncommitted):** GV-005/006 + FE-6 Primer + CRISPR FE +
FE-5.6 (all verified, Claude lane). Gotchas in
`~/.claude/plans/next-session-eamos.md`. `E:\eamos_nm_broken_DELETE_AFTER_REBOOT`
still pending a reboot delete.

**Next (all gated — explicit user direction):** commit the Claude-lane
checkpoint (gate lifted; mixed worktree → ask) · FE-7/8 · §7 TIDE FE wiring
when Codex ships `/api/v1/crispr/tide` · GV §6/§7 + viewer-payload
enrichment are Codex Cross-Agent Requests (FE not blocked, mock-first).

**Resume prompt:**
`# Resume prompt · 2026-05-19 09:38 +1000 · Claude (GV-005/006 DONE+verified)
Eamos. Read agent_handoff/README.md (protocol), agent_handoff/CURRENT.md
(## Claude + Locks + Requests), agent_handoff/RISKS.md (Dirty Worktree = git
policy), ~/.claude/plans/next-session-eamos.md, then git status --short
--branch. Delta: GV-005 + GV-006 DONE+verified. Next (all gated): commit
checkpoint / FE-7/8 / §7 TIDE wiring. Stop any dev server before /clear.
End clear-safe.`
