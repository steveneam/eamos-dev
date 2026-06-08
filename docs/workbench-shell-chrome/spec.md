# Persistent shell chrome — bottom-left utility cluster

**Status:** 🟡 DESIGN EXPLORATION + SPEC — review-gated. No code lands until Steven
approves. Persistent / structural / cross-surface chrome → explicit OK required
([[feedback_subagent_recommendations_not_authorization]]).

**Scope:** the persistent app-shell chrome — where the **Ask Eamos** assistant
entry point, an **account/settings** affordance, and the relocated
**Cite/Feedback** pill should live, following the SaaS/AI convention of a
bottom-left utility cluster (Claude / yorby.ai reference shots).

**Hard constraint — Ask Eamos is PARKED.** No LLM API key is funded
([[feedback_askeamos_parked]]). This spec plans *real estate + interaction only*.
Every assistant affordance ships as a **COMING SOON** placeholder; nothing here
wires chat live.

**Method run before writing:** graphify (`query "account settings nav"`,
`query "ask eamos chat"`, `query "cite feedback dock"`, `explain "WorkRail"`) →
ui-ux-pro-max `--domain ux` (Navigation / Sticky-nav-overlap, Focus-states High,
Keyboard-navigation High, Skip-links) + frontend-design lens → both reference
screenshots → `DESIGN.md`, `work-rail.css`, `Icon.tsx`,
`docs/workbench-report-sweep/workbench-chrome.md` (the ad-hoc z-stack + proposed
`--z-*` scale).

---

## 1. Inventory — what lives where today

### 1a. Cite / Feedback dock (the corner the owner wants back)
- **`app/web/components/ui/CiteChip.tsx`** — a **`position:fixed; bottom:16; left:16; z-index:900`** dock (`dockWrapStyle` :271-276). Two buttons (Feedback + Cite) + a `«`/`»` collapse-to-launcher (persisted at `localStorage['eamos.cite-dock.collapsed']`, SSR-safe via `useSyncExternalStore`). It **owns the `CiteModal` mount** and the **`?cite=1` deep-link listener** (:81-94) and resolves `{variant_display}` from `/report` URL params (:64-75). Feedback = a `mailto:sales@eamos.com.au` with page/variant/version prefilled (:104-113).
- **`app/web/components/ui/CiteModal.tsx`** — the citation modal (APA-ish copy block, return-focus to the dock wrapper ref).
- **`app/web/app/providers.tsx:39-41`** — `<CiteChip>` mounted **GLOBALLY**, inside a `<Suspense>` (required: it reads `useSearchParams`). So it renders on **every** surface (`/`, `/report`, `/workbench`, `/compare`, `/account`, …), even though its content (cite a variant report, feedback-with-variant) is **report-centric**.

### 1b. Ask Eamos surfaces (all parked / coming-soon)
- **`app/web/components/aistack/AskEamos.tsx`** — a *fully built* variant-aware chat panel (streaming via `lib/chat`, suggestion chips, "Coming soon" badge when `runId === null`, disclaimer line). Currently **report-embedded** (a section component), not shell chrome.
- **`app/web/components/aistack/EvidenceSummary.tsx`** + **`AIStack.tsx`** — report "AI evidence summary" block (the teal card top-of-report in screenshot 1).
- **`app/web/components/workbench/SidePanel.tsx:310-318`** — a **"Ask Eamos" tab** in the workbench Scratchpad (Log / Notes / Ask). Parked.
- **`workbench.css:2896-2944`** — a **parked floating `.ai-pill`** (`fixed; bottom:22; right:22; z-index:100`, navy pill) + **`.ai-panel`** (`fixed; bottom:76; right:22; z-index:99; width:420`, slide-up panel). Bottom-**RIGHT**, opposite the Cite dock. Not currently rendered (no JSX references it in the shipped tree — CSS-only ghost).
- **Backend exists** (`/api/v1/chat`, `chat_stream`, `ChatService`) but is gated off; do not wire.
- **`Icon.tsx:127` `IconSparkle`** (✦) — the canonical AI/NL affordance glyph, 1.75 family. Reuse for any Ask-Eamos launcher.

