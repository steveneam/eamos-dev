---
name: contract-window
description: Freeze the Eamos schema-first API contract before parallel lanes fork, keep the two TS mirrors in lockstep additively, and thaw at merge. Use before starting a parallel-worktree sprint or any change that touches app/backend/app/schemas/*.py or a backend.ts mirror.
---

# Contract Window

Adapted for Eamos from the Thalon contract-window SOP. A **contract window** is the
span of a parallel-agent sprint during which the shared API contract is **frozen**:
lanes may add to it but never reshape it, so disjoint lanes integrate without
clobbering each other's payload assumptions. Freeze at fork, thaw at merge.

This is the standing rule of Eamos Hard Rule 5 (schema-first, README) made into a
mechanical procedure for the parallel-lane model. It is a documentation/SOP skill —
there is no script; the ratchet is `test_frontend_contract.py`.

## Freeze targets (the contract surface)

The contract is these three files kept in lockstep — the Pydantic source of truth
plus its two TypeScript mirrors:

1. `app/backend/app/schemas/*.py` — the **authoritative** Pydantic request/response
   models. The shape is defined here first.
2. `app/web/lib/backend.ts` — the **active** Next.js frontend TS mirror.
3. `app/frontend/src/lib/backend.ts` — the legacy Vite TS mirror (touch only when
   the surface it types is touched; `/runs` still consumes it).

`test_frontend_contract.py` is the canary that proves the mirrors match the schema.

## Invariants (do not break these inside a window)

- **Additive-only.** Within an open window you may ADD optional fields, new response
  objects, and new endpoints. You may NOT rename, retype, remove, or make-required
  an existing field — that reshapes the frozen contract and breaks a sibling lane
  that already coded against it. A required change waits for the next window.
- **Schema-first ordering.** Land the Pydantic schema change FIRST, then update the
  TS mirror(s) in the same logical change. Never let a mirror lead the schema.
- **Mirror parity.** `app/web/lib/backend.ts` must stay in lockstep with the schema;
  update `app/frontend/src/lib/backend.ts` only if the touched surface feeds `/runs`.
- **One owner per window.** Exactly one lead agent owns the contract for a sprint,
  on the lead terminal. Other lanes consume the frozen contract; they request
  additions through the lead (COORDINATION.md board + a Shared File Lock on the
  schema file), they do not edit the schema in parallel.

## Mechanical sequence (per contract change)

```
1. branch    -> agent/<lane>-<slug> off up-to-date main (never edit the contract on main)
2. contracts -> decide the additive delta; record it on the COORDINATION.md board
3. schema    -> edit app/backend/app/schemas/<x>.py (additive); claim the Shared File Lock first
4. mirrors   -> update app/web/lib/backend.ts (+ app/frontend/src/lib/backend.ts iff /runs)
5. tests     -> cd app/backend && python -m pytest tests/test_frontend_contract.py -q
6. verify    -> backend pytest -q + web `npx tsc --noEmit` (mirror compiles against callers)
7. PR        -> open agent/* PR; the CI gate + human-approved merge apply (never --admin-bypass)
8. freeze    -> on merge the contract is re-frozen; release the Shared File Lock
```

## When to open a window

- Before launching a parallel-worktree sprint (Mode-B, `eamos-worktree-setup.ps1`):
  the lead freezes the contract, prepares each lane's worktree, and only then are
  the lanes launched.
- Before any single change that touches a `schemas/*.py` model or a `backend.ts`
  mirror, even solo — run the mechanical sequence so the mirror never drifts.

## Anti-patterns

- Reshaping a field mid-window "because it's cleaner" — that is what the additive
  rule forbids; open a fresh window for a breaking change.
- Two lanes editing `schemas/*.py` at once — one-owner-per-window exists to stop
  exactly this; the second lane files a Cross-Agent Request instead.
- A mirror edited without the matching schema edit — schema-first ordering, always.
