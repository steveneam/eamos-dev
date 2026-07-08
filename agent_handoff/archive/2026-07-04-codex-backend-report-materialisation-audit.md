# Archived Codex Handoff - Backend/Search/Report Materialisation Audit

Archived from `agent_handoff/CURRENT.md` on 2026-07-04 20:18 +1000 by Codex before replacing the live Codex section with the free in-silico predictor readiness handoff.

## Codex - Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule 1/2).
Section last edited: 2026-07-04 19:51 +1000 - Codex.

**Latest Codex update (2026-07-04 19:51 +1000 - Codex):**
Set Obsidian aside and ran a read-only backend/search/report materialisation
audit using the required graphify query, local docs/code inspection, and three
read-only subagents. No runtime/provider/source mutation occurred.

Findings:

- Search 7/8 is closed in repo at `HEAD == origin/main == 436721e`; auth-required
  read-only search is wired and tested. Open search work is product/deploy
  posture: mobile browser verification, optional live deploy smoke, stale
  Search index plan status cleanup, and broader public entity coverage only
  where existing durable payloads already support it.
- Report materialisation is mixed but honest: report shell, lookup payload,
  population, gene/locus context, lazy sections, source versions, data currency,
  ClinVar gene distribution, and local-evidence Phase 0 are materially wired.
  ClinGen VCEP source-cache copy/status and some molecular/protein warnings
  still need reconciliation.
- MAVE/MaveDB is functional evidence, not an in-silico predictor. The CC0 local
  materializer, runtime store, health/preflight/build-ledger surfaces, and report
  block are code-backed, but provider-cache still treats MaveDB as
  `cc0_import_not_materialized`; next safe work is a no-apply preflight/status
  pass, then Steven-approved CC0 materialisation and smoke.
- Tier-2 in-silico predictors are backend/admin-wired but artifact-gated:
  CI-SpliceAI needs a complete model/reference/score-cache set; CAPICE needs
  model plus SpliceAI-derived feature cache; ESM1b needs the private
  MIT-regenerated score CSV path and manifest metadata; REVEL and PrimateAI-3D
  need exact-variant score caches. Rows preserve provenance and launch-gate
  metadata and fail closed when artifacts are absent.
- AlphaMissense is the current local predictor lane treated as live/runtime-ready
  in the local-evidence/freshness stack. SpliceAI/CADD/REVEL rows can also appear
  from existing computational annotation payloads when backend data supplies
  them, but missing engines remain placeholders in the report UI. GPN-MSA and
  Pangolin are frontend catalog/planned surfaces rather than materialised backend
  lanes.
- Safe next plan: reconcile stale docs; write/update a predictor materialisation
  matrix covering artifact, license/launch gate, provider-cache key, report row,
  and verification; prioritize MaveDB CC0 first, then CI-SpliceAI/CAPICE complete
  artifact gates, then ESM1b after operator file availability, then REVEL/
  PrimateAI-3D/CADD/GPN-MSA/Pangolin source decisions.

No deploy/env/provider flip, Supabase mutation, runtime seed/sync, source
materialization/download/upload, deploy hook use, destructive git, secret output,
or Obsidian write/execute/open tool use occurred.

Previous Obsidian MCP handoff archived at
`agent_handoff/archive/2026-07-04-codex-obsidian-mcp-handoff.md`.

**Latest resume prompt:**
```text
# Resume prompt - 2026-07-04 19:51 +1000 - Codex backend/report materialisation audit
Eamos. Read AGENTS.md, CODEX.md, agent_handoff/README.md, agent_handoff/CURRENT.md, agent_handoff/RISKS.md, PROGRESS.md top, COORDINATION.md, docs/parallel-agents/{retrofit-notes,ratchet-philosophy}.md, docs/search-results-and-answer-hardening/{design,spec,plan}.md, docs/search-index/{spec,plan}.md, then git status --short --branch.
Delta: Obsidian set aside. Read-only backend/search/report audit found Search 7/8 closed at `origin/main` `436721e`; report core materialisation mostly wired; MaveDB CC0 is code-backed but not materialised; CI-SpliceAI/CAPICE/ESM1b/REVEL/PrimateAI-3D are backend/admin-wired but artifact-gated; AlphaMissense is the live/runtime-ready predictor lane; GPN-MSA/Pangolin remain catalog/planned surfaces.
Next: safe docs/planning slice: reconcile stale search/materialisation docs and write/update a predictor-materialisation matrix (artifact, license/launch gate, provider-cache key, report row, verification). If moving beyond planning, MaveDB CC0 preflight is first, then Tier-2 complete artifact gates, each only with Steven approval.
Guardrails: keep Search auth-required/read-only unless explicitly changed; no env/provider flips, Supabase mutation, runtime seed/sync, source materialization/download/upload, deploy hook use, destructive git, secret output, or Obsidian write/execute/open tool use/allowlisting unless explicitly approved.
End clear-safe with a fresh stamped resume prompt.
```
