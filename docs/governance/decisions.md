# Agent Coordination Decisions

Relocated from `agent_handoff/DECISIONS.md`: 2026-07-15 21:39 +1000 by Codex
to keep durable reference material outside the live session handoff.

## 2026-07-19: Workbench Design-Binding Contract Re-plan Approved

Section added: 2026-07-19 13:08 +0000 · Codex.

Decision (Steven, 2026-07-19): approve the minimal contract re-plan needed to
bind Primer, CRISPR, and Align requests to canonical Workbench build/reference
basis, edit revision, and context digest. Begin that re-plan next session, not
during the current wrap.

This approval authorizes the bounded planning/contract amendment and its local
verification. It does not approve a lane merge, red-CI waiver, Task F or other
Supabase mutation, deploy, provider/source action, Phase 7, or cleanup. Lane B
still requires green GitHub Actions and Steven's explicit merge approval.

## 2026-07-19: Repository-Local Google Fonts Approved

Section added: 2026-07-19 11:14 +0000 · Codex.

Decision (Steven, 2026-07-19): approve downloading and committing the existing
Inter, Spectral, and IBM Plex Mono faces so local and hosted builds no longer
depend on the live Google Fonts service. For this font-only slice, use the
manual/no-Actions route Steven requested: verify the complete frontend gate and
an outbound-network-constrained production build locally, push the verified
commit to `main` with CI skipped, and require the real Vercel deployment to pass.

Receipt: commit `a79d08b` vendors the seven exact Latin WOFF2 assets emitted by
the previously successful Google-backed build, preserves the existing weights,
CSS variables, swap behavior, and fallback stacks, and stores each upstream SIL
OFL 1.1 notice beside its family. Web tests passed 193/193; TypeScript, ESLint,
the 275-file web boundary, and a production build with HTTP(S) routed through a
dead local proxy passed. No GitHub Actions run started, and Vercel production
deployment `HoZVc4nrJARWYRvJ6ZQdvyxeSTvo` completed successfully.

This is a separate per-instance font-resilience exception. It does not widen
the Lane A exception or waive CI/merge, Task F, Supabase, deploy, provider,
source, Phase 7, or other founder gates for any later Product Workflow lane.

## 2026-07-19: Lane A Manual CI Substitute Approved

Section added: 2026-07-19 10:51 +0000 · Codex.

Decision (Steven, 2026-07-19): GitHub Actions is automation rather than the
substance of the gate. For Product Workflow Lane A only, replace the unavailable
hosted run with a complete local-equivalent verification, then commit and push
the verified contract to current `main` with CI skipped. This is the explicit
per-instance exception to Lane A's green-required-CI rule and the approval to
integrate Lane A after that substitute gate passes.

The substitute receipt must retain the exact changed paths, focused and full
backend tests, web tests/typecheck/lint, structural and coordination ratchets,
dependency audits, formatting/static checks, and a real Vercel build. Known
environment limits must remain visible rather than being reported green: this
Linux host has no Docker executable, and its local Next build cannot reach
Google Fonts. Lane A changes no container/build files, and main promotion waits
for the same commit's fresh Vercel preview.

This exception does not waive Task F, any Supabase mutation, later-lane gates,
production backend deployment, providers, sources, Phase 7, cleanup, or any
other cloud action. It does not manufacture or relabel the failed zero-step
Actions run as green.

## 2026-07-19: Product Workflow V1 And Five-Lane Sprint Approved

Section added: 2026-07-19 09:43 +0000 · Codex.

Decision (Steven, 2026-07-19): approve the Product Workflow V1 contract and the
five-lane Mode B partition in `plans/product-workflow-integration/`. Full gene
means the continuous resolved locus across every exon, intervening intron, and
UTR; the queried variant is initial focus only. Lane A may launch on the next
`gogogo`, subject to the already-recorded recovery-check ordering.

Supabase uses the repository's existing serialized convention:

- Lane B is the sole owner of its allocated migration file and may author and
  test it locally.
