# Render to syd2 Phase-3 Seed and Cutover

Status: Phase 3a exact-manifest green; internal Phase 3b Compose proof and
two-party tenant-grant verification green; external proxy, traffic cutover,
and Phase 3c remain held

Last verified: 2026-07-17 10:56 +0000 - Codex

Steven directly issued `phase 3 go` in the Eamos session at 2026-07-17
08:10 UTC. That authorizes the coordinated Phase 3 sequence: bulk seed,
backend cutover, and a parallel-run soak. It does not authorize the deferred
syd2 resize, destructive cleanup, or Phase 4 Render cancellation. Render must
remain live throughout Phase 3.

The controlling cross-repository plan is
`/home/deploy/work/swordfish/research/project1-asset-migration-plan-2026-07-15.md`.
Phase 1 and its nothing-lives-only-on-Render proof are already green. This
runbook freezes the expanded 23-file runtime contract discovered during the
Phase 3 review and supersedes the old seven-item command for the bulk seed.

## Frozen landing contract

| Set | Disposition | Files | Bytes |
| --- | --- | ---: | ---: |
| A | Original SG seed manifest | 7 | 40,847,382,851 |
| B | Preserved AlphaMissense/Pfam runtime files; all land | 10 | 5,061,937,840 |
| C | Additional runtime-required assets; all land | 6 | 2,034,216,254 |
| C | Superseded inputs and source-only sidecars; excluded | 22 | 618,689,240 |
| Total source proof | Fully classified | 45 | 48,562,226,185 |
| Final syd2 runtime tree | Exact landing set | 23 | 47,943,536,945 |

The authoritative machine-readable classification is
`app/backend/app/runtime-tree-manifest-syd2.json`. The canonical target-tree
manifest is `app/backend/app/runtime-tree-manifest-syd2.txt`; it has exactly 23
lines in `sha256  size  relpath` format and SHA-256:

```text
c907fa2aab78eb31a5ae30dcbc3e914ed89d90584d5aea845f360cdc25c20cbb
```

That target manifest is byte-for-byte identical to the independently captured
23-file Render runtime manifest. The JSON retains each predictor's source,
role, licence status, approval status, and launch gate.

The host contract remains:

```text
syd2 runtime root:      /srv/project1/assets/runtime
container runtime root: /var/data/eamos/bio_assets
bind mount:             /srv/project1/assets/runtime -> /var/data/eamos/bio_assets
host manifest root:     /srv/project1/manifests
container identity:     1000:1000
```

`/srv/project1/assets/.drill` is an untouched sibling of `runtime`; it must
never enter the application mount or target-tree comparison.

## Release gates before the first GET

All of the following must be recorded in one preflight window:

1. The commit containing this runbook, materializer, JSON classification, and
   canonical manifest has full CI green. The one-off shell pins the immutable
   backend image digest published by that run, uses `--pull=never`, and proves
   the live digest before executing Python.
2. The host proves numeric `1000:1000`, the exact bind mount above, an existing
   directory with zero entries at the runtime root, no symlinks, the `.drill`
   canary unchanged, and the expected one-off container absent.
3. `df -B1` shows at least `56,533,471,537` bytes free: the exact
   47,943,536,945-byte landing plus the runner's default 8-GiB
   (`8,589,934,592`-byte) post-run reserve. The last read-only measurement was
   85,942,239,232 bytes, but it must be re-read immediately before execution.
4. The Supabase organization Usage page is read fresh for the current billing
   cycle. Record the plan, cycle dates, current uncached egress, remaining
   included egress, and spend-cap posture. Historical usage is not release
   evidence. The remaining allowance or explicitly accepted overage must cover
   47,943,536,945 payload bytes plus protocol overhead.
5. A preflight-only invocation heads all 23 landing objects and reports exact
   sizes before any download. It must report `preflight_ready`, 23 landing
   items, 22 excluded source objects, zero target writes, and a projected free
   value at or above the default reserve.

Any mismatch halts the run. Do not lower `--minimum-free-after-bytes` on syd2.

## Credential boundary

Use the owner-only Phase-1 channel unchanged. Parse only these names from the
existing owner-local Eamos environment file and deliver them over the encrypted
stdin channel into a mode-`0600` ephemeral syd2 env file:

```text
SUPABASE_STORAGE_S3_ENDPOINT_URL
SUPABASE_STORAGE_S3_REGION
SUPABASE_STORAGE_S3_ACCESS_KEY_ID
SUPABASE_STORAGE_S3_SECRET_ACCESS_KEY
```

Never source the application environment wholesale, print a value, place a
value in a process argument, enable shell tracing, or add database/application
credentials. The one-off must pass the ephemeral file with Docker `--env-file`
and remove it in an unconditional trap. The runner calls only private Storage
S3 `HeadObject` and `GetObject`; it performs no source, metadata, database,
provider, or deploy mutation.

## Phase 3a - preflight and seed

Inside the digest-pinned one-off with the final runtime bind mount, run the
preflight first as numeric `1000:1000` with `umask 027`:

```bash
python -m app.cli.eamos_runtime_tree_materialize \
  --target-root /var/data/eamos/bio_assets \
  --preflight-only \
  --compact \
  --require-ready
```

Only after every release gate is green, run the seed in a fresh one-off using
the same digest, identity, mount, credential channel, and `umask`:

```bash
python -m app.cli.eamos_runtime_tree_materialize \
  --target-root /var/data/eamos/bio_assets \
  --compact \
  --require-ready
```

There is deliberately no force or overwrite option. The default requires an
empty target, heads every source before the first write, downloads one object
at a time into one same-directory temporary file, verifies exact byte count and
SHA-256, sets mode `0600`, and commits with an atomic no-clobber hard link.
Predictor metadata is preserved in the sanitized result. No object path, local
path, or credential value is emitted.

