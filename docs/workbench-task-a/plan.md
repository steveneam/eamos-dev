# Task A — build plan: 3-column workbench canvas + bottom-left utility cluster

**Status:** 🟡 GATED SPEC — no `app/web/**` code lands until Steven OKs this plan.
This is durable, structural, cross-surface chrome ([[feedback_subagent_recommendations_not_authorization]]).

**What this is.** A single sequenced implementation plan that synthesises the three
design source-of-truth docs into one build order. It does **not** re-litigate the
design — those decisions are made:

- `docs/workbench-3col/spec.md` → **Option C**: one CSS-grid `.canvas` split `[viewer | tool-rail]`, reuse the `.wr-section`/`WorkRailSection` grammar for the rail's internal chrome, factor the collapse helpers out of `WorkRail.tsx` into a shared module.
- `docs/workbench-shell-chrome/spec.md` → a non-scrolling `.work-rail-foot` cluster: reuse `AuthMenu.tsx` wholesale (upward popover), a COMING-SOON `IconSparkle` Ask launcher (parked), scope Cite → `/report` (TopNav button + `useCiteModal` hook), Feedback → account menu, remove the global `<CiteChip>` mount.
- `docs/workbench-audit/shell-flow.md §4` → resolves every open question in both specs (answers reproduced in §0 below).

**Method honoured.** Repository/source inspection confirmed the canonical reuse set is
`WorkRail`/`WorkRailSection` (`components/layout/WorkRail.tsx`), `Icon.tsx`,
`LibrarySection`, and that **no** separate account/chat module exists to reuse
beyond `AuthMenu.tsx`. ui-ux-pro-max + frontend-design lenses are already baked
into the source specs; this plan does not redo them.

---

## 0. Decisions locked (from `shell-flow.md §4`) — do not re-open

These are the answers to the two specs' "Open questions for Steven." Build to them.

### 3-col canvas
| # | Decision |
| - | -------- |
| Default viewer state | Primer `expanded`, CRISPR `expanded`, Align `collapsed`. **CRISPR auto-`collapse`s when the Off-targets sub-tab is selected** (widest content). |
| Split ratio | **Fixed `--tool-rail-w` token first** (~50/50 expanded, ~30/70 collapsed). NO drag handle in v1. |
| Tool-rail collapsible? | **No** — only the centre viewer collapses. The tool rail is the active task. |
| CanvasHeader controls when viewer collapsed/hidden | **Hide** in `hidden`; **collapse into a stub overflow menu** in `collapsed` (opens at `--z-popover`). |
| `expand-tool-to-full` | **Yes** — a small maximise handle on the tool-rail head drives viewer → `hidden`, rail → full width. `IconExpand` (new, 1.75 family). |
| Narrow fallback (<900px) | **Revert to today's vertical stack** (viewer above, tool below). No third column below 900px. |

### Bottom-left cluster
| # | Decision |
| - | -------- |
| Ship account chrome before auth is live? | **Yes** — `AuthMenu` + `AuthProvider` already degrade gracefully (`configured===false`). |
| Global or workbench-first? | **Global** via `WorkRail` (shared by report/workbench/compare). |
| Billing/Settings items | My account → `/account`, **Billing → `/#pricing`**, **Send feedback**, Sign out. **No invented `/settings`.** |
| Where do Cite + Feedback land? | **Cite → `/report` TopNav button** (scoped, carries `?cite=1` + `CiteModal` via a `useCiteModal()` hook). **Feedback → "Send feedback" item in the account menu** (global mailto). |
| Mobile drawer-closed account | **Accept drawer-only for v1.** No nav-avatar fallback (would cost the two-place nav edit the rail-foot was chosen to avoid). |

---

## 1. Ground-truth corrections (verified against `app/web` this session)

The two feature specs were written before recent cleanups; several of their
`file:line` references have drifted or vanished. **Build against these verified
facts, not the stale spec line numbers.**

1. **The z-scale has SHIPPED.** `globals.css:190-197` defines
   `--z-track:5 / --z-rail:45 / --z-nav:50 / --z-scrim:55 / --z-drawer:60 /
   --z-popover:70 / --z-pill:100 / --z-modal:200`. `work-rail.css` already consumes
   them (`:52, :163, :175, :194`); the tracks dropdown uses `--z-popover`
   (`workbench.css:226`). **Adopt the existing scale — do NOT introduce or re-define it.**
2. **All workbench CSS is one file** — `components/workbench/workbench.css`. There
   are **no** per-tool `primer/crispr/align/*.css` files (the 3-col spec §6's
   "`primer|crispr|align/*.css`" map is wrong). All panel rules live in the monolith.
3. **The `.align-source-grid` / `.align-input-row` / `.align-source-stats` rules the
   3-col spec §5 cited (`workbench.css:2018-2020`) no longer exist** — Align was
   refactored. The live Align layout rules are `.align-results` (`:2011`),
   `.align-summary` (`:2017`), `.align-metric` (`:2022`), `.align-textarea` (`:1952`),
   `.align-trace-channel` (`:2080+`). Treat Align's reflow as: the results/summary
   block + the (intrinsically wide) trace channel. **Re-verify Align's current grid
   columns at build time before adding container breakpoints.**
