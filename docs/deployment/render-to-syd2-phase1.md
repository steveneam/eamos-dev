# Render to syd2 Phase-1 Migration Readiness

Status: Phase 1 dry run approved and in progress; later migration phases remain gated

Last verified: 2026-07-16 09:14 +0000 - Codex

This runbook freezes the manifest and identity commands needed before Eamos
moves its Render asset cache to the Project 1 landing zone on syd2. Steven
explicitly authorized the isolated Phase-1 ClinGen dry run and its necessary
preparation at 2026-07-16 09:10 UTC. That approval does not authorize a resize,
bulk seed, full-corpus transfer, cutover, provider change, source-bucket
mutation, destructive cleanup, or Render cancellation.

The controlling sequence and gates remain:

- `/home/deploy/work/swordfish/research/project1-asset-migration-plan-2026-07-15.md`
- `/home/deploy/work/swordfish/research/capacity-and-data-plan-2026-07-13.md`
- `/home/deploy/work/swordfish/provisioning/project1/README.md`

## Readiness verdict

| Proof | 2026-07-16 result | Gate |
| --- | --- | --- |
| Private source-bucket inventory | Green: 35 objects, 43,500,288,345 bytes (40.513 GiB) | Complete |
| Source checksum authorities | Green for all 35 objects | Complete, with the legacy-object limitation below |
| Target container identity | Tracked image is numeric `1000:1000`; focused ratchet and app-construction smoke are green | Awaiting full CI and immutable built-image digest |
| Current live Render identity | Deployed image may predate hardening; live `id` is not yet observed | Blocked on authenticated Render shell/exec |
| Live Render regular-file manifest | Exact command frozen; raw artifact not yet captured | Blocked on authenticated Render shell/exec |
| Nothing-only-on-Render comparison | Comparator tested; live artifact not yet available | Blocked on the Render manifest |
| syd2 `deploy` numeric UID/GID | Swordfish froze derived `1000:1000` | Live verify-before-write assertion still required |
| syd2 asset-root contract | Runtime and isolated dry-run subtrees frozen; `.drill` remains an untouched sibling | Awaiting live preflight |
| Supabase egress headroom | Published allowance known; current-cycle account usage unknown | Blocked on dashboard proof |

Phase 1 remains closed until the live identity, raw Render manifest,
content comparison, isolated ClinGen dry run, and current-cycle egress proof are
all recorded. Render stays up.

## Safety boundary

The source CLI uses the configured server-side Supabase S3 access key. Supabase
documents these keys as server-side credentials with full S3 access that bypass
RLS, so treat them as secrets even though this code path calls only
`ListObjectsV2`, `HeadObject`, and `GetObject`:

- <https://supabase.com/docs/guides/storage/s3/authentication>
- <https://supabase.com/docs/guides/storage/s3/compatibility>

Do not run with shell tracing, print the environment, source `.env` into an
interactive shell, paste credentials into a command, or retain manifests with
world-readable permissions. The CLI reads the existing gitignored
`app/backend/.env` through `Settings`; it never prints credential values.

## 1. Freeze the source-bucket manifest

Run from the trusted Eamos checkout that already has the S3 settings locally
provisioned:

```bash
cd /home/deploy/work/eamos/app/backend
set -euo pipefail
umask 077
SOURCE_MANIFEST="$(mktemp /tmp/eamos-source-bucket.XXXXXX.manifest)"
export SOURCE_MANIFEST
.venv/bin/python -m app.cli.eamos_migration_manifest source > "$SOURCE_MANIFEST"
test "$(wc -l < "$SOURCE_MANIFEST")" -eq 35
sha256sum "$SOURCE_MANIFEST"
printf 'source_manifest=%s\n' "$SOURCE_MANIFEST"
```

The verified 2026-07-16 stderr summary is:

```text
source_manifest=ready objects=35 bytes=43500288345 small_object_bytes_downloaded=628449 operations=list,head,get-small-objects large_object_downloads=0 mutations=0
```

The resulting 35-line manifest SHA-256 was
`0892d1ecd0f7f8bf117a5eac04f8b04d028ed4dbc260a5ede55028f742ad85dc`.