- A lane never links to or mutates the shared Supabase project. The Codex lead
  owns the post-merge application checkpoint from current `main`.
- Remote application is part of completing the sprint, not an indefinite
  backlog. Before applying, the lead follows
  `docs/architecture-consistency-gate/task-f-supabase-production-readiness-runbook.md`,
  reconciles the remote migration ledger, fills the exact mutation approval
  template, and obtains Steven's confirmation for the named command/SQL,
  objects, rollback, and target.
- The current known target is dev project `eamos-dev`
  (`cpdjxsgasaesysvxkpmi`). Verify that live identity and migration state at the
  checkpoint; this approval does not authorize any other or future production
  project.
- After application, run RLS/grant and two-user ownership smokes, security and
  performance advisors, bounded lifecycle/delete tests, and update
  `docs/db/supabase-inventory.md` with the sanitized receipt.

Every lane merge still waits for Steven's explicit approval and green required
CI. All cloud/provider/source/Phase-7 holds outside that named, reviewed dev
migration remain unchanged.

## 2026-07-16: One Free Predictor Catalog, Decide Source Retention Later

Section added: 2026-07-16 12:47 +0000 · Codex.

Decision (Steven, 2026-07-16): Eamos exposes one free predictor catalog now.
Remove the product-facing `Free`/`Pro` and `Public`/`License review` distinctions,
restore REVEL and SpliceAI to product copy, and include every wired predictor.
Steven will decide later which sources stay or go.

This explicitly supersedes the 2026-05-19 AlphaMissense display hold and the
predictor-marketing restrictions recorded in the first 2026-07-16 free-landing
pass. AlphaMissense, ESM1b, REVEL, PrimateAI-3D, MetaLR, CI-SpliceAI, SpliceAI,
Pangolin, CADD, GPN-MSA, and CAPICE are all part of the same free product.

Implementation boundary:

- No predictor access pill, paywall, upgrade prompt, entitlement filter, or
  license-review placeholder belongs in the frontend.
- Retired `excluded_predictors` payload hints do not suppress returned rows in
  the report profile or computational call card.
- A score absent because an artifact, upstream result, or runtime is unavailable
  remains an honest data/readiness state. It is not an access tier.
- Preserve license, provenance, `launch_gate`, and
  `public_serialization_allowed` metadata on backend rows, health, and preflight
  so the later keep/remove decision has evidence. Metadata is informational now;
  do not erase it or turn it into account-role/auth plumbing.
- This decision does not authorize source downloads/materialization, provider or
  cloud changes, redistribution workarounds, or fabricated scores.

## 2026-07-08: Agent-Agnostic Ownership (supersedes role-pinned lane decisions)

Section edited: 2026-07-08 22:43 +1000 - Claude.

Decision (Steven, 2026-07-08): **ownership is agent-agnostic.** Any agent
(Claude or Codex) can edit any file and own everything full-stack — frontend,
backend, data/pipeline, docs, tests, tooling — including auditing/fixing the
other agent's historical work, dependencies, and branches. Steven picks the
active agent by **availability and usage limits**, not by task type. The old
Claude=frontend / Codex=backend wall is retired. Canonical: README Hard Rule 3
+ memory `feedback_agent_agnostic_ownership`; encoded in CLAUDE.md, CODEX.md,
AGENTS.md, COORDINATION.md, agent_handoff/README.md, plans/README.md, README.md.

**Effect on earlier decisions below — role-pinning superseded, substance kept.**
Where a prior decision names a role ("Codex owns X", "Codex-owned paths",
"Codex default staging scope = `app/backend/**`", "Claude/frontend files"),
read the role as **the acting/owning agent**; the operational substance still
applies to whichever agent does the work:

- **2026-07-02 (Standing commit/push/deploy-when-safe):** the standing approval
  is for **any agent**, not just Codex — commit/push/deploy after a slice is
  verified safe, under the same guardrails (no env/provider/Supabase/materialize/
  destructive-git/secret actions; DL-019 explicit staging).
