# Render to syd2 Phase-3 Seed and Cutover

Status: Phase 3a exact-manifest green; internal Phase 3b Compose proof and
two-party tenant-grant verification green; Phase 3c public endpoint, Vercel
traffic cutover, recovery soak, and independent host/container end sample
green; Phase 3 closed; Render rollback ready for a separate Phase-4 retirement

Last verified: 2026-07-22 14:25 +0000 - Codex + Swordfish

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
- both corpus binds read-only, private state read-write, the Dokploy project
  network plus external `dokploy-network` attached, and Traefik explicitly
  pinned to `dokploy-network`; and
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

## Phase 3c public cutover and soak

Steven directly authorized the domain attach and Vercel `API_PROXY_TARGET`
flip in the Eamos session on 2026-07-17. The mutation ledger is:

1. Swordfish had already created and independently verified the A record
   `preview-api.swordfish.cfd -> 103.249.236.41`, TTL 600. Eamos re-proved the
   answer through both `1.1.1.1` and `8.8.8.8`; Eamos did not mutate DNS.
2. At `2026-07-17T11:23:44Z`, Eamos attached the one Dokploy domain to Compose
   `5rBnRf20ht4wGRQ856ZLO`, service `backend`, HTTPS with Let's Encrypt, no
   Basic Auth, no forward auth, and no path stripping. Dokploy read-back is
   exact and `autoDeploy` remains false.
3. Dokploy Compose domains are materialized as Traefik container labels, so the
   route required one same-contract redeploy. Deployment
   `SSvNBmx91esTGz1tohYoU` completed at `2026-07-17T11:25:12Z`; the stored
   Compose SHA-256, 55-name environment allowlist, immutable image digest, and
   rate-limit-enabled posture remained exact.
4. Vercel production `API_PROXY_TARGET` was read back as
   `https://eamos-dev-sg.onrender.com`, changed to
   `https://preview-api.swordfish.cfd`, and read back exact. Vercel deployment
   `dpl_2Yy6712rwE4zHqaKPHjJoCxmC9SZ` was created at 11:28:28 UTC from the
   existing production commit `40d759e`, reached `READY`, and was promoted to
   `eamos-dev.vercel.app` at approximately 11:31 UTC.

The Dokploy domain's port `8000` is strictly the isolated container listener
named in the frozen Compose file. It is not a host-published or shared
workstation port. Public traffic uses HTTPS 443, host port bindings remain
empty, and the executable local-development contract remains frontend `3532`
plus backend `8532`; shared-workstation `3000` and `8000` remain unallocated
collision sentinels.

Immediate cutover proof passed:

- plain HTTP redirects to HTTPS; the Let's Encrypt certificate has the exact
  `preview-api.swordfish.cfd` SAN and is valid from 2026-07-17 through
  2026-10-15;
- direct `/healthz` returns 200 with application and database status `ok`;
  provider-cache health returns overall `ok` with the protein annotation and
  CRISPR providers available;
- a hostile `Origin` receives no `Access-Control-Allow-Origin`; security
  headers remain present; an unauthenticated evidence submission returns 401
  both directly and through Vercel;
- the complete provider-health JSON hashes to
  `b087c5a6993b7f8e64351f27eae0f656a27ba3e524533d84e06735dd64002620`
  both directly on syd2 and through `eamos-dev.vercel.app`. Render returns a
  different payload hash, proving the production proxy is reaching syd2 rather
  than the retained rollback origin;
- the production proxy resolves `RPE65 c.271C>T` deterministically with high
  confidence, normalized as `RPE65:c.271C>T`; and
- direct post-redeploy container inspection still reports the exact immutable
  digest, `1000:1000`, healthy/restart 0, read-only root, capability drop
  `ALL`, no-new-privileges, 2-GiB/2-CPU/256-PID limits, read-only corpus binds,
  private writable state, and zero published ports. The immediate resource
  sample was 747.7 MiB / 2 GiB, 12 PIDs, and 0.11% CPU.

Singapore Render remains independently reachable with provider-cache HTTP 200,
and its exact former Vercel target is retained above for rollback. No Render,
old-Application, image-tag, auto-deploy, Supabase, credential, cleanup, or
Phase-4 mutation occurred.

### Active soak observation and exit contract

Two direct synthetic `POST /api/v1/viewer` probes for `RPE65 c.271C>T` returned
503 during the immediate window. Both were Uvicorn responses, not Traefik
responses. Independent container/edge inspection found restart 0, cgroup
`low/high/max/oom/oom_kill` all zero, no Traefik 503, one router to one service,
and no stale Application route.