### 1c. Top nav — no account, no bottom chrome
- **`app/web/components/layout/TopNav.tsx`** — logo left + one right slot (default "Patient reports"). Used by **`/report`** and **`/compare`** (`ReportClient.tsx:457` passes `right={<ModePill current="report" />}`).
- **Workbench does NOT use `TopNav`** — `WorkbenchClient.tsx:63-72` rolls its own `.nav-wrap` (`workbench.css:27`, `z-index:50`) with `<ModePill current="workbench" />`. **So the nav chrome is not byte-identical across surfaces** — a key constraint for where shared chrome can live.
- **`app/web/components/layout/ModePill.tsx`** — the Report·Workbench·Batch switcher; the *one* shared element in every surface's right nav slot.
- **No persistent account/settings affordance exists anywhere in the product shell.** The only account entry today is the landing/`/account` top-nav `AuthMenu` (below) — never present on `/report`·`/workbench`·`/compare`.

### 1d. Account / auth — REAL routes + a REAL avatar menu already exist (big reuse)
- **`app/web/components/auth/AuthMenu.tsx`** — a **complete avatar + account-menu component**. Signed-in: avatar (first-letter, `Avatar` :319, teal/`#fff`) + truncated email + chevron → dropdown (`role="menu"`, "Signed in as {email}", **My account** → `/account`, **Sign out** → `signOut()`). Signed-out: **Sign in** / **Register** → anchored `AuthPanel` popover. Full a11y: `aria-haspopup="menu"`, `aria-expanded`, Esc + outside-click close, **focus returns to trigger** (:34). `tone="dark"|"light"`. Currently mounted **top-right** in `LandingNav` + `PageHeader` (`/account`), **never in the product shell**.
- **`app/web/components/auth/AuthProvider.tsx`** — `useAuth()` → `{ configured, loading, user{id,email}, signOut, … }`. `configured` is false when Supabase env is absent → graceful "not configured" mode. **Identity source = `user.email`; avatar = first letter.**
- **Real routes that exist** (`app/web/app/**/page.tsx`): `/account` (saved variants + ClinVar evidence ledger + a "Free plan / Upgrade → `/#pricing`" header), `/account/update-password`, `/auth`, `/checkout`, `/checkout/success`, `/terms`, `/privacy`.
- **Routes that do NOT exist (net-new if linked):** `/settings`, `/billing`, `/pricing` (pricing is an anchor `/#pricing` on landing; checkout is `/checkout`).

### 1e. The shared rail (where a bottom cluster would live)
- **`app/web/components/layout/WorkRail.tsx`** + **`work-rail.css`** — `<WorkRail>` is imported by **`ReportClient`, `CompareClient`, `WorkbenchShell`** (graphify-confirmed). A sticky flex column: `.work-rail-head` (toggle + title + action) → scrollable `.work-rail-body` (flex:1, `overflow-y:auto`). States: inline expanded (336px) ↔ collapsed icon-rail (48px, `.work-rail-stub` vertical label) ↔ `<1200px` off-canvas drawer (`transform:translateX(-100%)`, scrim, FAB). **No footer region today** — the body owns all vertical space below the head. `.wr-section` = the airy icon-led grammar (leading monochrome `Icon*` glyph, uppercase Inter label, far-right quiet `IconChevron`; groups separated by whitespace rhythm).
- **z-index landscape (no `--z-*` scale exists — confirmed `grep`):** nav `.nav-wrap:50`, `TopNav` `z-50`, inline rail `:45`, drawer `:60`, scrim `:55`, **rail FAB `:50` (collides with nav)**, `CiteChip:900`, parked `.ai-pill:100`/`.ai-panel:99`, edit-popover `:50`, export-backdrop `:200`. `AuthMenu` dropdown is `z-[60]`. The workbench-chrome audit already proposes a `--z-*` scale; this dock must slot into it.

---

## 2. Bottom-left cluster proposal

### Decision: **footer of `<WorkRail>`, NOT a new fixed dock**

The reference shells (yorby screenshot: avatar top-left, nav groups, **language selector pinned at the very bottom of the left rail**) put the utility cluster *inside the rail column as a non-scrolling footer*, not as a free-floating fixed dock. For Eamos this is the right call because:

