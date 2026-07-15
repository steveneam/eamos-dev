# Primer Integration Plan — FE-6 Primer panel

> Created 2026-05-18 · Claude · planning artifact (new file — does not touch
> Codex's `plans/v2-backend.md`, `app/backend/**`, or any locked shared
> handoff doc). Source material: the two documents under
> `…\variant-search-engine\Primers\`:
> - `AI Webtool Infrastructure Local Primer.txt` (backend infra)
> - `Frontend UI-UX Specification AI Genomic Primer Dashboard.txt` (FE brief)
>
> Companion to `plans/crispr-integration.md` (same parallel-mode, mock-first,
> contract-frozen discipline) and completes the still-Pending **Primer** half
> of `plans/v2-frontend.md` FE-6 (the CRISPR slice is already DONE+verified).

## 1. What the source documents are

| Doc | Owns | Status |
| --- | ---- | ------ |
| `AI Webtool Infrastructure Local Primer.txt` | Backend: local UCSC primer specificity (hgPcr/`.2bit`), Primer3, async FastAPI | **Already satisfied by Codex** — see §2 |
| `Frontend UI-UX Specification AI Genomic Primer Dashboard.txt` | Frontend: dashboard visual language, layout, interaction states, 3-layer result card, micro-UX | **This plan** (FE-6 Primer) |

## 2. The backend is already DONE and FROZEN (do not rebuild it)

Codex shipped the full primer backend as **M-002C** (backend-verified). The
infra doc's ask is implemented behind a provider seam:

- **`POST /api/v1/primer`** (`app/backend/app/api/routes/workbench.py:50`) —
  `PrimerRequest` → `PrimerResponse`.
- **Contract** (`app/backend/app/schemas/workbench.py`, mirrored in
  `app/frontend/src/lib/backend.ts`):
  - `PrimerRequest`: `gene, cdna, mode(sanger|qpcr|arms), tm_min(58),
    tm_max(62), product_size_min(300), product_size_max(700), avoid_snps(true)`
  - `PrimerPair`: `index, forward, reverse, tm_forward, tm_reverse,
    gc_forward, gc_reverse, product_size, specificity_hits, notes,
    recommended`
  - `PrimerResponse`: `mode, pairs[]`
- **Providers** (`app/backend/app/services/workbench_design.py`):
  - Fixture mode (default, `USE_REAL_APIS=false`): serves
    `app/backend/app/fixtures/workbench/primer_rpe65.json` (3 pairs, pair #1
    `recommended:true`).
  - Real mode: local **Primer3** (`primer3-py`) — Tm/GC/structures via
    Primer3 globals.
  - Specificity is pluggable via `PRIMER_SPECIFICITY_PROVIDER`:
    `template` (default, exact in-template amplicon screen) or
    **`ucsc_ispcr`** (local UCSC **isPcr** whole-genome screen against
    `hg38.2bit`). The infra doc asked for `hgPcr`; Codex correctly used
    **isPcr** — `hgPcr` is the web-CGI behind the UCSC form, `isPcr` is the
    standalone batch binary appropriate for local execution. Local-asset/host
    limitations are tracked in `docs/operations/risks-and-guardrails.md` (M-002C).
  - ARMS real-mode → structured `422 input_unsupported:primer_mode_arms`.
  - SNP masking not implemented even when `avoid_snps=true` (the `notes`
    string says so).
- The `notes` field already carries the specificity provenance prose:
  provider, product sizes, whether the product spans the queried base, and a
  "not an NCBI Primer-BLAST validation" caveat.

→ **Frontend builds mock-first against this frozen contract — zero
contract/schema edits — exactly the CRISPR-slice pattern.**
`test_frontend_contract.py` stays the drift canary (must stay 40/40,
untouched).

## 3. Why not drop the UI-UX doc in verbatim

The doc specifies a **standalone dark "developer dashboard"** (slate-950
canvas, emerald accent, JetBrains Mono, its own 2-column 100vh page with a
left genome/sequence input pane). Eamos Workbench is a **light semantic-class
system** (`styles/workbench.css` + DESIGN.md tokens; "never Benchling
rainbow", muted ~25% chroma), and Primer is **one tool panel inside the shared
Workbench shell**: it sits in the `tool-panel[data-panel="primer"]` slot
**below the persistent Sequence Viewer**, with the shared `CanvasHeader` +
`SidePanel` + `ContextStrip` chrome, and gene/cdna context is already threaded
in from the resolved variant (no left input pane — the doc assumed a
standalone tool).

This is the identical tension `crispr-integration.md §3` resolved. **Locked
decision (user, 2026-05-18): Adapt — rebuild the doc's *ideas* as an Eamos
panel, mirroring `CrisprPanel`.** The doc's structure and micro-UX are
honoured; its dark visual language is translated into Eamos light tokens
(emerald → `--teal`/`--teal-deep`/`--teal-tint`; slate → ink tokens).

**Upgrade (user, 2026-05-18, follow-up):** the user liked the dashboard
*feel* and asked for it to be codified. `DESIGN.md` now carries a
**Dashboard Interaction Language** (five principles + global `--elev-*`
elevation scale + tokenized `--dur-*`/`--ease-*` motion + affordance
cheat-sheet + `prefers-reduced-motion` guard; elevation relaxed **globally**
across v2 surfaces, motion = tokenized micro-interactions). **The Primer panel
is its first reference implementation** — the 3-layer card is the canonical
progressive-disclosure exemplar; later CRISPR/Align/Compare/Report modules
migrate to it as their own gated passes. So this is no longer "flat panel that
merely echoes the doc": it is the doc's dashboard *qualities* expressed
through the new DESIGN.md tokens, staying light and clinical. The doc's
**emoji** (🟢🟡🔴, ⚡, 📋) are **not** adopted — DESIGN.md's no-emoji rule
stands; badges use the existing dot+label pill pattern (§5.1).

## 4. Locked decisions (user, 2026-05-18)

1. **Aesthetic:** Adapt the doc into an Eamos light Workbench panel (mirror
   `CrisprPanel`); viewer stays visible above. Not the literal dark
   dashboard, not a hybrid dark-results-area. **The premium dashboard feel
   is delivered via the new `DESIGN.md` Dashboard Interaction Language**
   (global `--elev-*` elevation, `--dur-*`/`--ease-*` motion, the 3-layer
   progressive-disclosure pattern, affordance cheat-sheet) — Primer is its
   first reference implementation. Clinical core (hairlines, muted palette,
   semantic colours, no weight > 700, no emoji) is unchanged.
2. **Specificity Layer-3 depth:** Render from the frozen contract now
   (`specificity_hits` + parsed `notes` prose). **Separately file a GATED
   Codex brief** for an optional *additive* raw-specificity field (§6) —
   same backend-led, no-block pattern as `crispr-integration.md §7` TIDE.
3. **Loading state:** Honest. Button `Designing…` + a static labelled phase
   list (Constraints · Primer3 thermodynamics · Specificity screen) shown
   "in progress", all resolving together on the single response. **No
   simulated per-stage timers** (the doc's animated ticker would be theatre
   not backed by real progress events — the false-signal trap
   `crispr-integration.md §10` warns against).
4. **Presentation:** 3-layer progressive-disclosure **cards** (per the doc),
   not the dense output table the older `v2-frontend.md` FE-6 prose mentions.
   Conscious, documented deviation — the doc is the fresher brief and the
   CRISPR slice already evolved beyond "table" with user approval. The ★
   recommended-pair convention is preserved (teal-tint card).
5. **No new dependencies** — hand-rolled tooltip/gauge/card (matches
   `crispr-integration.md §3`; no charting/tooltip libs).

## 5. Phase A — Primer panel · CLAUDE · build next session (mock-first, gated)

Mock-first against the existing `POST /api/v1/primer` fixture. No contract
edits from the frontend. Mirrors the CRISPR slice file-for-file.

### New files

- `app/frontend/src/components/workbench/primer/PrimerPanel.tsx` — panel
  shell: header (title/sub), **mode segmented control** (Sanger | qPCR |
  ARMS), constraint form, a primary `Generate & Validate` button (the
  heaviest element in the form region — Dashboard principle #2; no emoji),
  the three interaction states (empty / honest-loading / results feed),
  error + ARMS-not-implemented states. Result cards enter with the
  `--dur-2`/`--ease-standard` staggered reveal (capped ~240 ms).
- `app/frontend/src/components/workbench/primer/PrimerResultCard.tsx` — the
  **canonical reference implementation of the DESIGN.md 3-layer
  progressive-disclosure pattern** (`.card--interactive`: rests `--elev-1`,
  rises to `--elev-2` on hover/focus-within via the motion tokens; still
  hairline-bordered):
  - **Layer 1 — decision surface (always visible):** specificity badge
    (taxonomy §5.1) + "Primer pair #N" + `★` if `recommended` + **Copy pair**
    button (clipboard, order-ready `F:…\nR:…`, graceful fallback). One-glance
    verdict in < 200 ms.
  - **Layer 2 — primary detail (always visible):** Forward / Reverse mono
    sequence chips (select-all on click) + bold `Tm` / `GC%` per primer +
    `Product: N bp`. ΔTm gauge (§5.1).
  - **Layer 3 — deep dive (hidden by default):** a `<details>`/summary
    disclosure (chevron `transform: rotate`, height+opacity reveal via
    `--dur-2`/`--ease-emphasized`) — left: thermodynamic profile (Tm pair,
    GC pair, ΔTm, product size); right: parsed specificity prose
    (provider · product sizes · spans-queried-base · Primer-BLAST caveat),
    with explainer `(?)` tooltips. The summary row is the affordance.
- `app/frontend/src/lib/workbench/primer-sample.ts` — **byte-faithful**
  transcription of `app/backend/app/fixtures/workbench/primer_rpe65.json`
  (mock-first fallback; mirrors `crispr-sample.ts`; no divergence from the
  backend fixture).
- `app/frontend/src/lib/workbench/primer-metrics.ts` (+
  `primer-metrics.test.ts`) — the **pure, testable core**:
  - `classifyPair(pair) → { badge, deltaTm, deltaTmWarn }` — badge taxonomy
    §5.1; `deltaTm = |tm_forward − tm_reverse|`, `deltaTmWarn = deltaTm > 2`.
  - `parseNotes(notes) → { provider?, productSizes?, spansTarget?,
    primerBlastCaveat?, raw }` — **defensive**: regex extraction with a
    raw-string fallback. `notes` wording is a soft contract (prose, not
    schema); the parser must never throw and must degrade to showing `raw`
    if patterns don't match.

### Edited files

- `app/frontend/src/lib/api.ts` — add
  `designPrimers(req: PrimerRequest): Promise<PrimerResponse>`, exactly
  mirroring `designGuides` (POST `/api/v1/primer` via `API_BASE_URL` +
  `parseResponse`; transport `TypeError` → `PRIMER_SAMPLE` mock fallback; a
  reachable backend that errors still surfaces the error).
- `app/frontend/src/components/workbench/WorkbenchShell.tsx` — render
  `<PrimerPanel gene={DATA.gene} cdna={…} />` into the existing empty
  `tool-panel[data-panel="primer"]` slot (the
  `{/* FE-6 (primer) … */}` placeholder). Reuse the existing
  gene/cdna-from-context derivation (the `CRISPR_CDNA` expression — generalise
  the const name to a shared `QUERY_CDNA`, surgical rename).
- `app/frontend/src/components/workbench/SidePanel.tsx` — add a `PrimerSide`
  branch replacing the generic stub (mirrors `CrisprSide`): primer mode info
  + target context (gene/exon/cdna) + AI-assist chips (FE-6 spec).
- `app/frontend/src/styles/workbench.css` — Primer styles reusing existing
  tokens (`.tool-panel-head/.tool-form/.field/.btn-teal/.seg/.help-note/
  .score-good|mid|bad`) **plus the new DESIGN.md tokens**: depth only via
  `--elev-*` (no ad-hoc `box-shadow`), transitions only via
  `--dur-*`/`--ease-*`, and the global `prefers-reduced-motion` guard must be
  present (add to `index.css` if not already there). New primer-specific
  only: 3-layer card (`.primer-card` built on `.card--interactive`, layer
  rows, `<details>` drawer), badge pills (dot+label, §5.1 — no emoji), ΔTm
  gauge colour states, copy-pair button, `.primer-tip` explainer tooltip
  (`:hover`/`:focus-within`, no JS lib). Light tokens only — no dark canvas.
  Mirror the CRISPR CSS block's "Reuses …" comment header.
- `plans/v2-frontend.md` — FE-6 Primer-slice progress note, **only at the
  verified boundary, under the Log Edit-Lock** (gated; next session).

### 5.1 Badge taxonomy (doc → frozen contract)

The doc's pill *concepts* map onto contract fields (no recompute of
`recommended` — the backend already picks the first 1-hit/1-intended pair).
Rendered as the existing **dot+label pill** (`<ClassificationBadge>`-style:
`2px 9px`, radius 4px, 0.5px border, status-token bg/text/dot) — **no
emoji** (DESIGN.md):

| Badge (label · tone) | Condition on `PrimerPair` |
| -------------------- | ------------------------- |
| **Specific** · benign/teal tone | `specificity_hits === 1` **and** `notes` indicates the product spans the queried base **and** no thermo flag |
| **Thermo warning** · `--warn` tone | `specificity_hits === 1` **but** a thermo flag (`deltaTm > 2°C`, or GC outside 35–70, or `notes` flags a warning structure) |
| **Off-target risk** · `--err` tone | `specificity_hits > 1` |
| **Check orientation** · `--warn` tone | `specificity_hits === 0` — surfaced **distinctly** (the infra doc's hgPcr-quirk note: 0 hits ⇒ "validate primer orientation", not silently "not specific") |

`recommended === true` → a leading `★` glyph (text, not emoji — matches the
existing CRISPR `★` convention in `DesignTab.tsx`) + `--teal-tint` card
background + the card is the one focal point in the feed (Dashboard
principle #2: one focal point per region).

### 5.2 Micro-UX from the doc, adapted

- **ΔTm gauge:** `|tm_forward − tm_reverse| > 2°C` → the numeric readout
  shifts grey → amber (computed in `primer-metrics`, unit-tested).
- **Explainer tooltips:** hover/focus `(?)` on Specificity / Tm / GC% /
  Product → micro-popover copy (hand-rolled `.primer-tip`, `aria-describedby`,
  keyboard-reachable).
- **Copy Pair:** Layer 1 → `navigator.clipboard.writeText` (order-ready
  format); graceful no-op + visual fallback if clipboard unavailable.
- **Paste sanitation — N/A (documented divergence):** the doc assumed a
  standalone tool with a raw-sequence paste box. The Eamos panel sources the
  template from the already-resolved gene/cdna context (viewer/URL), so there
  is **no free-sequence textarea** to sanitise. A "bring-your-own-template"
  affordance is out of scope (future extension).
- **ARMS mode:** the tab is selectable; on Generate, real mode returns the
  structured `422 …primer_mode_arms` → render a clean
  "ARMS real-mode design isn't implemented yet (backend M-002 follow-up)"
  state, **not** a raw error toast. In offline/mock mode the fixture is
  `mode:"sanger"`; if ARMS is selected the mock still returns the Sanger
  fixture — show a note that the demo serves the Sanger fixture.

### Verify (all green before "done"; mirrors `crispr-integration.md §5`)

- `cd app/frontend && npx vitest run` — green (+ `primer-metrics.test.ts`:
  fixture pair #1 → **Specific**; pair #3 (2 hits) → **Off-target risk**;
  synthetic ΔTm>2 → **Thermo warning** + amber gauge; 0-hit → **Check
  orientation**; malformed `notes` → `raw` passthrough, no throw).
- `cd app/frontend && npm run build` — `tsc -b` + vite clean.
- `cd app/backend && python -m pytest tests/test_frontend_contract.py -q` —
  40/40 (untouched — proves no FE-side contract drift).
- **DESIGN.md conformance grep:** no ad-hoc `box-shadow:` outside `--elev-*`,
  no `transition`/`animation` outside `--dur-*`/`--ease-*`, the
  `prefers-reduced-motion` guard present, no emoji in the panel.
- Browser pixel-check at `/workbench` Primer tab (Chrome DevTools MCP):
  cards render from the fixture; ★ recommended card is teal-tinted, first,
  and the single focal point; **interactive cards lift `--elev-1`→`--elev-2`
  on hover (and only interactive ones)**; the 3-layer `<details>` reveal
  animates (chevron rotate + height/opacity) at `--dur-2`; specificity
  badges correct (pair #3 → Off-target risk pill); Copy pair writes the
  clipboard; explainer tooltips open on hover+focus; honest loading shows the
  static phase list then the feed; ARMS shows the not-implemented state;
  **with OS "reduce motion" on, transitions collapse but the UI is fully
  usable**; **viewer still visible above; no horizontal scroll.**

## 6. Phase B — Codex backend brief: additive raw-specificity detail (gated)

> Codex-lane, backend-led, **gated**. Filed as `[OPEN] Claude→Codex` in
> `agent_handoff/CURRENT.md` → `## Cross-Agent Requests` (pointer here)
> **only at the Phase-A verified boundary, under the Log Edit-Lock, and only
> when Codex's lock is free** — exactly the `crispr-integration.md §7`
> pattern. FE stays mock-first and is **not blocked** by this.