4. **The dead `SidePanel` collapse button + `.ai-pill`/`.ai-panel` + `.zoom-pill`
   are already removed** (confirmed: no matches in `workbench.css` or
   `SidePanel.tsx`). `WorkbenchShell.tsx` no longer passes `onToggleCollapsed`. The
   audit's `SidePanel.tsx:735-752` / `:309-318` line numbers are stale — the **Ask
   tab** now lives at `SidePanel.tsx:307-315` (tab button) + body `~:375-396`.
5. **`viewerCollapsed(tool)` is align-only**, at `tools.ts:50-52` (`return tool === 'align'`),
   consumed at `WorkbenchShell.tsx:152` + applied at `:232`. The `.viewer.viewer-collapsed`
   rule is `workbench.css:190` and animates `max-height`/`padding`/`opacity` (a
   DESIGN.md layout-animation violation). **The new model must NOT inherit this rule.**
6. **`.tool-panels` / `.tool-panel` are at `workbench.css:1752-1761`** (not :1816). The
   `.tool-panel.active { display:block }` show/hide is the seam to restructure.
7. **`--side-w` does not exist**; the left rail width vocabulary is
   `--maxw-workbench-side: 360px` (`globals.css:156`) and `work-rail.css`'s own
   `--rail-w: 336px` (`:14`). `--nav-h:60px` / `--ctx-h:48px` exist (`globals.css:145-146`).
8. **`WorkRail` is consumed identically by all three surfaces** — `ReportClient.tsx:480`,
   `CompareClient.tsx:160`, `WorkbenchShell.tsx:306` (each passes `surface` + `output` +
   section children). **Any `.work-rail-foot` change is therefore global by construction.**
9. **`CanvasHeader` returns `null` when a tool has no controls** (`CanvasHeader.tsx:88-89`,
   `hasControls = tool==='viewer' || meta.tracks`). Align has `tracks:false`
   (`tools.ts:39`) → no header today. Under the grid this becomes the viewer column's
   header; the minimise handle must live somewhere that survives the `null` return.

---

## 2. Build sequence (overview)

Sub-order per the brief: **rail-foot cluster FIRST** (lower-risk, no canvas
restructure), **then the 3-col grid**. Each step is independently shippable and
browser-verifiable.

```
STEP 0  Pre-flight refactor — extract collapse helpers (behaviour-neutral)         🟢
─────── PART A · BOTTOM-LEFT CLUSTER (global shell, no canvas restructure) ───────
STEP 1  .work-rail-foot region in WorkRail + CSS (empty scaffold, all 3 surfaces)  🟡
STEP 2  AuthMenu rail-foot variant (upward popover, PORTAL out of the rail)        🟡
STEP 3  COMING-SOON Ask-Eamos launcher row (parked, IconSparkle)                   🟡
STEP 4  Cite → /report (useCiteModal hook + TopNav button); remove global CiteChip 🟡
STEP 5  Feedback → "Send feedback" in the account menu (global mailto)             🟡
─────── PART B · 3-COLUMN CANVAS (the structural lift) ───────────────────────────
STEP 6  3-state ViewerPane model in tools.ts + WorkbenchShell (persisted)          🟡
STEP 7  .canvas grid [viewer | tool-rail] + move .tool-panel into the right track  🟡
STEP 8  Viewer minimise/restore/maximise handles (CanvasHeader + stub)             🟡
STEP 9  Container-query (@container) panel reflow for the tool rail                 🟢
STEP 10 <900px vertical-stack fallback + reduced-motion + a11y pass                 🟡
─────── HOUSEKEEPING ─────────────────────────────────────────────────────────────
STEP 11 Reconcile DESIGN.md:559-571; demote Scratchpad "Ask" tab; boundary checks 🟢
```

