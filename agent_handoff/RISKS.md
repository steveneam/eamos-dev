# Agent Risks And Guardrails

## 1e86a78 Protein Annotation — Render OOM + Protein-Feature Regression (→ Codex)

Section added: 2026-06-15 22:08 +1000 · Claude (prod incident the moment `1e86a78`
went live). **Owner: Codex (backend lane).**

Commit `1e86a78` (`fix(protein): hydrate curated feature architecture` —
`protein_annotation.py` +379, `ReportGeneViewer.tsx` +359, new
`eamos_uniprot_feature_index` CLI) reached prod for the FIRST time on 2026-06-15
~21:58 +1000 — its original auto-deploy was a dropped GitHub→Vercel webhook, so it
was never live-verified on Vercel until Claude re-triggered it via `50d9dc8`. Render
SG had already been on `1e86a78` (Codex). Two regressions surfaced immediately:

- **HIGH — Render SG out-of-memory.** Render event: instance `8wqsn` "Ran out of
  memory (used over 2GB) while running your code" at 2026-06-15 22:00 +1000, then
  "Service recovered" (auto-restart). SG is the Standard **2 GB** instance — 2 GB is
  the hard ceiling. Almost certainly the USH2A protein annotation (5,202 aa) through
  `1e86a78`'s reworked `protein_annotation.py`. While OOMing, the backend returned a
  degraded `/viewer` payload and the report's "Gene & Locus context" briefly rendered
  raw SVG as text; it self-corrected after the instance recovered. **→ Codex: profile
  `protein_annotation` memory on large proteins, look for a leak / unbounded
  buffering (full feature-table parse, HMMER, or live UniProt fetch held whole in
  memory), stream/cap it. Inefficient coding / memory leak suspected.**
- **MED — protein features regressed vs the previously-shipped view.** The new
  UniProt-first "curated feature architecture" path needs `uniprot_features_enabled=true`
  + a **seeded UniProt feature index on Render**, both OFF/not-ready
  (`uniprot_features_enabled=false`, `uniprot_feature_index.ready=false`, per Codex's
  own handoff). With the index unavailable, fewer features surface than Codex's earlier
  verified state ("50 architecture blocks, 248 source hits, FN3 ranges"); the new FE
  also hides "sites" by default behind category filters. Net: features Codex previously
  added read as missing in prod. **→ Codex: either provision/seed the Render UniProt
  feature index and flip the flag, or make the flag-off path fall back to the full prior
  Pfam/HMMER architecture without dropping features.**

Mitigation (Steven's call): roll back prod to the last verified-good deploy
(`1c2df8b` FE + matching backend) until `1e86a78` is fixed, or keep it live and fix
forward. Vercel rollback target = `dpl_4FZS9XtQxjrvXmDFyCNGtPPpvpfc` (1c2df8b,
rollback-candidate).

## AI Gateway Chat — Pre-Launch Security Gate

Section edited: 2026-06-12 02:22 +1000 · Claude (from the vibe-security audit of
the variant-chat gateway foundation).

**Do not enable the `/report` variant chat against the live gateway in production
until these are addressed.** Full detail + fixes: `docs/ai-gateway/pre-launch-security.md`.

- **The real on/off switch is server-side `LLM_PROVIDER`** — keep production on
  `mock` (do not set `gateway`) until the items below are done. The frontend
  `NEXT_PUBLIC_AI_CHAT_ENABLED` flag is a UX gate only and is client-bypassable.
- **HIGH — `POST /api/v1/chat/stream` is unauthenticated, rate-limit-only**
  (`RATE_LIMIT_CHAT`, 10/window/IP). Wired to the paid gateway this is a cost-abuse
  vector; the `$50/mo` key cap bounds but can be exhausted (also a DoS for real
  users). Before prod-enabling: add **auth** (decide if `/report` chat should require
  login — product call) **and/or a per-user/tier daily token budget**, server-side.
  Do not rely on the provider cap alone.
- Companion launch items: **re-mint the gateway key** (it passed through a session
  transcript) and **top up paid credits** (free tier rate-limits `meta/llama-3.3-70b`).
- Audit found no Critical issues; secret handling, prompt-injection guards, the
  evidence-only outbound allowlist, no-XSS rendering, and no-SSRF were all clean.

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

Setup decided 2026-06-02 (see `agent_handoff/DECISIONS.md`): Hobby workspace +
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

High-conflict files:

- `CHANGELOG.md`
- `PROGRESS.md`
- `ROADMAP.md`
- `CLAUDE.md`
- `plans/*`
- `app/frontend/src/lib/backend.ts`
- backend Pydantic schema files when frontend contract work is active

Guardrail:

- Update shared docs at task boundaries, not while another agent is actively
  editing adjacent work.

## Repo Drive Relocation

Section edited: 2026-05-28 23:02 +1000 - Codex.

The removable `E:` drive reports `HealthStatus=Warning` /
`OperationalStatus=Full Repair Needed` and should not remain the Eamos repo
drive. The coordinated mitigation is relocation to internal `D:`. Once the
repo is moved and verified on `D:`, Eamos does not require `E:` repair; leave
`E:` as an unresolved hardware/media issue outside the repo workflow.

Residual risk: `E:\` removable drive Full Repair Needed flag never resolved;
repo relocated 2026-05-28 to `D:\` to avoid working off failing media. `E:\`
retained as cold backup until both agents verified on `D:\` across at least
one full session.

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

## WSL / Linux RAM Guardrail

Section edited: 2026-05-31 19:49 +1000 - Codex.

The post-move WSL `/mnt/d` proof path triggered a host crash when `vmmemWSL`
consumed available RAM. Do not launch WSL/Linux for routine Eamos work.
Windows-native checks are the default. If WSL-native proof work is explicitly
approved later, first confirm `%USERPROFILE%\.wslconfig` still caps WSL2 at
`memory=4GB`, `processors=2`, `swap=2GB`, and `guiApplications=false`; shut
WSL down immediately after the run.

Codex used this guarded path on 2026-05-31 for the dbSNP/ClinVar/phyloP native
reader proof after Steven's explicit approval. The cap was confirmed first, the
proof completed, and `wsl.exe --shutdown` was run afterward.

## Gated Work

Do not start without explicit user direction:

- FE-6
- FE-7
- FE-8
- M-002 real engines
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
