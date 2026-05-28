# Agent Coordination Decisions

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

## 2026-05-27: DL-019 Explicit Git Staging Rule

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