- **Additive only.** A new optional field (e.g.
  `PrimerPair.specificity_detail: list[SpecificityProduct] | None`) carrying
  the per-product data the local `isPcr` provider **already computes
  internally** but currently collapses into `specificity_hits` + `notes`
  (`IsPcrProduct` dataclass in `workbench_design.py`: `chrom, start, end,
  strand, size, spans_target`). Template-provider mode → `null`/omitted.
- Backend-led: `schemas/workbench.py` + `backend.ts` updated together;
  fixture byte-unchanged; `test_frontend_contract.py` stays green.
- **FE follow-on (own slice):** when present, Layer 3 gains a "raw genomic
  proof" column (chrom:coords ± strand, product sizes, target-spanning) and
  an amplicon-on-template mini-track (the GuideTrack analog — deferred to
  here because honest coordinates require this field; no synthetic
  coordinates in Phase A). When absent → the parsed-`notes` prose (Phase A).
- **Out of scope:** NCBI Primer-BLAST parity, genome-wide completeness, SNP
  masking, ARMS real-mode (separate M-002 approvals — see
  `docs/operations/risks-and-guardrails.md` M-002C).

## 7. Execution order & status

1. **§5 Phase A** (Claude, FE, mock-first) — **GATED on user approval; build
   next session.** No code written this session (planning only).
