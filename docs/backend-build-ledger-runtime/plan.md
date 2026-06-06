# Backend Build Ledger Runtime Plan

1. Add the shared backend build ledger service.
   - Encode every build-ledger lane in one ordered contract.
   - Attach dynamic inspections for hg38, AlphaMissense, ESM1b, protein assets,
     local evidence gates, and source manifest readiness.
   - Keep serialization sanitized.

2. Wire all selected surfaces horizontally.
   - Add `build_ledger` to `/api/v1/health/provider-cache`.
   - Add `build_ledger` to `eamos_source_asset_preflight`.
   - Keep the existing narrower provider summaries in place for compatibility.

3. Enforce runtime asset policy.
   - Remove app-startup coordinate resolver downloads.
   - Fail closed if the legacy startup materialization flag is enabled.
   - Update deployment guidance to seed/materialize by explicit off-peak
     process only.

4. Harden the batch.
   - Add tests for required ledger rows and sanitization.
   - Add tests for preflight ledger output.
   - Add a startup policy test.

5. Compact coordinate index runtime pass.
   - Add the read-only compact index reader and fixture artifact.
   - Build runtime resolver instances from the compact index path with raw GFF
     paths disabled.
   - Wire lookup/search/report, Gene View, local evidence, and batch through
     the shared compact-index contract where those backend boundaries already
     exist.
   - Add explicit sanitized provider-cache and preflight readiness probes for
     the compact index.

6. Verify.
   - Run targeted backend pytest for health, preflight, runtime predictors,
     clinical source tables, literature, and startup policy.
   - Run lint/format checks where available.
   - Run `git diff --check`.