The application path is now bounded. This exact variant misses the
compact coordinate variant lookup and invokes VariantValidator before using
the compact transcript, mounted hg38 sequence, and local protein-domain cache.
The two failures took approximately 15 and 28 seconds and bracketed a logged
VariantValidator 200. Subsequent direct and Vercel-proxied calls are 200; a
concurrent full-report sample recorded upstream `TimeoutError` / `ReadTimeout`
warnings while its separate fallback path still returned 200. The strongest
supported explanation is a transient external coordinate-resolution failure,
not migration infrastructure. Both failures clustered in the first 133 seconds
after startup, but the successful call between them means the evidence does not
prove a one-time cold lazy-load cause. The old access log does not retain the
structured response error, so the exact historical exception type remains an
explicit evidence limit. The tracked performance audit now has an opt-in
`--require-ok` ratchet that exits nonzero and preserves any future structured
error.

Swordfish's later apparent third 503 at `11:57:06` was a log-filter false
positive. The exact line is `/healthz` 200 at
`11:57:06.318275503Z`; `503` occurs only in the timestamp's nanoseconds. The
authoritative status tally therefore remains two viewer 503s. The 18 real
viewer requests from 11:59:38 through 12:10:44 produced 16 200s, two expected
422 validation rejects, and no 503.

#### Beginning sample - 2026-07-17 12:12 +0000

- Cloudflare and Google DNS both returned `103.249.236.41` at TTL 600. TLS was
  authorized for the exact SAN through 2026-10-15, and HTTP redirected to
  HTTPS.
- Direct `/healthz` and retained Render `/healthz` returned application/database
  `ok`. Vercel intentionally rewrites `/api/:path*`, not root `/healthz`; its
  proxied provider-health route returned 200 and byte-for-byte matched direct
  syd2 while Render returned a different healthy payload.
- The Vercel functional matrix returned 200 for deterministic parse, two full
  lookups, two initial summaries, all four lazy sections in both passes, and
  two viewers. Cold/warm full lookup latency was 44.0/11.2 seconds; viewer was
  1.22 seconds. A subsequent one-pass run with `--require-ok` also exited zero.
- Provider health remained overall `ok`: mounted hg38, compact coordinates,
  ClinGen, gene distribution, AlphaMissense, Pfam/HMMER, local deterministic
  CRISPR, and pure-code PVS1/NMD retained their expected ready/available state.
  Predictors with pre-existing launch gates remained explicitly unavailable;
  no provider was silently enabled by the migration.
- The app log contained one server-process start, 104+ health 200s, viewer
  18x 200 / 2x 422 / 2x 503 / 0x 429, no other 5xx, no traceback, and no OOM
  marker. After the deep sample the same healthy container used 1.106 GiB / 2
  GiB (55.31%) and 0.16% CPU.
- Direct and Vercel hostile-Origin probes received no ACAO; both retained HSTS,
  `nosniff`, and `SAMEORIGIN`; unauthenticated evidence submissions remained
  401. Stored Compose SHA, the 55-name environment allowlist,
  `autoDeploy=false`, the single approved domain, and rate limiting remained
  exact. Render stayed HTTP 200 and untouched.

#### Interrupted middle checkpoint and recovery baseline - 2026-07-19 05:03 +0000

The scheduled middle checkpoint is **not green**. A separate Swordfish incident
receipt and direct host evidence agree that the syd2 fleet kernel-patch reboot
at `2026-07-18T18:30:21Z` raced Traefik against swarm-overlay initialization.
The public edge remained unavailable until a replacement Traefik container
started at `2026-07-19T01:46:12Z`, an outage of approximately 7 hours 15
minutes. The Eamos container stayed on the same immutable container ID and
restarted with Docker at `18:30:27Z`; `RestartCount=0` therefore does not prove
uninterrupted service across a daemon or host reboot. Dokploy cleanup later
pruned the stopped edge container, while the application workload itself
remained healthy. The public-origin outage still breaks the consecutive clean
soak required by this runbook.

Swordfish restored the edge and installed an enabled boot-time
`swordfish-edge-up.service` that waits for the overlay before converging the
edge Compose service. The unit is enabled, active, and asserted in Swordfish's
hardening checks. It has not yet been naturally exercised by another host
reboot, so the retained Render origin remains the rollback.

The bounded recovery baseline passed without mutation:

- Cloudflare and Google DNS returned `103.249.236.41` at TTL 600; HTTP
  redirected to HTTPS; the exact-host certificate remains valid through
  2026-10-15. Direct syd2 and Render health returned application/database
  `ok`.
- Direct and Vercel provider-health payloads matched byte-for-byte at SHA-256
  `37b01faf906ec1c69fb5ddbc7166e617b03bed8854a03430397c3a3b1ed27ab3`.
  Render returned a distinct healthy payload. Mounted hg38, compact
  coordinates, ClinGen, gene distribution, local evidence, AlphaMissense,
  Pfam/HMMER, CRISPR, and PVS1/NMD retained their expected states.
- Deterministic parse plus two Vercel passes of full lookup, initial summary,
  all four lazy sections, and viewer returned 200 under `--require-ok`. Full
  lookup took 24.377/12.343 seconds and viewer 12.569/1.327 seconds. Handled
  upstream `TimeoutError`/`ReadTimeout` warnings did not become endpoint
  failures.