The command downloads 628,449 bytes in total from objects no larger than one
MiB, including checksum/JSON sidecars and a small index. It does not download
any object larger than one MiB and has no write or delete operation.

The tracked override file contains one reviewed checksum for the legacy Pfam
source object that predates adjacent SHA-256 sidecars. All other large-object
checksums come from agreeing content-addressed paths and/or adjacent manifests.

## 2. Verify the target image and observe the live Render identity

The tracked `app/backend/Dockerfile` now switches to numeric `USER 1000:1000`
after assigning only `/home/eamos` and `/app/data` to that identity. The numeric
form deliberately requires no passwd entry. The currently deployed Render
image may predate this hardening, so it is not a substitute for observing the
running SG instance. Run these read-only commands in an authenticated shell on
service `srv-d8ctvoh9rddc73a27nb0`:

```bash
set -euo pipefail
user="$(id -un 2>/dev/null || printf 'numeric-only')"
group="$(id -gn 2>/dev/null || printf 'numeric-only')"
printf 'uid=%s gid=%s user=%s group=%s\n' \
  "$(id -u)" "$(id -g)" "$user" "$group"
stat -c 'path=%n owner=%u:%g mode=%a' \
  /var/data/eamos \
  /var/data/eamos/bio_assets
if command -v findmnt >/dev/null 2>&1; then
  findmnt -T /var/data/eamos/bio_assets -o TARGET,SOURCE,FSTYPE,OPTIONS
else
  printf 'findmnt=unavailable\n'
fi
```

Record raw stdout. The old deployed image is expected to report `uid=0 gid=0`;
the new syd2 image must report `uid=1000 gid=1000`. Neither expectation is
evidence until captured from its live instance and tied to an immutable image
digest.

Root can write the current `deploy:deploy 0755` landing zone but would create
root-owned files. The frozen target is therefore the numeric image identity
`1000:1000`, matching syd2 `deploy`; the live owner assertion must pass before
the dry run writes anything.

## 3. Capture the complete live Render disk manifest

Run this during a quiet window with no materialization job writing the disk.
It reads and hashes every regular file under the live runtime root. It writes
only a small, mode-`0600` artifact under the container's ephemeral `/tmp`.
Hashing the roughly 41 GiB tree may take time.

```bash
bash -s <<'BASH'
set -euo pipefail
export LC_ALL=C
root=/var/data/eamos/bio_assets
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="/tmp/eamos-render-precutover-${stamp}.manifest"
tmp="$(mktemp /tmp/eamos-render-manifest.XXXXXX)"
trap 'rm -f "$tmp"' EXIT

test -d "$root"
cd "$root"
if test -n "$(find . -type l -print -quit)"; then
  printf 'FAIL: symlink found below %s; regular-file manifest would omit it\n' "$root" >&2
  exit 1
fi

find . -type f -printf '%P\0' | sort -z |
while IFS= read -r -d '' file; do
  case "$file" in
    *$'\n'*) printf 'FAIL: newline in filename\n' >&2; exit 1 ;;
  esac
  printf '%s  %s  %s\n' \
    "$(sha256sum < "$file" | cut -d' ' -f1)" \
    "$(stat -c %s -- "$file")" \
    "$file"
done > "$tmp"

chmod 600 "$tmp"
mv -- "$tmp" "$out"
trap - EXIT
printf 'render_manifest=%s files=%s\n' "$out" "$(wc -l < "$out")"
sha256sum "$out"
BASH
```

Retrieve the artifact without editing it. With Render SSH configured and
reachable, Render documents SCP using SFTP mode (`-s`):

```bash
scp -s \
  srv-d8ctvoh9rddc73a27nb0@ssh.singapore.render.com:/tmp/eamos-render-precutover-YYYYMMDDTHHMMSSZ.manifest \
  /tmp/eamos-render-precutover.manifest
chmod 600 /tmp/eamos-render-precutover.manifest
sha256sum /tmp/eamos-render-precutover.manifest
```

Official references:

- <https://render.com/docs/ssh>
- <https://render.com/docs/disks>