- **2026-06-01 (Backend Render redeploy + verify):** **deploy-ownership follows
  the pusher** — whichever agent commits/pushes a backend change owns its Render
  redeploy + live-verify loop (don't ping-pong). Technical facts unchanged
  (`.render-deploy-hook`, `RENDER_API_KEY` in shell env, Render autoDeploy off).
- **2026-05-27 (DL-019 staging):** the CORE rule stands and is agent-agnostic
  (explicit paths only; never `git add -A`/`.`/`commit -a`; stage only the paths
  for *your* change). The "Codex = `app/backend/**` / Claude = frontend" scope
  bullets are retired — the durable principle is **stage only your change's
  paths and never sweep the other agent's in-flight or unrelated work into your
  commit** (regardless of which folder it lives in).

Kept in full (only the role wall is removed): the coordination + safety
machinery, schema-first contracts (was "backend-led" — an ordering rule, not a
role rule), and the parallel-worktree sprint model (lead = proposing agent =
sole merger; Steven approves each merge).

## 2026-07-02: Codex Standing Commit/Push/Deploy Approval When Safe — [role-pinning SUPERSEDED 2026-07-08; see top entry]

Section edited: 2026-07-02 19:13 +1000 - Codex.

Decision (Steven, 2026-07-02): Codex may commit, push, and deploy after a
slice is verified safe, without asking Steven to repeat that approval each
time.

Scope and limits:

- This approves normal Codex-owned commit, push, and deploy execution after
  verification is green and the worktree/staging set is reviewed.
- It does not approve env/provider flips, Supabase mutations, runtime
  seed/sync, source materialization/download/upload, destructive git, cleanup
  deletion, or secret output.
- DL-019 still applies: run `git status --short` first, never use `git add -A`,
  `git add .`, or `git commit -a`, and stage explicit Codex-owned paths only.
- Deployment still requires normal post-deploy health/live verification and
  handoff/progress documentation.

## 2026-06-16: Tier 1 Materialization First

Section edited: 2026-06-16 22:18 +1000 - Codex.

Decision (Steven, 2026-06-16): after Epic A A12, prioritize the product-value
Tier 1 materialization lane first: ClinGen local, PubMed local, and literature
embeddings/RAG. Tier 2 predictor score caches and Tier 3 dbSNP/phyloP infra
batch remain important, but Tier 1 should be the next materialization sequence
unless Steven redirects.

Rationale: Tier 1 is small relative to dbSNP/phyloP, unlocks visible evidence
quality sooner, and can proceed alongside later infrastructure batching without
replacing `docs/backend-build-ledger-runtime/materialization-plan.md`. Guardrails
remain unchanged: materialize offline first, no startup downloads, no Supabase
apply/provider flip without explicit approval, no `LOCAL_EVIDENCE_ENABLED` flip
until the selected batch is verified.

## 2026-06-02: Render Plan Layout For Live Local-First Assets

Section edited: 2026-06-02 01:44 +1000 - Claude (Steven-decided; Codex-verified).

Decision (Steven, 2026-06-02) for wiring the local-first source adapters to the
live SG backend. Render has THREE separate billing layers (workspace plan /
runtime instance / build pipeline) plus disk — keep them straight:

- **Workspace plan = Hobby ($0).** DONE 2026-06-02. A persistent disk needs a
  paid *instance*, NOT the Pro workspace; Steven is solo so the Pro perks (team
  seats, horizontal autoscaling — moot once a disk is attached, audit/compliance,
  preview envs) aren't needed. Saves $25/mo.
- **SG runtime instance = Standard (~$25/mo, 2 GB RAM / 1 CPU).** PENDING (Steven
  bumps 2026-06-03). Starter's 512 MB is too tight: expected peak ~350-550 MB RSS
  for FastAPI + dbSNP (pysam/tabix) + phyloP (pyBigWig), with no margin for
  concurrency / allocator spikes / Pfam. SG is the SOLE backend, so don't gamble.
- **Persistent disk = 60 GB at mount path `/var/data`** (~$15/mo @ $0.25/GB).
  PENDING (2026-06-03). dbSNP ~29.55 GB + phyloP ~9.87 GB ≈ 40 GB of downloads
  alone, before hg38.2bit / protein / Pfam / HMMER indexes / temp / headroom;
  repo preflight encodes 60 GB. 10 GB impossible, 50 GB tight. Eamos assets live
  under `/var/data/eamos/...`.
- **Build pipeline = Starter (1,000 free min).** Unchanged; Performance not needed.

Provisioning (workspace / instance / disk toggles) = Steven's dashboard/billing.
Seeding + env wiring + the dbSNP/phyloP adapter materialization = Codex's backend
lane. Operational reality, env vars, and the seeding sequence: see
`docs/operations/risks-and-guardrails.md`
"Render Persistent Disk + Local-First Asset Seeding".

## 2026-06-01: Codex Owns Backend Render Redeploys And Verification — [role-pinning SUPERSEDED 2026-07-08 → deploy-ownership follows the pusher; see top entry]

Section edited: 2026-06-01 03:07 +1000 - Codex.

Decision (user-mandated, 2026-06-01): after Codex owns a backend commit and
push, Codex should also own the Render redeploy and live verification loop.

Operational default:

- Codex pushes backend commits when explicitly approved.
- Codex triggers the relevant Render deploy hook or official Render API/CLI
  deploy path.
- Codex polls Render until the target commit's deploy is live.
- Codex verifies backend health and the relevant live API smoke directly,
  including Vercel proxy checks when frontend traffic depends on that backend.
- Claude should not be expected to redeploy or verify backend Render services
  after a Codex backend push unless Steven explicitly redirects ownership.

Guardrails remain unchanged: no unapproved Render/Vercel/Supabase mutation,
no secret output in chat/docs/logs, keep Oregon or other fallback services
untouched unless Steven explicitly approves, and record live verification in
the handoff/progress notes.

## 2026-05-29: CLI First For External Services

Section edited: 2026-05-29 01:47 +1000 - Codex.

Decision (Claude/Steven handoff, 2026-05-29): for any external-service action
against Vercel, Render, Supabase, Stripe, GitHub, PostHog, Resend, Porkbun, or
similar services, try the official CLI first. If no CLI command exists for the
action, use the REST API with a short-lived token and revoke it afterward. If
neither works, fall back to MCP, preferably read-oriented tools only. Last
resort is a dashboard click run by Steven.

Do not use community-maintained wrapper CLIs or write reverse-engineered
scraper CLIs without explicit Steven approval.

Practical notes:

- Installed/authenticated on Windows: Vercel CLI via `npx vercel@latest`
  (auth at `%USERPROFILE%\.vercel\auth.json`, Steven logged in as `steveneam`).
- Installed on Windows PATH: Supabase CLI at
  `C:\Users\seamegdool\AppData\Roaming\npm\supabase`; it still needs
  `supabase login` before use.
- Pending installs if needed: Stripe CLI and Render CLI.
- Windows and WSL Ubuntu do not share CLI binaries or auth state. For current
  WSL-native reader proofs, keep external-service CLI work in Windows
  PowerShell and do not install Vercel/Supabase/Stripe/Render CLIs inside WSL
  unless a separate Linux-specific need is approved.
- Vercel MCP stays available for logs, deployments, and project metadata, but
  writes/config changes should use the official `vercel` CLI first.
- Project `.mcp.json` remains acceptable with Supabase, Render, Vercel, and
  chrome-devtools. Claude-side claude.ai Connectors are a separate token budget
  concern; unused Gmail, Google Calendar, and Google Drive connectors should be
  disconnected by Steven. PubMed is optional because the backend already wraps
  PubMed via E-utilities.
- Printing Press / `printingpress.dev` is not adopted for Eamos now. It is
  directionally aligned with the CLI-first rule, but Eamos should prefer
  official APIs, FTP/indexed files, and official CLIs. Reverse-engineered CLIs
  are too ToS-fragile for regulated bioinformatics work and too new to become a
  load-bearing dependency.
- Repeated multi-step Eamos workflows may get repo-local scripts such as
  `scripts/eamos-*.ps1` that wrap official CLIs in sequence. These are allowed
  because they live in the repo and avoid third-party CLI drift.

Reasoning: Phase 2 branch coordination showed Vercel project branch config was
resolved cleanly by `vercel git disconnect` / `vercel git connect`, after
MCP/REST/dashboard exploration burned time on unsupported endpoints. The
preferred escalation order is official CLI -> REST API -> MCP -> dashboard.
Claude's Printing Press follow-up also reinforced the token-economy rationale:
MCP tool schemas and large raw API payloads are expensive; local CLI
summarization keeps context smaller and tends to be more reliable.

## 2026-05-27: DL-019 Explicit Git Staging Rule — [core rule stands; per-agent scope bullets SUPERSEDED 2026-07-08, see top entry]

Section edited: 2026-05-27 23:27 +1000 - Codex.

Decision (user-confirmed, 2026-05-27): both agents must stage commits with
explicit paths only.

- Run `git status --short` before any staging or commit operation.
- Never use `git add -A`, `git add .`, or `git commit -a`.
- Use `git add -- <paths>` with paths scoped to the owning agent's lane.
- Codex default staging scope is `app/backend/**`, backend-owned docs/plans,
  and explicitly approved shared files only.
- Claude/frontend files, `plans/v2-redesign-impeccable.md`, Claude archive
  files, and unrelated docs must not be swept into Codex commits.
- Claude should likewise not sweep Codex `app/backend/**` work into a
  Claude-lane commit without explicit coordination.

Reasoning: broad staging on 2026-05-27 accidentally mixed frontend files into
backend commit attempts. Explicit staging preserves parallel-lane ownership and
keeps commit messages truthful.

Durable coordination decisions only. Section edited: 2026-05-19 14:22 +1000 ·
Codex (AlphaMissense hold backend fixture alignment). Superseded/done
decisions are marked inline (kept for rationale, not
re-litigation); the protocol itself lives in `agent_handoff/README.md`.

## 2026-05-21: Variant Input Architecture - Eamos Resolver Orchestrates Sources

Decision (user/Codex alignment, 2026-05-21): VariantValidator stays in the
variant-input pipeline, but only as one specialist source. It must not be the
single front door for all user input or all downstream source calls.

The durable architecture is:

- **Eamos Search Input Resolver is the orchestrator.** It detects the submitted
  form (`GENE:c.`, transcript HGVS, RefSeq genomic HGVS, gnomAD
  `chr-pos-ref-alt`, rsID, protein text where supported), resolves missing
  identifiers, records provenance/warnings, and emits source-specific query
  inputs.
- **VariantValidator is a specialist.** Use it for transcript HGVS
  normalization and transcript-to-GRCh38 coordinate mapping when it succeeds.
  Do not clone all of VariantValidator locally unless absolutely necessary.
- **Ensembl/MANE is a transcript resolver.** Use it when the user gives
  `GENE:c.` without an NM/ENST accession.
- **gnomAD receives VCF-style genomic IDs** such as `17-43057062-T-TG`, not
  transcript HGVS.
- **ClinVar should prefer resolved NC genomic HGVS** when available because
  loose transcript/cDNA searches can return unrelated top hits.
- **Literature search receives a term bundle,** not one brittle identifier.
- **Future hardening:** cache successful mappings locally and extend
  non-SNV/indel RefSeq genomic parsing, but keep external specialist sources
  in the loop with provenance.

Reasoning: live source work on 2026-05-20/21 showed that VariantValidator is
valuable but limited by input form support, timeouts, and source-specific
expectations. ClinVar transcript searches for USH2A/BRCA1 returned wrong top
hits, while NC genomic HGVS returned the intended records; gnomAD accepts the
chromosome-position-ref-alt form best. The robust path is therefore a custom
Eamos orchestrator that prepares the right identifier for each source rather
than trusting any single external resolver as the whole pipeline.

Implication: future backend work should improve the Eamos resolver/CLI and
source-specific adapters, not replace VariantValidator wholesale and not send
the same raw user string to every website.

## 2026-05-19: Naming Convention + Patient Report Pipeline On Hold

Decision (user-mandated, 2026-05-19): the word **"report" is ambiguous and
must not be used bare** in coordination, commits, or UI/handoff prose. Use
the canonical names:

- **Variant Evidence Report** — route `/report`, `ReportPage.tsx`, fed by
  `POST /api/v1/lookup` (**unauthed**; never was auth-broken). The
  post-search structured evidence report. **This is the active focus** —
  both agents' report work means *this*.
- **Patient Report Pipeline** — route `/runs`, `LegacyRunsApp.tsx`, PDF
  upload → intake → clinician review/approve (**auth-gated**). **ON HOLD.**
  No further `/runs` work by **Claude or Codex** until the user explicitly
  says so. The auto demo-session auth wiring already shipped (2026-05-19) is
  complete — leave it as-is, do not extend or build on it.

Implication for Codex: its prior "take the landing/report visual pass" /
"/runs upload auth" next-steps are **superseded** — `/runs` is parked;
"report" = the variant evidence report only. Always qualify the term.

Reasoning: repeated cross-agent confusion this session between the two
"report" surfaces caused work to start on the wrong one. Locking the
vocabulary + parking the patient pipeline removes the ambiguity.

## 2026-05-19: AlphaMissense On Hold (user decision)

Decision (user-mandated, 2026-05-19): **AlphaMissense is on hold. Do not
advance, surface, or re-enable it until the user explicitly approves.** It is
*on hold*, not cancelled — keep all assets.

- **Kept (do NOT remove):** the `'AlphaMissense'` contract literal in
  `app/frontend/src/lib/backend.ts` + `app/backend/app/schemas/run.py`,
  `sample-report.ts` sample assets, and any AlphaMissense tool/asset code.
  The live Variant Evidence Report fixture card/prose was removed by Codex on
  2026-05-19 per the backend ask below; the integration remains reversible.
- **Claude (FE) — DONE:** AlphaMissense removed from landing + variant-report
  UI via render filters (`InSilicoGrid`, `EvidenceTable`), `VariantHeader`
  sample-stat drop, `sources.ts` 6→5, landing copy "six→five",
  `sample-report.ts` consensus prose de-enumerated.
- **Codex (BE) — DONE 2026-05-19 14:22 +1000:** dropped AlphaMissense from
  `app/backend/app/fixtures/lookup_v2_modules.json` `in_silico_predictions`
  (the predictor card **and** the `consensus_note` "(REVEL, AlphaMissense,
  MetaLR)" enumeration) so the live Variant Evidence Report (`/report`) prose
  matches the FE removal.
  Contract literals were not touched. (See `CURRENT.md` → Cross-Agent
  Requests.)
- **Re-enable** is a single coordinated revert (FE filters + BE fixture) and
  requires explicit user approval — do not self-initiate.

Reasoning: user wants AlphaMissense parked without losing the integration so
it can be switched back on cleanly. Earlier the standalone AlphaMissense
*fetch tool/build plan* was cancelled (2026-05-14) — distinct from this
display-hold of the *predictor*; do not conflate.

## 2026-05-18: Dedup Protocol Into One Home + Trim CURRENT.md

Decision (user-mandated):

- The cross-agent protocol (hard rules, locks, idle, stop/break,
  resume-prompt format) lives **once** in `agent_handoff/README.md`.
  `CLAUDE.md`, `CODEX.md`, `CURRENT.md` point there, not re-state it.
- `CURRENT.md` is **state only** and is updated at **major** task/milestone
  boundaries only — replace your section, never stack history (new README
  Hard Rule 9). Incremental history goes to `PROGRESS.md` + each agent's own
  next-session doc.
- `WORKTREE_INVENTORY.md` retired (frozen snapshot; `git status` is the live
  truth) — archived verbatim, body stubbed to a redirect.

Reasoning: the hard rules were duplicated in 4 files (drift risk); `CURRENT.md`
had grown to 1200 lines, ~650 of which were stacked Codex history + ~250 lines
of re-encoded protocol. The pristine 1200-line `CURRENT.md` and old
`WORKTREE_INVENTORY.md` are archived verbatim under
`agent_handoff/archive/2026-05-18-*` (README Hard Rule 1 — nothing lost).

Implication: change a rule once (README.md). Both agents keep their own
incremental logs; `CURRENT.md` carries only the current major state.

## 2026-05-17: Create `agent_handoff/` As Universal Sync Point

Decision:

- Use `agent_handoff/` as the live operational coordination folder for Claude
  Code and direct Codex.

Reasoning:

- `CHANGELOG.md` should stay historical.
- `PROGRESS.md` should stay a session/build log.
- `ROADMAP.md` should stay strategic.
- `plans/*` should stay detailed execution plans.
- Agent handoffs are tactical and can be messy; they need their own workspace.

Implication:

- Both agents should read `agent_handoff/CURRENT.md` before editing.
- Both agents should update `agent_handoff/CURRENT.md` after finishing.

## 2026-05-17: Direct Codex Access Changes The Work Dynamic

Decision:

- Treat direct Codex as capable of substantive backend/API/pipeline/tool/test
  work, not only grunt work.

Reasoning:

- The old split came from plugin-mode limitations and access uncertainty.
- Direct Codex has now verified workspace filesystem access and outbound network
  connectivity.
- Direct Codex can inspect the full repo, run commands, edit files, and verify
  backend work directly.

Implication:

- Claude Code no longer needs to babysit Codex with excessive context for every
  backend task if the task is scoped and this folder is current.
- The user can delegate real backend tasks directly to Codex.
- Claude Code remains valuable for frontend/design/product context and for
  reviewing direct-Codex backend patches when useful.

## 2026-05-17: Sequential First, Parallel Later — SUPERSEDED 2026-05-17

**Superseded:** parallel mode is now ON (README Hard Rule 3). Kept for
rationale only.

Decision:

- Run Claude Code and Codex one at a time initially.
- Move to separate terminals only after both agents consistently use
  `agent_handoff/`.

Reasoning:

- The repo has a large intentional dirty worktree.
- The old assumptions are still present in existing docs and Claude's current
  context.
- Sequential handoff reduces accidental overlap while the new protocol settles.

Implication:

- At first, every task should end with a `CURRENT.md` update.
- Once stable, parallel work is acceptable with explicit disjoint file scopes.

## 2026-05-17: Stable Docs Need A Small Workflow Sync — DONE 2026-05-17

**Done:** the workflow doc-sync completed (see `TASKS.md`). Kept for rationale
only. Note: the 2026-05-18 restructure further consolidated the protocol into
`agent_handoff/README.md` as the single home.

Decision:

- Update stable workflow docs so future Claude Code sessions do not keep
  treating old direct-Codex limitations as current.

Files that should be updated:

- `CLAUDE.md`: primary repo behavior file. It currently says Codex owns grunt
  work and implies Codex cannot run server/build/live verification. That should
  be revised for direct Codex while preserving the UI/backend ownership default.
- `plans/README.md`: currently describes the Claude Code plugin `/codex:rescue`
  flow as the Codex path. It should distinguish historical/plugin delegation
  from direct Codex sessions.
- `README.md`: small update only where it points to the old plugin-based
  workflow or stale network-clearance assumptions.
- `PROGRESS.md`: add a short session note that direct Codex access was verified
  and `agent_handoff/` was created.
- `ROADMAP.md`: small hygiene update, especially the plugin-specific Codex
  dispatch reliability row.

Files that should usually not be updated for this workflow sync:

- `CHANGELOG.md`: leave historical entries intact.
- `plans/v2-backend.md` and `plans/v2-frontend.md`: treat as active/historical
  execution plans; do not churn unless the implementation plan itself changes.

Implication:

- This doc-sync is a good first Claude Code task tomorrow because it aligns
  Claude's future behavior before new implementation work starts.
- Keep edits small and surgical; no app code.