- Direct and Vercel hostile-Origin probes received no ACAO; HSTS, `nosniff`,
  and `SAMEORIGIN` remained present; unauthenticated evidence submissions
  stayed 401.
- Dokploy retained the exact Compose SHA, 55-name environment allowlist,
  `autoDeploy=false`, rate limiting, and one approved domain. The same app
  container retained its exact digest, numeric identity, read-only root,
  capability drop, resource/PID limits, read-only corpus mounts, private
  writable state, and zero published ports. The two-network runtime shape was
  already present in the beginning inspection and is not new drift.
- The runtime tree remained exactly 23 files / 47,943,536,945 bytes with
  correct ownership/modes and no symlinks. Disk headroom was 35,376,615,424
  bytes. After the deep sample Docker reported 880 MiB / 2 GiB; cgroup
  `low/high/max/oom/oom_kill` remained zero.
- Since the original beginning sample, the app log records the one host-reboot
  server start, three viewer 200s, zero 5xx, zero 429s, and no traceback/OOM
  marker. Since edge recovery it records two viewer 200s and no 5xx; the new
  Traefik log also contains no `preview-api` 5xx.

The consecutive observation clock restarts at edge recovery. A recovery-middle
sample is due around/after `2026-07-20T01:46:12Z`; Phase 3c cannot close before
an end sample around/after `2026-07-21T01:46:12Z`, and only if every evidence
gate below remains green. This timing supersedes the original cutover-based
floor; it does not authorize a provider, deployment, Render, or Phase-4 change.

One separate hardening item was discovered but was not mutated during the
frozen soak: with forwarded-header trust disabled, Traefik collapses app-level
IP buckets to its `10.0.1.41` source address. This did not cause the 503s—the
limiter returns 429, the live tally has zero 429s, and scanner 404/405/422
requests do not enter the viewer handler—but correct per-client limiting needs
a reviewed trusted-proxy boundary rather than an ad-hoc boolean flip.

Phase 3c cannot close earlier than the restarted 48-hour recovery floor above,
and elapsed time alone is insufficient. All of these evidence gates must also
pass:

1. spaced beginning/middle/end samples keep DNS, TLS, direct health, Vercel
   proxy health, and Render rollback health green;
2. representative parse, initial-summary, full-report, viewer, and local
   predictor/asset paths pass through the Vercel origin without unexplained
   migration-specific 5xx responses; the viewer observation above is closed;
3. the syd2 container records zero unexpected restarts, OOM events, or cgroup
   pressure, preserves meaningful memory/disk headroom, and retains the exact
   digest, hardening, mounts, environment-name set, and zero host bindings;
4. protected endpoints remain 401 without a valid JWT, arbitrary origins gain
   no CORS access, and rate limiting remains enabled; and
5. the Render origin remains a tested 200 rollback path, with the old Vercel
   target and redeploy sequence available until a separate Phase-4 decision.

A clean soak closes Phase 3 only. It does not authorize Render cancellation.
Only Steven may separately open Phase 4 after the seed, preservation, and soak
proofs are all green.

#### Recovery end sample and Phase-3 closure - 2026-07-22 14:25 +0000

The delayed recovery end sample is green. Eamos's public sample at 13:33 UTC
reconfirmed DNS/TLS, direct and Vercel origin identity, Render rollback health,
security headers/CORS/auth rejection, deterministic parse, and two complete
production report/viewer passes. Swordfish then independently sampled syd2 at
`2026-07-22T14:21:36Z` using read-only host and container inspection.

- The container remained on the frozen image digest with `RestartCount=0` and
  continuous uptime since before the `2026-07-19T01:46:12Z` recovery anchor.
- Health probes were green; anchored application and Traefik tallies contained
  zero 5xx, 429, traceback, ERROR/CRITICAL, or OOM events since recovery.
- The runtime tree remained exactly 23 files / 47,943,536,945 bytes, and the
  read-only mounts, numeric identity, capability drop, no-new-privileges,
  CPU/memory/PID limits, two-network shape, and zero published ports remained
  exact.
- Cgroup `low/high/max/oom/oom_kill` stayed zero. Cache-inclusive memory peak
  was about 1.70 GiB of the 2 GiB cap, while reclaimable-excluded live usage was
  886.2 MiB; disk retained 34 GiB free.
- Dokploy retained `autoDeploy=false`, one approved domain, and the exact
  55-name injected environment boundary. Ten additional running-process names
  were traced to the Python base image and Dockerfile path defaults, not
  out-of-band injection.
- Application rate limiting remained enabled. The edge retained its global
  100-request in-flight bound and security headers; the intentionally
  unattached IP-keyed 25/s router limiter remains a non-blocking future design
  question because the Next proxy would collapse all users into one IP bucket.

This closes every Phase-3c evidence gate above and therefore closes Phase 3.
The exact-byte preservation and nothing-only-on-Render proofs were already
green, so Phase 4 may now retire the Render rollback when Steven explicitly
performs that destructive provider action. No Render disk or service was
deleted by this verification.