1. **The rail already owns the left edge** on all three surfaces; a fixed `bottom:16;left:16` dock (today's CiteChip) **overlaps** the rail and fights its collapse/drawer states. A footer rides the rail's own width transitions for free.
2. **`useSyncExternalStore` collapse + drawer machinery already exists** in `WorkRail` — a footer inherits all three responsive states with no new fixed-position bookkeeping.
3. **One stacking context.** A rail footer sits at the rail's `z-index` (45 inline / 60 drawer); no new top-of-stack `z:900` element (today CiteChip's `900` floats above *everything*, including modals at `200` — a latent bug).
4. ui-ux-pro-max *Sticky Navigation* (Medium): "fixed nav should not obscure content." A fixed corner dock obscures the bottom of the scrollable rail body (which is exactly why CiteChip needed a manual collapse-to-launcher). A footer *reserves* its space instead of overlapping.

**Structure:** add a third, non-scrolling flex region to `.work-rail` —
`.work-rail-head` (flex:0) → `.work-rail-body` (flex:1, scrolls) →
**`.work-rail-foot` (flex:0, the new cluster)**. The body's `overflow-y:auto`
already clips between head and foot, so the foot never scrolls away.

```
┌─ EXPANDED RAIL (≥1200px, 336px) ───────────────┐
│  [‹]  REPORT CONTROLS              [＋ Save]    │  ← .work-rail-head
│ ──────────────────────────────────────────────│
│  ◇ ON THIS PAGE                            ⌄    │
│  ◇ RELATED VARIANTS                        ⌄    │  ← .work-rail-body
│  ◇ SAVE                                    ⌄    │     (scrolls)
│        · · ·  (scrollable controls)            │
│                                                │
│ ════════════════════════════════════════════ │  ← hairline (--line)
│  ✦  Ask Eamos                    ⟨COMING SOON⟩ │  ┐
│ ──────────────────────────────────────────────│  │ .work-rail-foot
│  (S)  steven@…           account menu  ⌄       │  ┘ (flex:0, pinned)
└────────────────────────────────────────────────┘
```

`✦ Ask Eamos` = a full-width launcher row (`IconSparkle` + label + a muted
`COMING SOON` tag, disabled/`aria-disabled`). `(S) steven@… ⌄` = the reused
`AuthMenu` in a rail register (avatar + truncated email + chevron) opening the
existing account dropdown **upward** (`origin-bottom-left`).

