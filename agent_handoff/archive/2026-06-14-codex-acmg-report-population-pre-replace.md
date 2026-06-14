# Archived Codex Section - 2026-06-14 22:45 +10:00

Archived verbatim before replacing the Codex section in `agent_handoff/CURRENT.md`.

## Codex - Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule 1/2).
Section last edited: 2026-06-14 21:59 +10:00 - Codex. Prior Codex section archived at `agent_handoff/archive/2026-06-14-codex-acmg-points-pre-replace.md`.

**Latest Codex update (2026-06-14 21:59 +10:00 - Codex):**
ACMG Tavtigian-2020 points-engine core is complete locally as a separate backend advisory engine. It does not modify `clinical_consensus.py` and does not populate report payloads yet.

Completed:
- Added `app/backend/app/services/acmg_points_engine.py` with `AcmgCriterionApplication`, `compute_acmg_points()`, `posterior_from_net()`, `tier_from_net()`, and `points_for_strength()`.
- The engine emits the frozen `EamosComputedClassification` Pydantic contract, including version pin, net/sums, posterior, tier, conflict block, BA1 override, benign-cut mode, and complete `per_criterion[]` audit rows.
- Implemented Tavtigian/ADR-0022 math: strength points, posterior formula (`OddsPath = 2.08^net`, prior 0.10), Tavtigian default tier cuts, and the `acgs_panel` benign-cut option for future VCEP overlay use only.
- Implemented fail-closed guards for BA1 as a hard non-summand override, explicit conflict-to-VUS cap, duplicate code rejection, mutually-exclusive pair rejection (`PM2`/`BA1`, `PM2`/`BS1`, `PP3`/`BP4`, `PS3`/`BS3`), missing-strength rejection, and deprecated `PP5`/`BP6` non-activation while keeping them as not-assessed audit rows.
- Added `app/backend/tests/test_acmg_points_engine.py` covering posterior anchors, tier edges, worked examples, BA1, conflict, mutual exclusions, deprecated criteria, complete rows, version pin, and source/provenance field preservation.

Verification recorded 2026-06-14 21:59 +10:00:
- `python -m pytest tests/test_frontend_contract.py -q` passed at session start after Claude's TS mirror.
- `python -m pytest tests/test_acmg_points_engine.py -q` passed.
- `python -m pytest tests/test_acmg_points_engine.py tests/test_frontend_contract.py tests/test_report_acmg_contract.py -q` passed.
- `python -m ruff check app/services/acmg_points_engine.py tests/test_acmg_points_engine.py` passed.
- `python -m black --check --target-version py310 app/services/acmg_points_engine.py tests/test_acmg_points_engine.py` passed after formatting the new service.
- `git diff --check` passed with the repo's usual CRLF warnings.
- `rg -n "[ \t]+$" app/backend/app/services/acmg_points_engine.py app/backend/tests/test_acmg_points_engine.py` returned no matches.
- `node scripts/eamos-encoding-scan.mjs app/backend/app/services/acmg_points_engine.py app/backend/tests/test_acmg_points_engine.py agent_handoff/CURRENT.md --json` passed.
- `python -m graphify update .` passed; graphify refreshed `graphify-out/graph.json`, `GRAPH_REPORT.md`, and `manifest.json` and skipped `graph.html` because the graph has 13,955 nodes.

Guardrails:
- No report population/evidence wiring, VCEP overlay, AI narration, benchmark harness, ClinVar P/B precompute, Render env/provider flip, Supabase mutation, startup download/materialization, commit, push, RAG enablement, or AI-gateway runtime flip.
- Kept frontend files untouched.

**Latest resume prompt:**
```text
# Resume prompt - 2026-06-14 21:59 +1000 - Codex ACMG points-engine core complete
Eamos. Read CODEX.md, AGENTS.md, agent_handoff/README.md, agent_handoff/CURRENT.md, agent_handoff/RISKS.md, docs/report-acmg-viz/spec.md, docs/report-acmg-viz/plan.md, then run git fetch origin && git status --short --branch.
Delta: ACMG Tavtigian-2020 points core is complete locally in `app/backend/app/services/acmg_points_engine.py` with `tests/test_acmg_points_engine.py`; it emits the frozen `EamosComputedClassification` contract and verifies posterior anchors, tier cuts, BA1 override, conflict VUS cap, deprecated PP5/BP6 fail-closed rows, mutual-exclusion rejection, and complete audit rows. Frontend contract canary is green.
Next: hold for Steven's explicit next backend slice. Do not start evidence/report population, VCEP overlay, AI narration, benchmark harness, ClinVar P/B precompute, Render/Supabase/startup-download/provider flip, commit, or push unless explicitly asked. End clear-safe.
```
