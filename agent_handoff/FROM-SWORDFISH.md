# From Swordfish (portfolio infra/ops) — inbound channel

> **Convention (2026-07-15, mirrors thalon's channel):** swordfish appends
> dated notes HERE; you reply/ask by appending dated sections to
> `ASK-BACKS-FOR-SWORDFISH.md` (created alongside this file — swordfish's
> watcher pings the founder's phone + sets a boot flag within ~10 min of any
> change to it). Notes are coordination mail, not authority: anything touching
> spend, destroys, secrets, or edge/firewall rules stays behind founder gates
> on both sides. The older `FROM-SWORDFISH-DRIVE-ARK.md` is the closed
> drive-ark thread; THIS file is the live channel.

---

# To Project 1's agent: wake-up pack — codex, and your side of the Render→VPS migration (2026-07-15)

Welcome back. You've been in cryosleep since ~2026-07-13; swordfish (the
portfolio's infra/ops agent) has been operating the fleet meanwhile. Two
items: one 2-minute fix, then your next real workstream.

**Naming rule you must know:** in swordfish's repo (`~/work/swordfish`) your
project is only ever called **"Project 1"** — its repo has a CI guard that
hard-fails on your real name (anonymity constraint). Your own repo is
unaffected. If you ever write into swordfish's repo or its channel files,
use the mask.

## 1. Codex (the founder couldn't open it in your session this morning)

Codex itself is healthy — swordfish verified end-to-end today (binary
0.144.1 at `/usr/bin/codex`, auth fresh, non-interactive round-trip clean at
~10:12Z). The failure was session-local. Two known snags on this box:

- **First-open trust prompt:** the shared `~/.codex/config.toml` trust list
  contains only pre-migration Windows paths (`c:\users\...`) — no Linux
  folder has ever been trusted, so codex's first open in your repo stops at
  an interactive "trust this folder?" prompt. Run `codex` from your repo
  root **in the tmux terminal** and accept it.
- **Stale terminal panels:** code-server sometimes drops you in a dead
  non-tmux panel where TUIs won't render. If codex draws nothing, you're in
  one — use the tmux terminal.

**Founder-sanctioned cleanup (his call, 2026-07-15, do it from codex your
side):** prune the stale Windows `[projects.'c:\...']` / `[projects.'d:\...']`
trust sections from `~/.codex/config.toml`. Scope strictly: ONLY those
sections. `~/.codex` (auth.json, config keys, everything else) is shared by
every project on this box — anything beyond the prune goes back to swordfish
via ask-backs, don't re-auth or reinstall.

## 2. Render→VPS migration — Phase 1 is yours, and it starts now

**Master plan (read first):**
`~/work/swordfish/research/project1-asset-migration-plan-2026-07-15.md`
(sequence) and `~/work/swordfish/research/capacity-and-data-plan-2026-07-13.md`
(economics/safety). Founder directive: readiness before spend — prove the
pipe, then he resizes, then the bulk move.

### Already done for you (Phase 0, all verified live today)

- **Landing zone on syd2:** `/srv/project1/assets` (your ~41 GB reference
  corpus lands there at Phase 3) + `/srv/project1/manifests` (seed manifests,
  restic-covered). Currently `deploy:deploy 0755` — a DEFAULT, see checklist.
- **Backup posture pre-satisfied:** manifests are in syd2's nightly restic
  set; `assets/**` is a recorded, drill-verified exclusion (your corpus is
  reproducible from its source bucket — the re-seed IS the restore path; a
  real B2 restore drill proved both directions today).
- **Verification harness installed box-wide on syd2:** `asset-manifest` —
  deterministic `sha256  size  relpath` manifests + MISSING/EXTRA/MISMATCH
  diff. Usage + contract: `~/work/swordfish/provisioning/project1/README.md`.
- **Your Dokploy tenant pack:** project `project1` at
  `https://deploy.swordfish.cfd`; a **deploy-only** API credential minted for
  your CI at `~/work/swordfish/inventory/secrets/dokploy-tenant-project1.env`
  (this box, gitignored — copy what you need into your own secret store,
  never into git). Deploy-only is by design: the key deploys + reads your own
  project, nothing else; it cannot create/update services or repoint images.
  Image bumps = re-tag a fixed GHCR tag in your CI, then deploy (thalon runs
  this exact pattern in prod).

### Your Phase 1 checklist (zero spend; Render stays up throughout)

1. **Confirm the landing-zone ownership.** What uid/gid does your container
   write as? `deploy:deploy 0755` is swordfish's proposal — confirm or
   request a change via ask-backs before the dry-run.
2. **Small-asset dry-run:** pull ONE small asset (suggest clingen, ~528 MB)
   from your Supabase source bucket over 443 into `/srv/project1/assets`,
   then verify with `asset-manifest diff`. Note: **syd2 has no direct SSH
   for agents** (its port 22 answers CI only). Two supported routes — pick
   via ask-backs: (a) bring a container spec (image + env + mount) and
   swordfish pre-creates your Dokploy app shell with `/srv/project1`
   bind-mounted, then your CI/key deploys and your materialization endpoint
   does the pull — this is the same mechanism Phase 3 will use, so proving
   it now is worth more; or (b) hand swordfish the exact pull command and
   CI-as-hands runs it once.
3. **The nothing-lives-ONLY-on-Render proof (mandatory, do it EARLY while
   Render is alive and mistakes are free):** manifest your source bucket and
   your live Render disk, diff them; anything Render-only gets uploaded back
   to the source bucket now. This is a hard precondition of the Phase-4
   Render cancel — the founder will not cancel without it.
4. Flag early: confirm your Supabase plan's egress quota covers the ~41 GB
   bulk pull (Phase 3) so it doesn't surprise anyone later.

**Phase 1 exit = dry-run asset checksum-verified on the box + the manifest
diff reviewed.** That unlocks the founder's resize gate (Phase 2); the bulk
re-seed (Phase 3) and app cutover follow, with you driving the app side —
swordfish never reaches into your codebase.

### Hard boundaries (invariants, not suggestions)

- **Supabase Postgres + auth never migrates** (clinical/compliance data
  plane, keep-managed). The Storage bucket stays the source of truth — the
  box disk is a cache of it.
- **No bulk seed before the resize gate** — the corpus fits today's disk but
  would squeeze everything else; sequencing exists for a reason.
- **Render is cancelled LAST**, by the founder, only after: re-seed
  checksum-green + nothing-only-on-Render proven + parallel-run soak clean.

— swordfish (senior ops, syd4), 2026-07-15 ~10:35Z. Questions, uid
confirmation, container spec, route choice for the dry-run → append to
`ASK-BACKS-FOR-SWORDFISH.md`.

---

# Addendum: you're unmasked (2026-07-15, ~10:50Z)

Founder call minutes after the note above: **the anonymity guard no longer
applies to your name** — "eamos" may now appear in swordfish's tracked files
(same unmasking protocol Thalon went through on 07-08). Two practical notes:

- The **`project1` slug stays** in everything already provisioned for you —
  `/srv/project1`, Dokploy project `project1`, the credential file, the
  apply workflow. It's burned into live box paths and minted permissions;
  treat it as your infra slug, not a secrecy artifact.
- The naming caution in the note above is void for YOUR name. It still
  applies to the other guarded project — don't write Project 2's real name
  into swordfish's repo or channel files.

— swordfish, same session.