Swordfish passive-monitors free bytes and container state without placing a
script on syd2. Record monotonic start/end times and byte/free-space samples.
Halt on a reserve breach, unexpected path, ownership change, checksum failure,
or source failure. If interrupted, do not rerun the default command and do not
delete anything broadly. `--resume` is permitted only after reviewing the
partial tree; it rehashes every completed expected file and refuses any
unexpected, mismatched, or symlink path before fetching missing items.

## Phase 3a exit proof

The seed is green only when all of these agree:

- sanitized CLI status `ready`; 23/23 items ready and SHA-256 verified;
- exactly 23 host files totaling 47,943,536,945 bytes;
- `asset-manifest diff` against the tracked canonical manifest exits zero with
  its single `OK` verdict;
- host files are owned `1000:1000`, mode `0600`, with no temporary residue;
- `.drill` is unchanged, the ephemeral env file is absent, and the one-off
  container was removed;
- post-run free bytes retain at least 8 GiB; and
- the sanitized result, host manifest, manifest hashes, timing, and passive
  samples are retained below `/srv/project1/manifests` with owner-only or
  group-readable operator modes.

No app/provider cutover begins on partial proof.

## Phase 3b internal Compose proof

Verified 2026-07-17 10:40 +0000 by Codex after recovery from an interrupted
session. The no-domain replacement is Dokploy raw Compose
`5rBnRf20ht4wGRQ856ZLO` / `project1-backend-dd110r`, deployment
`6FfxABW5Aplk_G7HWb1Z7`. It stores the exact tracked Compose SHA-256
`723d378cc67c4852d1fd285dba0c5b445043703766639b592807c44f8a169ee5`,
uses the 55-key explicit environment allowlist, has `autoDeploy=false`, and has
zero domains. GitHub Actions run `29571532636` is fully green for
`ac6d3e8`, including both backend shards, dependency security, coordination,
the container runtime contract, image publication, and immutable pull-back.

Direct effective-container inspection, not only control-plane read-back,
proved:

- immutable image digest `sha256:910dc159b3b2de8fec8f389ec7c328a6046733403793ba5f98b6cf83155a3fe1`;
- numeric `1000:1000`, read-only root, `cap_drop: ALL`,
  `no-new-privileges`, non-privileged execution, and no published ports;
- 2-GiB memory limit, 512-MiB reservation, 2 CPUs, 256 PIDs, and a
  512-MiB mode-`1777` `/tmp` tmpfs;
- both corpus binds read-only, private state read-write, and only the external
  `dokploy-network` attached; and
- exactly 23 corpus files / 47,943,536,945 bytes, with no symlinks or temporary
  residue and no ownership or mode violations.

The serving environment deliberately excludes the four S3 materialization
credentials, so an unassisted preflight failed closed as
`s3_credentials_missing`. Through the existing encrypted-stdin channel, only
those four names were placed in a mode-`0600` file on the container tmpfs. The
resume preflight then exact-hashed all 23 existing files, HEAD-verified all 23
private source objects, retained all 22 exclusions, reported zero missing or
downloaded bytes, and kept 36,086,616,064 free bytes. The credential file was
removed and remained absent after restart; no value entered an argument or
output.

The real functional matrix passed AlphaMissense for `1-68444869-T-C`, the
130,509-transcript compact index under its bounded 131,000 ceiling, the RPE65
viewer with local hg38 provenance, uncached Pfam/HMMER (`PF03055.22`), the
four-tile initial summary, and the full report with one exact RPE65 row and 12
evidence sources. A controlled restart recovered healthy with the immutable
digest and all hardening/mounts intact. From that clean restart, viewer +
summary + full lookup peaked at 54.11% / 1.073 GiB, with one container, zero
cgroup pressure, zero restart, and zero OOM events.

The hardened Application and Singapore Render service remain healthy rollback
services. No proxy, certificate, DNS, Vercel, Render, Supabase data-plane,
traffic, tag, workflow, or Phase-4 mutation followed this proof.

Swordfish independently closed the tenant-grant boundary at 2026-07-17 10:45
UTC. Through the tenant key itself, `compose.one` for
`5rBnRf20ht4wGRQ856ZLO` returned 200 with the expected service name,
`autoDeploy=false`, and zero domains. The old Application and a Thalon service
both returned 401; Docker container enumeration and SSH-key inventory returned
401; project enumeration returned only `project1`. That proves the permission
was moved rather than copied and that Docker, SSH, and cross-tenant authority
remain denied. The deliberate consequence is that CI can no longer deploy the
old Application rollback; Eamos accepted that human-only rollback posture and
did not widen the grant.

Swordfish also independently inspected the live Compose container and
corroborated healthy state, read-only root, capability drop `ALL`, the 2-GiB
limit, read-only corpus mounts, writable private state, and an exposed image
port with no host binding. This closes internal Phase 3b with two-party proof.
No external mutation is implied by the closure.

## Phase 3b and Phase 3c boundary

The no-domain backend deployment, runtime-tree preflight, representative live
lookup and predictor paths, and resource-headroom proof are complete on the
reviewed immutable image. Phase 3c begins only after Steven explicitly approves
the public hostname/Certificate-Transparency seam and the associated external
proxy and Vercel mutations. Record every environment/provider mutation; do not
change the managed Supabase data plane or move production traffic before the
external proxy path itself is proved.

Keep Render live and run both backends in parallel for Phase 3c. The controlling
plan suggests at least 48 hours. Monitor errors, latency, memory, disk, asset
lookups, and rollback readiness. A clean soak closes Phase 3; it does not open
Phase 4. Only Steven may separately authorize Render cancellation after the
seed proof, the Phase-1 preservation proof, and the parallel soak are all green.
