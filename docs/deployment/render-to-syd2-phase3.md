# Render to syd2 Phase-3 Seed and Cutover

Status: Phase 3 authorized; Phase 3a awaits immutable-image, host, and fresh-egress preflight

Last verified: 2026-07-17 08:25 +0000 - Codex

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

## Phase 3b and Phase 3c boundary

After the complete Phase 3a proof, deploy the Eamos backend on syd2 from the
same reviewed immutable image, retaining the runtime bind mount and numeric
identity. Re-prove container health, the runtime-tree preflight, representative
live lookup and predictor paths, resource headroom, and the external proxy path
before moving production traffic. Record every environment/provider mutation;
do not change the managed Supabase data plane.

Keep Render live and run both backends in parallel for Phase 3c. The controlling
plan suggests at least 48 hours. Monitor errors, latency, memory, disk, asset
lookups, and rollback readiness. A clean soak closes Phase 3; it does not open
Phase 4. Only Steven may separately authorize Render cancellation after the
seed proof, the Phase-1 preservation proof, and the parallel soak are all green.
