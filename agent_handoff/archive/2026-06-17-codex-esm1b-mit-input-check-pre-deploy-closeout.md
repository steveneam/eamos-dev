## Codex - Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule 1/2).
Section last edited: 2026-06-17 18:32 +1000 - Codex.

**Latest Codex update (2026-06-17 18:32 +1000 - Codex):**
Checked the ESM1b clean MIT-regeneration continuation point after Steven rejected the
HF precomputed score zip for the commercial path. The MIT-regeneration code path remains
wired locally, but the operator-generated inputs are not present.

Completed:
- Read the required handoff/docs and current git state.
- Confirmed `main...origin/main [ahead 3]`; recent commits are Claude web `c1ff060`,
  Claude web `999d0e9`, and Codex Tier 2 `dc9ec94`.
- Searched for clean-path inputs by exact filename:
  `esm1b-mit-regenerated-scores.csv` and `esm1b-mane-codon-contexts.jsonl`.
- Confirmed the default ESM1b runtime outputs are absent:
  `app/backend/data/bio_assets/predictors/esm1b/esm1b_hg38.tsv.gz`,
  `.tbi`, and `.manifest.json`.
- Reran read-only Tier 2 planner and source preflight from `app/backend`.

Current result:
- No ESM1b materialization was performed because the required MIT-regenerated score CSV
  and MANE codon-context JSONL were not found.
- No Hugging Face precomputed/non-commercial score zip was downloaded, staged, or used.
- `eamos_tier2_predictor_artifact_upload --compact` still reports `planned_count=0`,
  `missing_local_file=9`; ESM1b components are `missing_local_file`.
- `eamos_source_asset_preflight --compact` still reports the ESM1b build-ledger item as
  `missing_source_file` with launch gate `esm1b_mit_regeneration_required`.
- No Storage upload, no Supabase metadata/apply, no Render disk sync, no provider/env flip,
  and no `LOCAL_EVIDENCE_ENABLED` flip.

Clean-path command contract once the operator-side files exist:

```powershell
cd app/backend
python -m app.cli.eamos_esm1b_regenerated_scores_materialize `
  --score-csv <staging>/esm1b-mit-regenerated-scores.csv `
  --codon-context-jsonl <staging>/esm1b-mane-codon-contexts.jsonl `
  --target-path data/bio_assets/predictors/esm1b/esm1b_hg38.tsv.gz `
  --mane-version <MANE release/version> `
  --grch38-reference-sha256 <hg38 reference SHA256> `
  --require-ready `
  --compact
```

**Latest resume prompt:**
```text
# Resume prompt - 2026-06-17 18:32 +1000 - Codex ESM1b MIT-regeneration input check
Eamos. Read AGENTS.md, agent_handoff/README.md, agent_handoff/CURRENT.md, agent_handoff/RISKS.md, docs/pubmed-corpus-materialization/spec.md, docs/backend-build-ledger-runtime/materialization-plan.md, then run git status --short --branch and git log -8 --oneline.
Delta: MIT-regenerated ESM1b materialization path is wired locally, but no clean staging inputs were found; no materialization was run and no HF precomputed zip was substituted.
Current result: exact-name D: search found no `esm1b-mit-regenerated-scores.csv`, no `esm1b-mane-codon-contexts.jsonl`, and no local `esm1b_hg38.tsv.gz/.tbi/manifest`; read-only Tier 2 planner/preflight still show ESM1b `missing_local_file` / `missing_source_file` with `launch_gate=esm1b_mit_regeneration_required`.
Next: obtain or place the MIT-regenerated score CSV plus MANE codon-context JSONL in staging, then run `python -m app.cli.eamos_esm1b_regenerated_scores_materialize ... --require-ready --compact`; expected output is `esm1b_hg38.tsv.gz`, `.tbi`, and sidecar manifest with MIT-regenerated provenance and `license_gate: null`.
Guardrails: no HF score zip for the commercial path; no Storage upload; no Supabase metadata/apply; no Render disk sync; no provider/env flips; no `LOCAL_EVIDENCE_ENABLED` flip; explicit pathspecs only; keep held/unrelated files excluded (`app/web` compare files, `docs/proprietary/eamos-ai-gateway.md`, `scripts/eamos-encoding-scan.mjs`, `graphify-out/2026-06-15/`, unrelated handoff archives). End clear-safe.
```