```
┌ COLLAPSED 48px ICON-RAIL ┐
│        [›]               │  head (expand toggle)
│                          │
│    R E P O R T           │  .work-rail-stub (vertical)
│    C O N T R O L S       │
│                          │
│ ════════════════════════ │  hairline
│        ✦                 │  ┐ foot — icon-only, tooltip
│        (S)               │  ┘ on hover/focus; menu opens
└──────────────────────────┘     as a right-anchored popover
```
Collapsed: foot shows **icon-only** affordances (`✦` sparkle, `(S)` avatar),
each with `title` + `aria-label`; the account menu opens as a flyout to the
**right** of the 48px rail (it can't open downward — no room). Mirrors how the
`.work-rail-stub` already handles the collapsed body.

```
┌ NARROW / DRAWER (<1200px) ────────────────┐
│  ▤ Report controls            (FAB opens) │  the rail is an off-canvas
│  … the rail (incl. foot) slides in as the │  drawer; foot rides along at
│  drawer; account + Ask sit at its bottom  │  the bottom of the panel.
└────────────────────────────────────────────┘
  When the drawer is CLOSED, the account avatar is not visible in-shell.
  → see Open Question Q4: a small persistent avatar in the top nav for the
    drawer-closed case, OR accept "account lives in the drawer on mobile."
```

**Footer tokens (DESIGN.md-compliant):** top hairline `0.5px var(--line)`;
rows reuse `.wr-section-head` metrics (7px/8px padding, `--ink-2`, hover
`--bg-soft`); avatar `--teal`/`#fff` (already in `AuthMenu`); the COMING-SOON
tag = the same pill the `AskEamos` header uses (`10px`/700/uppercase,
`--ink-3` on `--bg`, `0.5px --line`). Motion via `--dur-1`/`--ease-standard`.

---

## 3. Ask Eamos placement — options + recommendation

All three keep it **COMING SOON** (parked). The launcher affordance is real;
the panel it would open is a placeholder.

| Option | What | Pros | Cons |
| --- | --- | --- | --- |
| **A — Rail-footer launcher → left-docked panel (Claude pattern) ⟵ RECOMMEND** | `✦ Ask Eamos` row in `.work-rail-foot`; (when live) opens a panel docked over the left/rail column, canvas stays centre-right. | Matches the Claude reference (chat bottom-left, canvas centre). One home, shared by all surfaces. Reuses `IconSparkle` + the built `AskEamos` panel body. Sits in the rail's stacking context. | Rail is narrow (336px) — a *docked* panel would need to widen the rail or overlay it (future, when un-parked). |
| **B — Reuse the parked `.ai-pill`/`.ai-panel` (bottom-RIGHT)** | Un-ghost the existing CSS: floating pill bottom-right, slide-up 420px panel. | Already built in CSS; tool-aware context slot exists. | **Bottom-right, not bottom-left** — contradicts the brief's convention and the screenshots. Re-introduces a fixed `z:99/100` floater (the exact stacking mess we're removing with CiteChip). Splits the cluster across two corners. |
| **C — Slide-over from the right edge** | Launcher in rail foot, panel slides over from the right. | Lots of room; doesn't fight the rail. | Slide-over from the right competes with the report/canvas content area and any future right-rail; heavier than the brief's "docked bottom-left" intent. |

**Recommendation: Option A.** Launcher row in the rail footer, opening (when
un-parked) a left/rail-docked panel — the Claude posture in the screenshot.
Until funded, the launcher is a **disabled COMING-SOON row** (no panel opens, or
opens a tiny "Variant-aware chat is coming" placeholder reusing the `AskEamos`
disabled-state copy at `AskEamos.tsx:228`).

