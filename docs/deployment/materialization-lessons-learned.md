# Deployment / Render / Wiring — Lessons Learned & Best Practices

Author: Claude · Created: 2026-06-21 00:40 +1000
Trigger: the 2026-06-20/21 hotspot session where we tried to seed the
M1/M5/M6/M7/M8 local-evidence batch onto SG and found the documented manual path
worked but was fragile. This is the canonical "do it better next time" doc for
**any** runtime-asset materialization, Render disk seed, or provider/env flip.
The operative step-by-step runbooks remain
`docs/deployment/render-provider-flip-workflows.md` +
`docs/deployment/render-coordinate-assets.md`; this doc is the *principles +
pre-flight checklist* they should link to.

## Root cause (why the gaps existed — fair version)

The gaps were **latent, not ignored**:

- The documented plan was executed faithfully, metadata-first and fail-closed.
- Nobody had reached the **live seed step**, because the work network firewalls
  SSH:22 and the Supabase pooler:5432 (only 443 is open). So the runtime-path /
  transport / env gaps only surfaced the night a hotspot opened those ports.
- Work advanced one low-blast-radius gate at a time (good for safety) but without
  an **end-to-end dry-run** that would have exposed the systems-level gaps.
- Some "gaps" are net-new features (orchestrator, 443-trigger, RepeatMasker
  upload lane), not mistakes.

**Meta-lesson: a deployment process is not "ready" until someone runs it
end-to-end to the actual failure point on the live target.** A green per-step
CLI is not proof; live `/api/v1/health/provider-cache` agreeing is.

## The six concrete gaps and their fixes

| # | Gap found on live SG | Best-practice fix |
| - | --- | --- |
| 1 | Runtime-path env vars UNSET → service reads ephemeral `./data`, not `/var/data`. Seeding to the disk wouldn't flip provider-cache. | **Env-as-code.** Declare every runtime-path env var in a checked-in `render.yaml` blueprint, or make `Settings` RENDER-aware (default to `/var/data/...` on the platform). Never rely on a manual env-set that can silently drift. |
| 2 | No `SUPABASE_STORAGE_S3_*` on the service → only single-stream REST transport; risky for the 29.5 GB dbSNP object. | **Resumable transport for large assets.** Provision the S3 creds on the service so `s3_multipart` works, or make REST range-resumable. A multi-GB seed must survive a dropped connection. |
| 3 | SSH sessions carry none of the service env (Render injects into PID 1 only). | **Run materialization in-process, not over SSH.** An in-process path has the env, the pooler, and Storage all reachable. If you must use SSH, source `/proc/1/environ` (never pass secrets through the command line / transcript). |
| 4 | The seed CLI does not reconcile Supabase metadata → the `materialization_metadata_missing` trap (bit the 2026-06-15 AlphaMissense run twice). | **Reconcile metadata inside the seeder.** The tool that lands the file should also move the `source_asset_materializations` row `download_pending → ready` after disk verification, atomically. |
| 5 | A derived runtime artifact (RepeatMasker compact index) had no durable Storage object and no upload lane → breaks the "Storage durable / disk cache / re-seed = one download" model. | **Every runtime asset gets a durable Storage object** — including *derived* ones — so disaster recovery is a uniform one-command download, not a special-case rebuild. |
| 6 | The whole operation depended on an operator's hotspot to bypass the work firewall. | **Make it network-independent.** A 443-triggerable, admin-only, in-process materialization path runs from anywhere (443 is open everywhere) and removes the hotspot/SSH dependency entirely — including the M3 clinical-table import. |

## Reusable pre-flight checklist (run BEFORE any seed / provider flip)

Do this on the **live target**, read-only, before mutating anything:

1. **Disk:** `df -h /var/data/eamos` — enough headroom for file + temp (large
   files peak at ~2× during download-then-rename unless atomic same-fs).
2. **Readers/tools present** on the live image (`pysam`, `pyBigWig`, `hmmpress`,
   `python`, etc.) — don't assume the image matches local.
3. **Env truth:** confirm the runtime-path env vars actually resolve to
   `/var/data/...` (read PID 1 env, not the dashboard). If they default to
   `./data`, fix #1 first.
4. **Transport creds** for the chosen download mode are present on the service.
5. **Memory cgroup** (`/sys/fs/cgroup/memory.{max,current}`) — confirm the seed +
   reader-open won't OOM the live web process; treat large indexed assets as a
   maintenance-window op.
6. **Durable source exists** in Storage (object + manifest sidecar) for every
   asset you intend to seed — including derived artifacts.
7. **Plan the metadata reconciliation** step up front so provider-cache can
   validate the asset (avoid the metadata-missing trap).

Acceptance signal is **live health JSON**, never file presence alone. After the
flip: `/healthz` green + the specific `source_assets.*.ready` / build-ledger item
agree with the disk proof.

## General best practices (deployment / render / wiring)

- **Durable source vs runtime cache:** Supabase private Storage/Postgres is the
  durable source of truth; Render disk is a runtime cache only. Anything on the
  disk must be re-seedable from a durable source by one idempotent command.
- **No startup / build-time / predeploy downloads of large assets.** Seed only
  through an explicit, idempotent, off-peak process. Startup fails closed if a
  legacy startup-materialization flag is on.
- **Idempotent + manifest-driven.** Materialization should be re-runnable safely:
  skip anything already present+checksum-matched; this doubles as disaster
  recovery.
- **One end-to-end dry-run before declaring "ready."** Reach the real failure
  point on the live target; don't ship a process proven only per-step.
- **Verify via live health, reconcile metadata, then (separately) flip the
  gate.** Keep `LOCAL_EVIDENCE_ENABLED` / provider flips as the *last* step,
  gated on all probes green.
- **Secrets discipline:** never echo secrets into a tool transcript (extract only
  hostnames; an over-broad `grep .env` leaked the S3 key on 2026-06-20 → rotate).
  Prefer in-process env or `/proc/1/environ` over passing creds on a command
  line.
- **Coordination (cross-agent):** do **not** concurrently edit the same lane's
  shared docs/source while the other agent holds a fresh Log Edit-Lock or Shared
  File Lock — surface the work as a CAR and let the lane owner fold it in, or wait
  for release. (Tonight: Codex took the config.py lock to build the fix, so these
  lessons were captured in this new doc + memory instead of editing the locked
  runbooks.)

## Folded into the live runbooks

Status as of 2026-06-21 01:05 +1000 (Claude, after Codex released the Log
Edit-Lock at 00:54):

- ✅ **DONE** `render-provider-flip-workflows.md`: added a "Pre-Flight Checklist
  (required …)" section pointing here + two new Hard Gates marking env-as-code
  (#1) and resumable transport (#2) as REQUIRED.
- ✅ **DONE** `RISKS.md`: added the "manual seed without env-as-code silently
  no-ops provider-cache" and "non-resumable large-asset transport" risks under
  `## Render Persistent Disk + Local-First Asset Seeding — Operational Reality`.
- ⏳ **DEFERRED to Codex** `materialization-plan.md`: replace the per-asset manual
  seed commands with the `eamos_materialize_all --manifest` orchestrator and point
  at the pinned manifest (`materialization-manifest-sg.json`). Held back because
  that file currently carries Codex's uncommitted materialization WIP — Codex
  should fold this in when committing asks A–D (avoids a concurrent edit on the
  same lane's dirty file). Pinned identities live in
  `materialization-robustness-handoff.md` + `materialization-manifest-sg.json`.
