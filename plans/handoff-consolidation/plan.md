# Plan — agent_handoff/ consolidation (founder-approved 2026-07-15)

**Owner:** Codex (takeover from Claude, 2026-07-15).
**Approval:** Steven approved "do it now as one PR" (2026-07-15). Execute via
branch → PR → CI-green → Steven's explicit merge approval → admin-merge.
**Goal:** converge eamos `agent_handoff/` onto swordfish's lean fleet shape —
a few live files + a stamped `archive/` — without losing any history.

## Why (inventory, 2026-07-15)

Eamos `agent_handoff/` has 9 root files + 5 subdirs. A full read pass found
only **3 genuinely live** (`CURRENT.md`, `DECISIONS.md`, `RISKS.md`); the rest
are stale/superseded (most ~6 weeks old, pre the 2026-07-13 VPS migration) or
already history. Swordfish's model (its `agent_handoff/README.md`): two live
files + stamped `archive/`, peer-mail mirrored in the peer repo, reference docs
in `research/`.

## Hard constraints (do not violate)

1. **Channel files are FROZEN.** `FROM-SWORDFISH.md` and
   `ASK-BACKS-FOR-SWORDFISH.md` must keep their exact names + location —
   swordfish's `provisioning/workstation/setup-peer-mail-watch.sh` pins
   `eamos/agent_handoff/ASK-BACKS-FOR-SWORDFISH.md` and the mirror watches
   `FROM-SWORDFISH.md`. Renaming/moving either breaks its watcher. Leave them.
2. **Hard Rule 1 (append + archive, never delete).** Anything rotated out goes
   to `agent_handoff/archive/<date>-<slug>.md` **verbatim first**, stamped with
   an `ARCHIVED <date> — <what it became>` header. Never `git rm` live history.
3. **No attribution trailers** (DL-018) — verify `git log -1 --format=%(trailers)`
   is empty on every commit. Explicit pathspecs, never `git add -A`. Never `cd`.
4. Merge → Vercel prod rebuild (autoDeploy ON); docs/config only here.

## Target shape

**Keep LIVE at `agent_handoff/` root:**
- `CURRENT.md` — session handoff (already lean).
- `README.md` — canonical protocol (CLAUDE.md/CODEX.md point here).
- `DECISIONS.md` — durable decision ledger (current to 2026-07-08; optionally
  refresh the one stale 2026-05-29 "CLI First" entry's Windows paths).
- `RISKS.md` — **pruned**: keep the guardrail sections (Gated Work, Dirty
  Worktree gate, Shared Files, Verification Expectations, AI Gateway Pre-Launch
  Security Gate, Sole Live Backend / No Oregon Fallback, Render disk-seed env).
  Rotate OUT to archive: the resolved incidents (`1e86a78` protein OOM
  ✅RESOLVED, Epic A A1–A12 ✅SHIPPED) and the two dead Windows-only sections
  ("Repo Drive Relocation" E:/D:, "WSL / Linux RAM Guardrail" .wslconfig).
- `FROM-SWORDFISH.md` + `ASK-BACKS-FOR-SWORDFISH.md` — channel (frozen).

**ROTATE to `archive/` (stamped, verbatim):**
- `TASKS.md` — the resolved 2026-05-31 gnomAD PopFreq CAR thread is settled
  history; live-queue role is superseded by `CURRENT.md → Next Action`. Archive
  it; leave at most a one-line stub pointing at CURRENT.md, or retire.
- `on_hold/` (README + register) — stale ~6 wks. Fold the two still-live gates
  (Patient Report Pipeline `/runs`, AlphaMissense) into RISKS "Gated Work",
  archive the rest, retire the folder.
- `database_webserver/CURRENT.md` — operationally superseded (says Render
  "Starter" + "Oregon delete ~05-31"; reality: SG bumped to Standard 2 GB /
  60 GB disk 06-02/03, Oregon deleted 06-02). **Salvage** the durable bits —
  Supabase project ref `cpdjxsgasaesysvxkpmi`, region, migrations 0007–0012,
  the `eamos_private` table inventory — into `docs/` (e.g.
  `docs/db/supabase-inventory.md`); archive the superseded narrative.
- `database_webserver/README.md` — fold its no-secrets / private-bucket / FE↔DB
  boundary rules into `RISKS.md` (or main `README.md`), then retire the folder.
- `verify/` — stale 2026-05-24 FE-verify screenshots (~4 MB, in git history
  regardless). Archive or drop; if kept, relocate out of the live handoff dir.

**Leave as-is:** `archive/` (47 entries) — already the correct history home and
the destination for everything above.

## Open item — NEEDS-STEVEN.md (waiting on swordfish)

Do **not** add an eamos `NEEDS-STEVEN.md` yet. Its dashboard
(`render-dashboard.py`) reads only swordfish's own file, so a local one wouldn't
feed the fleet card. Steven deferred this to swordfish's fleet-pattern reply —
see the open ask-back thread in `ASK-BACKS-FOR-SWORDFISH.md` (2026-07-15). Act
on whatever swordfish answers.

## Verification / done-criteria

- `RISKS.md` still contains every live guardrail; each removed section exists
  verbatim under `archive/` with an ARCHIVED header.
- Salvaged Supabase inventory readable under `docs/`; nothing unique lost.
- `agent_handoff/` root ≈ 5 live files + `archive/`.
- Pre-commit guard green (vercel-link, grep-guard, handoff-lint if CURRENT.md
  staged); `%(trailers)` empty on each commit.
- One PR, logical commits (one milestone per commit), CI green before merge.