2. **§6 Phase B** Codex brief — filed at the Phase-A verified boundary,
   gated; FE not blocked.
3. Parallel-mode discipline (same as CRISPR): Claude never edits
   `app/backend/**`, `plans/v2-backend.md`, or Codex's `CURRENT.md` section;
   contract shape stays backend-led; shared log/handoff edits only at
   verified boundaries under the Log Edit-Lock with real `Get-Date` stamps.
   This planning doc is a new file in Claude's lane (precedent:
   `crispr-integration.md`) and touches no shared/locked doc — Codex
   currently holds the Log Edit-Lock (active on GV-003/004).

## 8. Open risks

- **DESIGN.md elevation relaxed *globally* (user choice) — large latent blast
  radius.** Mitigation/guardrail: the new language is **opt-in by milestone**.
  Primer is the first reference implementation; **shipped panels
  (Viewer/CRISPR, Report v2 modules) are NOT retro-restyled in this slice** —
  each migrates as its own gated pass (stated in DESIGN.md "Adoption order").
  The next session must not "modernise everything" off the back of this.
- **`notes` is prose, not schema.** The `primer-metrics.parseNotes` regex is
  the main fragility — it must be defensive (raw-string fallback, never
  throws). If Codex re-words `notes`, the panel degrades to raw display, not
  a crash. The §6 additive field is the durable fix.
- **ΔTm>2 not exercisable from the current 3-pair fixture** (all pairs within
  2°C). Logic is unit-tested instead; the mock stays byte-faithful to the
  backend fixture (CRISPR precedent — do **not** diverge the mock to force a
  visual). Note in the pixel-check that the amber path is covered by vitest.
- **ARMS / 0-hit paths** need explicit non-error states (§5.2) — not raw
  error surfaces.
- **Presentation deviation** from `v2-frontend.md` FE-6's "output table"
  wording is intentional (§4.4) — the v2-frontend FE-6 note should be updated
  to point here at the verified boundary.
- No new deps (no charting/tooltip lib) — hand-rolled, matches CRISPR §3.
