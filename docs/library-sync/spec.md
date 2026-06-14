# Variant Library — Account Sync (spec)

**Status:** contract agreed with Codex (2026-06-14), queued to build · **Surface:** the shared variant library used across Report · Paper · Batch · Workbench
**Owners:** Codex (Supabase table + RLS + endpoints, `app/backend`) · Claude (FE sync layer, `app/web/lib/variant-library.ts`)

---

## 0. What this is

Make the saved variant library (saved variants **and** folders) **follow the user's account across devices** instead of living only in this browser. Today it's `localStorage`-only; this spec adds a backend mirror + an FE sync layer so a signed-in user sees the same library everywhere, while anonymous use is unchanged.

---

## 1. Current state (grounded)

- One store, one key: `app/web/lib/variant-library.ts` holds `{ variants: SavedVariant[], folders: Folder[] }` under `localStorage['eamos.library.v1']`. It's the single source of truth.
- All four surfaces render the same `LibrarySection` (`components/library/LibrarySection.tsx`) reading that store via `useLibrary()` — Report (`VariantLibraryRail`), Paper (`PaperClient`), Batch (`CompareClient`), Workbench (`WorkbenchShell`). Saved variants + folders are already shared across surfaces; they're just **not tied to the account**.
- `SavedVariant.id = query.toLowerCase()` (dedupe key). `Folder.id` is a generated string. Both carry timestamps (`savedAt` / `createdAt`).
- The store already emits a change event + listens to cross-tab `storage`, so writes propagate live within a browser.

**The gap:** clearing browser storage or switching devices loses the library. The `RailFoot` shows "Sign in / Register", but the library is local-only.

---

## 2. Scope

**In:** a Supabase table mirroring `{ variants, folders }`; login-gated `GET`/`PUT /api/v1/library`; an FE sync layer in `variant-library.ts` (pull-on-login → merge with local → debounced push), with `localStorage` kept as the offline cache + anonymous fallback.

**Out (v1):** normalization (stays JSONB), real-time/websocket sync, per-item endpoints, cross-account sharing, tombstone-based delete propagation (see §5 limitation), optimistic-concurrency conflict UI.

---

## 3. Storage (Supabase) — Codex

One row per user (whole-document JSONB mirror — agreed, no normalization for v1):

```
table user_library
  user_id     uuid     primary key  references auth.users(id) on delete cascade
  variants    jsonb    not null default '[]'   -- mirrors SavedVariant[]
  folders     jsonb    not null default '[]'   -- mirrors Folder[]
  updated_at  timestamptz not null default now()
```

- **RLS:** a user can `select`/`insert`/`update` only their own row (`auth.uid() = user_id`).
- `updated_at` bumped on every write (trigger or in the handler) — the whole-document conflict signal.

---

## 4. Endpoints (contract) — Codex

Login-gated (same auth posture as `/chat/stream`). Whole-document, no per-item routes in v1.

```
GET /api/v1/library
  → 200 { variants: SavedVariant[], folders: Folder[], updated_at: string }
  → empty row (first call) returns { variants: [], folders: [], updated_at: null }

PUT /api/v1/library
  body  { variants: SavedVariant[], folders: Folder[] }
  → 200 { updated_at: string }       -- echoes the new server timestamp
```

- The backend treats `variants`/`folders` as opaque JSON mirrors of the FE shapes — it does not reshape or validate item internals beyond basic type/size guards.
- Optimistic concurrency (`If-Unmodified-Since` / an `updated_at` precondition on PUT) is **deferred** — add later only if multi-device conflict loss becomes a real problem.

### FE mirror shapes (already defined in `variant-library.ts`)

```
SavedVariant { id, gene, variant, query, raw, savedAt, folderId, classification?, hgvs_full? }
Folder       { id, name, createdAt }
```

---

## 5. FE sync layer + merge semantics — Claude

`variant-library.ts` gains an optional sync layer. **`localStorage` stays the source of offline/anonymous state**; the account row is the cross-device mirror.

1. **Anonymous:** unchanged — read/write `localStorage` only. No network.
2. **On login / session present:** `GET /api/v1/library` → **union-merge** with the local store, then `PUT` the merged result (so a first sign-in *merges the local library up*, never clobbers it).
3. **On change while signed in:** write `localStorage` (as today) **and** schedule a debounced `PUT` (~1–2s) of the whole document.
4. **On logout:** stop syncing; keep the local cache as-is.

### Merge rule (union, keep-wins)

- **Variants:** union by `id`; on collision keep the one with the newer `savedAt`.
- **Folders:** union by `id`; keep the newer `createdAt` / last-edited name.
- Variant `folderId` references survive because folders are merged by the same `id`.

### Known v1 limitation (documented, accepted)

Union-merge **favours not losing a save** over propagating deletes — there are no tombstones, so a variant deleted on device A *may reappear* after device B (which still had it) syncs. Acceptable for a bookmark library; revisit with tombstones or per-item DELETE if it becomes annoying.

---

## 6. Claude ↔ Codex split

| Lane | Work |
|---|---|
| **Codex (`app/backend`)** | `user_library` table + RLS migration; `GET`/`PUT /api/v1/library` (login-gated), treating `variants`/`folders` as JSONB mirrors + `updated_at`. Basic size/type guards. No normalization. |
| **Claude (`app/web`)** | Sync layer in `variant-library.ts` (pull-on-login → union-merge → debounced push), behind auth state; `localStorage` stays offline cache + anon fallback. No surface/UX change — `LibrarySection` is unchanged; it just reads a store that now syncs. Same `.eamos-mock`/offline tolerance as other clients (no endpoint → local-only, no error). |

**Backend-led contract — frozen here.** Claude builds the FE sync layer against this; swaps from local-only to synced the moment the route lands (a missing route just means local-only, like the other clients' 404 fallback).

---

## 7. Decisions locked (from the 2026-06-14 Codex exchange)

- JSONB whole-document mirror of `{ variants, folders }` for v1 — **don't normalize** unless query/reporting needs force it.
- **Anon→login merge is FE-owned** (localStorage is the source of offline/anon state).
- Whole-document `GET`/`PUT` with `updated_at`; **optimistic-concurrency headers deferred**.
- No Render/Supabase env flips, no startup downloads, no provider flip to build this.

---

## 8. Value & impact

- **Value:** the library a clinician/researcher curates (across paper-ingest, search, batch, workbench) follows their account — the cross-surface continuity that prompted this. Low conceptual risk: the store shape is unchanged, so it's a drop-in mirror.
- **Impact:** additive and login-gated. Anonymous use is byte-identical to today. The only behavioural change is for signed-in users, who gain cross-device persistence. The one honest tradeoff is delete-propagation (§5).

---

## 9. Open questions / to confirm

1. **Delete propagation** — accept the v1 keep-wins limitation (§5), or invest in tombstones/per-item DELETE now? (lean: accept for v1.)
2. **Debounce + size cap** — confirm a reasonable PUT debounce (~1–2s) and a soft cap on library size before we'd need pagination/normalization.
3. **Folder rename conflicts** — last-write-wins by edit time is the v1 rule; confirm that's fine (no merge-of-names).

---

## Source connections

- FE store: `app/web/lib/variant-library.ts` · shared UI `app/web/components/library/LibrarySection.tsx` · per-surface rails (`VariantLibraryRail`, `PaperClient`, `CompareClient`, `WorkbenchShell`).
- Auth posture mirror: the chat endpoint's login gate (`/chat/stream`).
- Sibling: paper→variants surface (`docs/paper-variants-ui/spec.md`) writes into this library; this spec makes those saves portable.
