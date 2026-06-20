## Codex - Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule 1/2).
Section last edited: 2026-06-20 00:17 +1000 - Codex.

**Latest Codex update (2026-06-20 00:17 +1000 - Codex):**
Full variant-report scan/view-metric slice is complete locally. The report
header now shows backend-backed view count and report update date; WorkRail
related variant rows fetch/display their own per-variant view count and
last-viewed update date from the same aggregate metric path. The backend exposes
public, length-validated, rate-limited `GET`/`POST /api/v1/library/views/{query}`
over aggregate `variant_view_count`; saved-library CRUD remains authenticated,
and Supabase writes stay service-role/RPC only. Offline fixtures skip the
view-metric API so browser/preflight checks do not need a backend. Active
report/ACMG mock markers and dead report fixtures were removed; unused
`app/web/lib/acmg/mock.ts` and `app/web/components/report/ProteinTrack.tsx` were
deleted. Protein architecture view was browser-verified; the report preflight
URL parser was fixed and the fixture report is clean at 390/768 with no console
errors/overflow offenders. Ask-Eamos mock CLI and chat tests passed; live CLI
correctly skipped with `LLM_PROVIDER=mock`. Project-100 stack, focused backend
tests, frontend lint, diff-check (only LF/CRLF warnings), active report mock
scan, and graphify update passed.

M12/M13 CI-SpliceAI/CAPICE state remains as previously recorded: backend rows
emit only when complete local artifacts and sidecar manifests exist, with
commercial/launch/provenance metadata preserved. PubMed eUtils key remains only
in ignored `app/backend/.env`; do not echo or commit it. No live
seed/upload/write/provider flip/local-evidence flip/startup materialization
occurred.

**Latest resume prompt:**
```text
# Resume prompt - 2026-06-20 00:17 +1000 - Codex variant report scan/view metrics complete
Eamos. Read AGENTS.md, agent_handoff/README.md, agent_handoff/CURRENT.md (Codex section + locks), agent_handoff/RISKS.md, MEMORY.md, docs/backend-build-ledger-runtime/plan.md, docs/backend-build-ledger-runtime/materialization-plan.md, then run git -C D:/eamos fetch origin; git -C D:/eamos status --short --branch; git -C D:/eamos log -8 --oneline.
Delta: full variant report scan/view-metric slice is locally complete. Header and WorkRail related variants now display backend-backed per-variant view counts/update dates via public, rate-limited aggregate view endpoints. Offline fixtures skip view-metric API calls. Active report/ACMG mock markers were removed, dead report mock/protein files were deleted, WorkRail hydration/mobile overflow issues found by preflight were fixed, and the protein architecture view browser-rendered correctly. Corrected report preflight is clean at 390/768. Ask-Eamos mock CLI/tests passed; live CLI skips while `LLM_PROVIDER=mock`.
Verification passed: frontend lint; active report mock scan; fixture browser protein SVG check; corrected `eamos-report-preflight` at 390/768; `python -m pytest app/backend/tests/test_variant_library_api.py app/backend/tests/test_frontend_contract.py -q`; chat service/AI-gateway/rate-limit focused tests; project-100 stack; `git diff --check` except existing LF/CRLF warnings; `python -m graphify update .`.
State/guardrails: branch remains main...origin/main [ahead 5] with broad dirty worktree; do not `git add -A`. No commit/push was done. M12/M13 CI-SpliceAI/CAPICE rows still require complete local artifacts; PubMed eUtils key stays only in ignored `app/backend/.env`; keep `LLM_PROVIDER=mock`. No manual bulk connector SQL, PubMed/RAG corpus materialization, ESM1b materialization, provider flips, LOCAL_EVIDENCE_ENABLED flip, startup materialization, ungated Render disk seed, live upload/register/seed, or partial Claude summary.
Next: either isolate/stage intended paths carefully, or continue backend code gates for additional gated predictors (REVEL, PrimateAI-3D, SpliceAI/dbNSFP-style caches) using the same coordinate-key local-reader/report-row pattern and preserving source_id/license_gate/launch_gate/public_serialization/source version/provenance metadata. Recommended variants/workrail ranking/spec can be planned next session; current rows now have the metric display plumbing.
End clear-safe.
```
