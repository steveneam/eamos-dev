# Illustrae complement — icon module + `/workbench` LibrarySection + visual dial

> Status: **build runbook, pending Steven's OK on each gated step** (Claude, 2026-06-06).
> Frontend-only; mock-first; targets the Next app at `app/web`. Docs-only —
> no `app/web` code is written until Steven OKs each gated step (see §Gates below).
>
> Sequences three deferred items from the Illustrae competitive-steal log:
> 1. **P1–P2** — clean SVG icon module replacing ad-hoc Unicode glyphs across the
>    rail/library (Illustrae "asset-style restraint" steal, spec §6).
> 2. **P3** — `<LibrarySection>` mounted on `/workbench` (already on `/report` +
>    `/compare`; `onOpen` loads the variant into the viewer).
> 3. **P4** — dial three visual defaults from `phase-3-4-design.md` §9 (here-cue,
>    folder nesting rule, count pills).
> 4. **P5** — paste-ready Codex handoff: Supabase schema + RLS + popularity counter
>    + per-variant condition/panel lookups + Project-100 panel.

---

## Gates

- **No durable structural/visual change ships (is pushed) without Steven's explicit
  OK** — plan recs and runbook entries are not authorization (memory:
  `feedback_subagent_recommendations_not_authorization`).
- **Do not kill Codex's `:3000` dev server.** If Codex has a server running,
  let it stand; open a second tab or use `--port 3001`.
- Every step's verify gate = `tsc` 0 errors + `lint` 0 errors/warnings + browser
  pass on `:3000` checking the specific condition named. Run these in the
  `app/web` directory: `npx tsc --noEmit` and `npm run lint`.
- **Abort on the first `tsc` or `lint` error** before moving to the next step —
  never carry debt forward.

---

## 1. Background: what the glyphs are and where they live

All Unicode glyphs to replace, audited against the live tree:

| Glyph | Location | Current role | Icon name |
| ----- | -------- | ------------ | --------- |
| `⇄` | `SavedVariantCard.tsx:71` (pin button) | pin-for-compare toggle | `IconPin` |
| `✕` | `SavedVariantCard.tsx:78` (remove button) | remove from library | `IconRemove` |
| `✕` | `LibrarySection.tsx:212` (seltoolbar clear) | clear selection | `IconRemove` |
| `⌬` | `LibrarySection.tsx:197` (empty-state glyph) | empty-state icon | `IconBookmark` |
| `▾` | `LibrarySection.tsx:209` (Move-to-folder button label) | folder move menu trigger | `IconFolderMove` |
| `⤓` | `LibrarySection.tsx:319` (drag-over folder chevron swap) | drop-into folder cue | `IconDropInto` |
| `✎` | `LibrarySection.tsx:325` (folder rename button) | rename folder | `IconRename` |
| `✕` | `LibrarySection.tsx:330` (folder delete button) | delete folder | `IconRemove` |
| `✕` | `LibrarySection.tsx:374` (pin chip unpin) | unpin from tray | `IconRemove` |
| `→` | `LibrarySection.tsx:388` (Open-in-Compare button) | navigate to compare | `IconArrowRight` |
| WorkRail toggle chevrons | `WorkRail.tsx:188-189` (inline SVG) | expand/collapse rail | already SVG — no change needed |

Additional canonical icons to define (for completeness; used in the library or
anticipated by adjacent components):

| Icon name | Anticipated use |
| --------- | --------------- |
| `IconPlus` | `+ Save` button label (currently text `+`), `+ New folder` |
| `IconCheck` | `✓ Saved` button label (currently text `✓`) |
| `IconChevron` | Already an inline `<Chevron>` in both `LibrarySection.tsx` and `VariantCardRow.tsx`; consolidate |
| `IconArrowRight` | `Import VCF →` link, `Open in Compare →`, `→` on toolbar links |

---

## 2. Icon module design (P1)

### 2.1 File: `app/web/components/icons/Icon.tsx`

Follow the **exact pattern** of `ToolIcon.tsx` (`app/web/components/workbench/ToolIcon.tsx`):

