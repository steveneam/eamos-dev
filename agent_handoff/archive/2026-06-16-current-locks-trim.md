# Archived Shared File Lock records (trimmed from CURRENT.md 2026-06-16 22:35 +1000)

These are RELEASED Shared File Lock records older than one week (dated 2026-06-07
and 2026-06-08), pruned verbatim from `agent_handoff/CURRENT.md` to keep it under
the handoff-lint 500-line limit (Claude, during the A2+A12+A11 commit closeout).
History only — all locks below are RELEASED. Newer (≤1wk) lock records remain in
CURRENT.md.

- **Codex RELEASED PubMed/PMC local PubTator/LitVar edge-ingestion slice**
  (2026-06-08 02:32 +1000)
  - Scope: `app/backend/app/services/pubmed_local.py`,
    `app/backend/app/cli/eamos_pubmed_local_materialize.py`,
    `app/backend/app/cli/eamos_pubmed_local_preflight.py`, and
    `app/backend/tests/test_pubmed_local.py`.
  - Completed: schema/manifest v4 with `pubmed_literature_edge`; operator
    PubTator/LitVar edge JSONL inputs; edge source-file load-order/provenance;
    per-source edge import/orphan counters; seed pre-scan so edge hits can
    retain neutral article rows during query-scoped materialization; local
    PubMed search enrichment through existing `pubtator` and `litvar2_snippet`
    EP-VLEx fields. Live E-utilities fallback/refresh and no-startup-download
    policy preserved.
  - Verification: `test_pubmed_local.py`, health/publication/lookup/cache/
    frontend-contract pytest subset, Ruff, Black, `py_compile`,
    `python -m graphify update .`, and `git diff --check` passed.

- **Codex RELEASED PubMed/PMC local backend slice**
  (2026-06-08 00:24 +1000)
  - Scope: `app/backend/app/services/pubmed_local.py`,
    `app/backend/app/tools/pubmed.py`,
    `app/backend/app/cli/eamos_pubmed_local_materialize.py`,
    `app/backend/app/cli/eamos_pubmed_local_preflight.py`,
    `app/backend/app/api/routes/{health,lookup}.py`,
    `app/backend/app/services/{build_ledger,lookup_sections,lookup_service}.py`,
    `app/backend/app/{core/config.py,main.py,schemas/lookup.py}`,
    `app/backend/app/fixtures/tools/pubmed_local_sample.xml`,
    `app/backend/tests/{test_pubmed_local.py,test_health_api.py}`, and
    `app/backend/.env.example`.
  - Completed: explicit no-network materialization/preflight CLIs, standalone
    SQLite PubMed-local schema, provenance/checksum manifest, license-gated
    abstract retention, de-identified/sanitized metadata surfaces,
    disabled-by-default local PubMed adapter with `refresh=true` live bypass
    and no-hit live fallback, health/build-ledger status, and additive
    publication request refresh flag.
  - Verification: `test_pubmed_local.py`, `test_health_api.py`,
    tool/publication/lookup/cache/frontend-contract pytest subset, Ruff, Black,
    `py_compile`, and `python -m graphify update .` passed.

- **Codex RELEASED PubMed/PMC local scale-filter hardening**
  (2026-06-08 01:10 +1000)
  - Scope: `app/backend/app/services/pubmed_local.py`,
    `app/backend/app/cli/eamos_pubmed_local_materialize.py`,
    `app/backend/app/cli/eamos_pubmed_local_preflight.py`, and
    `app/backend/tests/test_pubmed_local.py`.
  - Completed: operator-supplied PMC OA license metadata overlays keyed by
    PMCID; optional PubMed XML `.md5` sidecar verification; materialization
    manifest/preflight counters for domain-filtered rows, PMC overlays, and
    input checksum status; opt-in `--domain-filter biomedical` profile with
    gene/biology/biochemistry/chemistry positives, language/status/pub-type
    guardrails, negative-domain exclusions, and token-aware short-gene matching.
    Biomedical engineering, chemical engineering, tissue engineering,
    biomaterials, retinal/gene-delivery contexts are explicit keep cases.
  - Verification: `test_pubmed_local.py`, health/publication/lookup/cache/
    frontend-contract pytest subset, Ruff, Black, `py_compile`, and
    `python -m graphify update .` passed.