**Placeholder affordance spec:** full-width button, `IconSparkle` (monochrome
`--ink-2`, not teal — it's a rail glyph) + "Ask Eamos" (`--ink-2`, Inter 600) +
right-aligned `COMING SOON` tag. `aria-disabled="true"`, `title="Variant-aware
chat — coming soon"`. On click (optional): toast/inline "We're wiring this to
your report next." No network, no panel. Keep the `Icon.tsx` family + `--dur-*`.

---

## 4. Account / Settings menu

**Reuse `AuthMenu.tsx` wholesale** — it already is the avatar + account dropdown
with full a11y. Add a rail register (a third tone, or a `placement="rail-foot"`
prop) so the dropdown opens **upward-left** (`origin-bottom-left`) instead of
top-right. Do **not** rebuild the menu.

**Menu contents (signed in):**
| Item | Route | Real? | Notes |
| --- | --- | --- | --- |
| "Signed in as {email}" header | — | ✅ | from `useAuth().user.email` (already rendered) |
| **My account** | `/account` | ✅ real | already in `AuthMenu` |
| **Billing / Upgrade** | `/#pricing` (or `/checkout`) | ⚠️ partial | `/account` already shows "Free plan · Upgrade → `/#pricing`"; reuse that target. A dedicated `/billing` route is **net-new** — see Q3. |
| **Settings** | `/settings` | ❌ net-new | no settings route exists. **Recommend: omit until there's a settings surface**, or point at `/account` (which IS the settings-ish surface today). Don't invent `/settings`. |
| **Sign out** | `signOut()` | ✅ real | already in `AuthMenu` |

**Signed-out:** `AuthMenu` already renders **Sign in / Register** → anchored
`AuthPanel`. In the rail foot, render the same, compactly (a single "Sign in"
row that opens the auth popover upward). When `configured === false` (no Supabase
env), `AuthMenu`'s auth actions already degrade gracefully — but **see Q1**: do
we show the account chrome at all before auth is fully wired in prod?

**Identity / avatar source:** `user.email` → first-letter avatar (`Avatar` in
`AuthMenu` :319). No PII beyond the email the user already sees.

**a11y (already satisfied by `AuthMenu`, preserve on relocation):**
- `role="menu"` + `role="menuitem"`, `aria-haspopup="menu"`, `aria-expanded`.
- Esc closes + **returns focus to the trigger** (`triggerRef.current?.focus()` :34).
- Outside-click closes (`mousedown` listener).
- ui-ux-pro-max *Keyboard Navigation* (High) + *Focus States* (High): the menu
  items are real `<a>`/`<button>`; focus rings present (`:focus-visible` box-shadow).
  When relocated to the rail foot, **verify tab order** stays logical (head →
  body → foot → account), and the **upward** popover doesn't trap focus.

---

## 5. Cite / Feedback relocation

**Owner's ask:** get Cite/Feedback **off** the prime bottom-left corner "for now."
The account/Ask cluster claims that corner.

**Recommendation: split by concern, and SCOPE Cite to `/report`.**

- **Cite** is intrinsically **report-centric** (it cites *a variant report* with
  `{variant_display}` + access date + report version). It has no meaning on
  `/workbench` or `/compare`. → **Move Cite into the `/report` chrome**, not the
  global shell. Two viable homes:
  - **(preferred) the `/report` `TopNav` right slot / a small action group** beside the `ModePill`, as a `⌗ Cite` button (reusing `IconShare`/a quote glyph) that opens the existing `CiteModal`. Report already has a header action region.
  - or a **`/report`-only rail-foot row** (above the account cluster) — but that mixes a report action into the shared rail foot, so the TopNav home is cleaner.
- **Feedback** is **global** (any surface, mailto). → **Move Feedback into an
  overflow "⋯ / Help" affordance** — either a small item in the **account menu**
  ("Send feedback") or a tiny "⋯" button in the nav. Lowest-friction: add
  **"Send feedback"** as a `role="menuitem"` in the relocated `AuthMenu` dropdown
  (it already renders a menu; Feedback's `mailto` builder moves there).

**Migration — preserve the load-bearing bits (CiteChip is global today):**
1. **Keep the `?cite=1` deep-link.** Today `CiteChip` listens for it globally. On relocation, the **`CiteModal` mount + the `?cite=1` listener must move with Cite into the `/report` chrome** (the deep link only ever targets a report). Extract the modal-state + `searchParams` listener into a small `useCiteModal()` hook so the `/report` Cite button and the deep link share one path (mirrors today's `openCite`).
2. **Preserve `{variant_display}` resolution** (`CiteChip.tsx:64-75`) — it already early-returns `null` off `/report`, so scoping to `/report` is a natural fit.
3. **Preserve the collapse-pref** only if Cite stays a persistent dock; if Cite becomes a `TopNav` button, the `eamos.cite-dock.collapsed` store + `«/»` launcher are **removed (your-own-orphan cleanup)**.
4. **Remove `<CiteChip>` from `providers.tsx`** (global mount) once Cite/Feedback have new homes; the global shell no longer carries it.

---

## 6. Cross-surface impact

`<WorkRail>` is shared by **`/report`, `/workbench`, `/compare`** — so a rail-foot
cluster is a **GLOBAL-shell** decision, not workbench-only.

**Global (all three surfaces) if we adopt the rail foot:**
- New `.work-rail-foot` region in `WorkRail.tsx` + `work-rail.css` → appears on
  report·workbench·compare automatically. Account + Ask-Eamos become persistent
  on every product surface (they are not today).
- `<CiteChip>` removed from `providers.tsx` → disappears from `/`, `/account`,
  etc. (where it was meaningless anyway).

**Per-surface:**
- **Cite** becomes **`/report`-only** chrome (TopNav button + scoped modal/deep-link).
- **Feedback** stays global but moves into the account menu / overflow.
- **Workbench rolls its own `.nav-wrap`** (not `TopNav`) — so if any chrome lands
  in the *nav* (e.g. a top-right avatar fallback for the drawer-closed mobile
  case, Q4), it must be added in **two** places (`TopNav` for report/compare +
  `.nav-wrap` for workbench) or unified first. The **rail foot avoids this** —
  one shared `WorkRail` covers all three. (Argument *for* the rail foot.)

**z-index / stacking (tie to the proposed `--z-*` scale):**
- The rail foot inherits the rail's z (`45` inline, `60` drawer) — **no new
  top-of-stack element.** This *fixes* today's `CiteChip z:900` anomaly (it
  floats above the `z:200` export modal).
- The **account dropdown** opens at the rail's layer; ensure it sits **above the
  rail body** but **below true modals**. In the `workbench-chrome.md` proposed
  scale (`--z-track:5 / --z-rail:45 / --z-nav:50 / --z-drawer:60 /
  --z-popover:70 / --z-pill:100 / --z-modal:200`), the dropdown = **`--z-popover`
  (70)**; `AuthMenu`'s current `z-[60]` should adopt that token. Define the
  scale once (globals.css) and consume it — do **not** add another arbitrary value.
- ui-ux-pro-max *Stacking Context* (High): the rail is `position:sticky` (a new
  stacking context). A dropdown rendered *inside* the rail is clipped by the
  rail's `overflow:hidden` — **the foot's popover must render in a portal or the
  rail's `overflow` must be relaxed for the foot row.** Flag for implementation.

---

## 7. Open questions for Steven

1. **Ship account chrome before auth is fully wired in prod?** `AuthMenu` +
   `AuthProvider` exist and degrade gracefully (`configured===false` → "not
   configured"). Do we surface the bottom-left account cluster **now** (showing
   Sign in / Register everywhere), or hold it until Supabase auth is live in
   prod? (Recommend: ship it — it's already graceful, and signed-out "Sign in"
   is a legitimate persistent affordance.)
2. **Global cluster, or workbench-first?** The rail is shared, so the cleanest
   build is global (all three surfaces at once). Do you want it **global from
   day one**, or staged **workbench-only first** (which would mean a workbench-
   local foot, duplicated later — more rework)? (Recommend: global via `WorkRail`.)
3. **Billing/Settings menu items — real routes or omit?** No `/settings` or
   `/billing` route exists. Options: (a) omit both, keep menu = My account +
   Sign out (+ Feedback); (b) "Billing" → `/#pricing` / `/checkout`; (c)
   net-new `/settings` + `/billing` (more scope, backend touches). (Recommend:
   (a)+(b) — My account, Billing→`/#pricing`, Send feedback, Sign out. No
   invented `/settings`.)
4. **Where exactly do Cite + Feedback land?** Proposed: **Cite → `/report`
   TopNav button** (scoped, carries the `?cite=1` deep link + `CiteModal`);
   **Feedback → "Send feedback" item in the account menu** (global mailto).
   Confirm, or prefer a single "⋯ Help" overflow in the nav holding both?
5. **Mobile drawer-closed account access (Q4-adjacent).** When the rail is a
   closed drawer (<1200px), the account avatar isn't visible in-shell. Accept
   "account lives in the drawer on mobile," or add a small persistent avatar to
   the top nav for that case (costs the two-place nav edit — `TopNav` +
   workbench `.nav-wrap`)? (Recommend: accept drawer-only for v1; revisit.)

---

## Summary for the builder (once approved)
- **Reuse, don't rebuild:** `AuthMenu.tsx` (avatar + account dropdown + a11y),
  `useAuth()` (identity/sign-out), `IconSparkle` (Ask affordance), `CiteModal` +
  the `{variant_display}` + `?cite=1` logic, `.wr-section-head` metrics.
- **Net-new:** `.work-rail-foot` region in `WorkRail.tsx`/`work-rail.css`; a
  `placement="rail-foot"` variant of `AuthMenu` (upward popover); a disabled
  COMING-SOON Ask-Eamos launcher row; the `--z-*` scale (shared with the
  workbench-chrome audit); a `useCiteModal()` hook extracted from `CiteChip`.
- **Removed (own-orphan cleanup):** global `<CiteChip>` mount in `providers.tsx`;
  the `eamos.cite-dock.collapsed` store + `«/»` launcher (if Cite → a nav button).
- **No app/web edits in this pass.** Spec is review-gated.