Port 22 to `ssh.singapore.render.com` timed out from the current syd4 host on
2026-07-16, and this session has neither an authenticated Render API token nor
dashboard shell. Do not claim the SCP route is verified here. The fallback is
for an authenticated operator to run
`cat /tmp/eamos-render-precutover-YYYYMMDDTHHMMSSZ.manifest` with the path
printed by the capture command, copy stdout byte-for-byte into a mode-`0600`
local file, and confirm the recorded manifest SHA-256. Render one-off jobs are
not a substitute because they cannot access a service's persistent disk.

## 4. Prove nothing lives only on Render

The source bucket and runtime disk intentionally use different paths. Compare
content identity (`sha256`, byte size), not relpath:

```bash
cd /home/deploy/work/eamos/app/backend
set -euo pipefail
.venv/bin/python -m app.cli.eamos_migration_manifest compare \
  --source "$SOURCE_MANIFEST" \
  --runtime /tmp/eamos-render-precutover.manifest
```

Exit `0` with `render_only=0` is the only green result. Any `RENDER_ONLY` line
or nonzero exit blocks the migration. Uploading a missing derivative back to
Supabase is a separate, explicit mutation gate and is deliberately absent from
this runbook.

`source_only_identities` may be nonzero because the bucket includes raw source
objects and metadata not materialized on the runtime disk. Preserve the raw
Render manifest after the content comparison: its relpaths become the exact
target-tree contract for the syd2 cache.

## 5. Freeze the syd2 identity and tree contract

Swordfish reports `/srv/project1/assets` and `/srv/project1/manifests` as
`deploy:deploy 0755` and froze the derived first-boot identity as `1000:1000`.
Capture live numeric proof through its supported CI-as-hands route before any
container writes:

```bash
set -euo pipefail
printf 'deploy_uid=%s deploy_gid=%s\n' "$(id -u deploy)" "$(id -g deploy)"
getent passwd deploy
getent group "$(id -g deploy)"
stat -c 'path=%n owner=%u:%g mode=%a' \
  /srv/project1/assets \
  /srv/project1/manifests
asset-manifest self-test
```

Do not bind-mount `/srv/project1/assets` itself as the application asset root.
Swordfish intentionally maintains
`/srv/project1/assets/.drill/exclusion-canary.bin` to prove the bulk-tree backup
exclusion; the exact Render manifest would therefore always fail with
`EXTRA: .drill/exclusion-canary.bin`.

Swordfish confirmed this isolated contract at 2026-07-16 09:00 UTC:

```text
syd2 host runtime root: /srv/project1/assets/runtime
container runtime root: /var/data/eamos/bio_assets
bind mount:             /srv/project1/assets/runtime -> /var/data/eamos/bio_assets
dry-run scratch root:   /srv/project1/assets/phase1-dry-run
dry-run container root: /var/data/eamos/phase1-dry-run
```

The `.drill` canary remains untouched as a sibling. The small ClinGen dry run
belongs below `phase1-dry-run`, not the final runtime root.

After the resize gate and full authorized seed, run the following as the
numeric `deploy` identity. First place the unedited Render target manifest in
`/srv/project1/manifests/` and verify its transfer checksum.

```bash
set -euo pipefail
umask 027
RUNTIME_ROOT=/srv/project1/assets/runtime
RENDER_TARGET=/srv/project1/manifests/render-precutover-YYYYMMDDTHHMMSSZ.manifest
SYD2_MANIFEST="/srv/project1/manifests/syd2-$(date -u +%Y%m%dT%H%M%SZ).manifest"
tmp="$(mktemp /srv/project1/manifests/.syd2-manifest.XXXXXX)"
trap 'rm -f "$tmp"' EXIT

test -d "$RUNTIME_ROOT"
test -f "$RENDER_TARGET"
asset-manifest manifest "$RUNTIME_ROOT" > "$tmp"
chmod 640 "$tmp"
mv -- "$tmp" "$SYD2_MANIFEST"
trap - EXIT
asset-manifest diff "$RENDER_TARGET" "$RUNTIME_ROOT"
sha256sum "$RENDER_TARGET" "$SYD2_MANIFEST"
printf 'syd2_manifest=%s\n' "$SYD2_MANIFEST"
```

`asset-manifest diff` must emit exactly one `OK: tree matches manifest ...`
line and exit `0`. `MISSING`, `EXTRA`, or `MISMATCH` blocks cutover.

