# Pass D — execution-ready build plan (interpretability)

> Code-verified against `app/web` on 2026-06-10 (subagent + main-agent). The spec
> `docs/workbench-interpretability/spec.md` is sound but its line numbers drifted;
> **build to the anchors here, not the spec's.** Three items: D-1 score bullets,
> D-2 Align lede, D-3 Design→Off-target bridge. Steven approved the sequence
> (part B polish → **pass D** → control-cleanup → overall cleanup → refactor/lint).

## Conventions
Score gauges use the **score palette** (`--teal-deep` / `--warn` / `--err`), NOT
`--cls-*` (those are ACMG verdicts — don't touch `lib/classification.ts`). Tokens
not hex; `.eamos-mock` for mock/illustrative; never touch the mono sequence viewer.
Hottest shared file = `workbench.css` (append-only, near the named anchors).

---

## D-1 — CRISPR score-bullet cells (value + tiny bar, magnitude legible in grayscale)

1. **New `app/web/components/workbench/ScoreBullet.tsx`** (presentational, no hooks).
   Props `{ value, min, max, thresholds:[lo,hi], sense:'higher-better'|'lower-better'|'band', display, muted?, title? }`.
   Render: a 2-col cell = right-aligned `display` (tabular-nums) + a ~6px track
   (`background:var(--bg-soft)`, inset `--line` border, min-width ~56px) with
   `color-mix` good/mid/bad zones from the thresholds + a 2px `--ink` value marker
   (`box-shadow:0 0 0 1.5px var(--bg)`, borrow from `ScoreScale.tsx:38` `ScorePin`).
   Number colour reuses `.score-good/mid/bad`. `muted` → marker+number `--ink-4` +
   dashed track (the `.eamos-mock` affordance; no chip pseudo-element in a table cell).
2. **`workbench.css`**: append a `.score-bullet` block right after `.score-good/mid/bad`
   (**~lines 2016-2018**; `.score-mid` now also has `font-weight:600`). Tokens only.
3. **`DesignTab.tsx`** (import `import { ScoreBullet } from '../ScoreBullet'`):
   - On-target cell **501-503** → `<ScoreBullet value={g.on_target_score} min={0} max={100} thresholds={[60,75]} sense="higher-better" display={g.on_target_score.toFixed(1)} muted={!providerDisclosure.sourceBacked}/>`.
   - Off-target cell **504-506** → `min={0} max={1} thresholds={[0.05,0.2]} sense="lower-better" display={g.off_target_score.toFixed(1)} muted={!providerDisclosure.sourceBacked}`. **Keep Design's own scale — do NOT unify with OffTargetTab's CFD scale.**
   - GC% cell **507** → `min={0} max={100} thresholds={[40,70]} sense="band" display={String(g.gc_percent)}`.
   - `<th>` On-target **462-464** text → `On-target (0–100)`; Off-target **465-467** → `Off-target (lower safer)` (keep the rich `title`s). `providerDisclosure.sourceBacked` is in scope (`:161`).
4. **`OffTargetTab.tsx`** (import ScoreBullet): Score cell **622-624** → `<ScoreBullet value={s.score} min={0} max={1} thresholds={[0.05,0.2]} sense="lower-better" display={s.score.toFixed(3)}/>` (no `muted` — panel self-discloses mock at 430-435). Pinned on-target **592** → full-bar bullet (value 1). `<th>Score` **570-572** → `Score (CFD 0–1)`.
- **Verify:** CRISPR→Design→design guides; bars render on on/off/GC; grayscale legible; Design 0–100 vs Off-targets 0–1 differ + headers state ranges; muted (local provider) shows dashed treatment.

## D-2 — Align result-card 3-tier hierarchy (lede → strip → caption)

In `align/PairwiseView.tsx`: add a `Lede` sub-component (Tier 1): big Identity
(`formatPercent(alignment.identity)`, ~18–20px), the active-diff clause
(`differenceLabel(alignment.differences[safeActive])`), exact-match → green
"Exact match — no mismatches or gaps" (`--teal-deep`/`--teal-tint`), `· N het` when
`hetIndices.size>0`, and the `◀▶` nav moved up (reuse `step`/`align-nav-btn` from
**83-96**). Remove Identity (`142-147`), Ref span (`174-178`), Read span (`179-183`)
from `Summary` (leaves Coverage/Matches/Mismatches/Gaps = 4 tiles). New order:
`<Lede/>` → `<Summary/>` strip → a muted `.align-spans-caption` (Ref/Read via
`formatRange`) → `<AlignedTrace/>` → `<DifferenceList/>`. Remove the standalone
diff-nav at **83-96**. `workbench.css`: append `.align-lede` + `.align-spans-caption`
near the align block (`.align-summary` **2149**, `.align-diff-current` **2272**,
`.align-diff-note.ok` **2207**). **Verify:** read with ≥1 diff = sentence, Identity
loudest, nav updates label; exact-match = green; spans = one muted caption line.

## D-3 — Design → Off-targets deep-link bridge

`CrisprPanel.tsx`: lift `screenSeed` state (the panel already has the `onSubTabChange`
hook from the auto-collapse work; add a `ScreenSeed {guide,pam,strand?,source}` +
`setTab('offtargets')`). `DesignTab.tsx`: add `onScreenGuide?` prop + a per-row
"Screen ↗" button after the Notes cell (**511**) reusing `.ots-export-btn`
(`workbench.css:2786`) + `IconScope` (`Icon.tsx:188`); new `<th>Screen</th>` after
**472**; bump empty-state `colSpan` **517** 10→11. `OffTargetTab.tsx`: add
`seed?`/`onSeedConsumed?`; **consume via the render-phase reset idiom (NOT a
useEffect — the spec is wrong here)** mirroring `ReadRow.tsx:50-55`:
```
const [seenSeed, setSeenSeed] = useState<ScreenSeed|null>(null)
if (seed && seed !== seenSeed) { setSeenSeed(seed); setGuide(seed.guide); setPam(seed.pam||'NGG'); if(seed.strand) setStrand(seed.strand); onSeedConsumed?.() }
```
Do NOT fabricate genomic chrom/pos from template-relative Design offsets — leave
defaults; render a `.help-note` (not `.eamos-mock`) "Seeded from {source}; set the
genomic locus before enumerating (Design positions are template-relative)", cleared
in `clearComputed` (**167**). **Verify:** Design "Screen ↗" → switches to Off-targets,
pre-fills guide+PAM, provenance note shows, editing clears it, no re-prefill on tab toggle.

## Shared-file conflict notes (now mostly resolved — those edits are committed)
`workbench.css` + `DesignTab.tsx` were the collision points with the primer/canvas
work; that's all committed (HEAD ≥ `93e9d45`), so Pass D can proceed. Order: D-1 → D-3
(both edit DesignTab — do together) → D-2. `tools.ts`, `WorkbenchShell.tsx`,
`SequenceViewerV2.tsx`, primer/* are NOT touched by Pass D.
