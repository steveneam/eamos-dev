# Plan — agent_handoff/ consolidation (founder-approved 2026-07-15)

**Owner:** Codex (takeover from Claude, 2026-07-15).
**Approval:** Steven approved "do it now as one PR" (2026-07-15). Execute via
branch → PR → CI-green → Steven's explicit merge approval → admin-merge.
**Updated:** 2026-07-15 21:39 +1000 by Codex after direct comparison with
`/home/deploy/work/swordfish/agent_handoff` and Steven's final layout direction.
**Goal:** converge eamos `agent_handoff/` onto swordfish's lean fleet shape —
a few live files + a stamped `archive/` — without losing any history.

## Why (inventory, 2026-07-15)

Eamos `agent_handoff/` started with 9 tracked root files + 5 subdirs, then the
VPS migration added four loose prompt/drive-note artifacts. A full read pass
found only the canonical current handoff and peer-mail channels belonged on
the live surface; durable risk/decision ledgers are reference docs, while the
rest is stale/superseded history. Swordfish's live model is `CURRENT.md` +
`NEEDS-STEVEN.md` + convention `README.md` + stamped `archive/`; peer-mail
files remain in the peer repo as pinned exceptions.

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
- `CURRENT.md` — lean session handoff.
- `NEEDS-STEVEN.md` — open founder action queue, matching Swordfish's format.
- `README.md` — canonical Eamos coordination protocol.
- `FROM-SWORDFISH.md` + `ASK-BACKS-FOR-SWORDFISH.md` — watcher-pinned peer-mail
  exceptions; names and locations remain frozen.
- `archive/` — stamped historical material only.

**Move durable live references outside the handoff:**
- `DECISIONS.md` → `docs/governance/decisions.md`.
- pruned `RISKS.md` → `docs/operations/risks-and-guardrails.md`.
- Update every live pointer; leave dated archives/build logs unchanged.

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
  boundary rules into `docs/operations/risks-and-guardrails.md` (or main
  `README.md`), then retire the folder.
- `verify/` — stale 2026-05-24 FE-verify screenshots (~4 MB, in git history
  regardless). Archive or drop; if kept, relocate out of the live handoff dir.
- VPS migration artifacts (`FROM-SWORDFISH-DRIVE-ARK.md`, the first-boot resume
  prompt, and both `drive-notes/*` prompts) — stamp and archive with each
  original body preserved byte-for-byte; retire the emptied directories.

**Leave as-is:** `archive/` (47 entries) — already the correct history home and
the destination for everything above.

## NEEDS-STEVEN.md + fleet dashboard

Steven directed the live-Swordfish layout alignment before PR #8 merges, so
add Eamos's local queue now with the open M-013 branch-protection/CI decision.
Swordfish's dashboard currently reads only its own queue; ask Swordfish through
the pinned outbound channel to add peer queue ingestion or confirm the fleet
collector pattern. Dashboard ingestion is follow-up work and does not block the
Eamos layout or the already-approved Graphify retirement.

## Verification / done-criteria

- `docs/operations/risks-and-guardrails.md` contains every live guardrail; each
  removed section exists verbatim under `archive/` with an ARCHIVED header.
- Salvaged Supabase inventory readable under `docs/`; nothing unique lost.
- `agent_handoff/` root is exactly `CURRENT.md`, `NEEDS-STEVEN.md`, `README.md`,
  the two peer-mail files, and `archive/`; no empty legacy directories remain.
- All four loose VPS migration artifacts are stamped in `archive/`, and body
  hashes match the original bytes (including the two CRLF prompts).
- Pre-commit guard green (vercel-link, grep-guard, handoff-lint if CURRENT.md
  staged); `%(trailers)` empty on each commit.
- One PR, logical commits (one milestone per commit), CI green before merge.