- One shared `svgProps` object: `viewBox="0 0 24 24"`, `fill="none"`,
  `stroke="currentColor"`, `strokeWidth={2}`, `strokeLinecap="round"`,
  `strokeLinejoin="round"`.
- Named component exports — one `export function IconPin(...)`, one
  `export function IconRemove(...)`, etc. No default export; no union-based
  switch (unlike `ToolIcon`'s `tool` switch — these are individual exports so
  tree-shaking works and call sites are explicit).
- Props signature: `{ size?: number; className?: string }` — `size` defaults to
  `16`, forwarded as both `width` and `height` on the `<svg>`. `className`
  forwarded to the `<svg>`. This matches the 22px / 20px / 14px targets in
  the library without requiring wrapper divs.
- `ReactNode` return type (same as `ToolIcon.tsx:13`).
- No additional dependencies — pure SVG, no icon library.

### 2.2 Canonical SVG paths (Lucide-vocabulary, 24px grid)

All geometry is on the 24px grid; rendered sizes are set via the `size` prop.
These are the paths to implement — use or refine these reference geometries:

| Component | SVG content |
| --------- | ----------- |
| `IconPin` | Two parallel horizontal arrows: `<path d="M7 16H4m13 0h-3M12 4v10"/><path d="M8 12l4-8 4 8"/><path d="M6 16c0 2.2 1.8 4 6 4s6-1.8 6-4"/>` — or a simpler "compare columns" symbol mirroring `ToolIcon`'s compare case; exact path is the implementer's call, but it must read as "send to compare" not "geographical pin" |
| `IconRemove` | `<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>` (× cross) |
| `IconBookmark` | `<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>` |
| `IconFolderMove` | `<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><polyline points="15 13 18 16 15 19"/><line x1="11" y1="16" x2="18" y2="16"/>` |
| `IconDropInto` | `<polyline points="12 5 12 19"/><polyline points="5 15 12 22 19 15"/>` (arrow-down-to-line) |
| `IconRename` | `<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>` (pencil-edit) |
| `IconArrowRight` | `<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>` |
| `IconPlus` | `<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>` |
| `IconCheck` | `<polyline points="20 6 9 17 4 12"/>` |
| `IconChevron` | `<polyline points="6 9 12 15 18 9"/>` (down); the component renders it at 0deg; callers rotate via CSS `transform` for left/right/up — same pattern the existing inline `<Chevron>` components already use |

---

## 3. Phased build order

Each row is a discrete, independently verifiable unit. Do not start a row until
the previous row's verify gate is green. **Steven's OK required before shipping
(pushing) any row marked structural/visual.**