## 6. Confirm egress before an approved transfer

Supabase currently documents 250 GB of included uncached egress for Pro/Team
organizations and overage billing after the quota. The private inventory is
43.500 GB (decimal) before protocol overhead and any later growth, but the
organization's plan and current billing-cycle usage have not been observed:

- <https://supabase.com/docs/guides/platform/manage-your-usage/egress>

Before the Phase-1 ClinGen download, record the dashboard plan, billing-cycle
dates, current uncached egress, and at least 527,925,248 bytes of remaining
included headroom plus a deliberate safety margin. Repeat the same proof for
the full inventory before Phase 3. A published maximum alone is not
account-specific proof.

## 7. Run the isolated ClinGen pipe proof

The selected current ClinGen object is the pinned 527,925,248-byte SQLite
artifact already present in `app/materialization-manifest-sg.json`. Run this
only after the image digest, numeric ownership, free-space, credential channel,
and egress preflights are green. The S3 credentials must arrive through the
owner-only operator channel; never paste them into this command or a log.

Bind `/srv/project1/assets/phase1-dry-run` to
`/var/data/eamos/phase1-dry-run` in the digest-pinned app shell. Then run as the
container's numeric `1000:1000` identity:

```bash
set -euo pipefail
umask 027
DRY_ROOT=/var/data/eamos/phase1-dry-run
PAYLOAD="$DRY_ROOT/payload"
METADATA="$DRY_ROOT/metadata"
test "$(id -u):$(id -g)" = "1000:1000"
test -d "$DRY_ROOT"
test -z "$(find "$DRY_ROOT" -mindepth 1 -print -quit)"
mkdir -p "$PAYLOAD" "$METADATA"
python -m app.cli.eamos_generated_artifact_sync \
  --artifact clingen_local \
  --source-object-uri supabase://eamos-source-assets/generated/eamos_clingen_local/clingen_local_sqlite/sha256-50e12d4c0caaefceeece8f1e04de654158c5197a03fb6def991728591028dd9b/clingen-local.sqlite \
  --destination "$PAYLOAD/clingen-local.sqlite" \
  --manifest-destination "$METADATA/clingen-local.manifest.json" \
  --expected-size-bytes 527925248 \
  --expected-md5 60997c2c9a6837bd8614f489e79021fb \
  --expected-sha256 50e12d4c0caaefceeece8f1e04de654158c5197a03fb6def991728591028dd9b \
  --download-mode s3_multipart \
  --require-ready
```

The sanitized report must say `ready`, `downloaded`, `md5_verified`, and
`sha256_verified` are true. On syd2, independently close the host-side proof:

```bash
set -euo pipefail
EXPECTED=/srv/project1/manifests/phase1-clingen-source.manifest
printf '%s  %s  %s\n' \
  50e12d4c0caaefceeece8f1e04de654158c5197a03fb6def991728591028dd9b \
  527925248 \
  clingen-local.sqlite > "$EXPECTED"
chmod 640 "$EXPECTED"
asset-manifest diff \
  "$EXPECTED" \
  /srv/project1/assets/phase1-dry-run/payload
stat -c 'path=%n owner=%u:%g mode=%a size=%s' \
  /srv/project1/assets/phase1-dry-run/payload/clingen-local.sqlite
sha256sum \
  /srv/project1/assets/phase1-dry-run/payload/clingen-local.sqlite \
  "$EXPECTED"
```

The harness must emit exactly its single `OK` verdict, the payload owner must
be `1000:1000`, and the payload SHA-256 must equal the pinned value. Any
mismatch stops Phase 1; do not retry with `--force`, broaden the asset set, or
move the dry-run payload into the final runtime tree.

## Checksum limitation

Supabase's S3 compatibility surface supports list, head, and get operations but
does not provide a trustworthy server-side SHA-256 for every legacy object.
This source manifest therefore uses actual content hashes for objects up to one
MiB and agreeing tracked sidecars/content-addressed paths for large objects,
plus the single reviewed Pfam override. The isolated dry run and full re-seed
must still hash the downloaded bytes; those destination hashes close the proof
for the transferred objects.
