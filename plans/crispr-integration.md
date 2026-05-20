# CRISPR Integration Plan — Blueprints 1 & 2

> Created 2026-05-17 · Claude · planning artifact (new file — does not touch
> Codex's `plans/v2-backend.md` or any locked shared doc). Source material:
> the two CRISPR blueprint bundles under
> `…\variant-search-engine\CRISPR\` (Blueprint 1 = automated gRNA design;
> Blueprint 2 = post-CRISPR editing analytics) + their reference React
> dashboards, prompt notes, and the FastAPI-integration snippet.

## 1. What the source documents are

Two **distinct tools**, each with a Python engine scaffold + a generic
reference React dashboard:

| Blueprint | Tool | Stage | Engine logic (supplied) | Reference UI |
| --------- | ---- | ----- | ----------------------- | ------------ |
| **1** | gRNA **design** | pre-edit | PAM scan (`(?=([ATCG][ATCG]G))`) · Hsu (2013) off-target weight matrix · DeepHF (2019) BiLSTM on-target · Bowtie/BWA genome align · GFF3 exon filter | `GrnaDesignDashboard`: seq textarea → guide table w/ hover-to-map track, sort, min-spec slider |
| **2** | editing-outcome **analytics** | post-edit | TIDE Sanger NNLS deconvolution (Brinkman 2014) · CRISPResso2 NGS · SPROUT/inDelphi repair predictor | `CrisprAnalysisDashboard`: 2× `.ab1` upload → indel-spectrum bar chart (Observed vs AI), recharts |

The DeepHF BiLSTM and SPROUT/inDelphi nets are **architecture scaffolds only —
no trained weights are supplied**. The Hsu off-target, PAM scan, and TIDE NNLS
math is fully deterministic and implementable exactly as written.

## 2. Locked decisions (user, 2026-05-17)

1. **Scope:** both blueprints — Blueprint 1 built now, Blueprint 2
   scaffolded + planned now (backend deferred).
2. **Execution model:** parallel mode — Claude builds all `app/frontend/**`
   now, **mock-first** against the existing contract; the backend engine is
   delivered to Codex as the briefs in §6/§7 of this doc.
3. **Engine fidelity:** deterministic-first — Hsu + PAM + a transparent
   on-target heuristic. DeepHF / SPROUT ML deferred until weights are sourced.
4. **Blueprint 2 placement:** **sub-tabs inside the CRISPR tool**
   (`Design` | `Outcomes`). Rail stays at 5 tools; `TOOL_ORDER` unchanged.
5. **Charting:** hand-rolled SVG (matches the existing Workbench PhyloP
   bar-chart precedent — zero new frontend dependencies).

## 3. Why not drop the blueprint code in verbatim

The reference dashboards are generic full-page `slate-900` Tailwind pages with
their own `<header>`, raw `fetch('http://localhost:8000/...')`, inline mock
fallbacks, a `recharts` dependency, and contract shapes that differ from
Eamos's. Eamos requires:

- semantic-class design system (`workbench.css` + DESIGN.md tokens) — no
  Tailwind utility soup in Workbench components;
- the `lib/api.ts` client layer (`API_BASE_URL` + `parseResponse<T>`), not raw
  `fetch` in components;
- contract-first backend (`backend.ts` ↔ Pydantic, `test_frontend_contract.py`
  is the canary; contract changes are **backend-led**);
- hand-rolled SVG charts (no charting dep today).

→ The blueprint UIs are **reference designs**; we rebuild them as Eamos panels
against the existing `CrisprResponse` contract.

## 4. Contract reconciliation (surfaced for Codex — backend-led)

| Blueprint 1 field | Eamos `CrisprGuide` (`backend.ts:396`) | Note |
| ----------------- | -------------------------------------- | ---- |
| `spacer` | `guide` (+ `pam`) | direct |
| `position` | `cut_position` | semantics differ (spacer-start vs cut site) — Codex confirms |
| `deepHfEfficiencyScore` (↑ better) | `on_target_score` | direct |
| `hsuSpecificityScore` (**↑ better**, 0–100) | `off_target_score` (**↓ better** in fixture, 16.2 = good) | **direction mismatch — Codex decides**: either redefine `off_target_score` as Hsu specificity (↑ better) or add an additive `specificity_score` field. FE renders whatever the contract says; `test_frontend_contract.py` stays the canary. |

Blueprint 2 has **no existing contract** — new `CrisprTide*` schema +
`POST /api/v1/crispr/tide` (Codex, §7).

## 5. Phase A — CRISPR Design panel (Blueprint 1) · CLAUDE · build now

Mock-first against the existing `POST /api/v1/crispr` fixture
(`app/backend/app/fixtures/workbench/crispr_rpe65.json` — 3 guides + ssODN).
No contract edits from the frontend.

**New files**
- `app/frontend/src/components/workbench/crispr/CrisprPanel.tsx` — the panel
  shell with `Design` | `Outcomes` sub-tabs (Outcomes = §8 scaffold).
- `app/frontend/src/components/workbench/crispr/DesignTab.tsx` — form + gRNA
  table + ssODN block.
- `app/frontend/src/components/workbench/crispr/GuideTrack.tsx` — the
  blueprint's signature row-hover ribbon: maps spacer+PAM onto a mini
  sequence track from the gene-window context around `cut_position`.

**Edited files**
- `lib/api.ts` — add `designGuides(req: CrisprRequest): Promise<CrisprResponse>`
  (follow the `variantLookup`/`createRun` pattern: `API_BASE_URL` +
  `parseResponse`, `POST /api/v1/crispr`). Add `analyzeTide` stub for §8.
- `components/workbench/WorkbenchShell.tsx` — render `<CrisprPanel/>` into the
  existing empty `tool-panel[data-panel="crispr"]` slot (`WorkbenchShell.tsx:104`).
  Viewer stays visible above (DESIGN.md: Primer/CRISPR sit below the viewer;
  `viewerCollapsed` already false for `crispr`).
- `components/workbench/SidePanel.tsx` — add a `CrisprSide` branch (like
  `ViewerSide`) replacing the generic stub: editing strategy + target window +
  AI-assist chips (FE-6 spec).
- `styles/workbench.css` — panel / table / track / sub-tab styles using
  existing design tokens (no new Tailwind utilities).
- `plans/v2-frontend.md` — FE-6 CRISPR-slice progress note (at the verified
  boundary, under the Log Edit-Lock).

**Behaviour**
- Form → `CrisprRequest`: Cas enzyme (SpCas9/SaCas9/Cas12a) · strand filter
  (both/plus/minus) · off-target tolerance · target window (±bp, default ±10).
- gRNA table: `#` · guide(5′→3′)+PAM (accent-split: spacer teal / PAM rose,
  mapped to Eamos accent tokens) · cut pos · strand · on-target badge ·
  off-target/specificity badge (threshold-coloured) · GC% · notes.
  Recommended guide → ★ + teal-tint row (matches the PrimerPanel ★ convention
  from FE-6).
- Re-skinned blueprint interactions: row-hover → `GuideTrack`; sort toggle
  (on-target / off-target); min-score filter chip.
- HDR ssODN block from `CrisprResponse.ssodn`: 3 stacked monospace lines
  reference / variant / repair template; corrective bases teal, silent PAM
  edit indigo, target base warn-tint; arm lengths + estimated HDR efficiency.

**Verify (all green before "done")**
- `cd app/frontend && npx vitest run` — green (+ any new pure-logic tests, e.g.
  guide-track mapping).
- `cd app/frontend && npm run build` — `tsc -b` + vite clean.
- `cd app/backend && python -m pytest tests/test_frontend_contract.py -q` —
  40/40 (untouched — proves no FE-side contract drift).
- Browser pixel-check at `/workbench` CRISPR tab (Chrome DevTools MCP):
  table renders from the fixture; ★ row highlights; row-hover maps the
  ribbon; sub-tabs switch; ssODN colour-coding correct; viewer still visible
  above; no horizontal scroll.

## 6. Phase B — Codex backend brief: real CRISPR design engine (M-002D)

> Codex-lane, backend-led, gated on this plan's approval. Codex owns
> `app/backend/**` + `plans/v2-backend.md` + `schemas/workbench.py`. This is
> the precise ask; a one-line pointer goes in `## Cross-Agent Requests`.

- **Provider seam:** behind the existing `/api/v1/crispr` provider boundary in
  `app/backend/app/services/workbench_design.py`, mirroring the Primer M-002C
  pattern (opt-in env var, e.g. `CRISPR_PROVIDER=…`; fixture mode is the
  unchanged default; structured Workbench HTTP errors —
  `503 workbench_provider_unavailable` / `:failed`).
- **PAM scan (enzyme-aware):** SpCas9 `NGG`, SaCas9 `NNGRRT`, Cas12a `TTTV`
  (5′ PAM). Scan both strands; extract the enzyme-appropriate spacer with
  strand + coordinates resolved against the M-002A sequence context.
- **Off-target = Hsu (2013), deterministic.** Use the supplied weight vector
  and `Hsu = 100 / (100 + Σ Wᵢ)` exactly as in
  `# Blueprint for an Automated CRISPR 1.txt §3` (also coded in its §5
  scaffold). Off-target candidate enumeration: a deterministic in-context /
  provided-reference scan first; genome-wide Bowtie/BWA is a documented
  follow-up (no genome assets bundled — same constraint as M-002C isPcr).
- **On-target = transparent heuristic first** (GC band, poly-T `TTTT`
  penalty, position rules). **DeepHF BiLSTM explicitly deferred** — the
  scaffold has no trained weights; do not ship random-weight inference.
- **Contract decision (Codex owns):** resolve the off-target-direction
  mismatch in §4 (redefine `off_target_score` ↑-better, or add additive
  `specificity_score`). Whatever ships, update `schemas/workbench.py` +
  `backend.ts` together and keep `test_frontend_contract.py` green.
- **Acceptance:** fixture mode byte-unchanged; real mode returns
  source-backed guides, a valid empty-guide result, or a documented HTTP
  error; deterministic unit tests for PAM scan + Hsu math (assert against
  the blueprint's worked weights); opt-in smoke documented.
- **Out of scope:** clinical-editability claims, genome-wide off-target
  completeness, DeepHF weights.

## 7. Phase C — Codex backend brief: post-CRISPR TIDE analytics (new task)

> New backend milestone (suggest "M-002I — TIDE/outcome analytics"). Codex
> proposes the exact task id in `plans/v2-backend.md`.

- **New endpoint:** `POST /api/v1/crispr/tide` (multipart: `control_file`,
  `edited_file`, `cut_site_index` query, default 100). New
  `CrisprTideRequest`/`CrisprTideResponse` schema +
  `backend.ts` mirror (backend-led).
- **TIDE NNLS deconvolution — deterministic, implementable now.** Exactly the
  Brinkman (2014) math in `# Blueprint …Analytics Engine 2.txt §2/§5`:
  build the shifted-control matrix `A`, solve `min‖Ax−E‖₂, x≥0` with
  `scipy.optimize.nnls`, normalise to an indel-frequency spectrum, derive
  overall efficiency + residual.
- **AB1 ingestion:** shares the AB1 reader with **M-002E** (alignment AB1
  parsing) — coordinate so there is one AB1 parser, not two. Malformed /
  unsupported input → structured `422`.
- **SPROUT/inDelphi repair predictor deferred** (no weights). Response keeps a
  `predicted` series slot the FE can render once a model is sourced; until
  then it is `null`/omitted and the FE shows observed-only.
- **CRISPResso2 NGS path:** out of scope for the first slice (Sanger/TIDE
  only); note as a follow-up.
- **Acceptance:** deterministic TIDE unit tests (synthetic control/edited
  signals → known indel spectrum); fixture/demo mode for empty input;
  structured errors; contract green.

## 8. Phase C(fe) — Outcomes sub-tab scaffold · CLAUDE · build now (mock-first)

- `crispr/OutcomesTab.tsx` rendered by the `Outcomes` sub-tab in
  `CrisprPanel.tsx`: two `.ab1`/JSON drop inputs + a "Cas9 cleavage base
  index" numeric (default 100) + Run.
- `crispr/IndelSpectrum.tsx` — **hand-rolled SVG** grouped bar chart
  (Observed vs AI-Predicted), styled like the Workbench PhyloP chart;
  efficiency + residual callouts.
- Wired via `lib/api.ts` `analyzeTide(...)` → `POST /api/v1/crispr/tide`,
  **mock-first** against a new `lib/workbench/crispr-tide-sample.ts` (shape
  transcribed from Blueprint 2's reference response) until §7 lands. When the
  real endpoint exists and `predicted` is null, render observed-only.
- Same verification gates as §5.

## 9. Execution order & status

1. **§5 Phase A** (Claude) — ✅ **DONE + verified** 2026-05-17 23:47 +1000
   (Session 26). Mock-first on the existing `CrisprResponse` contract; vitest
   42/42, build clean, contract 40/40 untouched, browser pixel-check.
2. **§8 Phase C(fe)** (Claude) — ✅ **DONE + verified** same session. TIDE
   shape FE-local (`lib/workbench/crispr-tide-sample.ts`, Rule 5) until §7.
3. Codex briefs filed at the verified boundary under the Log Edit-Lock:
   **§7 TIDE** = `[OPEN] Claude→Codex` in `agent_handoff/CURRENT.md`
   → `## Cross-Agent Requests` (pointer here). **§6 NOT filed** — Codex
   already shipped the gRNA design engine as backend **M-002D** in parallel
   (idle/verified @ 2026-05-17 23:44), so a §6 brief is redundant.
4. **§6 backend** = Codex **M-002D — done**. **§7 backend** (TIDE
   endpoint) — Codex-lane, gated; FE is mock-first and not blocked.

Status note: the §4 off-target-direction reconciliation + the
`cut_position`-semantics question (see §5 / `crispr-guide-map.ts` header)
are now Codex/M-002D contract calls — FE renders whatever the contract says
and `test_frontend_contract.py` stays the canary.

Parallel-mode discipline: Claude never edits `app/backend/**`,
`plans/v2-backend.md`, or Codex's `CURRENT.md` section; contract shape stays
backend-led; log/handoff edits only at verified boundaries under the Log
Edit-Lock with real `Get-Date` stamps.

## 10. Open risks

- Off-target-direction contract mismatch (§4) — must be resolved before FE
  badge semantics are final; FE builds against the current fixture meaning
  until Codex decides.
- No ML weights → on-target/repair scores are heuristic/observed-only in v1;
  must be labelled as such in the UI (no false "AI prediction" where there is
  none).
- AB1 parser shared between TIDE (§7) and M-002E — coordinate to avoid two
  parsers.
- `recharts` deliberately **not** added — Outcomes chart is hand-rolled SVG.