| # | Step | Files touched | Verify gate |
| - | ---- | ------------- | ----------- |
| **P1** | **Icon module — new file only, no consumers yet** | `app/web/components/icons/Icon.tsx` (NEW) | `tsc --noEmit` 0 errors; `lint` 0 warnings; import each named export in a scratch `.tsx` (or run a type-check smoke) to confirm all 10 names resolve; no browser change |
| **P2a** | **Glyph swap — `VariantCardRow.tsx`** (Caret inline SVG → `<IconChevron>`); `SavedVariantCard.tsx` (`⇄` → `<IconPin size={13}>`; `✕` → `<IconRemove size={13}>`) | `app/web/components/icons/Icon.tsx` (add `IconChevron` if not in P1), `app/web/components/library/VariantCardRow.tsx`, `app/web/components/library/SavedVariantCard.tsx` | `tsc` 0; `lint` 0; browser `:3000/report?…` — card pin/remove buttons render SVG icons at same visual weight; disclosure caret works; no functional regression |
| **P2b** | **Glyph swap — `LibrarySection.tsx`** (`⌬` → `<IconBookmark>`; `▾` → `<IconFolderMove>`; `⤓` drag-glyph → `<IconDropInto>`; rename `✎` → `<IconRename>`; delete `✕` → `<IconRemove>`; pin-chip `✕` → `<IconRemove size={11}>`; `→` on Open-in-Compare → `<IconArrowRight>`) | `app/web/components/library/LibrarySection.tsx` | `tsc` 0; `lint` 0; browser on `:3000/compare` or `:3000/report` — empty state, drag-over folder swap, selection toolbar, tray unpin, Compare button all render SVG at correct sizes; seltoolbar `✕` clears selection |
| **P2c** | **Glyph swap — `VariantLibraryRail.tsx` + `WorkRail.tsx`** (only if any residual Unicode glyphs exist after P2a/b; WorkRail's toggle chevrons are already inline SVG so this is likely a no-op, but confirm) | `app/web/components/report/VariantLibraryRail.tsx`, `app/web/components/layout/WorkRail.tsx` (read-only confirm or tiny change) | `tsc` 0; `lint` 0; no visual regression on rail toggle or Save/Saved buttons |
| **P3** | **Mount `<LibrarySection>` on `/workbench`** — add `<LibrarySection onOpen={handleOpen} currentQuery={currentQuery} />` into `WorkbenchShell.tsx`'s `railContent`; `handleOpen` calls `router.push('/workbench?gene=…&cdna=…')` built from the saved variant's `gene`/`variant` fields (mirrors the `reportHrefForQuery` pattern but targeting `/workbench`); `currentQuery` derived from the shell's `gene + ' ' + cdna` props (same pattern as the report's `currentQuery`). The existing `ToolBar` + `SidePanel` block stays at the top of `railContent`; `<LibrarySection>` is appended below it with a `<hr className="wb-rail-divider" />` separator. **GATED on Steven's OK before ship.** | `app/web/components/workbench/WorkbenchShell.tsx`, `app/web/components/library/LibrarySection.tsx` (import only; no logic change) | `tsc` 0; `lint` 0; browser `:3000/workbench` — library section visible below the ToolBar/SidePanel; save a variant on `/report`, switch to `/workbench`, confirm it appears in the rail; click a saved-variant card from `/workbench` → URL navigates to `/workbench?gene=…&cdna=…` (viewer re-fetches, not a full reload); drawer still closes correctly on `<1200px` |
| **P4a** | **Dial: "you are here" cue** — confirm the `data-here='true'` card treatment (§9 item 1) is the 2px `--ink-4` inset bar, NOT a teal cue; read `library.css` line ~655 to confirm it already targets `data-here='true'`; if the CSS is already correct, this is a read-and-confirm step with no file change | `app/web/components/library/library.css` (read-only confirm or 1-line fix) | Browser on `/report` — open report for a saved variant; its card in the rail shows a quiet grey left bar, no teal left bar; teal left bar only appears when checkbox is selected |
| **P4b** | **Dial: folder nesting rule** — confirm `library.css` renders the single `0.5px var(--line)` left rule down a folder's cards (§9 item 2); if already correct (see `library.css` line ~832), this is a confirm step; if not, add the `border-left` | `app/web/components/library/library.css` (read-only confirm or 1-line fix) | Browser — create a folder, move 2 variants in; the folder body shows a faint left rule tying cards to the folder head; no other rules in the rail |
| **P4c** | **Dial: count pills** — confirm `.lib-count` renders as the `--bg-soft2` pill (§9 item 3); if the shipped CSS already has `.lib-count` with `background: var(--bg-soft2)` (see `library.css` line ~720), this is a confirm; if removed, re-add the `min-width/height/padding/border-radius` rule | `app/web/components/library/library.css` (read-only confirm or 3-line fix) | Browser — section headers for "Saved variants", "Folders", "Compare tray" show numeric count as a small pill, not bare text; pill uses soft background, not teal |
| **P5** | **Codex handoff doc** — write `docs/workspace-rail/illustrae-complement-codex-handoff.md` with the paste-ready backend spec (§4 below) | `docs/workspace-rail/illustrae-complement-codex-handoff.md` (NEW) | Doc exists; Codex can act on it without reading this runbook |

---

## 4. P5 — Codex backend handoff (no code, paste-ready)

This section is the complete content of the handoff doc written at P5. It can
also be pasted verbatim into a Codex session.

---

### Codex backend lane — durable variant-library persistence

**Context.** The Eamos variant-library rail (`<LibrarySection>`) is live and
mock-first on `localStorage` (`lib/variant-library.ts`). The frontend store
API is stable and will **not** change shape. This lane replaces the persistence
backend behind the same exported functions so no React component changes.

**Contracts to honour** (Codex must not break these):