- **Codex RELEASED PubMed/PMC local source-manifest scale slice**
  (2026-06-08 01:47 +1000)
  - Scope: `app/backend/app/services/pubmed_local.py`,
    `app/backend/app/cli/eamos_pubmed_local_materialize.py`,
    `app/backend/app/cli/eamos_pubmed_local_preflight.py`,
    `app/backend/app/api/routes/health.py`, and
    `app/backend/tests/test_pubmed_local.py`.
  - Completed: schema/manifest v3 adds `pubmed_source_file` rows with sanitized
    source-file basename, load order, source kind, format, size, MD5 sidecar
    status, and per-shard import counters. Materialization/preflight/health now
    expose source-file count, source-kind counts, and aggregate import stats by
    source kind. CLI adds `--xml-source-kind auto|baseline|update|pubmed_xml`
    for explicit baseline/update batch labeling.
  - Verification: `test_pubmed_local.py`, health/publication/lookup/cache/
    frontend-contract pytest subset, Ruff, Black, `py_compile`, and
    `python -m graphify update .` passed.

- **Codex RELEASED Workbench backend contracts and adapter materialization checks**
  (2026-06-07 19:31 +1000)
  - Scope: `app/backend/app/schemas/workbench.py`,
    `app/backend/app/api/routes/workbench.py`,
    `app/backend/app/services/workbench_design.py`,
    `app/backend/app/services/crispr_ssodn.py`,
    `app/backend/app/services/predictor_runtime.py`,
    `app/backend/app/api/routes/health.py`,
    `app/backend/app/cli/eamos_source_asset_preflight.py`,
    `app/backend/app/services/build_ledger.py`,
    `app/backend/tests/test_workbench_api.py`,
    `app/backend/tests/test_frontend_contract.py`,
    `app/backend/tests/test_predictor_runtime.py`,
    `app/backend/tests/test_health_api.py`,
    `app/backend/tests/test_source_asset_preflight_cli.py`,
    `app/frontend/src/lib/backend.ts`, and `app/web/lib/backend.ts`.
  - Completed: additive `POST /api/v1/crispr/ssodn` donor-design contract with
    120 nt configurable default, orderable 5-prime-to-3-prime donor,
    strand/orientation, variant offset, arm lengths, intron mask, warnings,
    and optional guide/PAM-block mode; verified all seven public RPE65 workbook
    examples by uppercase sequence hash and offset, ignoring manual casing only.
  - Completed: CI-SpliceAI and CAPICE admin predictor materialization inspectors
    now feed health, preflight, and build ledger surfaces while preserving
    launch-gate metadata and hiding local paths.
  - Coordination answer to Claude: **A, green**. Claude can commit the full
    coordinated Workbench/off-target FE + backend tree and push. Codex owns the
    SG Render deploy hook and live verification after push.
  - Verification: focused Workbench/backend pytest, predictor runtime pytest,
    health/preflight focused pytest, compact-index materialization pytest,
    frontend contract pytest, Ruff, scoped Black check, backend.ts mirror byte
    check, and `python -m graphify update .` passed.

- **Codex RELEASED CRISPR off-target backend contracts**
  (2026-06-07 18:16 +1000)
  - Scope: `app/backend/app/schemas/workbench.py`,
    `app/backend/app/api/routes/workbench.py`,
    `app/backend/app/services/workbench_design.py`,
    `app/backend/app/services/crispr_offtarget_screening.py`,
    `app/backend/tests/test_workbench_api.py`,
    `app/backend/tests/test_frontend_contract.py`,
    `app/frontend/src/lib/backend.ts`, and `app/web/lib/backend.ts`.
  - Completed: additive `/api/v1/crispr/offtargets` exact
    `{genome_build, sites}` response, additive screening-primer contract reusing
    the existing primer provider, deterministic de-identified off-target fixture,
    focused backend/contract tests, and byte-identical backend.ts mirrors. No
    Claude frontend surface edits.
  - Verification: backend Ruff passed; scoped Black check passed; focused pytest
    passed including compact-index materialization test; backend.ts mirrors
    byte-identical; `python -m graphify update .` passed.
