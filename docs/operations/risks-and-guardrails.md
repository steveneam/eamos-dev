# Agent Risks And Guardrails

Consolidated: 2026-07-15 11:19 UTC by Codex. Relocated from
`agent_handoff/RISKS.md`: 2026-07-15 21:39 +1000 by Codex. The complete
pre-consolidation ledger is preserved at
`agent_handoff/archive/2026-07-15-risks-pre-consolidation.md`.

## AI Gateway Chat - Live Security Boundary

Section reconciled: 2026-07-15 11:19 UTC by Codex against the shipped route
guards, `docs/ai-gateway/pre-launch-security.md`, and the live handoff.

Ask-Eamos is live with server-side `LLM_PROVIDER=gateway`. The original launch
HIGH is met: both chat endpoints require an authenticated principal, enforce a
per-user burst limit, enforce the enabled 10-request per-user daily cap, and
retain the global daily backstop. Do not revert those controls or treat
`NEXT_PUBLIC_AI_CHAT_ENABLED` as a security boundary.

Residual guardrails:

- The daily counters are in-process. They reset on deploy and would not be
  coherent across multiple backend instances; move them to a private durable
  store before multi-instance scaling or stronger billing guarantees.
- M-006, the single metered gateway choke point, remains deferred. Until it
  lands, preserve the route-level auth and cap ordering on every paid chat path.
- Keep provider keys backend-only, retain a hard provider spend cap, and do not
  rely on provider billing lag as the application budget.
- Keep the evidence-only outbound allowlist, separate system/user messages, no
  user-facing tool access, escaped-text rendering, and the fixed gateway URL.
- The transcript-exposed key was rotated on 2026-06-20. Rotate again on any new
  exposure signal; never record key material in handoff or deployment docs.

## Dirty Worktree

Section edited: 2026-05-18 17:14 +1000 · Claude (user lifted Claude's commit
gate; destructive/cross-lane guardrail kept).

The worktree is intentionally dirty and contains verified work from both lanes.

Guardrails:

- **Commit gate lifted for Claude (user-authorized 2026-05-18).** Claude may
  create commits of its own verified frontend work on a non-default branch
  without re-asking. Codex's commit gate is unchanged (its own brief governs).
- Cross-lane: do **not** sweep Codex's uncommitted backend tree
  (`app/backend/**`, `plans/v2-backend.md`, `plans/gene-viewer/`) into a Claude
  commit without coordination — commit Claude-lane paths, or coordinate first.
- Still **never** without an explicit user ask: `stash`, `reset`, `checkout`
  (discarding), `clean`, discard changes, force-push, or any rewrite of
  `e0f1763` / shared `origin` lineage. These protect the other agent's
  uncommitted work and origin/main, not Claude specifically.
- Do not treat untracked files as junk.

## Sole Live Backend — No Oregon Fallback

Section edited: 2026-06-02 01:01 +1000 - Claude.

The Oregon Render service (`srv-d896ie77f7vs73brs140` / `eamos-dev.onrender.com`)
was DELETED 2026-06-02 (Steven-approved, after Codex's SG live-verify on commit
`8290312`). Singapore (`srv-d8ctvoh9rddc73a27nb0` / `eamos-dev-sg.onrender.com`)
is now the SOLE live backend and Vercel proxies to it. There is no longer a
standby Render service to fail over to — if SG is down, prod has no backend.
Deletion is irreversible; recreate a standby/region service if a fallback is
wanted again.

## Render Persistent Disk + Local-First Asset Seeding — Operational Reality