- Store exports: `saveVariant / saveVariants / removeVariant / isSaved / getLibrary / subscribe / createFolder / renameFolder / removeFolder / moveVariant`
- Types: `SavedVariant { id, gene, variant, query, raw, folderId?, savedAt, classification?, hgvs_full? }`, `Folder { id, name, createdAt }`
- Store id: `query.toLowerCase()` (dedupe key — must survive round-trip to Supabase)
- Event: `'eamos:library-change'` dispatched after any mutation

#### Supabase schema (suggested — Codex owns final shape)

```sql
-- Collections (frontend name: Folder)
create table collection (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  name        text not null,
  created_at  timestamptz not null default now()
);

-- Saved variants
create table saved_variant (
  id               text not null,          -- query.toLowerCase() dedupe key
  user_id          uuid not null references auth.users(id) on delete cascade,
  gene             text,
  variant          text,
  query            text not null,
  raw              text,
  folder_id        uuid references collection(id) on delete set null,
  saved_at         bigint not null,        -- ms epoch (matches store's savedAt)
  classification   text,                  -- ClassificationTier or null
  hgvs_full        text,
  primary key (id, user_id)
);

-- Popularity counter (for the "Frequently reviewed" Related-variants lane)
create table variant_view_count (
  query_id     text primary key,          -- query.toLowerCase()
  view_count   bigint not null default 0,
  last_viewed  timestamptz not null default now()
);
```

#### RLS

```sql
-- collection: user owns their rows
alter table collection enable row level security;
create policy "owner" on collection
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- saved_variant: user owns their rows
alter table saved_variant enable row level security;
create policy "owner" on saved_variant
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- variant_view_count: public read (the popularity lane is aggregated data,
-- not per-user), but only the service role can write
alter table variant_view_count enable row level security;
create policy "public_read" on variant_view_count
  for select using (true);
-- writes via service-role only (no RLS-bypassing grants to anon/authenticated)
```

#### API endpoints (CRUD mirroring the store)

All routes under `/api/v1/library/`. Auth = Supabase JWT (same pattern as
existing `/api/v1/lookup` etc.). The frontend swaps the localStorage persistence
backend once these exist — no rail component changes.

| Method | Path | Body / Params | Action |
| ------ | ---- | ------------- | ------ |
| `GET` | `/variants` | — | Returns `SavedVariant[]` for the auth user, ordered by `saved_at DESC` |
| `POST` | `/variants` | `SavedVariant` | Upsert (id + user_id dedupe); returns saved row |
| `DELETE` | `/variants/:id` | — | Delete for auth user |
| `GET` | `/folders` | — | Returns `Folder[]` for auth user |
| `POST` | `/folders` | `{ name: string }` | Create, returns new `Folder` |
| `PATCH` | `/folders/:id` | `{ name: string }` | Rename |
| `DELETE` | `/folders/:id` | — | Delete folder; backend moves its variants to `folder_id = null` before deleting |
| `PATCH` | `/variants/:id/folder` | `{ folder_id: string \| null }` | Move variant |

#### Popularity counter

Increment `variant_view_count.view_count` on every `/api/v1/lookup` call (or a
dedicated `POST /api/v1/library/views/:query_id` endpoint the frontend fires on
report load). The "Frequently reviewed" Related-variants lane reads from a
`GET /api/v1/library/popular?limit=10` endpoint (top-10 by `view_count`).
**Frontend blocks no work on this** — the lane is already gated behind a
"Coming soon" state until the endpoint exists.

#### Per-variant condition/panel lookups (upgrades "Same condition" / "Same panel" lanes)

Current v1: these lanes use data already on the report payload
(`associated_conditions`, `locus_context`, `getPanel`). True per-variant lists
for a condition or panel require:

- `GET /api/v1/lookup/condition/:omim_id/variants` → `{ variants: NearbyVariant[] }` — other variants annotated with this condition.
- `GET /api/v1/lookup/panel/:panel_id/variants` → `{ variants: NearbyVariant[] }` — panel's curated variants. Reuses the `/panels` work already in the backlog.

The frontend "Same condition" lane upgrades from informational (condition name +
case count) to clickable `<VariantCardRow>` entries once this endpoint exists.
Same for "Same panel". Flag as a backlog item, not blocking P3/P4 FE work.