🟡 = durable/structural/persistent-element (covered by Steven's approval of this plan).
🟢 = additive/behaviour-neutral within the approved feature.

---

## STEP 0 — Pre-flight: extract the collapse helpers (behaviour-neutral) 🟢

**Change.** Lift the three persistence helpers out of `WorkRail.tsx` into a new
`lib/work-rail-collapse.ts` so both the left rail and (later) the centre viewer
share one SSR-safe persistence path. **Pure refactor — zero behaviour change.**

**Files.**
- **New** `app/web/lib/work-rail-collapse.ts` — export `storageKey(scope)`,
  `readCollapsed(scope): boolean | null`, and a `writeCollapsed(scope, value)`
  setter (the `try/localStorage.setItem` body currently inlined in `toggle`/
  `expandFromIcon`). Keep the exact `eamos-rail-<scope>-collapsed` key shape.
- `app/web/components/layout/WorkRail.tsx:23-34` — delete the local `storageKey`
  + `readCollapsed`; import from the new module. `initialCollapsed` (`:39-44`),
  `toggle` (`:120-134`), `expandFromIcon` (`:136-143`) call the imported setter.
  `subscribeCompact`/`getCompactSnapshot`/`getServerCompactSnapshot` stay in
  `WorkRail.tsx` (they're rail-layout-specific, not persistence).

**Approach.** Generalise the param name from `surface` to `scope` so the same
helpers serve both `eamos-rail-workbench` (rail) and `eamos-wb-viewer-<tool>`
(viewer, STEP 6). No new dependency; identical `try/catch` private-mode guards.

**Browser-verify.** `npm --prefix app/web run dev` → `/workbench`, `/report`,
`/compare`: collapse each rail, reload — pref persists exactly as before. Toggle
in a private window — no throw. `npm --prefix app/web run lint` clean (no unused
imports). **No visual change expected.**

**Risks.** Low. Only risk is an import cycle if the new module imports from
`WorkRail` — it must not (helpers are leaf-level, depend on nothing).

---

# PART A — bottom-left utility cluster (global shell)

> Per `shell-flow.md §4`: lower-risk, no canvas restructure, ships first. It is a
> **global** change — `.work-rail-foot` appears on report + workbench + compare the
> moment it lands (§1.8). Treat every step's browser-verify as a three-surface check.

## STEP 1 — `.work-rail-foot` region (scaffold) 🟡

**Change.** Add a third, non-scrolling flex region to the rail:
`.work-rail-head` (flex:0) → `.work-rail-body` (flex:1, scrolls) →
**`.work-rail-foot` (flex:0, pinned)**. Ship it empty first (a hairline + a
placeholder height) so the layout/scroll behaviour is proven before content lands.

**Files.**
- `app/web/components/layout/WorkRail.tsx:195` — after the `.work-rail-body` div,
  add `<div className="work-rail-foot">{foot}</div>`. Add an optional
  `foot?: ReactNode` prop to `WorkRailProps` (`:97-109`). Render the foot **only
  when `foot` is provided** so report/compare are unaffected until their callers opt in.
- `app/web/components/layout/work-rail.css` — new `.work-rail-foot` block: `flex:0 0 auto`,
  top hairline `border-top: 0.5px solid var(--line)`, padding matching
  `.work-rail-head` (`12px`). In `.is-collapsed`, the foot goes icon-only
  (mirror the `.is-collapsed .work-rail-*` rules at `:120-128`). Add the
  reduced-motion guard entry (`:324-331`).
- `app/web/components/workbench/WorkbenchShell.tsx:306-314` — pass `foot={<railFoot/>}`
  to the workbench `<WorkRail>` (the foot content arrives in STEPs 2-3; scaffold
  with a stub first).

**Approach.** The body's existing `overflow-y:auto` (`work-rail.css:101-107`)
already clips between head and foot, so the foot never scrolls away — this is
exactly the structure `shell-flow §4` / chrome-spec §2 prescribe. **No new fixed
positioning** — the foot rides the rail's flex column and inherits its collapse +
drawer + `--rail-live-w` machinery for free.

**Browser-verify.** `/workbench`: empty foot pinned to the rail bottom; body
scrolls under it (load a long Library list to force scroll). Collapse rail to 48px
→ foot shrinks to the icon lane, body content hidden as before. <1200px → foot
rides the drawer in/out. **`/report` + `/compare` unchanged** (no `foot` prop yet).

**Risks.** If `.work-rail-body` had `flex:1` competing with a foot that has
intrinsic height, the body could over-grow; `min-height:0` on the body
(`work-rail.css:107`) already guards this — verify the scroll boundary lands above
the foot, not under it.

## STEP 2 — `AuthMenu` rail-foot variant (the account row) 🟡

**Change.** Reuse `AuthMenu.tsx` wholesale; add a `placement="rail-foot"` mode that
(a) renders a full-width rail row (avatar + truncated email + chevron) and (b) opens
the account dropdown **upward** (`origin-bottom-left`) instead of top-right.

**Files.**
- `app/web/components/auth/AuthMenu.tsx` — add `placement?: 'nav' | 'rail-foot'`
  (default `'nav'`, so existing `LandingNav`/`PageHeader` mounts are untouched).
  - The popover className currently hardcodes top-anchored positioning
    (`:114-117`). For `rail-foot`, swap to a bottom-anchored variant
    (`bottom-full mb-2 origin-bottom-left`) and `z-[var(--z-popover)]` (replacing
    the literal `z-[60]` at `:115-116` — adopt the token, §1.1).
  - The signed-in trigger (`:58-78`) gets a full-width rail register (left-aligned,
    `--wr-section-head` metrics) when `placement==='rail-foot'`.
- `app/web/components/workbench/WorkbenchShell.tsx` — the `railFoot` node renders
  `<AuthMenu placement="rail-foot" tone="light" />`.

**Approach — the load-bearing caveat.** The rail is `overflow:hidden`
(`work-rail.css:41`) **and** `position:sticky` (`:36`) — a new stacking context.
A dropdown rendered *inside* the foot is **clipped** by that `overflow:hidden` and
trapped under the rail's stacking context. **The rail-foot popover MUST portal out**
(React `createPortal` to `document.body`) and position itself off the trigger's
`getBoundingClientRect()`, OR the foot row must escape the clip. Portal is the clean
answer and matches how robust menus handle sticky+overflow parents. This is called
out in both source specs (3-col §6, chrome §6) and `shell-flow §4` — it is the #1
implementation risk for Part A. Preserve all existing a11y: `role="menu"`,
`aria-haspopup`, `aria-expanded`, Esc-returns-focus-to-trigger (`AuthMenu.tsx:31-36`),
outside-click close (`:28-30`).

**Browser-verify.** `/workbench` signed-out → "Sign in / Register" row in the foot;
click → `AuthPanel` opens **upward**, fully visible (not clipped by the rail).
Signed-in (or stub `useAuth`) → avatar + email row; dropdown opens upward with My
account / Sign out. Tab order: head → body → foot → account trigger → menu items.
Esc closes + focus returns to the trigger. Collapsed 48px rail → avatar-only with
`title`; menu opens as a **right-side** flyout (no downward room). Repeat on
`/report` + `/compare` once they opt into `foot` (or defer their opt-in to a follow-up;
this plan wires the workbench foot and leaves report/compare foot opt-in as a
one-line change each).

**Risks.** Portal positioning on scroll/resize (recompute on open + on
`scroll`/`resize` while open, or use a tiny positioning effect). Focus trap: the
portalled menu must keep Esc/outside-click wired to the same `open` state.

## STEP 3 — COMING-SOON Ask-Eamos launcher row 🟡

**Change.** A full-width disabled launcher row above the account row in the foot:
`IconSparkle` (monochrome `--ink-2`, **not** teal — it's a rail glyph) + "Ask Eamos"
+ a right-aligned `COMING SOON` tag.

**Files.**
- `app/web/components/workbench/WorkbenchShell.tsx` (or a small new
  `components/layout/RailFoot.tsx` if the foot grows past ~30 lines) — render the
  launcher row using `IconSparkle` from `Icon.tsx:127`.
- `app/web/components/layout/work-rail.css` — `.wr-foot-ask` row reusing
  `.wr-section-head` metrics (`:234-260`); the `COMING SOON` tag reuses the pill
  style the `AskEamos` header uses (`10px`/700/uppercase, `--ink-3` on `--bg`,
  `0.5px --line`).

**Approach.** `aria-disabled="true"`, `title="Variant-aware chat — coming soon"`.
**No network, no panel, no LLM wiring** ([[feedback_askeamos_parked]]). Mock-first:
the row is the affordance, the panel is parked. Do **not** un-ghost the old
`.ai-pill`/`.ai-panel` (already deleted, §1.4) — the rail foot is the one Ask home.

**Browser-verify.** Foot shows `✦ Ask Eamos  [COMING SOON]`; click does nothing
(no console error, no nav). Keyboard: row is focusable, announces disabled. Collapsed
rail → sparkle-only with `title`. No bottom-right floater anywhere.

**Risks.** Minimal. Ensure the disabled row still has a visible focus ring
(disabled ≠ unfocusable here — it's `aria-disabled`, a button kept in tab order
for discoverability) so it's reachable on keyboard.

## STEP 4 — Cite → `/report` (scoped); remove the global mount 🟡

**Change.** Move the Cite action out of the global bottom-left dock into the
`/report` TopNav, and extract the modal-state + `?cite=1` deep-link logic into a
reusable hook so the button and the deep link share one path.

**Files.**
- **New** `app/web/lib/useCiteModal.ts` (or `components/report/useCiteModal.ts`) —
  lift from `CiteChip.tsx`: the `citeOpen`/`date` state (`:43, :78`), the `?cite=1`
  listener (`:81-94`), `openCite` (`:96-99`), `closeCite` (`:115-131`), the
  `{variant_display}` resolver (`:64-75`), and `REPORT_VERSION` (`:8`). Return
  `{ citeOpen, openCite, closeCite, variantDisplay, date, reportVersion }`.
- `app/web/components/report/ReportClient.tsx` — consume `useCiteModal()`; render a
  **`⌗ Cite` button** in the TopNav right slot beside the `ModePill` (reuse
  `IconShare` from `Icon.tsx:287` or a quote glyph), and mount `<CiteModal>` here
  (moved off the global tree). The button's `onClick = openCite`.
- `app/web/app/providers.tsx:36-41` — **remove the global `<CiteChip>` mount** and
  its `<Suspense>` wrapper + the `import { CiteChip }` at `:7`.
- `app/web/components/ui/CiteChip.tsx` — the Feedback/Cite **dock UI** is retired
  (its responsibilities split to STEP 4 Cite + STEP 5 Feedback). Keep `CiteModal.tsx`
  (still used). The `eamos.cite-dock.collapsed` store + `«/»` launcher
  (`CiteChip.tsx:13-33, 141-178, 249-267, 327-340`) are **your-own-orphan cleanup** —
  delete with the dock.

**Approach.** Cite is intrinsically report-centric — `variantDisplay` already
early-returns `null` off `/report` (`CiteChip.tsx:64-65`), so scoping is natural.
The TopNav is the cleaner home than a report-only rail-foot row (keeps the shared
foot free of a per-surface action). Preserve the deep link: `?cite=1` must still
open the modal — that's why the listener moves into the hook, not just the button.

**Browser-verify.** `/report?...&cite=1` → modal opens on load (deep link intact).
Click the TopNav `Cite` button → same modal, `{variant}` + access date + version
correct. Close → `?cite=1` stripped from the URL (the `router.replace` in
`closeCite`). `/workbench` + `/compare` + `/` → **no** Cite dock anywhere (global
mount gone). `npm --prefix app/web run lint` clean (no dangling `CiteChip` import).

**Risks.** `useCiteModal` reads `useSearchParams` → its consumer (`ReportClient`)
must already be inside a Suspense boundary (it is — the report is a client surface
under the App Router shell). Verify no hydration warning. Removing the global
`<Suspense><CiteChip/></Suspense>` must not orphan the `PostHogPageView` Suspense
(separate boundary at `providers.tsx:31-33` — leave it).

## STEP 5 — Feedback → "Send feedback" in the account menu 🟡

**Change.** Move the global Feedback `mailto` into the relocated `AuthMenu`
dropdown as a `role="menuitem"`.

**Files.**
- `app/web/components/auth/AuthMenu.tsx` `AccountDropdown` (`:146-211`) — add a
  **"Send feedback"** menu item above "Sign out". Its handler builds the same
  `mailto:sales@eamos.com.au` with page URL + (when on `/report`) variant +
  `REPORT_VERSION` prefilled — lift `openFeedback` from `CiteChip.tsx:104-113`.
  Add **"Billing"** → `/#pricing` (per §0) and **"My account"** (already present).
- The feedback builder needs `pathname` + the variant display. Easiest: reuse the
  `useCiteModal()` `variantDisplay` (or a slimmer `useFeedbackMailto()` sibling) so
  the subject still routes by variant on `/report` and is generic elsewhere.

**Approach.** Feedback is global (any surface). The account menu is the lowest-
friction global home (it already renders a menu with full a11y). Keep the mailto
shape identical so triage routing is unchanged.

**Browser-verify.** Account menu (any surface) → "Send feedback" → opens mail client
with prefilled subject/body; on `/report` the subject carries the variant, elsewhere
it's generic. "Billing" → `/#pricing`. "My account" → `/account`. "Sign out" works.
Menu a11y unchanged (Esc, outside-click, focus return).

**Risks.** `mailto` from a portalled menu still works (it's a `window.location.href`
assignment, not DOM-position-dependent). Ensure the menu closes after firing the mailto.

---

# PART B — 3-column canvas (controls | viewer | tool-rail)

> The structural lift. Depends on STEP 0 (helpers) but is independent of Part A.
> Option C: one grid `.canvas`, the `.wr-section` grammar for the rail's chrome,
> the extracted helpers for viewer persistence. **Never a second `<WorkRail>`**
> (avoids nested sticky / inverted semantics / `--rail-live-w` collision).

## STEP 6 — 3-state ViewerPane model 🟡

**Change.** Replace the binary `viewerCollapsed(tool): boolean` with a 3-state
model owned by `WorkbenchShell`, persisted per tool.

**Files.**
- `app/web/components/workbench/tools.ts:50-52` — replace `viewerCollapsed` with
  `export type ViewerPane = 'expanded' | 'collapsed' | 'hidden'` and
  `defaultViewerPane(tool): ViewerPane` encoding §0: `viewer`→N/A,
  `primer`→`expanded`, `crispr`→`expanded`, `align`→`collapsed`. Keep a named export
  shim only if a grep shows other consumers (currently the sole consumer is
  `WorkbenchShell.tsx:152`).
- `app/web/components/workbench/WorkbenchShell.tsx` — lift `viewerPane` state with a
  lazy `useState` initializer reading `eamos-wb-viewer-<tool>` via the STEP-0
  `readCollapsed`/`writeCollapsed` helpers (SSR returns `defaultViewerPane(tool)`,
  the no-setState-in-effect pattern this file already uses at `:98-102`). Replace
  `const collapsed = viewerCollapsed(tool)` (`:152`).
- The CRISPR Off-targets auto-collapse (§0) needs the active CRISPR sub-tab. If the
  sub-tab state lives inside `CrisprPanel`, lift a thin `onSubTabChange` callback up
  to `WorkbenchShell` (or read it via a shared store) so selecting Off-targets sets
  `viewerPane='collapsed'`. **Verify where CRISPR sub-tab state lives before wiring.**

**Approach.** Persist as a string, not a boolean (the helper's `readCollapsed`
returns `'1'|'0'|null` today — generalise it to return the raw string, or add a
`readPane`/`writePane` pair alongside). Per-tool key so Primer-expanded and
Align-collapsed coexist.

**Browser-verify.** Switch tools: Primer/CRISPR open `expanded`, Align opens
`collapsed`. Set a non-default state, reload → it persists per tool. Select CRISPR
→ Off-targets → viewer auto-collapses; back to Design → stays per the persisted
pref (auto-collapse is a one-way nudge, not a lock). No console errors on first
paint (SSR default matches client default).

**Risks.** SSR/client mismatch if the initializer reads `localStorage` during
render on the server — guard with `typeof window === 'undefined'` returning the
default (mirror `WorkRail.tsx:40`). The Off-target auto-collapse must not fight a
user who then manually re-expands — make it fire on sub-tab *change*, not every render.

## STEP 7 — `.canvas` grid `[viewer | tool-rail]` 🟡

**Change.** When a tool is active (`tool!=='viewer'`), make `.canvas` a 2-track CSS
grid; move the active `.tool-panel` into the right track; the `CanvasHeader` + viewer
stay in the left track. The `tool==='viewer'` path stays exactly as today (single column).

**Files.**
- `app/web/components/workbench/WorkbenchShell.tsx:218-302` — restructure
  `canvasOutput`:
  - `tool==='viewer'` → today's stack (`CanvasHeader` → `.viewer`), full width. **Unchanged.**
  - else → `<main className="canvas" data-tool-active data-viewer-pane={viewerPane}>`
    with two children: a **left column** wrapping `CanvasHeader` + the `.viewer`
    `<section>`, and a **right column** `.wb-tool-rail` holding the active tool panel.
    Drop the `PANEL_TOOLS.map` stacked-render (`:284-300`); render only the active
    tool into the right track (the inactive `display:none` panels were only needed
    for the stacked layout).
- `app/web/components/workbench/workbench.css`:
  - `.canvas[data-tool-active]` → `display:grid; grid-template-columns: minmax(0,1fr) var(--tool-rail-w);`
    Add `--tool-rail-w` to `:root` or `.wb-work-shell` (~`clamp(420px, 46%, 560px)`
    per the spec's measure). Gap via an existing spacing token.
  - `data-viewer-pane='collapsed'` → `grid-template-columns: var(--rail-w-collapsed, 48px) minmax(0,1fr)`
    (viewer becomes the stub lane, tool rail grows). `='hidden'` →
    `grid-template-columns: 0 minmax(0,1fr)` (viewer removed from layout). `='hidden'`
    + maximise → tool rail full width.
  - **Motion: animate `grid-template-columns`** at `--dur-2 var(--ease-emphasized)`
    (DESIGN.md Disclosure: grid-cols + opacity is sanctioned). **Do NOT touch the
    `.viewer.viewer-collapsed` max-height rule** (`:190`) — it's the audit-flagged
    pattern; the new model supersedes it. The viewer content cross-fades opacity.
  - `.wb-tool-rail` — sticky within the grid track, own `overflow-y:auto`, internal
    chrome from `.wr-section`/`.side-section` grammar + `--report-subpanel-*` card
    geometry. Reuse `--maxw-workbench-side` vocabulary for its max width.
  - `.wb-viewer-stub` — mirror `.work-rail-stub` (`work-rail.css:129-152`): vertical
    writing-mode "Sequence" label + expand affordance.
- `app/web/components/workbench/CanvasHeader.tsx` — the header now sits atop the
  **left (viewer) column**, not the full canvas. Its flush-right cluster
  (`workbench.css:127-128`) reads as "controls for this sequence." (Left-aligning it
  per `shell-flow §3.5` is a nice-to-have, not required for this step.)

**Approach.** One `<main class="canvas">`, one stacking context, one grid template
driven by `data-*` attributes — the cleanest stacking story and the owner-controlled
split knob (Option C / B core). The tool panel keeps its existing internals
(`.tool-panel-head`, `.tool-form`, etc., `workbench.css:1754+`); it just lives in a
narrower track now (STEP 9 handles its reflow).

**Browser-verify.** Primer/CRISPR: viewer left ~50%, tool rail right ~50%, **the
Generate/run primary action visible without scrolling** (the whole point —
`shell-flow §3`). Align: viewer is the 48px stub, tool rail ~70%. Switch tools →
grid columns animate smoothly (no max-height jank). `tool==='viewer'` → single full-
width viewer, no rail, **identical to today**. Resize 1440→1200 → still 3 logical
regions (left rail drawers at 1199 per existing `WorkRail`). The monospace sequence
viewer is **byte-identical** inside its (now narrower) column — no wrapping/scaling
regressions (it already scrolls horizontally).

**Risks.** (a) `min-width:0` on the viewer track is essential or the mono sequence
forces the grid wider than the viewport — set `minmax(0,1fr)`. (b) The right track's
sticky must be scoped so it doesn't fight the left `WorkRail`'s sticky (different
ancestors — OK, but verify no double-scroll). (c) The CRISPR/Align tables inside the
narrower track will overflow until STEP 9 — acceptable interim (`overflow-x:auto`
exists on `.crispr-table-wrap` `:2512`).

## STEP 8 — viewer minimise / restore / maximise handles 🟡

**Change.** Wire the three affordances that move the viewer between
expanded/collapsed/hidden and the tool rail to full width.

**Files.**
- `app/web/components/workbench/CanvasHeader.tsx` — in `expanded`, add a **minimise
  handle** at the right end of the header row: a real `<button>` (1.75-family glyph —
  `IconWindow` `:249` or a new minimise glyph), `aria-label="Minimise sequence"`,
  `aria-expanded`, `title`. **Problem:** `CanvasHeader` returns `null` for Align
  (`:88-89`). Fix: the minimise/restore control must live in a wrapper that survives
  the `null` (render it in `WorkbenchShell`'s left-column header band, *outside*
  `CanvasHeader`'s conditional), OR give `CanvasHeader` a zero-controls branch that
  still renders the handle.
- `.wb-viewer-stub` (STEP 7) is itself the **restore button** in `collapsed`
  (`role=button`, `aria-label="Expand sequence"`) → sets `viewerPane='expanded'`.
- **`hidden` restore chip** — a small "Show sequence" chip in the header region when
  `viewerPane==='hidden'` → `expanded`.
- **`expand-tool-to-full` maximise handle** on the `.wb-tool-rail` head: a new
  `IconExpand` (add to `Icon.tsx`, 1.75 family) → sets `viewerPane='hidden'` + rail
  full width. Pairs with the CRISPR Off-targets auto-collapse (STEP 6) as the manual
  escalation.
- CanvasHeader-controls-when-collapsed (§0): in `collapsed`, fold the
  track/strand/allele/export controls into a **stub overflow menu** (opens at
  `--z-popover`); in `hidden`, **hide** them (they belong to the viewer).

**Approach.** Mirror `WorkRail`'s own toggle+stub pair exactly (persistent, not
hover-revealed → discoverable on touch, matching the `.chromatogram-toggle`
precedent). Chevron/expand glyphs rotate via `transform` (DESIGN.md Disclosure).
State change keeps focus on the handle (which becomes the stub), never steals it
from the tool rail.

**Browser-verify.** Primer `expanded` → click minimise → viewer animates to the
48px stub, tool rail grows, focus stays on the now-stub. Click stub → restores.
Tool-rail maximise → viewer `hidden`, rail full width, "Show sequence" chip appears
→ click restores. CRISPR → Off-targets auto-collapses (STEP 6) → maximise hides
fully → Off-target table gets full width. Keyboard: every handle Tab-reachable,
visible focus ring (`box-shadow: 0 0 0 3px color-mix(--teal 22%)` per
`work-rail.css:257-260`), `aria-expanded` reflects state. Non-colour cue: the stub
says "Sequence" (text).

**Risks.** The `CanvasHeader` `null`-return is the trap (§1.9) — the handle must not
live inside the part that disappears for Align. Focus management across the
expand/collapse swap (don't drop focus to `<body>`).

## STEP 9 — container-query (`@container`) panel reflow 🟢

**Change.** The tool rail's width is **decoupled from the viewport** — a ~500px rail
inside a 1440px viewport means the panels' existing **viewport** media queries never
fire. Convert the panels' internal breakpoints to **container-relative** so they
reflow on rail width.

**Files.**
- `app/web/components/workbench/workbench.css`:
  - Add `container-type: inline-size; container-name: wbtool;` to `.wb-tool-rail`
    (STEP 7). **This is a net-new technique here — confirmed no `@container` exists
    anywhere in `app/web` yet** (grep clean), so introduce it cleanly with a comment.
  - **CRISPR** (MEDIUM risk): `.crispr-summary`'s `@media (max-width:560px)`
    (`workbench.css:2554`) → `@container wbtool (max-width: 560px)`. Same for
    `.ots-field-wide`'s `@media (max-width:560px)` (`:2600`). `.crispr-table-wrap`
    already has `overflow-x:auto` (`:2512`) — keep as the sanctioned table fallback.
  - **Align** (HIGH risk): **re-verify the live Align grid first** (§1.3 — the
    spec's `.align-source-grid` is gone; the current layout is `.align-results`/
    `.align-summary`/`.align-metric` `:2011-2048` + the trace channel `:2080+`). Add
    a `@container wbtool (max-width: ...)` 1-col fallback for whatever multi-column
    Align block currently exists; ensure the trace channel keeps `overflow-x:auto`.
  - **Primer** (LOW risk): `.tool-form` is `repeat(auto-fit, minmax(170px,1fr))` —
    already reflows cleanly; **no change needed**. Verify at ≥420px.
- Add `overflow-x:auto` wrappers to any table still missing one (audit at build time).

**Approach.** `@container` is the clean answer the specs + `shell-flow §4` all name;
a `data-rail-narrow` attribute the shell sets is the documented fallback if a target
browser lacks container-query support (Next 16's browser baseline supports it, so
prefer `@container`). The minimum usable rail measure is **≥420px**; below that the
shell should prefer `collapsed`/maximise (STEP 8) so the rail gets the room.

**Browser-verify.** At a ~500px rail (viewer `expanded`), CRISPR summary collapses
to 1 column (container query fired — confirm it does NOT fire at 1440px viewport
when the rail is full-width). Align multi-column block → 1 column at the narrow
container; trace scrolls horizontally, never breaks the mono grid. Primer 5-col form
→ 2-3 cols cleanly. Toggle the viewer collapsed → rail widens → panels re-expand.

**Risks.** Container queries need the container to establish `container-type` — if
`.wb-tool-rail` also needs `position:sticky`, both can coexist but verify the sticky
still works with `container-type:inline-size` (it does; just confirm). Don't put
`container-type` on an ancestor that the viewer also lives under, or the viewer's
own future container styles would key off the wrong box.

## STEP 10 — `<900px` vertical-stack fallback + reduced-motion + a11y 🟡

**Change.** Below ~900px the 3-column model is abandoned for today's vertical stack
(viewer above, tool below); ship the reduced-motion guard and the full a11y pass.

**Files.**
- `app/web/components/workbench/workbench.css`:
  - `@media (max-width: 899px)` → `.canvas[data-tool-active]` reverts to
    `display:block` (or single-column grid), tool panel stacks below the viewer
    (≈ today's `.tool-panels` behaviour). The left `WorkRail` is already a drawer at
    <1200 (`work-rail.css:155`), so <900 is purely the right-side collapse.
  - `@media (prefers-reduced-motion: reduce)` → drop the `grid-template-columns`
    transition (instant state swap), matching `work-rail.css:324-331`.
- a11y sweep across STEPs 7-9: viewer region keeps a stable landmark; `hidden`
  removes it but leaves the restore chip in tab order; reading order is strictly
  left (context) → centre (see) → right (act).

**Approach.** The collapse order is already specified: left rail → drawer first
(existing, at 1199), centre viewer → stub next (auto/tool-driven), tool rail →
stacked-below last (this step, at 899). No horizontal scroll at any width
(ui-ux-pro-max `horizontal-scroll` High). Start with stacked-below; only build a
tool-rail bottom-drawer if QA shows stacking is insufficient (it won't be — it's
today's known-good layout).

**Browser-verify.** 1440 → 1200 → 1000 → 900 → 768 → 390: at each step no horizontal
page scroll; below 900 the tool panel sits under the viewer (today's layout); left
rail drawers at 1199. Reduced-motion OS setting → grid changes are instant, no
animation. Full keyboard pass: Tab through the entire shell (nav → ctx → left rail →
viewer handle → tool rail → rail foot account) in a logical order.

**Risks.** The 900px breakpoint interacting with the 1199 left-rail drawer — verify
the band 900-1199 (left rail drawered, 3-col still active) looks right, not just the
extremes.

---

# HOUSEKEEPING

## STEP 11 — reconcile docs, demote the Scratchpad Ask tab, refresh the graph 🟢

**Change.**
- **Reconcile `DESIGN.md:559-571`** — it still documents the OLD shell (`<TopNav/>`
  on workbench [it rolls its own `.nav-wrap`], a vertical `<ToolRail/>` icon rail,
  `<AskEamosPill/>` bottom-right, `<WorkbenchShell/>` as `grid-template-columns:
  64px 1fr 360px`, `<SidePanel/>` as a 360px *right* column). Update the table so the
  3 columns read **controls (left WorkRail) | viewer (centre) | tool-rail (right)**,
  the nav is the shared `.nav-wrap`, Ask-Eamos is the rail-foot launcher (not a
  bottom-right pill), and the bottom-left cluster (account + Ask) is documented. This
  is a **technical-writer / doc task** — flag it; the architect/dev should not prose-
  edit DESIGN.md beyond the structural correction. (Per `shell-flow §5.3`.)
- **Demote the Scratchpad "Ask Eamos" tab** (`SidePanel.tsx:307-315` + body
  `~:375-396`) to a clean **Log/Notes 2-tab strip** once the rail-foot Ask launcher
  (STEP 3) ships — one Ask home, not two ([[feedback_askeamos_parked]]). Remove the
  `'ask'` tab button + its body branch + any now-unused state. Your-own-orphan cleanup.
- Run the structural boundary guards after the code lands so the new modules
  (`lib/work-rail-collapse.ts`, `lib/useCiteModal.ts`, the rail-foot, the grid)
  are covered by executable wiring checks.

**Browser-verify.** Scratchpad shows Log / Notes only (no Ask tab); the rail-foot Ask
launcher is the sole Ask affordance. DESIGN.md table matches the shipped shell.
`git diff` on DESIGN.md is structural only.

**Risks.** Don't delete pre-existing dead code beyond your own orphans
([[CLAUDE.md §3 Surgical Changes]]) — the `TOOL_META.compare` / `ToolIcon` compare
case the audit flags (`tools.ts:41-46`) is **out of scope** for Task A; mention, don't remove.

---

## Cross-cutting conventions honoured (the plan's guardrails)

- **Classification colour only via `lib/classification.ts` (`--cls-*`)** — no
  verdict colour invented in any new chrome; the rail-foot/account/Ask use
  `--ink-*`/`--teal` register glyphs (never status colour). The `.scratch-cv-cls`
  off-ramp bug the audit flags is a **separate** verdict-colour lane, not Task A.
- **Stacking via `--z-*`** (`globals.css:190-197`) — the account popover adopts
  `--z-popover` (70); the rail foot inherits the rail's `--z-rail`/`--z-drawer`. **No
  new arbitrary z values.** This also *fixes* the old `CiteChip z:900` anomaly (it's
  removed in STEP 4).
- **Tokens, not raw hex** — `--dur-*`/`--ease-*`, `--line`, `--bg`/`--bg-soft`,
  `--r-*`, `--report-subpanel-*`, `--maxw-workbench-side`, `--rail-w(-collapsed)`.
- **Reuse `Icon.tsx` 1.75 family** — `IconSparkle`, `IconWindow`, `IconChevron`,
  `IconShare`; new `IconExpand` joins the family (same `iconBase`, weight 1.75).
- **Mock-first + `.eamos-mock`** — the Ask launcher is parked (no LLM key); any gated
  metric stays mock-marked.
- **NEVER break the monospace sequence viewer** — the grid uses `minmax(0,1fr)` and
  the viewer's own horizontal scroll; STEP 7's browser-verify explicitly checks the
  mono grid is byte-identical in the narrower column.
- **Animate `grid-template-columns`, never `.viewer` max-height** — the old
  `.viewer-collapsed` pattern (`workbench.css:190`) is superseded, not extended.
- **Portal the rail-foot popover** out of the rail's `overflow:hidden`+sticky
  stacking context (STEP 2) — the single highest implementation risk in Part A.
- **`@container` is net-new** to `app/web` — introduce it cleanly on `.wb-tool-rail`
  (STEP 9), with the `data-rail-narrow` attribute as the documented fallback.
- **Durable/structural change is gated** — this whole plan is 🟡; it ships only on
  Steven's OK.

## Verification ledger (per part)

| Part | Gate command(s) |
| ---- | --------------- |
| Every step | `npm --prefix app/web run lint` clean; no new console errors |
| STEP 0 | rail persistence unchanged on all 3 surfaces (reload test) |
| Part A | account popover not clipped (portal works); Cite deep-link intact on `/report`; no Cite/Feedback dock off-report; foot rides collapse + drawer |
| Part B | primary action in view (Primer/CRISPR); mono viewer byte-identical; grid animates (no max-height jank); `tool==='viewer'` identical to today; container queries fire on rail width not viewport; <900 reverts to vertical stack; reduced-motion instant |
| Housekeeping | DESIGN.md table matches shipped shell; Scratchpad = Log/Notes; structural boundary guards pass |

Browser-verify via the `browser-verify` skill against `npm --prefix app/web run dev`
(→ `http://localhost:3000`). **Kill the dev server at task end**
([[feedback_background_process_cleanup]]).