Section edited: 2026-06-02 01:44 +1000 - Claude (from Codex's verified provisioning brief).

Setup decided 2026-06-02 (see `docs/governance/decisions.md`): Hobby workspace +
Standard SG instance + 60 GB disk at `/var/data`. When actually wiring the
dbSNP/phyloP/Pfam local-first adapters to live SG, these operational constraints
hold:

- **Render disks are RUNTIME-ONLY** — not mounted during build / predeploy /
  one-off jobs. Do NOT download ~40 GB of assets during deploy/startup.
- **Pre-seed, do not startup-download.** Sequence: attach disk → deploy with the
  local adapters STILL DISABLED → seed assets onto the disk via Render Shell /
  SCP / a controlled runtime CLI → verify size/checksum/materialization metadata
  → THEN set the env paths/flags and redeploy.
- **Attaching a disk disables zero-downtime deploys and forces single-instance.**
  SG is the SOLE backend (Oregon deleted), so every disk-backed deploy is a brief
  prod blip — do the attach + seeding in an OFF-PEAK / maintenance window.
- **Env vars (Codex-specified):**
  - `HG38_2BIT_RUNTIME_ASSET_MODE=mounted_volume`
  - `HG38_2BIT_RUNTIME_ASSET_PATH=/var/data/eamos/bio_assets/genomes/hg38.2bit`
  - `PROTEIN_ANNOTATION_PFAM_HMM_GZ_PATH=/var/data/eamos/bio_assets/protein_annotation/downloads/Pfam-A.hmm.gz`
  - `PROTEIN_ANNOTATION_PFAM_HMM_PATH=/var/data/eamos/bio_assets/protein_annotation/Pfam-A.hmm`
- **Keep `PROTEIN_ANNOTATION_ENABLED=false`** until Pfam is materialized +
  extracted, `hmmpress` indexes are present, and runtime preflight is green.
- **No committed dbSNP/phyloP asset-root env/wiring yet** — current code has the
  hg38/Pfam env paths but NOT a global dbSNP/phyloP asset-root env. That adapter/
  materialization path wiring is still uncommitted Codex backend work; don't
  assume those env vars exist until it lands. So "adapters wired to live web" is a
  follow-on Codex task AFTER the disk is provisioned + seeded, not an immediate
  consequence of attaching the disk.

Hardening added 2026-06-21 01:05 +1000 - Claude (from the 2026-06-20/21 hotspot
seed dry-run; canonical write-up `docs/deployment/materialization-lessons-learned.md`):

- **HIGH — manual seed without env-as-code silently no-ops provider-cache.** On
  live SG the 8 runtime-path env vars (`*_RUNTIME_*_PATH`, `CLINGEN_LOCAL_*_PATH`)
  were UNSET, so Pydantic defaulted to relative `./data/...` (ephemeral `/app`),
  NOT `/var/data`. Seeding files onto the disk would NOT have flipped
  provider-cache to `ready` because the service was reading a different (empty)
  path. Mitigation now in code: `Settings` is RENDER-aware
  (`_RENDER_RUNTIME_PATH_DEFAULTS` in `core/config.py` defaults these to
  `/var/data/...` whenever a `RENDER*` env var is present) + a checked-in
  `render.yaml` env group. **Pre-flight rule:** before any seed, confirm the path
  env vars actually resolve to `/var/data` on the running service (read PID 1 env,
  not the dashboard) — file presence on disk is NOT proof the service will use it.
- **HIGH — non-resumable large-asset transport.** SG has no
  `SUPABASE_STORAGE_S3_*` creds, so the only download mode is single-stream REST
  with no range-resume. A dropped connection mid-transfer on the 29.55 GB dbSNP
  object (or 9.87 GB phyloP) restarts from zero. **Pre-flight rule:** provision the
  S3 creds on the service so `s3_multipart` works (use the ROTATED secret — the old
  one was transcript-leaked 2026-06-20) before seeding any multi-GB asset; treat a
  non-resumable multi-GB seed as a do-not-start condition.

Verified 2026-06-21 02:39 +1000 - Claude (during the first live 443 seed):

- **MED — eamos-local user accounts live on the EPHEMERAL container FS, wiped
  every deploy.** `database_url = "sqlite+pysqlite:///./data/app.db"` resolves to
  `/app/data/app.db` on SG (ephemeral), NOT `/var/data`. A user registered via
  `/auth/register` authed fine, then 401'd after a redeploy (its row was gone) —
  this bit the admin-materialization seed flow (had to re-register on the final
  image). **Real production users are NOT affected** — they authenticate via
  Supabase (signature-validated JWT, `_supabase_principal`, no SQLite lookup). So
  the blast radius is eamos-local `/auth/register` accounts + any operator/admin
  flow that registers a user then redeploys. The RENDER-aware defaults moved
  bio-assets to `/var/data` but left `app.db` ephemeral. **Fix options (Codex's
  auth lane):** point `DATABASE_URL` at `/var/data/eamos/app.db` so local accounts
  persist, OR formally treat eamos-local auth as dev-only and document that real
  auth is Supabase. Until decided, deploy-spanning admin flows must re-register on
  the final image or use a Supabase JWT.

## Backend Launch Security Findings

Section edited: 2026-05-26 20:23 +1000 - Codex.

The vendored vibe-security backend review findings are now mostly resolved in
the local backend tree:

- **Resolved locally - backend rate limiting.** Auth register/login/logout/me,
  public lookup/parse/publications, chat/stream, evidence submission, payment
  checkout/webhook, and Workbench primer/crispr/align now call a configurable
  in-memory limiter. Evidence and checkout combine per-IP with per-principal
  counters; auth combines per-IP with username/token subject where available.
  This is launch-suitable for a single Render instance. Durable multi-instance
  deployments should move counters to Redis, a private DB table, or gateway
  controls.
- **Resolved locally - production debug default.**
  `app/backend/app/core/config.py` and `app/backend/.env.example` now default
  `DEBUG=false`. Render env was directly verified read-only by Codex on
  2026-05-26: backend service `eamos-dev` has `DEBUG=false`.
- **Resolved locally - Stripe checkout redirects.** `CheckoutSessionRequest`
  no longer accepts `success_url` / `cancel_url`; extra fields are rejected, and
  Stripe checkout always uses configured server-side redirect URLs.
- **Resolved locally - Workbench AB1/alignment bounds.** Primer/CRISPR/align
  request schemas now bound core text/numeric fields; AB1 parsing rejects
  overlarge encoded/decoded payloads, too many base calls/qualities/peaks,
  too many trace-channel samples, and non-finite signal values; real-mode
  `/align` rejects ambiguous sequence+AB1 input; and pairwise alignment checks
  the matrix size before calling Biopython.
- **Resolved locally - viewer route perimeter.** `/api/v1/viewer` now uses the
  Workbench rate limiter, `GeneViewerRequest` fields/window values/tracks are
  bounded, and spoofable proxy-header trust for rate-limit client IP selection
  now defaults false unless explicitly enabled.
- **Resolved live per Claude/Steven - Supabase advisor cleanup.** Supabase
  0006 reportedly cleared the `public.rls_auto_enable()` advisor warning and
  security advisors are clean.
- **Residual - durable perimeter.** The limiter is still in-memory and
  single-instance; a multi-instance deployment should move counters to Redis,
  a private Supabase/Postgres table, or gateway controls. If forwarded-client-IP
  semantics are needed later, enable them only after reviewing the exact
  Render/gateway path.
- **Resolved - live env visibility.** Render `DEBUG=false` was reported set by
  Claude/Steven and is now directly verified by Codex through the Render API.

## Gene Viewer Dynamic Product Risks

Section edited: 2026-05-26 04:12 +1000 - Codex.

The gene/protein viewer now has an internal Eamos variant-applied product
workflow, but the following limits should remain explicit:

- It is a molecular-display workflow, not an ACMG classification engine. PVS1,
  NMD, LoF mechanism, rescue transcript, and pathogenicity strength should
  remain source-gated.
- Simple transcript-window SNV/indel/dup/delins edits are handled locally.
  Cross-segment, cross-exon, or ambiguous HGVS representations fail closed until
  the viewer can represent multi-segment edits without misleading geometry.
- Backend source confidence still matters. Prefer VEP/VariantValidator/ClinVar
  consequence data and keep unsupported protein-only or ambiguous alignments out
  of live variant-applied claims.
- Browser verification used Vite fallback sample data because the backend API
  was not running. Re-smoke with the backend running before treating live
  request/render wiring as end-to-end verified.
- Mobile Workbench horizontal overflow remains a separate frontend risk.

## Project-Wide Hardening Cohort

Section edited: 2026-05-26 20:10 +1000 - Codex.

The current ClinVar stack is not the project-wide hardening matrix Steven
clarified on 2026-05-26:

- Existing fixture shape:
  `app/backend/app/fixtures/tools/clinvar_gene_agnostic_report_stack.json` has
  10 non-RPE65 genes x 9 variants = 90 variants, plus one separate global
  RPE65 control.
- Required hardening shape is now defined in
  `app/backend/app/fixtures/hardening/project_100_sample_manifest.json`: 10
  chosen genes x (one per-gene reference/control render sample + nine challenge
  variants) = 100 samples across landing, variant report, and Workbench.
- Keep this as a separate hardening manifest instead of mutating the existing
  ClinVar report-stack fixture, because
  `app/backend/app/fixtures/workbench/gene_viewer_transcript_models.json`
  references the existing stack for curated snapshot hydration.
- Supabase storage can hold durable hardening artifacts/caches later, but only
  through backend-owned service-role paths with private schemas/buckets,
  explicit RLS/storage policies, and reviewed migrations.

## Old Agent-Split Assumptions

Some existing docs say or imply Claude Code owns substantive work while Codex
does backend/grunt/review work through the plugin.

Current interpretation:

- Those docs explain the historical workflow.
- They are not a technical restriction on direct Codex sessions.
- Direct Codex can do meaningful backend work when explicitly delegated.

## Shared Files

Section reconciled: 2026-07-15 11:19 UTC by Codex.

High-conflict files:

- `CHANGELOG.md`
- `PROGRESS.md`
- `ROADMAP.md`
- `CLAUDE.md`
- `CODEX.md`
- `agent_handoff/*`
- `plans/*`
- `app/web/lib/backend.ts`
- `app/frontend/src/lib/backend.ts`
- backend Pydantic schema files when frontend contract work is active

Guardrail:

- Claim the lock in `agent_handoff/CURRENT.md` before editing these surfaces.
  Update shared docs at task boundaries, not while another agent is actively
  editing adjacent work. Full mechanics live in `agent_handoff/README.md`.


## Private Source Storage Upload Limits

Section edited: 2026-06-01 01:31 +1000 - Codex.

The prior source Storage blockers are resolved for the staged dbSNP/phyloP
objects: Steven raised the Supabase project/global and private bucket limits to
50 GiB, configured local server-side S3 credentials, and explicitly approved
uploads. Codex uploaded dbSNP and phyloP through backend-owned S3 multipart
tooling and verified remote sizes match local sizes.

Current guardrails:

- Keep `eamos-source-assets` private. Do not use a public genomic/protein
  bucket, signed frontend raw-source URLs, direct frontend Storage reads, or
  browser-role grants for genomic/protein source assets.
- Local S3 credentials are server-side only and must remain in ignored `.env`
  or deployment secrets, never committed or emitted in logs/docs.
- Large source uploads should use the hardened S3 multipart path, not ordinary
  browser-style upload: path-style addressing, long connect/read timeouts,
  retries, TCP keepalive, and large multipart chunks. The current implementation
  uses 120s connect timeout, 300s read timeout, 10 retry attempts, 128 MiB
  chunks, and concurrency 3.
- Supabase `ListMultipartUploads` still reports stale upload IDs from failed
  attempts, but `AbortMultipartUpload` returns "The specified upload does not
  exist." Completed objects are size-matched and visible. Treat those stale IDs
  as non-actionable Supabase listing residue unless they persist beyond the
  provider cleanup window or block future operations.

## Private Database And Storage Boundary

Section consolidated: 2026-07-15 11:19 UTC by Codex from the retired
`database_webserver/` handoff.

- Never record service-role keys, database URLs, JWT secrets, S3 credentials,
  signed URLs, or deployment tokens in tracked docs or frontend configuration.
- `eamos_private` tables and source assets are backend-owned. Keep RLS enabled,
  revoke browser roles, and grant DML only to `service_role`.
- Frontend and Vercel code must use backend endpoints for source/cache data;
  never query private tables or raw object paths from the browser.
- Keep genomic, protein, and source-data buckets private. Backend readers must
  verify approval state, size, and checksum before accepting a materialization.
- After DDL, import, policy, or Storage changes, run Supabase security and
  performance advisors plus a bounded smoke query. Durable project, migration,
  and table inventory lives in `docs/db/supabase-inventory.md`.

## Gated Work

Section consolidated: 2026-07-15 11:19 UTC by Codex from the retired
pause register.

Do not start without explicit user direction:

- FE-6
- FE-7
- FE-8
- M-002 real engines
- Patient Report Pipeline (`/runs`, PDF upload/intake/clinician review). Do not
  extend the demo auth or upload/review/approve/chat/PDF-preview flow until the
  founder explicitly reopens it.
- AlphaMissense display/integration. Keep its assets and contract literals, but
  do not surface, remove, re-enable, or refactor them until the founder explicitly
  reopens that lane.
- branch surgery / destructive git ops (reset, clean, force-push, lineage
  rewrite) — Claude *commits* are no longer gated (see Dirty Worktree)
- broad cleanup/refactors

## M-002C Primer Provider Limitations

Section edited: 2026-05-28 20:49 +1000 - Codex.

Real primer design now uses local Primer3 via `primer3-py>=2.3,<3` in
`USE_REAL_APIS=true` mode. It now includes exact amplicon screening against the
resolved design template by default. It also has an opt-in local UCSC `isPcr`
whole-genome specificity provider when `PRIMER_SPECIFICITY_PROVIDER=ucsc_ispcr`
and local `isPcr`/`hg38.2bit` assets are configured. Current limitations are
deliberate and should not be misread as completed verification:

- With the default `PRIMER_SPECIFICITY_PROVIDER=template`, `specificity_hits`
  means exact products inside the resolved template window, not whole-genome
  hits.
- With `PRIMER_SPECIFICITY_PROVIDER=ucsc_ispcr`, `specificity_hits` means
  local UCSC `isPcr` whole-genome products from the configured hg38 `.2bit`
  file. The local assets are now installed under ignored
  `app/backend/data/bio_assets/**` and `hg38.2bit` MD5 was verified. The
  original 2026-05-17 native Windows smoke failed because the official UCSC
  `isPcr` binary is a Linux ELF. As of 2026-05-28, `Ubuntu-24.04` WSL2 is
  installed and native `pysam`/`pyBigWig` indexed-reader proofs pass there, but
  the `isPcr` provider itself still needs a separate WSL smoke before treating
  whole-genome primer specificity as verified.
- A direct online UCSC `hgPcr` call returned a Cloudflare/Turnstile
  bot-protection page from this environment on 2026-05-17. Do not rely on the
  interactive UCSC CGI endpoint for production backend specificity.
- Local UCSC `isPcr` is not NCBI Primer-BLAST; it does not provide
  Primer-BLAST's database/configuration checks or SNP-aware validation.
- SNP masking is not implemented yet even when `avoid_snps=true`; real primer
  pair notes state this explicitly.
- ARMS-specific real primer design is not implemented and returns a structured
  `422` unsupported-mode error.
- `primer3-py` packages Primer3 under GPL-family licensing; confirm this is
  acceptable before distribution decisions or before treating it as a
  production dependency.
- UCSC/Kent BLAT-family command-line executables have licensing constraints
  for commercial use; confirm distribution/deployment comfort before bundling
  binaries.

## M-002D CRISPR Provider Planning Risks

Section edited: 2026-05-17 23:42 +1000 · Codex.

M-002D first-slice implementation is now complete as a backend-only local
deterministic SpCas9 provider. Key risks/limits to carry forward:

- The DeepHF PyTorch class in the blueprint is architecture scaffolding only;
  no trained weights or model provenance were supplied. Do not ship
  random-weight "DeepHF" inference. First-pass on-target scoring should be
  transparently labelled as heuristic unless weights are sourced and reviewed.
- The existing `CrisprGuide.off_target_score` fixture behaves like a
  lower-is-better risk value, while Hsu specificity is a higher-is-better
  0-100 score. The backend plan recommends preserving `off_target_score` as
  `100 - hsu_specificity_score` for the first slice and adding an optional
  `specificity_score` only after explicit contract approval.
- The CRISPR blueprint had a formula/scaffold mismatch in the Hsu distance
  penalty constant (`2` in the prose formula, `4` in the scaffold/original
  implementation pattern). M-002D uses constant `4.0` and locks it in unit
  tests against the MIT/Hsu-style position, distance, and mismatch-count
  formula.
- Genome-wide off-target enumeration requires approved local reference assets
  and Bowtie/BWA indexes. The implemented deterministic in-context scan tests
  Hsu math, but it must not be marketed as whole-genome specificity.
- The prompt's PostgreSQL storage request is broader than the first provider
  slice. The current backend defaults to SQLite; any persistent CRISPR guide
  repository should be a separately approved storage task with migration and
  deployment decisions.
- Blueprint 2 post-edit analytics is a separate workflow from guide design and
  should share any AB1 parser with M-002E alignment rather than creating a
  second trace parser.
- M-002D did not add raw target sequence/genomic-region request fields or
  frontend `specificity_score`; keep those as explicit paired contract-change
  approvals if needed.

## Gene Viewer Real-Data Contract Risks

Section edited: 2026-05-18 15:18 +1000 - Codex.

Draft planning artifacts are in `plans/gene-viewer/`. Carry these risks into
implementation:

- `POST /api/v1/viewer` now exists and fixture mode returns the backend RPE65
  viewer payload, including explicit reference versus variant-applied display
  mode. The current Workbench frontend is still driven by the frontend RPE65
  sample until GV-005/GV-006 coordination lands.
- The existing backend `SequenceContextService` resolves a narrow design-engine
  sequence window, not a full transcript/exon/intron/protein viewer model.
- RPE65 is reverse-strand and uses both RefSeq (`NM_000329.3`) and Ensembl/MANE
  identifiers in the materials. Implementation must bridge aliases and test
  reverse-strand transcript-oriented coordinates instead of assuming genomic
  plus-strand order.
- Reference/control versus variant-applied mode is a new contract decision.
  The draft recommends defaulting to reference/control and making variant mode
  explicit.
- The supplied RPE65 brief is intentionally ambitious and includes PostgreSQL,
  Redis, Celery, and broad ingestion. The draft plan deliberately defers those
  runtime additions until the viewer contract and source-backed coordinate
  layer are proven.
- GV-008 live-smoked the default HTTP source client for RPE65 `c.260A>G`:
  VariantValidator resolved GRCh38 `1-68444869-T-C` and protein consequence
  `p.Asp87Gly`; Ensembl symbol lookup hydrated MANE/RefSeq transcript
  `NM_000329.3` / `ENST00000262340.6`, reverse-strand exon/CDS windows, and
  translation protein-domain overlap. This proves the RPE65 happy path, not
  broad gene/variant completeness.
- Live ClinVar gene-wide hydration is not implemented yet. The protein view
  should use a lollipop-style ClinVar track, but ClinVar marker size must not
  imply patient/cohort frequency unless backed by a real count source.
- Do not let primer, CRISPR, or alignment consume a new viewer sequence basis
  until the viewer endpoint is implemented, contract-tested, and the user
  approves a tool contract follow-up.

## Verification Expectations

Use focused verification scaled to the task:

- Backend/API/schema: `cd app/backend && python -m pytest tests/ -q`
- Contract: `cd app/backend && python -m pytest tests/test_frontend_contract.py -q`
- Frontend: `cd app/frontend && npm run build`
- Frontend unit tests: `cd app/frontend && npm run test`
- Browser/pixel checks: required after meaningful Workbench UI changes.

If a check is not run, record it in `agent_handoff/CURRENT.md`.