#### Project-100 panel definition

The "Same panel" lane uses `lib/panels` → `getPanel(gene)` client-side. The
**Project-100** panel (a curated 100-gene oncology panel discussed in the batch
VCF spec) should be added to the backend panel registry so it appears in the
`getPanel()` response for its constituent genes. Add it to the panel seed data
under whatever mechanism the existing panels are registered (e.g.
`app/backend/eamos/panels/` or the Supabase `panel` table if that migration has
landed). Gene list TBD by Steven — this is a placeholder flag, not a
blocking dep for P1–P4.

---

## 5. Risks

| Risk | Likelihood | Impact | Mitigation |
| ---- | ---------- | ------ | ---------- |
| **Icon size mismatches** — replacing a Unicode glyph with an SVG at the wrong `size` prop leaves the hit target or visual weight wrong | Medium | Low — visual only | Read each call site's current button dimensions (`22px`, `20px`, `14px`, `11px`) and pass the correct `size`; spot-check in browser at each P2 sub-step |
| **`onOpen` full-reload UX on `/workbench`** — `router.push('/workbench?gene=…&cdna=…')` triggers the Next.js router (client-side navigation), but if the workbench page remounts on every push (no `startTransition` / no server component boundary), the viewer flickers or loses scroll state | Medium | Medium | Confirm `WorkbenchShell` is fully client-side (`'use client'`; it is) so the push is a URL-only update; test by clicking a saved-variant card from within `/workbench` — viewer should re-fetch without a full mount cycle. If flicker occurs, investigate whether the `useEffect` dep array on `getGeneViewer` triggers unnecessarily on same-gene push. |
| **`LibrarySection` scroll height on `/workbench`** — the workbench rail is already populated with `ToolBar` + `SidePanel` which can be tall; adding `LibrarySection` below may push it off-screen with no scroll | Medium | Low | Confirm the workbench rail's `.work-rail-body` has `overflow-y: auto` (check `work-rail.css`); if not, the fix is one CSS line — not a structural change |
| **`lint` warnings from icon import paths** — if `app/web` has path-alias rules that don't cover a new `@/components/icons/` import, the build will warn | Low | Low | The existing `ToolIcon.tsx` already lives at `@/components/workbench/`; mirror the same import pattern; confirm `tsconfig.json` `paths` covers `@/components/**` |
| **Unicode glyphs in `library.css` comments** — the design doc references `⌬`, `⤓`, `✎` in comments; these are safe (they're not rendered), but flag them for the implementer so they are not confused with un-replaced render glyphs | Low | None | Note for implementer: CSS comments and `aria-label` strings keep the descriptive text; only the _rendered_ JSX button children are swapped |
| **Codex `variant_view_count` write path** — incrementing a counter on every lookup call adds a Supabase write to the hot path; on concurrent requests this can cause write contention or rate-limit the free tier | Medium | Medium | Mitigate with Postgres `ON CONFLICT DO UPDATE view_count = view_count + 1` (single atomic upsert); consider a debounced write or a background queue if volume warrants it |

---

## 6. Self-check against the brief

- Icon module at `app/web/components/icons/Icon.tsx` — named exports in
  `ToolIcon.tsx` SVG style: **P1**.
- Ad-hoc glyphs replaced across `SavedVariantCard`, `LibrarySection`,
  `VariantCardRow`, `WorkRail` (WorkRail is already SVG, confirmed at P2c):
  **P2a–P2c**.
- Shared `<LibrarySection>` on `/workbench` via `WorkbenchShell.tsx` with
  `onOpen = router.push('/workbench?gene=…&cdna=…')`: **P3**.
- Three visual defaults from `phase-3-4-design.md` §9 dialled (here-cue,
  folder rule, count pills): **P4a–P4c** (confirm or 1-line fix each).
- Paste-ready Codex handoff with Supabase schema + RLS + popularity counter +
  per-variant condition/panel lookups + Project-100 panel: **P5**.
- Every durable structural/visual step gated on Steven's explicit OK: **§Gates**.
- No `app/web` code edited in this doc: correct — runbook only.
