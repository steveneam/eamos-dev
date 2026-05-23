# Agent Risks And Guardrails

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

Section edited: 2026-05-17 23:07 +1000 · Codex.

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
  `app/backend/data/bio_assets/**` and `hg38.2bit` MD5 was verified. A live
  local `isPcr` smoke was attempted on 2026-05-17 but is blocked on this native
  Windows host: the official UCSC `isPcr` binary is a Linux ELF and no WSL
  distribution is installed, causing `WinError 193` / structured `503
  workbench_provider_unavailable`.
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
